from __future__ import annotations

import hashlib
import unittest
from dataclasses import FrozenInstanceError, replace
from decimal import Decimal, Inexact, ROUND_DOWN, ROUND_UP, Rounded, localcontext

from p50k.detectors.fund_allocation import calculate_allocation_change, evaluate_allocation
from p50k.evidence_store import EvidenceStore, Observation
from p50k.replay import ReplayCursor

LOCATOR = "synthetic://fund-allocation-test"
SOURCES = {LOCATOR: hashlib.sha256(b"authored fund-allocation fixture").hexdigest()}
IMPORTED = "2026-10-08T12:00:00Z"
CUTOFF = "2026-09-03T12:00:00Z"


def fractions(**weights: str) -> dict[str, Decimal]:
    return {category: Decimal(value) for category, value in weights.items()}


def period_row(key: str, period: str, effective: str, published: str,
               weights: dict[str, Decimal], **changes) -> Observation:
    attributes = {
        "kind": "ASSET_ALLOCATION", "period": period, "cadence": "MONTHLY",
        "fund_scope": "single-class-fund", "share_class": "class-a",
        "valuation_timezone": "Europe/Istanbul", "allocation_basis": "MONTHLY_AVERAGE",
        "category_schema_id": "authored-asset-class-schema-v1", "categories": tuple(weights),
        "category_mapping_status": "VERIFIED", "category_coverage": "COMPLETE",
        "source_weight_unit": "PERCENT", "source_weight_unit_status": "VERIFIED",
        "weights_normalization": "NONE",
    }
    payload = dict(
        observation_key=key, fund="SYN", source_id="SYNTHETIC_ALLOCATION", source_version="v1",
        locator=LOCATOR, origin="SYNTHETIC", values=weights,
        units={category: "FRACTION" for category in weights}, effective_at=effective,
        published_at=published, available_at=published, observed_at=published,
        ingested_at=IMPORTED, availability_provenance="OBSERVED", rights_status="SYNTHETIC",
        source_timestamps={}, attributes=attributes,
        limitations=("Authored synthetic fixture; no provider entitlement or performance claim.",),
    )
    payload.update(changes)
    return Observation(**payload)


def with_metadata(row: Observation, **changes) -> Observation:
    return replace(row, attributes={**row.attributes, **changes})


