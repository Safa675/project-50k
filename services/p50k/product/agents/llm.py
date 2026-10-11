"""Budgeted Responses calls for agent roles: daily bucket, total target, store=false, no SDK retries."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from contextlib import contextmanager
from contextvars import ContextVar
from decimal import Decimal
import json
import socket

from openai import OpenAI, APIConnectionError, APITimeoutError
import httpx2
try:
    import httpx
except ImportError:
    httpx = httpx2

from p50k.product.agents.config import AgentConfig, RoleModel
from p50k.product.agents.vocabulary import FAST_ROLES
from p50k.product.ai_client import AIUnavailable, reserve, settle
from p50k.product.archive import ISTANBUL
from p50k.product.db import connect
from p50k.product.settings import Settings

MAX_INPUT_BYTES = 24576
TOTAL_TARGET_RETRY = timedelta(minutes=15)
USER_REQUEST: ContextVar[bool] = ContextVar('agent_user_request', default=False)


@contextmanager
def task_budget(user_request: bool):
    token = USER_REQUEST.set(user_request)
    try:
        yield
    finally:
        USER_REQUEST.reset(token)


def request_not_sent(error: Exception) -> bool:
    """Only proven connection establishment/DNS failures are free of remote usage.

    Read/write/protocol errors and timeouts remain uncertain and retain the
    reservation. The installed SDK uses httpx2; accept httpx for older transports.
    """
    if not isinstance(error, APIConnectionError) or isinstance(error, APITimeoutError):
        return False
    chain: list[BaseException] = []
    pending: list[BaseException] = [error]
    while pending:
        current = pending.pop()
        if any(current is item for item in chain):
            continue
        chain.append(current)
        pending.extend(item for item in (current.__cause__, current.__context__) if item is not None)
    uncertain = (TimeoutError, httpx.TimeoutException, httpx2.TimeoutException,
                 httpx.ReadError, httpx.WriteError, httpx.ProtocolError,
                 httpx2.ReadError, httpx2.WriteError, httpx2.ProtocolError)
    if any(isinstance(item, uncertain) for item in chain):
        return False
    return any(isinstance(item,(socket.gaierror,httpx.ConnectError,httpx2.ConnectError)) for item in chain)


class BudgetWait(Exception):
    """No reservation is possible now; the task waits instead of failing."""

    def __init__(self, reason: str, until: datetime, calls: list[str] | None = None, cost: Decimal = Decimal(0)):
        self.reason, self.until, self.calls, self.cost = reason, until, calls or [], cost
        super().__init__(reason)


class CallFailed(Exception):
    """A reserved call did not complete; its reservation was settled conservatively."""

    def __init__(self, code: str, call_id: str, cost: Decimal):
        self.code, self.call_id, self.cost = code, call_id, cost
        super().__init__(code)


def istanbul_today() -> date:
    return datetime.now(ISTANBUL).date()


def daily_bucket(day: date | None = None) -> str:
    return 'agents:' + (day or istanbul_today()).isoformat()


def next_budget_day() -> datetime:
    return datetime.combine(istanbul_today() + timedelta(days=1), time.min, ISTANBUL).astimezone(timezone.utc)


def role_model(config: AgentConfig, role: str) -> RoleModel:
    return config.fast if role in FAST_ROLES else config.strong


def ensure_daily_bucket(connection, config: AgentConfig, day: date | None = None) -> str:
    bucket = daily_bucket(day)
    connection.execute('INSERT INTO ai.budget_buckets(bucket,cap_usd,enabled) VALUES (%s,%s,true) ON CONFLICT DO NOTHING',
                       (bucket, config.daily_cap_usd))
    return bucket


def reserve_agent_budget(settings: Settings, config: AgentConfig, amount: Decimal) -> str:
    """Check the overall target across every bucket, then reserve in today's agent bucket."""
    with connect(settings) as connection:
        connection.execute("SET LOCAL statement_timeout='5s'")
        bucket = ensure_daily_bucket(connection, config)
        total = connection.execute('SELECT COALESCE(sum(spent_usd+reserved_usd),0) FROM ai.budget_buckets').fetchone()[0]
    if Decimal(total) + amount > config.total_target_usd:
        raise BudgetWait('TOTAL_TARGET', datetime.now(timezone.utc) + TOTAL_TARGET_RETRY)
    try:
        protected = config.background_reserve_usd if config.demo and not USER_REQUEST.get() else Decimal(0)
        return reserve(settings, bucket, amount, protected_usd=protected)
    except AIUnavailable as error:
        if str(error) == 'BUDGET_UNAVAILABLE':
            raise BudgetWait('DAILY_BUDGET', next_budget_day()) from None
        raise


def call(settings: Settings, config: AgentConfig, role: str, *, instructions: str, payload: dict,
         schema: dict, schema_name: str, prompt_version: str, schema_version: str) -> tuple[str, str, Decimal, str]:
    """One strict-schema call. Returns output text, call ID, booked cost and model."""
    from p50k.product.agents import control
    model = role_model(config, role)
    if config.mode != 'live':
        raise AIUnavailable('AI_OFF')
    if settings.db_name != 'p50k':
        raise AIUnavailable('LIVE_DATABASE_REJECTED')
    if not config.key_file.is_file():
        raise AIUnavailable('KEY_UNAVAILABLE')
    if not model.priced:
        raise AIUnavailable('MODEL_PRICING_UNCONFIGURED')
    control.require_running(settings)
    body = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
    if len(body.encode()) > MAX_INPUT_BYTES:
        raise AIUnavailable('INPUT_REJECTED')
    input_bytes = len(body.encode()) + len(instructions.encode()) + len(json.dumps(schema).encode()) + 1024
    maximum = (Decimal(input_bytes) * model.input_price
               + Decimal(model.max_output_tokens) * model.output_price) / Decimal(1000000)
    reservation = reserve_agent_budget(settings, config, maximum)
    response = None
    booked = maximum
    try:
        client = OpenAI(api_key=config.key_file.read_text(encoding='utf-8').strip(), max_retries=0,
                        timeout=config.timeout_seconds)
        response = client.responses.create(model=model.model, store=False, max_output_tokens=model.max_output_tokens,
            service_tier='default', reasoning={'effort': model.effort}, instructions=instructions, input=body,
            text={'format': {'type': 'json_schema', 'name': schema_name, 'strict': True, 'schema': schema}})
        if response.status != 'completed' or not response.usage:
            raise AIUnavailable('MODEL_INCOMPLETE')
        cost = (Decimal(response.usage.input_tokens) * model.input_price
                + Decimal(response.usage.output_tokens) * model.output_price) / Decimal(1000000)
        booked = cost
        settle(settings, reservation, cost)
        with connect(settings) as connection:
            connection.execute("SET LOCAL statement_timeout='5s'")
            connection.execute("""INSERT INTO ai.calls(call_id,reservation_id,model_id,ai_mode,prompt_version,schema_version,
                input_tokens,output_tokens,cost_usd,outcome) VALUES (%s,%s,%s,'live',%s,%s,%s,%s,%s,'COMPLETED')""",
                (response.id, reservation, model.model, prompt_version, schema_version,
                 response.usage.input_tokens, response.usage.output_tokens, cost))
        return response.output_text, response.id, cost, model.model
    except Exception as error:
        unsent = response is None and request_not_sent(error)
        booked = Decimal(0) if unsent else booked
        settle(settings, reservation, booked)
        raise CallFailed('MODEL_CONNECTION_FAILED' if unsent else 'MODEL_CALL_FAILED',
                         getattr(response, 'id', None) or 'reservation:' + reservation, booked) from None
