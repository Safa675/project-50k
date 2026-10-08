"""Synthetic input/commit gates for the strictly scoped research runner."""
from __future__ import annotations

from datetime import date
from decimal import Decimal, Inexact, Rounded, localcontext
import importlib.util
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest

_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _ROOT / "research/events/2026-09-17-spk-liquidations/fund_holdings_divergence/run.py"
_SPEC = importlib.util.spec_from_file_location("thf_divergence_runner", _SCRIPT)
runner = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(runner)


class RunnerGateTests(unittest.TestCase):
    def test_scope_rejects_other_fund_before_reading_rows(self):
        with self.assertRaises(runner.ResearchInputError):
            runner.load_nav({"fund": "OTHER", "rows": []})

    def test_nav_zero_and_null_stay_missing_future_labels_excluded(self):
        out = runner.load_nav({"fund": "THF", "rows": [
            ["2026-09-14", 0], ["2026-09-15", None],
            ["2026-09-16", "1.25"], ["2026-09-17", "99999"]]})
        self.assertEqual(out, {date(2026, 9, 14): None, date(2026, 9, 15): None,
                               date(2026, 9, 16): Decimal("1.25")})

    def test_duplicate_nav_labels_rejected(self):
        with self.assertRaises(runner.ResearchInputError):
            runner.load_nav({"fund": "THF", "rows": [["2026-01-02", 1], ["2026-01-02", 2]]})

    def test_nonfinite_and_nonpositive_are_missing_boolean_rejected(self):
        for value in (0, -1, "NaN", "Infinity", None):
            self.assertIsNone(runner.decimal_or_missing(value))
        with self.assertRaises(runner.ResearchInputError):
            runner.decimal_or_missing(True)

    def test_escape_and_symlinks_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "file").write_text("synthetic")
            (root / "alias").symlink_to(root / "file")
            for path in ("../outside", root.parent / "outside", "alias"):
                with self.assertRaises(runner.ResearchInputError):
                    runner.canonical_path(root, path)

    def test_code_must_match_committed_blob(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            (root / "runtime.py").write_text("# synthetic runtime\n")
            subprocess.run(["git", "add", "runtime.py"], cwd=root, check=True)
            subprocess.run(["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                            "commit", "-qm", "synthetic fixture"], cwd=root, check=True)
            proof = runner.committed_code(root, ("runtime.py",))
            self.assertEqual(proof["files"][0]["sha256"], runner.sha256(root / "runtime.py"))
            (root / "runtime.py").write_text("# changed synthetic runtime\n")
            with self.assertRaises(runner.ResearchInputError):
                runner.committed_code(root, ("runtime.py",))

    def test_unknown_security_not_guessed_and_contradictions_rejected(self):
        universe = {"fund_code": "THF", "symbol_to_multiple_ISIN_contradictions": [],
                    "securities": [{"symbol": "AAA", "isins": ["SYNTHETIC_A"]}]}
        selection = {"fund_code": "THF", "equity_symbols": ["BBB"], "alias_choices": []}
        self.assertEqual(runner.identity_lookup(universe, selection), {})
        universe["symbol_to_multiple_ISIN_contradictions"] = ["synthetic contradiction"]
        with self.assertRaises(runner.ResearchInputError):
            runner.identity_lookup(universe, selection)

    def test_unregistered_alias_is_rejected(self):
        universe = {"fund_code": "THF", "symbol_to_multiple_ISIN_contradictions": [],
                    "securities": [{"symbol": name, "isins": ["SYNTHETIC_A"]} for name in ("AAA", "BBB")]}
        selection = {"fund_code": "THF", "equity_symbols": ["BBB"],
                     "alias_choices": [{"fetch_symbol": "BBB", "reported_isin": "SYNTHETIC_A",
                                        "omitted_superseded_labels": ["AAA"]}]}
        with self.assertRaises(runner.ResearchInputError):
            runner.identity_lookup(universe, selection)

    def test_signed_row_weights_distinguished_from_netted_isin_weights(self):
        rows = [SimpleNamespace(isin=isin, position_value=SimpleNamespace(value=Decimal(value)))
                for isin, value in (("A", "100"), ("A", "-20"), ("B", "30"))]
        source = SimpleNamespace(headline_total_value=SimpleNamespace(value=Decimal("100")), rows=rows)
        out = runner.reported_weight_summary(source)
        self.assertEqual(out["positive_net_isin_weight"], "1.1")
        self.assertEqual(out["absolute_negative_net_isin_weight"], "0")
        self.assertEqual(out["positive_reported_row_weight"], "1.3")
        self.assertEqual(out["absolute_negative_reported_row_weight"], "0.2")
        self.assertEqual(out["gross_reported_position_weight"], "1.5")
        self.assertEqual(out["negative_reported_position_count"], 1)

    def test_summary_percent_and_absolute_selection_ignore_ambient_precision(self):
        rows = []
        for interval, gap in enumerate(("0.123456781", "0.123456789"), 1):
            rows.append(SimpleNamespace(valuation_date=date(2026, 1, interval + 1),
                        fund_row_label=date(2026, 1, interval + 2), interval_number=interval,
                        metric=SimpleNamespace(availability="AVAILABLE", actual_return=Decimal(gap),
                                               equity_proxy_return=Decimal(0), gap=Decimal(gap))))
        window = SimpleNamespace(rows=rows)
        expected = runner.summary(window)
        with localcontext() as context:
            context.prec = 3
            context.traps[Inexact] = True
            context.traps[Rounded] = True
            actual = runner.summary(window)
        self.assertEqual(actual, expected)
        self.assertEqual(actual["largest_absolute_gap"]["interval_number"], 2)
        self.assertEqual(actual["endpoint"]["gap_percentage_points"], "12.345678900")

    def test_weight_ratios_ignore_ambient_inexact_and_rounded_traps(self):
        source = SimpleNamespace(headline_total_value=SimpleNamespace(value=Decimal("3")),
                 rows=[SimpleNamespace(isin="A", position_value=SimpleNamespace(value=Decimal("1")))])
        expected = runner.reported_weight_summary(source)
        with localcontext() as context:
            context.prec = 3
            context.traps[Inexact] = True
            context.traps[Rounded] = True
            actual = runner.reported_weight_summary(source)
        self.assertEqual(actual, expected)
        self.assertEqual(actual["positive_net_isin_weight"], "0." + "3" * 80)


if __name__ == "__main__":
    unittest.main()
