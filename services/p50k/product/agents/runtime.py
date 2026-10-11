"""Claim, execute and complete agent tasks; worker threads for the always-on team."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import logging
import threading
import time
from typing import Any
from uuid import uuid4

from psycopg.types.json import Jsonb

from p50k.product.agents import checks, control, llm, roles, sentinel, store
from p50k.product.agents.config import AgentConfig
from p50k.product.agents.vocabulary import FAILED_STEP_TR, SKIP_NOTES
from p50k.product.ai_client import AIUnavailable
from p50k.product.analysis_context import use_analysis_date
from p50k.product.chat_tools import load_context
from p50k.product.db import connect
from p50k.product.decisions import build_packet
from p50k.product.settings import Settings

logger = logging.getLogger(__name__)
RETRY_DELAY = timedelta(seconds=60)
CONNECTION_RETRY_DELAY = timedelta(minutes=5)
SCAN_CHECK_SECONDS = 5
RESUME_SECONDS = 60
VERIFIER_AI_OFF_TR = 'Testler kodla çalıştırıldı. Yapay zekâ kapalı olduğu için açıklamalar değerlendirilmedi.'
VERIFIER_NOTHING_TR = 'Testler kodla çalıştırıldı. Değerlendirilecek bir açıklama olmadığı için yapay zekâ adımı çalıştırılmadı.'


def case_messages(connection, case_id: str, kind: str) -> list[dict[str, Any]]:
    return [row[0] for row in connection.execute(
        'SELECT payload FROM agents.messages WHERE case_id=%s AND kind=%s ORDER BY message_id', (case_id, kind)).fetchall()]


def load_case(settings: Settings, task: store.Task) -> roles.CaseContext:
    """Rebuild the case's evidence in its own analysis view; reject a changed packet."""
    try:
        chat = load_context(settings, task.fund_code)
    except AIUnavailable:
        raise roles.Skip('EVIDENCE_UNAVAILABLE') from None
    if chat.run_id != task.detector_run_id or (task.packet_sha256 and task.packet_sha256 != chat.checksum):
        raise roles.Skip('EVIDENCE_CHANGED')
    with connect(settings) as connection:
        connection.execute("SET LOCAL statement_timeout='5s'")
        connection.execute('UPDATE agents.cases SET packet_sha256=%s WHERE case_id=%s AND packet_sha256 IS NULL',
                           (chat.checksum, task.case_id))
        row = connection.execute("""SELECT input.as_of,run.origin,run.cutoff,fund.category
            FROM det.detector_runs run JOIN det.run_inputs input USING(run_id)
            JOIN ref.funds fund ON fund.fund_code=%s WHERE run.run_id=%s""", (task.fund_code, chat.run_id)).fetchone()
    run = store.Run(chat.run_id, row[0], row[1], row[2])
    return roles.CaseContext(task.case_id, task.fund_code, row[3], chat, run, task.scope != 'live')


def verifier_tests(settings: Settings, task: store.Task, owner: str, case: roles.CaseContext) -> list[tuple[str, dict]]:
    """Run the skeptic's requested tests first, then every other standard test, once per task.

    The tests are deterministic and cost nothing, so a test the skeptic did not pick still
    informs the ratings; results are stored before any model call.
    """
    with connect(settings) as connection:
        connection.execute("SET LOCAL statement_timeout='20s'")
        stored = connection.execute("""SELECT payload FROM agents.messages WHERE task_id=%s AND kind='test_result'
            ORDER BY message_id""", (task.task_id,)).fetchall()
        if stored:
            return [(row[0]['ref'], row[0]['result']) for row in stored]
        plans = case_messages(connection, task.case_id, 'test_plan')
        requested = [test for test in (plans[-1].get('tests', []) if plans else []) if test in checks.TESTS]
        context = checks.CheckContext(case.fund_code, case.category, case.run, tuple(case.chat.packet.evidence))
        results = [(f't{index + 1}', checks.run_check(connection, test, context))
                   for index, test in enumerate(dict.fromkeys([*requested, *checks.DEFAULT_TESTS]))]
        if not store.owns(connection, task, owner):
            raise roles.Skip('LEASE_LOST')
        for reference, item in results:
            store.add_message(connection, task.case_id, task.task_id, 'verifier', 'team', 'test_result',
                              checks.describe(item), {'ref': reference, 'test': item['test'],
                              'name_tr': checks.TESTS[item['test']][0], 'outcome': item['outcome'],
                              'requested': item['test'] in requested, 'result': item})
    return results


