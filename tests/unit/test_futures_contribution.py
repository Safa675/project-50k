"""Synthetic exact-contract P&L, expiry boundaries, and unavailable inputs."""
from __future__ import annotations

import unittest
from copy import deepcopy
from dataclasses import replace
from datetime import date, datetime, timedelta
from decimal import Decimal, Inexact, Rounded, ROUND_DOWN, localcontext

from p50k.analytics.futures_contribution import (
    ContractSpecification, FuturesPosition, SettlementObservation,
    calculate_futures_contribution,
)


D = Decimal
BASE = date(2025, 11, 4)
END = date(2025, 11, 5)
EXPIRY = date(2025, 11, 28)


def specification(**changes):
    spec = ContractSpecification("F_SYNTH1125", D(10), EXPIRY, "CASH", "TRY",
                                 "INDEX_POINTS", "TRY_PER_INDEX_POINT")
    return replace(spec, **changes)


def position(**changes):
    return replace(FuturesPosition(specification(), "LONG", D(100)), **changes)


def marks(spec=None, *, first=D(20), last=D(22), last_date=END):
    spec = spec or specification()
    return {spec.contract_id: {
        BASE: SettlementObservation(spec, BASE, first),
        last_date: SettlementObservation(spec, last_date, last),
    }}


def calculate(positions=None, **changes):
    arguments = dict(base_date=BASE, endpoint_date=END,
                     fund_net_assets=D(100000), settlements=marks())
    arguments.update(changes)
    return calculate_futures_contribution(
        (position(),) if positions is None else positions, **arguments)


