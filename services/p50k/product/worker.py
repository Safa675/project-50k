"""Phase-one database heartbeat; queue processing is enabled with the AI phase."""

from __future__ import annotations

from pathlib import Path
import logging
import signal
import threading
import time

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
            heartbeat.write_text(str(time.time()), encoding="ascii")
            logger.info("worker_database_heartbeat")
        except Exception as error:
            logger.warning("worker_database_unavailable", extra={"error_class": type(error).__name__})
        stopped.wait(10)


if __name__ == "__main__":
    main()
