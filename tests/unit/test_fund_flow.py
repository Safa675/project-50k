from __future__ import annotations

import hashlib
import unittest
from dataclasses import FrozenInstanceError, replace
from decimal import Decimal, Inexact, ROUND_DOWN, ROUND_UP, Rounded, localcontext

from p50k.detectors.fund_flow import BaselineCheck, calculate_endpoint_change, evaluate_flow
from p50k.evidence_store import EvidenceStore, Observation
from p50k.replay import ReplayCursor

LOCATOR = "synthetic://fund-flow-test"
SOURCES = {LOCATOR: hashlib.sha256(b"authored fund-flow fixture").hexdigest()}
IMPORTED = "2026-09-04T12:00:00Z"
CUTOFF = "2026-09-03T12:00:00Z"


def period_row(key: str, period: str, effective: str, published: str,
               assets: str = "1000", nav: str = "10", **changes) -> Observation:
    attributes = {
        "period": period, "cadence": "MONTHLY", "fund_scope": "single-class-fund",
        "share_class": "class-a", "currency": "TRY", "valuation_timezone": "Europe/Istanbul",
        "valuation_basis": "MONTH_END", "assets_effective_at": effective, "nav_effective_at": effective,
        "asset_basis": "NET_ASSETS", "nav_basis": "RAW_TRANSACTION_NAV",
        "distribution_status": "VERIFIED_NONE", "unit_change_status": "VERIFIED_NONE", "merger_status": "VERIFIED_NONE",
    }
    payload = dict(
        observation_key=key, fund="SYN", source_id="SYNTHETIC_FLOW", source_version="v1",
        locator=LOCATOR, origin="SYNTHETIC", values={"total_value": Decimal(assets), "nav": Decimal(nav)},
        units={"total_value": "TRY", "nav": "TRY/unit"}, effective_at=effective,
        published_at=published, available_at=published, observed_at=published, ingested_at=IMPORTED,
        availability_provenance="OBSERVED", rights_status="SYNTHETIC", source_timestamps={},
        attributes=attributes, limitations=("Authored synthetic fixture; no provider entitlement or performance claim.",),
    )
    payload.update(changes)
    return Observation(**payload)


def with_metadata(row: Observation, **changes) -> Observation:
    return replace(row, attributes={**row.attributes, **changes})


class EndpointChangeTest(unittest.TestCase):
    def calculate(self, assets="1200", nav="12"):
        return calculate_endpoint_change(Decimal("1000"), Decimal(assets), Decimal("10"), Decimal(nav))

    def test_investment_return_alone_has_zero_residual(self):
        for assets, nav in (("1200", "12"), ("800", "8")):
            with self.subTest(assets=assets):
                result = self.calculate(assets, nav)
                self.assertEqual((result.residual, result.rate, result.reasons), (Decimal("0"), Decimal("0"), ()))

    def test_signed_changes_and_zero_closing_assets(self):
        for assets, nav, residual, rate in (("1320", "12", "120", "0.12"), ("1080", "12", "-120", "-0.12"),
                                          ("0", "10", "-1000", "-1")):
            with self.subTest(assets=assets):
                result = self.calculate(assets, nav)
                self.assertEqual((result.residual, result.rate), (Decimal(residual), Decimal(rate)))
                self.assertFalse(result.reasons)

    def test_missing_invalid_signs_nonfinite_and_float_are_explicit(self):
        invalid = (None, Decimal("NaN"), Decimal("sNaN"), Decimal("Infinity"), Decimal("-Infinity"), 1.0, True, "10")
        for index in range(4):
            for value in invalid:
                numbers = [Decimal("1000"), Decimal("1100"), Decimal("10"), Decimal("10")]
                numbers[index] = value
                with self.subTest(index=index, value=value):
                    result = calculate_endpoint_change(*numbers)
                    self.assertIsNone(result.residual)
                    self.assertIsNone(result.rate)
                    self.assertTrue(result.reasons)
        for index in range(4):
            for value in (Decimal("0"), Decimal("-1")):
                if index == 1 and value == 0:
                    continue
                numbers = [Decimal("1000"), Decimal("1100"), Decimal("10"), Decimal("10")]
                numbers[index] = value
                with self.subTest(index=index, value=value):
                    self.assertIsNone(calculate_endpoint_change(*numbers).rate)

    def test_precision_rounding_exponents_and_traps_are_context_independent(self):
        values = (Decimal("11"), Decimal("17"), Decimal("3"), Decimal("7"))
        expected = calculate_endpoint_change(*values)
        for rounding in (ROUND_DOWN, ROUND_UP):
            with localcontext() as context:
                context.prec, context.rounding, context.Emin, context.Emax = 2, rounding, -2, 2
                context.traps[Inexact] = context.traps[Rounded] = True
                self.assertEqual(calculate_endpoint_change(*values), expected)
                self.assertEqual((context.prec, context.rounding, context.Emin, context.Emax), (2, rounding, -2, 2))
                self.assertTrue(context.traps[Inexact] and context.traps[Rounded])

    def test_unrepresentable_arithmetic_stays_missing(self):
        result = calculate_endpoint_change(Decimal("1E999999"), Decimal("1"), Decimal("1"), Decimal("10"))
        self.assertEqual(result.reasons, ("arithmetic_not_representable",))
        self.assertIsNone(result.rate)

    def test_result_is_frozen(self):
        with self.assertRaises(FrozenInstanceError):
            self.calculate().rate = Decimal("1")


