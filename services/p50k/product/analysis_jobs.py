"""Deduplicated, bounded date calculations using the unchanged detector runtime."""
from __future__ import annotations
from psycopg.types.json import Jsonb
from p50k.product.analysis_context import selection,use_analysis_date,current_cutoff
from p50k.product.db import connect
from p50k.product.detector_pipeline import VERSION_ID


def job_key(selected: str) -> str:
    return 'analysis-replay:'+VERSION_ID+':'+selected


def analysis_status(settings, selected: str | None=None) -> str:
    selected=selected or selection(settings)
    if selected=='live':return 'ready'
    with connect(settings) as connection:
        connection.execute('SET TRANSACTION READ ONLY')
        connection.execute("SET LOCAL statement_timeout='3s'")
        row=connection.execute('''SELECT 1 FROM det.detector_runs run JOIN det.run_inputs input USING(run_id)
            WHERE run.origin='HISTORICAL_REPLAY' AND input.complete AND input.version_id=%s
              AND (run.cutoff AT TIME ZONE 'Europe/Istanbul')::date=%s LIMIT 1''',(VERSION_ID,selected)).fetchone()
        if row:return 'ready'
        job=connection.execute('SELECT status FROM ops.jobs WHERE idempotency_key=%s',(job_key(selected),)).fetchone()
        return {'READY':'queued','RUNNING':'running','FAILED':'failed','SUCCEEDED':'ready'}.get(job[0],'failed') if job else 'not_started'


def enqueue_analysis(settings,selected: str) -> str:
    state=analysis_status(settings,selected)
    if state in {'ready','running','queued'}:return state
    with connect(settings) as connection:
        connection.execute('SELECT pg_advisory_xact_lock(50000045)')
        count=connection.execute("SELECT count(*) FROM ops.jobs WHERE job_type='analysis_replay' AND status IN ('READY','RUNNING')").fetchone()[0]
        if count>=3:raise ValueError('ANALYSIS_QUEUE_BUSY')
        connection.execute("INSERT INTO ops.jobs(job_type,idempotency_key,payload,priority) VALUES('analysis_replay',%s,%s,0) ON CONFLICT DO NOTHING",
                           (job_key(selected),Jsonb({'analysis_date':selected})))
    return analysis_status(settings,selected)


def run_analysis(settings,selected: str) -> None:
    from p50k.product.detector_runner import run
    with use_analysis_date(selected),connect(settings) as connection:
        run(connection,current_cutoff(settings),'HISTORICAL_REPLAY')
