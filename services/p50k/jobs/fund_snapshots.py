"""Daily TEFAS fund snapshot collector.

TEFAS serves only today's fund size, units outstanding and investor count, so
their history has to be built by saving the snapshot every business day; a
missed day cannot be fetched later. For each fund a run fetches the snapshot
and the last week of dated prices, and dates the snapshot only when its price
equals the newest dated price (fund size and units agree with that price:
units x price = size). Otherwise the as-of date is stored as unknown.

Results go to SQLite: at most one dated row per fund and as-of date, with the
raw TEFAS rows kept as evidence. From the repo root:
    PYTHONPATH=services python -m p50k.jobs.fund_snapshots [--codes TTE AAL] [--tefas-only] [--limit N]

The default database is ~/.local/share/project-50k/fund_snapshots.sqlite3
(override with --db or P50K_DATA_DIR). It stays out of git because TEFAS data
rights have not been reviewed.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Callable, Sequence

from p50k.providers.resilience import CircuitBreaker, CircuitBreakerError, retry_with_backoff
from p50k.providers.tefas import FundNotFound, FundSnapshot, PricePoint, TefasClient, TefasUnavailable

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS fund_snapshots (
    fund TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    as_of TEXT,
    as_of_rule TEXT NOT NULL,
    price TEXT,
    total_value TEXT,
    units_outstanding TEXT,
    investors INTEGER,
    daily_return_pct TEXT,
    category TEXT,
    category_rank INTEGER,
    category_size INTEGER,
    market_share_pct TEXT,
    units_x_price_vs_total_rel_diff REAL,
    raw_snapshot TEXT NOT NULL,
    raw_prices TEXT NOT NULL,
    PRIMARY KEY (fund, retrieved_at)
);
CREATE UNIQUE INDEX IF NOT EXISTS fund_snapshots_one_per_day
    ON fund_snapshots (fund, as_of) WHERE as_of IS NOT NULL;
CREATE TABLE IF NOT EXISTS collector_runs (
    started_at TEXT PRIMARY KEY,
    finished_at TEXT NOT NULL,
    requested INTEGER NOT NULL,
    dated INTEGER NOT NULL,
    undated INTEGER NOT NULL,
    already_stored INTEGER NOT NULL,
    not_found TEXT NOT NULL,
    failed TEXT NOT NULL,
    stopped TEXT
);
"""

DATED_RULE = "price_equals_newest_dated_price"


@dataclass
class RunSummary:
    started_at: str
    requested: int
    dated: int = 0
    undated: int = 0
    already_stored: int = 0
    not_found: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    stopped: str | None = None


def default_db_path() -> Path:
    base = os.environ.get("P50K_DATA_DIR") or Path.home() / ".local" / "share" / "project-50k"
    return Path(base) / "fund_snapshots.sqlite3"


def connect(path: Path | str) -> sqlite3.Connection:
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.executescript(SCHEMA)
    return db


def date_snapshot(snapshot: FundSnapshot, prices: Sequence[PricePoint]) -> tuple[str | None, str]:
    """Return (as-of date or None, rule or reason)."""
    if snapshot.price is None:
        return None, "unknown:no_snapshot_price"
    if not prices:
        return None, "unknown:no_dated_prices"
    newest = prices[-1]
    if snapshot.price == newest.price:
        return newest.date.isoformat(), DATED_RULE
    # Usually a run that straddled the day's price publication.
    return None, "unknown:price_differs_from_newest_dated_price"


