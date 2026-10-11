"""Agent cases, leased tasks and append-only messages in PostgreSQL.

Every query that selects evidence runs inside the analysis view of its case
(`use_analysis_date`), so a case can only ever see its own day's detector run.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import re
from typing import Any
from uuid import uuid4

from psycopg.types.json import Jsonb

from p50k.product.agents import control
from p50k.product.agents.vocabulary import ROLES, TASK_TITLES, FAILED_STEP_TR
from p50k.product.analysis_context import current_cutoff, data_origins, historical_mode, validate_date
from p50k.product.archive import ISTANBUL
from p50k.product.chat_language import DEFINITIONS
from p50k.product.settings import Settings

SCOPE = re.compile(r'^(live|asof:[0-9]{4}-[0-9]{2}-[0-9]{2})$')
LEASE_SECONDS = 300
MAX_ATTEMPTS = 3
CLAIM_LOCK = 50000036
REQUEST_LOCK = 50000037


def scope_date(scope: str) -> str:
    if not SCOPE.fullmatch(scope):
        raise ValueError('SCOPE_INVALID')
    return 'live' if scope == 'live' else scope[len('asof:'):]


def scope_key(selected: str) -> str:
    return 'live' if selected == 'live' else 'asof:' + selected


def default_scope(settings: Settings) -> str | None:
    try:
        return scope_key(validate_date(settings.analysis_date))
    except ValueError:
        return None


def label(detector_id: str) -> str:
    return DEFINITIONS.get(detector_id, ('Kaynak incelemesi', '', ''))[0]


@dataclass(frozen=True)
class Run:
    run_id: str
    as_of: date
    origin: str
    cutoff: datetime


def scope_run(connection, settings: Settings) -> Run | None:
    """Newest complete run for the active view, with the same rule as decision packets."""
    cutoff = current_cutoff(settings)
    origins = data_origins(settings)
    if settings.db_name == 'p50k_dev':
        origins.append('SYNTHETIC')
    row = connection.execute("""SELECT run.run_id,input.as_of,run.origin,run.cutoff
        FROM det.detector_runs run JOIN det.run_inputs input USING(run_id)
        WHERE run.origin=ANY(%s) AND input.complete AND run.cutoff IS NOT NULL AND run.cutoff<=%s
          AND (NOT %s OR (run.cutoff AT TIME ZONE 'Europe/Istanbul')::date=%s)
        ORDER BY run.cutoff DESC,run.created_at DESC,run.run_id DESC LIMIT 1""",
        (origins, cutoff, historical_mode(settings), cutoff.astimezone(ISTANBUL).date())).fetchone()
    return Run(str(row[0]), row[1], row[2], row[3]) if row else None


def triggered_funds(connection, run: Run) -> list[dict[str, Any]]:
    """Non-attribute TRIGGERED evidence by fund, admitted by the run's own cutoff."""
    rows = connection.execute("""SELECT signal.fund_code,
            array_agg(signal.detector_id ORDER BY signal.detector_id),
            array_agg(signal.evidence_id ORDER BY signal.detector_id),
            bool_or(signal.detector_id='AN-FND-005')
        FROM det.signals signal JOIN det.evidence_items item USING(evidence_id)
        WHERE signal.run_id=%s AND signal.state='TRIGGERED' AND signal.as_of<=%s
          AND NOT COALESCE((item.metadata->>'is_attribute')::boolean,false)
          AND item.available_at IS NOT NULL AND item.available_at<=%s
        GROUP BY signal.fund_code ORDER BY signal.fund_code""", (run.run_id, run.as_of, run.cutoff)).fetchall()
    return [{'fund_code': row[0], 'detectors': list(row[1]), 'evidence_ids': list(row[2]), 'regulatory': bool(row[3])}
            for row in rows]


def add_message(connection, case_id: str, task_id: str | None, from_role: str, to_role: str, kind: str,
                body: str, payload: dict[str, Any] | None = None, model_id: str | None = None,
                prompt_version: str | None = None) -> int:
    return connection.execute("""INSERT INTO agents.messages
        (case_id,task_id,from_role,to_role,kind,body_tr,payload,model_id,prompt_version)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING message_id""",
        (case_id, task_id, from_role, to_role, kind, body, Jsonb(payload or {}), model_id, prompt_version)).fetchone()[0]


