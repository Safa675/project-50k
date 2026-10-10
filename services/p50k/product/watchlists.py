"""Owner-scoped saved funds and bounded notifications from existing evidence."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from psycopg.rows import dict_row

from p50k.product.db import connect
from p50k.product.queries import decimal_text
from p50k.product.settings import Settings

MAX_SAVED_FUNDS = 100


class WatchlistError(ValueError):
    def __init__(self, code: str, status: int = 400):
        self.code, self.status = code, status
        super().__init__(code)


def save_fund(settings: Settings, user_id: str, code: str) -> dict[str, Any]:
    with connect(settings) as connection:
        connection.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,50000039))", (user_id,))
        if not connection.execute("SELECT 1 FROM ref.funds WHERE fund_code=%s", (code,)).fetchone():
            raise WatchlistError("FUND_NOT_FOUND", 404)
        if connection.execute("SELECT 1 FROM auth.watchlist_funds WHERE user_id=%s AND fund_code=%s", (user_id, code)).fetchone():
            return {"fund_code": code, "saved": True}
        if connection.execute("SELECT count(*) FROM auth.watchlist_funds WHERE user_id=%s", (user_id,)).fetchone()[0] >= MAX_SAVED_FUNDS:
            raise WatchlistError("WATCHLIST_LIMIT_REACHED", 409)
        connection.execute("INSERT INTO auth.watchlist_funds(user_id,fund_code) VALUES(%s,%s)", (user_id, code))
    return {"fund_code": code, "saved": True}


def remove_fund(settings: Settings, user_id: str, code: str) -> dict[str, Any]:
    with connect(settings) as connection:
        connection.execute("DELETE FROM auth.watchlist_funds WHERE user_id=%s AND fund_code=%s", (user_id, code))
    return {"fund_code": code, "saved": False}


def _snapshot(connection: Any, settings: Settings, user_id: str, now: datetime) -> dict[str, Any]:
    """One transaction snapshot; only the latest eligible complete run is shown."""
    connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
    connection.execute("SET LOCAL statement_timeout='5s'")
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute("""SELECT run.run_id,run.created_at,inputs.as_of,run.cutoff
            FROM det.detector_runs run JOIN det.run_inputs inputs USING(run_id)
            WHERE run.origin=%s AND inputs.complete AND run.cutoff<=%s
                AND run.created_at<=%s
            ORDER BY run.cutoff DESC,run.created_at DESC,run.run_id DESC LIMIT 1""",
            ("SYNTHETIC" if settings.db_name == "p50k_dev" else "DELAYED", now, now))
        run = cursor.fetchone()
        cursor.execute("""SELECT saved.fund_code,fund.name,fund.category,saved.saved_at
            FROM auth.watchlist_funds saved JOIN ref.funds fund USING(fund_code)
            WHERE saved.user_id=%s ORDER BY saved.saved_at DESC,saved.fund_code LIMIT %s""", (user_id, MAX_SAVED_FUNDS))
        funds = cursor.fetchall()
        cursor.execute("SELECT enabled FROM auth.notification_preferences WHERE user_id=%s", (user_id,))
        preference = cursor.fetchone()
        enabled = preference["enabled"] if preference else True
        signals = []
        coverage = {}
        if run:
            cursor.execute("""SELECT s.fund_code,count(*) AS signal_count,
                    count(*) FILTER (WHERE s.state='ABSTAINED') AS abstained_count
                FROM det.signals s JOIN auth.watchlist_funds saved USING(fund_code)
                WHERE saved.user_id=%s AND s.run_id=%s GROUP BY s.fund_code""",
                (user_id, run["run_id"]))
            coverage = {row["fund_code"]: row for row in cursor.fetchall()}
            cursor.execute("""SELECT s.fund_code,f.name,s.detector_id,s.reason,s.value,s.threshold,
                    s.evidence_id,s.as_of,e.effective_date,e.available_at,e.source_references,
                    e.unit,read.read_at
                FROM auth.watchlist_funds saved
                JOIN det.signals s USING(fund_code)
                JOIN ref.funds f USING(fund_code)
                JOIN det.evidence_items e ON e.evidence_id=s.evidence_id
                LEFT JOIN auth.notification_reads read ON read.evidence_id=s.evidence_id AND read.user_id=%s
                WHERE saved.user_id=%s AND s.run_id=%s AND s.state='TRIGGERED'
                    AND e.available_at IS NOT NULL AND e.available_at<=%s
                    AND e.effective_date<=%s AND s.as_of<=%s
                    AND NOT COALESCE((e.metadata->>'is_attribute')::boolean,false)
                ORDER BY e.available_at DESC,s.fund_code,s.detector_id LIMIT 800""",
                (user_id, user_id, run["run_id"], now, now.astimezone(ZoneInfo("Europe/Istanbul")).date(), now.astimezone(ZoneInfo("Europe/Istanbul")).date()))
            signals = cursor.fetchall()
        for signal in signals:
            signal["value"] = decimal_text(signal["value"])
            signal["threshold"] = decimal_text(signal["threshold"])
            signal["source_references"] = [
                {key: item.get(key) for key in ("source_id", "source_sha256", "available_at")}
                for item in signal["source_references"] if isinstance(item, dict)]
        for fund in funds:
            fund["triggered_count"] = sum(signal["fund_code"] == fund["fund_code"] for signal in signals)
            fund["signal_count"] = coverage.get(fund["fund_code"], {}).get("signal_count", 0)
            fund["abstained_count"] = coverage.get(fund["fund_code"], {}).get("abstained_count", 0)
        return {"items": funds, "total": len(funds), "signals": signals,
                "as_of": run["as_of"] if run else None,
                "run_id": str(run["run_id"]) if run else None,
                "run_created_at": run["created_at"] if run else None,
                "cutoff": run["cutoff"] if run else None,
                "notifications_enabled": enabled, "development_result": True,
                "data_mode": "SYNTHETIC" if settings.db_name == "p50k_dev" else "DELAYED"}


def watchlist(settings: Settings, user_id: str, now: datetime | None = None) -> dict[str, Any]:
    with connect(settings) as connection:
        return _snapshot(connection, settings, user_id, now or datetime.now(timezone.utc))


def notifications(settings: Settings, user_id: str, *, unread_only: bool = False,
                  limit: int = 100, offset: int = 0, now: datetime | None = None) -> dict[str, Any]:
    snapshot = watchlist(settings, user_id, now)
    items = snapshot.pop("signals") if snapshot["notifications_enabled"] else []
    unread = sum(item["read_at"] is None for item in items)
    if unread_only:
        items = [item for item in items if item["read_at"] is None]
    return {"items": items[offset:offset + limit], "total": len(items), "unread": unread,
            "limit": limit, "offset": offset,
            **{key: snapshot[key] for key in ("as_of", "run_id", "run_created_at", "notifications_enabled", "development_result", "data_mode")}}


def mark_read(settings: Settings, user_id: str, evidence_ids: list[str]) -> dict[str, int]:
    snapshot = watchlist(settings, user_id)
    visible = {item["evidence_id"] for item in snapshot["signals"]}
    requested = set(evidence_ids)
    if not requested.issubset(visible):
        raise WatchlistError("NOTIFICATION_NOT_FOUND", 404)
    with connect(settings) as connection:
        count = 0
        for evidence_id in sorted(requested):
            count += connection.execute("""INSERT INTO auth.notification_reads(user_id,evidence_id)
                VALUES(%s,%s) ON CONFLICT DO NOTHING""", (user_id, evidence_id)).rowcount
    return {"marked_read": count}


def set_notifications(settings: Settings, user_id: str, enabled: bool) -> dict[str, bool]:
    with connect(settings) as connection:
        connection.execute("""INSERT INTO auth.notification_preferences(user_id,enabled) VALUES(%s,%s)
            ON CONFLICT(user_id) DO UPDATE SET enabled=EXCLUDED.enabled,updated_at=clock_timestamp()""", (user_id, enabled))
    return {"notifications_enabled": enabled}
