"""Small offline reference for proposed Project 50K behavior.

Synthetic/unit verification only. No market-data connections, model training,
forecasting, legal classification, delivery or empirically calibrated confidence.
Production implementations must also enforce provenance and field-level rights.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Context, Decimal, DecimalException, InvalidOperation, ROUND_HALF_EVEN, ROUND_HALF_UP, localcontext
import hashlib
import json
import math
import re
from statistics import median
from typing import Iterable, Mapping, Sequence


# Reference arithmetic is independent of callers' mutable Decimal contexts.
# This is computational precision, not a currency/settlement rounding policy.
_ARITHMETIC_CONTEXT = Context(prec=50, rounding=ROUND_HALF_EVEN)
_EVIDENCE_WEIGHTS = {
    "completeness": Decimal("0.35"), "freshness": Decimal("0.25"),
    "integrity": Decimal("0.25"), "corroboration": Decimal("0.15"),
}
_ORIGINS = ("LIVE", "DELAYED", "HISTORICAL_REPLAY", "SYNTHETIC")
_TIMESTAMP_PATTERN = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})",
    re.IGNORECASE,
)


class InvalidEvidence(ValueError):
    """The inputs must not support a publishable conclusion."""


@dataclass(frozen=True)
class SignalResult:
    outcome: str  # CANDIDATE, NOT_FLAGGED, ABSTAINED
    metric: float | None
    reason: str


def _finite(value: float) -> float:
    if isinstance(value, bool):
        raise InvalidEvidence("Boolean is not a numeric observation")
    try:
        out = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise InvalidEvidence("Expected finite number") from exc
    if not math.isfinite(out):
        raise InvalidEvidence("Missing or non-finite number")
    return out


def _decimal(value: str | Decimal) -> Decimal:
    if not isinstance(value, (str, Decimal)):
        raise InvalidEvidence("Financial amount must be a decimal string or Decimal")
    try:
        out = Decimal(value)
    except InvalidOperation as exc:
        raise InvalidEvidence("Invalid decimal") from exc
    if not out.is_finite():
        raise InvalidEvidence("Financial amount must be finite")
    return out


def parse_timestamp(value: str) -> datetime:
    """Read RFC 3339 instants with at most microsecond precision.

    Reject unknown offsets and unsupported precision rather than silently
    truncating a later instant into an earlier replay cutoff.
    """
    if (not isinstance(value, str) or not _TIMESTAMP_PATTERN.fullmatch(value)
            or value.endswith("-00:00")):
        raise InvalidEvidence("Expected RFC 3339 timestamp with a known offset and at most six fractional digits")
    try:
        dt = datetime.fromisoformat(value.upper().replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise InvalidEvidence("Invalid timestamp") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise InvalidEvidence("Timestamp must include UTC offset")
    return dt


def eligible_evidence(records: Iterable[Mapping[str, object]], cutoff: str) -> list[Mapping[str, object]]:
    """Temporal eligibility filter, not a revision selector or frozen snapshot.

    Availability, publication and supplied observation/effective instants must
    pass. Unknown or malformed row timestamps are excluded. Invalid cutoff
    raises. Callers still select immutable source versions, clear rights,
    capture configuration and prohibit live research.
    """
    limit = parse_timestamp(cutoff)
    out = []
    for record in records:
        if not isinstance(record, Mapping):
            continue
        if record.get("availability_provenance") not in ("OBSERVED", "ARCHIVE_VERIFIED"):
            continue
        try:
            if parse_timestamp(record.get("available_at")) > limit:
                continue
            if any(parse_timestamp(record[key]) > limit
                   for key in ("published_at", "observed_at", "effective_at")
                   if record.get(key) is not None):
                continue
        except InvalidEvidence:
            continue
        out.append(record)
    return out


def normalize_borsapy_fund_history(row: Mapping[str, object]) -> dict[str, object]:
    """Applies ONLY to the code-inspected price-history provider path.

    Legacy FundSize/Investors columns are placeholders there, even if an older
    consumer expects numbers. Another provider must have a separate adapter.
    """
    return {"Price": row.get("Price"), "FundSize": None, "Investors": None,
            "history_capability": "PRICE_ONLY", "quality_reason": "provider_history_placeholders"}


def relative_volume(current: float, prior_same_slots: Sequence[float], *, final_bar: bool,
                    same_feed: bool, min_observations: int = 20, threshold: float = 3.0) -> SignalResult:
    """Prior sessions’ same completed time slot, supplied by a provenance layer."""
    _detector_configuration(min_observations, threshold)
    if final_bar is not True or same_feed is not True:
        return SignalResult("ABSTAINED", None, "unfinished_bar_or_mixed_feed")
    if len(prior_same_slots) < min_observations:
        return SignalResult("ABSTAINED", None, "insufficient_baseline")
    try:
        x = _finite(current)
        history = [_finite(v) for v in prior_same_slots]
    except InvalidEvidence:
        return SignalResult("ABSTAINED", None, "invalid_numeric_input")
    if x < 0 or any(v < 0 for v in history):
        return SignalResult("ABSTAINED", None, "negative_volume")
    base = median(history)
    if not math.isfinite(base):
        return SignalResult("ABSTAINED", None, "nonfinite_derived_metric")
    if base <= 0:
        return SignalResult("ABSTAINED", None, "nonpositive_baseline")
    ratio = x / base
    if not math.isfinite(ratio):
        return SignalResult("ABSTAINED", None, "nonfinite_derived_metric")
    return SignalResult("CANDIDATE" if ratio >= threshold else "NOT_FLAGGED", ratio, "same_slot_median_ratio")


def robust_return_signal(current_log_return: float, prior_log_returns: Sequence[float], *,
                         adjustment_verified: bool, min_observations: int = 20,
                         threshold: float = 4.0, absolute_return_floor: float = 0.01) -> SignalResult:
    """Robust unusualness; this z-score is not a probability or fraud score."""
    _detector_configuration(min_observations, threshold, absolute_return_floor)
    if adjustment_verified is not True:
        return SignalResult("ABSTAINED", None, "unverified_corporate_action_adjustment")
    if len(prior_log_returns) < min_observations:
        return SignalResult("ABSTAINED", None, "insufficient_baseline")
    try:
        x = _finite(current_log_return)
        history = [_finite(v) for v in prior_log_returns]
    except InvalidEvidence:
        return SignalResult("ABSTAINED", None, "invalid_numeric_input")
    center = median(history)
    mad = median([abs(v - center) for v in history])
    if not math.isfinite(center) or not math.isfinite(mad):
        return SignalResult("ABSTAINED", None, "nonfinite_derived_metric")
    if mad <= 0:
        return SignalResult("ABSTAINED", None, "zero_mad")
    z = abs(x - center) / (1.4826 * mad)
    if not math.isfinite(z):
        return SignalResult("ABSTAINED", None, "nonfinite_derived_metric")
    try:
        raw_move = abs(math.expm1(x))
    except OverflowError:
        return SignalResult("ABSTAINED", None, "implausible_log_return")
    flag = z >= threshold and raw_move >= absolute_return_floor
    return SignalResult("CANDIDATE" if flag else "NOT_FLAGGED", z, "robust_log_return_deviation")


def _detector_configuration(min_observations: int, threshold: float,
                            absolute_return_floor: float = 0) -> None:
    """Configuration failures must not masquerade as a normal observation."""
    try:
        valid = (type(min_observations) is int and min_observations >= 2
                 and isinstance(threshold, (int, float, Decimal))
                 and isinstance(absolute_return_floor, (int, float, Decimal))
                 and _finite(threshold) > 0 and _finite(absolute_return_floor) >= 0)
    except InvalidEvidence as exc:
        raise ValueError("Invalid detector configuration") from exc
    if not valid:
        raise ValueError("Invalid detector configuration")


def estimated_fund_flow(aum_previous: str, aum_current: str, nav_previous: str,
                        nav_current: str, *, dates_aligned: bool,
                        distribution_adjustment_verified: bool) -> Decimal:
    """Approximate net flow; never exact/redemption-order history."""
    if dates_aligned is not True or distribution_adjustment_verified is not True:
        raise InvalidEvidence("Unaligned dates or unknown distributions")
    a0, a1, p0, p1 = map(_decimal, (aum_previous, aum_current, nav_previous, nav_current))
    if a0 <= 0 or a1 < 0 or p0 <= 0 or p1 <= 0:
        raise InvalidEvidence("AUM/NAV invalid")
    try:
        with localcontext(_ARITHMETIC_CONTEXT):
            # Multiply before dividing to avoid avoidable repeating-ratio error.
            return a1 - (a0 * p1 / p0)
    except DecimalException as exc:
        raise InvalidEvidence("Fund calculation exceeds reference decimal range") from exc


def allocation_distance(previous: Mapping[str, str], current: Mapping[str, str],
                        *, complete_category_map: bool) -> Decimal:
    """Total variation for verified nonnegative percent vectors only.

    Inputs are percentages summing to 100 within 0.1 percentage point.
    Output is a fraction in [0,1]. Derivatives/negative weights require another
    reviewed model and must not be silently renormalized.
    """
    if complete_category_map is not True or not previous or not current:
        raise InvalidEvidence("Allocation categories incomplete")
    if any(not isinstance(k, str) or not k.strip() for k in set(previous) | set(current)):
        raise InvalidEvidence("Allocation category IDs must be nonempty strings")
    a = {k: _decimal(v) for k, v in previous.items()}
    b = {k: _decimal(v) for k, v in current.items()}
    if any(v < 0 for v in list(a.values()) + list(b.values())):
        raise InvalidEvidence("Signed exposure not a probability vector")
    try:
        with localcontext(_ARITHMETIC_CONTEXT):
            if any(abs(sum(v[k] for k in sorted(v)) - Decimal(100)) > Decimal('0.1') for v in (a, b)):
                raise InvalidEvidence("Weights not complete percentages")
            distance = sum(abs(a.get(k, Decimal(0)) - b.get(k, Decimal(0)))
                           for k in sorted(set(a) | set(b))) / Decimal(200)
            if not distance.is_finite() or not 0 <= distance <= 1:
                raise InvalidEvidence("Rounded allocation totals cannot support a distance in [0,1]")
            return distance
    except DecimalException as exc:
        raise InvalidEvidence("Allocation calculation exceeds reference decimal range") from exc


def evidence_strength(components: Mapping[str, float], *, hard_gates_pass: bool) -> dict[str, object]:
    if type(hard_gates_pass) is not bool:
        raise InvalidEvidence("Hard gate result must be an explicit boolean")
    if set(components) != set(_EVIDENCE_WEIGHTS):
        raise InvalidEvidence("Expected exactly the four evidence components")
    numbers = {k: _finite(v) for k, v in components.items()}
    decimals = {k: _decimal(str(v)) for k, v in components.items()}
    if any(v < 0 or v > 1 for v in decimals.values()):
        raise InvalidEvidence("Evidence components must be in [0,1]")
    with localcontext(_ARITHMETIC_CONTEXT):
        score = int((100 * sum(decimals[k] * w for k, w in _EVIDENCE_WEIGHTS.items()))
                    .quantize(Decimal("1"), rounding=ROUND_HALF_UP)) if hard_gates_pass else None
    return {"mode": "HEURISTIC_EVIDENCE" if hard_gates_pass else "UNAVAILABLE",
            "evidence_score": score, "calibrated_probability": None,
            "method_version": "evidence-strength-v1", "components": numbers,
            "reasons": [] if hard_gates_pass else ["publication_hard_gate_failed"]}


def email_eligible(*, origin: str, severity: str, follows_asset: bool,
                   personal_opt_in: bool, global_opt_in: bool, global_release_approved: bool,
                   current_subscription: bool, evidence_valid: bool, external_sending_enabled: bool,
                   already_sent: bool = False, under_daily_cap: bool = True,
                   evidence_origins: Sequence[str] | None = None, dry_run: bool = True) -> bool:
    """Immediate email only. Digest and in-app policies are separate.

    Fail closed for unknown modes/severities, replay/synthetic, stale opt-in,
    failed evidence, missing/mixed non-live evidence origins, dry-run or disabled
    sending. Positive authorization flags must be actual booleans. This helper
    sends nothing and does not validate evidence truth, rights, outbox or roles.
    """
    if origin not in ("LIVE", "DELAYED") or severity not in ("MEDIUM", "HIGH", "CRITICAL"):
        return False
    flags = (follows_asset, personal_opt_in, global_opt_in, global_release_approved,
             current_subscription, evidence_valid, external_sending_enabled,
             already_sent, under_daily_cap, dry_run)
    if any(type(value) is not bool for value in flags):
        return False
    if (not isinstance(evidence_origins, (list, tuple)) or not evidence_origins
            or any(value not in ("LIVE", "DELAYED") for value in evidence_origins)):
        return False
    if not all((current_subscription, evidence_valid, external_sending_enabled, under_daily_cap)) or already_sent or dry_run:
        return False
    if follows_asset:
        return personal_opt_in and severity in {"HIGH", "CRITICAL"}
    return global_opt_in and severity == "CRITICAL" and global_release_approved


def delivery_key(*, user_id: str, event_id: str, channel: str,
                 origin: str, delivery_class: str, material_update_id: str | None = None) -> str:
    """Stable key; an explanation rewrite/retry must not create another send."""
    if any(not isinstance(value, str) or not value.strip() for value in (user_id, event_id)):
        raise InvalidEvidence("Delivery requires nonempty user and event IDs")
    if (channel not in ("EMAIL", "IN_APP") or origin not in _ORIGINS
            or delivery_class not in ("PERSONAL", "GLOBAL_CRITICAL", "DIGEST", "UPDATE", "CORRECTION")):
        raise InvalidEvidence("Unknown delivery channel, origin or class")
    if delivery_class in ("UPDATE", "CORRECTION") and (
            not isinstance(material_update_id, str) or not material_update_id.strip()):
        raise InvalidEvidence("Material changes need a stable approved update ID")
    if delivery_class not in ("UPDATE", "CORRECTION") and material_update_id is not None:
        raise InvalidEvidence("Initial delivery must not vary with an explanation rewrite ID")
    payload = [user_id, event_id, channel, origin, delivery_class, material_update_id]
    return hashlib.sha256(json.dumps(payload, separators=(',', ':')).encode()).hexdigest()
