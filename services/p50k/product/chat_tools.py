"""Four typed, bounded read-only chat tools with the D7 evidence allowlist."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from p50k.product.ai_client import AIUnavailable
from p50k.product.archive import canonical_json
from p50k.product.db import connect
from p50k.product.egress import Evidence, Packet, allowed_options
from p50k.product.settings import Settings
from p50k.product.analysis_context import current_cutoff,data_origins,historical_mode
from p50k.product.archive import ISTANBUL


@dataclass(frozen=True)
class ChatContext:
    packet: Packet
    run_id: str
    origin: str
    checksum: str
    reasons: dict[str, str] = field(default_factory=dict)
    # Server-side request facts for the agent tools; never taken from the client body.
    scope: str | None = None
    user_id: str | None = None
    team_case: dict | None = None


def load_context(settings: Settings, code: str, evidence_id: str | None = None) -> ChatContext:
    """Read existing evidence without creating/changing a decision packet."""
    now = current_cutoff(settings)
    origins = data_origins(settings)
    if settings.db_name=='p50k_dev':origins.append('SYNTHETIC')
    with connect(settings) as connection:
        connection.execute('SET TRANSACTION READ ONLY')
        connection.execute("SET LOCAL statement_timeout='5s'")
        fund = connection.execute('SELECT name,category FROM ref.funds WHERE fund_code=%s', (code,)).fetchone()
        if not fund:
            raise AIUnavailable('FUND_NOT_FOUND')
        run = connection.execute("""SELECT run.run_id,input.as_of,run.origin,run.cutoff
            FROM det.detector_runs run JOIN det.run_inputs input USING(run_id)
            WHERE run.origin=ANY(%s) AND input.complete AND run.cutoff<=%s
              AND (NOT %s OR (run.cutoff AT TIME ZONE 'Europe/Istanbul')::date=%s)
              AND (%s::text IS NULL OR EXISTS(SELECT 1 FROM det.evidence_items selected
                  WHERE selected.run_id=run.run_id AND selected.fund_code=%s AND selected.evidence_id=%s))
            ORDER BY run.cutoff DESC,run.created_at DESC,run.run_id DESC LIMIT 1""", (origins, now, historical_mode(settings),now.astimezone(ISTANBUL).date(),evidence_id, code, evidence_id)).fetchone()
        if not run:
            raise AIUnavailable('EVIDENCE_UNAVAILABLE')
        rows = connection.execute("""SELECT item.evidence_id,item.detector_id,item.state,
            signal.value,signal.threshold,item.effective_date,item.metadata
            FROM det.signals signal JOIN det.evidence_items item USING(evidence_id)
            WHERE signal.run_id=%s AND signal.fund_code=%s
              AND signal.as_of<=%s AND (item.effective_date IS NULL OR item.effective_date<=%s)
              AND (item.available_at<=%s OR (item.available_at IS NULL AND signal.state='ABSTAINED'))
            ORDER BY signal.detector_id LIMIT 8""", (run[0], code, run[1],run[1],run[3])).fetchall()
    if not rows or (evidence_id is not None and evidence_id not in {row[0] for row in rows}):
        raise AIUnavailable('EVIDENCE_UNAVAILABLE')
    evidence = [Evidence(evidence_id=row[0], detector_id=row[1], state=row[2],
        value=str(row[3]) if row[3] is not None else None, threshold=str(row[4]) if row[4] is not None else None,
        effective_date=row[5].isoformat() if row[5] else None, is_attribute=bool(row[6].get('is_attribute'))) for row in rows]
    packet = Packet(fund_code=code, fund_name=fund[0], category=fund[1], as_of=run[1].isoformat(),
                    evidence=evidence, allowed_options=allowed_options(evidence))
    payload = {**packet.model_dump(), 'run_id':str(run[0]), 'origin':run[2], 'cutoff':run[3].isoformat()}
    return ChatContext(packet, str(run[0]), run[2], hashlib.sha256(canonical_json(payload).encode()).hexdigest(),
                       {row[0]:str(row[6].get('reason','')) for row in rows})


class FundArguments(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    fund_code: str = Field(pattern=r'^[A-Z0-9]{2,12}$')


class SearchArguments(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    query: str = Field(min_length=1, max_length=80)
    limit: int = Field(ge=1, le=5)


ARGUMENTS = {'search_funds':SearchArguments, 'get_fund_profile':FundArguments,
             'get_signals':FundArguments, 'get_decision':FundArguments,
             'get_case_status':FundArguments, 'request_investigation':FundArguments}
TOOLS = [{'type':'function', 'name':name, 'description':description, 'strict':True,
          'parameters':ARGUMENTS[name].model_json_schema()} for name, description in (
    ('search_funds','Find up to five public fund catalog entries. Current metadata only.'),
    ('get_fund_profile','Read public name and category for the current thread fund.'),
    ('get_signals','Read deterministic evidence for the current thread fund; no raw prices.'),
    ('get_decision','Read the effective enum and evidence IDs for the current evidence packet; no private review text.'),
    ('get_case_status','Read the agent team case for the current thread fund in the selected date: step statuses, '
                       'validated team output with evidence aliases and categorical test outcomes.'),
    ('request_investigation','Queue an investigation of the current thread fund by the agent team at user priority. '
                             'Use only when the user asks for an investigation or a new review round; a reported '
                             'case that no human has reviewed starts a new round. Deduplicated and rate-limited.'))]
AGENT_TOOLS = {'get_case_status', 'request_investigation'}
# Tools that reveal no identity, offered in historical (anonymous) views.
HISTORICAL_TOOLS = {'get_signals', 'get_decision', *AGENT_TOOLS}


def bounded_json(payload: Any, limit: int = 4096) -> str:
    value = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
    if len(value.encode()) > limit:
        raise AIUnavailable('TOOL_OUTPUT_TOO_LARGE')
    return value


def agent_tool(settings: Settings, scope: str | None, user_id: str | None, name: str, code: str,
               packet: Packet | None = None, run_id: str | None = None) -> str:
    """The two agent tools; request_investigation uses the same service and limits as POST /agents/requests."""
    if not scope or not user_id:
        raise AIUnavailable('TOOL_UNAVAILABLE')
    import psycopg
    from p50k.product.agents import service
    try:
        if name == 'get_case_status':
            return bounded_json(service.case_status(settings, scope, code, packet, run_id), 8192)
        outcome = service.request_investigation(settings, scope, user_id, code)
    except service.AgentRequestError as error:
        raise AIUnavailable(error.code) from None
    except psycopg.Error:
        raise AIUnavailable('TOOL_UNAVAILABLE') from None
    return bounded_json({'queued': outcome['queued'], 'case_status': outcome['status'], 'outcome': outcome['outcome']})


def invoke_tool(settings: Settings, context: ChatContext, name: str, raw: str) -> str:
    if context.origin=='HISTORICAL_REPLAY' and name in {'search_funds','get_fund_profile'}:
        raise AIUnavailable('TOOL_UNAVAILABLE_FOR_HISTORICAL_CONTEXT')
    if name not in ARGUMENTS or len(raw.encode()) > 1024:
        raise AIUnavailable('TOOL_ARGUMENT_REJECTED')
    try:
        args = ARGUMENTS[name].model_validate_json(raw)
    except ValueError:
        raise AIUnavailable('TOOL_ARGUMENT_REJECTED') from None
    packet = context.packet
    if name != 'search_funds' and args.fund_code != packet.fund_code:
        raise AIUnavailable('TOOL_SCOPE_REJECTED')
    if name in AGENT_TOOLS:
        return agent_tool(settings, context.scope, context.user_id, name, packet.fund_code, packet, context.run_id)
    if name == 'get_fund_profile':
        return bounded_json({'fund_code':packet.fund_code, 'name':packet.fund_name,
                             'category':packet.category, 'metadata_scope':'CURRENT_CATALOG'})
    if name == 'get_signals':
        return bounded_json(packet.model_dump())
    with connect(settings) as connection:
        connection.execute('SET TRANSACTION READ ONLY')
        connection.execute("SET LOCAL statement_timeout='5s'")
        if name == 'search_funds':
            term = '%' + args.query.replace('\\','\\\\').replace('%','\\%').replace('_','\\_') + '%'
            rows = connection.execute('SELECT fund_code,name FROM ref.funds WHERE fund_code ILIKE %s OR name ILIKE %s ORDER BY fund_code LIMIT %s',
                                      (term, term, args.limit)).fetchall()
            return bounded_json({'items':[{'fund_code':row[0], 'name':row[1]} for row in rows]})
        row = connection.execute("""SELECT value.effective_value,value.effective_source,decision.evidence_ids
            FROM ai.effective_decisions value JOIN ai.packets packet USING(packet_id)
            LEFT JOIN ai.decisions decision ON decision.decision_id=value.decision_id
            WHERE value.fund_code=%s AND packet.packet_sha256=%s
            ORDER BY packet.packet_id DESC LIMIT 1""", (packet.fund_code, context.checksum)).fetchone()
        return bounded_json({'decision':row[0] if row else 'UNDECIDED',
                             'source':row[1] if row else None, 'evidence_ids':row[2] if row else []})
