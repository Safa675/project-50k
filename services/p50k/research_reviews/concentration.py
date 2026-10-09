"""Descriptive concentration of an explicitly bounded reported securities subset.

No anomaly threshold, issuer inference, look-through, or fraud score is assigned.
Only synthetic fixtures may call this until the bounded protocol and runtime are
committed. Report selection and PDF extraction belong to the offline runner.
"""
from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime
from decimal import Context, Decimal, DivisionByZero, InvalidOperation, Overflow, ROUND_HALF_EVEN, localcontext
from fractions import Fraction
import re
from typing import Mapping, Sequence

from p50k.research_reviews.contracts import CUTOFF_AT, CUTOFF_DATE

CONCENTRATION_SCHEMA = "p50k.holding-concentration.v1"
SCOPE = "POSITIVE_IDENTIFIED_ISIN_SECURITIES"
WEIGHT_BASIS = "NORMALIZED_IDENTIFIED_SECURITIES_VALUE"
METRIC_FIELDS = ("top1_ratio", "top5_ratio", "top10_ratio", "hhi")
HASH = re.compile(r"[a-f0-9]{64}")
ISIN = re.compile(r"[A-Z]{2}[A-Z0-9]{10}")
SECURITY_TYPES = frozenset({"EQUITY", "BOND", "FUND", "OTHER_SECURITY"})


def ratio_string(value: Fraction) -> str:
    """Stable 128-digit ratios, isolated from every caller Decimal context."""
    with localcontext(Context(prec=128, rounding=ROUND_HALF_EVEN,
                              traps=[InvalidOperation, DivisionByZero, Overflow])):
        return str(Decimal(value.numerator) / Decimal(value.denominator))


def value_string(value: Fraction) -> str:
    """Preserve exact sums of finite decimal input values without rounding."""
    numerator, denominator = value.numerator, value.denominator
    twos = fives = 0
    while denominator % 2 == 0:
        twos += 1
        denominator //= 2
    while denominator % 5 == 0:
        fives += 1
        denominator //= 5
    if denominator != 1:
        raise ValueError("Position values must have a finite decimal expansion")
    scale = max(twos, fives)
    coefficient = numerator * 2 ** (scale - twos) * 5 ** (scale - fives)
    sign = "-" if coefficient < 0 else ""
    digits = str(abs(coefficient)).rjust(scale + 1, "0")
    return sign + (digits if scale == 0 else digits[:-scale] + "." + digits[-scale:])


def calculate_metrics(values: Mapping[str, Decimal]) -> dict:
    """Aggregate input identities first; normalized subset is the denominator."""
    if not values or any(not isinstance(value, Decimal) or not value.is_finite() or value <= 0
                         for value in values.values()):
        raise ValueError("Concentration requires finite positive security values")
    ordered = sorted(((identity, Fraction(value)) for identity, value in values.items()),
                     key=lambda item: (-item[1], item[0]))
    total = sum((value for _, value in ordered), Fraction())
    weights = {identity: value / total for identity, value in ordered}
    return {
        "subset_value": value_string(total), "position_count": len(ordered),
        "top1_ratio": ratio_string(sum((value for _, value in ordered[:1]), Fraction()) / total),
        "top5_ratio": ratio_string(sum((value for _, value in ordered[:5]), Fraction()) / total),
        "top10_ratio": ratio_string(sum((value for _, value in ordered[:10]), Fraction()) / total),
        "hhi": ratio_string(sum((weight * weight for weight in weights.values()), Fraction())),
        "ordered": [identity for identity, _ in ordered],
        "weights": {identity: ratio_string(weight) for identity, weight in weights.items()},
    }


