"""Versioned private research contract, independent of the frozen public API."""
from __future__ import annotations

SCHEMA = "p50k.fund-review.v1"
CUTOFF_AT = "2026-09-16T23:59:59+03:00"
CUTOFF_DATE = "2026-09-16"
METADATA = {
    "origin": "HISTORICAL_REPLAY",
    "analysis_mode": "EXPLORATORY_ARCHIVE",
    "cutoff_at": CUTOFF_AT,
    "cutoff_semantics": "RECORDED_SOURCE_DATE_FILTER",
    "point_in_time_verified": False,
    "historical_availability": "UNKNOWN",
    "rights_status": "UNKNOWN",
    "universe_basis": "OCTOBER_2026_INVESTOR_SNAPSHOT",
    "category_basis": "CURRENT_SNAPSHOT",
}
ARITHMETIC_STATUSES = frozenset({"AVAILABLE", "UNAVAILABLE"})
RESEARCH_SCREENS = frozenset({"CROSSING", "NO_CROSSING", "UNKNOWN"})
FRESHNESS = frozenset({"FRESH", "STALE", "UNKNOWN"})
ASSESSMENTS = frozenset({"FULL", "PARTIAL", "UNAVAILABLE"})
FLOW_DIRECTIONS = frozenset({"INFLOW_ESTIMATE", "OUTFLOW_ESTIMATE", "NONE", "UNKNOWN"})


def empty_finding(kind: str) -> dict:
    """Never turn unavailable input into a negative result."""
    d1 = kind == "d1"
    result = {
        "arithmetic_status": "UNAVAILABLE", "research_screen": "UNKNOWN",
        "freshness": "UNKNOWN", "production_status": "ABSTAINED",
        "missing_reasons": [], "qualifications": ["historical_availability_unknown"],
        "metric_period": {"start": None if d1 else "2026-07", "end": None if d1 else "2026-08"},
        "units": {"statistic": "DAILY_LOG_RETURN" if d1 else "RATIO",
                  "threshold": "DAILY_LOG_RETURN" if d1 else "RATIO"},
        "input_refs": [], "statistic": None, "threshold": None if d1 else "0.10",
    }
    if d1:
        result.update(usable_observations=0, window_positions=0, eligible_peers=0,
                      latest_contributing_at=None)
    else:
        result.update(direction="UNKNOWN", previous_assets=None, current_assets=None,
                      previous_nav=None, current_nav=None, residual=None, endpoint_refs=[],
                      input_units={"assets": "REPORT_CURRENCY", "nav": "REPORT_CURRENCY_PER_UNIT"})
    return result


def eligible(finding: dict) -> bool:
    return finding["arithmetic_status"] == "AVAILABLE" and finding["freshness"] == "FRESH"
