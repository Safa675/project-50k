"""Deduplicated, bounded date calculations using the unchanged detector runtime.

A selected day is ready only when a complete run of the current detector version
is persisted for that exact Istanbul day; a finished job alone is not proof.
Job state is reported only while that run is absent. A failed calculation may be
requested again a bounded number of times. The detector runtime writes a run in
one transaction and reuses an identical completed run, so a retry can neither
duplicate nor alter stored results.
"""
from __future__ import annotations

from typing import Any

from psycopg import Connection
from psycopg.types.json import Jsonb

from p50k.product.analysis_context import current_cutoff, selection, use_analysis_date
from p50k.product.db import connect
from p50k.product.detector_pipeline import VERSION_ID

MAX_ACTIVE_JOBS = 3
MAX_RETRIES = 3


def job_key(selected: str) -> str:
    return 'analysis-replay:'+VERSION_ID+':'+selected


def scope_status(connection: Connection, settings, selected: str) -> str:
    """Status of one validated selection, read inside the caller's transaction."""
    if selected=='live':
        return 'ready'
    with use_analysis_date(selected):
        cutoff=current_cutoff(settings)
    # p50k_dev views also read synthetic runs; keep readiness consistent there.
    run=connection.execute('''SELECT 1 FROM det.detector_runs run JOIN det.run_inputs input USING(run_id)
        WHERE input.complete AND run.cutoff IS NOT NULL AND run.cutoff<=%s
          AND (run.cutoff AT TIME ZONE 'Europe/Istanbul')::date=%s::date
          AND ((run.origin='HISTORICAL_REPLAY' AND input.version_id=%s) OR (%s AND run.origin='SYNTHETIC'))
        LIMIT 1''',(cutoff,selected,VERSION_ID,settings.db_name=='p50k_dev')).fetchone()
    if run:
        return 'ready'
    job=connection.execute('''SELECT status,attempts>=max_attempts,COALESCE(lease_until<now(),false)
        FROM ops.jobs WHERE idempotency_key=%s AND job_type='analysis_replay' ''',(job_key(selected),)).fetchone()
    if job is None:
        return 'not_started'
    status,exhausted,expired=job
    if status=='READY':
        return 'queued'
    if status=='RUNNING':
        # An expired lease with attempts left waits to be claimed again.
        return ('failed' if exhausted else 'queued') if expired else 'running'
    # FAILED, or SUCCEEDED although this day's run is not persisted.
    return 'failed'


def analysis_status(settings, selected: str | None=None) -> str:
    selected=selected or selection(settings)
    if selected=='live':
        return 'ready'
    with connect(settings) as connection:
        connection.execute('SET TRANSACTION READ ONLY')
        connection.execute("SET LOCAL statement_timeout='3s'")
        return scope_status(connection,settings,selected)


def request_analysis(connection: Connection, settings, selected: str) -> str:
    """Queue, keep or retry one day's calculation inside the caller's transaction."""
    if selected=='live':
        return 'ready'
    connection.execute('SELECT pg_advisory_xact_lock(50000045)')
    state=scope_status(connection,settings,selected)
    if state not in {'not_started','failed'}:
        return state
    # The day's own job (a stale lease being retried) does not take a second slot.
    active=connection.execute("""SELECT count(*) FROM ops.jobs WHERE job_type='analysis_replay'
        AND status IN ('READY','RUNNING') AND idempotency_key<>%s""",(job_key(selected),)).fetchone()[0]
    if active>=MAX_ACTIVE_JOBS:
        raise ValueError('ANALYSIS_QUEUE_BUSY')
    if state=='not_started':
        connection.execute("INSERT INTO ops.jobs(job_type,idempotency_key,payload,priority) VALUES('analysis_replay',%s,%s,0) ON CONFLICT DO NOTHING",
                           (job_key(selected),Jsonb({'analysis_date':selected})))
    else:
        connection.execute('''UPDATE ops.jobs SET status='READY',attempts=0,available_at=clock_timestamp(),
                lease_owner=NULL,lease_until=NULL,error_class=NULL,updated_at=clock_timestamp(),
                payload=jsonb_set(payload,'{retries}',to_jsonb(COALESCE((payload->>'retries')::integer,0)+1))
            WHERE idempotency_key=%s AND job_type='analysis_replay'
              AND COALESCE((payload->>'retries')::integer,0)<%s
              AND (status IN ('FAILED','SUCCEEDED')
                   OR (status='RUNNING' AND lease_until<now() AND attempts>=max_attempts))''',
                           (job_key(selected),MAX_RETRIES))
    return scope_status(connection,settings,selected)


def enqueue_analysis(settings,selected: str) -> str:
    if selected=='live':
        return 'ready'
    with connect(settings) as connection:
        connection.execute("SET LOCAL statement_timeout='5s'")
        return request_analysis(connection,settings,selected)


def run_analysis(settings,selected: str) -> dict[str,Any]:
    if selected=='live':
        raise ValueError('ANALYSIS_DATE_REQUIRED')
    from p50k.product.detector_runner import run
    with use_analysis_date(selected),connect(settings) as connection:
        return run(connection,current_cutoff(settings),'HISTORICAL_REPLAY')