class FuturesContributionTests(unittest.TestCase):
    def test_long_contracts_times_multiplier_times_price_difference(self):
        result = calculate()
        self.assertEqual(result.availability, "AVAILABLE")
        self.assertEqual(result.pnl_try, D(2000))
        self.assertEqual(result.contribution, D("0.02"))
        self.assertEqual(result.items[0].mark_date, END)
        self.assertEqual(result.prices_required, 2)
        self.assertEqual(result.prices_present, 2)

    def test_short_contracts_invert_gain_and_loss(self):
        result = calculate((position(side="SHORT"),))
        self.assertEqual(result.pnl_try, D(-2000))
        fallen = calculate((position(side="SHORT"),), settlements=marks(last=D(18)))
        self.assertEqual(fallen.pnl_try, D(2000))

    def test_net_opposite_sides_retains_both_items(self):
        result = calculate((position(), position(side="SHORT", contracts=D(60))))
        self.assertEqual(result.pnl_try, D(800))
        self.assertEqual(len(result.items), 2)
        self.assertEqual([item.side for item in result.items], ["LONG", "SHORT"])
        self.assertEqual(result.prices_required, 2)

    def test_duplicate_side_aggregates_without_losing_source_count(self):
        result = calculate((position(contracts=D(30)), position(contracts=D(70))))
        self.assertEqual(result.pnl_try, D(2000))
        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.items[0].contracts, D(100))
        self.assertEqual(result.items[0].source_row_count, 2)

    def test_duplicate_identity_with_changed_spec_is_unavailable(self):
        for field, value in (("multiplier", D(20)), ("expiry", END),
                             ("settlement_type", "PHYSICAL")):
            with self.subTest(field=field):
                result = calculate((position(), position(spec=specification(**{field: value}))))
                self.assertEqual(result.availability, "UNAVAILABLE")
                self.assertIn("inconsistent_duplicate_contract_specification:F_SYNTH1125", result.reasons)

    def test_two_exact_contract_identities_are_not_mixed(self):
        other = specification(contract_id="F_OTHER1125", multiplier=D(5))
        quotes = marks()
        quotes.update(marks(other, last=D(18)))
        result = calculate((position(), position(spec=other, side="SHORT", contracts=D(10))),
                           settlements=quotes)
        self.assertEqual(result.pnl_try, D(2100))
        self.assertEqual(result.prices_required, 4)

    def test_share_quote_times_shares_per_contract_is_try(self):
        spec = specification(multiplier=D(100), price_unit="TRY_PER_SHARE",
                             multiplier_unit="SHARES_PER_CONTRACT")
        result = calculate((position(spec=spec, contracts=D(2)),), settlements=marks(spec))
        self.assertEqual(result.pnl_try, D(400))

    def test_mismatched_units_are_unavailable(self):
        spec = specification(price_unit="TRY_PER_SHARE")
        result = calculate((position(spec=spec),), settlements=marks(spec))
        self.assertEqual(result.availability, "UNAVAILABLE")
        self.assertTrue(any("matching_quote_and_multiplier_units_required" in r for r in result.reasons))

    def test_unknown_units_are_not_assumed(self):
        spec = specification(price_unit="UNKNOWN", multiplier_unit="UNKNOWN")
        result = calculate((position(spec=spec),), settlements=marks(spec))
        self.assertEqual(result.availability, "UNAVAILABLE")

    def test_currency_conversion_is_not_inferred(self):
        spec = specification(currency="USD")
        result = calculate((position(spec=spec),), settlements=marks(spec))
        self.assertEqual(result.availability, "UNAVAILABLE")
        self.assertTrue(any("currency_must_be_try" in r for r in result.reasons))

    def test_zero_quantity_requires_prices(self):
        result = calculate((position(contracts=D(0)),), settlements={})
        self.assertEqual(result.availability, "UNAVAILABLE")
        self.assertEqual(result.prices_required, 2)
        self.assertIsNone(result.contribution)
        good = calculate((position(contracts=D(0)),))
        self.assertEqual(good.pnl_try, D(0))

    def test_one_missing_contract_abstains_from_entire_sum(self):
        other = specification(contract_id="F_OTHER1125")
        result = calculate((position(), position(spec=other)), settlements=marks())
        self.assertEqual(result.availability, "UNAVAILABLE")
        self.assertIsNone(result.pnl_try)
        self.assertIsNone(result.contribution)
        self.assertEqual(result.items, ())

    def test_expired_strictly_before_baseline_excluded_without_quotes(self):
        old = specification(expiry=BASE - timedelta(days=1), settlement_type="PHYSICAL")
        result = calculate((position(spec=old),), settlements={})
        self.assertEqual(result.availability, "AVAILABLE")
        self.assertEqual(result.pnl_try, D(0))
        self.assertEqual(result.prices_required, 0)
        self.assertEqual(result.excluded[0].reason, "expired_strictly_before_baseline_no_roll_assumed")

    def test_expired_identity_cannot_substitute_rolled_contract_quotes(self):
        old = specification(expiry=BASE - timedelta(days=1))
        rolled = specification(contract_id="F_SYNTH1225")
        result = calculate((position(spec=old),), settlements=marks(rolled, last=D(999)))
        self.assertEqual(result.pnl_try, D(0))
        self.assertEqual(result.items, ())

    def test_cash_expiry_freezes_contribution_at_exact_expiry_mark(self):
        quotes = marks(last_date=EXPIRY, last=D(24))
        quotes["F_SYNTH1125"][EXPIRY + timedelta(days=1)] = SettlementObservation(
            specification(), EXPIRY + timedelta(days=1), D(999))
        result = calculate(endpoint_date=EXPIRY + timedelta(days=10), settlements=quotes)
        self.assertEqual(result.pnl_try, D(4000))
        self.assertEqual(result.items[0].mark_date, EXPIRY)

    def test_cash_expiry_requires_expiry_day_not_nearby_quote(self):
        quotes = marks(last_date=EXPIRY + timedelta(days=1), last=D(24))
        result = calculate(endpoint_date=EXPIRY + timedelta(days=10), settlements=quotes)
        self.assertEqual(result.availability, "UNAVAILABLE")
        self.assertIn("exact_settlement_missing:F_SYNTH1125:2025-11-28", result.reasons)

    def test_cash_contract_expiring_on_baseline_has_zero_with_one_mark(self):
        spec = specification(expiry=BASE)
        quote = {spec.contract_id: {BASE: SettlementObservation(spec, BASE, D(20))}}
        result = calculate((position(spec=spec),), settlements=quote)
        self.assertEqual(result.pnl_try, D(0))
        self.assertEqual(result.prices_required, 1)
        self.assertEqual(result.items[0].mark_date, BASE)

    def test_physical_expiry_inside_window_unsupported(self):
        spec = specification(settlement_type="PHYSICAL", expiry=END)
        result = calculate((position(spec=spec),), settlements=marks(spec))
        self.assertEqual(result.availability, "UNAVAILABLE")
        self.assertIn("physical_delivery_inside_window_unsupported:F_SYNTH1125", result.reasons)

    def test_physical_contract_before_expiry_is_supported(self):
        spec = specification(settlement_type="PHYSICAL")
        result = calculate((position(spec=spec),), settlements=marks(spec))
        self.assertEqual(result.pnl_try, D(2000))

    def test_metadata_changes_in_required_settlement_are_unavailable(self):
        for field, value in (("multiplier", D(20)), ("expiry", END),
                             ("settlement_type", "PHYSICAL"), ("currency", "USD"),
                             ("contract_id", "F_OTHER1125"), ("price_unit", "TRY_PER_SHARE")):
            with self.subTest(field=field):
                quotes = marks()
                quotes["F_SYNTH1125"][END] = SettlementObservation(specification(**{field: value}), END, D(22))
                result = calculate(settlements=quotes)
                self.assertEqual(result.availability, "UNAVAILABLE")
                self.assertIn("settlement_contract_specification_changed:F_SYNTH1125:2025-11-05", result.reasons)

    def test_baseline_metadata_change_is_unavailable(self):
        quotes = marks()
        quotes["F_SYNTH1125"][BASE] = SettlementObservation(specification(multiplier=D(20)), BASE, D(20))
        self.assertEqual(calculate(settlements=quotes).availability, "UNAVAILABLE")

    def test_date_field_must_match_mapping_key(self):
        quotes = marks()
        quotes["F_SYNTH1125"][END] = SettlementObservation(specification(), END + timedelta(days=1), D(22))
        self.assertEqual(calculate(settlements=quotes).availability, "UNAVAILABLE")

    def test_all_positive_price_requirements_are_strict(self):
        for value in (None, D(0), D(-1), D("NaN"), D("sNaN"), D("Infinity"), 22.0):
            with self.subTest(value=str(value)):
                self.assertEqual(calculate(settlements=marks(last=value)).availability, "UNAVAILABLE")

    def test_invalid_contract_quantity_never_guessed(self):
        for value in (None, D(-1), D("NaN"), D("Infinity"), 100.0):
            with self.subTest(value=str(value)):
                self.assertEqual(calculate((position(contracts=value),)).availability, "UNAVAILABLE")

    def test_multiplier_nav_and_side_require_explicit_valid_values(self):
        for value in (None, D(0), D(-1), D("NaN"), D("Infinity"), 10.0):
            with self.subTest(value=str(value)):
                self.assertEqual(calculate(fund_net_assets=value).availability, "UNAVAILABLE")
                self.assertEqual(calculate((position(spec=specification(multiplier=value)),)).availability, "UNAVAILABLE")
        for side in ("UNKNOWN", "long", "", None):
            self.assertEqual(calculate((position(side=side),)).availability, "UNAVAILABLE")

    def test_empty_report_does_not_establish_actual_zero_pnl(self):
        result = calculate(())
        self.assertEqual(result.availability, "UNAVAILABLE")
        self.assertIsNone(result.pnl_try)

    def test_continuous_or_alias_contract_identities_are_rejected(self):
        for identity in ("F_SYNTH", "F_SYNTH_NEAR", "F_SYNTH1325", "F_SYNTH1125 ",
                         "f_SYNTH1125", "UNKNOWN", None):
            with self.subTest(identity=identity):
                spec = specification(contract_id=identity)
                self.assertEqual(calculate((position(spec=spec),)).availability, "UNAVAILABLE")

    def test_explicit_actual_expiry_must_agree_with_identity_month(self):
        for expiry in (date(2025, 12, 1), date(2026, 11, 28)):
            spec = specification(expiry=expiry)
            result = calculate((position(spec=spec),))
            self.assertEqual(result.availability, "UNAVAILABLE")
            self.assertTrue(any("contract_maturity_month_disagrees" in r for r in result.reasons))

    def test_invalid_inputs_and_unordered_dates_unavailable(self):
        for positions in (("bad",), "bad", None):
            self.assertEqual(calculate_futures_contribution(positions, base_date=BASE, endpoint_date=END,
                fund_net_assets=D(100000), settlements=marks()).availability, "UNAVAILABLE")
        for arguments in (dict(endpoint_date=BASE - timedelta(days=1)),
                          dict(base_date=datetime(2025, 11, 4)), dict(settlements=None)):
            self.assertEqual(calculate(**arguments).availability, "UNAVAILABLE")

    def test_same_day_baseline_is_zero_not_missing(self):
        result = calculate(endpoint_date=BASE)
        self.assertEqual(result.pnl_try, D(0))
        self.assertEqual(result.prices_required, 1)

    def test_future_prices_and_spec_changes_leave_earlier_result_unchanged(self):
        quotes = marks()
        before = calculate(settlements=quotes)
        future = END + timedelta(days=1)
        quotes["F_SYNTH1125"][future] = SettlementObservation(
            specification(multiplier=D(999), expiry=BASE), future, D("NaN"))
        quotes["F_FUTURE1125"] = {future: SettlementObservation(specification(), future, D(999))}
        self.assertEqual(calculate(settlements=quotes), before)

    def test_post_expiry_horizon_and_prices_do_not_change_frozen_pnl(self):
        quotes = marks(last_date=EXPIRY, last=D(24))
        first = calculate(endpoint_date=EXPIRY, settlements=quotes)
        second = calculate(endpoint_date=EXPIRY + timedelta(days=100), settlements=quotes)
        self.assertEqual(first, second)

    def test_inexact_ratio_ignores_caller_context_and_preserves_flags(self):
        reference = calculate(fund_net_assets=D(3))
        with localcontext() as caller:
            caller.prec = 2
            caller.rounding = ROUND_DOWN
            caller.traps[Inexact] = True
            caller.traps[Rounded] = True
            flags = caller.flags.copy()
            result = calculate(fund_net_assets=D(3))
            self.assertEqual(result, reference)
            self.assertEqual(caller.flags, flags)
            self.assertEqual(caller.prec, 2)
            self.assertEqual(caller.rounding, ROUND_DOWN)

    def test_source_decimal_products_retain_precision(self):
        spec = specification(multiplier=D("123456789.123456789"))
        long = position(spec=spec, contracts=D("987654321.987654321"))
        result = calculate((long,), settlements=marks(spec, first=D("1.000000001"), last=D("1.000000002")))
        with localcontext() as ctx:
            ctx.prec = 100
            expected = long.contracts * spec.multiplier * D("0.000000001")
        self.assertEqual(result.pnl_try, expected)

    def test_input_positions_and_quote_mappings_are_not_mutated(self):
        rows, quotes = [position(), position(side="SHORT")], marks()
        old_rows, old_quotes = deepcopy(rows), deepcopy(quotes)
        calculate(rows, settlements=quotes)
        self.assertEqual(rows, old_rows)
        self.assertEqual(quotes, old_quotes)

    def test_results_never_assign_fraud_or_point_in_time_admission(self):
        for result in (calculate(), calculate(settlements={})):
            self.assertEqual(result.fund_status, "ABSTAINED")
            self.assertEqual(result.fraud_status, "ABSTAINED")
            self.assertEqual(result.origin, "HISTORICAL_REPLAY")
            self.assertEqual(result.admission, "CONDITIONAL_ARCHIVE_DIAGNOSTIC")
            self.assertFalse(result.point_in_time_admitted)
            self.assertEqual(result.assumption, "static_reported_contract_quantity_not_actual_trades_or_pnl")


if __name__ == "__main__":
    unittest.main()
