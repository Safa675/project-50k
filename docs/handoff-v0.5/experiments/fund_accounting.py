#!/usr/bin/env python3
"""Offline fund-accounting research; synthetic counterexamples, not a live detector.

Run from the project root:
python experiments/fund_accounting.py --output research/engine_lab/fund_results.json

An exact Fraction ledger supplies ground truth independently of the Decimal
endpoint residual. No networking, third-party packages, production imports, or
empirical data. Assertions check accounting implications and non-identifiability.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from fractions import Fraction
from itertools import product
from pathlib import Path

PRECISION = 50
TOLERANCE = Decimal("1e-40")
COMMAND = "python experiments/fund_accounting.py --output research/engine_lab/fund_results.json"


def fraction(value: str | int | Fraction) -> Fraction:
    return value if isinstance(value, Fraction) else Fraction(str(value))


def decimal(value: str | int | Fraction | Decimal) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, Fraction):
        return Decimal(value.numerator) / Decimal(value.denominator)
    return Decimal(str(value))


def serialized(value):
    if isinstance(value, (Decimal, Fraction)):
        return str(value)
    if isinstance(value, dict):
        return {key: serialized(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [serialized(item) for item in value]
    return value


def require_positive(value: Decimal, name: str) -> None:
    if not value.is_finite() or value <= 0:
        raise ValueError(f"{name} must be finite and positive")


def endpoint_residual(a0, a1, p0, p1, split_factor="1") -> tuple[Decimal, Decimal]:
    """Endpoint unit-value residual; calling it actual cash requires more evidence."""
    with localcontext() as context:
        context.prec = PRECISION
        context.rounding = ROUND_HALF_EVEN
        a0, a1, p0, p1, split_factor = map(decimal, (a0, a1, p0, p1, split_factor))
        for name, value in (("opening_net_assets", a0), ("opening_NAV", p0),
                            ("closing_NAV", p1), ("split_factor", split_factor)):
            require_positive(value, name)
        if not a1.is_finite() or a1 < 0:
            raise ValueError("closing_net_assets must be finite and nonnegative")
        residual = a1 - a0 * split_factor * p1 / p0
        return residual, residual / a0


@dataclass
class Ledger:
    """Exact stylized single-class shares/cash lifecycle, not a price simulator."""
    units: Fraction = Fraction(100)
    nav: Fraction = Fraction(10)
    external_cash: Fraction = Fraction(0)
    cash_distributions: Fraction = Fraction(0)
    noncash_transfers: Fraction = Fraction(0)
    split_factor: Fraction = Fraction(1)
    events: list = field(default_factory=list)

    def __post_init__(self):
        self.opening_units = self.units
        self.opening_nav = self.nav
        self.opening_assets = self.units * self.nav

    @property
    def assets(self) -> Fraction:
        return self.units * self.nav

    def revalue(self, nav, reason="market_revaluation") -> None:
        nav = fraction(nav)
        assert nav > 0
        self.events.append({"event": reason, "old_NAV": self.nav, "new_NAV": nav})
        self.nav = nav

    def subscribe_or_redeem(self, cash) -> None:
        cash = fraction(cash)
        change = cash / self.nav
        assert self.units + change >= 0
        self.events.append({"event": "external_subscription_or_redemption", "cash": cash,
                            "transaction_NAV": self.nav, "unit_change": change})
        self.units += change
        self.external_cash += cash

    def distribute(self, per_unit, reinvest_fraction="0") -> None:
        per_unit, reinvest_fraction = map(fraction, (per_unit, reinvest_fraction))
        assert 0 <= per_unit < self.nav and 0 <= reinvest_fraction <= 1
        payout = self.units * per_unit
        self.nav -= per_unit
        reinvested = payout * reinvest_fraction
        self.units += reinvested / self.nav
        self.cash_distributions += payout - reinvested
        self.events.append({"event": "distribution", "per_pre_distribution_unit": per_unit,
                            "reinvestment_fraction": reinvest_fraction,
                            "cash_distribution": payout - reinvested,
                            "reinvested_distribution": reinvested, "ex_distribution_NAV": self.nav})

    def split(self, factor) -> None:
        factor = fraction(factor)
        assert factor > 0
        self.units *= factor
        self.nav /= factor
        self.split_factor *= factor
        self.events.append({"event": "unit_split", "new_units_per_old_unit": factor})

    def merger_transfer(self, assets) -> None:
        assets = fraction(assets)
        self.units += assets / self.nav
        self.noncash_transfers += assets
        self.events.append({"event": "noncash_merger_transfer", "net_assets_transferred": assets})


def case(name: str, ledger: Ledger, conclusion: str, **extras) -> dict:
    raw, rate = endpoint_residual(ledger.opening_assets, ledger.assets,
                                  ledger.opening_nav, ledger.nav)
    adjusted, _ = endpoint_residual(ledger.opening_assets, ledger.assets,
                                   ledger.opening_nav, ledger.nav, ledger.split_factor)
    exact_unit_residual = ledger.nav * (ledger.units - ledger.opening_units)
    assert abs(raw - decimal(exact_unit_residual)) <= TOLERANCE
    return {"id": name, "synthetic": True, "opening_net_assets": ledger.opening_assets,
            "closing_net_assets": ledger.assets, "opening_NAV": ledger.opening_nav,
            "closing_NAV": ledger.nav, "opening_units": ledger.opening_units,
            "closing_units": ledger.units, "raw_endpoint_residual": raw,
            "fraction_of_opening_net_assets": rate, "split_adjusted_residual": adjusted,
            "actual_external_subscription_minus_redemption_cash": ledger.external_cash,
            "cash_distributions_excluded_from_new_subscription_cash": ledger.cash_distributions,
            "noncash_transfers": ledger.noncash_transfers, "events": ledger.events,
            "conclusion": conclusion, **extras}


def numerical_cases() -> list[dict]:
    cases = []
    for nav, reason in (("12", "market_gain"), ("8", "market_loss"),
                        ("9.5", "fees_or_liability_revaluation")):
        ledger = Ledger()
        ledger.revalue(nav, reason)
        cases.append(case(f"no_flow_{reason}", ledger,
                          "Matched net-asset and NAV revaluation cancels; AUM change alone is not flow."))
        assert cases[-1]["raw_endpoint_residual"] == 0

    early = Ledger()
    early.subscribe_or_redeem("100")
    early.revalue("12")
    late = Ledger()
    late.revalue("12")
    late.subscribe_or_redeem("120")
    for name, ledger in (("early_100_cash", early), ("late_120_cash_same_endpoints", late)):
        cases.append(case(name, ledger,
                          "Same endpoint AUM/NAV and unit count, different actual cash; cash timing is unidentified."))
    assert early.assets == late.assets and early.units == late.units
    assert early.external_cash == 100 and late.external_cash == 120
    assert cases[-1]["raw_endpoint_residual"] == cases[-2]["raw_endpoint_residual"] == 120

    late100 = Ledger()
    late100.revalue("12")
    late100.subscribe_or_redeem("100")
    cases.append(case("late_100_cash", late100,
                      "Exact cash equality holds in the stylized end-period subscription case."))
    assert cases[-1]["raw_endpoint_residual"] == 100

    offset = Ledger()
    offset.subscribe_or_redeem("100")
    offset.revalue("12")
    offset.subscribe_or_redeem("-120")
    cases.append(case("offset_units_but_negative_cash", offset,
                      "Equal endpoint units yield zero residual while cash subscriptions minus redemptions is -20."))
    assert cases[-1]["raw_endpoint_residual"] == 0 and offset.external_cash == -20

    for reinvestment in ("0", "0.5", "1"):
        ledger = Ledger()
        ledger.distribute("1", reinvestment)
        record = case(f"distribution_reinvestment_{reinvestment}", ledger,
                      "Raw NAV counts reinvestment as unit growth; total-return residual counts cash distributions as outflow unless corrected.")
        total_return_factor = Fraction(1)  # One immediate distribution; no other return or trading.
        tr_residual = ledger.assets - ledger.opening_assets * total_return_factor
        corrected = tr_residual + ledger.cash_distributions
        assert corrected == 0 and ledger.external_cash == 0
        record.update({"known_total_return_factor": total_return_factor,
                       "uncorrected_total_return_residual": tr_residual,
                       "distribution_corrected_total_return_residual": corrected})
        cases.append(record)

    split = Ledger()
    split.split("2")
    cases.append(case("two_for_one_split", split,
                      "Raw residual 500 is mechanical; known split adjustment restores zero."))
    assert cases[-1]["raw_endpoint_residual"] == 500 and cases[-1]["split_adjusted_residual"] == 0

    merger = Ledger()
    merger.merger_transfer("500")
    cases.append(case("noncash_merger", merger,
                      "500 residual reflects transferred assets, not 500 new external subscription cash."))
    assert cases[-1]["raw_endpoint_residual"] == 500 and merger.external_cash == 0

    fx = Ledger()
    fx.revalue("12", "same_currency_FX_translation")
    cases.append(case("FX_same_reporting_currency", fx,
                      "FX translation cancels when AUM and NAV use the same currency and valuation."))
    wrongfx, _ = endpoint_residual("1000", "1200", "10", "10")
    cases.append({"id": "FX_mismatched_currencies", "synthetic": True,
                  "inputs": {"A0_TRY": "1000", "A1_TRY": "1200", "p0_USD": "10", "p1_USD": "10"},
                  "naive_residual": wrongfx, "actual_external_cash": "0",
                  "required_outcome": "ABSTAIN_CURRENCY_MISMATCH",
                  "conclusion": "AUM translated to TRY and unchanged USD NAV create a false 200 residual."})

    # Class A and B each start at 500, then A gains 20% and B loses 20%.
    class_mismatch, _ = endpoint_residual("1000", "1000", "10", "12")
    cases.append({"id": "whole_fund_AUM_one_class_NAV", "synthetic": True,
                  "class_A_assets": ["500", "600"], "class_B_assets": ["500", "400"],
                  "naive_residual": class_mismatch, "actual_external_cash": "0",
                  "required_outcome": "ABSTAIN_SCOPE_OR_CLASS_MISMATCH",
                  "conclusion": "Whole-fund AUM with one class return fabricates -200; oldest-class approximation is not an identity."})
    assert class_mismatch == -200
    # A redemption was recognized before the window; its payable settles inside it.
    opening_gross_assets, opening_liabilities = Fraction(1100), Fraction(100)
    closing_gross_assets, closing_liabilities = Fraction(1000), Fraction(0)
    opening_net = opening_gross_assets - opening_liabilities
    closing_net = closing_gross_assets - closing_liabilities
    settlement_residual, _ = endpoint_residual(opening_net, closing_net, "10", "10")
    assert opening_net == closing_net == 1000 and settlement_residual == 0
    cases.append({"id": "redemption_liability_settlement_not_new_unit_flow", "synthetic": True,
                  "opening_gross_assets": opening_gross_assets, "opening_liabilities": opening_liabilities,
                  "closing_gross_assets": closing_gross_assets, "closing_liabilities": closing_liabilities,
                  "net_assets_both": opening_net, "units_both": "100", "NAV_both": "10",
                  "raw_endpoint_residual": settlement_residual, "bank_cash_settlement": "-100",
                  "new_share_transaction_subscription_minus_redemption_in_window": "0",
                  "conclusion": "Paying a previously recognized redemption payable is bank cash outflow with no current-window net unit flow; target accounting basis must be explicit."})
    return cases


def investor_count_cases() -> list[dict]:
    records = []
    # Opening two holders: 10 and 90 units; first redeems all 10 units.
    for added_units, expected_cash in ((0, -100), (10, 0), (25, 150)):
        ledger = Ledger()
        ledger.subscribe_or_redeem("-100")
        if added_units:
            ledger.subscribe_or_redeem(str(added_units * 10))
        record = case(f"investors_2_to_1_cash_{expected_cash}", ledger,
                      "Identical investor-count decrease has negative, zero, or positive new subscription cash.",
                      opening_investors=2, closing_investors=1,
                      opening_holder_units={"departing": 10, "remaining": 90},
                      closing_holder_units={"remaining": 90 + added_units})
        assert ledger.external_cash == expected_cash
        records.append(record)
    return records


def allocation_distance(before, after) -> Decimal:
    before, after = [list(map(decimal, values)) for values in (before, after)]
    if len(before) != len(after) or not before:
        raise ValueError("Comparable nonempty category universe required")
    if any(not value.is_finite() or value < 0 for value in before + after):
        raise ValueError("Signed/nonfinite exposures require a different model")
    if sum(before) != 1 or sum(after) != 1:
        raise ValueError("Complete weights must sum to one; no silent normalization")
    return sum(abs(new - old) for old, new in zip(before, after)) / 2


def allocation_cases() -> list[dict]:
    before = [Fraction(1, 2), Fraction(1, 2)]
    after = [Fraction(2, 3), Fraction(1, 3)]
    # Fixed security quantities, first price doubles, second unchanged.
    tv = allocation_distance(before, after)
    assert abs(tv - Decimal(1) / 6) <= TOLERANCE
    unchanged_tv = allocation_distance(before, before)
    assert unchanged_tv == 0
    quantities = {"X": Fraction(500), "Y": Fraction(500)}
    buys = sells = Fraction(0)
    for sold, bought in (("X", "Y"), ("Y", "X")):
        quantities[sold] -= 500
        quantities[bought] += 500
        sells += 500
        buys += 500
    assert quantities == {"X": 500, "Y": 500} and buys == sells == 1000
    # Cash ledger controls: both end with cash 0, securities 900, net assets 900.
    for opening_cash, opening_security, security_sale in ((100, 900, 0), (0, 1000, 100)):
        closing_cash = opening_cash + security_sale - 100
        closing_security = opening_security - security_sale
        assert closing_cash == 0 and closing_security == 900
    return [
        {"id": "allocation_price_drift_no_trade", "synthetic": True,
         "opening_security_values": ["500", "500"], "closing_security_values": ["1000", "500"],
         "quantities_unchanged": True, "observed_weight_distance": tv,
         "actual_security_buys": "0", "actual_security_sells": "0",
         "conclusion": "TV=1/6 from revaluation alone; allocation distance is not trading turnover."},
        {"id": "allocation_same_endpoints_different_turnover", "synthetic": True,
         "observed_weight_distance_both_paths": unchanged_tv,
         "path_A": {"buys": "0", "sells": "0"},
         "path_B": {"events": ["sell all X for 500", "buy Y for 500", "sell added Y for 500", "buy X for 500"],
                    "buys": "1000", "sells": "1000", "opening_assets": "1000"},
         "conclusion": "Unchanged weights hide round-trip trading; both observed TV values are zero."},
        {"id": "redemption_same_fund_endpoints_different_security_sales", "synthetic": True,
         "opening_net_assets": "1000", "closing_net_assets": "900", "NAV_both": "10",
         "external_redemption_both": "100",
         "path_A": {"opening_cash": "100", "opening_security": "900", "security_sales": "0", "closing_cash": "0"},
         "path_B": {"opening_cash": "0", "opening_security": "1000", "security_sales": "100", "closing_cash": "0"},
         "conclusion": "Even known redemption cash does not identify security sales without cash/holdings/trade evidence."},
        {"id": "stale_holdings_current_exposure_unidentified", "synthetic": True,
         "report_valuation": "2026-09-01T17:00:00+03:00", "report_publication": "2026-09-03T09:00:00+03:00",
         "query_cutoff": "2026-10-01T12:00:00+03:00", "reported_X_weight_both": "0.5",
         "possible_current_X_weights": ["0.5", "0"],
         "conclusion": "The same last published report permits different current holdings; only historical disclosed exposure is observable."},
    ]


def eligible_snapshot(observations, cutoff) -> tuple[list[dict], list[str]]:
    """Small bitemporal fixture selector: valuation, publication and receipt all gated."""
    cutoff = datetime.fromisoformat(cutoff)
    eligible = []
    excluded = []
    for record in observations:
        times = [datetime.fromisoformat(record[key]) for key in
                 ("effective_at", "published_at", "available_at")]
        if any(value > cutoff for value in times):
            excluded.append(record["id"])
        else:
            eligible.append(record)
    latest = {}
    for record in eligible:
        key = (record["field"], record["effective_at"])
        if key not in latest or datetime.fromisoformat(record["available_at"]) > datetime.fromisoformat(latest[key]["available_at"]):
            latest[key] = record
    return sorted(latest.values(), key=lambda item: item["id"]), sorted(excluded)


def temporal_cases() -> list[dict]:
    observations = [
        {"id": "NAV_v1", "field": "NAV", "value": "10", "effective_at": "2026-09-01T17:00:00+03:00",
         "published_at": "2026-09-02T09:00:00+03:00", "available_at": "2026-09-02T09:05:00+03:00"},
        {"id": "AUM_v1", "field": "net_assets", "value": "1000", "effective_at": "2026-09-01T17:00:00+03:00",
         "published_at": "2026-09-02T10:00:00+03:00", "available_at": "2026-09-02T10:05:00+03:00"},
        {"id": "NAV_v2", "field": "NAV", "value": "9.8", "effective_at": "2026-09-01T17:00:00+03:00",
         "published_at": "2026-09-03T09:00:00+03:00", "available_at": "2026-09-03T09:05:00+03:00"},
    ]
    cases = []
    for cutoff, expected in (("2026-09-02T08:00:00+03:00", []),
                             ("2026-09-02T09:30:00+03:00", ["NAV_v1"]),
                             ("2026-09-02T10:30:00+03:00", ["AUM_v1", "NAV_v1"]),
                             ("2026-09-03T10:00:00+03:00", ["AUM_v1", "NAV_v2"])):
        included, excluded = eligible_snapshot(observations, cutoff)
        assert [item["id"] for item in included] == expected
        cases.append({"id": f"publication_cutoff_{cutoff}", "synthetic": True, "cutoff": cutoff,
                      "included": included, "excluded": excluded,
                      "ready_for_same_time_endpoint": len(included) == 2,
                      "conclusion": "Valuation date does not confer availability; later receipt/publication and revisions cannot alter a frozen earlier snapshot."})
    return cases


def metadata_gate(aum: dict, nav: dict) -> list[str]:
    """Executable narrow comparability guard, not a full source capability adapter."""
    reasons = []
    for field in ("scope_id", "share_class_id", "currency", "effective_at", "valuation_basis"):
        if not aum.get(field) or not nav.get(field) or aum[field] != nav[field]:
            reasons.append(f"MISMATCH_OR_UNKNOWN_{field.upper()}")
    if aum.get("asset_basis") != "net_assets":
        reasons.append("AUM_NOT_VERIFIED_NET_ASSETS")
    if nav.get("nav_kind") != "transaction_NAV_unadjusted":
        reasons.append("UNSUPPORTED_OR_UNKNOWN_NAV_CONVENTION")
    if not aum.get("corporate_actions_resolved") or not nav.get("corporate_actions_resolved"):
        reasons.append("CORPORATE_ACTIONS_UNRESOLVED")
    for record in (aum, nav):
        if record.get("missing_reason") is not None:
            reasons.append("MISSING_OR_PLACEHOLDER")
    return sorted(set(reasons))


def metadata_cases() -> list[dict]:
    base = {"scope_id": "SYNTHETIC-FUND-A", "share_class_id": "A", "currency": "TRY",
            "effective_at": "2026-09-01T17:00:00+03:00", "valuation_basis": "same_declared_net_valuation",
            "asset_basis": "net_assets", "nav_kind": "transaction_NAV_unadjusted",
            "corporate_actions_resolved": True, "missing_reason": None}
    assert metadata_gate(base, base) == []
    records = [{"id": "matched_endpoint_metadata", "synthetic": True,
                "outcome": "ELIGIBLE_FOR_RESIDUAL_ONLY", "reasons": [],
                "conclusion": "Comparable metadata allows arithmetic; it does not identify actual cash or grant data rights."}]
    for name, field, replacement in (("mismatched_effective_times", "effective_at", "2026-09-02T17:00:00+03:00"),
                                      ("mismatched_currency", "currency", "USD"),
                                      ("mismatched_class", "share_class_id", "B"),
                                      ("gross_AUM_not_net_assets", "asset_basis", "gross_assets"),
                                      ("total_return_series_not_raw_NAV", "nav_kind", "total_return_index"),
                                      ("unknown_corporate_actions", "corporate_actions_resolved", False),
                                      ("historical_AUM_placeholder", "missing_reason", "PROVIDER_DEFAULT_PLACEHOLDER")):
        changed = {**base, field: replacement}
        aum, nav = (changed, base) if field in ("asset_basis", "missing_reason") else (base, changed)
        reasons = metadata_gate(aum, nav)
        assert reasons
        records.append({"id": name, "synthetic": True, "changed_field": field,
                        "changed_value": replacement, "outcome": "ABSTAIN_INCOMPARABLE_ENDPOINTS", "reasons": reasons})
    return records


def investor_count_change(opening: int, closing: int, missing_reason=None) -> dict:
    if missing_reason is not None:
        return {"outcome": "ABSTAIN_MISSING_COUNT"}
    if opening < 0 or closing < 0:
        return {"outcome": "ABSTAIN_INVALID_COUNT"}
    absolute = closing - opening
    if opening == 0:
        return {"outcome": "ABSOLUTE_CHANGE_ONLY_PERCENT_UNDEFINED", "absolute_change": absolute}
    return {"outcome": "OBSERVED_COUNT_CHANGE_ONLY", "absolute_change": absolute,
            "fraction_change": Decimal(absolute) / opening}


def uncertainty_bounds(a0_range, a1_range, p0_range, p1_range) -> dict:
    """Conservative independent positive-input bounds, not a statistical interval."""
    ranges = [tuple(map(decimal, bounds)) for bounds in (a0_range, a1_range, p0_range, p1_range)]
    for bounds in ranges:
        require_positive(bounds[0], "interval_lower")
        require_positive(bounds[1], "interval_upper")
        if bounds[0] > bounds[1]:
            raise ValueError("interval_lower exceeds interval_upper")
    (a0lo, a0hi), (a1lo, a1hi), (p0lo, p0hi), (p1lo, p1hi) = ranges
    residual = (a1lo - a0hi * p1hi / p0lo, a1hi - a0lo * p1lo / p0hi)
    rate = (a1lo / a0hi - p1hi / p0lo, a1hi / a0lo - p1lo / p0hi)
    threshold = Decimal("0.1")  # Illustrative project threshold; not empirically validated.
    if rate[0] >= threshold:
        label = "ROBUST_POSITIVE_OVER_ILLUSTRATIVE_THRESHOLD"
    elif rate[1] <= -threshold:
        label = "ROBUST_NEGATIVE_OVER_ILLUSTRATIVE_THRESHOLD"
    elif rate[0] > -threshold and rate[1] < threshold:
        label = "ENTIRE_BOUND_BELOW_ILLUSTRATIVE_THRESHOLD"
    else:
        label = "THRESHOLD_CLASSIFICATION_UNRESOLVED"
    # Corner enumeration is an independent boundary check for these monotone formulas.
    for a0, a1, p0, p1 in product(*ranges):
        point, point_rate = endpoint_residual(a0, a1, p0, p1)
        assert residual[0] - TOLERANCE <= point <= residual[1] + TOLERANCE
        assert rate[0] - TOLERANCE <= point_rate <= rate[1] + TOLERANCE
    return {"input_bounds": {"opening_assets": ranges[0], "closing_assets": ranges[1],
                             "opening_NAV": ranges[2], "closing_NAV": ranges[3]},
            "residual_bound": residual, "fraction_of_opening_assets_bound": rate,
            "threshold": threshold, "classification": label, "corner_checks": 16,
            "interval_kind": "deterministic_input_bounds_not_confidence_interval"}


def sensitivity_cases() -> list[dict]:
    cases = []
    for name, end_assets in (("rounding_threshold_overlap", ("1095", "1105")),
                             ("robust_above_threshold", ("1145", "1155")),
                             ("robust_below_threshold", ("1035", "1045"))):
        record = uncertainty_bounds(("995", "1005"), end_assets,
                                    ("9.995", "10.005"), ("9.995", "10.005"))
        record.update({"id": name, "synthetic": True,
                       "bounds_origin": "Illustrative +/-5 asset currency units and +/-0.005 NAV; not measured provider error."})
        cases.append(record)
    assert cases[0]["classification"] == "THRESHOLD_CLASSIFICATION_UNRESOLVED"
    assert cases[1]["classification"] == "ROBUST_POSITIVE_OVER_ILLUSTRATIVE_THRESHOLD"
    assert cases[2]["classification"] == "ENTIRE_BOUND_BELOW_ILLUSTRATIVE_THRESHOLD"
    return cases


def invalid_input_cases() -> list[dict]:
    records = []
    for name, inputs in (("zero_opening_assets", ("0", "100", "10", "10")),
                         ("negative_opening_assets", ("-1", "100", "10", "10")),
                         ("zero_opening_NAV", ("100", "100", "0", "10")),
                         ("zero_closing_NAV", ("100", "100", "10", "0")),
                         ("negative_closing_assets", ("100", "-1", "10", "10")),
                         ("NaN_assets", ("100", "NaN", "10", "10")),
                         ("infinite_NAV", ("100", "100", "10", "Infinity"))):
        try:
            endpoint_residual(*inputs)
        except ValueError as error:
            records.append({"id": name, "synthetic": True, "inputs": inputs,
                            "outcome": "ABSTAIN_INVALID_INPUT", "reason": str(error)})
        else:
            raise AssertionError(f"Invalid case accepted: {name}")
    for name, values in (("signed_weights", ["1.2", "-0.2"]),
                         ("incomplete_weights", ["0.4", "0.4"])):
        try:
            allocation_distance(["0.5", "0.5"], values)
        except ValueError as error:
            records.append({"id": name, "synthetic": True, "inputs": values,
                            "outcome": "ABSTAIN_INCOMPARABLE_ALLOCATION", "reason": str(error)})
        else:
            raise AssertionError(f"Invalid allocation accepted: {name}")
    placeholder = investor_count_change(10, 0, "PROVIDER_DEFAULT_PLACEHOLDER")
    true_zero = investor_count_change(0, 10)
    assert placeholder["outcome"] == "ABSTAIN_MISSING_COUNT"
    assert true_zero == {"outcome": "ABSOLUTE_CHANGE_ONLY_PERCENT_UNDEFINED", "absolute_change": 10}
    records.extend([
        {"id": "zero_investor_placeholder", "synthetic": True, "opening_count": 10, "closing_count": 0,
         "missing_reason": "PROVIDER_DEFAULT_PLACEHOLDER", "outcome": placeholder["outcome"],
         "conclusion": "Provider default zero must not become a -100% investor change."},
        {"id": "observed_true_zero_investor_denominator", "synthetic": True,
         "opening_count": 0, "closing_count": 10, "missing_reason": None,
         "outcome": "ABSOLUTE_CHANGE_ONLY_PERCENT_UNDEFINED",
         "conclusion": "Observed zero differs from missing but still has no percentage denominator."},
    ])
    return records


def bounded_formula_checks() -> dict:
    checked = 0
    maximum_error = Decimal(0)
    for q0, p0, p1, cash, early, split_factor in product(
            (1, 10, 100), ("0.01", "1", "3", "10"), ("0.02", "2", "7", "12"),
            ("-0.001", "0", "0.1", "10"), (False, True), ("1", "2")):
        ledger = Ledger(fraction(q0), fraction(p0))
        if early:
            ledger.subscribe_or_redeem(cash)
        ledger.revalue(p1)
        if not early:
            ledger.subscribe_or_redeem(cash)
        ledger.split(split_factor)
        estimated, _ = endpoint_residual(ledger.opening_assets, ledger.assets,
                                         ledger.opening_nav, ledger.nav, ledger.split_factor)
        oracle = ledger.nav * (ledger.units - ledger.opening_units * ledger.split_factor)
        error = abs(estimated - decimal(oracle))
        maximum_error = max(maximum_error, error)
        assert error <= TOLERANCE
        if not early:
            assert abs(estimated - decimal(ledger.external_cash)) <= TOLERANCE
        checked += 1
    return {"checked_synthetic_combinations": checked, "maximum_absolute_decimal_vs_exact_fraction_error": maximum_error,
            "absolute_numeric_tolerance": TOLERANCE, "precision": PRECISION,
            "scope": "Finite authored grid; not exhaustive proof, provider tests, empirical accuracy, or threshold validation."}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    with localcontext() as context:
        context.prec = PRECISION
        context.rounding = ROUND_HALF_EVEN
        result = {"schema_version": "1.0", "lab": "fund_accounting", "evaluation_date": "2026-10-02",
                  "command": COMMAND, "synthetic_only": True, "live_data_accessed": False,
                  "scientific_status": "counterexamples_and_bounded_formula_checks_no_empirical_accuracy",
                  "accounting_cases": numerical_cases(), "investor_count_cases": investor_count_cases(),
                  "allocation_and_holdings_cases": allocation_cases(), "publication_cutoff_cases": temporal_cases(),
                  "endpoint_metadata_cases": metadata_cases(),
                  "uncertainty_cases": sensitivity_cases(), "invalid_and_missing_cases": invalid_input_cases(),
                  "bounded_formula_checks": bounded_formula_checks(),
                  "limitations": ["No actual fund observations, historical replay, NAV reconstruction, or trade-ledger validation.",
                                  "Exact cash cannot generally be recovered from two NAV/AUM endpoints, even with endpoint unit counts.",
                                  "Distribution examples use one immediate distribution with no other return; no general corporate-action processor.",
                                  "Cadence/rights/adjustment metadata are proposed gates; source-specific adapters are not implemented.",
                                  "Synthetic uncertainty bounds are illustrative and assume positive independent input bounds."]}
        result["experiment_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        payload = json.dumps(serialized(result), indent=2, ensure_ascii=False) + "\n"
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(payload, encoding="utf-8")
        named = sum(len(result[key]) for key in ("accounting_cases", "investor_count_cases",
                    "allocation_and_holdings_cases", "publication_cutoff_cases", "endpoint_metadata_cases", "uncertainty_cases", "invalid_and_missing_cases"))
        print(f"PASS: {named} named synthetic cases; {result['bounded_formula_checks']['checked_synthetic_combinations']} bounded accounting combinations; 48 uncertainty corner checks.")
        print("Observed: identical AUM/NAV endpoints give cash 100 or 120; zero residual can coexist with net cash -20.")
        print("Observed: raw split residual 500; distribution reinvestment residual 0/50/100; adjusted stylized controls zero.")
        print("Observed: investor count 2->1 gives net cash -100/0/+150; allocation TV can be positive with zero trades or zero with round trips.")
        print(f"Saved {arguments.output}")


if __name__ == "__main__":
    main()
