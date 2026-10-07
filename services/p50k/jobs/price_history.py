"""Download dated TEFAS unit-price history for a list of funds into JSON files.

One file per fund, written atomically: the fund code, when it was retrieved,
the TEFAS period bucket, and [date, price] rows with prices as exact decimal
strings, or null where TEFAS reports no price (it writes 0, before a fund
starts and after its price stops). The rows carry nothing else (category rank and size in
TEFAS's history rows repeat today's value, so they are dropped). From the repo
root:
    PYTHONPATH=services python -m p50k.jobs.price_history --codes THF TP2 --out DIR [--periyod 60]

Periods are TEFAS buckets: 12 is one year, 36 three years, 60 five years (the
maximum). A fund that TEFAS no longer knows is reported, not written.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Sequence

from p50k.providers.resilience import CircuitBreaker, CircuitBreakerError, retry_with_backoff
from p50k.providers.tefas import FundNotFound, TefasClient, TefasUnavailable

logger = logging.getLogger(__name__)

PERIOD_ONE_YEAR, PERIOD_THREE_YEARS, PERIOD_FIVE_YEARS = 12, 36, 60


@dataclass
class DownloadSummary:
    saved: dict[str, int] = field(default_factory=dict)  # fund -> number of rows
    not_found: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    stopped: str | None = None


def download(client: TefasClient, codes: Sequence[str], out_dir: Path, *,
             periyod: int = PERIOD_FIVE_YEARS, pause_seconds: float = 1.5,
             sleep: Callable[[float], None] = time.sleep,
             now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
             breaker: CircuitBreaker | None = None) -> DownloadSummary:
    summary = DownloadSummary()
    out_dir.mkdir(parents=True, exist_ok=True)
    breaker = breaker or CircuitBreaker(failure_threshold=5, recovery_timeout=600, failure_on=(TefasUnavailable,))

    @retry_with_backoff(retry_on=(TefasUnavailable,), max_retries=2, base_delay=5.0, max_delay=30.0, sleep=sleep)
    def fetch(code: str):
        try:
            return breaker.call(client.price_history, code, periyod)
        finally:
            sleep(pause_seconds)

    for code in codes:
        code = code.upper()
        try:
            points = fetch(code)
        except FundNotFound:
            summary.not_found.append(code)
            continue
        except CircuitBreakerError:
            summary.stopped = f"TEFAS kept failing; stopped before {code}"
            break
        except TefasUnavailable as exc:
            logger.warning("%s skipped: %s", code, exc)
            summary.failed.append(code)
            continue
        payload = {
            "fund": code,
            "source": "TEFAS fonFiyatBilgiGetir",
            "periyod": periyod,
            "retrieved_at": now().isoformat(),
            "rows": [[point.date.isoformat(), None if point.price is None else str(point.price)] for point in points],
        }
        _write_atomic(out_dir / f"{code}.json", json.dumps(payload, ensure_ascii=False))
        summary.saved[code] = len(points)
    return summary


def load(path: Path) -> list[tuple[str, str | None]]:
    """Read one saved file back as (date, price) pairs; the price is None where TEFAS had none."""
    return [(day, price) for day, price in json.loads(path.read_text(encoding="utf-8"))["rows"]]


def _write_atomic(path: Path, text: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--codes", nargs="+", required=True, help="fund codes")
    parser.add_argument("--out", type=Path, required=True, help="directory for one JSON file per fund")
    parser.add_argument("--periyod", type=int, default=PERIOD_FIVE_YEARS, choices=(12, 36, 60),
                        help="TEFAS period bucket: 12 one year, 36 three years, 60 five years")
    parser.add_argument("--pause", type=float, default=1.5, help="seconds between requests")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    summary = download(TefasClient(), args.codes, args.out, periyod=args.periyod, pause_seconds=args.pause)
    logger.info("saved %d funds, not found %d, failed %d%s", len(summary.saved), len(summary.not_found),
                len(summary.failed), f", stopped: {summary.stopped}" if summary.stopped else "")
    return 1 if summary.stopped or summary.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
