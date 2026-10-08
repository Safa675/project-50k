from __future__ import annotations

import copy
import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from decimal import Decimal, ROUND_UP, localcontext
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[2]
RUNNER = REPO / "research/events/2026-09-17-spk-liquidations/fund_flows/run.py"
SPEC = importlib.util.spec_from_file_location("fund_flow_research_runner", RUNNER)
research = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(research)


class FundFlowResearchTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / "repo"
        self.repo.mkdir()
        self.series = self.repo / "raw/kap/series"
        self.series.mkdir(parents=True)
        self.output = self.repo / "raw/kap/flow-analysis"
        for relative in research.RUNTIME_FILES:
            destination = self.repo / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO / relative, destination)
        protocol = self.repo / research.PROTOCOL_REL
        protocol.write_text("Synthetic committed research protocol; no real values.\n")
        (self.repo / research.ALLOWLIST_REL).write_text("THF TP2 AAA\n")
        (self.repo / ".gitignore").write_text("/raw/\n")
        self.git("init", "-q")
        self.git("add", ".")
        self.git("-c", "user.name=Synthetic Test", "-c", "user.email=synthetic@example.invalid",
                 "commit", "-qm", "Synthetic protocol and runtime fixtures")

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.repo), *args], capture_output=True, check=True).stdout

    def report(self, period, assets="1000", nav="10", **overrides):
        return {"period": period, "cadence": "monthly", "total_value": assets,
                "period_end_price": nav, "previous_period_price": None,
                "units_outstanding": None, "disclosure_index": f"SYN-{period}",
                "published_at": "2026-10-05T12:00:00+03:00", "company_title": "Synthetic Company",
                "problems": [], **overrides}

    def write_fund(self, code="THF", reports=None, **overrides):
        payload = {"fund": code, "source": research.SOURCE_MARKER, "origin": "SYNTHETIC",
                   "reports": reports if reports is not None else [self.report("2025-09"), self.report("2025-10")],
                   **overrides}
        path = self.series / f"{code}.json"
        path.write_text(json.dumps(payload, allow_nan=True), encoding="utf-8")
        return path

    def run_research(self, **options):
        return research.run_research(repo_root=self.repo, **options)

    def analyze(self, code="THF"):
        return research.analyze_fund(code, self.series / f"{code}.json", self.repo, "synthetic-core-version")

    def test_price_only_growth_and_signed_residuals(self):
        self.write_fund(reports=[self.report("2025-09"), self.report("2025-10", "1200", "12"),
                                 self.report("2025-11", "1320", "12"), self.report("2025-12", "1188", "12")])
        pairs = self.analyze()["pairs"]
        self.assertEqual([Decimal(row["residual"]) for row in pairs], [Decimal(0), Decimal(120), Decimal(-132)])
        self.assertEqual([row["screen_crossing"] for row in pairs], [False, True, True])
        self.assertTrue(all(row["production_status"] == "ABSTAINED" for row in pairs))
        self.assertTrue(all(row["eligibility"]["baseline"] == "UNKNOWN" for row in pairs))

    def test_exact_positive_and_negative_ten_percent_boundaries(self):
        for assets, expected in (("1100", "0.10"), ("900", "-0.10")):
            with self.subTest(assets=assets):
                self.write_fund(reports=[self.report("2025-09"), self.report("2025-10", assets)])
                row = self.analyze()["pairs"][0]
                self.assertEqual(Decimal(row["rate"]), Decimal(expected))
                self.assertTrue(row["screen_crossing"])

    def test_tiny_below_threshold_preserved_under_hostile_decimal_context(self):
        self.write_fund(reports=[self.report("2025-09", "1", "1"),
                                 self.report("2025-10", "1.0999999999999999999999999999999", "1"),
                                 self.report("2025-11", "1.2099999999999999999999999999998", "1")])
        normal = self.run_research(codes=["THF"])
        with localcontext() as context:
            context.prec = 2
            context.rounding = ROUND_UP
            hostile = self.run_research(codes=["THF"])
        self.assertEqual(hostile["fingerprint"], normal["fingerprint"])
        self.assertFalse(hostile["funds"][0]["pairs"][0]["screen_crossing"])

    def test_actual_zero_closing_assets_is_not_missing_nav(self):
        self.write_fund(reports=[self.report("2025-09"), self.report("2025-10", "0")])
        row = self.analyze()["pairs"][0]
        self.assertEqual(Decimal(row["rate"]), Decimal(-1))
        self.assertTrue(row["screen_crossing"])
        self.assertEqual(row["production_status"], "ABSTAINED")

    def test_invalid_numbers_and_unusable_denominators_abstain_arithmetic(self):
        cases = [("total_value", None), ("total_value", "NaN"), ("total_value", "Infinity"),
                 ("total_value", "-1"), ("period_end_price", "0"), ("period_end_price", True),
                 ("period_end_price", float("inf"))]
        for field, value in cases:
            with self.subTest(field=field, value=value):
                self.write_fund(reports=[self.report("2025-09"), self.report("2025-10", **{field: value})])
                row = self.analyze()["pairs"][0]
                self.assertIsNone(row["rate"])
                self.assertIsNone(row["screen_crossing"])
                self.assertTrue(row["arithmetic_reasons"])
        self.write_fund(reports=[self.report("2025-09", "0"), self.report("2025-10")])
        self.assertIsNone(self.analyze()["pairs"][0]["rate"])

    def test_json_numeric_decimals_do_not_pass_through_float(self):
        path = self.write_fund()
        path.write_text('{"fund":"THF","source":"KAP Portföy Dağılım Raporu","origin":"SYNTHETIC",'
                        '"reports":[{"period":"2025-09","cadence":"monthly","total_value":1,"period_end_price":1},'
                        '{"period":"2025-10","cadence":"monthly","total_value":1.0999999999999999999999999999999,"period_end_price":1}]}')
        row = self.analyze()["pairs"][0]
        self.assertEqual(row["rate"], "0.0999999999999999999999999999999")
        self.assertFalse(row["screen_crossing"])

    def test_window_weekly_and_previous_only_period_boundaries(self):
        self.write_fund(reports=[self.report("2025-08"), self.report("2025-09"), self.report("2025-10"),
                                 self.report("2026-W40", cadence="weekly"), self.report("2026-09"),
                                 self.report("2026-10")])
        result = self.analyze()
        self.assertEqual([row["closing_period"] for row in result["pairs"]], ["2025-10", "2026-09"])
        self.assertEqual(result["ignored_weekly_reports"], 1)
        self.assertEqual(result["ignored_outside_window_reports"], 2)
        self.assertEqual(result["pairs"][0]["previous_period"], "2025-09")
        self.assertIsNone(result["pairs"][1]["rate"])

    def test_gap_not_bridged_or_filled_from_previous_price_field(self):
        self.write_fund(reports=[self.report("2025-10"), self.report("2025-12", "9000", previous_period_price="10")])
        row = self.analyze()["pairs"][-1]
        self.assertEqual(row["previous_period"], "2025-11")
        self.assertEqual(row["arithmetic_reasons"], ["missing_previous_contiguous_month"])
        self.assertIsNone(row["endpoint_values"])

    def test_duplicate_months_never_choose_best_or_latest_revision(self):
        self.write_fund(reports=[self.report("2025-09"), self.report("2025-10"),
                                 self.report("2025-10", "1300", disclosure_index="SYN-DUP"), self.report("2025-11")])
        result = self.analyze()
        for row in result["pairs"]:
            self.assertIsNone(row["rate"])
            self.assertIn("ambiguous_duplicate_monthly_endpoint", row["arithmetic_reasons"])
        self.assertEqual(len(result["pairs"][0]["endpoint_sources"]["current"]), 2)
        self.assertEqual(len(result["pairs"][1]["endpoint_sources"]["previous"]), 2)

    def test_latest_invalid_month_not_substituted_into_current_rank(self):
        self.write_fund(reports=[self.report("2025-09"), self.report("2025-10", "1300"),
                                 self.report("2025-11", nav=None)])
        result = self.run_research(codes=["THF"])
        summary = result["funds"][0]["summary"]
        self.assertEqual(summary["latest_reported_pair"]["closing_period"], "2025-11")
        self.assertIsNone(summary["latest_screen_crossing"])
        self.assertEqual(summary["latest_valid_pair"]["closing_period"], "2025-10")
        self.assertTrue(summary["latest_valid_pair_stale"])
        self.assertTrue(summary["historical_any_screen_crossing"])
        self.assertEqual(result["ranking_by_latest_abs_rate"], [])

    def test_peak_ties_earliest_period_and_fund_rank_ties_code_ascending(self):
        for code in ("THF", "AAA"):
            self.write_fund(code, [self.report("2025-09"), self.report("2025-10", "1100"),
                                   self.report("2025-11", "1210")])
        result = self.run_research(codes=["THF", "AAA"])
        self.assertEqual(result["ranking_by_peak_abs_rate"], ["AAA", "THF"])
        self.assertEqual(result["ranking_by_latest_abs_rate"], ["AAA", "THF"])
        self.assertTrue(all(f["summary"]["peak_period"] == "2025-10" for f in result["funds"]))

    def test_nominal_pre_order_subset_does_not_use_september(self):
        self.write_fund(reports=[self.report("2026-07"), self.report("2026-08", "1100"),
                                 self.report("2026-09", "2200")])
        summary = self.analyze()["summary"]
        self.assertEqual(summary["peak_period"], "2026-09")
        self.assertEqual(summary["pre_order_peak_period"], "2026-08")
        self.assertEqual(Decimal(summary["pre_order_peak_signed_rate"]), Decimal("0.1"))
        self.assertEqual(summary["pre_order_crossing_pair_count"], 1)

    def test_diagnostics_keep_actual_endpoint_price_and_allow_arithmetic(self):
        self.write_fund(reports=[self.report("2025-09", units_outstanding="99"),
                                 self.report("2025-10", "1100", previous_period_price="9", units_outstanding="99")])
        row = self.analyze()["pairs"][0]
        self.assertTrue(row["screen_crossing"])
        self.assertEqual(row["endpoint_values"]["previous_nav"], "10")
        self.assertEqual(len(row["diagnostics"]), 3)

    def test_provenance_has_exact_operand_pointer_hash_and_raw_publication(self):
        path = self.write_fund()
        before = path.read_bytes()
        result = self.run_research(codes=["THF"])
        row = result["funds"][0]["pairs"][0]
        current = row["endpoint_sources"]["current"][0]
        self.assertEqual(current["source_pointer"], "reports[1]")
        self.assertEqual(len(current["record_sha256"]), 64)
        self.assertEqual(current["published_at_raw"], "2026-10-05T12:00:00+03:00")
        self.assertEqual(row["source_file"]["sha256"], hashlib.sha256(before).hexdigest())
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(row["core_version"], result["registration"]["core_sha256"])
        self.assertEqual(set(result["registration"]["code_manifest"]),
                         {p.as_posix() for p in research.RUNTIME_FILES} | {research.ALLOWLIST_REL.as_posix()})

    def test_future_or_outside_report_changes_do_not_change_earlier_pair(self):
        reports = [self.report("2025-09"), self.report("2025-10", "1100"), self.report("2026-10", "9000")]
        self.write_fund(reports=reports)
        before = self.analyze()["pairs"][0]
        reports[-1]["total_value"] = "15000"
        self.write_fund(reports=reports)
        after = self.analyze()["pairs"][0]
        for row in (before, after):
            row.pop("source_file")
        self.assertEqual(before, after)
        self.assertEqual(after["production_status"], "ABSTAINED")

    def test_missing_empty_and_malformed_sources_retained_with_denominators(self):
        self.write_fund("AAA", [])
        (self.series / "TP2.json").write_text("{broken synthetic JSON")
        result = self.run_research()
        self.assertEqual(result["source_manifest"]["THF"]["state"], "MISSING")
        self.assertEqual(result["source_manifest"]["TP2"]["state"], "INVALID")
        reasons = {f["fund"]: f["fund_reasons"] for f in result["funds"]}
        self.assertIn("source_reports_empty", reasons["AAA"])
        self.assertEqual(result["cohorts"]["known_eight_targets"]["selected"], 2)
        self.assertEqual(result["cohorts"]["known_eight_targets"]["missing_sources"], 1)
        self.assertEqual(result["cohorts"]["known_eight_targets"]["invalid_sources"], 1)

    def test_invalid_report_shape_retains_fund_and_report_reasons(self):
        self.write_fund(reports=[None, self.report("2026-13"), self.report("2025-09"), self.report("2025-10")])
        result = self.analyze()
        self.assertEqual(len(result["report_issues"]), 2)
        self.assertEqual(result["summary"]["valid_pair_count"], 1)
        path = self.write_fund()
        payload = json.loads(path.read_bytes())
        payload["reports"] = None
        path.write_text(json.dumps(payload))
        self.assertEqual(self.analyze()["fund_reasons"], ["source_reports_missing_or_invalid"])

    def test_selection_rejected_before_any_source_read(self):
        for selected in (["ZZZ"], ["THF", "THF"], [], ["thf"], ["../THF"]):
            with self.subTest(selected=selected), patch.object(research, "analyze_fund", side_effect=AssertionError("source read")):
                with self.assertRaises(ValueError):
                    self.run_research(codes=selected)

    def test_fund_identity_and_provider_marker_mismatch_rejected(self):
        for overrides in ({"fund": "AAA"}, {"source": "Different Provider"}):
            with self.subTest(overrides=overrides):
                self.write_fund(**overrides)
                with self.assertRaises(ValueError):
                    self.run_research(codes=["THF"])
        self.assertFalse(self.output.exists())

    def test_protocol_allowlist_and_runtime_changes_block_before_source_reads(self):
        for relative in (research.PROTOCOL_REL, research.ALLOWLIST_REL, research.RUNTIME_FILES[-1]):
            with self.subTest(relative=relative):
                path = self.repo / relative
                original = path.read_bytes()
                path.write_bytes(original + b"\n")
                with patch.object(research, "analyze_fund", side_effect=AssertionError("source read")):
                    with self.assertRaisesRegex(ValueError, "differs from committed"):
                        self.run_research(codes=["THF"])
                path.write_bytes(original)

    def test_supplied_protocol_hash_guard_and_protocol_commit_recorded(self):
        self.write_fund()
        with patch.object(research, "analyze_fund", side_effect=AssertionError("source read")):
            with self.assertRaisesRegex(ValueError, "supplied protocol hash"):
                self.run_research(codes=["THF"], protocol_sha256="0" * 64)
        digest = hashlib.sha256((self.repo / research.PROTOCOL_REL).read_bytes()).hexdigest()
        result = self.run_research(codes=["THF"], protocol_sha256=digest)
        self.assertEqual(result["registration"]["protocol_sha256"], digest)
        self.assertEqual(result["registration"]["protocol_commit"], self.git("rev-parse", "HEAD").decode().strip())

    def test_output_outside_base_or_through_symlink_refused_before_source_reads(self):
        outside = Path(self.temp.name) / "outside"
        outside.mkdir()
        self.output.parent.mkdir(exist_ok=True)
        alias = self.output.parent / "flow-analysis"
        for out in (outside, self.series, self.repo / "raw/other"):
            with self.subTest(out=out), patch.object(research, "analyze_fund", side_effect=AssertionError("source read")):
                with self.assertRaises(ValueError):
                    self.run_research(codes=["THF"], out_dir=out)
        alias.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.run_research(codes=["THF"])

    def test_canonical_source_symlink_is_not_followed(self):
        other = Path(self.temp.name) / "outside.json"
        other.write_text("unopened content")
        (self.series / "THF.json").symlink_to(other)
        with self.assertRaisesRegex(ValueError, "canonical file"):
            self.run_research(codes=["THF"])

    def test_deterministic_rerun_reuses_immutable_own_file(self):
        path = self.write_fund()
        before = path.read_bytes()
        first = self.run_research(codes=["THF"], run_at="2026-10-08T10:00:00Z")
        output = Path(first["metadata"]["output_path"])
        output_bytes, mtime = output.read_bytes(), output.stat().st_mtime_ns
        second = self.run_research(codes=["THF"], run_at="2026-10-08T11:00:00Z")
        self.assertEqual(first, second)
        self.assertEqual(output.read_bytes(), output_bytes)
        self.assertEqual(output.stat().st_mtime_ns, mtime)
        self.assertEqual(output.parent.name, first["fingerprint"])
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(self.git("ls-files", "--", "raw"), b"")

    def test_changed_source_gets_separate_run_and_old_output_preserved(self):
        self.write_fund()
        first = self.run_research(codes=["THF"])
        old_path = Path(first["metadata"]["output_path"])
        before = old_path.read_bytes()
        self.write_fund(reports=[self.report("2025-09"), self.report("2025-10", "1100")])
        second = self.run_research(codes=["THF"])
        self.assertNotEqual(first["fingerprint"], second["fingerprint"])
        self.assertNotEqual(first["metadata"]["output_path"], second["metadata"]["output_path"])
        self.assertEqual(old_path.read_bytes(), before)

    def test_foreign_or_conflicting_output_never_overwritten(self):
        self.write_fund()
        result = self.run_research(codes=["THF"])
        output = Path(result["metadata"]["output_path"])
        changed = copy.deepcopy(result)
        changed["funds"][0]["pairs"][0]["rate"] = "0.90"
        for foreign in ({"schema": "foreign"}, changed):
            with self.subTest(foreign=foreign["schema"]):
                encoded = json.dumps(foreign).encode()
                output.write_bytes(encoded)
                with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
                    self.run_research(codes=["THF"])
                self.assertEqual(output.read_bytes(), encoded)

    def test_output_symlink_and_hardlink_input_alias_refused(self):
        source = self.write_fund()
        result = self.run_research(codes=["THF"])
        output = Path(result["metadata"]["output_path"])
        output.unlink()
        output.symlink_to(source)
        with self.assertRaises(ValueError):
            self.run_research(codes=["THF"])
        output.unlink()
        os.link(source, output)
        with self.assertRaisesRegex(ValueError, "alias an input"):
            self.run_research(codes=["THF"])

    def test_metadata_only_output_tampering_is_not_reused(self):
        self.write_fund()
        result = self.run_research(codes=["THF"])
        output = Path(result["metadata"]["output_path"])
        for metadata in ({}, {**result["metadata"], "output_path": "unrelated/synthetic.json"}):
            with self.subTest(metadata=metadata):
                changed = {**result, "metadata": metadata}
                encoded = json.dumps(changed).encode()
                output.write_bytes(encoded)
                with self.assertRaisesRegex(ValueError, "unrelated or missing metadata"):
                    self.run_research(codes=["THF"])
                self.assertEqual(output.read_bytes(), encoded)

    def test_unrelated_run_directory_file_protected(self):
        self.write_fund()
        result = self.run_research(codes=["THF"])
        output = Path(result["metadata"]["output_path"])
        foreign = output.parent / "unrelated.txt"
        foreign.write_text("Synthetic protected file")
        with self.assertRaisesRegex(ValueError, "unrelated files"):
            self.run_research(codes=["THF"])
        self.assertEqual(foreign.read_text(), "Synthetic protected file")

    def test_stdout_contains_aggregate_counts_and_private_path_only(self):
        self.write_fund("AAA")
        result = self.run_research(codes=["AAA"])
        stream = io.StringIO()
        with patch.object(research, "run_research", return_value=result), redirect_stdout(stream):
            self.assertEqual(research.main(["--funds", "AAA"]), 0)
        printed = json.loads(stream.getvalue())
        self.assertEqual(printed["selected_funds"], 1)
        self.assertNotIn("AAA", stream.getvalue())
        self.assertEqual(printed["output_path"], result["metadata"]["output_path"])


if __name__ == "__main__":
    unittest.main()
