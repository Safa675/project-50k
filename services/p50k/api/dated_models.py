"""Strict response validation for the separate dated D1 contract (fund_review_dated/PROTOCOL.md).

Only cutoff-free helpers are imported from models.py: its Provenance, Finding,
D1Finding, Chart, Source, Summary and ErrorResponse are bound to the fixed
2026-09-16 cutoff. Every per-date model here checks nested dates against the
response's own ``cutoff_date`` in an after-validator, so validation never depends on
a request-scoped validation context.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
import re
from typing import Annotated, Literal

from pydantic import AfterValidator, BeforeValidator, Field, model_validator

from p50k.research_reviews.dated_comments import TEMPLATES_TR, dated_order, summarize_dated
from p50k.research_reviews.dated_contracts import (
    DEFAULT_DATE, SNAPSHOT_BOUND, THRESHOLD_FIXED, cutoff_at_for, d1_state, validate_cutoff, validate_grid,
)

from .models import StrictModel, financial_string, strict_boolean, strict_integer, timestamp_string

HASH_PATTERN = r"^[a-f0-9]{64}$"
CODE_PATTERN = r"^[A-Z0-9]{3}$"
STALE_REASON = "final_contributing_observation_before_cutoff"


def day_string(value: str) -> str:
    """A complete canonical calendar date; partial YYYY-MM periods are refused."""
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is None or date.fromisoformat(value).isoformat() != value:
        raise ValueError("Dated observations must use canonical YYYY-MM-DD dates")
    return value


def cutoff_string(value: str) -> str:
    try:
        return validate_cutoff(value)
    except ValueError as exc:
        raise ValueError("The cutoff date must be a canonical date inside the registered range") from exc


Financial = Annotated[str, AfterValidator(financial_string)]
Timestamp = Annotated[str, AfterValidator(timestamp_string)]
Day = Annotated[str, AfterValidator(day_string)]
CutoffDate = Annotated[str, AfterValidator(cutoff_string)]
Hash = Annotated[str, Field(pattern=HASH_PATTERN)]
Code = Annotated[str, Field(pattern=CODE_PATTERN)]
Count = Annotated[int, Field(ge=0)]
Fixed100 = Annotated[Literal[100], BeforeValidator(strict_integer)]
StrictFalse = Annotated[Literal[False], BeforeValidator(strict_boolean)]
StrictBool = Annotated[bool, BeforeValidator(strict_boolean)]


class DatedLabels(StrictModel):
    origin: Literal["HISTORICAL_REPLAY"]
    analysis_mode: Literal["EXPLORATORY_ARCHIVE"]
    cutoff_semantics: Literal["RECORDED_SOURCE_DATE_FILTER"]
    point_in_time_verified: StrictFalse
    historical_availability: Literal["UNKNOWN"]
    rights_status: Literal["UNKNOWN"]
    universe_basis: Literal["OCTOBER_2026_INVESTOR_SNAPSHOT"]
    category_basis: Literal["CURRENT_SNAPSHOT"]
    knowledge_basis: Literal["RECORDED_SOURCE_DATE_RECONSTRUCTION"]
    findings_scope: Literal["D1_ONLY"]
    date_rule: Literal["MONTH_END_PLUS_WINDOW_END_V1"]


LABEL_FIELDS = tuple(DatedLabels.model_fields)


class DatedProvenance(DatedLabels):
    cutoff_at: str
    cutoff_date: CutoffDate
    index_id: Hash
    immutable_bundle_id: Hash

    @model_validator(mode="after")
    def cutoff_matches_date(self) -> DatedProvenance:
        if self.cutoff_at != cutoff_at_for(self.cutoff_date):
            raise ValueError("cutoff_at must be the fixed +03:00 end of the response's own cutoff_date")
        return self


class DatedMetricPeriod(StrictModel):
    start: Day | None
    end: Day | None


class D1Units(StrictModel):
    statistic: Literal["DAILY_LOG_RETURN"]
    threshold: Literal["DAILY_LOG_RETURN"]


class DatedD1(StrictModel):
    arithmetic_status: Literal["AVAILABLE", "UNAVAILABLE"]
    research_screen: Literal["CROSSING", "NO_CROSSING", "UNKNOWN"]
    freshness: Literal["FRESH", "STALE", "UNKNOWN"]
    production_status: Literal["ABSTAINED"]
    missing_reasons: list[str]
    qualifications: list[str]
    metric_period: DatedMetricPeriod
    units: D1Units
    input_refs: list[Hash]
    statistic: Financial | None
    threshold: Financial | None
    usable_observations: Count
    window_positions: Count
    eligible_peers: Count
    latest_contributing_at: Day | None

    @model_validator(mode="after")
    def d1_shape(self) -> DatedD1:
        start, end = self.metric_period.start, self.metric_period.end
        if self.window_positions > 60 or self.usable_observations > self.window_positions:
            raise ValueError("Invalid D1 observation window")
        if len(set(self.input_refs)) != len(self.input_refs):
            raise ValueError("D1 inputs must be unique")
        if start is not None and end is not None and start > end:
            raise ValueError("D1 metric period is reversed")
        if self.arithmetic_status == "UNAVAILABLE":
            if self.statistic is not None or self.research_screen != "UNKNOWN" or self.freshness != "UNKNOWN":
                raise ValueError("Unavailable arithmetic cannot carry a finding")
            return self
        if self.statistic is None or self.threshold is None or self.research_screen == "UNKNOWN":
            raise ValueError("Available arithmetic requires a statistic, threshold and screen")
        if self.usable_observations < 50 or self.eligible_peers < 10:
            raise ValueError("D1 requires at least 50 observations and 10 eligible peers")
        if self.latest_contributing_at is None or start is None or end is None or \
                not start <= self.latest_contributing_at <= end:
            raise ValueError("Available D1 must identify its window and a latest observation inside it")
        if self.freshness not in ("FRESH", "STALE") or (self.freshness == "STALE") != (STALE_REASON in self.missing_reasons):
            raise ValueError("Available D1 freshness must be explained")
        expected = "CROSSING" if Decimal(self.statistic) > Decimal(self.threshold) else "NO_CROSSING"
        if self.research_screen != expected:
            raise ValueError("D1 uses a strict greater-than crossing")
        return self

    def check_cutoff(self, cutoff: str) -> None:
        dates = (self.metric_period.start, self.metric_period.end, self.latest_contributing_at)
        if any(value is not None and value > cutoff for value in dates):
            raise ValueError("D1 dates cannot pass the response cutoff")
        if self.arithmetic_status == "AVAILABLE":
            if self.metric_period.end != cutoff:
                raise ValueError("Available D1 windows end at the response cutoff")
            if self.freshness != ("FRESH" if self.latest_contributing_at == cutoff else "STALE"):
                raise ValueError("D1 freshness is measured against the response cutoff")


class DatedChartPoint(StrictModel):
    date: Day
    fund: Financial | None
    peers: Financial | None


class DatedChart(StrictModel):
    status: Literal["AVAILABLE", "UNAVAILABLE"]
    reason: str | None
    baseline_date: Day | None
    unit: Literal["INDEX_100"]
    points: list[DatedChartPoint]
    peer_count: Count

    @model_validator(mode="after")
    def chart_shape(self) -> DatedChart:
        dates = [point.date for point in self.points]
        if dates != sorted(set(dates)):
            raise ValueError("Chart points must be unique ordered dates")
        if self.status == "AVAILABLE" and (not dates or self.baseline_date != dates[0] or self.peer_count < 10):
            raise ValueError("Available charts require a common baseline and 10 peers")
        if self.status == "UNAVAILABLE" and (dates or self.baseline_date is not None or not self.reason):
            raise ValueError("Unavailable charts need an explanation and no invented data")
        return self

    def check_cutoff(self, cutoff: str) -> None:
        if any(point.date > cutoff for point in self.points) or \
                (self.baseline_date is not None and self.baseline_date > cutoff):
            raise ValueError("Chart dates cannot pass the response cutoff")


class DateContext(StrictModel):
    has_positive_price_on_or_before_cutoff: StrictBool


class DatedRecord(StrictModel):
    code: Code
    name: Annotated[str, Field(min_length=1)]
    category: Annotated[str, Field(min_length=1)] | None
    comment_tr: str
    d1_state: Literal["ELIGIBLE_CROSSING", "ELIGIBLE_NO_CROSSING", "STALE", "UNAVAILABLE"]
    d1: DatedD1
    chart: DatedChart
    date_context: DateContext
    evidence: list[Hash]

    @model_validator(mode="after")
    def record_claims(self) -> DatedRecord:
        state = d1_state(self.d1.model_dump(mode="json"))
        if self.d1_state != state or self.comment_tr != TEMPLATES_TR[state]:
            raise ValueError("Record state and comment must follow the D1 finding")
        if not self.date_context.has_positive_price_on_or_before_cutoff and \
                (state != "UNAVAILABLE" or self.chart.status != "UNAVAILABLE"):
            raise ValueError("A fund without a price at the cutoff has no D1 result or chart")
        if self.evidence != sorted(set(self.evidence)) or not set(self.d1.input_refs) <= set(self.evidence):
            raise ValueError("Evidence must be sorted, unique and include every D1 input")
        return self

    def check_cutoff(self, cutoff: str) -> None:
        self.d1.check_cutoff(cutoff)
        self.chart.check_cutoff(cutoff)


class DatedSource(StrictModel):
    source_id: Hash
    kind: Literal["PRICE", "SNAPSHOT", "CALIBRATION", "UNIVERSE", "PROTOCOL", "CODE"]
    label: str
    fund_code: Code | None
    sha256: Hash
    file_name: str
    media_type: Literal["application/json", "text/plain", "application/octet-stream"]
    pdf_available: StrictFalse
    published_at: Timestamp | None
    retrieved_at: Timestamp | None
    historical_availability: Literal["UNKNOWN"]
    rights_status: Literal["UNKNOWN"]
    origin: Literal["HISTORICAL_REPLAY"]
    disclosure_id: None
    disclosure_url: None

    @model_validator(mode="after")
    def price_identifies_fund(self) -> DatedSource:
        if self.kind == "PRICE" and self.fund_code is None:
            raise ValueError("Price sources must identify their fund")
        return self

    def check_cutoff(self, cutoff: str) -> None:
        if self.published_at is not None and \
                datetime.fromisoformat(self.published_at) > datetime.fromisoformat(cutoff_at_for(cutoff)):
            raise ValueError("Sources cannot be published after the response cutoff")


class DatedSummary(StrictModel):
    denominator: Fixed100
    record_count: Fixed100
    d1_eligible_crossing: Count
    d1_eligible_no_crossing: Count
    d1_stale: Count
    d1_unavailable: Count
    no_price_at_cutoff: Count

    @model_validator(mode="after")
    def counts_add_up(self) -> DatedSummary:
        if self.d1_eligible_crossing + self.d1_eligible_no_crossing + self.d1_stale + self.d1_unavailable != 100:
            raise ValueError("D1 states must cover the 100 funds")
        if self.no_price_at_cutoff > self.d1_unavailable:
            raise ValueError("Unpriced funds are a subset of unavailable funds")
        return self


class ThresholdProvenance(StrictModel):
    calibration_end_exclusive: Literal["2025-10-06"]
    percentile: Annotated[Literal[99], BeforeValidator(strict_integer)]
    crossing: Literal["STRICTLY_ABOVE"]
    calibration_run_at_utc: Timestamp
    results_sha256: Hash
    threshold_map_sha256: Hash
    detectors_sha256: Hash
    preregistration_sha256: Hash
    calibration_universe_basis: Literal["OCTOBER_2026_INVESTOR_SNAPSHOT"]
    calibration_category_basis: Literal["2026-10-06 snapshot"]
    note: Literal["Thresholds were computed over a post-event universe that includes the evaluated funds."]

    @model_validator(mode="after")
    def registered_bound(self) -> ThresholdProvenance:
        if any(getattr(self, key) != value for key, value in THRESHOLD_FIXED.items()):
            raise ValueError("Threshold provenance differs from the registered calibration bound")
        return self


class SnapshotInfo(StrictModel):
    bound: Literal["2026-10-07T08:52:12.470547+00:00"]
    latest_retrieved_at: Timestamp
    projection_sha256: Hash

    @model_validator(mode="after")
    def within_bound(self) -> SnapshotInfo:
        if datetime.fromisoformat(self.latest_retrieved_at) > datetime.fromisoformat(SNAPSHOT_BOUND):
            raise ValueError("Snapshot rows cannot pass the registered bound")
        return self


class DateEntry(StrictModel):
    date: CutoffDate
    cutoff_at: str
    bundle_id: Hash

    @model_validator(mode="after")
    def entry_cutoff(self) -> DateEntry:
        if self.cutoff_at != cutoff_at_for(self.date):
            raise ValueError("Every entry carries its canonical cutoff")
        return self


class DatesResponse(DatedLabels):
    """Labels, the index ID and the sealed entries only: no counts, findings or codes."""
    index_id: Hash
    default_date: Literal["2026-09-16"]
    entries: list[DateEntry]

    @model_validator(mode="after")
    def sealed_grid(self) -> DatesResponse:
        dates = validate_grid([entry.date for entry in self.entries])
        if DEFAULT_DATE not in dates or len({entry.bundle_id for entry in self.entries}) != len(self.entries):
            raise ValueError("The date index needs its default date and distinct bundles")
        return self


class DatedSummaryResponse(DatedProvenance):
    summary: DatedSummary
    threshold_provenance: ThresholdProvenance
    snapshot: SnapshotInfo


class DatedFundsResponse(DatedProvenance):
    funds: list[DatedRecord]

    @model_validator(mode="after")
    def bound_records(self) -> DatedFundsResponse:
        codes = [record.code for record in self.funds]
        if len(codes) != 100 or len(set(codes)) != 100:
            raise ValueError("The selected universe must contain exactly 100 unique funds")
        for record in self.funds:
            record.check_cutoff(self.cutoff_date)
        dumped = [record.model_dump(mode="json") for record in self.funds]
        if [row["code"] for row in sorted(dumped, key=dated_order)] != codes:
            raise ValueError("Funds must follow the registered order")
        return self


class DatedFundResponse(DatedProvenance):
    fund: DatedRecord
    sources: list[DatedSource]

    @model_validator(mode="after")
    def bound_detail(self) -> DatedFundResponse:
        self.fund.check_cutoff(self.cutoff_date)
        for source in self.sources:
            source.check_cutoff(self.cutoff_date)
        identifiers = [source.source_id for source in self.sources]
        if identifiers != sorted(set(identifiers)) or set(identifiers) != set(self.fund.evidence):
            raise ValueError("Detail sources must be exactly the record's evidence")
        return self


class DatedError(StrictModel):
    code: Literal["DATE_INVALID", "DATE_NOT_REGISTERED", "FUND_NOT_FOUND", "CONTEXT_MISMATCH",
                  "INDEX_UNAVAILABLE", "INDEX_INVALID", "BUNDLE_INVALID", "NOT_FOUND", "INVALID_REQUEST",
                  "HOST_REJECTED", "INTERNAL_ERROR"]
    message_tr: Annotated[str, Field(min_length=1)]


class DatedErrorResponse(DatedLabels):
    cutoff_at: str | None
    cutoff_date: CutoffDate | None
    index_id: Hash | None
    immutable_bundle_id: None
    error: DatedError

    @model_validator(mode="after")
    def request_context(self) -> DatedErrorResponse:
        expected = None if self.cutoff_date is None else cutoff_at_for(self.cutoff_date)
        if self.cutoff_at != expected:
            raise ValueError("Error cutoff_at must match its own cutoff_date or be null")
        if self.cutoff_date is not None and self.index_id is None:
            raise ValueError("A registered error context names its index")
        return self


@dataclass(frozen=True)
class DatedView:
    """One validated indexed bundle; every response for its date is built from here."""
    metadata: dict
    summary: DatedSummaryResponse
    funds: DatedFundsResponse
    sources: tuple[DatedSource, ...]

    def detail(self, code: str) -> DatedFundResponse | None:
        fund = next((record for record in self.funds.funds if record.code == code), None)
        if fund is None:
            return None
        ids = set(fund.evidence)
        return DatedFundResponse.model_validate({
            **self.metadata, "fund": fund.model_dump(mode="json"),
            "sources": [source.model_dump(mode="json") for source in self.sources if source.source_id in ids]})


def validate_dated_view(bundle: dict, index_id: str) -> DatedView:
    """Validate every public value, reference and count of one bundle against its own cutoff."""
    metadata = {**{key: bundle[key] for key in LABEL_FIELDS}, "cutoff_at": bundle["cutoff_at"],
                "cutoff_date": bundle["cutoff_date"], "index_id": index_id,
                "immutable_bundle_id": bundle["immutable_bundle_id"]}
    DatedProvenance.model_validate(metadata)
    summary = DatedSummaryResponse.model_validate({**metadata, "summary": bundle["summary"],
                                                   "threshold_provenance": bundle["threshold_provenance"],
                                                   "snapshot": bundle["snapshot"]})
    funds = DatedFundsResponse.model_validate({**metadata, "funds": bundle["funds"]})
    sources = tuple(DatedSource.model_validate(value) for value in bundle["sources"])
    for source in sources:
        source.check_cutoff(metadata["cutoff_date"])
    identifiers = {source.source_id for source in sources}
    if len(identifiers) != len(sources):
        raise ValueError("Source identifiers must be unique")
    if any(not set(record.evidence) <= identifiers for record in funds.funds):
        raise ValueError("Every evidence reference must exist in the bundle sources")
    records = [record.model_dump(mode="json") for record in funds.funds]
    if summarize_dated(records) != summary.summary.model_dump(mode="json"):
        raise ValueError("Summary counts must match the list/detail records")
    return DatedView(metadata, summary, funds, sources)