def team_output(settings: Settings, case_id: str) -> tuple[list[dict], list[dict], list[tuple[str, dict]], list[dict]]:
    with connect(settings) as connection:
        connection.execute('SET TRANSACTION READ ONLY')
        hypotheses = case_messages(connection, case_id, 'hypothesis')
        counters = case_messages(connection, case_id, 'counter')
        tests = [(item['ref'], item['result']) for item in case_messages(connection, case_id, 'test_result')]
        ratings = case_messages(connection, case_id, 'verification')
    return hypotheses, counters, tests, ratings


def file_invalid_decision(connection, case: roles.CaseContext, packet_id: int, digest: str, config: AgentConfig,
                          calls: list[str]) -> None:
    """A failed team proposal stays visible to reviewers, unless any proposal already exists."""
    if connection.execute('SELECT 1 FROM ai.decisions WHERE packet_id=%s LIMIT 1', (packet_id,)).fetchone():
        return
    model = llm.role_model(config, 'reporter')
    connection.execute("""INSERT INTO ai.decisions
        (packet_id,fund_code,packet_sha256,decision_value,validation_state,evidence_ids,rationale,output,model_id,
         prompt_version,schema_version,ai_mode,effort,method,call_id)
        VALUES (%s,%s,%s,NULL,'INVALID','[]',NULL,NULL,%s,%s,%s,%s,%s,'TEAM',%s)""",
        (packet_id, case.fund_code, digest, model.model if config.mode == 'live' else 'synthetic',
         roles.PROMPT_VERSIONS['reporter'], roles.SCHEMA_VERSIONS['reporter'], config.mode, model.effort,
         calls[-1] if calls else 'failed:' + uuid4().hex))


def complete(settings: Settings, config: AgentConfig, task: store.Task, owner: str, status: str, *,
             outcome: roles.Outcome | None = None, notes: list[tuple[str, str, dict]] | None = None,
             error_class: str | None = None, not_before: datetime | None = None,
             calls: list[str] | None = None, cost: Decimal | None = None,
             case: roles.CaseContext | None = None, filing: tuple | None = None) -> bool:
    """Messages, the filed decision and the task result commit together, only under our lease."""
    with connect(settings) as connection:
        connection.execute("SET LOCAL statement_timeout='10s'")
        if not store.owns(connection, task, owner):
            return False
        # owns() holds the task row lock. A concurrent user promotion is either
        # visible here or happens after finish(), which resets its budget wait.
        if config.demo and status == 'waiting_budget' and error_class == 'DAILY_BUDGET' and task.source != 'user':
            source = connection.execute('SELECT source FROM agents.tasks WHERE task_id=%s', (task.task_id,)).fetchone()
            if source and source[0] == 'user':
                not_before = datetime.now(timezone.utc)
        if outcome:
            for message in outcome.messages:
                store.add_message(connection, task.case_id, task.task_id, task.role, message['to_role'], message['kind'],
                                  message['body'], message['payload'], outcome.model_id, outcome.prompt_version)
            calls, cost = outcome.calls, outcome.cost
        for to_role, body, payload in notes or []:
            store.add_message(connection, task.case_id, task.task_id, task.role, to_role, 'note', body, payload)
        if filing and case:
            packet_id, digest, report = filing
            if report is None:
                file_invalid_decision(connection, case, packet_id, digest, config, calls or [])
            else:
                decision = report.decision
                model = llm.role_model(config, 'reporter')
                decision_id = connection.execute("""INSERT INTO ai.decisions
                    (packet_id,fund_code,packet_sha256,decision_value,validation_state,evidence_ids,rationale,output,model_id,
                     prompt_version,schema_version,ai_mode,effort,method,call_id)
                    VALUES (%s,%s,%s,%s,'VALID',%s,%s,%s,%s,%s,%s,%s,%s,'TEAM',%s) RETURNING decision_id""",
                    (packet_id, case.fund_code, digest, decision['decision'], Jsonb(decision['cited_evidence_ids']),
                     decision['rationale_tr'], Jsonb(decision), report.model_id, report.prompt_version,
                     roles.SCHEMA_VERSIONS['reporter'], config.mode, model.effort, report.calls[-1])).fetchone()[0]
                connection.execute("UPDATE agents.cases SET status='reported',decision_id=%s WHERE case_id=%s",
                                   (decision_id, task.case_id))
        return store.finish(connection, task, owner, status, call_id=(calls or [None])[-1],
                            cost=cost, error_class=error_class, not_before=not_before)


