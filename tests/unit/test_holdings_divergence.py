"""Synthetic arithmetic and publication boundaries; no provider data."""
from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, Inexact, Rounded, ROUND_DOWN, localcontext
from zoneinfo import ZoneInfo

from p50k.analytics.holdings_divergence import (
    HoldingsSnapshot, StockPosition, build_diagnostic_windows,
    calculate_holdings_gap,
)


D = Decimal
LOCAL = ZoneInfo("Europe/Istanbul")
BASE = date(2025, 11, 4)
END = date(2025, 11, 5)


def snapshot(*positions: StockPosition, **changes: object) -> HoldingsSnapshot:
    result = HoldingsSnapshot("synthetic-report", date(2025, 10, 31),
        datetime(2025, 11, 3, 12, tzinfo=LOCAL), D(100),
        positions or (StockPosition("SYNTHETIC_A", "AAA", D(80)),))
    return replace(result, **changes)


def metric(report: HoldingsSnapshot | None = None, **changes: object):
    arguments = dict(base_date=BASE, valuation_date=END,
        prices={"AAA": {BASE: D(100), END: D(90)}},
        base_nav=D(100), end_nav=D(92))
    arguments.update(changes)
    return calculate_holdings_gap(report or snapshot(), **arguments)


def calendar() -> tuple[date, ...]:
    # A synthetic weekday calendar, not a claim about actual BIST holidays.
    days = tuple(date(2025, 11, 3) + timedelta(days=n) for n in range(61))
    return tuple(day for day in days if day.weekday() < 5)


def windows(reports=None, **changes):
    sessions = calendar()
    arguments = dict(market_sessions=sessions,
        fund_nav_by_label={sessions[n + 1]: D(100) for n in range(len(sessions) - 1)},
        prices={"AAA": {day: D(100) for day in sessions}},
        fund_label_cutoff=date(2025, 12, 31))
    arguments.update(changes)
    return build_diagnostic_windows(reports or (snapshot(),), **arguments)


