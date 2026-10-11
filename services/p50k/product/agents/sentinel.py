"""Nöbetçi: deterministic, LLM-free scans of the exact run of each active analysis view."""
from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any

from p50k.product.agents import store
from p50k.product.agents.vocabulary import REGULATORY_BONUS
from p50k.product.analysis_context import use_analysis_date, validate_date
from p50k.product.db import connect
from p50k.product.settings import Settings

SCAN_INTERVAL_SECONDS = 60
MAX_SCOPES_PER_TICK = 12
SCAN_LOCK = 50000038

NEW_RUN_CLOSE_TR = 'Yeni bir hesaplama geldiği için bu vaka kapatıldı; gerekirse güncel kanıtla yeni vaka açılır.'
NOT_TRIGGERED_CLOSE_TR = 'Yeni hesaplamada bu fon için inceleme sınırı aşılmadığından vaka kapatıldı.'


def base_priority(entry: dict[str, Any]) -> int:
    """Regulatory evidence first, then the number of triggered detectors."""
    return max(1, min(60, (REGULATORY_BONUS if entry['regulatory'] else 0) + len(entry['detectors'])))


def ordered_labels(entry: dict[str, Any]) -> list[str]:
    detectors = sorted(entry['detectors'], key=lambda item: (item != 'AN-FND-005', item))
    return list(dict.fromkeys(store.label(item) for item in detectors))


def case_title(entry: dict[str, Any]) -> str:
    return ('İnceleme sınırı aşıldı: ' + ', '.join(ordered_labels(entry)))[:240]


def opening_note(entry: dict[str, Any]) -> str:
    return ('Nöbetçi seçili tarihteki tamamlanmış hesaplamayı taradı ve bu fon için vaka açtı. '
            'İnceleme sınırı aşılan ölçümler: ' + ', '.join(ordered_labels(entry)) + '.')


def active_scopes(connection, settings: Settings) -> list[str]:
    """The configured default view plus views with user activity in the last hour."""
    scopes: list[str] = []
    default = store.default_scope(settings)
    if default:
        scopes.append(default)
    rows = connection.execute("""SELECT analysis_scope_key,max(created_at) seen FROM (
            SELECT analysis_scope_key,created_at FROM agents.requests WHERE created_at>now()-interval '1 hour'
            UNION ALL
            SELECT thread.analysis_scope_key,message.created_at FROM ai.chat_messages message
            JOIN ai.chat_threads thread USING(thread_id) WHERE message.created_at>now()-interval '1 hour'
        ) activity GROUP BY analysis_scope_key ORDER BY seen DESC LIMIT %s""", (MAX_SCOPES_PER_TICK,)).fetchall()
    for row in rows:
        scope = row[0]
        if scope in scopes or not store.SCOPE.fullmatch(scope):
            continue
        try:
            validate_date(store.scope_date(scope))
        except ValueError:
            continue
        scopes.append(scope)
    return scopes[:MAX_SCOPES_PER_TICK]


def is_due(connection, settings: Settings, scope: str) -> bool:
    last = connection.execute("""SELECT detector_run_id,finished_at FROM agents.sentinel_scans
        WHERE analysis_scope_key=%s ORDER BY finished_at DESC LIMIT 1""", (scope,)).fetchone()
    if not last:
        return True
    if (datetime.now(timezone.utc) - last[1]).total_seconds() >= SCAN_INTERVAL_SECONDS:
        return True
    with use_analysis_date(store.scope_date(scope)):
        run = store.scope_run(connection, settings)
    return (run.run_id if run else None) != (str(last[0]) if last[0] else None)


def scan(settings: Settings, scope: str) -> dict[str, Any]:
    """Open or refresh cases for TRIGGERED evidence in this view's exact run; no LLM."""
    started = datetime.now(timezone.utc)
    opened = refreshed = funds = 0
    run = None
    with use_analysis_date(store.scope_date(scope)), connect(settings) as connection:
        connection.execute("SET LOCAL statement_timeout='30s'")
        connection.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,%s))', (scope, SCAN_LOCK))
        run = store.scope_run(connection, settings)
        if run:
            funds = connection.execute('SELECT count(DISTINCT fund_code) FROM det.signals WHERE run_id=%s',
                                       (run.run_id,)).fetchone()[0]
            entries = store.triggered_funds(connection, run)
            triggered = {entry['fund_code']: entry for entry in entries}
            active = connection.execute("""SELECT item.case_id,item.fund_code,item.status,item.detector_run_id,item.opened_by,item.priority,
                    NOT EXISTS (SELECT 1 FROM agents.tasks task WHERE task.case_id=item.case_id
                        AND task.status IN ('queued','running','waiting_budget')) idle
                FROM agents.cases item WHERE item.analysis_scope_key=%s AND item.status<>'closed'""", (scope,)).fetchall()
            current: set[str] = set()
            for case_id, code, status, case_run, opened_by, priority, idle in active:
                case_id = str(case_id)
                if str(case_run) == run.run_id:
                    current.add(code)
                    if code in triggered and base_priority(triggered[code]) > priority:
                        store.raise_case(connection, case_id, base_priority(triggered[code]))
                        refreshed += 1
                    continue
                if status == 'open' and (code in triggered or opened_by == 'user'):
                    connection.execute('UPDATE agents.cases SET detector_run_id=%s WHERE case_id=%s', (run.run_id, case_id))
                    current.add(code)
                    refreshed += 1
                elif status == 'open' or idle:
                    store.close_case(connection, case_id, NEW_RUN_CLOSE_TR if code in triggered else NOT_TRIGGERED_CLOSE_TR)
                else:
                    current.add(code)
            for entry in sorted(entries, key=lambda item: (-base_priority(item), item['fund_code'])):
                if entry['fund_code'] in current:
                    continue
                created = store.open_case(connection, scope=scope, fund_code=entry['fund_code'], run=run,
                    opened_by='sentinel', priority=base_priority(entry), title=case_title(entry),
                    opening_note=opening_note(entry),
                    payload={'run_id': run.run_id, 'evidence_ids': entry['evidence_ids'],
                             'detectors': entry['detectors'], 'regulatory': entry['regulatory']})
                if created:
                    opened += 1
        connection.execute("""INSERT INTO agents.sentinel_scans
            (analysis_scope_key,detector_run_id,funds_scanned,cases_opened,cases_refreshed,started_at,finished_at)
            VALUES (%s,%s,%s,%s,%s,%s,clock_timestamp())""",
            (scope, run.run_id if run else None, funds, opened, refreshed, started))
    return {'scope': scope, 'run_id': run.run_id if run else None, 'funds_scanned': funds,
            'cases_opened': opened, 'cases_refreshed': refreshed}


def tick(settings: Settings) -> list[dict[str, Any]]:
    results = []
    with connect(settings) as connection:
        connection.execute("SET LOCAL statement_timeout='5s'")
        scopes = active_scopes(connection, settings)
        due = [scope for scope in scopes if is_due(connection, settings, scope)]
    for scope in due:
        try:
            results.append(scan(settings, scope))
        except Exception as error:
            logging.getLogger(__name__).warning('sentinel_scan_failed', extra={'error_class': type(error).__name__})
    return results