def open_case(connection, *, scope: str, fund_code: str, run: Run, opened_by: str, priority: int,
              title: str, requested_by: str | None = None, opening_note: str,
              payload: dict[str, Any] | None = None) -> str | None:
    """Create one case with its dependent tasks; None when an active case already exists."""
    row = connection.execute("""INSERT INTO agents.cases
        (analysis_scope_key,fund_code,opened_by,requested_by,priority,detector_run_id,title_tr)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (analysis_scope_key,fund_code) WHERE status<>'closed' DO NOTHING RETURNING case_id""",
        (scope, fund_code, opened_by, requested_by, priority, run.run_id, title[:240])).fetchone()
    if not row:
        return None
    case_id = str(row[0])
    source = 'user' if opened_by == 'user' else 'system'
    ids = {role: str(uuid4()) for role in ROLES}
    plan = [('hypothesizer', []), ('skeptic', []),
            ('verifier', [ids['hypothesizer'], ids['skeptic']]), ('reporter', [ids['verifier']])]
    if opened_by == 'sentinel':
        connection.execute("""INSERT INTO agents.tasks(task_id,case_id,role,status,priority,source,title_tr,started_at,finished_at,attempts)
            VALUES (%s,%s,'sentinel','done',%s,'system',%s,clock_timestamp(),clock_timestamp(),1)""",
            (ids['sentinel'], case_id, priority, TASK_TITLES['sentinel']))
    for role, depends in plan:
        connection.execute("""INSERT INTO agents.tasks(task_id,case_id,role,priority,source,requested_by,depends_on,title_tr)
            VALUES (%s,%s,%s,%s,%s,%s,%s::uuid[],%s)""",
            (ids[role], case_id, role, priority, source, requested_by, depends, TASK_TITLES[role]))
    if opened_by == 'sentinel':
        add_message(connection, case_id, ids['sentinel'], 'sentinel', 'team', 'case_opened', opening_note, payload)
    else:
        add_message(connection, case_id, None, 'reporter', 'team', 'handoff', opening_note, payload)
    return case_id


def raise_case(connection, case_id: str, priority: int, *, user: str | None = None) -> None:
    """Move an active case up the queue; a user request may also retry stopped AI steps."""
    connection.execute("UPDATE agents.cases SET priority=GREATEST(priority,%s) WHERE case_id=%s AND status<>'closed'",
                       (priority, case_id))
    if user is None:
        connection.execute("""UPDATE agents.tasks SET priority=GREATEST(priority,%s)
            WHERE case_id=%s AND status IN ('queued','waiting_budget','running')""", (priority, case_id))
        return
    connection.execute("""UPDATE agents.tasks SET priority=GREATEST(priority,%s),source='user',
            requested_by=COALESCE(requested_by,%s),
            not_before=CASE WHEN status='waiting_budget' THEN clock_timestamp() ELSE not_before END
        WHERE case_id=%s AND status IN ('queued','waiting_budget','running')""", (priority, user, case_id))
    connection.execute("""UPDATE agents.tasks SET status='queued',priority=GREATEST(priority,%s),source='user',
            requested_by=COALESCE(requested_by,%s),not_before=clock_timestamp(),finished_at=NULL,error_class=NULL
        WHERE case_id=%s AND role<>'sentinel' AND attempts<%s
          AND (status='failed' OR (status='skipped' AND error_class IN ('AI_OFF','AI_UNAVAILABLE')))""",
        (priority, user, case_id, MAX_ATTEMPTS))


def close_case(connection, case_id: str, note: str, from_role: str = 'sentinel') -> None:
    connection.execute("""UPDATE agents.tasks SET status='skipped',finished_at=clock_timestamp(),error_class='CASE_CLOSED'
        WHERE case_id=%s AND status IN ('queued','waiting_budget')""", (case_id,))
    connection.execute("UPDATE agents.cases SET status='closed',closed_at=clock_timestamp() WHERE case_id=%s AND status<>'closed'",
                       (case_id,))
    add_message(connection, case_id, None, from_role, 'team', 'note', note)


@dataclass(frozen=True)
class Task:
    task_id: str
    case_id: str
    role: str
    attempts: int
    priority: int
    source: str
    scope: str
    fund_code: str
    detector_run_id: str
    packet_sha256: str | None
    case_status: str


CLAIM_SQL = """WITH candidate AS (
    SELECT task.task_id FROM agents.tasks task JOIN agents.cases item USING(case_id)
    WHERE item.status IN ('open','investigating') AND task.role<>'sentinel' AND task.attempts<%(maximum)s
      AND ((task.status IN ('queued','waiting_budget') AND task.not_before<=now())
           OR (task.status='running' AND task.lease_until<now()))
      AND NOT EXISTS (SELECT 1 FROM agents.tasks dependency WHERE dependency.task_id=ANY(task.depends_on)
          AND dependency.status NOT IN ('done','failed','skipped'))
      AND (task.source='user' OR item.status<>'open' OR NOT EXISTS (
          SELECT 1 FROM agents.cases recent WHERE recent.started_at>now()-make_interval(secs=>%(gap)s)))
    ORDER BY task.priority DESC,task.created_at,task.task_id
    LIMIT 1 FOR UPDATE OF task SKIP LOCKED)
UPDATE agents.tasks task SET status='running',attempts=task.attempts+1,lease_owner=%(owner)s,
    lease_until=now()+make_interval(secs=>%(lease)s),started_at=COALESCE(task.started_at,clock_timestamp()),
    finished_at=NULL
FROM candidate WHERE task.task_id=candidate.task_id
RETURNING task.task_id,task.case_id,task.role,task.attempts,task.priority,task.source"""


