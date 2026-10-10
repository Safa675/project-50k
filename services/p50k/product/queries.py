"""Bounded, parameterized, read-only SQL for the fund API.

The catalog is explicitly current metadata. Observation queries independently
enforce publication availability; an undated observation is never usable.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from urllib.parse import urlsplit

from psycopg import Connection
from psycopg.rows import dict_row

from p50k.product.models import (
    Coverage, DailyChart, EventsPage, Fund, FundsPage, PricePoint,
    RegulatoryEvent, Signal, SignalsPage, SourceReference,
)


def decimal_text(value: Decimal | str | int | None) -> str | None:
    if value is None:
        return None
    result = Decimal(value)
    if not result.is_finite():
        raise ValueError("Non-finite evidence")
    return format(result, "f")


def evidence_values(value: Any) -> Any:
    """Never emit a binary float as a detector figure in a public contract."""
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, (int, Decimal)):
        return decimal_text(value)
    if isinstance(value, float):
        return decimal_text(Decimal(str(value)))
    if isinstance(value, list):
        return [evidence_values(item) for item in value]
    if isinstance(value, dict) and all(isinstance(key, str) for key in value):
        return {key: evidence_values(item) for key, item in value.items()}
    raise ValueError("Unsupported evidence value")


def coverage_for(signals: list[Signal]) -> Coverage:
    detectors = [item for item in signals if not item.is_attribute]
    triggered = sum(item.state == "TRIGGERED" for item in detectors)
    covering = sum(item.state == "NOT_TRIGGERED" for item in detectors)
    abstained = sum(item.state == "ABSTAINED" for item in detectors)
    state = "TRIGGERED" if triggered else "NOT_TRIGGERED" if covering else "ABSTAINED"
    return Coverage(
        triggered=triggered, not_triggered=covering, abstained=abstained,
        state=state,
        reason="TRIGGER_PRESENT" if triggered else "COVERING_DETECTORS" if covering else "INSUFFICIENT_COVERAGE",
        evidence_ids=[item.evidence_id for item in signals],
    )


def source_url(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return None
    # Only the official public event source is a clickable link, never a path.
    if parsed.scheme != "https" or parsed.hostname not in {"spk.gov.tr", "www.spk.gov.tr"}:
        return None
    if parsed.username or parsed.password or port not in {None, 443}:
        return None
    return value


def source_reference(value: dict[str, Any]) -> SourceReference:
    payload = dict(value)
    if isinstance(payload.get("effective_date"), str):
        payload["effective_date"] = date.fromisoformat(payload["effective_date"])
    if isinstance(payload.get("available_at"), str):
        payload["available_at"] = datetime.fromisoformat(payload["available_at"].replace("Z", "+00:00"))
    payload["source_url"] = source_url(payload.get("source_url"))
    return SourceReference(**payload)


FUND_COLUMNS = "fund_code, name, category, tefas_status, listing_as_of"
PRICE_SQL = """
    SELECT DISTINCT ON (effective_date)
        effective_date, nav, published_at, available_at, source_id,
        source_sha256, unit, availability_rule, origin
    FROM obs.fund_prices
    WHERE fund_code = %s AND effective_date BETWEEN %s AND %s
        AND available_at IS NOT NULL AND available_at <= %s
        AND (published_at IS NULL OR published_at <= %s)
    ORDER BY effective_date, available_at DESC, observed_at DESC NULLS LAST,
        source_sha256 DESC
"""
SIGNALS_CTE = """
    WITH latest_run AS (
        SELECT run.run_id, inputs.version_id FROM det.detector_runs run
        JOIN det.run_inputs inputs ON inputs.run_id = run.run_id
        WHERE run.origin = 'DELAYED' AND run.cutoff IS NOT NULL AND run.cutoff <= %s
            AND inputs.complete
        ORDER BY run.cutoff DESC, run.created_at DESC, run.run_id DESC LIMIT 1
    ), selected AS (
        SELECT signal.fund_code, signal.detector_id, latest_run.version_id,
            signal.run_id, signal.state, signal.reason, signal.value,
            signal.threshold, signal.evidence_id, signal.as_of,
            item.origin, item.values, item.thresholds, item.unit, item.available_at, item.source_references,
            COALESCE((item.metadata->>'is_attribute')::boolean, false) AS is_attribute
        FROM det.signals signal
        JOIN latest_run ON latest_run.run_id = signal.run_id
        JOIN det.evidence_items item ON item.evidence_id = signal.evidence_id
        WHERE signal.as_of <= %s
            AND (item.available_at <= %s OR (item.available_at IS NULL AND signal.state = 'ABSTAINED'))
            AND (%s::text IS NULL OR signal.fund_code = %s)
            AND (%s::text IS NULL OR signal.state = %s)
    )