def retry_later(settings: Settings, config: AgentConfig, task: store.Task, owner: str,
                failure: roles.Failed) -> bool:
    """A model call that failed twice (network loss, a sleeping machine) waits and retries.

    Only a call failure retries, and only below the attempt limit; invalid output fails at once.
    """
    if failure.code not in {'MODEL_CALL_FAILED','MODEL_CONNECTION_FAILED'} or task.attempts >= store.MAX_ATTEMPTS:
        return False
    delay = CONNECTION_RETRY_DELAY * (2 ** max(0,task.attempts-1)) if failure.code=='MODEL_CONNECTION_FAILED' else RETRY_DELAY
    complete(settings, config, task, owner, 'queued', error_class=failure.code, calls=failure.calls,
             cost=failure.cost, not_before=datetime.now(timezone.utc) + delay)
    return True


def execute(settings: Settings, config: AgentConfig, task: store.Task, owner: str) -> str:
    """Run one claimed task inside its case's analysis view. Returns the final task status."""
    with use_analysis_date(store.scope_date(task.scope)), llm.task_budget(task.source == 'user'):
        try:
            case = load_case(settings, task)
            if task.role == 'hypothesizer':
                outcome = roles.hypothesizer(settings, config, case)
            elif task.role == 'skeptic':
                outcome = roles.skeptic(settings, config, case)
            elif task.role == 'verifier':
                # The deterministic tests always run first and cost nothing; only the rating needs AI.
                tests = verifier_tests(settings, task, owner, case)
                hypotheses, counters, _, _ = team_output(settings, task.case_id)
                if config.mode == 'off':
                    complete(settings, config, task, owner, 'skipped', error_class='AI_OFF',
                             notes=[('team', VERIFIER_AI_OFF_TR, {'reason': 'AI_OFF'})])
                    return 'skipped'
                if not hypotheses and not counters:
                    complete(settings, config, task, owner, 'done', notes=[('team', VERIFIER_NOTHING_TR, {})])
                    return 'done'
                try:
                    outcome = roles.verifier_ratings(settings, config, case, hypotheses, counters, tests)
                except roles.Skip as skip:
                    if skip.code not in {'AI_OFF', 'AI_UNAVAILABLE'}:
                        raise
                    complete(settings, config, task, owner, 'skipped', error_class=skip.code,
                             notes=[('team', VERIFIER_AI_OFF_TR, {'reason': skip.code})])
                    return 'skipped'
            elif task.role == 'reporter':
                if config.mode == 'off':
                    raise roles.Skip('AI_OFF')
                hypotheses, counters, tests, ratings = team_output(settings, task.case_id)
                packet, packet_id, digest = build_packet(settings, task.fund_code)
                if digest != case.chat.checksum:
                    raise roles.Skip('EVIDENCE_CHANGED')
                try:
                    outcome = roles.reporter(settings, config, case, hypotheses, counters, tests, ratings)
                except roles.Failed as failure:
                    if retry_later(settings, config, task, owner, failure):
                        return 'queued'
                    complete(settings, config, task, owner, 'failed', error_class=failure.code, calls=failure.calls,
                             cost=failure.cost, notes=[('human', FAILED_STEP_TR, {'reason': failure.code})],
                             case=case, filing=(packet_id, digest, None))
                    return 'failed'
                complete(settings, config, task, owner, 'done', outcome=outcome, case=case,
                         filing=(packet_id, digest, outcome))
                return 'done'
            else:
                raise roles.Skip('ROLE_NOT_RUNNABLE')
        except control.TeamPaused as paused:
            complete(settings, config, task, owner, 'queued', error_class='TEAM_PAUSED',
                     calls=paused.calls, cost=paused.cost)
            return 'queued'
        except roles.Skip as skip:
            note = SKIP_NOTES.get(skip.code)
            complete(settings, config, task, owner, 'skipped', error_class=skip.code,
                     notes=[('team', note, {'reason': skip.code})] if note else [])
            return 'skipped'
        except roles.Failed as failure:
            if retry_later(settings, config, task, owner, failure):
                return 'queued'
            complete(settings, config, task, owner, 'failed', error_class=failure.code, calls=failure.calls,
                     cost=failure.cost, notes=[('human', FAILED_STEP_TR, {'reason': failure.code})])
            return 'failed'
        except llm.BudgetWait as wait:
            complete(settings, config, task, owner, 'waiting_budget', error_class=wait.reason, not_before=wait.until,
                     calls=wait.calls, cost=wait.cost)
            return 'waiting_budget'
        complete(settings, config, task, owner, 'done', outcome=outcome)
        return 'done'