class AllocationChangeTest(unittest.TestCase):
    def test_no_composition_change_has_zero_distance(self):
        weights = fractions(equity="0.8", cash="0.2", debt="0")
        result = calculate_allocation_change(weights, weights)
        self.assertEqual((result.distance, result.max_category_delta, result.screen_crossing),
                         (Decimal(0), Decimal(0), False))
        self.assertFalse(result.reasons)

    def test_twenty_percentage_point_shift_is_inclusive(self):
        result = calculate_allocation_change(fractions(equity="0.8", cash="0.2"),
                                             fractions(equity="0.6", cash="0.4"))
        self.assertEqual((result.distance, result.max_category_delta), (Decimal("0.20"), Decimal("0.20")))
        self.assertTrue(result.screen_crossing)

    def test_aggregated_shift_can_cross_without_any_category_crossing(self):
        result = calculate_allocation_change(fractions(a="0.25", b="0.25", c="0.25", d="0.25"),
                                             fractions(a="0.4", b="0.4", c="0.1", d="0.1"))
        self.assertEqual((result.distance, result.max_category_delta), (Decimal("0.30"), Decimal("0.15")))
        self.assertTrue(result.screen_crossing)

    def test_full_replacement_is_distance_one_and_deltas_are_signed(self):
        result = calculate_allocation_change(fractions(equity="1", cash="0"),
                                             fractions(equity="0", cash="1"))
        self.assertEqual((result.distance, result.max_category_delta), (Decimal(1), Decimal(1)))
        self.assertEqual(result.category_deltas, (("cash", Decimal(1)), ("equity", Decimal(-1))))

    def test_category_order_does_not_change_the_result(self):
        opening = fractions(equity="0.8", cash="0.2")
        closing = fractions(equity="0.65", cash="0.35")
        expected = calculate_allocation_change(opening, closing)
        actual = calculate_allocation_change(dict(reversed(tuple(opening.items()))),
                                            dict(reversed(tuple(closing.items()))))
        self.assertEqual(actual, expected)
        self.assertFalse(actual.screen_crossing)

    def test_missing_empty_invalid_and_incomplete_category_mappings_are_missing(self):
        normal = fractions(equity="1", cash="0")
        for invalid in (None, {}, [], "weights", {"": Decimal(1)}, {"UNKNOWN": Decimal(1)},
                        {1: Decimal(1)}, fractions(equity="1")):
            for previous, current in ((invalid, normal), (normal, invalid)):
                with self.subTest(invalid=invalid, previous=previous is invalid):
                    result = calculate_allocation_change(previous, current)
                    self.assertIsNone(result.distance)
                    self.assertIsNone(result.max_category_delta)
                    self.assertIsNone(result.screen_crossing)
                    self.assertEqual(result.category_deltas, ())
                    self.assertTrue(result.reasons)

    def test_missing_nondecimal_nonfinite_or_out_of_bounds_weights_are_not_repaired(self):
        normal = fractions(equity="0.8", cash="0.2")
        invalids = (None, 0.8, True, "0.8", Decimal("NaN"), Decimal("sNaN"), Decimal("Infinity"),
                    Decimal("-Infinity"), Decimal("-0.1"), Decimal("1.1"))
        for invalid in invalids:
            for side in (0, 1):
                pair = [normal, normal]
                pair[side] = {"equity": invalid, "cash": Decimal("0.2")}
                with self.subTest(invalid=invalid, side=side):
                    result = calculate_allocation_change(*pair)
                    self.assertIsNone(result.screen_crossing)
                    self.assertTrue(result.reasons)

    def test_signed_leverage_distribution_is_not_normalized(self):
        result = calculate_allocation_change(fractions(equity="1.2", derivative="-0.2"),
                                             fractions(equity="1", derivative="0"))
        self.assertIsNone(result.distance)
        self.assertIn("previous_weight_out_of_bounds:derivative", result.reasons)

    def test_rounded_totals_are_rejected_instead_of_normalized(self):
        exact = fractions(a="0.3333", b="0.3333", c="0.3334")
        for rounded in (fractions(a="0.3333", b="0.3333", c="0.3333"),
                        fractions(a="0.3334", b="0.3334", c="0.3333")):
            with self.subTest(rounded=rounded):
                result = calculate_allocation_change(exact, rounded)
                self.assertEqual(result.reasons, ("current_weights_do_not_sum_to_one",))
                self.assertIsNone(result.distance)

    def test_tiny_total_error_is_not_rounded_into_a_valid_distribution(self):
        near_one = Decimal("0." + "9" * 200)
        result = calculate_allocation_change(fractions(a="1", b="0"), {"a": near_one, "b": Decimal(0)})
        self.assertEqual(result.reasons, ("current_weights_do_not_sum_to_one",))
        self.assertIsNone(result.distance)

    def test_precision_rounding_and_traps_do_not_change_results_or_caller_context(self):
        opening = fractions(a="0.600000000000000000000001", b="0.399999999999999999999999")
        closing = fractions(a="0.8", b="0.2")
        expected = calculate_allocation_change(opening, closing)
        self.assertEqual(expected.distance, Decimal("0.199999999999999999999999"))
        self.assertFalse(expected.screen_crossing)
        for rounding in (ROUND_DOWN, ROUND_UP):
            with self.subTest(rounding=rounding), localcontext() as context:
                context.prec, context.rounding, context.Emin, context.Emax = 2, rounding, -2, 2
                context.traps[Inexact] = context.traps[Rounded] = True
                self.assertEqual(calculate_allocation_change(opening, closing), expected)
                self.assertEqual((context.prec, context.rounding, context.Emin, context.Emax), (2, rounding, -2, 2))
                self.assertTrue(context.traps[Inexact] and context.traps[Rounded])

    def test_bounded_exact_precision_and_extreme_numeric_zero(self):
        exact = {"a": Decimal("1"), "b": Decimal("0E-999999")}
        self.assertEqual(calculate_allocation_change(exact, exact).distance, Decimal(0))
        unsupported = {"a": Decimal("1"), "b": Decimal("1E-4097")}
        result = calculate_allocation_change(exact, unsupported)
        self.assertIn("current_weight_precision_out_of_bounds:b", result.reasons)
        self.assertIsNone(result.distance)
        too_many = {str(index): Decimal(0) for index in range(1001)}
        self.assertIn("previous_category_count_out_of_bounds",
                      calculate_allocation_change(too_many, exact).reasons)

    def test_metric_is_immutable(self):
        result = calculate_allocation_change(fractions(a="1"), fractions(a="1"))
        with self.assertRaises(FrozenInstanceError):
            result.distance = Decimal(1)


