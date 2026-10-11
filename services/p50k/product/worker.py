"""Phase-one database heartbeat; queue processing is enabled with the AI phase."""

from __future__ import annotations

from pathlib import Path
import logging
import os
import signal
import threading
import time
from uuid import uuid4

from p50k.product.logging import configure_logging
from p50k.product.settings import Settings


def main() -> None:
    configure_logging()
    settings = Settings.from_env()
    stopped = threading.Event()
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, lambda *_: stopped.set())
    logger = logging.getLogger(__name__)
    heartbeat = Path("/tmp/p50k-worker-heartbeat")
    owner='worker:'+uuid4().hex
    agent_owners: list[str] = []
    def keep_alive() -> None:
        while not stopped.is_set():
            try:
                from p50k.product.db import connect
                with connect(settings) as connection:
                    connection.execute("SELECT 1")
                    connection.execute("UPDATE ops.jobs SET lease_until=now()+interval '3 minutes' WHERE status='RUNNING' AND lease_owner=%s",(owner,))
                heartbeat.write_text(str(time.time()), encoding="ascii")
            except Exception as error:
                logger.warning("worker_heartbeat_unavailable",extra={"error_class":type(error).__name__})
            if agent_owners:
                # Agent leases are renewed separately so a missing agent schema never stops the heartbeat.
                try:
                    from p50k.product.agents.store import extend_leases
                    from p50k.product.db import connect
                    with connect(settings) as connection:
                        extend_leases(connection, agent_owners)
                except Exception as error:
                    logger.warning("agent_lease_unavailable",extra={"error_class":type(error).__name__})
            stopped.wait(10)
    threading.Thread(target=keep_alive,daemon=True).start()
    if os.environ.get("P50K_AGENTS_ENABLED", "true").lower() in {"true", "1"}:
        # DEC-035: the always-on agent team runs beside the existing jobs in this worker.
        from p50k.product.agents.runtime import start as start_agents
        try:
            workers = min(4, max(1, int(os.environ.get("P50K_AGENT_WORKERS", "2"))))
        except ValueError:
            workers = 2
        agent_owners.extend(start_agents(settings, owner, stopped, workers))
    while not stopped.is_set():
        try:
            import psycopg
            with psycopg.connect(**settings.connect_kwargs()) as connection:
                connection.execute(
                    "INSERT INTO ops.worker_heartbeats (worker_id, last_seen_at, status, details) "
                    "VALUES ('product-worker', now(), 'IDLE', '{\"ai_mode\":\"off\"}'::jsonb) "
                    "ON CONFLICT (worker_id) DO UPDATE SET "
                    "last_seen_at=EXCLUDED.last_seen_at, status=EXCLUDED.status, details=EXCLUDED.details"
                )
            from p50k.product.ai_worker import step
            step(settings,owner)
            logger.info("worker_database_heartbeat")
        except Exception as error:
            logger.warning("worker_database_unavailable", extra={"error_class": type(error).__name__})
        stopped.wait(10)


if __name__ == "__main__":
    main()