def store(db: sqlite3.Connection, snapshot: FundSnapshot, prices: Sequence[PricePoint],
          retrieved_at: str, as_of: str | None, rule: str) -> bool:
    """Insert one snapshot; returns False if a dated row for that fund and day already exists."""
    size_check = None
    if snapshot.units_outstanding is not None and snapshot.price is not None and snapshot.total_value:
        size_check = float(abs(snapshot.units_outstanding * snapshot.price - snapshot.total_value)
                           / snapshot.total_value)
    cursor = db.execute(
        "INSERT OR IGNORE INTO fund_snapshots VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (snapshot.code, retrieved_at, as_of, rule, _text(snapshot.price), _text(snapshot.total_value),
         _text(snapshot.units_outstanding), snapshot.investors, _text(snapshot.daily_return_pct),
         snapshot.category, snapshot.category_rank, snapshot.category_size, _text(snapshot.market_share_pct),
         size_check, json.dumps(snapshot.raw, default=str, ensure_ascii=False),
         json.dumps([[p.date.isoformat(), str(p.price)] for p in prices])),
    )
    return cursor.rowcount == 1


def run(client: TefasClient, db: sqlite3.Connection, codes: Sequence[str], *,
        pause_seconds: float = 1.5,
        sleep: Callable[[float], None] = time.sleep,
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        breaker: CircuitBreaker | None = None) -> RunSummary:
    summary = RunSummary(started_at=now().isoformat(), requested=len(codes))
    breaker = breaker or CircuitBreaker(failure_threshold=5, recovery_timeout=600, failure_on=(TefasUnavailable,))

    @retry_with_backoff(retry_on=(TefasUnavailable,), max_retries=2, base_delay=5.0, max_delay=30.0, sleep=sleep)
    def fetch(func, code):
        try:
            return breaker.call(func, code)
        finally:
            sleep(pause_seconds)

    for code in codes:
        try:
            snapshot = fetch(client.snapshot, code)
            prices = fetch(client.price_history, code)
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
        retrieved_at = now().isoformat()
        as_of, rule = date_snapshot(snapshot, prices)
        if store(db, snapshot, prices, retrieved_at, as_of, rule):
            if as_of:
                summary.dated += 1
            else:
                summary.undated += 1
        else:
            summary.already_stored += 1
        db.commit()

    db.execute("INSERT OR REPLACE INTO collector_runs VALUES (?,?,?,?,?,?,?,?,?)",
               (summary.started_at, now().isoformat(), summary.requested, summary.dated, summary.undated,
                summary.already_stored, json.dumps(summary.not_found), json.dumps(summary.failed), summary.stopped))
    db.commit()
    return summary


def fund_codes(client: TefasClient, *, tefas_only: bool) -> list[str]:
    rows = client.fund_list("YAT")
    return sorted({row["fonKodu"] for row in rows
                   if isinstance(row.get("fonKodu"), str) and (not tefas_only or row.get("tefasDurum") is True)})


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", type=Path, default=None,
                        help="SQLite file (default: ~/.local/share/project-50k/fund_snapshots.sqlite3)")
    parser.add_argument("--codes", nargs="*", help="fund codes; default: every investment fund TEFAS lists")
    parser.add_argument("--tefas-only", action="store_true", help="only funds traded on TEFAS")
    parser.add_argument("--limit", type=int, help="collect at most this many funds")
    parser.add_argument("--pause", type=float, default=1.5, help="seconds between requests")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    client = TefasClient()
    codes = [c.upper() for c in args.codes] if args.codes else fund_codes(client, tefas_only=args.tefas_only)
    codes = codes[: args.limit] if args.limit else codes
    db_path = args.db or default_db_path()
    logger.info("collecting %d funds into %s (about %d requests)", len(codes), db_path, 2 * len(codes))
    db = connect(db_path)
    try:
        summary = run(client, db, codes, pause_seconds=args.pause)
    finally:
        db.close()
    logger.info("dated %d, undated %d, already stored %d, not found %d, failed %d%s",
                summary.dated, summary.undated, summary.already_stored, len(summary.not_found),
                len(summary.failed), f", stopped: {summary.stopped}" if summary.stopped else "")
    return 1 if summary.stopped else 0


def _text(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


if __name__ == "__main__":
    raise SystemExit(main())