def empty_concentration(*, reasons: Sequence[str] = ()) -> dict:
    return {
        "schema": CONCENTRATION_SCHEMA, "status": "UNAVAILABLE", "research_screen": "NOT_SCREENED",
        "production_status": "ABSTAINED", "scope": SCOPE, "weight_basis": WEIGHT_BASIS,
        "coverage_basis": "REPORTED_PORTFOLIO_VALUE", "issuer_aggregation": "NOT_AVAILABLE",
        "fund_lookthrough": "NOT_PERFORMED", "cadence": "MONTHLY", "report_period": None, "effective_date": None,
        "published_at": None, "age_days": None, "current_source_id": None, "input_refs": [],
        "missing_reasons": sorted(set(reasons)) or ["selected_monthly_holdings_missing"], "qualifications": [
            "historical_availability_unknown", "security_concentration_not_issuer_concentration",
            "normalized_identified_subset_not_whole_fund", "no_anomaly_threshold_registered"],
        "subset_value": None, "reported_portfolio_value": None, "portfolio_coverage_ratio": None,
        "portfolio_rounding_bound": None,
        "position_count": 0, **{field: None for field in METRIC_FIELDS}, "positions": [],
        "comparison": {
            "status": "UNAVAILABLE", "reason": "previous_report_unavailable", "previous_period": None,
            "previous_effective_date": None, "previous_published_at": None, "input_refs": [],
            **{f"previous_{field}": None for field in METRIC_FIELDS},
            **{f"{field}_delta": None for field in METRIC_FIELDS},
        },
    }


def _month_end(period: str) -> date:
    if re.fullmatch(r"\d{4}-(?:0[1-9]|1[0-2])", period) is None:
        raise ValueError("Holding reports require canonical monthly periods")
    year, month = map(int, period.split("-"))
    return date(year, month, monthrange(year, month)[1])


def _snapshot_finding(snapshot, source_id: str | None, reasons: Sequence[str]) -> dict:
    result = empty_concentration(reasons=reasons)
    if snapshot is None:
        if not result["missing_reasons"]:
            result["missing_reasons"] = ["selected_monthly_holdings_missing"]
        return result
    if not reasons:
        result["missing_reasons"] = []
    if source_id is None or HASH.fullmatch(source_id) is None:
        result["missing_reasons"].append("verified_pdf_source_reference_missing")
        return result
    effective = _month_end(snapshot.report_period)
    published = snapshot.published_at
    if not isinstance(published, datetime) or published.utcoffset() is None:
        result["missing_reasons"].append("publication_missing_or_invalid")
        return result
    if published > datetime.fromisoformat(CUTOFF_AT) or effective > date.fromisoformat(CUTOFF_DATE):
        result["missing_reasons"].append("selected_monthly_report_after_cutoff")
        return result
    result.update(report_period=snapshot.report_period, effective_date=effective.isoformat(),
                  published_at=published.isoformat(), age_days=(date.fromisoformat(CUTOFF_DATE) - effective).days,
                  current_source_id=source_id, input_refs=[source_id])
    if result["missing_reasons"]:
        return result
    result["qualifications"] = sorted(set(result["qualifications"] + list(snapshot.qualifications)))
    if not snapshot.reconciled:
        result["missing_reasons"] = sorted(set(result["missing_reasons"] + list(snapshot.problems) +
                                              ["selected_holdings_not_reconciled"]))
        return result
    portfolio = snapshot.portfolio_total
    if portfolio is None or not portfolio.value.is_finite() or portfolio.value <= 0:
        result["missing_reasons"].append("positive_reported_portfolio_value_missing")
        return result
    result["reported_portfolio_value"] = str(portfolio.value)
    if any(not row.position_value.value.is_finite() or row.position_value.value < 0 for row in snapshot.rows):
        result["missing_reasons"].append("negative_or_invalid_position_value")
        return result
    identified = [row for row in snapshot.rows if row.instrument_type in SECURITY_TYPES and
                  row.position_value.value > 0 and isinstance(row.isin, str) and ISIN.fullmatch(row.isin)]
    if not identified:
        result["missing_reasons"].append("no_positive_identified_security_values")
        return result
    values: dict[str, Fraction] = {}
    native_names: dict[str, set[str]] = {}
    source_rows: dict[str, list[dict]] = {}
    for row in identified:
        identity = row.isin
        values[identity] = values.get(identity, Fraction()) + Fraction(row.position_value.value)
        native_names.setdefault(identity, set()).add(row.native_name)
        source_rows.setdefault(identity, []).append({"source_id": source_id, "page": row.source_page,
                                                    "bbox": list(row.source_bbox),
                                                    "reported_value": str(row.position_value.value)})
    total = sum(values.values(), Fraction())
    rounding_bound = Fraction(10) ** portfolio.value.as_tuple().exponent / 2 + sum(
        (Fraction(10) ** row.position_value.value.as_tuple().exponent / 2 for row in snapshot.rows
         if row.instrument_type != "DERIVATIVE"), Fraction())
    if total > Fraction(portfolio.value) + rounding_bound:
        result["missing_reasons"].append("identified_subset_exceeds_reported_portfolio")
        return result
    result["portfolio_rounding_bound"] = value_string(rounding_bound)
    if total > Fraction(portfolio.value):
        result["qualifications"].append("coverage_exceeds_one_within_printed_rounding")
    metrics = calculate_metrics({identity: Decimal(value_string(value)) for identity, value in values.items()})
    result.update({field: metrics[field] for field in ("subset_value", "position_count", *METRIC_FIELDS)})
    result["portfolio_coverage_ratio"] = ratio_string(total / Fraction(portfolio.value))
    result["positions"] = [{"isin": identity, "native_name": " / ".join(sorted(native_names[identity])),
                             "value": value_string(values[identity]), "weight": metrics["weights"][identity],
                             "source_rows": sorted(source_rows[identity], key=lambda row: (row["page"], row["bbox"]))}
                            for identity in metrics["ordered"][:10]]
    has_unidentified = any(row.instrument_type in SECURITY_TYPES and row.position_value.value > 0 and
                           (not isinstance(row.isin, str) or ISIN.fullmatch(row.isin) is None)
                           for row in snapshot.rows)
    has_nonsecurity = any(row.instrument_type not in SECURITY_TYPES and
                          (row.position_value.value > 0 or row.instrument_type == "DERIVATIVE")
                          for row in snapshot.rows)
    partial_reasons = []
    if has_unidentified:
        partial_reasons.append("positive_security_without_identified_isin")
    if has_nonsecurity:
        partial_reasons.append("nonsecurity_or_derivative_positions_excluded")
    if any(row.instrument_type == "FUND" for row in identified):
        result["qualifications"].append("fund_holdings_without_lookthrough")
    result["status"] = "PARTIAL" if partial_reasons else "AVAILABLE"
    result["qualifications"] = sorted(set(result["qualifications"] + partial_reasons))
    result["missing_reasons"] = sorted(set(result["missing_reasons"]))
    return result


