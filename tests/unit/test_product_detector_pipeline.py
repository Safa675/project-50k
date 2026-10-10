"""Synthetic orchestration checks for the immutable all-fund v2 protocol."""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import unittest

import numpy as np

from p50k.product import detector_pipeline as pipeline

CATEGORY = "Synthetic category"


def synthetic_dataset(count: int = 12, rows: int = 350) -> pipeline.DataSet:
    days: list[date] = []
    day = date(2024, 10, 1)
    while len(days) < rows:
        if day.weekday() < 5:
            days.append(day)
        day += timedelta(days=1)
    rng = np.random.default_rng(101)
    prices = np.exp(np.cumsum(rng.normal(0, 0.003, (count, rows)), axis=1))
    codes = tuple(f"SYNTH{index:02}" for index in range(count))
    available = datetime.combine(days[-1], datetime.min.time(), timezone.utc) + timedelta(hours=12) if days else None
    return pipeline.DataSet(codes=codes, categories=(CATEGORY,) * count, days=tuple(days),
                            prices=prices, present=np.ones(prices.shape, dtype=bool),
                            ambiguous=np.zeros(prices.shape, dtype=bool),
                            source_hashes={code: ("a" * 64,) for code in codes},
                            input_sha256="b" * 64, input_watermark=available,
                            latest_availability={code: available for code in codes} if available else {})


def fixture_cutoff(dataset: pipeline.DataSet) -> datetime:
    return datetime.combine(dataset.days[-1], datetime.min.time(), timezone.utc) + timedelta(hours=12)


def by_detector(signals: list[pipeline.Signal]) -> dict[str, pipeline.Signal]:
    return {signal.detector_id: signal for signal in signals}


def thresholds_for_scores(scores: dict[str, np.ndarray], adjustment: Decimal = Decimal(0),
                          trigger: bool = True) -> dict[str, dict[str, str]]:
    thresholds: dict[str, dict[str, str]] = {}
    for detector, values in scores.items():
        value = Decimal(str(values[-1]))
        direction = Decimal(1) if detector == "D4" else Decimal(-1)
        threshold = value + direction * adjustment * (1 if trigger else -1)
        thresholds[detector] = {CATEGORY: str(threshold)}
    return thresholds


def small_price_dataset(days: tuple[date, ...], prices: list[float],
                        present: list[bool] | None = None) -> pipeline.DataSet:
    code = "SYNTH00"
    matrix = np.array([prices], dtype=float)
    available = datetime.combine(days[-1], datetime.min.time(), timezone.utc) + timedelta(hours=12) if days else None
    return pipeline.DataSet(codes=(code,), categories=(CATEGORY,), days=days, prices=matrix,
                            present=np.array([present if present is not None else [True] * len(days)], dtype=bool),
                            ambiguous=np.zeros(matrix.shape, dtype=bool),
                            source_hashes={code: ("a" * 64,)}, input_sha256="b" * 64,
                            input_watermark=available, latest_availability={code: available} if available else {})


