"""Strict, evidence-bearing contracts for the authenticated fund read API."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, JsonValue


FundCode = Annotated[str, Field(pattern=r"^[A-Z0-9]{2,12}$")]
DecimalText = Annotated[str, Field(pattern=r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")]
CoverageState = Literal["TRIGGERED", "NOT_TRIGGERED", "ABSTAINED"]
Origin = Literal["LIVE", "DELAYED", "HISTORICAL_REPLAY", "SYNTHETIC"]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Provenance(Contract):
    origin: Origin = "DELAYED"
    rights_status: Literal["UNREVIEWED"] = "UNREVIEWED"


class Fund(Contract):
    fund_code: FundCode
    name: str
    category: str | None
    tefas_status: str | None
    listing_as_of: date | None
    metadata_current_only: Literal[True] = True


class FundsPage(Provenance):
    items: list[Fund]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0, le=10000)


class PricePoint(Provenance):
    effective_date: date
    nav: DecimalText | None
    published_at: AwareDatetime | None
    available_at: AwareDatetime
    source_id: str
    source_sha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    unit: str
    availability_rule: str
    ambiguous_revision: bool = False


class DailyChart(Provenance):
    fund_code: FundCode
    cadence: Literal["DAILY_NAV"] = "DAILY_NAV"
    start_date: date
    end_date: date
    cutoff: AwareDatetime
    points: list[PricePoint]
    missing_dates: Literal["ABSENT_OBSERVATIONS"] = "ABSENT_OBSERVATIONS"


class FundPriceSummary(Contract):
    """Dated display references, never a replacement for missing observations."""

    scope: Literal["CHART_WINDOW"] = "CHART_WINDOW"
    latest_observation: PricePoint | None = None
    last_available: PricePoint | None = None
    status: Literal["AVAILABLE", "LATEST_MISSING", "LATEST_CONFLICTING", "NO_OBSERVATIONS"] = "NO_OBSERVATIONS"


class SourceReference(Contract):
    source_id: str
    source_sha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    effective_date: date | None
    available_at: AwareDatetime | None
    source_url: str | None


class Signal(Provenance):
    fund_code: FundCode
    detector_id: str
    version_id: str
    run_id: str
    state: CoverageState
    reason: str
    value: DecimalText | None
    threshold: DecimalText | None
    evidence_id: str
    as_of: date
    effective_date: date | None = None
    development_result: Literal[True] = True
    values: dict[str, JsonValue]
    thresholds: dict[str, JsonValue]
    unit: str
    available_at: AwareDatetime | None
    is_attribute: bool = False
    source_references: list[SourceReference] = Field(default_factory=list)
    development_label: Literal["geliştirme sonucu; eşikler olaydan sonra belirlendi"] = "geliştirme sonucu; eşikler olaydan sonra belirlendi"


class SignalsPage(Provenance):
    items: list[Signal]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0, le=50000)
    cutoff: AwareDatetime
    development_result: Literal[True] = True


class Coverage(Contract):
    triggered: int = Field(ge=0)
    not_triggered: int = Field(ge=0)
    abstained: int = Field(ge=0)
    state: CoverageState
    reason: str
    evidence_ids: list[str]


class RegulatoryEvent(Provenance):
    event_id: str
    fund_code: FundCode
    event_type: str
    effective_date: date | None
    status: Literal["CANDIDATE", "CONFIRMED"]
    review_state: Literal["UNDER_REVIEW", "HUMAN_CONFIRMED"]
    triggers_regulatory_signal: bool
    bulletin_id: str | None = None
    in_monitoring_scope: bool = False
    quotation: str | None
    source_id: str
    source_sha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    source_url: str | None
    published_at: AwareDatetime | None
    available_at: AwareDatetime | None
    confirmed_at: AwareDatetime | None
    availability_rule: str
    availability_unknown: bool = False


class EventsPage(Provenance):
    items: list[RegulatoryEvent]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0, le=10000)
    cutoff: AwareDatetime


class FundDetail(Provenance):
    fund: Fund
    chart: DailyChart
    price_summary: FundPriceSummary = Field(default_factory=FundPriceSummary)
    signals: list[Signal]
    coverage: Coverage
    events: list[RegulatoryEvent]
    events_total: int = Field(ge=0)
    cutoff: AwareDatetime
    development_result: Literal[True] = True