class FlowEvaluationTest(unittest.TestCase):
    def setUp(self):
        self.store = EvidenceStore()
        self.addCleanup(self.store.close)
        self.previous = period_row("opening", "2026-07", "2026-07-31T18:00:00Z", "2026-08-03T09:00:00Z")
        self.current = period_row("closing", "2026-08", "2026-08-31T18:00:00Z", "2026-09-02T09:00:00Z", assets="1150")
        self.history = period_row("history", "2026-06", "2026-06-30T18:00:00Z", "2026-07-02T09:00:00Z")
        self.check = period_row("baseline", "2026-06", "2026-07-05T12:00:00Z", "2026-07-05T13:00:00Z")
        self.check = with_metadata(self.check, baseline_status="PASSED", baseline_config_id="authored-synthetic-baseline-v1",
                                   baseline_input_keys=("history",), baseline_input_versions={"history": "v1"})
        self.baseline = BaselineCheck("PASSED", "authored-synthetic-baseline-v1", ("baseline",))

    def cursor(self, rows=None, cutoff=CUTOFF):
        if rows is None:
            rows = (self.previous, self.current, self.history, self.check)
        bundle = self.store.import_bundle(rows, sources=SOURCES, imported_at=IMPORTED)
        return ReplayCursor(self.store, bundle, cutoff)

    def evaluate(self, previous=None, current=None, *, baseline=None, extra=(), cutoff=CUTOFF):
        rows = (previous or self.previous, current or self.current, self.history, self.check, *extra)
        return evaluate_flow(self.cursor(rows, cutoff), "opening", "closing", baseline=self.baseline if baseline is None else baseline)

    def assert_abstained(self, result, reason=None):
        self.assertEqual(result.status, "ABSTAINED")
        self.assertEqual(result.evidence_ids, ())
        self.assertIsNone(result.metric.residual)
        self.assertIsNone(result.metric.rate)
        self.assertTrue(result.reasons)
        if reason is not None:
            self.assertIn(reason, result.reasons)

    def test_positive_and_negative_fixed_threshold_cases(self):
        for assets, status, rate in (("1150", "TRIGGERED", "0.15"), ("850", "TRIGGERED", "-0.15"),
                                     ("1050", "NOT_TRIGGERED", "0.05"), ("1000", "NOT_TRIGGERED", "0")):
            current = replace(self.current, values={"total_value": Decimal(assets), "nav": Decimal("10")})
            with self.subTest(assets=assets):
                result = self.evaluate(current=current)
                self.assertEqual(result.status, status)
                self.assertEqual(result.metric.rate, Decimal(rate))
                self.assertEqual(set(result.evidence_ids), {"opening@v1", "closing@v1", "baseline@v1", "history@v1"})
                self.assertEqual(result.reasons, ("conditional_endpoint_residual_not_reported_cash",))

    def test_positive_and_negative_ten_percent_boundaries_are_inclusive(self):
        for assets, status in (("1100", "TRIGGERED"), ("900", "TRIGGERED"),
                               ("1099.999999", "NOT_TRIGGERED"), ("900.000001", "NOT_TRIGGERED")):
            with self.subTest(assets=assets), localcontext() as context:
                context.prec = 2
                context.rounding = ROUND_UP
                context.traps[Inexact] = True
                result = self.evaluate(current=replace(self.current, values={"total_value": Decimal(assets), "nav": Decimal("10")}))
                self.assertEqual(result.status, status)

    def test_default_and_failed_baseline_abstain_even_below_threshold(self):
        cursor = self.cursor()
        for baseline in (None, BaselineCheck(), BaselineCheck("FAILED")):
            with self.subTest(baseline=baseline):
                self.assert_abstained(evaluate_flow(cursor, "opening", "closing", baseline=baseline), "baseline_unverified")

    def test_baseline_requires_stored_matching_config_and_input_evidence(self):
        for baseline in (BaselineCheck("PASSED"), BaselineCheck("PASSED", "config", ()),
                         BaselineCheck("PASSED", "wrong-config", ("baseline",)),
                         BaselineCheck("PASSED", self.baseline.config_id, ("missing",))):
            with self.subTest(baseline=baseline):
                self.assert_abstained(self.evaluate(baseline=baseline))
        for metadata in ({"baseline_status": "UNVERIFIED"}, {"baseline_input_keys": ()},
                         {"baseline_input_keys": ("closing",)}, {"baseline_input_keys": ("missing",)},
                         {"baseline_input_versions": {}}, {"baseline_input_versions": {"history": "future-version"}},
                         {"baseline_input_keys": ({"invalid": "key"},)}):
            check = with_metadata(self.check, **metadata)
            with self.subTest(metadata=metadata):
                result = evaluate_flow(self.cursor((self.previous, self.current, self.history, check)),
                                       "opening", "closing", baseline=self.baseline)
                self.assert_abstained(result)

    def test_baseline_future_inputs_and_late_configuration_abstain(self):
        for history in (replace(self.history, effective_at=self.previous.effective_at),
                        replace(self.history, published_at="2026-09-04T00:00:00Z", available_at="2026-09-04T00:00:00Z",
                                observed_at="2026-09-04T00:00:00Z")):
            with self.subTest(history=history.observation_key):
                self.assert_abstained(evaluate_flow(self.cursor((self.previous, self.current, history, self.check)),
                                                    "opening", "closing", baseline=self.baseline))
        check = replace(self.check, published_at="2026-08-01T00:00:00Z", available_at="2026-08-01T00:00:00Z",
                        observed_at="2026-08-01T00:00:00Z")
        self.assert_abstained(evaluate_flow(self.cursor((self.previous, self.current, self.history, check)),
                                           "opening", "closing", baseline=self.baseline),
                             "baseline_check_was_not_fixed_before_opening_period")

    def test_baseline_scope_and_rights_must_match_periods(self):
        history = with_metadata(self.history, share_class="other")
        self.assert_abstained(evaluate_flow(self.cursor((self.previous, self.current, history, self.check)),
                                           "opening", "closing", baseline=self.baseline), "baseline_scope_mismatch")
        rows = tuple(replace(row, origin="HISTORICAL_REPLAY", rights_status="APPROVED")
                     for row in (self.previous, self.current, self.history, self.check))
        self.assertEqual(evaluate_flow(self.cursor(rows), "opening", "closing", baseline=self.baseline).status, "TRIGGERED")
        changed = (*rows[:2], replace(rows[2], rights_status="UNKNOWN"), rows[3])
        self.assert_abstained(evaluate_flow(self.cursor(changed), "opening", "closing", baseline=self.baseline))

    def test_baseline_uses_exact_inputs_at_its_own_check_cutoff(self):
        expected = self.evaluate()
        later_history = replace(self.history, source_version="v2", values={"total_value": Decimal("999999"), "nav": Decimal("12")},
                                published_at="2026-08-01T00:00:00Z", available_at="2026-08-01T00:00:00Z",
                                observed_at="2026-08-01T00:00:00Z")
        self.assertEqual(expected, self.evaluate(extra=(later_history,)))
        result = self.evaluate(extra=(later_history,))
        self.assertIn("history@v1", result.evidence_ids)
        self.assertNotIn("history@v2", result.evidence_ids)

    def test_baseline_cannot_use_history_received_after_its_check(self):
        for field in ("available_at", "published_at", "observed_at"):
            history = replace(self.history, **{field: "2026-07-06T00:00:00Z"})
            with self.subTest(field=field):
                self.assert_abstained(evaluate_flow(self.cursor((self.previous, self.current, history, self.check)),
                                                    "opening", "closing", baseline=self.baseline),
                                      "baseline_prior_inputs_unavailable_or_not_prior")

    def test_baseline_claiming_future_input_version_abstains(self):
        later_history = replace(self.history, source_version="v2", published_at="2026-08-01T00:00:00Z",
                                available_at="2026-08-01T00:00:00Z", observed_at="2026-08-01T00:00:00Z")
        check = with_metadata(self.check, baseline_input_versions={"history": "v2"})
        result = evaluate_flow(self.cursor((self.previous, self.current, self.history, later_history, check)),
                               "opening", "closing", baseline=self.baseline)
        self.assert_abstained(result, "baseline_prior_input_version_mismatch")

    def test_ambiguous_prior_baseline_revision_abstains(self):
        tie = replace(self.history, source_version="tie", values={"total_value": Decimal("1070"), "nav": Decimal("10")})
        self.assert_abstained(self.evaluate(extra=(tie,)), "eligible_revision_order_unresolved")
        later = replace(self.history, source_version="v2", published_at="2026-08-01T00:00:00Z",
                        available_at="2026-08-01T00:00:00Z", observed_at="2026-08-01T00:00:00Z")
        self.assert_abstained(self.evaluate(extra=(tie, later)), "baseline_revision_order_unresolved")

    def test_one_explicit_prior_input_does_not_require_twenty_samples(self):
        self.assertEqual(self.evaluate().status, "TRIGGERED")

    def test_unknown_scope_currency_basis_and_actions_abstain(self):
        for field in ("fund_scope", "share_class", "currency", "valuation_timezone", "asset_basis", "nav_basis",
                      "valuation_basis", "distribution_status", "unit_change_status", "merger_status"):
            with self.subTest(field=field):
                self.assert_abstained(self.evaluate(current=with_metadata(self.current, **{field: "UNKNOWN"})))
        for field in ("distribution_status", "unit_change_status", "merger_status"):
            with self.subTest(field=field):
                self.assert_abstained(self.evaluate(current=with_metadata(self.current, **{field: "PRESENT_RESOLVED"})))

    def test_missing_metadata_cannot_claim_normal(self):
        self.assert_abstained(self.evaluate(current=replace(self.current, attributes={})))

    def test_incompatible_scope_class_currency_and_fund_abstain(self):
        for field, value in (("fund_scope", "other-scope"), ("share_class", "class-b"),
                             ("currency", "USD"), ("valuation_timezone", "UTC")):
            with self.subTest(field=field):
                self.assert_abstained(self.evaluate(current=with_metadata(self.current, **{field: value})))
        self.assert_abstained(self.evaluate(current=replace(self.current, fund="OTHER")), "fund_mismatch")

    def test_currency_assertion_cannot_override_unknown_or_incompatible_units(self):
        for units in ({"total_value": "UNKNOWN_CURRENCY", "nav": "UNKNOWN_CURRENCY/unit"},
                      {"total_value": "TRY", "nav": "USD/unit"}, {"total_value": "USD", "nav": "TRY/unit"}):
            with self.subTest(units=units):
                self.assert_abstained(self.evaluate(current=replace(self.current, units=units)), "currency_or_units_mismatch")

    def test_asset_and_nav_effective_times_must_match(self):
        for value in (None, "2026-08-30T18:00:00Z", "invalid"):
            for field in ("assets_effective_at", "nav_effective_at"):
                with self.subTest(field=field, value=value):
                    self.assert_abstained(self.evaluate(current=with_metadata(self.current, **{field: value})),
                                         "assets_and_nav_valuation_unmatched")

    def test_month_end_respects_explicit_valuation_timezone(self):
        current = replace(self.current, effective_at="2026-08-30T22:00:00Z")
        current = with_metadata(current, assets_effective_at=current.effective_at, nav_effective_at=current.effective_at)
        self.assertEqual(self.evaluate(current=current).status, "TRIGGERED")
        wrong = with_metadata(current, valuation_timezone="UTC")
        previous = with_metadata(self.previous, valuation_timezone="UTC")
        self.assert_abstained(self.evaluate(previous=previous, current=wrong), "valuation_not_period_month_end")

    def test_nonmonthend_invalid_period_and_weekly_cadence_abstain(self):
        for metadata in ({"period": "2026-13"}, {"period": "2026-00"}, {"period": "0000-08"},
                         {"period": "2026-09"}, {"period": "2026-W35", "cadence": "WEEKLY"},
                         {"cadence": "DAILY"}, {"valuation_timezone": "Missing/Zone"}):
            with self.subTest(metadata=metadata):
                self.assert_abstained(self.evaluate(current=with_metadata(self.current, **metadata)))

    def test_gapped_and_reversed_periods_are_not_bridged(self):
        current = period_row("closing", "2026-09", "2026-09-30T18:00:00Z", "2026-10-02T09:00:00Z")
        self.assert_abstained(self.evaluate(current=current, cutoff="2026-10-03T12:00:00Z"), "consecutive_monthly_periods_required")
        self.assert_abstained(evaluate_flow(self.cursor(), "closing", "opening", baseline=self.baseline),
                             "consecutive_monthly_periods_required")

    def test_unknown_rights_and_mixed_origin_abstain(self):
        rows = tuple(replace(row, origin="HISTORICAL_REPLAY", rights_status="UNKNOWN")
                     for row in (self.previous, self.current, self.history, self.check))
        self.assert_abstained(evaluate_flow(self.cursor(rows), "opening", "closing", baseline=self.baseline), "data_rights_unverified")
        current = replace(self.current, origin="HISTORICAL_REPLAY", rights_status="APPROVED")
        self.assert_abstained(self.evaluate(current=current), "origin_or_rights_mismatch")

    def test_missing_publication_receipt_effective_time_and_order_abstain(self):
        for field in ("published_at", "observed_at", "effective_at"):
            with self.subTest(field=field):
                self.assert_abstained(self.evaluate(current=replace(self.current, **{field: None})), "source_timing_unverified")
        row = replace(self.current, available_at="2026-09-01T00:00:00Z")
        self.assert_abstained(self.evaluate(current=row), "source_timing_inconsistent")

    def test_missing_and_unusable_numbers_abstain(self):
        for values in ({"total_value": None, "nav": Decimal("10")}, {"total_value": Decimal("1150"), "nav": None},
                       {"total_value": Decimal("1150"), "nav": Decimal("0")},
                       {"total_value": Decimal("-1"), "nav": Decimal("10")}):
            with self.subTest(values=values):
                self.assert_abstained(self.evaluate(current=replace(self.current, values=values)))

    def test_each_future_source_time_excludes_all_metrics_and_evidence_ids(self):
        for field in ("published_at", "available_at", "observed_at", "effective_at"):
            future = replace(self.current, **{field: "2026-09-04T00:00:00Z"})
            with self.subTest(field=field):
                self.assert_abstained(self.evaluate(current=future), "selected_evidence_unavailable_at_cutoff")

    def test_unknown_availability_never_exposes_numeric_metric(self):
        for available in (None, self.current.available_at):
            with self.subTest(available=available):
                result = self.evaluate(current=replace(self.current, availability_provenance="UNKNOWN", available_at=available))
                self.assert_abstained(result, "selected_evidence_unavailable_at_cutoff")

    def test_changing_future_values_leaves_entire_earlier_result_unchanged(self):
        future = replace(self.current, published_at="2026-09-04T00:00:00Z", available_at="2026-09-04T00:00:00Z",
                         observed_at="2026-09-04T00:00:00Z")
        first = self.evaluate(current=future)
        changed = replace(future, source_version="v2", values={"total_value": Decimal("999999"), "nav": Decimal("12")})
        self.assertEqual(first, self.evaluate(current=changed))

    def test_future_revisions_and_additions_do_not_change_eligible_earlier_output(self):
        expected = self.evaluate()
        future = replace(self.current, source_version="v2", values={"total_value": Decimal("999999"), "nav": Decimal("12")},
                         available_at="2026-09-04T00:00:00Z", published_at="2026-09-04T00:00:00Z", observed_at="2026-09-04T00:00:00Z")
        self.assertEqual(expected, self.evaluate(extra=(future,)))
        changed = replace(future, source_version="v3", attributes={})
        addition = replace(future, observation_key="future-other", fund="OTHER")
        self.assertEqual(expected, self.evaluate(extra=(changed, addition)))

    def test_eligible_revision_updates_and_tied_versions_abstain(self):
        later = replace(self.current, source_version="v2", values={"total_value": Decimal("1020"), "nav": Decimal("10")},
                        published_at="2026-09-02T10:00:00Z", available_at="2026-09-02T10:00:00Z", observed_at="2026-09-02T10:00:00Z")
        result = self.evaluate(extra=(later,))
        self.assertEqual(result.status, "NOT_TRIGGERED")
        self.assertIn("closing@v2", result.evidence_ids)
        tie = replace(self.current, source_version="tie", values={"total_value": Decimal("1070"), "nav": Decimal("10")})
        self.assert_abstained(self.evaluate(extra=(tie,)), "eligible_revision_order_unresolved")

    def test_exact_cutoff_and_equivalent_timezones(self):
        exact = self.current.observed_at
        first = self.evaluate(cutoff=exact)
        self.assertEqual(first.status, "TRIGGERED")
        self.assertEqual(first, self.evaluate(cutoff="2026-09-02T12:00:00+03:00"))

    def test_direct_rows_or_store_cannot_bypass_replay_cursor(self):
        for value in (self.store, self.current, None):
            with self.subTest(value=type(value).__name__):
                self.assert_abstained(evaluate_flow(value, "opening", "closing", baseline=self.baseline), "replay_cursor_required")
        for previous, current in (("opening", "opening"), ("missing", "closing"), (None, "closing")):
            with self.subTest(previous=previous, current=current):
                self.assert_abstained(evaluate_flow(self.cursor(), previous, current, baseline=self.baseline))

    def test_later_import_time_is_not_retrieval_or_publication(self):
        current = replace(self.current, ingested_at="2027-01-01T00:00:00Z")
        self.assertEqual(self.evaluate(), self.evaluate(current=current))

    def test_results_and_baseline_record_are_frozen(self):
        for obj, field, value in ((self.evaluate(), "status", "NOT_TRIGGERED"), (self.baseline, "status", "PASSED")):
            with self.subTest(field=field), self.assertRaises(FrozenInstanceError):
                setattr(obj, field, value)


if __name__ == "__main__":
    unittest.main()