def claim(connection, owner: str, gap_seconds: int) -> Task | None:
    """Highest-priority ready task, with background pacing and an exclusive lease."""
    connection.execute("SET LOCAL statement_timeout='5s'")
    if not control.allows_new_work(connection):
        return None
    connection.execute('SELECT pg_advisory_xact_lock(%s)', (CLAIM_LOCK,))
    exhausted = connection.execute("""UPDATE agents.tasks SET status='failed',lease_owner=NULL,lease_until=NULL,
            finished_at=clock_timestamp(),error_class='ATTEMPTS_EXHAUSTED'
        WHERE status='running' AND lease_until<now() AND attempts>=%s RETURNING task_id,case_id,role""",
        (MAX_ATTEMPTS,)).fetchall()
    for task_id, case_id, role in exhausted:
        add_message(connection, str(case_id), str(task_id), role, 'human', 'note', FAILED_STEP_TR,
                    {'reason': 'ATTEMPTS_EXHAUSTED'})
    row = connection.execute(CLAIM_SQL, {'maximum': MAX_ATTEMPTS, 'gap': gap_seconds, 'owner': owner,
                                         'lease': LEASE_SECONDS}).fetchone()
    if not row:
        return None
    case = connection.execute("""UPDATE agents.cases SET status=CASE WHEN status='open' THEN 'investigating' ELSE status END,
            started_at=COALESCE(started_at,clock_timestamp())
        WHERE case_id=%s RETURNING analysis_scope_key,fund_code,detector_run_id,packet_sha256,status""", (row[1],)).fetchone()
    return Task(str(row[0]), str(row[1]), row[2], row[3], row[4], row[5], case[0], case[1], str(case[2]), case[3], case[4])


def owns(connection, task: Task, owner: str) -> bool:
    return connection.execute("SELECT 1 FROM agents.tasks WHERE task_id=%s AND status='running' AND lease_owner=%s FOR UPDATE",
                              (task.task_id, owner)).fetchone() is not None


def finish(connection, task: Task, owner: str, status: str, *, call_id: str | None = None,
           cost: Any = None, error_class: str | None = None, not_before: datetime | None = None) -> bool:
    row = connection.execute("""UPDATE agents.tasks SET status=%(status)s,
            finished_at=CASE WHEN %(status)s IN ('done','failed','skipped') THEN clock_timestamp() ELSE NULL END,
            lease_owner=NULL,lease_until=NULL,call_id=COALESCE(%(call)s,call_id),
            cost_usd=CASE WHEN %(cost)s::numeric IS NULL THEN cost_usd ELSE COALESCE(cost_usd,0)+%(cost)s::numeric END,
            error_class=%(error)s,not_before=COALESCE(%(not_before)s::timestamptz,not_before),
            attempts=CASE WHEN %(status)s='waiting_budget' OR %(error)s='TEAM_PAUSED'
                THEN GREATEST(attempts-1,0) ELSE attempts END
        WHERE task_id=%(task)s AND status='running' AND lease_owner=%(owner)s RETURNING task_id""",
        {'status': status, 'call': call_id, 'cost': cost, 'error': error_class, 'not_before': not_before,
         'task': task.task_id, 'owner': owner}).fetchone()
    return row is not None


def resume_skipped(connection) -> int:
    """Re-queue AI steps skipped while AI was off or unavailable, for cases still in progress.

    Each claim counts an attempt, so a persistent cause stops after the attempt limit.
    """
    rows = connection.execute("""UPDATE agents.tasks task SET status='queued',not_before=clock_timestamp(),
            finished_at=NULL,error_class=NULL
        FROM agents.cases item
        WHERE item.case_id=task.case_id AND item.status IN ('open','investigating') AND task.role<>'sentinel'
          AND task.status='skipped' AND task.error_class IN ('AI_OFF','AI_UNAVAILABLE') AND task.attempts<%s
        RETURNING task.task_id""", (MAX_ATTEMPTS,)).fetchall()
    return len(rows)


def extend_leases(connection, owners: list[str]) -> None:
    connection.execute("""UPDATE agents.tasks SET lease_until=now()+make_interval(secs=>%s)
        WHERE status='running' AND lease_owner=ANY(%s)""", (LEASE_SECONDS, owners))
