"""AN-FND-002: conditional endpoint residual, never reported cash flow.

The arithmetic helper is suitable for exploratory research. Production admission
requires an immutable ReplayCursor, matched monthly evidence and a separately
evidenced prior-only baseline check. Unknown metadata fails closed.
"""
from __future__ import annotations

import calendar
import re
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import (
    Context, Decimal, DecimalException, DivisionByZero, InvalidOperation, Overflow,
    ROUND_HALF_EVEN, Underflow, localcontext,
)
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from p50k.evidence_store import Observation, parse_timestamp
from p50k.replay import AmbiguousRevision, ReplayCursor

_CONTEXT = Context(prec=50, rounding=ROUND_HALF_EVEN, Emin=-999999, Emax=999999,
                   capitals=1, clamp=0, flags=[],
                   traps=[InvalidOperation, DivisionByZero, Overflow, Underflow])
_THRESHOLD = Decimal("0.10")
_SCOPE_FIELDS = ("fund_scope", "share_class", "currency", "valuation_timezone")
_ACTION_FIELDS = ("distribution_status", "unit_change_status", "merger_status")


@dataclass(frozen=True)
class EndpointChange:
    residual: Decimal | None
    rate: Decimal | None
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class BaselineCheck:
    """Reference a stored, prior-only check; this is not a baseline algorithm.

    Every evidence key must identify an eligible check record with matching
    baseline_config_id, baseline_status=PASSED, nonempty baseline_input_keys and
    exact baseline_input_versions. Inputs are replayed at the check's own receipt
    time. Both the check and its inputs precede the opening valuation period.
    """

    status: str = "UNVERIFIED"
    config_id: str | None = None
    evidence_keys: tuple[str, ...] = ()


@dataclass(frozen=True)
class FlowEvaluation:
    status: str
    reasons: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    metric: EndpointChange


def calculate_endpoint_change(previous_assets: Decimal | None, current_assets: Decimal | None,
                              previous_nav: Decimal | None, current_nav: Decimal | None) -> EndpointChange:
    """Compute F*=A1-A0*(P1/P0), then F*/A0, without estimating exact cash.

    Decimal values only; missing, invalid and unusable denominators stay missing.
    The local precision and rounding do not depend on the caller's context.
    """
    named = ("previous_assets", "current_assets", "previous_nav", "current_nav")
    values = (previous_assets, current_assets, previous_nav, current_nav)
    reasons = []
    for name, value in zip(named, values):
        if value is None:
            reasons.append(f"{name}_missing")
        elif not isinstance(value, Decimal):
            reasons.append(f"{name}_requires_decimal")
        elif not value.is_finite():
            reasons.append(f"{name}_nonfinite")
        elif (name != "current_assets" and value <= 0) or (name == "current_assets" and value < 0):
            reasons.append(f"{name}_invalid_sign")
    if reasons:
        return EndpointChange(None, None, tuple(reasons))
    try:
        with localcontext(_CONTEXT):
            residual = current_assets - previous_assets * (current_nav / previous_nav)
            rate = residual / previous_assets
    except DecimalException:
        return EndpointChange(None, None, ("arithmetic_not_representable",))
    return EndpointChange(residual, rate)


def _abstain(*reasons: str) -> FlowEvaluation:
    return FlowEvaluation("ABSTAINED", tuple(reasons), (), EndpointChange(None, None, tuple(reasons)))


def _known_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip()) and value.strip().upper() not in ("UNKNOWN", "UNVERIFIED")


def _time_reason(row: Observation) -> str | None:
    if row.availability_provenance not in ("OBSERVED", "ARCHIVE_VERIFIED") or any(
            getattr(row, field) is None for field in ("effective_at", "published_at", "available_at", "observed_at")):
        return "source_timing_unverified"
    effective, publication, availability, observation = (parse_timestamp(getattr(row, field)) for field in
                                                        ("effective_at", "published_at", "available_at", "observed_at"))
    if not effective <= publication <= availability <= observation:
        return "source_timing_inconsistent"
    return None