def concentration_finding(current=None, *, source_id: str | None = None, previous=None,
                          previous_source_id: str | None = None, missing_reasons: Sequence[str] = (),
                          previous_missing_reasons: Sequence[str] = (),
                          input_refs: Sequence[str] = (),
                          comparison_basis_verified: bool = False) -> dict:
    """Describe selected snapshots; selection never falls back after parse errors.

    The caller must establish compatible reported-value bases before enabling
    a historical delta. Complete securities coverage alone does not establish it.
    """
    result = _snapshot_finding(current, source_id, missing_reasons)
    prior = _snapshot_finding(previous, previous_source_id, previous_missing_reasons)
    comparison = result["comparison"]
    comparison.update(previous_period=prior["report_period"], previous_effective_date=prior["effective_date"],
                      previous_published_at=prior["published_at"], input_refs=prior["input_refs"])
    if any(not isinstance(reference, str) or HASH.fullmatch(reference) is None for reference in input_refs):
        raise ValueError("Concentration inputs require opaque source IDs")
    result["input_refs"] = sorted(set(result["input_refs"] + prior["input_refs"] + list(input_refs)))
    if prior["report_period"] is None:
        comparison["reason"] = "previous_report_unavailable"
    elif result["status"] != "AVAILABLE" or prior["status"] != "AVAILABLE":
        comparison["reason"] = "both_reports_require_complete_comparable_security_coverage"
    elif not comparison_basis_verified:
        comparison["reason"] = "report_value_basis_not_verified_comparable"
    elif prior["report_period"] >= result["report_period"]:
        comparison["reason"] = "previous_period_not_earlier"
    else:
        comparison.update(status="AVAILABLE", reason=None)
        for field in METRIC_FIELDS:
            comparison[f"previous_{field}"] = prior[field]
            comparison[f"{field}_delta"] = value_string(Fraction(Decimal(result[field])) - Fraction(Decimal(prior[field])))
    return result