class AllocationEvaluationTest(unittest.TestCase):
    def setUp(self):
        self.store = EvidenceStore()
        self.addCleanup(self.store.close)
        self.previous = period_row("opening", "2026-07", "2026-07-31T18:00:00Z", "2026-08-03T09:00:00Z",
                                   fractions(equity="0.8", cash="0.2"))
        self.current = period_row("closing", "2026-08", "2026-08-31T18:00:00Z", "2026-09-02T09:00:00Z",
                                  fractions(equity="0.6", cash="0.4"))

    def cursor(self, rows=None, cutoff=CUTOFF):
        if rows is None:
            rows = (self.previous, self.current)
        bundle = self.store.import_bundle(rows, sources=SOURCES, imported_at=IMPORTED)
        return ReplayCursor(self.store, bundle, cutoff)

    def evaluate(self, previous=None, current=None, *, extra=(), cutoff=CUTOFF):
        rows = (previous or self.previous, current or self.current, *extra)
        return evaluate_allocation(self.cursor(rows, cutoff), "opening", "closing")

    def assert_abstained(self, result, reason=None):
        self.assertEqual(result.status, "ABSTAINED")
        self.assertTrue(result.reasons)
        self.assertEqual(result.evidence_ids, ())
        self.assertIsNone(result.metric.distance)
        self.assertIsNone(result.metric.max_category_delta)
        self.assertIsNone(result.metric.screen_crossing)
        self.assertEqual(result.metric.category_deltas, ())
        if reason is not None:
            self.assertIn(reason, result.reasons)

    def test_admitted_positive_and_normal_control_with_no_baseline_requirement(self):
        for equity, cash, status in (("0.6", "0.4", "TRIGGERED"), ("0.75", "0.25", "NOT_TRIGGERED"),
                                     ("0.8", "0.2", "NOT_TRIGGERED")):
            with self.subTest(equity=equity):
                result = self.evaluate(current=replace(self.current, values=fractions(equity=equity, cash=cash)))
                self.assertEqual(result.status, status)
                self.assertEqual(result.evidence_ids, ("closing@v1", "opening@v1"))
                self.assertEqual(result.reasons, ("allocation_composition_change_not_trade_turnover",
                                                 "monthly_average_composition_not_month_end_holdings"))

    def test_threshold_boundary_is_not_changed_by_caller_rounding(self):
        for equity, cash, status in (("0.6", "0.4", "TRIGGERED"),
                                     ("0.600000000000000000000001", "0.399999999999999999999999", "NOT_TRIGGERED")):
            with self.subTest(equity=equity), localcontext() as context:
                context.prec, context.rounding = 2, ROUND_UP
                context.traps[Inexact] = True
                current = replace(self.current, values=fractions(equity=equity, cash=cash))
                self.assertEqual(self.evaluate(current=current).status, status)

    def test_aggregate_distance_trigger_is_used_in_production(self):
        opening = fractions(a="0.25", b="0.25", c="0.25", d="0.25")
        closing = fractions(a="0.4", b="0.4", c="0.1", d="0.1")
        previous = period_row("opening", "2026-07", self.previous.effective_at, self.previous.published_at, opening)
        current = period_row("closing", "2026-08", self.current.effective_at, self.current.published_at, closing)
        result = self.evaluate(previous, current)
        self.assertEqual(result.status, "TRIGGERED")
        self.assertEqual(result.metric.max_category_delta, Decimal("0.15"))

    def test_month_end_and_monthly_average_basis_stay_distinct(self):
        previous = with_metadata(self.previous, allocation_basis="MONTH_END")
        current = with_metadata(self.current, allocation_basis="MONTH_END")
        result = self.evaluate(previous, current)
        self.assertEqual(result.status, "TRIGGERED")
        self.assertIn("month_end_composition", result.reasons)
        self.assert_abstained(self.evaluate(previous=previous), "allocation_basis_mismatch")

    def test_same_fund_scope_class_source_and_timezone_are_required(self):
        for changes, reason in (({"fund": "OTHER"}, "fund_mismatch"),
                                ({"source_id": "OTHER_SOURCE"}, "allocation_source_mismatch")):
            with self.subTest(changes=changes):
                self.assert_abstained(self.evaluate(current=replace(self.current, **changes)), reason)
        for field, value in (("fund_scope", "another-scope"), ("share_class", "other-class"),
                             ("valuation_timezone", "UTC")):
            with self.subTest(field=field):
                self.assert_abstained(self.evaluate(current=with_metadata(self.current, **{field: value})),
                                      "scope_class_or_timezone_mismatch")

    def test_missing_and_unverified_metadata_default_to_abstention(self):
        fields = ("kind", "fund_scope", "share_class", "valuation_timezone", "allocation_basis",
                  "category_schema_id", "category_mapping_status", "category_coverage", "source_weight_unit",
                  "source_weight_unit_status", "weights_normalization", "cadence", "period", "categories")
        for field in fields:
            for invalid in (None, "UNKNOWN", "UNVERIFIED"):
                with self.subTest(field=field, invalid=invalid):
                    current = with_metadata(self.current, **{field: invalid})
                    self.assert_abstained(self.evaluate(current=current))
        self.assert_abstained(self.evaluate(current=replace(self.current, attributes={})))

    def test_category_schema_must_be_complete_unambiguous_and_identical(self):
        for categories in (("equity",), ("equity", "cash", "missing"), ("equity", "cash", "cash"),
                           (), (None, "cash"), ({"bad": "category"}, "cash")):
            with self.subTest(categories=categories):
                self.assert_abstained(self.evaluate(current=with_metadata(self.current, categories=categories)),
                                      "complete_category_schema_required")
        self.assert_abstained(self.evaluate(current=with_metadata(self.current, category_schema_id="new-schema")),
                              "category_schema_mismatch")
        current = replace(self.current, values=fractions(equity="1"), units={"equity": "FRACTION"},
                          attributes={**self.current.attributes, "categories": ("equity",)})
        self.assert_abstained(self.evaluate(current=current), "category_schema_mismatch")

    def test_source_units_are_explicit_and_normalization_is_not_admitted(self):
        for unit in ("PERCENT", "TRY", "UNKNOWN"):
            with self.subTest(unit=unit):
                current = replace(self.current, units={"equity": unit, "cash": "FRACTION"})
                self.assert_abstained(self.evaluate(current=current), "fraction_units_required")
        for unit in ("UNKNOWN", "TRY", "BASIS_POINTS"):
            with self.subTest(source_unit=unit):
                current = with_metadata(self.current, source_weight_unit=unit)
                self.assert_abstained(self.evaluate(current=current), "source_weight_unit_unverified")
        for normalization in (None, "SUM_NORMALIZED", "SIGNED_TO_POSITIVE", "UNKNOWN"):
            with self.subTest(normalization=normalization):
                current = with_metadata(self.current, weights_normalization=normalization)
                self.assert_abstained(self.evaluate(current=current), "normalized_or_unverified_weights_not_admitted")
        current = with_metadata(self.current, source_weight_unit="FRACTION")
        self.assertEqual(self.evaluate(current=current).status, "TRIGGERED")

    def test_rounded_or_signed_source_weights_abstain_without_metrics(self):
        for weights in (fractions(equity="0.5999", cash="0.4"), fractions(equity="1.1", cash="-0.1"),
                        {"equity": Decimal("0.6"), "cash": None}):
            with self.subTest(weights=weights):
                self.assert_abstained(self.evaluate(current=replace(self.current, values=weights)))

    def test_unverified_or_restricted_real_data_rights_abstain(self):
        for rights in ("UNKNOWN", "RESTRICTED"):
            previous = replace(self.previous, origin="HISTORICAL_REPLAY", rights_status=rights)
            current = replace(self.current, origin="HISTORICAL_REPLAY", rights_status=rights)
            with self.subTest(rights=rights):
                self.assert_abstained(self.evaluate(previous, current), "data_rights_unverified")
        previous = replace(self.previous, origin="HISTORICAL_REPLAY", rights_status="APPROVED")
        current = replace(self.current, origin="HISTORICAL_REPLAY", rights_status="APPROVED")
        self.assertEqual(self.evaluate(previous, current).status, "TRIGGERED")
        self.assert_abstained(self.evaluate(previous=previous), "origin_or_rights_mismatch")

    def test_unknown_missing_or_inconsistent_source_timing_abstains(self):
        for field in ("effective_at", "published_at", "observed_at"):
            with self.subTest(field=field):
                self.assert_abstained(self.evaluate(current=replace(self.current, **{field: None})),
                                      "source_timing_unverified")
        current = replace(self.current, availability_provenance="UNKNOWN", available_at=None)
        self.assert_abstained(self.evaluate(current=current), "selected_evidence_unavailable_at_cutoff")
        for changes in ({"published_at": "2026-08-30T09:00:00Z"},
                        {"available_at": "2026-09-01T09:00:00Z"},
                        {"observed_at": "2026-09-01T09:00:00Z"}):
            with self.subTest(changes=changes):
                self.assert_abstained(self.evaluate(current=replace(self.current, **changes)),
                                      "source_timing_inconsistent")
        self.assertEqual(self.evaluate(current=replace(self.current, availability_provenance="ARCHIVE_VERIFIED")).status,
                         "TRIGGERED")

    def test_replay_checks_effective_publication_availability_and_receipt_cutoffs(self):
        for field in ("effective_at", "published_at", "available_at", "observed_at"):
            with self.subTest(field=field):
                current = replace(self.current, **{field: "2026-09-04T09:00:00Z"})
                self.assert_abstained(self.evaluate(current=current), "selected_evidence_unavailable_at_cutoff")
        self.assert_abstained(self.evaluate(cutoff="2026-09-02T08:59:59Z"),
                              "selected_evidence_unavailable_at_cutoff")
        self.assertEqual(self.evaluate(cutoff="2026-09-02T09:00:00Z").status, "TRIGGERED")

    def test_period_gaps_reversals_wrong_cadence_and_invalid_periods_abstain(self):
        for period in ("2026-07", "2026-06", "2026-10", "2026-13", "0000-08", "2026-8", "UNKNOWN"):
            with self.subTest(period=period):
                self.assert_abstained(self.evaluate(current=with_metadata(self.current, period=period)),
                                      "consecutive_monthly_periods_required")
        self.assert_abstained(self.evaluate(current=with_metadata(self.current, cadence="WEEKLY")),
                              "monthly_period_unverified")
        self.assert_abstained(evaluate_allocation(self.cursor(), "closing", "opening"),
                              "consecutive_monthly_periods_required")

    def test_report_effective_date_must_match_report_month_end_and_timezone(self):
        current = replace(self.current, effective_at="2026-08-30T18:00:00Z")
        self.assert_abstained(self.evaluate(current=current), "effective_date_not_period_month_end")
        current = replace(self.current, effective_at="2026-08-31T22:00:00Z")
        self.assert_abstained(self.evaluate(current=current), "effective_date_not_period_month_end")
        current = with_metadata(self.current, valuation_timezone="Not/A_Timezone")
        self.assert_abstained(self.evaluate(current=current), "valuation_timezone_unverified")

    def test_year_boundary_consecutive_periods_are_supported(self):
        previous = period_row("opening", "2025-12", "2025-12-31T18:00:00Z", "2026-01-02T09:00:00Z",
                              fractions(equity="0.8", cash="0.2"))
        current = period_row("closing", "2026-01", "2026-01-31T18:00:00Z", "2026-02-02T09:00:00Z",
                             fractions(equity="0.6", cash="0.4"))
        self.assertEqual(self.evaluate(previous, current).status, "TRIGGERED")

    def test_only_an_immutable_cursor_and_distinct_existing_keys_are_accepted(self):
        self.assert_abstained(evaluate_allocation(None, "opening", "closing"), "replay_cursor_required")
        cursor = self.cursor()
        for previous, current in (("opening", "opening"), (None, "closing"), ("UNKNOWN", "closing")):
            with self.subTest(previous=previous, current=current):
                self.assert_abstained(evaluate_allocation(cursor, previous, current),
                                      "distinct_period_evidence_keys_required")
        self.assert_abstained(evaluate_allocation(cursor, "opening", "missing"),
                              "selected_evidence_unavailable_at_cutoff")
        with self.assertRaises(FrozenInstanceError):
            cursor.cutoff = "2026-10-01T00:00:00Z"

    def test_later_added_or_altered_future_revision_cannot_change_earlier_decision(self):
        frozen_cursor = self.cursor()
        earlier = evaluate_allocation(frozen_cursor, "opening", "closing")
        for weights in (fractions(equity="0.8", cash="0.2"), fractions(equity="0.1", cash="0.9")):
            future = replace(self.current, source_version="later", values=weights,
                             published_at="2026-09-10T09:00:00Z", available_at="2026-09-10T09:00:00Z",
                             observed_at="2026-09-10T09:00:00Z")
            with self.subTest(weights=weights):
                self.assertEqual(self.evaluate(extra=(future,)), earlier)
                self.assertEqual(evaluate_allocation(frozen_cursor, "opening", "closing"), earlier)
                self.assertNotIn("closing@later", self.evaluate(extra=(future,)).evidence_ids)
        future = replace(self.current, source_version="later-normal", values=fractions(equity="0.8", cash="0.2"),
                         published_at="2026-09-10T09:00:00Z", available_at="2026-09-10T09:00:00Z",
                         observed_at="2026-09-10T09:00:00Z")
        later = self.evaluate(extra=(future,), cutoff="2026-09-10T09:00:00Z")
        self.assertEqual(later.status, "NOT_TRIGGERED")
        self.assertIn("closing@later-normal", later.evidence_ids)

    def test_ambiguous_eligible_revisions_abstain_even_if_values_match(self):
        conflicting = replace(self.current, source_version="unordered-v2")
        self.assert_abstained(self.evaluate(extra=(conflicting,)), "eligible_revision_order_unresolved")

    def test_late_observed_revision_does_not_inherit_old_publication_eligibility(self):
        future_receipt = replace(self.current, source_version="received-later", values=fractions(equity="0.8", cash="0.2"),
                                 observed_at="2026-10-07T12:00:00Z")
        self.assertEqual(self.evaluate(extra=(future_receipt,)), self.evaluate())

    def test_evaluation_and_numeric_result_are_immutable(self):
        result = self.evaluate()
        with self.assertRaises(FrozenInstanceError):
            result.status = "NOT_TRIGGERED"
        with self.assertRaises(FrozenInstanceError):
            result.metric.distance = Decimal(0)


if __name__ == "__main__":
    unittest.main()