def _rights_reason(rows: tuple[Observation, ...]) -> str | None:
    if len({row.origin for row in rows}) != 1 or len({row.rights_status for row in rows}) != 1:
        return "origin_or_rights_mismatch"
    expected = "SYNTHETIC" if rows[0].origin == "SYNTHETIC" else "APPROVED"
    if any(row.rights_status != expected for row in rows):
        return "data_rights_unverified"
    return None


def _period_number(row: Observation) -> int | None:
    attributes = row.attributes
    period = attributes.get("period")
    if attributes.get("cadence") != "MONTHLY" or not isinstance(period, str) or not re.fullmatch(r"\d{4}-\d{2}", period):
        return None
    year, month = map(int, period.split("-"))
    if year < 1 or not 1 <= month <= 12:
        return None
    return year * 12 + month


def _period_reasons(row: Observation) -> list[str]:
    metadata = row.attributes
    reasons = []
    if any(not _known_text(metadata.get(field)) for field in _SCOPE_FIELDS):
        reasons.append("scope_class_currency_or_timezone_unknown")
    currency = metadata.get("currency")
    if not isinstance(currency, str) or not re.fullmatch(r"[A-Z]{3}", currency):
        reasons.append("currency_unverified")
    if row.units.get("total_value") != currency or row.units.get("nav") != f"{currency}/unit":
        reasons.append("currency_or_units_mismatch")
    if metadata.get("asset_basis") != "NET_ASSETS" or metadata.get("nav_basis") != "RAW_TRANSACTION_NAV":
        reasons.append("asset_or_nav_basis_unverified")
    if any(metadata.get(field) != "VERIFIED_NONE" for field in _ACTION_FIELDS):
        reasons.append("distribution_unit_change_or_merger_unresolved")
    period_number = _period_number(row)
    if period_number is None or metadata.get("valuation_basis") != "MONTH_END":
        reasons.append("monthly_valuation_unverified")
    elif row.effective_at is not None:
        try:
            timezone = ZoneInfo(metadata.get("valuation_timezone", ""))
            valuation_day = parse_timestamp(row.effective_at).astimezone(timezone).date()
            year, month = map(int, metadata["period"].split("-"))
            if (valuation_day.year, valuation_day.month, valuation_day.day) != (year, month, calendar.monthrange(year, month)[1]):
                reasons.append("valuation_not_period_month_end")
        except (TypeError, ValueError, OverflowError, ZoneInfoNotFoundError):
            reasons.append("valuation_timezone_unverified")
    for field in ("assets_effective_at", "nav_effective_at"):
        value = metadata.get(field)
        try:
            if value is None or row.effective_at is None or parse_timestamp(value) != parse_timestamp(row.effective_at):
                reasons.append("assets_and_nav_valuation_unmatched")
                break
        except ValueError:
            reasons.append("assets_and_nav_valuation_unmatched")
            break
    return reasons


