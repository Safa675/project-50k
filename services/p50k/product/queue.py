"""Leased PostgreSQL jobs with deduplication and ownership-bound completion."""
from __future__ import annotations
from psycopg.types.json import Jsonb
from p50k.product.db import connect
from p50k.product.settings import Settings
from p50k.product.analysis_context import selection,analysis_scope_key

def enqueue(settings: Settings, code: str, packet_sha256: str) -> str:
    from p50k.product.ai_client import AIConfig
    from p50k.product.decisions import PROMPT_VERSION,SCHEMA_VERSION
    config=AIConfig.from_env()
    key=':'.join(('ai_decide',code,packet_sha256,config.mode,config.model,config.effort,PROMPT_VERSION,SCHEMA_VERSION,analysis_scope_key(settings)))
    with connect(settings) as connection:
        connection.execute("INSERT INTO ops.jobs(job_type,idempotency_key,payload) VALUES ('ai_decide',%s,%s) ON CONFLICT DO NOTHING",(key,Jsonb({'fund_code':code,'analysis_date':selection(settings),'budget_bucket':'batch'})))
        return str(connection.execute('SELECT job_id FROM ops.jobs WHERE idempotency_key=%s',(key,)).fetchone()[0])

def claim(settings: Settings, owner: str):
    with connect(settings) as connection:
        connection.execute("UPDATE ops.jobs SET status='FAILED',lease_owner=NULL,error_class='AttemptsExhausted' WHERE status='RUNNING' AND lease_until<now() AND attempts>=max_attempts")
        return connection.execute("""WITH chosen AS (SELECT job_id FROM ops.jobs WHERE job_type IN ('ai_decide','analysis_replay') AND attempts<max_attempts
            AND ((status='READY' AND available_at<=now()) OR (status='RUNNING' AND lease_until<now()))
            ORDER BY priority,available_at FOR UPDATE SKIP LOCKED LIMIT 1)
            UPDATE ops.jobs job SET status='RUNNING',attempts=attempts+1,lease_owner=%s,
              lease_until=now()+interval '3 minutes',updated_at=clock_timestamp()
            FROM chosen WHERE job.job_id=chosen.job_id RETURNING job.job_id,job.payload,job.attempts,job.max_attempts,job.job_type""",(owner,)).fetchone()

def finish(settings: Settings, job: str, owner: str, error_class: str | None=None):
    with connect(settings) as connection:
        row=connection.execute("""UPDATE ops.jobs SET status=CASE WHEN %s::text IS NULL THEN 'SUCCEEDED'
            WHEN attempts>=max_attempts OR %s IN ('AI_OFF','KEY_UNAVAILABLE','MOCK_DATABASE_REJECTED') THEN 'FAILED' ELSE 'READY' END,
            available_at=now()+make_interval(secs=>power(2,attempts)::integer),lease_owner=NULL,lease_until=NULL,
            error_class=%s,updated_at=clock_timestamp() WHERE job_id=%s AND status='RUNNING' AND lease_owner=%s RETURNING job_id""",
            (error_class,error_class,error_class,job,owner)).fetchone()
        return bool(row)
