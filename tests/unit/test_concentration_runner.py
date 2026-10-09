"""Synthetic selection/registration checks; never read original fund data."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


REPO = Path(__file__).resolve().parents[2]
RUNNER_PATH = REPO / "research/events/2026-09-17-spk-liquidations/fund_concentration_app/run.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("synthetic_concentration_runner", RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def report(month=8, *, published="02.09.2026 10:00:00", index=1, year=2026, cadence="AB"):
    return {"disclosureBasic": {"year": year, "donem": month, "period": cadence,
                                "publishDate": published, "disclosureIndex": index}}


class MonthlySelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner = load_runner()

    def test_latest_monthly_and_previous_selected_before_values(self):
        rows = [report(7, published="02.08.2026 10:00:00", index=2), report(),
                report(6, published="02.07.2026 10:00:00", index=3)]
        periods, reasons = self.runner.monthly_candidates(rows)
        self.assertEqual([[r.period for r in group] for group in periods], [["2026-08"], ["2026-07"]])
        self.assertEqual(reasons, [])

    def test_future_publication_and_future_month_cannot_enter(self):
        eligible = report(7, published="02.08.2026 10:00:00")
        periods, _ = self.runner.monthly_candidates([
            eligible, report(8, published="17.09.2026 00:00:00", index=2),
            report(9, published="16.09.2026 10:00:00", index=3)])
        self.assertEqual(periods[0][0].period, "2026-07")
        self.assertEqual(len(periods), 1)

    def test_cutoff_equality_and_explicit_offset_admitted(self):
        periods, _ = self.runner.monthly_candidates([report(published="2026-09-16T23:59:59+03:00")])
        self.assertEqual(periods[0][0].published_at, "2026-09-16T23:59:59+03:00")
        self.assertIsNone(periods[0][0].timing_assumption)

    def test_duplicates_remain_ambiguous_without_success_fallback(self):
        periods, _ = self.runner.monthly_candidates([report(index=1), report(index=2),
            report(7, published="02.08.2026 10:00:00", index=3)])
        self.assertEqual(len(periods[0]), 2)
        registry = self.runner.SourceRegistry()
        with patch.object(Path, "glob", side_effect=AssertionError("PDF opened before ambiguity guard")):
            snapshot, ref, reasons = self.runner._snapshot(Path("/synthetic"), "Z00", "Synthetic Fund",
                                                           ["Z00"], periods[0], registry)
        self.assertIsNone(snapshot)
        self.assertIsNone(ref)
        self.assertEqual(reasons, ["selected_monthly_period_ambiguous"])

    def test_weekly_cannot_replace_missing_monthly(self):
        periods, _ = self.runner.monthly_candidates([report(34, cadence="HB"),
                                                    report(7, published="02.08.2026 10:00:00")])
        self.assertEqual(periods[0][0].period, "2026-07")

    def test_invalid_metadata_is_explicit(self):
        periods, reasons = self.runner.monthly_candidates([report(published=""), report(month=13), report(index="../1")])
        self.assertEqual(periods, [])
        self.assertEqual(set(reasons), {"monthly_publication_missing_or_invalid", "monthly_period_invalid", "monthly_disclosure_id_invalid"})
        self.assertEqual(self.runner.monthly_candidates({})[1], ["report_list_missing_or_invalid"])

    def test_unopened_code_rejected_before_source_reads(self):
        with patch.object(Path, "glob", side_effect=AssertionError("source read")):
            with self.assertRaises(ValueError):
                self.runner._snapshot(Path("/synthetic"), "BAD", "Synthetic Fund", ["Z00"], [], self.runner.SourceRegistry())

    def test_selected_missing_pdf_never_uses_previous_period(self):
        periods, _ = self.runner.monthly_candidates([report(), report(7, published="02.08.2026 10:00:00", index=2)])
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / "raw/kap/reports/Z00"
            folder.mkdir(parents=True)
            (folder / "2026-07_2.pdf").write_bytes(b"%PDF-synthetic")
            snapshot, _, reasons = self.runner._snapshot(root, "Z00", "Synthetic Fund", ["Z00"], periods[0], self.runner.SourceRegistry())
        self.assertIsNone(snapshot)
        self.assertEqual(reasons, ["selected_pdf_missing"])

    def test_future_numeric_changes_cannot_change_selection(self):
        future = report(9, published="02.10.2026 10:00:00", index=2)
        before = self.runner.monthly_candidates([report(), future])
        future["value"] = "99999999"
        self.assertEqual(self.runner.monthly_candidates([report(), future]), before)

    def test_monthly_publication_cannot_precede_reported_month_end(self):
        periods, reasons = self.runner.monthly_candidates([report(published="10.08.2026 10:00:00")])
        self.assertEqual(periods, [])
        self.assertEqual(reasons, ["monthly_publication_precedes_period_end"])

    def test_identity_normalization_preserves_turkish_words(self):
        self.assertEqual(self.runner._normalized("ÖRNEK PORTFÖY (TL) FONU"), "ornek portfoy tl fonu")

    def test_printed_month_and_year_must_be_unique(self):
        self.assertEqual(self.runner.printed_monthly_period("Ağustos-2026\nSynthetic Fund"), "2026-08")
        self.assertEqual(self.runner.printed_monthly_period("2026 TEMMUZ"), "2026-07")
        self.assertIsNone(self.runner.printed_monthly_period("Ağustos 2026 / Ekim 2026"))
        self.assertIsNone(self.runner.printed_monthly_period("2026-08 / Synthetic Fund"))

    def test_future_period_inside_renamed_pdf_never_reaches_parser(self):
        class Page:
            def get_text(self, mode):
                return "EKİM 2026\nSynthetic Fund"
        class Document:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def __len__(self): return 1
            def __getitem__(self, index): return Page()
        fake_fitz = SimpleNamespace(open=lambda **kwargs: Document())
        periods, _ = self.runner.monthly_candidates([report()])
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / "raw/kap/reports/Z00"
            folder.mkdir(parents=True)
            (folder / "2026-08_1.pdf").write_bytes(b"%PDF-synthetic")
            with patch.dict(sys.modules, {"fitz": fake_fitz}), patch.object(self.runner,
                    "read_security_holdings", side_effect=AssertionError("future-period values parsed")):
                snapshot, ref, reasons = self.runner._snapshot(root, "Z00", "Synthetic Fund", ["Z00"], periods[0], self.runner.SourceRegistry())
        self.assertIsNotNone(ref)
        self.assertIn("selected_pdf_monthly_period_mismatch", snapshot.problems)
        self.assertFalse(snapshot.reconciled)
        self.assertEqual(reasons, [])


class RegistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner = load_runner()

    def test_uncommitted_or_mutated_runtime_refused_before_data(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            for relative in (self.runner.PROTOCOL_REL, self.runner.ALLOWLIST_REL, *self.runner.RUNTIME_FILES):
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("synthetic runtime\n")
            (root / self.runner.ALLOWLIST_REL).write_text("\n".join(f"Z{x:02}" for x in range(100)))
            with self.assertRaises(ValueError):
                self.runner.verify_registration(root)
            subprocess.run(["git", "-C", str(root), "add", "."], check=True)
            subprocess.run(["git", "-C", str(root), "-c", "user.name=Synthetic", "-c",
                            "user.email=synthetic@example.invalid", "commit", "-qm", "Synthetic registration"], check=True)
            selected, registration = self.runner.verify_registration(root)
            self.assertEqual(len(selected), 100)
            self.assertEqual(set(registration["code_manifest"]),
                {r.as_posix() for r in (self.runner.PROTOCOL_REL, self.runner.ALLOWLIST_REL, *self.runner.RUNTIME_FILES)})
            (root / self.runner.RUNTIME_FILES[0]).write_text("changed synthetic runtime")
            with self.assertRaises(ValueError):
                self.runner.verify_registration(root)


if __name__ == "__main__":
    unittest.main()