class HoldingsGapTests(unittest.TestCase):
    def test_eighty_percent_stock_drop_is_not_renormalized(self):
        result = metric()
        self.assertEqual(result.equity_proxy_return, D("-0.08"))
        self.assertEqual(result.actual_return, D("-0.08"))
        self.assertEqual(result.gap, D(0))
        self.assertEqual(result.net_equity_weight, D("0.8"))

    def test_perfect_replication_zero_gap_with_two_securities(self):
        report = snapshot(StockPosition("SYNTHETIC_A", "AAA", D(50)),
                          StockPosition("SYNTHETIC_B", "BBB", D(30)))
        result = metric(report, prices={"AAA": {BASE: D(100), END: D(110)},
                                       "BBB": {BASE: D(100), END: D(90)}},
                        end_nav=D(102))
        self.assertEqual(result.gap, D(0))
        self.assertEqual(result.equity_proxy_return, D("0.02"))
        self.assertEqual(result.prices_present, result.prices_required)

    def test_frozen_half_weight_double_then_return_has_zero_cumulative_proxy(self):
        report = snapshot(StockPosition("SYNTHETIC_A", "AAA", D(50)))
        final = date(2025, 11, 6)
        prices = {"AAA": {BASE: D(100), END: D(200), final: D(100)}}
        first = metric(report, prices=prices, end_nav=D(150))
        last = metric(report, prices=prices, valuation_date=final, end_nav=D(100))
        self.assertEqual(first.equity_proxy_return, D("0.5"))
        self.assertEqual(last.equity_proxy_return, D(0))
        self.assertEqual(last.gap, D(0))
        self.assertNotEqual(last.equity_proxy_return, D("0.125"))

    def test_negative_reported_weight_retained_as_arithmetic_only(self):
        result = metric(snapshot(StockPosition("SYNTHETIC_A", "AAA", D(-50))), end_nav=D(105))
        self.assertEqual(result.equity_proxy_return, D("0.05"))
        self.assertEqual(result.net_equity_weight, D("-0.5"))
        self.assertEqual(result.gross_equity_weight, D("0.5"))
        self.assertEqual(result.negative_reported_position_count, 1)
        self.assertIn("signed_negative_rows_economic_meaning_unknown", result.caveats)
        self.assertEqual(result.fund_status, "ABSTAINED")
        self.assertEqual(result.fraud_status, "ABSTAINED")

    def test_duplicate_isin_signed_values_aggregate_before_weighting(self):
        report = snapshot(StockPosition("SYNTHETIC_A", "AAA", D(80)),
                          StockPosition("SYNTHETIC_A", "AAA", D(-30)))
        result = metric(report, end_nav=D(95))
        self.assertEqual(result.security_count, 1)
        self.assertEqual(result.prices_required, 2)
        self.assertEqual(result.signed_weights, (("SYNTHETIC_A", "AAA", D("0.5")),))
        self.assertEqual(result.net_equity_weight, D("0.5"))
        self.assertEqual(result.gross_equity_weight, D("0.5"))
        self.assertEqual(result.gross_reported_position_weight, D("1.1"))
        self.assertEqual(result.gap, D(0))

    def test_contradictory_alias_for_same_isin_rejected(self):
        report = snapshot(StockPosition("SYNTHETIC_A", "AAA", D(80)),
                          StockPosition("SYNTHETIC_A", "BBB", D(-30)))
        result = metric(report)
        self.assertEqual(result.availability, "UNAVAILABLE")
        self.assertIn("contradictory_price_identity:SYNTHETIC_A", result.reasons)
        self.assertIsNone(result.gap)

    def test_distinct_isins_mapped_to_same_symbol_rejected(self):
        report = snapshot(StockPosition("SYNTHETIC_A", "AAA", D(80)),
                          StockPosition("SYNTHETIC_B", "AAA", D(20)))
        self.assertIn("price_symbol_has_multiple_isins:AAA", metric(report).reasons)

    def test_unknown_identity_rejected(self):
        result = metric(snapshot(StockPosition("SYNTHETIC_A", None, D(80))))
        self.assertIn("price_identity_unknown:SYNTHETIC_A", result.reasons)
        self.assertIsNone(result.equity_proxy_return)

    def test_missing_required_baseline_close_not_forward_filled(self):
        result = metric(prices={"AAA": {BASE - timedelta(days=1): D(100), END: D(90)}})
        self.assertEqual(result.availability, "UNAVAILABLE")
        self.assertEqual(result.prices_present, 1)
        self.assertIsNone(result.gap)
        self.assertIn("baseline_positive_finite_decimal_close_required:AAA", result.reasons)

    def test_missing_required_end_close_not_forward_filled(self):
        result = metric(prices={"AAA": {BASE: D(100)}})
        self.assertIsNone(result.actual_return)
        self.assertIsNone(result.gap)
        self.assertIn("endpoint_positive_finite_decimal_close_required:AAA", result.reasons)

    def test_zero_position_still_requires_both_prices(self):
        report = snapshot(StockPosition("SYNTHETIC_A", "AAA", D(80)),
                          StockPosition("SYNTHETIC_B", "BBB", D(0)))
        result = metric(report)
        self.assertEqual(result.security_count, 2)
        self.assertEqual(result.prices_required, 4)
        self.assertEqual(result.prices_present, 2)
        self.assertIn("price_series_missing:BBB", result.reasons)
        self.assertIsNone(result.gap)

    def test_small_value_position_is_not_dropped_for_rounding(self):
        report = snapshot(StockPosition("SYNTHETIC_A", "AAA", D(80)),
                          StockPosition("SYNTHETIC_B", "BBB", D("0.00001")))
        self.assertEqual(metric(report).availability, "UNAVAILABLE")

    def test_invalid_prices_and_nav_remain_unknown(self):
        for invalid in (None, D(0), D(-1), D("NaN"), D("sNaN"), D("Infinity"), 100.0):
            with self.subTest(invalid=str(invalid)):
                result = metric(prices={"AAA": {BASE: D(100), END: invalid}})
                self.assertIsNone(result.gap)
                self.assertEqual(result.availability, "UNAVAILABLE")
                self.assertIsNone(metric(base_nav=invalid).gap)
                self.assertIsNone(metric(end_nav=invalid).gap)

    def test_invalid_net_assets_and_position_values_rejected(self):
        for invalid in (None, D(0), D(-1), D("NaN"), D("Infinity"), 100.0):
            with self.subTest(invalid=str(invalid)):
                self.assertIsNone(metric(snapshot(fund_net_assets=invalid)).gap)
        for invalid in (None, D("NaN"), D("Infinity"), 80.0):
            self.assertIsNone(metric(snapshot(StockPosition("SYNTHETIC_A", "AAA", invalid))).gap)

    def test_source_reconciliation_problem_gates_numbers(self):
        result = metric(snapshot(problems=("printed_value_inconsistent",)))
        self.assertEqual(result.reasons, ("printed_value_inconsistent",))
        self.assertIsNone(result.gap)

    def test_naive_publication_time_rejected(self):
        result = metric(snapshot(available_at=datetime(2025, 11, 3, 12)))
        self.assertIn("publication_timezone_required", result.reasons)

    def test_baseline_on_publication_day_rejected(self):
        result = metric(snapshot(available_at=datetime(2025, 11, 4, 1, tzinfo=LOCAL)))
        self.assertIn("baseline_must_be_after_publication_date", result.reasons)

    def test_report_period_after_publication_rejected(self):
        self.assertIn("report_period_after_publication", metric(snapshot(reported_period_end=BASE)).reasons)

    def test_same_or_reversed_market_dates_rejected(self):
        for day in (BASE, BASE - timedelta(days=1)):
            self.assertIn("strictly_increasing_market_dates_required", metric(valuation_date=day).reasons)

    def test_net_asset_growth_is_not_unit_return(self):
        fixed_prices = {"AAA": {BASE: D(100), END: D(100)}}
        original = metric(prices=fixed_prices, end_nav=D(100))
        scaled = metric(snapshot(StockPosition("SYNTHETIC_A", "AAA", D(800)),
                                 fund_net_assets=D(1000)), prices=fixed_prices, end_nav=D(100))
        self.assertEqual(original.actual_return, D(0))
        self.assertEqual(scaled.actual_return, D(0))
        self.assertEqual(original.gap, scaled.gap)

    def test_hedged_fund_flat_and_stocks_down_gap_is_not_fraud(self):
        result = metric(snapshot(futures_present=True), end_nav=D(100))
        self.assertEqual(result.gap, D("0.08"))
        self.assertTrue(result.futures_present)
        self.assertEqual(result.fraud_status, "ABSTAINED")
        self.assertIn("unmodeled_futures_cash_yield_fees_trading_and_dividends", result.caveats)

    def test_futures_presence_does_not_add_notional_to_spot(self):
        without = metric()
        with_futures = metric(snapshot(futures_present=True))
        self.assertEqual(without.equity_proxy_return, with_futures.equity_proxy_return)
        self.assertEqual(without.net_equity_weight, with_futures.net_equity_weight)

    def test_caller_decimal_traps_and_rounding_do_not_change_output(self):
        report = snapshot(StockPosition("SYNTHETIC_A", "AAA", D(1)), fund_net_assets=D(3))
        expected = metric(report)
        with localcontext() as context:
            context.prec = 2
            context.rounding = ROUND_DOWN
            context.traps[Inexact] = True
            context.traps[Rounded] = True
            actual = metric(report)
        self.assertEqual(actual, expected)

    def test_extreme_exponents_rejected_before_arithmetic(self):
        self.assertIsNone(metric(snapshot(fund_net_assets=D("1e5000"))).gap)

    def test_price_map_future_mutations_do_not_change_prior_endpoint(self):
        prices = {"AAA": {BASE: D(100), END: D(90), END + timedelta(days=1): D(50)}}
        expected = metric(prices=prices)
        prices["AAA"][END + timedelta(days=1)] = D(1000000)
        self.assertEqual(metric(prices=prices), expected)


