"""Strict response validation for the separate private research contract."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation, localcontext
import re
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field, model_validator

CUTOFF_AT = "2026-09-16T23:59:59+03:00"
HASH_PATTERN = r"^[a-f0-9]{64}$"
CODE_PATTERN = r"^[A-Z0-9]{3}$"


def financial_string(value: str) -> str:
    if not re.fullmatch(r"[+-]?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?", value):
        raise ValueError("Financial quantities must be finite decimal strings")
    try:
        # A rejected exponent can signal InvalidOperation during construction.
        # Keep parsing flags inside a local context even when caller traps differ.
        with localcontext():
            if not Decimal(value).is_finite():
                raise ValueError("Financial quantities must be finite decimal strings")
    except InvalidOperation as exc:
        raise ValueError("Invalid decimal string") from exc
    return value


def period_string(value: str) -> str:
    if re.fullmatch(r"\d{4}-\d{2}", value):
        date.fromisoformat(value + "-01")
    else:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is None:
            raise ValueError("Periods must be canonical YYYY-MM or YYYY-MM-DD")
        date.fromisoformat(value)
    return value


def timestamp_string(value: str) -> str:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})", value):
        raise ValueError("Timestamps must be explicit RFC3339 values")
    datetime.fromisoformat(value)
    return value


def strict_boolean(value: object) -> bool:
    if type(value) is not bool:
        raise ValueError("Boolean flags cannot be numeric substitutes")
    return value


def strict_integer(value: object) -> int:
    if type(value) is not int:
        raise ValueError("Counts must be integers, not coerced substitutes")
    return value


Financial = Annotated[str, AfterValidator(financial_string)]
Period = Annotated[str, AfterValidator(period_string)]
Timestamp = Annotated[str, AfterValidator(timestamp_string)]
Hash = Annotated[str, Field(pattern=HASH_PATTERN)]
Code = Annotated[str, Field(pattern=CODE_PATTERN)]
Count = Annotated[int, Field(ge=0)]
Fixed100 = Annotated[Literal[100], BeforeValidator(strict_integer)]


class StrictModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)


class Provenance(StrictModel):
    origin: Literal["HISTORICAL_REPLAY"]
    analysis_mode: Literal["EXPLORATORY_ARCHIVE"]
    cutoff_at: Literal["2026-09-16T23:59:59+03:00"]
    cutoff_semantics: Literal["RECORDED_SOURCE_DATE_FILTER"]
    point_in_time_verified: Annotated[Literal[False], BeforeValidator(strict_boolean)]
    historical_availability: Literal["UNKNOWN"]
    rights_status: Literal["UNKNOWN"]
    universe_basis: Literal["OCTOBER_2026_INVESTOR_SNAPSHOT"]
    category_basis: Literal["CURRENT_SNAPSHOT"]
    immutable_bundle_id: Hash


PROVENANCE_FIELDS = tuple(Provenance.model_fields)


class MetricPeriod(StrictModel):
    start: Period | None
    end: Period | None


class FindingUnits(StrictModel):
    statistic: Literal["DAILY_LOG_RETURN", "RATIO"]
    threshold: Literal["DAILY_LOG_RETURN", "RATIO"]


class Finding(StrictModel):
    arithmetic_status: Literal["AVAILABLE", "UNAVAILABLE"]
    research_screen: Literal["CROSSING", "NO_CROSSING", "UNKNOWN"]
    freshness: Literal["FRESH", "STALE", "UNKNOWN"]
    production_status: Literal["ABSTAINED"]
    missing_reasons: list[str]
    qualifications: list[str]
    metric_period: MetricPeriod
    units: FindingUnits
    input_refs: list[Hash]
    statistic: Financial | None
    threshold: Financial | None

    @model_validator(mode="after")
    def missing_is_unknown(self) -> Finding:
        if self.arithmetic_status == "UNAVAILABLE":
            if self.statistic is not None or self.research_screen != "UNKNOWN":
                raise ValueError("Unavailable arithmetic cannot carry a finding")
        elif self.statistic is None or self.threshold is None or self.research_screen == "UNKNOWN":
            raise ValueError("Available arithmetic requires a statistic and threshold")
        for value in (self.metric_period.start, self.metric_period.end):
            if value is not None and value > CUTOFF_AT[:10]:
                raise ValueError("Finding periods cannot extend after the cutoff")
        return self


class D1Finding(Finding):
    usable_observations: Count
    window_positions: Count
    eligible_peers: Count
    latest_contributing_at: str | None

    @model_validator(mode="after")
    def d1_units(self) -> D1Finding:
        if self.units.statistic != "DAILY_LOG_RETURN" or self.units.threshold != "DAILY_LOG_RETURN":
            raise ValueError("D1 units must be DAILY_LOG_RETURN")
        if self.window_positions > 60 or self.usable_observations > self.window_positions:
            raise ValueError("Invalid D1 observation window")
        if self.latest_contributing_at is not None:
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", self.latest_contributing_at) is None:
                raise ValueError("D1 observations must use canonical daily dates")
            date.fromisoformat(self.latest_contributing_at)
            if self.latest_contributing_at > CUTOFF_AT[:10]:
                raise ValueError("D1 cannot include a future contributing observation")
        if self.arithmetic_status == "AVAILABLE":
            if self.usable_observations < 50 or self.eligible_peers < 10:
                raise ValueError("D1 requires at least 50 observations and 10 eligible peers")
            if self.latest_contributing_at is None or self.metric_period.start is None or self.metric_period.end is None:
                raise ValueError("Available D1 must identify its window and latest observation")
            expected_freshness = "FRESH" if self.latest_contributing_at == CUTOFF_AT[:10] else "STALE"
            if self.freshness != expected_freshness:
                raise ValueError("D1 freshness must match the latest contributing observation")
            expected_screen = "CROSSING" if Decimal(self.statistic) > Decimal(self.threshold) else "NO_CROSSING"
            if self.research_screen != expected_screen:
                raise ValueError("D1 uses a strict greater-than crossing")
        return self


class EndpointReference(StrictModel):
    period: Period
    source_id: Hash
    record_sha256: Hash
    record_hash_basis: Literal["CONSUMED_ENDPOINT_FIELDS"]
    published_at: Timestamp | None
    published_at_raw: str | None
    historical_availability: Literal["UNKNOWN"]


class FlowFinding(Finding):
    direction: Literal["INFLOW_ESTIMATE", "OUTFLOW_ESTIMATE", "NONE", "UNKNOWN"]
    previous_assets: Financial | None
    current_assets: Financial | None
    previous_nav: Financial | None
    current_nav: Financial | None
    residual: Financial | None
    endpoint_refs: list[EndpointReference]
    input_units: "FlowInputUnits"

    @model_validator(mode="after")
    def flow_units(self) -> FlowFinding:
        if self.units.statistic != "RATIO" or self.units.threshold != "RATIO":
            raise ValueError("Flow statistic units must be RATIO")
        if self.arithmetic_status == "UNAVAILABLE" and self.direction != "UNKNOWN":
            raise ValueError("Unavailable flow has unknown direction")
        if self.arithmetic_status == "AVAILABLE":
            if any(value is None for value in (self.previous_assets, self.current_assets,
                                               self.previous_nav, self.current_nav, self.residual)):
                raise ValueError("Available flow must retain every input")
            if any(Decimal(value) <= 0 for value in (self.previous_assets, self.previous_nav, self.current_nav)):
                raise ValueError("Opening assets and NAVs must be positive")
            if Decimal(self.current_assets) < 0:
                raise ValueError("Closing assets must not be negative")
            if self.freshness != "FRESH" or len(self.endpoint_refs) != 2:
                raise ValueError("Available flow must retain two dated endpoints")
            if [endpoint.period for endpoint in self.endpoint_refs] != ["2026-07", "2026-08"]:
                raise ValueError("Flow uses only the July/August monthly pair")
            cutoff = datetime.fromisoformat(CUTOFF_AT)
            if any(endpoint.published_at is None or datetime.fromisoformat(endpoint.published_at) > cutoff
                   for endpoint in self.endpoint_refs):
                raise ValueError("Flow endpoint publication must be known and before cutoff")
            if Decimal(self.threshold) != Decimal("0.10"):
                raise ValueError("The fixed flow screen threshold is 0.10")
            rate = Decimal(self.statistic)
            expected_screen = "CROSSING" if rate.copy_abs() >= Decimal(self.threshold) else "NO_CROSSING"
            expected_direction = "INFLOW_ESTIMATE" if rate > 0 else "OUTFLOW_ESTIMATE" if rate < 0 else "NONE"
            if self.research_screen != expected_screen or self.direction != expected_direction:
                raise ValueError("Flow screen and direction must match its signed estimate")
            from p50k.detectors.fund_flow import calculate_endpoint_change
            calculated = calculate_endpoint_change(previous_assets=Decimal(self.previous_assets),
                                                   current_assets=Decimal(self.current_assets),
                                                   previous_nav=Decimal(self.previous_nav),
                                                   current_nav=Decimal(self.current_nav))
            if calculated.residual != Decimal(self.residual) or calculated.rate != rate:
                raise ValueError("Flow arithmetic must match the retained inputs")
        if self.metric_period.start != "2026-07" or self.metric_period.end != "2026-08":
            raise ValueError("Flow periods must remain fixed even when unavailable")
        return self


class FlowInputUnits(StrictModel):
    assets: Literal["REPORT_CURRENCY"]
    nav: Literal["REPORT_CURRENCY_PER_UNIT"]


class ChartPoint(StrictModel):
    date: Period
    fund: Financial | None
    peers: Financial | None


class Chart(StrictModel):
    status: Literal["AVAILABLE", "UNAVAILABLE"]
    reason: str | None
    baseline_date: Period | None
    unit: Literal["INDEX_100"]
    points: list[ChartPoint]
    peer_count: Count

    @model_validator(mode="after")
    def chart_dates(self) -> Chart:
        dates = [point.date for point in self.points]
        if dates != sorted(set(dates)) or any(day > CUTOFF_AT[:10] for day in dates):
            raise ValueError("Chart points must be unique ordered dates before cutoff")
        if any(len(day) != 10 for day in dates):
            raise ValueError("Daily chart points require complete calendar dates")
        if self.status == "AVAILABLE" and (not dates or self.baseline_date != dates[0] or self.peer_count < 10):
            raise ValueError("Available charts require a common baseline and 10 peers")
        if self.status == "UNAVAILABLE" and (dates or self.baseline_date is not None or not self.reason):
            raise ValueError("Unavailable charts need an explanation and no invented data")
        return self


class Fund(StrictModel):
    code: Code
    name: str
    category: str | None
    comment_tr: str
    assessment: Literal["FULL", "PARTIAL", "UNAVAILABLE"]
    eligible_crossings: Annotated[int, Field(ge=0, le=2)]
    d1: D1Finding
    flow: FlowFinding
    chart: Chart
    evidence: list[Hash]

    @model_validator(mode="after")
    def eligibility_claims(self) -> Fund:
        findings = (self.d1, self.flow)
        eligible = [finding.arithmetic_status == "AVAILABLE" and finding.freshness == "FRESH" for finding in findings]
        count = sum(ok and finding.research_screen == "CROSSING" for ok, finding in zip(eligible, findings))
        assessment = "FULL" if all(eligible) else "PARTIAL" if any(eligible) else "UNAVAILABLE"
        if count != self.eligible_crossings or assessment != self.assessment:
            raise ValueError("Fund eligibility and assessment must match the two findings")
        return self


class Source(StrictModel):
    source_id: Hash
    kind: Literal["PRICE", "KAP_SERIES", "KAP_PDF", "SNAPSHOT", "CALIBRATION", "UNIVERSE", "PROTOCOL", "CODE"]
    label: str
    fund_code: Code | None
    sha256: Hash
    file_name: str
    media_type: Literal["application/json", "application/pdf", "text/plain", "application/octet-stream"]
    pdf_available: Annotated[bool, BeforeValidator(strict_boolean)]
    published_at: Timestamp | None
    retrieved_at: Timestamp | None
    historical_availability: Literal["UNKNOWN"]
    rights_status: Literal["UNKNOWN"]
    origin: Literal["HISTORICAL_REPLAY"]
    disclosure_id: Annotated[str, Field(pattern=r"^[0-9]+$")] | None
    disclosure_url: str | None

    @model_validator(mode="after")
    def official_disclosure(self) -> Source:
        expected = None if self.disclosure_id is None else f"https://www.kap.org.tr/tr/Bildirim/{self.disclosure_id}"
        if self.disclosure_url != expected:
            raise ValueError("Disclosure links must use the fixed official KAP URL")
        if self.pdf_available != (self.kind == "KAP_PDF" and self.media_type == "application/pdf"):
            raise ValueError("PDF availability must match its source type")
        return self


class Summary(StrictModel):
    total: Fixed100
    fully_assessable: Count
    partially_assessable: Count
    unavailable: Count
    two_findings: Count
    one_finding: Count
    no_findings: Count
    unassessable_no_findings: Count
    d1_assessable: Count
    flow_assessable: Count
    d1_stale: Count
    denominator: Fixed100

    @model_validator(mode="after")
    def counts_add_up(self) -> Summary:
        if self.fully_assessable + self.partially_assessable + self.unavailable != self.total:
            raise ValueError("Assessment counts must equal the denominator")
        if self.two_findings + self.one_finding + self.no_findings + self.unassessable_no_findings != self.total:
            raise ValueError("Finding counts must equal the denominator")
        return self


class Health(StrictModel):
    status: Literal["OK"]
    record_count: Fixed100


class HealthResponse(Provenance):
    health: Health


class SummaryResponse(Provenance):
    summary: Summary


class FundsResponse(Provenance):
    funds: list[Fund]


class FundResponse(Provenance):
    fund: Fund
    sources: list[Source]


class Error(StrictModel):
    code: Literal["BUNDLE_UNAVAILABLE", "BUNDLE_INVALID", "NOT_FOUND", "INVALID_REQUEST", "HOST_REJECTED", "INTERNAL_ERROR"]
    message_tr: str


class ErrorResponse(Provenance):
    immutable_bundle_id: Hash | None
    error: Error


def validate_public_bundle(bundle: dict) -> tuple[Provenance, Summary, tuple[Fund, ...], tuple[Source, ...]]:
    """Validate every public value, referential link, count and universe cardinality."""
    provenance = Provenance.model_validate({key: bundle[key] for key in PROVENANCE_FIELDS})
    summary = Summary.model_validate(bundle["summary"])
    funds = tuple(Fund.model_validate(value) for value in bundle["funds"])
    sources = tuple(Source.model_validate(value) for value in bundle["sources"])
    if len(funds) != 100 or len({fund.code for fund in funds}) != 100:
        raise ValueError("The selected universe must contain exactly 100 unique funds")
    if len({source.source_id for source in sources}) != len(sources):
        raise ValueError("Source identifiers must be unique")
    source_ids = {source.source_id for source in sources}
    for fund in funds:
        references = set(fund.evidence + fund.d1.input_refs + fund.flow.input_refs)
        references.update(endpoint.source_id for endpoint in fund.flow.endpoint_refs)
        if not references <= source_ids:
            raise ValueError("Every evidence reference must exist in the manifest")
    actual = {
        "fully_assessable": sum(fund.assessment == "FULL" for fund in funds),
        "partially_assessable": sum(fund.assessment == "PARTIAL" for fund in funds),
        "unavailable": sum(fund.assessment == "UNAVAILABLE" for fund in funds),
        "two_findings": sum(fund.eligible_crossings == 2 for fund in funds),
        "one_finding": sum(fund.eligible_crossings == 1 for fund in funds),
        "no_findings": sum(fund.eligible_crossings == 0 and fund.assessment == "FULL" for fund in funds),
        "unassessable_no_findings": sum(fund.eligible_crossings == 0 and fund.assessment != "FULL" for fund in funds),
        "d1_assessable": sum(fund.d1.arithmetic_status == "AVAILABLE" and fund.d1.freshness == "FRESH" for fund in funds),
        "flow_assessable": sum(fund.flow.arithmetic_status == "AVAILABLE" and fund.flow.freshness == "FRESH" for fund in funds),
        "d1_stale": sum(fund.d1.freshness == "STALE" for fund in funds),
    }
    if any(getattr(summary, key) != value for key, value in actual.items()):
        raise ValueError("Summary counts must match list/detail records")
    return provenance, summary, funds, sources
