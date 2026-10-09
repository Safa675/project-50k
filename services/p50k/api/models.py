"""Strict response validation for the separate private research contract."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation, localcontext
from fractions import Fraction
import math
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


class ConcentrationSourceRow(StrictModel):
    source_id: Hash
    page: Annotated[int, Field(ge=1)]
    bbox: tuple[float, float, float, float] | list[float]
    reported_value: Financial

    @model_validator(mode="after")
    def valid_source_rectangle(self) -> ConcentrationSourceRow:
        if len(self.bbox) != 4 or not all(math.isfinite(value) for value in self.bbox):
            raise ValueError("Holding source rectangles must contain four finite coordinates")
        x0, y0, x1, y1 = self.bbox
        if not (0 <= x0 < x1 <= 950 and 0 <= y0 < y1 <= 1200):
            raise ValueError("Holding source rectangles must use the supported PDF profile")
        if Decimal(self.reported_value) <= 0:
            raise ValueError("Concentration source rows require positive reported values")
        return self


class ConcentrationPosition(StrictModel):
    isin: Annotated[str, Field(pattern=r"^[A-Z]{2}[A-Z0-9]{10}$")]
    native_name: Annotated[str, Field(min_length=1)]
    value: Financial
    weight: Financial
    source_rows: Annotated[list[ConcentrationSourceRow], Field(min_length=1)]

    @model_validator(mode="after")
    def positive_position(self) -> ConcentrationPosition:
        if Decimal(self.value) <= 0 or not 0 < Decimal(self.weight) <= 1:
            raise ValueError("Identified concentration positions must be positive")
        if sum((Fraction(Decimal(row.reported_value)) for row in self.source_rows), Fraction()) != Fraction(Decimal(self.value)):
            raise ValueError("Aggregated positions must retain their contributing source-row values")
        return self


class ConcentrationComparison(StrictModel):
    status: Literal["AVAILABLE", "UNAVAILABLE"]
    reason: str | None
    previous_period: Period | None
    previous_effective_date: Period | None
    previous_published_at: Timestamp | None
    input_refs: list[Hash]
    previous_top1_ratio: Financial | None
    previous_top5_ratio: Financial | None
    previous_top10_ratio: Financial | None
    previous_hhi: Financial | None
    top1_ratio_delta: Financial | None
    top5_ratio_delta: Financial | None
    top10_ratio_delta: Financial | None
    hhi_delta: Financial | None

    @model_validator(mode="after")
    def unavailable_comparison_is_unknown(self) -> ConcentrationComparison:
        fields = (self.previous_top1_ratio, self.previous_top5_ratio, self.previous_top10_ratio, self.previous_hhi,
                  self.top1_ratio_delta, self.top5_ratio_delta, self.top10_ratio_delta, self.hhi_delta)
        if self.status == "UNAVAILABLE" and (not self.reason or any(value is not None for value in fields)):
            raise ValueError("Unavailable concentration comparisons cannot invent historical metrics")
        if self.status == "AVAILABLE" and (self.reason is not None or any(value is None for value in fields)):
            raise ValueError("Available concentration comparisons require all previous metrics and deltas")
        return self


class Concentration(StrictModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True, serialize_by_alias=True)
    schema_version: Literal["p50k.holding-concentration.v1"] = Field(alias="schema")
    status: Literal["AVAILABLE", "PARTIAL", "UNAVAILABLE"]
    research_screen: Literal["NOT_SCREENED"]
    production_status: Literal["ABSTAINED"]
    scope: Literal["POSITIVE_IDENTIFIED_ISIN_SECURITIES"]
    weight_basis: Literal["NORMALIZED_IDENTIFIED_SECURITIES_VALUE"]
    coverage_basis: Literal["REPORTED_PORTFOLIO_VALUE"]
    issuer_aggregation: Literal["NOT_AVAILABLE"]
    fund_lookthrough: Literal["NOT_PERFORMED"]
    cadence: Literal["MONTHLY"]
    report_period: Period | None
    effective_date: Period | None
    published_at: Timestamp | None
    age_days: Count | None
    current_source_id: Hash | None
    input_refs: list[Hash]
    missing_reasons: list[str]
    qualifications: list[str]
    subset_value: Financial | None
    reported_portfolio_value: Financial | None
    portfolio_coverage_ratio: Financial | None
    portfolio_rounding_bound: Financial | None
    position_count: Count
    top1_ratio: Financial | None
    top5_ratio: Financial | None
    top10_ratio: Financial | None
    hhi: Financial | None
    positions: Annotated[list[ConcentrationPosition], Field(max_length=10)]
    comparison: ConcentrationComparison

    @model_validator(mode="after")
    def bounded_descriptive_arithmetic(self) -> Concentration:
        from calendar import monthrange
        from p50k.research_reviews.concentration import ratio_string, value_string

        pairs = [(self.report_period, self.effective_date, self.published_at),
                 (self.comparison.previous_period, self.comparison.previous_effective_date,
                  self.comparison.previous_published_at)]
        for period, effective, published in pairs:
            if (period is None) != (effective is None) or (period is None) != (published is None):
                raise ValueError("Monthly concentration provenance must retain period, month-end, and publication together")
            if period is not None:
                if len(period) != 7 or len(effective) != 10:
                    raise ValueError("Concentration requires monthly periods and complete month-end dates")
                year, month = map(int, period.split("-"))
                if effective != date(year, month, monthrange(year, month)[1]).isoformat():
                    raise ValueError("Concentration effective date must be the reported month-end")
                if effective > CUTOFF_AT[:10] or datetime.fromisoformat(published) > datetime.fromisoformat(CUTOFF_AT):
                    raise ValueError("Concentration report and publication must precede the cutoff")
        expected_age = None if self.effective_date is None else (date.fromisoformat(CUTOFF_AT[:10]) - date.fromisoformat(self.effective_date)).days
        if self.age_days != expected_age:
            raise ValueError("Concentration age must match its reported month-end")
        if (self.current_source_id is None) != (self.report_period is None):
            raise ValueError("A selected concentration report requires its exact PDF source ID")
        if self.current_source_id is not None and self.current_source_id not in self.input_refs:
            raise ValueError("The selected concentration PDF must belong to its source union")
        values = (self.subset_value, self.portfolio_coverage_ratio, self.portfolio_rounding_bound,
                  self.top1_ratio, self.top5_ratio, self.top10_ratio, self.hhi)
        if self.status == "UNAVAILABLE":
            if any(value is not None for value in values) or self.position_count or self.positions or not self.missing_reasons:
                raise ValueError("Unavailable concentration requires missing reasons and null metrics")
        else:
            if any(value is None for value in values) or self.reported_portfolio_value is None or self.portfolio_rounding_bound is None or self.report_period is None:
                raise ValueError("Readable concentration requires every metric, denominator and date")
            if self.missing_reasons:
                raise ValueError("Readable concentration cannot retain blocking missing reasons")
            subset, portfolio = Fraction(Decimal(self.subset_value)), Fraction(Decimal(self.reported_portfolio_value))
            rounding = Fraction(Decimal(self.portfolio_rounding_bound))
            if portfolio <= 0 or rounding < 0 or not 0 < subset <= portfolio + rounding or self.portfolio_coverage_ratio != ratio_string(subset / portfolio):
                raise ValueError("Subset coverage must match its positive reported denominator")
            if (subset > portfolio) != ("coverage_exceeds_one_within_printed_rounding" in self.qualifications):
                raise ValueError("Coverage over one must identify its printed rounding overhang")
            if not 0 < Decimal(self.top1_ratio) <= Decimal(self.top5_ratio) <= Decimal(self.top10_ratio) <= 1 or not 0 < Decimal(self.hhi) <= 1:
                raise ValueError("Concentration shares and HHI must be bounded ratios")
            if self.position_count < 1 or len(self.positions) != min(10, self.position_count):
                raise ValueError("Concentration retains exactly the first ten positions, or all when fewer")
            ordered = sorted(self.positions, key=lambda position: (-Fraction(Decimal(position.value)), position.isin))
            if self.positions != ordered or len({position.isin for position in self.positions}) != len(self.positions):
                raise ValueError("Concentration positions must be unique and ordered by value then ISIN")
            for position in self.positions:
                if position.weight != ratio_string(Fraction(Decimal(position.value)) / subset):
                    raise ValueError("Concentration weights must use the identified-security subset")
            for count, field in ((1, "top1_ratio"), (5, "top5_ratio"), (10, "top10_ratio")):
                total = sum((Fraction(Decimal(position.value)) for position in self.positions[:count]), Fraction())
                if getattr(self, field) != ratio_string(total / subset):
                    raise ValueError("Top-N shares must match the retained largest positions")
            retained = sum((Fraction(Decimal(position.value)) for position in self.positions), Fraction())
            head_hhi = sum(((Fraction(Decimal(position.value)) / subset) ** 2 for position in self.positions), Fraction())
            tail_weight = (subset - retained) / subset
            tail_count = self.position_count - len(self.positions)
            if retained > subset or (tail_count > 0 and tail_weight <= 0):
                raise ValueError("Truncated concentration positions require positive unretained exposure")
            lower = head_hhi + (tail_weight * tail_weight / tail_count if tail_count else Fraction())
            upper = head_hhi + tail_weight * tail_weight
            if not Decimal(ratio_string(lower)) <= Decimal(self.hhi) <= Decimal(ratio_string(upper)):
                raise ValueError("HHI must be consistent with the retained head and remaining position count")
            if self.position_count <= 10:
                total = sum((Fraction(Decimal(position.value)) for position in self.positions), Fraction())
                hhi = sum(((Fraction(Decimal(position.value)) / subset) ** 2 for position in self.positions), Fraction())
                if total != subset or self.hhi != ratio_string(hhi):
                    raise ValueError("Complete retained positions must reproduce the exact subset HHI")
            partial_reasons = {"positive_security_without_identified_isin", "nonsecurity_or_derivative_positions_excluded"}
            if self.status == "PARTIAL" and not partial_reasons.intersection(self.qualifications):
                raise ValueError("Partial concentration must explain excluded exposure")
            if self.status == "AVAILABLE" and partial_reasons.intersection(self.qualifications):
                raise ValueError("Complete concentration cannot claim excluded exposure")
        comparison = self.comparison
        if not set(comparison.input_refs).issubset(self.input_refs):
            raise ValueError("Historical concentration sources must belong to the same finding")
        if any(row.source_id not in self.input_refs for position in self.positions for row in position.source_rows):
            raise ValueError("Position source rows must belong to the concentration input union")
        if any(row.source_id != self.current_source_id for position in self.positions for row in position.source_rows):
            raise ValueError("Current positions must retain the exact selected PDF identity")
        if comparison.status == "AVAILABLE":
            if self.status != "AVAILABLE" or comparison.previous_period is None or comparison.previous_period >= self.report_period or not comparison.input_refs:
                raise ValueError("Concentration changes require an earlier complete comparable report")
            for field in ("top1_ratio", "top5_ratio", "top10_ratio", "hhi"):
                current, previous = getattr(self, field), getattr(comparison, "previous_" + field)
                if not 0 < Decimal(previous) <= 1:
                    raise ValueError("Historical concentration metrics must be bounded ratios")
                expected = value_string(Fraction(Decimal(current)) - Fraction(Decimal(previous)))
                if getattr(comparison, field + "_delta") != expected:
                    raise ValueError("Concentration deltas must match the retained current and previous metrics")
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
    concentration: Concentration | None = None

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
    concentration_available: Count | None = None
    concentration_partial: Count | None = None
    concentration_unavailable: Count | None = None

    @model_validator(mode="after")
    def counts_add_up(self) -> Summary:
        if self.fully_assessable + self.partially_assessable + self.unavailable != self.total:
            raise ValueError("Assessment counts must equal the denominator")
        if self.two_findings + self.one_finding + self.no_findings + self.unassessable_no_findings != self.total:
            raise ValueError("Finding counts must equal the denominator")
        extension_counts = (self.concentration_available, self.concentration_partial, self.concentration_unavailable)
        if any(value is not None for value in extension_counts) and (any(value is None for value in extension_counts) or sum(extension_counts) != self.total):
            raise ValueError("Concentration coverage counts must retain the full denominator")
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
    source_by_id = {source.source_id: source for source in sources}
    for fund in funds:
        references = set(fund.evidence + fund.d1.input_refs + fund.flow.input_refs)
        references.update(endpoint.source_id for endpoint in fund.flow.endpoint_refs)
        if fund.concentration is not None:
            concentration = fund.concentration
            references.update(concentration.input_refs)
            references.update(concentration.comparison.input_refs)
            for reference in concentration.input_refs:
                source = source_by_id.get(reference)
                if source is not None and source.kind not in ("KAP_PDF", "KAP_SERIES", "CODE", "PROTOCOL", "UNIVERSE"):
                    raise ValueError("Concentration sources must belong to its registered KAP-only scope")
                if source is not None and source.kind in ("KAP_PDF", "KAP_SERIES") and source.fund_code != fund.code:
                    raise ValueError("Concentration evidence must identify the same fund")
                if source is not None and source.kind == "KAP_PDF" and (source.published_at is None or datetime.fromisoformat(source.published_at) > datetime.fromisoformat(CUTOFF_AT)):
                    raise ValueError("Concentration PDF evidence requires known publication before cutoff")
            current_pdf_ids = {row.source_id for position in concentration.positions for row in position.source_rows}
            if concentration.current_source_id is not None:
                current_pdf_ids.add(concentration.current_source_id)
            for identifier in current_pdf_ids:
                source = source_by_id.get(identifier)
                if source is None or not source.pdf_available or source.fund_code != fund.code or source.published_at is None or datetime.fromisoformat(source.published_at) != datetime.fromisoformat(concentration.published_at):
                    raise ValueError("Holding source rows require same-fund PDFs with the reported publication")
            for identifier in concentration.comparison.input_refs:
                source = source_by_id.get(identifier)
                if source is None or not source.pdf_available or source.fund_code != fund.code or source.published_at is None or datetime.fromisoformat(source.published_at) != datetime.fromisoformat(concentration.comparison.previous_published_at):
                    raise ValueError("Previous concentration sources require same-fund eligible PDF publication")
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
    extension_count = sum(fund.concentration is not None for fund in funds)
    if extension_count:
        if extension_count != 100:
            raise ValueError("Concentration extensions must retain all 100 records")
        for status in ("AVAILABLE", "PARTIAL", "UNAVAILABLE"):
            count = sum(fund.concentration.status == status for fund in funds)
            if getattr(summary, "concentration_" + status.lower()) != count:
                raise ValueError("Concentration summary must match its 100 records")
    elif any(getattr(summary, field) is not None for field in ("concentration_available", "concentration_partial", "concentration_unavailable")):
        raise ValueError("Unextended v1 bundles cannot invent concentration coverage counts")
    return provenance, summary, funds, sources
