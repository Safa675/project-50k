from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from decimal import Decimal, ROUND_UP, localcontext
from pathlib import Path
from unittest.mock import patch

from p50k.providers.kap_allocation import TextCell

REPO = Path(__file__).resolve().parents[2]
RUNNER = REPO / "research/events/2026-09-17-spk-liquidations/fund_allocations/run.py"
SPEC = importlib.util.spec_from_file_location("fund_allocation_research_runner", RUNNER)
research = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(research)


class FundAllocationResearchTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / "repo"
        self.repo.mkdir()
        self.reports = self.repo / "raw/kap/reports"
        self.reports.mkdir(parents=True)
        self.output = self.repo / "raw/kap/allocation-analysis"
        for relative in research.RUNTIME_FILES:
            destination = self.repo / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO / relative, destination)
        protocol = self.repo / research.PROTOCOL_REL
        protocol.write_text("Synthetic committed allocation protocol; no real values.\n")
        (self.repo / research.ALLOWLIST_REL).write_text("THF TP2 AAA\n")
        (self.repo / ".gitignore").write_text("/raw/\n")
        self.git("init", "-q")
        self.git("add", ".")
        self.git("-c", "user.name=Synthetic Test", "-c", "user.email=synthetic@example.invalid",
                 "commit", "-qm", "Synthetic protocol and runtime fixtures")
        extractor = patch.object(research, "_extract_rows", side_effect=self.extract_fixture)
        self.addCleanup(extractor.stop)
        extractor.start()

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.repo), *args], capture_output=True, check=True).stdout

    def cell(self, text, y=20, page=1, x=20):
        return TextCell(page, x, y, x + 300, y + 10, text)

    def extract_fixture(self, raw):
        payload = json.loads(raw)
        year, month = map(int, payload["period"].split("-"))
        month_name = list(research._MONTHS)[month - 1]
        cells = [self.cell(payload["fund_title"], 10), self.cell(f"{month_name}-{year}", 25),
                 self.cell("I-FON HAKKINDA BİLGİLER", 40),
                 self.cell("II-FONUN PERFORMANSINA İLİŞKİN BİLGİLER", 60),
                 self.cell("F-) Aylık Ortalama Portföydeki Menkul Kıymetler Yüzdesi", 80)]
        for index, (category, weight) in enumerate(payload.get("weights", {}).items()):
            number = Decimal(weight).as_tuple()
            percent = Decimal((number.sign, number.digits, number.exponent + 2))
            cells.append(self.cell(f"{chr(97 + index)}-) {category} : {format(percent, 'f')}", 100 + index * 20))
        cells.append(self.cell("G-) Aylık Ortalama Portföy Devir Hızı", 200))
        return cells, {"pages": 1, "creator": "Synthetic", "pymupdf_version": "SYNTHETIC"}

    def report(self, filename_period, index=1, **overrides):
        year, month = map(int, filename_period.split("-"))
        return {"disclosureBasic": {"period": "AB", "year": year, "donem": month,
                "disclosureIndex": index, "stockCode": "THF", "companyTitle": "Synthetic Fund",
                "publishDate": "05.10.2026 12:00:00", **overrides}}

    def write_pdf(self, code, filename_period, index, weights=None, suffix="", **overrides):
        directory = self.reports / code
        directory.mkdir(exist_ok=True)
        path = directory / f"{filename_period}_{index}{suffix}.pdf"
        path.write_text(json.dumps({"fund_title": f"{code}-Synthetic Fund", "period": filename_period,
                                   "weights": weights or {"Hisse Senetleri": "0.4", "Tahvil": "0.6"},
                                   **overrides}))
        return path

    def write_fund(self, code="THF", records=None, weights=None):
        records = records if records is not None else [self.report("2025-09", 1), self.report("2025-10", 2)]
        directory = self.reports / code
        directory.mkdir(exist_ok=True)
        for record in records:
            basic = record.get("disclosureBasic") if isinstance(record, dict) else None
            if isinstance(basic, dict) and basic.get("period") == "AB" and 1 <= basic.get("donem", 0) <= 12:
                basic["stockCode"] = code
                period = f"{basic['year']:04d}-{basic['donem']:02d}"
                self.write_pdf(code, period, basic["disclosureIndex"], (weights or {}).get(period))
        path = directory / "kap_report_list.json"
        path.write_text(json.dumps(records))
        return path

    def run_research(self, **options):
        options.setdefault("protocol_sha256", hashlib.sha256((self.repo / research.PROTOCOL_REL).read_bytes()).hexdigest())
        return research.run_research(repo_root=self.repo, **options)

    def analyze(self, code="THF"):
        return research.analyze_fund(code, self.repo, "synthetic-core-version")

    def test_actual_parser_and_core_integration_identical_distribution(self):
        self.write_fund()
        row = self.analyze()["pairs"][0]
        self.assertEqual(row["distance"], Decimal(0))
        self.assertFalse(row["screen_crossing"])
        self.assertEqual(row["basis"], "MONTHLY_AVERAGE")
        self.assertEqual(row["production_status"], "ABSTAINED")
        self.assertNotIn("baseline_unverified", row["production_reasons"])

    def test_exact_boundary_and_signed_category_changes(self):
        self.write_fund(weights={"2025-10": {"Hisse Senetleri": "0.6", "Tahvil": "0.4"}})
        row = self.analyze()["pairs"][0]
        self.assertEqual(row["distance"], Decimal("0.20"))
        self.assertEqual(row["max_category_delta"], Decimal("0.20"))
        self.assertTrue(row["screen_crossing"])
        self.assertEqual(set(row["category_deltas"].values()), {Decimal("0.2"), Decimal("-0.2")})

    def test_tiny_below_boundary_context_independent_and_deterministic(self):
        self.write_fund(weights={"2025-10": {
            "Hisse Senetleri": "0.5999999999999999999999999999999",
            "Tahvil": "0.4000000000000000000000000000001"}})
        normal = self.run_research(codes=["THF"])
        with localcontext() as context:
            context.prec = 2
            context.rounding = ROUND_UP
            hostile = self.run_research(codes=["THF"])
        self.assertEqual(hostile, normal)
        self.assertFalse(normal["funds"][0]["pairs"][0]["screen_crossing"])

    def test_missing_sources_have_twelve_explicit_scheduled_attempts(self):
        result = self.run_research()
        self.assertEqual(len(result["funds"]), 3)
        self.assertTrue(all(f["summary"]["pair_count"] == 12 for f in result["funds"]))
        self.assertTrue(all(f["summary"]["valid_pair_count"] == 0 for f in result["funds"]))
        self.assertEqual(result["cohorts"]["known_eight_targets"]["missing_sources"], 2)
        self.assertEqual(result["cohorts"]["other_selected_funds"]["monthly_attempts"], 12)

    def test_weekly_and_outside_window_excluded_before_pdf_reads(self):
        records = [self.report("2025-08", 1), self.report("2025-09", 2), self.report("2025-10", 3),
                   self.report("2026-09", 4, period="HB", donem=40), self.report("2026-10", 5)]
        self.write_fund(records=records)
        result = self.analyze()
        self.assertEqual(result["ignored_weekly_reports"], 1)
        self.assertEqual(result["ignored_outside_window_reports"], 2)
        self.assertEqual(len(result["reports"]), 2)
        self.assertEqual(result["summary"]["valid_pair_count"], 1)

    def test_gaps_do_not_bridge_calendar_months(self):
        self.write_fund(records=[self.report("2025-10", 1), self.report("2025-12", 2)])
        row = self.analyze()["pairs"][2]
        self.assertEqual(row["closing_period"], "2025-12")
        self.assertEqual(row["previous_period"], "2025-11")
        self.assertEqual(row["arithmetic_reasons"], ["missing_previous_contiguous_month"])
        self.assertIsNone(row["distance"])

    def test_duplicate_monthly_disclosures_fail_closed(self):
        self.write_fund(records=[self.report("2025-09", 1), self.report("2025-10", 2),
                                 self.report("2025-10", 3), self.report("2025-11", 4)])
        pairs = self.analyze()["pairs"]
        for row in pairs[:2]:
            self.assertIn("ambiguous_duplicate_monthly_endpoint", row["arithmetic_reasons"])
            self.assertIsNone(row["distance"])

    def test_duplicate_metadata_same_id_does_not_disappear(self):
        self.write_fund(records=[self.report("2025-09", 1), self.report("2025-10", 2), self.report("2025-10", 2)])
        self.assertEqual(len(self.analyze()["pairs"][0]["endpoint_sources"]["current"]), 2)

    def test_multiple_plausible_allocation_attachments_fail_closed(self):
        self.write_fund()
        self.write_pdf("THF", "2025-10", 2, suffix="_1")
        result = self.analyze()
        self.assertIn("ambiguous_multiple_allocation_attachments", result["reports"][1]["problems"])
        self.assertIsNone(result["pairs"][0]["distance"])

    def test_invalid_second_table_cannot_be_cherry_picked_away(self):
        self.write_fund()
        self.write_pdf("THF", "2025-10", 2, {"Hisse Senetleri": "0.3", "Tahvil": "0.6"}, suffix="_1")
        record = self.analyze()["reports"][1]
        self.assertIn("ambiguous_multiple_allocation_attachments", record["problems"])
        self.assertIsNone(record["weights"])

    def test_category_schema_change_not_filled_with_zero(self):
        self.write_fund(weights={"2025-10": {"Hisse Senetleri": "1"}})
        row = self.analyze()["pairs"][0]
        self.assertIn("category_schema_missing_or_mismatched", row["arithmetic_reasons"])
        self.assertIsNone(row["screen_crossing"])

    def test_negative_and_nonunit_tables_stay_noncomputable(self):
        for weights in ({"Hisse Senetleri": "-0.1", "Tahvil": "1.1"},
                        {"Hisse Senetleri": "0.3", "Tahvil": "0.6"}):
            with self.subTest(weights=weights):
                self.write_fund(weights={"2025-10": weights})
                self.assertIsNone(self.analyze()["pairs"][0]["distance"])

    def test_missing_current_pdf_keeps_metadata_and_missing_reason(self):
        self.write_fund()
        (self.reports / "THF/2025-10_2.pdf").unlink()
        result = self.analyze()
        self.assertEqual(result["reports"][1]["problems"], ["report_pdf_missing"])
        self.assertIsNone(result["pairs"][0]["distance"])

    def test_exact_attachment_filename_does_not_match_longer_disclosure_id(self):
        self.write_fund()
        (self.reports / "THF/2025-10_2.pdf").rename(self.reports / "THF/2025-10_22.pdf")
        self.assertEqual(self.analyze()["reports"][1]["attachments"], [])

    def test_latest_scheduled_reported_valid_are_separate(self):
        self.write_fund(records=[self.report("2026-07", 1), self.report("2026-08", 2)],
                        weights={"2026-08": {"Hisse Senetleri": "0.7", "Tahvil": "0.3"}})
        result = self.run_research(codes=["THF"])
        summary = result["funds"][0]["summary"]
        self.assertEqual(summary["latest_scheduled_pair"]["closing_period"], "2026-09")
        self.assertIsNone(summary["latest_screen_crossing"])
        self.assertEqual(summary["latest_reported_pair"]["closing_period"], "2026-08")
        self.assertTrue(summary["latest_reported_screen_crossing"])
        self.assertTrue(summary["latest_reported_pair_stale"])
        self.assertTrue(summary["latest_valid_pair_stale"])
        self.assertEqual(result["ranking_by_latest_distance"], [])

    def test_latest_reported_invalid_not_replaced_by_previous_valid(self):
        self.write_fund(records=[self.report("2026-06", 1), self.report("2026-07", 2), self.report("2026-08", 3)])
        (self.reports / "THF/2026-08_3.pdf").unlink()
        summary = self.analyze()["summary"]
        self.assertEqual(summary["latest_reported_pair"]["closing_period"], "2026-08")
        self.assertIsNone(summary["latest_reported_screen_crossing"])
        self.assertEqual(summary["latest_valid_pair"]["closing_period"], "2026-07")

    def test_nominal_pre_order_subset_does_not_use_september(self):
        self.write_fund(records=[self.report("2026-07", 1), self.report("2026-08", 2), self.report("2026-09", 3)],
                        weights={"2026-08": {"Hisse Senetleri": "0.5", "Tahvil": "0.5"},
                                 "2026-09": {"Hisse Senetleri": "0.8", "Tahvil": "0.2"}})
        summary = self.analyze()["summary"]
        self.assertEqual(summary["peak_period"], "2026-09")
        self.assertEqual(summary["pre_order_peak_period"], "2026-08")
        self.assertFalse(summary["pre_order_any_screen_crossing"])

    def test_peak_ties_earliest_period_and_code_ascending(self):
        for code in ("AAA", "THF"):
            self.write_fund(code, [self.report("2025-09", 1), self.report("2025-10", 2), self.report("2025-11", 3)],
                            weights={"2025-10": {"Hisse Senetleri": "0.6", "Tahvil": "0.4"},
                                     "2025-11": {"Hisse Senetleri": "0.4", "Tahvil": "0.6"}})
        result = self.run_research(codes=["THF", "AAA"])
        self.assertEqual(result["ranking_by_peak_distance"], ["AAA", "THF"])
        self.assertTrue(all(f["summary"]["peak_period"] == "2025-10" for f in result["funds"]))

    def test_provenance_preserves_original_list_pdf_hashes_and_publication(self):
        path = self.write_fund()
        before = {p: p.read_bytes() for p in (self.reports / "THF").iterdir()}
        result = self.run_research(codes=["THF"])
        row = result["funds"][0]["pairs"][0]["endpoint_sources"]["current"][0]
        self.assertEqual(row["published_at_raw"], "05.10.2026 12:00:00")
        self.assertEqual(row["metadata_pointer"], "[1].disclosureBasic")
        self.assertEqual(len(row["metadata_record_sha256"]), 64)
        source = result["source_manifest"]["THF"]
        self.assertEqual(source["report_list"]["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(len(source["pdfs"]), 2)
        self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_later_month_does_not_change_earlier_pair_metrics(self):
        self.write_fund()
        before = self.analyze()["pairs"][0]
        self.write_fund(records=[self.report("2025-09", 1), self.report("2025-10", 2), self.report("2025-11", 3)],
                        weights={"2025-11": {"Hisse Senetleri": "1"}})
        after = self.analyze()["pairs"][0]
        before.pop("source_file")
        after.pop("source_file")
        self.assertEqual(before, after)

    def test_empty_malformed_and_invalid_metadata_remain_explicit(self):
        self.write_fund("AAA", records=[])
        (self.reports / "TP2").mkdir()
        (self.reports / "TP2/kap_report_list.json").write_text("{invalid")
        result = self.run_research()
        reasons = {f["fund"]: f["fund_reasons"] for f in result["funds"]}
        self.assertIn("source_report_list_empty", reasons["AAA"])
        self.assertIn("source_report_list_invalid", reasons["TP2"])
        self.assertEqual(result["cohorts"]["known_eight_targets"]["invalid_sources"], 1)

    def test_stock_code_conflict_rejected_before_pdf_reads(self):
        path = self.write_fund()
        records = json.loads(path.read_bytes())
        records[0]["disclosureBasic"]["stockCode"] = "AAA"
        path.write_text(json.dumps(records))
        with patch.object(research, "_read_pdf", side_effect=AssertionError("PDF read")):
            with self.assertRaisesRegex(ValueError, "fund must match"):
                self.run_research(codes=["THF"])

    def test_pdf_title_and_printed_period_mismatch_abstain(self):
        for overrides in ({"fund_title": "Other Synthetic Fund"}, {"period": "2025-11"}):
            with self.subTest(overrides=overrides):
                self.write_fund()
                self.write_pdf("THF", "2025-10", 2, **overrides)
                result = self.analyze()
                self.assertIsNone(result["pairs"][0]["distance"])
                self.assertTrue(result["reports"][1]["attachments"][0]["identity"]["problems"])

    def test_pdf_identity_supports_wrapped_title_punctuation_and_month_cells(self):
        basic = {"stockCode": "THF", "companyTitle": "Synthetic Portfolio (TL) Fund"}
        cells = [self.cell("THF-SYNTHETIC PORTFOLIO", 10), self.cell("TL FUND", 25),
                 self.cell("AĞUSTOS", 40), self.cell("2026", 55)]
        self.assertEqual(research._pdf_identity(cells, "THF", "2026-08", basic)["problems"], [])

    def test_pdf_identity_supports_full_month_interval_but_not_footer_timestamp(self):
        basic = {"stockCode": "THF", "companyTitle": "Synthetic Fund"}
        cells = [self.cell("Synthetic Fund", 10), self.cell("Rapor Dönemi", 25),
                 self.cell("01/08/2026 ve 31/08/2026", 40)]
        self.assertEqual(research._pdf_identity(cells, "THF", "2026-08", basic)["problems"], [])
        cells[-1] = self.cell("02/09/2026 20:40:18", 40)
        self.assertIn("pdf_report_period_unverified", research._pdf_identity(cells, "THF", "2026-08", basic)["problems"])

    def test_numeric_section_boundary_excludes_downstream_period_names(self):
        basic = {"stockCode": "THF", "companyTitle": "Synthetic Fund"}
        cells = [self.cell("Synthetic Fund", 10), self.cell("2-FONUN PERFORMANSINA İLİŞKİN BİLGİLER", 30),
                 self.cell("AĞUSTOS-2026", 50)]
        self.assertIn("pdf_report_period_unverified", research._pdf_identity(cells, "THF", "2026-08", basic)["problems"])

    def test_founding_date_cannot_become_or_conflict_with_report_period(self):
        basic = {"stockCode": "THF", "companyTitle": "Synthetic Fund"}
        cells = [self.cell("Synthetic Fund", 10), self.cell("AĞUSTOS-2026", 25),
                 self.cell("I-FONU TANITICI BİLGİLER", 40), self.cell("Fonun Kuruluş Tarihi", 55),
                 self.cell("24 Şubat 2025", 70)]
        self.assertEqual(research._pdf_identity(cells, "THF", "2026-08", basic)["problems"], [])
        cells.pop(1)
        self.assertIn("pdf_report_period_unverified", research._pdf_identity(cells, "THF", "2025-02", basic)["problems"])

    def test_conflicting_fallback_list_is_not_implicitly_discarded(self):
        path = self.write_fund()
        fallback = self.reports / "kap_portfolio_reports_THF.body"
        records = json.loads(path.read_bytes())
        records[1]["disclosureBasic"]["publishDate"] = "06.10.2026 12:00:00"
        fallback.write_text(json.dumps(records))
        with patch.object(research, "_read_pdf", side_effect=AssertionError("PDF read")):
            result = self.analyze()
        self.assertIn("ambiguous_conflicting_report_list_sources", result["fund_reasons"])
        self.assertEqual(len(result["source_file"]["list_sources"]), 2)
        self.assertEqual(result["summary"]["valid_pair_count"], 0)

    def test_semantically_identical_fallback_lists_preserve_both_hashes(self):
        path = self.write_fund()
        fallback = self.reports / "kap_portfolio_reports_THF.body"
        fallback.write_text(json.dumps(json.loads(path.read_bytes()), indent=2))
        result = self.analyze()
        self.assertEqual(result["summary"]["valid_pair_count"], 1)
        sources = result["source_file"]["list_sources"]
        self.assertEqual(len(sources), 2)
        self.assertNotEqual(sources[0]["sha256"], sources[1]["sha256"])

    def test_selection_and_missing_protocol_hash_rejected_before_sources(self):
        with patch.object(research, "analyze_fund", side_effect=AssertionError("source read")):
            for selected in (["ZZZ"], ["THF", "THF"], [], ["thf"], ["../THF"]):
                with self.subTest(selected=selected), self.assertRaises(ValueError):
                    self.run_research(codes=selected)
            with self.assertRaisesRegex(ValueError, "hash is required"):
                research.run_research(repo_root=self.repo, codes=["THF"])

    def test_protocol_allowlist_runtime_and_supplied_hash_guards(self):
        for relative in (research.PROTOCOL_REL, research.ALLOWLIST_REL, research.RUNTIME_FILES[-1]):
            with self.subTest(relative=relative):
                path = self.repo / relative
                original = path.read_bytes()
                path.write_bytes(original + b"\n")
                with patch.object(research, "analyze_fund", side_effect=AssertionError("source read")):
                    with self.assertRaisesRegex(ValueError, "differs from committed"):
                        self.run_research(codes=["THF"])
                path.write_bytes(original)
        with self.assertRaisesRegex(ValueError, "supplied protocol hash"):
            self.run_research(codes=["THF"], protocol_sha256="0" * 64)

    def test_output_outside_base_or_not_ignored_refused_before_sources(self):
        with patch.object(research, "analyze_fund", side_effect=AssertionError("source read")):
            for out in (Path(self.temp.name) / "outside", self.reports, self.repo / "raw/other"):
                with self.subTest(out=out), self.assertRaises(ValueError):
                    self.run_research(codes=["THF"], out_dir=out)
        (self.repo / ".gitignore").write_text("")
        with self.assertRaises(ValueError):
            self.run_research(codes=["THF"])

    def test_input_and_output_symlink_escapes_are_refused(self):
        outside = Path(self.temp.name) / "outside"
        outside.mkdir()
        self.output.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.run_research(codes=["THF"])
        self.output.unlink()
        (self.reports / "THF").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.run_research(codes=["THF"])

    def test_idempotent_run_preserves_own_result_bytes(self):
        self.write_fund()
        first = self.run_research(codes=["THF"], run_at="2026-10-08T00:00:00+00:00")
        destination = Path(first["metadata"]["output_path"])
        original = destination.read_bytes()
        second = self.run_research(codes=["THF"], run_at="2026-10-09T00:00:00+00:00")
        self.assertEqual(second, first)
        self.assertEqual(destination.read_bytes(), original)

    def test_idempotent_run_preserves_fractional_pdf_coordinates(self):
        self.write_fund()

        def fractional_geometry(raw):
            cells, metadata = self.extract_fixture(raw)
            return [TextCell(cell.page, float(cell.x0) + 0.125, float(cell.y0) + 0.125,
                             float(cell.x1) + 0.125, float(cell.y1) + 0.125, cell.text)
                    for cell in cells], metadata

        with patch.object(research, "_extract_rows", side_effect=fractional_geometry):
            first = self.run_research(codes=["THF"], run_at="2026-10-08T00:00:00+00:00")
            path = Path(first["metadata"]["output_path"])
            original = path.read_bytes()
            second = self.run_research(codes=["THF"], run_at="2026-10-09T00:00:00+00:00")

        self.assertEqual(second, first)
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(second["metadata"]["run_at_utc"], "2026-10-08T00:00:00+00:00")
        coordinates = second["funds"][0]["reports"][0]["attachments"][0]["source_rows"][0]["rect"]
        self.assertTrue(all(isinstance(value, float) for value in coordinates))
        self.assertTrue(all(value % 1 == 0.125 for value in coordinates))

    def test_foreign_output_and_unrelated_directory_content_refused(self):
        self.write_fund()
        result = self.run_research(codes=["THF"])
        destination = Path(result["metadata"]["output_path"])
        for content in (b'{"foreign":true}', b"invalid output"):
            with self.subTest(content=content):
                destination.write_bytes(content)
                with self.assertRaises(ValueError):
                    self.run_research(codes=["THF"])
                self.assertEqual(destination.read_bytes(), content)
        destination.unlink()
        (destination.parent / "foreign.txt").write_text("Keep this file")
        with self.assertRaisesRegex(ValueError, "unrelated files"):
            self.run_research(codes=["THF"])

    def test_source_change_creates_different_run_identity(self):
        self.write_fund()
        first = self.run_research(codes=["THF"])
        self.write_pdf("THF", "2025-10", 2, {"Hisse Senetleri": "0.7", "Tahvil": "0.3"})
        second = self.run_research(codes=["THF"])
        self.assertNotEqual(first["fingerprint"], second["fingerprint"])
        self.assertTrue(Path(first["metadata"]["output_path"]).exists())

    def test_cli_outputs_aggregate_counts_without_non_target_names(self):
        self.write_fund("AAA")
        output = io.StringIO()
        digest = hashlib.sha256((self.repo / research.PROTOCOL_REL).read_bytes()).hexdigest()
        runner = research.run_research
        with patch.object(research, "run_research", side_effect=lambda **options: runner(repo_root=self.repo, **options)), redirect_stdout(output):
            self.assertEqual(research.main(["--funds", "AAA", "--protocol-sha256", digest]), 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["selected_funds"], 1)
        self.assertNotIn("AAA", output.getvalue())


if __name__ == "__main__":
    unittest.main()
