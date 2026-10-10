"""Synthetic golden equivalence and causal-window checks for product detectors."""
from __future__ import annotations

import importlib.util
import unittest
from datetime import date
from pathlib import Path

import numpy as np

from p50k.product import detector_math as math

FROZEN_SOURCE = (Path(__file__).resolve().parents[2] / "research" / "events"
                 / "2026-09-17-spk-liquidations" / "price_detectors" / "detectors.py")
spec = importlib.util.spec_from_file_location("frozen_price_math_for_synthetic_tests", FROZEN_SOURCE)
assert spec is not None and spec.loader is not None
frozen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(frozen)


class ProductDetectorMathTests(unittest.TestCase):
    def test_missing_zero_and_nonpositive_prices_invalidate_adjacent_returns(self) -> None:
        prices = np.array([1, 1.1, np.nan, 1.2, 1.32, 0, 1, -1, -2, np.inf, 2])
        returns = math.log_returns(prices)
        self.assertTrue(np.isnan(returns[[0, 2, 3, 5, 6, 7, 8, 9, 10]]).all())
        np.testing.assert_allclose(returns[[1, 4]], np.log([1.1, 1.1]))

    def test_log_ratio_overflow_and_underflow_do_not_invent_gaps(self) -> None:
        limits = np.finfo(float)
        prices = np.array([limits.tiny, limits.max, limits.tiny])
        out = math.log_returns(prices)
        expected = np.log(limits.max) - np.log(limits.tiny)
        np.testing.assert_allclose(out[1:], [expected, -expected])

    def test_returns_match_frozen_math_on_synthetic_positive_prices_and_gaps(self) -> None:
        rng = np.random.default_rng(9)
        prices = np.exp(np.cumsum(rng.normal(0, 0.01, 450)))
        prices[[3, 200, 403]] = np.nan
        np.testing.assert_array_equal(math.log_returns(prices), frozen.log_returns(prices))

    def test_peer_median_excludes_self_and_requires_ten_finite_peers(self) -> None:
        returns = np.vstack([np.full(2, 100.0)] + [np.full(2, float(k)) for k in range(10)])
        returns[5, 1] = np.nan
        peers = math.leave_one_out_peer_medians(returns)
        self.assertEqual(peers[0, 0], 4.5)
        self.assertTrue(np.isnan(peers[0, 1]))
        self.assertEqual(peers[5, 1], 5.5)  # Missing own observation still has ten peers.
        self.assertTrue(np.isnan(math.leave_one_out_peer_medians(returns[:10])).all())

    def test_category_medians_match_frozen_with_ties_odd_even_counts_and_gaps(self) -> None:
        rng = np.random.default_rng(11)
        returns = rng.integers(-3, 4, size=(27, 95)).astype(float)
        returns[rng.random(returns.shape) < 0.31] = np.nan
        returns[:, 4] = np.nan
        returns[0, 5] = np.nan
        actual = math.leave_one_out_peer_medians(returns)
        for own in range(len(returns)):
            np.testing.assert_array_equal(actual[own], frozen.peer_median(returns, own))

    def test_nonfinite_peer_values_are_missing(self) -> None:
        returns = np.arange(12.0)[:, None]
        returns[1, 0] = np.inf
        peers = math.leave_one_out_peer_medians(returns)
        self.assertEqual(peers[0, 0], 6.5)
        returns[2, 0] = -np.inf
        self.assertTrue(np.isnan(math.leave_one_out_peer_medians(returns)[0, 0]))

    def test_rolling_median_counts_finite_values_and_preserves_calendar_gaps(self) -> None:
        values = np.array([1, np.inf, 3, 5, np.nan])
        actual = math.rolling_median(values, window=3, min_count=2)
        np.testing.assert_array_equal(actual, [np.nan, np.nan, 2, 4, 4])

    def test_change_uses_separate_sixty_and_previous_one_hundred_twenty_dates(self) -> None:
        excess = np.concatenate([np.zeros(120), np.ones(60)])
        out = math.excess_change(excess)
        self.assertTrue(np.isnan(out[158]))
        self.assertEqual(out[159], 1)
        self.assertEqual(out[179], 1)
        self.assertEqual(math.excess_change(np.full(300, 0.2))[-1], 0)

    def test_correlations_match_frozen_using_only_complete_pairs(self) -> None:
        rng = np.random.default_rng(17)
        x = rng.normal(0, 0.01, 450)
        y = x * 0.7 + rng.normal(0, 0.004, 450)
        x[rng.random(450) < 0.07] = np.nan
        y[rng.random(450) < 0.05] = np.nan
        np.testing.assert_allclose(math.rolling_corr(x, y, 120, 100),
                                   frozen.rolling_corr(x, y, 120, 100), atol=1e-13, rtol=1e-13)

    def test_zero_variance_abstains_including_identical_decimal_values(self) -> None:
        for constant in (0, 1, 0.2):
            with self.subTest(constant=constant):
                self.assertTrue(np.isnan(math.rolling_corr(np.full(200, constant),
                                                          np.arange(200.0), 120, 100)).all())
                self.assertTrue(np.isnan(math.autocorrelation(np.full(200, constant))).all())

    def test_correlation_counts_pairs_not_independently_available_values(self) -> None:
        x, y = np.arange(120.0), np.arange(120.0)
        x[:11] = np.nan
        y[-11:] = np.nan
        self.assertTrue(np.isnan(math.rolling_corr(x, y, 120, 100)[-1]))
        y[-11:-9] = [109, 110]
        self.assertAlmostEqual(math.rolling_corr(x, y, 120, 100)[-1], 1)

    def test_all_four_scores_match_frozen_synthetic_golden_results(self) -> None:
        rng = np.random.default_rng(33)
        own, peers = rng.normal(0, 0.01, (2, 450))
        own[[25, 107, 202, 299]] = np.nan
        peers[[36, 129, 226]] = np.nan
        expected = {"D1": frozen.excess_level(own - peers),
                    "D2": frozen.excess_change(own - peers),
                    "D3": frozen.autocorrelation(own),
                    "D4": frozen.peer_correlation(own, peers)}
        actual = math.score_series(own, peers)
        self.assertEqual(set(actual), set(expected))
        for detector in expected:
            with self.subTest(detector=detector):
                np.testing.assert_allclose(actual[detector], expected[detector], atol=1e-13, rtol=1e-13)

    def test_appending_future_prices_cannot_change_prior_peer_or_detector_values(self) -> None:
        rng = np.random.default_rng(41)
        prices = np.exp(np.cumsum(rng.normal(0, 0.01, (15, 520)), axis=1))
        prices[rng.random(prices.shape) < 0.03] = np.nan
        cutoff = 350
        earlier_returns = np.array([math.log_returns(row[:cutoff]) for row in prices])
        full_returns = np.array([math.log_returns(row) for row in prices])
        earlier_peers = math.leave_one_out_peer_medians(earlier_returns)
        full_peers = math.leave_one_out_peer_medians(full_returns)
        np.testing.assert_array_equal(earlier_peers, full_peers[:, :cutoff])
        for own in (0, 7, 14):
            earlier = math.score_series(earlier_returns[own], earlier_peers[own])
            full = math.score_series(full_returns[own], full_peers[own])
            for detector in earlier:
                np.testing.assert_array_equal(earlier[detector], full[detector][:cutoff])

    def test_future_changes_cannot_change_earlier_statistics(self) -> None:
        rng = np.random.default_rng(43)
        own, peers = rng.normal(0, 0.01, (2, 500))
        before = math.score_series(own, peers)
        own[350:] += 1
        peers[350:] -= 1
        after = math.score_series(own, peers)
        for detector in before:
            np.testing.assert_array_equal(before[detector][:350], after[detector][:350])
            self.assertFalse(np.array_equal(before[detector][350:], after[detector][350:], equal_nan=True))

    def test_age_is_unknown_before_first_price_and_when_no_first_price_exists(self) -> None:
        calendar = [date(2030, 1, 1), date(2030, 1, 10)]
        np.testing.assert_array_equal(math.age_days(calendar, date(2030, 1, 5)), [np.nan, 5])
        self.assertTrue(np.isnan(math.age_days(calendar, None)).all())

    def test_threshold_requires_five_funds_and_one_thousand_finite_values(self) -> None:
        five = [np.arange(200.0) for _ in range(5)]
        self.assertEqual(math.threshold(five, 99), frozen.threshold(five, 99))
        self.assertEqual(math.threshold(five, 1), frozen.threshold(five, 1))
        self.assertIsNone(math.threshold([np.arange(199.0)] * 5, 99))
        self.assertIsNone(math.threshold([np.arange(250.0)] * 4 + [np.full(250, np.nan)], 99))
        self.assertIsNone(math.threshold([np.arange(199.0)] * 5 + [np.array([np.inf, -np.inf])], 99))
        self.assertIsNone(math.threshold([], 99))

    def test_empty_series_and_invalid_window_or_calendar_do_not_produce_values(self) -> None:
        for function in (math.log_returns, math.excess_level, math.excess_change, math.autocorrelation):
            self.assertEqual(function(np.array([])).size, 0)
        self.assertEqual(math.leave_one_out_peer_medians(np.empty((0, 0))).shape, (0, 0))
        self.assertTrue(np.isnan(math.lagged(np.arange(2.0), 10)).all())
        for window, minimum in ((0, 1), (1, 0), (2, 3)):
            with self.subTest(window=window, minimum=minimum), self.assertRaises(ValueError):
                math.rolling_median(np.arange(4.0), window, minimum)
        with self.assertRaises(ValueError):
            math.score_series(np.arange(2.0), np.arange(3.0))
        with self.assertRaises(ValueError):
            math.rolling_corr(np.arange(2.0), np.arange(3.0), 2, 2)


if __name__ == "__main__":
    unittest.main()