def _baseline_reasons(baseline: BaselineCheck | None, cursor: ReplayCursor, eligible: dict[str, Observation],
                      previous: Observation, current: Observation) -> tuple[list[str], tuple[Observation, ...]]:
    if not isinstance(baseline, BaselineCheck) or baseline.status != "PASSED":
        return ["baseline_unverified"], ()
    if not _known_text(baseline.config_id) or not isinstance(baseline.evidence_keys, tuple) or not baseline.evidence_keys:
        return ["baseline_configuration_or_evidence_missing"], ()
    records = []
    for key in baseline.evidence_keys:
        if not _known_text(key) or key not in eligible:
            return ["baseline_evidence_unavailable_at_cutoff"], ()
        check = eligible[key]
        reason = _time_reason(check)
        if reason:
            return ["baseline_" + reason], ()
        if parse_timestamp(check.observed_at) > parse_timestamp(previous.effective_at):
            return ["baseline_check_was_not_fixed_before_opening_period"], ()
        if check.attributes.get("baseline_status") != "PASSED" or check.attributes.get("baseline_config_id") != baseline.config_id:
            return ["baseline_configuration_or_status_mismatch"], ()
        inputs = check.attributes.get("baseline_input_keys")
        if not isinstance(inputs, tuple) or not inputs or any(not _known_text(value) for value in inputs):
            return ["baseline_prior_inputs_missing"], ()
        versions = check.attributes.get("baseline_input_versions")
        if not isinstance(versions, Mapping) or set(versions) != set(inputs) or any(not _known_text(value) for value in versions.values()):
            return ["baseline_prior_input_versions_missing"], ()
        try:
            at_check = {row.observation_key: row for row in
                        ReplayCursor(cursor.store, cursor.bundle_id, check.observed_at).observations()}
        except AmbiguousRevision:
            return ["baseline_revision_order_unresolved"], ()
        selected = []
        for input_key in inputs:
            if not _known_text(input_key) or input_key not in at_check or input_key in (key, previous.observation_key, current.observation_key):
                return ["baseline_prior_inputs_unavailable_or_not_prior"], ()
            if at_check[input_key].source_version != versions[input_key]:
                return ["baseline_prior_input_version_mismatch"], ()
            selected.append(at_check[input_key])
        rows = (check, *selected)
        for row in rows:
            reason = _time_reason(row)
            if reason:
                return ["baseline_" + reason], ()
            if row.fund != previous.fund or any(row.attributes.get(field) != previous.attributes.get(field) for field in _SCOPE_FIELDS):
                return ["baseline_scope_mismatch"], ()
            reason = _rights_reason((previous, current, row))
            if reason:
                return ["baseline_" + reason], ()
            if parse_timestamp(row.effective_at) >= parse_timestamp(previous.effective_at):
                return ["baseline_uses_nonprior_evidence"], ()
        records.extend(rows)
    return [], tuple(records)


def evaluate_flow(cursor: ReplayCursor, previous_key: str, current_key: str,
                  *, baseline: BaselineCheck | None = None) -> FlowEvaluation:
    """Apply the fixed absolute 10% heuristic only to fully admitted evidence.

    Each selected Observation must contain total_value/net assets and raw nav,
    common currency units, matched field valuation instants and the documented
    scope, month-end, cadence and action metadata. The cursor is the only read
    path. Unknown or future evidence yields no numeric metrics or evidence IDs.
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
    if any(previous.attributes.get(field) != current.attributes.get(field) for field in _SCOPE_FIELDS):
        reasons.append("scope_class_currency_or_timezone_mismatch")
    for row in (previous, current):
        reason = _time_reason(row)
        if reason:
            reasons.append(reason)
        reasons.extend(_period_reasons(row))
    reason = _rights_reason((previous, current))
    if reason:
        reasons.append(reason)
    earlier, later = _period_number(previous), _period_number(current)
    if earlier is None or later is None or later != earlier + 1:
        reasons.append("consecutive_monthly_periods_required")
    if reasons:
        return _abstain(*dict.fromkeys(reasons))
    baseline_reasons, baseline_rows = _baseline_reasons(baseline, cursor, eligible, previous, current)
    if baseline_reasons:
        return _abstain(*baseline_reasons)
    metric = calculate_endpoint_change(previous.values.get("total_value"), current.values.get("total_value"),
                                       previous.values.get("nav"), current.values.get("nav"))
    if metric.reasons:
        return _abstain(*metric.reasons)
    triggered = metric.rate.copy_abs() >= _THRESHOLD
    evidence_ids = tuple(sorted({row.observation_key + "@" + row.source_version
                                 for row in (previous, current, *baseline_rows)}))
    return FlowEvaluation("TRIGGERED" if triggered else "NOT_TRIGGERED",
                          ("conditional_endpoint_residual_not_reported_cash",), evidence_ids, metric)
