"""Synthetic checks of detectors.py. Run from this folder: python -m unittest test_detectors -v"""
import sys
import unittest
from datetime import date
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import detectors as det  # noqa: E402

nan = np.nan


class DetectorTest(unittest.TestCase):
    def test_a_return_needs_both_prices(self):
        r = det.log_returns(np.array([1.0, 1.1, nan, 1.2, 1.32]))
        self.assertTrue(np.isnan(r[[0, 2, 3]]).all())
        self.assertAlmostEqual(r[1], np.log(1.1))
        self.assertAlmostEqual(r[4], np.log(1.1))

    def test_peer_median_leaves_out_the_fund_and_needs_ten_peers(self):
        block = np.vstack([np.full(2, 100.0)] + [np.full(2, float(k)) for k in range(10)])
        block[5, 1] = nan  # date 1 has only nine peers
        m = det.peer_median(block, 0)
        self.assertEqual(m[0], 4.5)  # median of 0..9; the fund's own 100 is not in it
        self.assertTrue(np.isnan(m[1]))

    def test_rolling_median_counts_only_defined_values(self):
        out = det.rolling_median(np.array([1.0, nan, 3.0, 5.0]), window=3, min_count=2)
        self.assertTrue(np.isnan(out[:2]).all())
        self.assertEqual(list(out[2:]), [2.0, 4.0])

    def test_change_compares_the_last_60_dates_with_the_120_before(self):
        e = np.concatenate([np.zeros(120), np.ones(60)])
        out = det.excess_change(e)
        self.assertTrue(np.isnan(out[158]))  # the earlier window has only 99 values
        self.assertEqual(out[159], 1.0)
        self.assertEqual(out[179], 1.0)
        self.assertEqual(det.excess_change(np.full(300, 0.2))[-1], 0.0)

    def test_no_statistic_uses_a_later_date(self):
        rng = np.random.default_rng(0)
        r, m = rng.normal(0, 0.01, 400), rng.normal(0, 0.01, 400)
        r2, m2 = r.copy(), m.copy()
        r2[300:] += 0.05
        m2[300:] -= 0.05
        pairs = [(det.excess_level(r - m), det.excess_level(r2 - m2)),
                 (det.excess_change(r - m), det.excess_change(r2 - m2)),
                 (det.autocorrelation(r), det.autocorrelation(r2)),
                 (det.peer_correlation(r, m), det.peer_correlation(r2, m2))]
        for before, after in pairs:
            np.testing.assert_array_equal(before[:300], after[:300])
            self.assertFalse(np.array_equal(before[300:], after[300:], equal_nan=True))

    def test_smoothed_returns_have_high_autocorrelation(self):
        rng = np.random.default_rng(1)
        m = rng.normal(0, 0.01, 2000)
        smooth = 0.5 * m + 0.5 * det.lagged(m, 1)  # a price that reacts over two days: about 0.5
        # Averaged over many 120-date windows, so one window's sampling noise cannot decide the test.
        self.assertGreater(np.nanmean(det.autocorrelation(smooth)), 0.35)
        self.assertLess(abs(np.nanmean(det.autocorrelation(m))), 0.1)

    def test_a_window_without_variance_is_undefined(self):
        self.assertTrue(np.isnan(det.rolling_corr(np.ones(120), np.arange(120.0), 120, 100)[-1]))

    def test_age_counts_days_from_the_first_price(self):
        out = det.age_days([date(2025, 1, 1), date(2025, 1, 10)], date(2025, 1, 5))
        self.assertTrue(np.isnan(out[0]))
        self.assertEqual(out[1], 5)
        self.assertTrue(np.isnan(det.age_days([date(2025, 1, 1)], None)).all())

    def test_threshold_abstains_with_too_few_values_or_funds(self):
        five = [np.arange(200.0) for _ in range(5)]
        self.assertEqual(det.threshold(five, 99), np.percentile(np.tile(np.arange(200.0), 5), 99))
        self.assertIsNone(det.threshold([np.arange(250.0)] * 4 + [np.full(250, nan)], 99))  # four funds
        self.assertIsNone(det.threshold([np.arange(199.0)] * 5, 99))  # 995 values


if __name__ == "__main__":
    unittest.main()