"""
EVENTS_CTE = """
    WITH selected AS (
        SELECT DISTINCT ON (event_id)
            event_id, fund_code, event_type, effective_date, status,
            quotation, source_id, source_sha256, metadata,
            published_at, available_at, confirmed_at, availability_rule, origin
        FROM obs.regulatory_events
        WHERE available_at IS NOT NULL AND available_at <= %s
            AND (published_at IS NULL OR published_at <= %s)
            AND (effective_date IS NULL OR effective_date <= %s)
            AND (status = 'CANDIDATE' OR confirmed_at <= %s)
            AND (%s::text IS NULL OR fund_code = %s)
        ORDER BY event_id, (status = 'CONFIRMED') DESC,
            available_at DESC, source_sha256 DESC
    )
"""


class FundQueries:
    def __init__(self, connection: Connection):
        self.connection = connection

    def _rows(self, statement: str, parameters: tuple[Any, ...]) -> list[dict[str, Any]]:
        with self.connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(statement, parameters)
            return cursor.fetchall()

    def _count(self, statement: str, parameters: tuple[Any, ...]) -> int:
        row, = self._rows(statement, parameters)
        return int(row["total"])

    def funds(self, query: str, limit: int, offset: int) -> FundsPage:
        # Escape LIKE metacharacters so every character is a literal search.
        term = "%" + query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        where = " WHERE fund_code ILIKE %s OR name ILIKE %s"
        parameters = (term, term)
        total = self._count("SELECT count(*) AS total FROM ref.funds" + where, parameters)
        rows = self._rows("SELECT " + FUND_COLUMNS + " FROM ref.funds" + where
                          + " ORDER BY fund_code LIMIT %s OFFSET %s", parameters + (limit, offset))
        return FundsPage(items=[Fund(**row) for row in rows], total=total, limit=limit, offset=offset)

    def fund(self, code: str) -> Fund | None:
        rows = self._rows("SELECT " + FUND_COLUMNS + " FROM ref.funds WHERE fund_code = %s", (code,))
        return Fund(**rows[0]) if rows else None

    def chart(self, code: str, start: date, end: date, cutoff: datetime) -> DailyChart:
        rows = self._rows(PRICE_SQL, (code, start, end, cutoff, cutoff))
        points = [PricePoint(**{**row, "nav": decimal_text(row["nav"])}) for row in rows]
        return DailyChart(fund_code=code, start_date=start, end_date=end, cutoff=cutoff, points=points)

    def signals(self, code: str | None, state: str | None, as_of: date,
                cutoff: datetime, limit: int, offset: int) -> SignalsPage:
        parameters = (cutoff, as_of, cutoff, code, code, state, state)
        total = self._count(SIGNALS_CTE + "SELECT count(*) AS total FROM selected", parameters)
        rows = self._rows(SIGNALS_CTE + "SELECT * FROM selected ORDER BY fund_code, detector_id LIMIT %s OFFSET %s",
                          parameters + (limit, offset))
        items = []
        for row in rows:
            payload = dict(row)
            payload["run_id"] = str(payload["run_id"])
            payload["value"] = decimal_text(payload["value"])
            payload["threshold"] = decimal_text(payload["threshold"])
            payload["values"] = evidence_values(payload["values"])
            payload["thresholds"] = evidence_values(payload["thresholds"])
            payload["source_references"] = [source_reference(item) for item in payload["source_references"]]
            items.append(Signal(**payload))
        return SignalsPage(items=items, total=total, limit=limit, offset=offset, cutoff=cutoff)

    def events(self, code: str | None, as_of: date, cutoff: datetime,
               limit: int, offset: int) -> EventsPage:
        parameters = (cutoff, cutoff, as_of, cutoff, code, code)
        total = self._count(EVENTS_CTE + "SELECT count(*) AS total FROM selected", parameters)
        rows = self._rows(EVENTS_CTE + "SELECT * FROM selected ORDER BY effective_date DESC NULLS LAST, event_id LIMIT %s OFFSET %s",
                          parameters + (limit, offset))
        items = []
        for row in rows:
            metadata = row.pop("metadata")
            confirmed = row["status"] == "CONFIRMED"
            in_scope = (row["source_id"] in {"SPK", "spk-bulletins"}
                        and row["event_type"] == "SPK_LIQUIDATION_ORDER"
                        and metadata.get("bulletin_id") == "2026-61")
            row["quotation"] = row["quotation"] or metadata.get("quotation")
            items.append(RegulatoryEvent(
                **row, source_url=source_url(metadata.get("source_url")),
                review_state="HUMAN_CONFIRMED" if confirmed else "UNDER_REVIEW",
                triggers_regulatory_signal=confirmed and in_scope,
                bulletin_id=metadata.get("bulletin_id"), in_monitoring_scope=in_scope,
            ))
        return EventsPage(items=items, total=total, limit=limit, offset=offset, cutoff=cutoff)
