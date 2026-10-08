"""AN-FND-004: comparable asset-class allocation changes, not trade turnover.

The Decimal helper can screen exploratory distributions. Production admission
reads an immutable ReplayCursor and requires complete, dated, comparable source
evidence. Monthly averages remain monthly averages; unknown metadata fails closed.
"""
from __future__ import annotations

import calendar
import re
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import (
    Context, Decimal, DecimalException, DivisionByZero, Inexact, InvalidOperation,
    Overflow, ROUND_HALF_EVEN, Rounded, Underflow, localcontext,
)
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from p50k.evidence_store import Observation, parse_timestamp
from p50k.replay import AmbiguousRevision, ReplayCursor

_THRESHOLD = Decimal("0.20")
_MAX_CATEGORIES = 1000
_MAX_DECIMAL_PLACES = 4096
_SCOPE_FIELDS = ("fund_scope", "share_class", "valuation_timezone")
_BASES = ("MONTH_END", "MONTHLY_AVERAGE")


@dataclass(frozen=True)
class AllocationChange:
    distance: Decimal | None
    max_category_delta: Decimal | None
    category_deltas: tuple[tuple[str, Decimal], ...] = ()
    reasons: tuple[str, ...] = ()

    @property
    def screen_crossing(self) -> bool | None:
        """The literal fixed catalog screen, not an evidence-admission decision."""
        if self.distance is None or self.max_category_delta is None or self.reasons:
            return None
        return self.distance >= _THRESHOLD or self.max_category_delta >= _THRESHOLD


@dataclass(frozen=True)
class AllocationEvaluation:
    status: str
    reasons: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    metric: AllocationChange


def _known_text(value: object) -> bool:
    return (isinstance(value, str) and bool(value.strip())
            and value.strip().upper() not in ("UNKNOWN", "UNVERIFIED"))


def _missing(*reasons: str) -> AllocationChange:
    return AllocationChange(None, None, (), tuple(reasons))


def calculate_allocation_change(previous: Mapping[str, Decimal | None] | None,
                                current: Mapping[str, Decimal | None] | None) -> AllocationChange:
    """Compute D=0.5*sum(abs(current-previous)) for exact unit distributions.

    Each category must be explicit in both periods, including actual source
    zeros. Neither missing categories nor rounded totals are repaired. Fractions
    must be finite nonnegative Decimal values with exact totals of one. Bounded
    precision supports up to 1000 categories and 4096 fractional places, and
    arithmetic never inherits the caller's rounding or trap configuration.
    """
    reasons = []
    for name, weights in (("previous", previous), ("current", current)):
        if weights is None:
            reasons.append(f"{name}_allocation_missing")
        elif not isinstance(weights, Mapping) or not weights:
            reasons.append(f"{name}_nonempty_category_mapping_required")
        elif len(weights) > _MAX_CATEGORIES:
            reasons.append(f"{name}_category_count_out_of_bounds")
        elif any(not _known_text(category) for category in weights):
            reasons.append(f"{name}_category_names_invalid")
    if reasons:
        return _missing(*reasons)
    if set(previous) != set(current):
        return _missing("category_schema_mismatch")
    categories = tuple(sorted(previous))
    decimal_places = 0
    for name, weights in (("previous", previous), ("current", current)):
        for category in categories:
            value = weights[category]
            if value is None:
                reasons.append(f"{name}_weight_missing:{category}")
            elif not isinstance(value, Decimal):
                reasons.append(f"{name}_weight_requires_decimal:{category}")
            elif not value.is_finite():
                reasons.append(f"{name}_weight_nonfinite:{category}")
            elif value < 0 or value > 1:
                reasons.append(f"{name}_weight_out_of_bounds:{category}")
            elif value:
                places = max(0, -value.as_tuple().exponent)
                if places > _MAX_DECIMAL_PLACES:
                    reasons.append(f"{name}_weight_precision_out_of_bounds:{category}")
                decimal_places = max(decimal_places, places)
    if reasons:
        return _missing(*reasons)
    precision = max(50, decimal_places + len(str(2 * len(categories))) + 3)
    context = Context(prec=precision, rounding=ROUND_HALF_EVEN,
                      Emin=-999999, Emax=999999, capitals=1, clamp=0, flags=[],
                      traps=[InvalidOperation, DivisionByZero, Overflow, Underflow, Inexact, Rounded])
    # Canonicalize only numeric zero to avoid meaningless zero exponents.
    opening = {category: previous[category] if previous[category] else Decimal(0) for category in categories}
    closing = {category: current[category] if current[category] else Decimal(0) for category in categories}
    try:
        with localcontext(context):
            for name, weights in (("previous", opening), ("current", closing)):
                if sum(weights.values(), Decimal(0)) != Decimal(1):
                    reasons.append(f"{name}_weights_do_not_sum_to_one")
            if reasons:
                return _missing(*reasons)
            deltas = tuple((category, closing[category] - opening[category]) for category in categories)
            absolutes = tuple(delta.copy_abs() for _, delta in deltas)
            distance = Decimal("0.5") * sum(absolutes, Decimal(0))
            largest = max(absolutes)
    except DecimalException:
        return _missing("arithmetic_not_representable")
    return AllocationChange(distance, largest, deltas)


def _abstain(*reasons: str) -> AllocationEvaluation:
    return AllocationEvaluation("ABSTAINED", tuple(reasons), (), _missing(*reasons))


def _time_reason(row: Observation) -> str | None:
    if row.availability_provenance not in ("OBSERVED", "ARCHIVE_VERIFIED") or any(
            getattr(row, field) is None for field in ("effective_at", "published_at", "available_at", "observed_at")):
        return "source_timing_unverified"
    instants = tuple(parse_timestamp(getattr(row, field)) for field in
                     ("effective_at", "published_at", "available_at", "observed_at"))
    if not instants[0] <= instants[1] <= instants[2] <= instants[3]:
        return "source_timing_inconsistent"
    return None


