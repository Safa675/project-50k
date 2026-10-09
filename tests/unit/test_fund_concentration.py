"""Authored holdings, arithmetic, and immutable base-extension tests only."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal, Inexact, InvalidOperation, Rounded, ROUND_DOWN, localcontext
from fractions import Fraction
from pathlib import Path
import tempfile
import unittest

from p50k.providers.security_holdings import SecurityHoldingRow
from p50k.providers.thf_holdings import PrintedNumber
from p50k.research_reviews.bundle import BundleIntegrityError, SourceRegistry, canonical_bytes, digest, write_bundle
from p50k.research_reviews.bundle_v2 import extend_bundle, load_research_bundle, write_research_bundle
from p50k.research_reviews.concentration import calculate_metrics, concentration_finding, empty_concentration, ratio_string
from tests.unit.test_fund_review_bundle import CODES, all_missing_bundle
from tests.unit.test_security_holdings import read


def printed(value: str, *, page=1, row=1) -> PrintedNumber:
    return PrintedNumber(Decimal(value), value, page, (760.0, float(600 + row * 10), 817.0, float(607 + row * 10)))


def row(index: int, value: str, *, identity: str | None = None, kind="EQUITY") -> SecurityHoldingRow:
    number = printed(value, row=index)
    return SecurityHoldingRow(identity if identity is not None else f"TRSYNTH{index:05}", f"Authored {index}",
                              kind, "Authored category", "TL", number, 1, index,
                              (20.0, number.source_bbox[1], 817.0, number.source_bbox[3]))


class ConcentrationArithmeticTests(unittest.TestCase):
    def test_duplicate_isin_lots_aggregate_before_top_n_and_hhi(self):
        result = concentration_finding(read(), source_id="a" * 64)
        self.assertEqual(result["status"], "AVAILABLE", result)
        self.assertEqual(result["position_count"], 2)
        self.assertEqual(result["subset_value"], "100")
        self.assertEqual(result["top1_ratio"], "0.9")
        self.assertEqual(result["top5_ratio"], "1")
        self.assertEqual(result["top10_ratio"], "1")
        self.assertEqual(result["hhi"], "0.82")
        self.assertEqual(result["portfolio_coverage_ratio"], "1")
        self.assertEqual(len(result["positions"][0]["source_rows"]), 2)
        self.assertEqual(result["age_days"], 16)
        self.assertEqual(result["research_screen"], "NOT_SCREENED")
        self.assertEqual(result["production_status"], "ABSTAINED")

    def test_equal_weights_have_deterministic_ties_and_top_ten_limit(self):
        snapshot = replace(read(), rows=tuple(row(index, "10.00") for index in range(12)),
                           portfolio_total=printed("120.00"))
        result = concentration_finding(snapshot, source_id="a" * 64)
        self.assertEqual(result["position_count"], 12)
        self.assertEqual(len(result["positions"]), 10)
        self.assertEqual([position["isin"] for position in result["positions"]], [f"TRSYNTH{index:05}" for index in range(10)])
        self.assertEqual(result["top1_ratio"], ratio_string(Fraction(1, 12)))
        self.assertEqual(result["top5_ratio"], ratio_string(Fraction(5, 12)))
        self.assertEqual(result["top10_ratio"], ratio_string(Fraction(10, 12)))
        self.assertEqual(result["hhi"], ratio_string(Fraction(1, 12)))

    def test_unidentified_security_is_partial_with_subset_denominator(self):
        snapshot = read()
        snapshot = replace(snapshot, rows=(*snapshot.rows[:-1], replace(snapshot.rows[-1], isin=None)))
        result = concentration_finding(snapshot, source_id="a" * 64)
        self.assertEqual(result["status"], "PARTIAL")
        self.assertEqual(result["subset_value"], "90")
        self.assertEqual(result["portfolio_coverage_ratio"], "0.9")
        self.assertEqual(result["top1_ratio"], "1")
        self.assertEqual(result["hhi"], "1")
        self.assertIn("positive_security_without_identified_isin", result["qualifications"])

    def test_printed_rounding_overhang_is_disclosed_without_renormalizing_coverage(self):
        snapshot = read()
        snapshot = replace(snapshot, rows=(replace(snapshot.rows[0], position_value=printed("60.0050")), *snapshot.rows[1:]))
        result = concentration_finding(snapshot, source_id="a" * 64)
        self.assertEqual(result["status"], "AVAILABLE")
        self.assertEqual(result["subset_value"], "100.005")
        self.assertEqual(result["portfolio_coverage_ratio"], "1.00005")
        self.assertEqual(result["portfolio_rounding_bound"], "0.01505")
        self.assertIn("coverage_exceeds_one_within_printed_rounding", result["qualifications"])
        invalid = replace(snapshot, rows=(replace(snapshot.rows[0], position_value=printed("60.10")), *snapshot.rows[1:]))
        self.assertEqual(concentration_finding(invalid, source_id="a" * 64)["status"], "UNAVAILABLE")

    def test_repo_and_derivative_are_excluded_with_visible_partial_coverage(self):
        for kind in ("REPO", "DERIVATIVE", "DEPOSIT", "MONEY_MARKET", "COLLATERAL", "UNKNOWN"):
            snapshot = read()
            snapshot = replace(snapshot, rows=(*snapshot.rows[:-1], replace(snapshot.rows[-1], instrument_type=kind)))
            result = concentration_finding(snapshot, source_id="a" * 64)
            with self.subTest(kind=kind):
                self.assertEqual(result["status"], "PARTIAL")
                self.assertEqual(result["position_count"], 1)
                self.assertEqual(result["portfolio_coverage_ratio"], "0.9")
                self.assertIn("nonsecurity_or_derivative_positions_excluded", result["qualifications"])

    def test_zero_row_is_not_exposure_and_zero_derivative_still_qualifies(self):
        snapshot = read()
        zero = replace(snapshot.rows[-1], position_value=printed("0.00"), isin=None)
        result = concentration_finding(replace(snapshot, rows=(*snapshot.rows[:-1], zero), portfolio_total=printed("90.00")), source_id="a" * 64)
        self.assertEqual(result["status"], "AVAILABLE")
        derivative = replace(zero, instrument_type="DERIVATIVE")
        result = concentration_finding(replace(snapshot, rows=(*snapshot.rows[:-1], derivative), portfolio_total=printed("90.00")), source_id="a" * 64)
        self.assertEqual(result["status"], "PARTIAL")

    def test_fund_units_remain_security_and_do_not_invent_lookthrough(self):
        snapshot = read()
        result = concentration_finding(replace(snapshot, rows=(*snapshot.rows[:-1], replace(snapshot.rows[-1], instrument_type="FUND"))), source_id="a" * 64)
        self.assertEqual(result["status"], "AVAILABLE")
        self.assertEqual(result["fund_lookthrough"], "NOT_PERFORMED")
        self.assertIn("fund_holdings_without_lookthrough", result["qualifications"])

    def test_negative_and_nonfinite_rows_abstain_without_absolute_values(self):
        snapshot = read()
        for value in ("-1.00", "NaN", "Infinity"):
            result = concentration_finding(replace(snapshot, rows=(*snapshot.rows[:-1], replace(snapshot.rows[-1], position_value=printed(value)))), source_id="a" * 64)
            with self.subTest(value=value):
                self.assertEqual(result["status"], "UNAVAILABLE")
                self.assertIsNone(result["hhi"])
                self.assertEqual(result["positions"], [])
                self.assertIn("negative_or_invalid_position_value", result["missing_reasons"])

    def test_unsupported_unreconciled_missing_and_nonpositive_portfolio_abstain(self):
        snapshot = read()
        cases = [None, replace(snapshot, supported_profile=False), replace(snapshot, problems=("authored_mismatch",)),
                 replace(snapshot, portfolio_total=None), replace(snapshot, portfolio_total=printed("0.00")),
                 replace(snapshot, portfolio_total=printed("-1.00"))]
        for candidate in cases:
            result = concentration_finding(candidate, source_id="a" * 64)
            self.assertEqual(result["status"], "UNAVAILABLE")
            self.assertTrue(result["missing_reasons"])
            self.assertIsNone(result["hhi"])

    def test_unknown_source_identity_and_no_identified_subset_abstain(self):
        self.assertEqual(concentration_finding(read())["status"], "UNAVAILABLE")
        snapshot = replace(read(), rows=tuple(replace(item, isin=None) for item in read().rows))
        result = concentration_finding(snapshot, source_id="a" * 64)
        self.assertEqual(result["status"], "UNAVAILABLE")
        self.assertIn("no_positive_identified_security_values", result["missing_reasons"])

    def test_source_admission_reasons_block_even_readable_numbers(self):
        result = concentration_finding(read(), source_id="a" * 64, missing_reasons=["disclosure_identity_mismatch"])
        self.assertEqual(result["status"], "UNAVAILABLE")
        self.assertIsNone(result["hhi"])

    def test_future_publication_and_period_never_supply_values_or_pdf_refs(self):
        original = read()
        candidates = [replace(original, published_at=datetime(2026, 9, 17, tzinfo=timezone.utc)),
                      replace(original, report_period="2026-09")]
        for snapshot in candidates:
            before = concentration_finding(snapshot, source_id="a" * 64)
            changed = replace(snapshot, rows=(row(1, "999.00"),), portfolio_total=printed("999.00"))
            self.assertEqual(before, concentration_finding(changed, source_id="a" * 64))
            self.assertEqual(before["input_refs"], [])
            self.assertIsNone(before["report_period"])

    def test_previous_delta_requires_two_complete_verified_compatible_reports(self):
        current = read()
        previous = replace(read(), report_period="2026-07", published_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
                           rows=(row(1, "50.00"), row(2, "50.00")))
        unverified = concentration_finding(current, source_id="a" * 64, previous=previous, previous_source_id="b" * 64)
        self.assertEqual(unverified["comparison"]["status"], "UNAVAILABLE")
        self.assertEqual(unverified["comparison"]["reason"], "report_value_basis_not_verified_comparable")
        self.assertIsNone(unverified["comparison"]["hhi_delta"])
        result = concentration_finding(current, source_id="a" * 64, previous=previous, previous_source_id="b" * 64, comparison_basis_verified=True)
        self.assertEqual(result["comparison"]["status"], "AVAILABLE")
        self.assertEqual(result["comparison"]["hhi_delta"], "0.32")
        self.assertEqual(result["comparison"]["top1_ratio_delta"], "0.4")
        self.assertEqual(result["input_refs"], ["a" * 64, "b" * 64])
        partial = replace(previous, rows=(replace(previous.rows[0], instrument_type="REPO"), previous.rows[1]))
        self.assertEqual(concentration_finding(current, source_id="a" * 64, previous=partial, previous_source_id="b" * 64, comparison_basis_verified=True)["comparison"]["status"], "UNAVAILABLE")

    def test_isolated_precision_traps_and_existing_flags_do_not_change_arithmetic(self):
        expected = concentration_finding(read(), source_id="a" * 64)
        with localcontext() as caller:
            caller.prec = 2
            caller.rounding = ROUND_DOWN
            caller.traps[Inexact] = caller.traps[Rounded] = caller.traps[InvalidOperation] = True
            caller.flags[Inexact] = True
            flags, traps = caller.flags.copy(), caller.traps.copy()
            self.assertEqual(concentration_finding(read(), source_id="a" * 64), expected)
            self.assertEqual(caller.flags, flags)
            self.assertEqual(caller.traps, traps)
            self.assertEqual(caller.prec, 2)

    def test_direct_metrics_reject_missing_zero_negative_and_untyped_values(self):
        for values in ({}, {"A": Decimal(0)}, {"A": Decimal(-1)}, {"A": Decimal("NaN")}, {"A": 1}):
            with self.assertRaises(ValueError):
                calculate_metrics(values)


class ConcentrationBundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.base = all_missing_bundle()
        self.base_dir = write_bundle(self.directory / "base", self.base)
        self.registry = SourceRegistry()
        source_id = self.registry.add(self.base_dir / "bundle.json", "CODE")
        self.registration = {"base_bundle_source_id": source_id, "fixture": "authored synthetic extension"}
        self.concentrations = {code: empty_concentration(reasons=["authored_missing_pdf"]) for code in CODES}

    def extend(self, **changes):
        arguments = {"sources": list(self.registry.sources.values()), "manifest": list(self.registry.manifest.values()),
                     "registration": self.registration}
        arguments.update(changes)
        return extend_bundle(self.base, self.concentrations, **arguments)

    def test_extension_preserves_every_core_record_summary_and_original_bundle(self):
        original = (self.base_dir / "bundle.json").read_bytes()
        result = self.extend()
        self.assertEqual([row["code"] for row in result["funds"]], [row["code"] for row in self.base["funds"]])
        for old, new in zip(self.base["funds"], result["funds"]):
            self.assertEqual(old, {key: value for key, value in new.items() if key != "concentration"})
        for key, value in self.base["summary"].items():
            self.assertEqual(result["summary"][key], value)
        self.assertEqual(result["summary"]["concentration_unavailable"], 100)
        sealed = write_research_bundle(self.directory / "extension", result)
        self.assertEqual(load_research_bundle(sealed), result)
        self.assertEqual(load_research_bundle(self.base_dir), self.base)
        self.assertEqual((self.base_dir / "bundle.json").read_bytes(), original)

    def test_all_100_and_no_unopened_extensions_are_required(self):
        for selected in ({code: value for code, value in self.concentrations.items() if code != "Z99"},
                         {**self.concentrations, "NEW": empty_concentration()}):
            with self.assertRaises(ValueError):
                extend_bundle(self.base, selected, sources=[], manifest=[], registration=self.registration)

    def test_missing_base_source_binding_is_rejected(self):
        with self.assertRaises(BundleIntegrityError):
            self.extend(registration={})

    def test_changed_original_base_bundle_is_rejected(self):
        result = self.extend()
        sealed = write_research_bundle(self.directory / "extension", result)
        path = self.base_dir / "bundle.json"
        path.write_bytes(path.read_bytes() + b" ")
        with self.assertRaises(BundleIntegrityError):
            load_research_bundle(sealed)

    def test_resealed_changes_to_original_findings_comments_counts_or_order_are_rejected(self):
        mutations = [lambda result: result["funds"][0].update(comment_tr="Changed core comment"),
                     lambda result: result["funds"][0]["d1"].update(statistic="1"),
                     lambda result: result["summary"].update(d1_assessable=1),
                     lambda result: result["funds"].reverse()]
        for mutate in mutations:
            result = self.extend()
            mutate(result)
            result.pop("immutable_bundle_id")
            result["immutable_bundle_id"] = digest(canonical_bytes(result))
            with self.assertRaises(BundleIntegrityError):
                write_research_bundle(self.directory / "malicious", result)

    def test_resealed_wrong_concentration_counts_and_missing_record_rejected(self):
        for field in ("summary", "funds"):
            result = self.extend()
            if field == "summary":
                result["summary"]["concentration_unavailable"] = 99
            else:
                result["funds"][0].pop("concentration")
            result.pop("immutable_bundle_id")
            result["immutable_bundle_id"] = digest(canonical_bytes(result))
            with self.assertRaises(BundleIntegrityError):
                write_research_bundle(self.directory / "malicious", result)

    def test_reused_source_ids_cannot_replace_original_metadata(self):
        original = deepcopy(self.registry.sources[next(iter(self.registry.sources))])
        base = deepcopy(self.base)
        base["sources"] = [original]
        changed = deepcopy(original)
        changed["label"] = "Conflicting source label"
        with self.assertRaises(BundleIntegrityError):
            extend_bundle(base, self.concentrations, sources=[changed], manifest=[], registration=self.registration)


if __name__ == "__main__":
    unittest.main()
