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
    Coverage, DailyChart, EventsPage, Fund, FundsPage, FundPriceSummary, PricePoint,
    RegulatoryEvent, Signal, SignalsPage, SourceReference,
)
from p50k.product.analysis_context import historical_mode, page_origin, run_day, run_origins


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


def price_summary_for(chart: DailyChart) -> FundPriceSummary:
    """Keep the latest missing row visible beside the last actual positive NAV.

    Both references retain their own dates and provenance within the requested
    chart window. No value is carried forward or interpreted as today's price.
    Repeat the availability guard here so later appended observations cannot
    alter a summary evaluated against the same cutoff.
    """
    points = sorted((point for point in chart.points
                     if chart.start_date <= point.effective_date <= chart.end_date
                     and point.available_at <= chart.cutoff
                     and (point.published_at is None or point.published_at <= chart.cutoff)),
                    key=lambda point: point.effective_date)
    if not points:
        return FundPriceSummary()
    latest = points[-1]
    known = [point for point in points if not point.ambiguous_revision
             and point.nav is not None and Decimal(point.nav) > 0]
    status = ("LATEST_CONFLICTING" if latest.ambiguous_revision else "AVAILABLE"
              if latest.nav is not None and Decimal(latest.nav) > 0 else "LATEST_MISSING")
    return FundPriceSummary(latest_observation=latest,
                            last_available=known[-1] if known else None, status=status)


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
    for field in ('effective_date','available_at','source_url'):
        payload.setdefault(field,None)
    if isinstance(payload.get("effective_date"), str):
        payload["effective_date"] = date.fromisoformat(payload["effective_date"])
    if isinstance(payload.get("available_at"), str):
        payload["available_at"] = datetime.fromisoformat(payload["available_at"].replace("Z", "+00:00"))
    payload["source_url"] = source_url(payload.get("source_url"))
    return SourceReference(**payload)