def _period_number(row: Observation) -> int | None:
    period = row.attributes.get("period")
    if (row.attributes.get("cadence") != "MONTHLY" or not isinstance(period, str)
            or not re.fullmatch(r"\d{4}-\d{2}", period)):
        return None
    year, month = map(int, period.split("-"))
    if year < 1 or not 1 <= month <= 12:
        return None
    return year * 12 + month


def _row_reasons(row: Observation) -> list[str]:
    metadata = row.attributes
    reasons = []
    if metadata.get("kind") != "ASSET_ALLOCATION":
        reasons.append("allocation_observation_required")
    if any(not _known_text(metadata.get(field)) for field in _SCOPE_FIELDS):
        reasons.append("scope_class_or_timezone_unknown")
    if metadata.get("allocation_basis") not in _BASES:
        reasons.append("allocation_basis_unverified")
    if not _known_text(metadata.get("category_schema_id")) or metadata.get("category_mapping_status") != "VERIFIED":
        reasons.append("category_mapping_unverified")
    categories = metadata.get("categories")
    if (not isinstance(categories, tuple) or not categories
            or any(not _known_text(category) for category in categories)
            or len(set(categories)) != len(categories) or set(categories) != set(row.values)):
        reasons.append("complete_category_schema_required")
    if metadata.get("category_coverage") != "COMPLETE":
        reasons.append("category_coverage_unverified")
    if (metadata.get("source_weight_unit") not in ("PERCENT", "FRACTION")
            or metadata.get("source_weight_unit_status") != "VERIFIED"):
        reasons.append("source_weight_unit_unverified")
    if metadata.get("weights_normalization") != "NONE":
        reasons.append("normalized_or_unverified_weights_not_admitted")
    if any(unit != "FRACTION" for unit in row.units.values()):
        reasons.append("fraction_units_required")
    if _period_number(row) is None:
        reasons.append("monthly_period_unverified")
    elif row.effective_at is not None:
        try:
            zone = ZoneInfo(metadata.get("valuation_timezone", ""))
            actual = parse_timestamp(row.effective_at).astimezone(zone).date()
            year, month = map(int, metadata["period"].split("-"))
            if (actual.year, actual.month, actual.day) != (year, month, calendar.monthrange(year, month)[1]):
                reasons.append("effective_date_not_period_month_end")
        except (TypeError, ValueError, OverflowError, ZoneInfoNotFoundError):
            reasons.append("valuation_timezone_unverified")
    return reasons


def evaluate_allocation(cursor: ReplayCursor, previous_key: str,
                        current_key: str) -> AllocationEvaluation:
    """Screen two admitted consecutive monthly reports at the cursor cutoff.

    Observation values are explicit category fractions (units FRACTION). Source
    percent values must have undergone only exact division by 100, with original
    units preserved in metadata. Unknown rights, timing, category completeness,
    mapping or basis yield no numeric metrics or evidence IDs. No historical
    baseline or trade/cash-flow inference is part of AN-FND-004.
    """
    if not isinstance(cursor, ReplayCursor):
        return _abstain("replay_cursor_required")
    if not _known_text(previous_key) or not _known_text(current_key) or previous_key == current_key:
        return _abstain("distinct_period_evidence_keys_required")
    try:
        eligible = {row.observation_key: row for row in cursor.observations()}
    except AmbiguousRevision:
        return _abstain("eligible_revision_order_unresolved")
    if previous_key not in eligible or current_key not in eligible:
        return _abstain("selected_evidence_unavailable_at_cutoff")
    previous, current = eligible[previous_key], eligible[current_key]
    reasons = []
    if previous.fund != current.fund:
        reasons.append("fund_mismatch")
    if previous.source_id != current.source_id:
        reasons.append("allocation_source_mismatch")
    if any(previous.attributes.get(field) != current.attributes.get(field) for field in _SCOPE_FIELDS):
        reasons.append("scope_class_or_timezone_mismatch")
    for row in (previous, current):
        reason = _time_reason(row)
        if reason:
            reasons.append(reason)
        reasons.extend(_row_reasons(row))
    if previous.origin != current.origin or previous.rights_status != current.rights_status:
        reasons.append("origin_or_rights_mismatch")
    expected_rights = "SYNTHETIC" if previous.origin == "SYNTHETIC" else "APPROVED"
    if any(row.rights_status != expected_rights for row in (previous, current)):
        reasons.append("data_rights_unverified")
    if previous.attributes.get("allocation_basis") != current.attributes.get("allocation_basis"):
        reasons.append("allocation_basis_mismatch")
    if (previous.attributes.get("category_schema_id") != current.attributes.get("category_schema_id")
            or set(previous.values) != set(current.values)):
        reasons.append("category_schema_mismatch")
    earlier, later = _period_number(previous), _period_number(current)
    if earlier is None or later is None or later != earlier + 1:
        reasons.append("consecutive_monthly_periods_required")
    if reasons:
        return _abstain(*dict.fromkeys(reasons))
    metric = calculate_allocation_change(previous.values, current.values)
    if metric.reasons:
        return _abstain(*metric.reasons)
    evidence_ids = tuple(sorted(row.observation_key + "@" + row.source_version for row in (previous, current)))
    basis_reason = ("monthly_average_composition_not_month_end_holdings"
                    if current.attributes["allocation_basis"] == "MONTHLY_AVERAGE"
                    else "month_end_composition")
    return AllocationEvaluation("TRIGGERED" if metric.screen_crossing else "NOT_TRIGGERED",
                                ("allocation_composition_change_not_trade_turnover", basis_reason),
                                evidence_ids, metric)