class ProductDetectorPipelineTests(unittest.TestCase):
    def test_calibration_excludes_cutoff_and_every_later_price(self) -> None:
        dataset = synthetic_dataset()
        baseline = pipeline.calibrate_dataset(dataset)
        for detector in pipeline.PERCENTILES:
            self.assertIsNotNone(baseline[detector][CATEGORY], detector)
        after_cutoff = np.array([day >= date(2025, 10, 6) for day in dataset.days])
        changed = dataset.prices.copy()
        changed[:, after_cutoff] *= np.exp(np.arange(after_cutoff.sum()) % 3)
        changed[0, after_cutoff] = np.nan
        self.assertEqual(pipeline.calibrate_dataset(replace(dataset, prices=changed)), baseline)

    def test_missing_current_return_abstains_even_when_raw_rolling_history_is_sufficient(self) -> None:
        dataset = synthetic_dataset()
        dataset.prices[0, -1] = np.nan
        scores = pipeline.calculate_scores(dataset)
        for detector in pipeline.PERCENTILES:
            self.assertTrue(np.isnan(scores[dataset.codes[0]][detector][-1]), detector)
            self.assertTrue(np.isfinite(scores[dataset.codes[0]][detector][-2]), detector)
        thresholds = {detector: {CATEGORY: "0"} for detector in pipeline.PERCENTILES}
        signals = by_detector(pipeline.evaluate_fund(dataset, dataset.codes[0], fixture_cutoff(dataset),
                                                     thresholds, scores[dataset.codes[0]]))
        for detector in pipeline.PERCENTILES:
            self.assertEqual(signals[detector].state, "ABSTAINED", detector)
            self.assertIsNone(signals[detector].value)

    def test_missing_prior_calendar_price_breaks_current_return(self) -> None:
        dataset = synthetic_dataset()
        dataset.prices[0, -2] = np.nan
        scores = pipeline.calculate_scores(dataset)[dataset.codes[0]]
        for detector, values in scores.items():
            self.assertTrue(np.isnan(values[-1]), detector)

    def test_insufficient_current_peers_masks_peer_detectors_but_not_own_autocorrelation(self) -> None:
        dataset = synthetic_dataset()
        dataset.prices[:3, -1] = np.nan
        scores = pipeline.calculate_scores(dataset)[dataset.codes[3]]
        for detector in ("D1", "D2", "D4"):
            self.assertTrue(np.isnan(scores[detector][-1]), detector)
        self.assertTrue(np.isfinite(scores["D3"][-1]))

    def test_threshold_ties_do_not_trigger_either_comparison_direction(self) -> None:
        dataset = synthetic_dataset()
        code = dataset.codes[0]
        scores = pipeline.calculate_scores(dataset)[code]
        thresholds = thresholds_for_scores(scores)
        signals = by_detector(pipeline.evaluate_fund(dataset, code, fixture_cutoff(dataset), thresholds, scores))
        for detector in pipeline.PERCENTILES:
            self.assertEqual(signals[detector].state, "NOT_TRIGGERED", detector)
            self.assertEqual(signals[detector].value, signals[detector].threshold)

    def test_strict_upper_and_lower_triggers_and_normal_controls(self) -> None:
        dataset = synthetic_dataset()
        code = dataset.codes[0]
        scores = pipeline.calculate_scores(dataset)[code]
        for should_trigger in (True, False):
            thresholds = thresholds_for_scores(scores, Decimal("0.001"), should_trigger)
            signals = by_detector(pipeline.evaluate_fund(dataset, code, fixture_cutoff(dataset), thresholds, scores))
            for detector in pipeline.PERCENTILES:
                self.assertEqual(signals[detector].state,
                                 "TRIGGERED" if should_trigger else "NOT_TRIGGERED", detector)

    def test_missing_category_threshold_never_borrows_another_category(self) -> None:
        dataset = synthetic_dataset()
        code = dataset.codes[0]
        scores = pipeline.calculate_scores(dataset)[code]
        thresholds = {detector: {"Other synthetic category": "0"} for detector in pipeline.PERCENTILES}
        signals = by_detector(pipeline.evaluate_fund(dataset, code, fixture_cutoff(dataset), thresholds, scores))
        for detector in pipeline.PERCENTILES:
            self.assertEqual(signals[detector].state, "ABSTAINED")
            self.assertEqual(signals[detector].reason, "NO_CATEGORY_THRESHOLD")

    def test_missing_category_remains_explicitly_uncovered(self) -> None:
        dataset = replace(synthetic_dataset(), categories=(None,) * 12)
        signals = by_detector(pipeline.evaluate_fund(dataset, dataset.codes[0], fixture_cutoff(dataset), {}))
        for detector in pipeline.PERCENTILES:
            self.assertEqual(signals[detector].state, "ABSTAINED")
            self.assertEqual(signals[detector].reason, "CATEGORY_MISSING")

    def test_category_with_ten_funds_can_only_calibrate_non_peer_detector(self) -> None:
        thresholds = pipeline.calibrate_dataset(synthetic_dataset(count=10))
        for detector in ("D1", "D2", "D4"):
            self.assertIsNone(thresholds[detector][CATEGORY])
        self.assertIsNotNone(thresholds["D3"][CATEGORY])
        all_abstain = pipeline.calibrate_dataset(synthetic_dataset(count=4))
        for detector in pipeline.PERCENTILES:
            self.assertIsNone(all_abstain[detector][CATEGORY])

    def test_short_visible_history_is_attribute_and_never_anomaly(self) -> None:
        dataset = synthetic_dataset()
        signal = by_detector(pipeline.evaluate_fund(dataset, dataset.codes[0], fixture_cutoff(dataset), {}))["D5"]
        self.assertEqual(signal.state, "NOT_TRIGGERED")
        self.assertTrue(signal.metadata["is_attribute"])
        self.assertTrue(signal.metadata["short_visible_history"])
        self.assertTrue(signal.metadata["age_is_lower_bound"])
        self.assertLess(signal.value, Decimal(730))

    def test_no_positive_history_abstains_on_age_and_staleness_but_warns_missing_nav(self) -> None:
        for missing in (np.nan, 0, -1):
            with self.subTest(missing=missing):
                dataset = small_price_dataset((date(2026, 10, 9),), [missing])
                signals = by_detector(pipeline.evaluate_fund(dataset, dataset.codes[0], fixture_cutoff(dataset), {}))
                for detector in (*pipeline.PERCENTILES, "D5", "AN-DQ-001"):
                    self.assertEqual(signals[detector].state, "ABSTAINED", detector)
                self.assertEqual(signals["AN-DQ-002"].state, "TRIGGERED")

    def test_staleness_counts_only_elapsed_weekdays_before_cutoff_date(self) -> None:
        dataset = small_price_dataset((date(2026, 10, 9),), [100])  # Friday.
        expected = ((9, 0, "NOT_TRIGGERED"), (11, 0, "NOT_TRIGGERED"),
                    (12, 0, "NOT_TRIGGERED"), (13, 1, "NOT_TRIGGERED"),
                    (14, 2, "TRIGGERED"))
        for cutoff_day, count, state in expected:
            with self.subTest(cutoff_day=cutoff_day):
                cutoff = datetime(2026, 10, cutoff_day, 12, tzinfo=timezone.utc)
                signal = by_detector(pipeline.evaluate_fund(dataset, dataset.codes[0], cutoff, {}))["AN-DQ-001"]
                self.assertEqual(signal.value, Decimal(count))
                self.assertEqual(signal.state, state)
                self.assertTrue(signal.metadata["official_holidays_unverified"])

    def test_missing_latest_explicit_row_warns_but_absent_row_is_not_invented(self) -> None:
        days = (date(2026, 10, 9), date(2026, 10, 12))
        for is_present, expected in ((True, "TRIGGERED"), (False, "NOT_TRIGGERED")):
            with self.subTest(is_present=is_present):
                dataset = small_price_dataset(days, [100, np.nan], [True, is_present])
                signal = by_detector(pipeline.evaluate_fund(dataset, dataset.codes[0], fixture_cutoff(dataset), {}))["AN-DQ-002"]
                self.assertEqual(signal.state, expected)

    def test_regulatory_event_requires_confirmed_status_known_time_and_reviewed_scope(self) -> None:
        dataset = synthetic_dataset()
        code = dataset.codes[0]
        cutoff = datetime(2026, 10, 10, 12, tzinfo=timezone.utc)
        event = {"event_id": "synthetic-event", "fund_code": code, "event_type": "SPK_LIQUIDATION_ORDER",
                 "status": "CONFIRMED", "effective_date": date(2026, 9, 17),
                 "available_at": datetime(2026, 9, 17, 12, tzinfo=timezone.utc),
                 "confirmed_at": datetime(2026, 9, 18, 12, tzinfo=timezone.utc),
                 "source_id": "spk-bulletins", "source_sha256": "c" * 64,
                 "metadata": {"bulletin_id": "2026-61"}}
        cases = (({}, "TRIGGERED"), ({"status": "CANDIDATE"}, "ABSTAINED"),
                 ({"confirmed_at": None}, "ABSTAINED"),
                 ({"confirmed_at": cutoff + timedelta(seconds=1)}, "ABSTAINED"),
                 ({"available_at": None}, "ABSTAINED"),
                 ({"available_at": cutoff + timedelta(seconds=1)}, "ABSTAINED"),
                 ({"effective_date": date(2026, 10, 11)}, "ABSTAINED"),
                 ({"event_type": "UNREVIEWED_EVENT"}, "ABSTAINED"),
                 ({"source_id": "unreviewed-source"}, "ABSTAINED"),
                 ({"metadata": {"bulletin_id": "2026-60"}}, "ABSTAINED"))
        scores = pipeline.calculate_scores(dataset)[code]
        for changes, expected in cases:
            with self.subTest(changes=changes):
                fixture = replace(dataset, events={code: ({**event, **changes},)})
                signal = by_detector(pipeline.evaluate_fund(fixture, code, cutoff, {}, scores))["AN-FND-005"]
                self.assertEqual(signal.state, expected)
                self.assertEqual(signal.metadata["source_scope"], "SPK 2026/61 only")
                if expected == "TRIGGERED":
                    self.assertEqual(signal.available_at, event["available_at"])
                    self.assertEqual(signal.metadata["event_ids"], [event["event_id"]])
                else:
                    self.assertIsNone(signal.available_at)

    def test_absent_event_is_scope_limited_abstention(self) -> None:
        dataset = synthetic_dataset()
        signal = by_detector(pipeline.evaluate_fund(dataset, dataset.codes[0], fixture_cutoff(dataset), {}))["AN-FND-005"]
        self.assertEqual(signal.state, "ABSTAINED")
        self.assertEqual(signal.reason, "SOURCE_SCOPE_LIMITED")

    def test_empty_calendar_reports_all_coverage_states_without_invented_history(self) -> None:
        dataset = small_price_dataset((), [])
        cutoff = datetime(2026, 10, 10, 12, tzinfo=timezone.utc)
        signals = by_detector(pipeline.evaluate_fund(dataset, dataset.codes[0], cutoff, {}))
        self.assertEqual(set(signals), set(pipeline.DETECTOR_IDS))
        self.assertEqual(signals["AN-DQ-002"].state, "TRIGGERED")
        for detector in (*pipeline.PERCENTILES, "D5", "AN-DQ-001", "AN-FND-005"):
            self.assertEqual(signals[detector].state, "ABSTAINED", detector)


if __name__ == "__main__":
    unittest.main()