FUND_COLUMNS = "fund_code, name, category, tefas_status, listing_as_of"
PRICE_SQL = """
    WITH eligible AS (
        SELECT effective_date, nav, published_at, available_at, observed_at,
            source_id, source_sha256, unit, availability_rule, origin,
            dense_rank() OVER (PARTITION BY effective_date
                ORDER BY available_at DESC, observed_at DESC NULLS LAST) AS priority
        FROM obs.fund_prices
        WHERE fund_code = %s AND effective_date BETWEEN %s AND %s
            AND available_at IS NOT NULL AND available_at <= %s
            AND (published_at IS NULL OR published_at <= %s)
    ), latest AS (
        SELECT * FROM eligible WHERE priority = 1
    ), conflicts AS (
        SELECT effective_date,
            (count(DISTINCT nav) > 1 OR (count(nav) > 0 AND count(nav) < count(*))) AS ambiguous_revision
        FROM latest GROUP BY effective_date
    )
    SELECT DISTINCT ON (latest.effective_date)
        latest.effective_date,
        CASE WHEN conflicts.ambiguous_revision THEN NULL::numeric ELSE latest.nav END AS nav,
        latest.published_at, latest.available_at, latest.source_id,
        latest.source_sha256, latest.unit, latest.availability_rule, latest.origin,
        conflicts.ambiguous_revision
    FROM latest JOIN conflicts USING (effective_date)
    ORDER BY latest.effective_date, latest.source_sha256 DESC
"""
SIGNALS_CTE = """
    WITH latest_run AS (
        SELECT run.run_id, inputs.version_id FROM det.detector_runs run
        JOIN det.run_inputs inputs ON inputs.run_id = run.run_id
        WHERE run.origin = ANY(%s) AND run.cutoff IS NOT NULL AND run.cutoff <= %s
            AND (%s::date IS NULL OR (run.cutoff AT TIME ZONE 'Europe/Istanbul')::date=%s::date)
            AND inputs.complete
        ORDER BY run.cutoff DESC, run.created_at DESC, run.run_id DESC LIMIT 1
    ), selected AS (
        SELECT signal.fund_code, signal.detector_id, latest_run.version_id,
            signal.run_id, signal.state, signal.reason, signal.value,
            signal.threshold, signal.evidence_id, signal.as_of, item.effective_date,
            item.origin, item.values, item.thresholds, item.unit, item.available_at, item.source_references,
            COALESCE((item.metadata->>'is_attribute')::boolean, false) AS is_attribute
        FROM det.signals signal
        JOIN latest_run ON latest_run.run_id = signal.run_id
        JOIN det.evidence_items item ON item.evidence_id = signal.evidence_id
        JOIN ref.funds fund ON fund.fund_code=signal.fund_code
        WHERE signal.as_of <= %s
            AND (item.available_at <= %s OR (item.available_at IS NULL AND signal.state = 'ABSTAINED'))
            AND (%s::text IS NULL OR signal.fund_code = %s)
            AND (%s::text IS NULL OR signal.state = %s)
            AND (fund.fund_code ILIKE %s OR fund.name ILIKE %s)
            AND (%s::text IS NULL OR fund.category=%s)
    )
"""
EVENTS_CTE = """
    WITH selected AS (
        SELECT DISTINCT ON (event_id)
            event_id, fund_code, event_type, effective_date, status,
            quotation, source_id, source_sha256, metadata,
            published_at, available_at, confirmed_at, availability_rule, origin
        FROM obs.regulatory_events
        WHERE (available_at <= %s OR (available_at IS NULL AND ingested_at <= %s))
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

    def funds(self, query: str, limit: int, offset: int, category: str | None = None) -> FundsPage:
        # Escape LIKE metacharacters so every character is a literal search.
        term = "%" + query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        where = " WHERE (fund_code ILIKE %s OR name ILIKE %s) AND (%s::text IS NULL OR category=%s)"
        parameters = (term, term, category, category)
        total = self._count("SELECT count(*) AS total FROM ref.funds" + where, parameters)
        rows = self._rows("SELECT " + FUND_COLUMNS + " FROM ref.funds" + where
                          + " ORDER BY fund_code LIMIT %s OFFSET %s", parameters + (limit, offset))
        if historical_mode():
            for row in rows:row['tefas_status']=None
        return FundsPage(items=[Fund(**row) for row in rows], total=total, limit=limit, offset=offset)

    def fund(self, code: str) -> Fund | None:
        rows = self._rows("SELECT " + FUND_COLUMNS + " FROM ref.funds WHERE fund_code = %s", (code,))
        if rows and historical_mode():rows[0]['tefas_status']=None
        return Fund(**rows[0]) if rows else None

    def chart(self, code: str, start: date, end: date, cutoff: datetime) -> DailyChart:
        rows = self._rows(PRICE_SQL, (code, start, end, cutoff, cutoff))
        points = [PricePoint(**{**row, "nav": decimal_text(row["nav"])}) for row in rows]
        return DailyChart(fund_code=code, start_date=start, end_date=end, cutoff=cutoff, points=points)

    def signals(self, code: str | None, state: str | None, as_of: date,
                cutoff: datetime, limit: int, offset: int, query: str='', category: str|None=None) -> SignalsPage:
        origins = run_origins(database=getattr(getattr(self.connection,'info',None),'dbname',None) or 'unknown')
        # A retrospective read uses only the run of its cutoff's own day.
        day = run_day(cutoff)
        term='%'+query.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%'
        parameters = (origins, cutoff, day, day, as_of, cutoff, code, code, state, state,term,term,category,category)
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
        return SignalsPage(items=items, total=total, limit=limit, offset=offset, cutoff=cutoff, origin=page_origin())

    def events(self, code: str | None, as_of: date, cutoff: datetime,
               limit: int, offset: int) -> EventsPage:
        parameters = (cutoff, cutoff, cutoff, as_of, cutoff, code, code)
        total = self._count(EVENTS_CTE + "SELECT count(*) AS total FROM selected", parameters)
        rows = self._rows(EVENTS_CTE + "SELECT * FROM selected ORDER BY effective_date DESC NULLS LAST, event_id LIMIT %s OFFSET %s",
                          parameters + (limit, offset))
        items = []
        for row in rows:
            metadata = row.pop("metadata")
            confirmed = row["status"] == "CONFIRMED"
            availability_unknown = row["available_at"] is None
            in_scope = (row["source_id"] in {"SPK", "spk-bulletins"}
                        and row["event_type"] == "SPK_LIQUIDATION_ORDER"
                        and metadata.get("bulletin_id") == "2026-61")
            row["quotation"] = row["quotation"] or metadata.get("quotation")
            items.append(RegulatoryEvent(
                **row, source_url=source_url(metadata.get("source_url")),
                review_state="HUMAN_CONFIRMED" if confirmed and not availability_unknown else "UNDER_REVIEW",
                triggers_regulatory_signal=confirmed and in_scope and not availability_unknown and row["effective_date"] is not None,
                bulletin_id=metadata.get("bulletin_id"), in_monitoring_scope=in_scope,
                availability_unknown=availability_unknown,
            ))
        return EventsPage(items=items, total=total, limit=limit, offset=offset, cutoff=cutoff, origin=page_origin())