class DiagnosticWindowTests(unittest.TestCase):
    def test_baseline_after_publication_and_at_most_twenty_intervals(self):
        result = windows()[0]
        self.assertEqual(result.base_date, BASE)
        self.assertEqual(result.base_fund_row_label, END)
        self.assertEqual(len(result.rows), 20)
        self.assertEqual(result.rows[0].valuation_date, END)
        self.assertEqual(result.rows[0].fund_row_label, date(2025, 11, 6))
        self.assertEqual(result.rows[-1].interval_number, 20)

    def test_next_publication_day_is_excluded(self):
        following = snapshot(snapshot_id="next-report", reported_period_end=date(2025, 11, 7),
                             available_at=datetime(2025, 11, 10, 12, tzinfo=LOCAL))
        result = windows((snapshot(), following))[0]
        self.assertEqual(result.next_publication_date, date(2025, 11, 10))
        self.assertEqual([row.valuation_date for row in result.rows],
                         [date(2025, 11, day) for day in (5, 6, 7)])

    def test_future_report_values_do_not_change_earlier_window(self):
        following = snapshot(snapshot_id="next-report", reported_period_end=date(2025, 11, 7),
                             available_at=datetime(2025, 11, 10, 12, tzinfo=LOCAL))
        expected = windows((snapshot(), following))[0]
        changed = replace(following, positions=(StockPosition("SYNTHETIC_A", "AAA", D(9999)),))
        self.assertEqual(windows((snapshot(), changed))[0], expected)

    def test_publication_day_uses_istanbul_timezone(self):
        report = snapshot(available_at=datetime(2025, 11, 3, 22, tzinfo=timezone.utc))
        self.assertEqual(windows((report,))[0].base_date, END)

    def test_no_baseline_before_later_same_day_report(self):
        following = snapshot(snapshot_id="correction", available_at=datetime(2025, 11, 3, 15, tzinfo=LOCAL))
        earlier = windows((snapshot(), following))[0]
        self.assertEqual(earlier.reasons, ("no_eligible_baseline_session",))
        self.assertEqual(earlier.rows, ())

    def test_cutoff_uses_fund_row_label_not_price_valuation_date(self):
        result = windows(fund_label_cutoff=date(2025, 11, 10))[0]
        self.assertEqual(result.rows[-1].valuation_date, date(2025, 11, 7))
        self.assertEqual(result.rows[-1].fund_row_label, date(2025, 11, 10))
        self.assertNotIn(date(2025, 11, 10), [row.valuation_date for row in result.rows])

    def test_labels_after_cutoff_not_read(self):
        sessions = calendar()
        nav = {sessions[n + 1]: D(100) for n in range(len(sessions) - 1)}
        expected = windows(fund_nav_by_label=nav, fund_label_cutoff=date(2025, 11, 10))
        nav[date(2025, 11, 11)] = D("NaN")
        self.assertEqual(windows(fund_nav_by_label=nav, fund_label_cutoff=date(2025, 11, 10)), expected)

    def test_missing_stock_bar_does_not_change_tefas_alignment(self):
        sessions = calendar()
        prices = {"AAA": {day: D(100) for day in sessions if day != END}}
        first = windows(prices=prices)[0].rows[0]
        self.assertEqual(first.valuation_date, END)
        self.assertEqual(first.fund_row_label, date(2025, 11, 6))
        self.assertIsNone(first.metric.gap)
        self.assertIn("endpoint_positive_finite_decimal_close_required:AAA", first.metric.reasons)

    def test_duplicate_nav_labels_mapping_to_one_session_fail_closed(self):
        sessions = calendar()
        nav = {sessions[n + 1]: D(100) for n in range(len(sessions) - 1)}
        nav[date(2025, 11, 8)] = D(101)  # Saturday and Monday both map to Friday.
        result = windows(fund_nav_by_label=nav)[0]
        friday = next(row for row in result.rows if row.valuation_date == date(2025, 11, 7))
        self.assertIsNone(friday.metric.gap)
        self.assertIn("multiple_fund_labels_for_market_session", friday.metric.reasons)

    def test_missing_baseline_nav_makes_entire_window_unavailable(self):
        sessions = calendar()
        nav = {sessions[n + 1]: D(100) for n in range(len(sessions) - 1)}
        del nav[END]
        result = windows(fund_nav_by_label=nav)[0]
        self.assertTrue(result.rows)
        self.assertTrue(all(row.metric.gap is None for row in result.rows))
        self.assertTrue(all("fund_nav_missing_for_market_session" in row.metric.reasons for row in result.rows))

    def test_unavailable_nav_preserves_known_unmodeled_futures_presence(self):
        report = snapshot(futures_present=True)
        sessions = calendar()
        nav = {sessions[n + 1]: D(100) for n in range(len(sessions) - 1)}
        del nav[END]
        result = windows((report,), fund_nav_by_label=nav)[0]
        self.assertTrue(result.rows)
        self.assertTrue(all(row.metric.availability == "UNAVAILABLE" for row in result.rows))
        self.assertTrue(all(row.metric.futures_present for row in result.rows))
        self.assertTrue(all("unmodeled_futures_cash_yield_fees_trading_and_dividends" in row.metric.caveats
                            for row in result.rows))
        self.assertTrue(all(row.metric.fund_status == "ABSTAINED" for row in result.rows))
        self.assertTrue(all(row.metric.fraud_status == "ABSTAINED" for row in result.rows))

    def test_zero_nav_stays_missing(self):
        sessions = calendar()
        nav = {sessions[n + 1]: D(100) for n in range(len(sessions) - 1)}
        nav[date(2025, 11, 6)] = D(0)
        self.assertIsNone(windows(fund_nav_by_label=nav)[0].rows[0].metric.gap)

    def test_invalid_and_duplicate_calendar_rejected(self):
        for invalid in ((), (END, BASE), (BASE, BASE), (datetime(2025, 11, 4), END)):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                windows(market_sessions=invalid)

    def test_unbounded_or_boolean_window_length_rejected(self):
        for invalid in (0, 21, True, 3.5):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                windows(max_intervals=invalid)

    def test_duplicate_snapshot_id_or_publication_instant_rejected(self):
        following = snapshot(snapshot_id="synthetic-report", available_at=datetime(2025, 11, 10, 12, tzinfo=LOCAL))
        with self.assertRaises(ValueError):
            windows((snapshot(), following))
        with self.assertRaises(ValueError):
            windows((snapshot(), snapshot(snapshot_id="other")))

    def test_naive_publication_rejected_before_sorting(self):
        with self.assertRaises(ValueError):
            windows((snapshot(available_at=datetime(2025, 11, 3, 12)),))

    def test_no_eligible_return_interval_is_explicit(self):
        result = windows(fund_label_cutoff=date(2025, 11, 5))[0]
        self.assertEqual(result.base_date, BASE)
        self.assertEqual(result.rows, ())
        self.assertEqual(result.reasons, ("no_eligible_return_interval",))


if __name__ == "__main__":
    unittest.main()
