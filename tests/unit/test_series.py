import math
import statistics
import unittest
from datetime import date, datetime, timedelta

from p50k.series import (InvalidSeries, SeriesPoint, align_by_date, log_returns, max_drawdown,
                         mean, quantile, sample_std_dev, simple_returns)


def series(*values, start=date(2026, 9, 28)):
    return [SeriesPoint(start + timedelta(days=i), v) for i, v in enumerate(values)]


class StatisticsTest(unittest.TestCase):
    def test_undefined_statistics_are_none_not_zero(self):
        self.assertIsNone(mean([]))
        self.assertIsNone(sample_std_dev([]))
        self.assertIsNone(sample_std_dev([5.0]))
        self.assertIsNone(quantile([], 0.5))

    def test_mean_and_std_match_the_statistics_module(self):
        values = [0.012, -0.004, 0.0, 0.031, -0.019, 0.007]
        self.assertAlmostEqual(mean(values), statistics.fmean(values), places=15)
        self.assertAlmostEqual(sample_std_dev(values), statistics.stdev(values), places=15)

    def test_quantile_matches_the_inclusive_method(self):
        values = [3.0, -1.0, 7.5, 2.0, 0.5, 10.0, 4.0]
        cuts = statistics.quantiles(values, n=20, method="inclusive")
        for k, expected in enumerate(cuts, start=1):
            with self.subTest(q=k / 20):
                self.assertAlmostEqual(quantile(values, k / 20), expected, places=12)
        self.assertEqual(quantile(values, 0), -1.0)
        self.assertEqual(quantile(values, 1), 10.0)

    def test_quantile_rejects_out_of_range_q(self):
        for q in (-0.1, 1.1, float("nan"), True):
            with self.subTest(q=q), self.assertRaises(ValueError):
                quantile([1.0], q)

    def test_rejects_non_finite_boolean_text_and_missing_values(self):
        for bad in (float("nan"), float("inf"), True, None, "1.0"):
            for func in (mean, sample_std_dev, lambda v: quantile(v, 0.5)):
                with self.subTest(bad=bad), self.assertRaises(InvalidSeries):
                    func([1.0, bad])


class ReturnsTest(unittest.TestCase):
    def test_simple_and_log_returns(self):
        points = series(100.0, 110.0, 99.0)
        simple = simple_returns(points)
        self.assertEqual([p.date for p in simple], [points[1].date, points[2].date])
        self.assertAlmostEqual(simple[0].value, 0.10, places=15)
        self.assertAlmostEqual(simple[1].value, -0.10, places=15)
        logs = log_returns(points)
        self.assertAlmostEqual(logs[0].value, math.log(1.1), places=15)
        self.assertAlmostEqual(math.fsum(p.value for p in logs), math.log(99 / 100), places=15)

    def test_unsorted_input_is_sorted_by_date(self):
        points = series(100.0, 110.0, 121.0)
        self.assertEqual(simple_returns(list(reversed(points))), simple_returns(points))

    def test_a_return_spans_whatever_gap_lies_between_observations(self):
        before, after = date(2026, 5, 26), date(2026, 6, 1)
        [only] = simple_returns([SeriesPoint(before, 100.0), SeriesPoint(after, 105.0)])
        self.assertEqual(only.date, after)
        self.assertAlmostEqual(only.value, 0.05, places=15)

    def test_short_series_give_no_returns(self):
        self.assertEqual(simple_returns([]), [])
        self.assertEqual(log_returns(series(100.0)), [])

    def test_invalid_series_raise(self):
        cases = {
            "zero price": series(100.0, 0.0),
            "negative price": series(100.0, -1.0),
            "NaN placeholder": series(100.0, float("nan")),
            "duplicate date": [SeriesPoint(date(2026, 10, 6), 1.0), SeriesPoint(date(2026, 10, 6), 1.1)],
            "datetime instead of date": [SeriesPoint(datetime(2026, 10, 6), 1.0)],
            "text date": [SeriesPoint("2026-10-06", 1.0)],
        }
        for name, points in cases.items():
            for func in (simple_returns, log_returns, max_drawdown):
                with self.subTest(case=name, func=func.__name__), self.assertRaises(InvalidSeries):
                    func(points)


class DrawdownTest(unittest.TestCase):
    def test_max_drawdown_is_a_fraction(self):
        self.assertAlmostEqual(max_drawdown(series(100, 120, 90, 110, 80, 130)), 80 / 120 - 1, places=15)

    def test_rising_series_has_zero_drawdown_and_empty_has_none(self):
        self.assertEqual(max_drawdown(series(1.0, 2.0, 3.0)), 0.0)
        self.assertIsNone(max_drawdown([]))


class AlignByDateTest(unittest.TestCase):
    def test_inner_join_reports_dropped_observations(self):
        fund = series(1.0, 1.1, 1.2, 1.3)  # Sep 28 to Oct 1
        peer = series(2.0, 2.1, start=date(2026, 9, 29)) + series(2.3, start=date(2026, 10, 2))
        aligned = align_by_date({"TTE": fund, "peer": peer})
        self.assertEqual(aligned.dates, [date(2026, 9, 29), date(2026, 9, 30)])
        self.assertEqual(aligned.values, {"TTE": [1.1, 1.2], "peer": [2.0, 2.1]})
        self.assertEqual(aligned.unmatched, {"TTE": 2, "peer": 1})

    def test_negative_values_are_allowed(self):
        returns = series(-0.02, 0.01)
        self.assertEqual(align_by_date({"r": returns}).values, {"r": [-0.02, 0.01]})

    def test_empty_inputs(self):
        self.assertEqual(align_by_date({}).dates, [])
        self.assertEqual(align_by_date({"a": series(1.0), "b": []}).dates, [])


if __name__ == "__main__":
    unittest.main()
