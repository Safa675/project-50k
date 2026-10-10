"""Leak detection keeps real ticker tokens without mistaking encoded package hashes."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

MODULE_PATH = Path(__file__).resolve().parents[2] / ".claude/skills/p50k-leak-scan/leak_scan.py"
SPEC = importlib.util.spec_from_file_location("product_leak_scan", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class LeakScanTests(unittest.TestCase):
    def test_actual_ticker_fields_are_detected(self) -> None:
        pattern = MODULE.code_pattern(["THF"])
        self.assertIsNotNone(pattern.search('"code": "THF"'))
        self.assertIsNotNone(pattern.search("fund=THF;"))

    def test_mixed_case_words_and_hash_substrings_are_not_tickers(self) -> None:
        pattern = MODULE.code_pattern(["THF"])
        self.assertIsNone(pattern.search('"integrity": "sha512-xTHFaX/sU1r"'))
        self.assertIsNone(pattern.search("someTHFword"))
        self.assertIsNone(pattern.search("ATHFB"))

    def test_fixture_ids_and_filenames_are_checked_without_metadata_collisions(self) -> None:
        pattern = MODULE.fixture_code_pattern(["THF"])
        self.assertIsNotNone(pattern.search('"fund": "THF"'))
        self.assertIsNotNone(pattern.search('"prices/THF.json"'))
        self.assertIsNotNone(pattern.search('"THF_2030.pdf"'))
        self.assertIsNone(pattern.search('b"%THF-1.7"'))
        self.assertIsNone(pattern.search('"P50K_THF_PASSWORD_FILE"'))
        self.assertIsNone(pattern.search('"THF/unit"'))
        self.assertIsNone(pattern.search('"license": "THF-2.0"'))

    def test_csv_checks_both_bare_and_quoted_cells(self) -> None:
        self.assertEqual(MODULE.csv_codes('THF,"TP2",100', {"THF", "TP2"}), {"THF", "TP2"})
        self.assertEqual(MODULE.csv_codes('fund,nav', {"THF", "TP2"}), set())


if __name__ == "__main__":
    unittest.main()