def run_one(settings: Settings, config: AgentConfig, owner: str) -> str | None:
    with connect(settings) as connection:
        task = store.claim(connection, owner, config.case_gap_seconds)
    if not task:
        return None
    try:
        return execute(settings, config, task, owner)
    except Exception as error:
        logger.warning('agent_task_error', extra={'error_class': type(error).__name__, 'role': task.role})
        with connect(settings) as connection:
            if task.attempts < store.MAX_ATTEMPTS:
                store.finish(connection, task, owner, 'queued', error_class=type(error).__name__,
                             not_before=datetime.now(timezone.utc) + RETRY_DELAY)
                return 'queued'
            if store.finish(connection, task, owner, 'failed', error_class=type(error).__name__):
                store.add_message(connection, task.case_id, task.task_id, task.role, 'human', 'note', FAILED_STEP_TR,
                                  {'reason': type(error).__name__})
        return 'failed'


def loop(settings: Settings, owner: str, stopped: threading.Event, *, scan: bool) -> None:
    """One always-on agent thread; errors keep their class only and back off."""
    scanned = resumed = 0.0
    while not stopped.is_set():
        try:
            config = AgentConfig.from_env()
            if scan and time.monotonic() - scanned >= SCAN_CHECK_SECONDS:
                scanned = time.monotonic()
                sentinel.tick(settings, config)
                if config.mode != 'off' and time.monotonic() - resumed >= RESUME_SECONDS:
                    resumed = time.monotonic()
                    with connect(settings) as connection:
                        if control.allows_new_work(connection):
                            store.resume_skipped(connection)
            worked = run_one(settings, config, owner) is not None
        except Exception as error:
            logger.warning('agent_loop_unavailable', extra={'error_class': type(error).__name__})
            stopped.wait(30)
            continue
        stopped.wait(0.2 if worked else 3)


def start(settings: Settings, owner: str, stopped: threading.Event, workers: int = 2) -> list[str]:
    owners = [f'{owner}:agents:{index}' for index in range(workers)]
    for index, name in enumerate(owners):
        threading.Thread(target=loop, args=(settings, name, stopped), kwargs={'scan': index == 0},
                         daemon=True, name=f'agents-{index}').start()
    return owners
