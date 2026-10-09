"""Authored PDF words; no third-party portfolio numbers or identities."""
from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal, Inexact, Rounded, ROUND_DOWN, localcontext

from p50k.providers.security_holdings import SECURITY_TYPES, read_security_holdings
from p50k.providers.thf_holdings import HoldingsReadError, PositionedWord


def word(text, x0, x1, y, height=7, page=1):
    return PositionedWord(page, x0, y, x1, y + height, text)


def fixture():
    words = [word("III-FON PORTFÖY DEĞERİ TABLOSU", 20, 250, 500, 10),
             word("ISIN", 233, 247, 540), word("KODU", 249, 269, 540),
             word("TOPLAM", 758, 787, 540), word("DEĞER", 789, 814, 540),
             word("HİSSE SENETLERİ", 20, 160, 570, 10),
             word("Hisse Türk", 20, 80, 590, 9)]
    for y, name, isin, value in [(620, "ALPHA", "TRSYNTH00001", "60,00"),
                                 (650, "ALPHA", "TRSYNTH00001", "30,00")]:
        words += [word(name, 20, 75, y), word("TL", 100, 108, y),
                  word(isin, 223, 277, y + 10), word(value, 760, 817, y)]
    for y, height in [(680, 8), (695, 9)]:
        words += [word("GRUP", 24 if height == 8 else 20, 47, y, height),
                  word("TOPLAMI", 50, 86, y, height), word("90,00", 760, 817, y, height)]
    words += [word("BORÇLANMA SENETLERİ", 20, 190, 720, 10),
              word("Devlet Tahvili", 20, 95, 740, 9),
              word("BETA", 20, 55, 760), word("TL", 100, 108, 760),
              word("TRSYNTH00002", 223, 277, 760), word("10,00", 760, 817, 760)]
    for y, height in [(780, 8), (795, 9)]:
        words += [word("GRUP", 24 if height == 8 else 20, 47, y, height),
                  word("TOPLAMI", 50, 86, y, height), word("10,00", 760, 817, y, height)]
    words += [word("FON PORTFÖY DEĞERİ", 20, 185, 820, 10), word("100,00", 760, 817, 820, 10),
              word("IV-FON TOPLAM DEĞERİ TABLOSU", 20, 250, 850, 10),
              word("A-)FON PORTFÖY DEĞERİ", 20, 180, 880), word("100,00", 250, 329, 880),
              word("FON TOPLAM DEĞERİ", 20, 180, 910), word("95,00", 250, 331, 910),
              word("V-AY İÇİNDE YAPILAN GİDERLER", 20, 250, 950, 10)]
    return words


def read(words=None, **changes):
    arguments = dict(page_sizes=[(950.0, 1200.0)], report_period="2026-08",
                     published_at=datetime(2026, 9, 2, tzinfo=timezone.utc),
                     source_path="synthetic/FUND.pdf", source_sha256="a" * 64)
    arguments.update(changes)
    return read_security_holdings(fixture() if words is None else words, **arguments)


class SecurityHoldingsTests(unittest.TestCase):
    def test_all_source_lots_and_distinct_denominators_are_preserved(self):
        snapshot = read()
        self.assertTrue(snapshot.reconciled, snapshot.problems)
        self.assertEqual(len(snapshot.rows), 3)
        self.assertEqual(snapshot.rows[0].isin, snapshot.rows[1].isin)
        self.assertEqual(snapshot.rows[0].instrument_type, "EQUITY")
        self.assertEqual(snapshot.rows[2].instrument_type, "BOND")
        self.assertEqual(snapshot.portfolio_total.value, Decimal("100.00"))
        self.assertEqual(snapshot.fund_net_assets.value, Decimal("95.00"))
        self.assertEqual(snapshot.excluded_rows, ())
        self.assertEqual(snapshot.unidentified_rows, ())

    def test_duplicate_group_totals_are_not_position_rows(self):
        snapshot = read()
        self.assertEqual(sum((r.position_value.value for r in snapshot.rows), Decimal(0)), Decimal("100.00"))
        self.assertEqual([r.native_name for r in snapshot.rows], ["ALPHA", "ALPHA", "BETA"])

    def test_wrapped_isin_and_source_geometry_are_retained(self):
        row = read().rows[0]
        self.assertEqual(row.isin, "TRSYNTH00001")
        self.assertEqual(row.position_value.raw, "60,00")
        self.assertEqual(row.position_value.source_bbox, (760, 620, 817, 627))
        self.assertEqual(row.source_bbox, (20, 620, 817, 627))

    def test_missing_identifier_is_partial_and_source_row_remains(self):
        words = [w for w in fixture() if not (w.text == "TRSYNTH00002")]
        snapshot = read(words)
        self.assertTrue(snapshot.reconciled)
        self.assertIsNone(snapshot.rows[-1].isin)
        self.assertEqual(snapshot.unidentified_rows, (snapshot.rows[-1],))
        self.assertIn("positive_identified_security_subset_is_partial", snapshot.qualifications)

    def test_unknown_asset_heading_never_inherits_preceding_security_type(self):
        words = [replace(w, text="UNSUPPORTED INSTRUMENTS") if w.text == "BORÇLANMA SENETLERİ"
                 else replace(w, text="Unsupported subtype") if w.text == "Devlet Tahvili" else w for w in fixture()]
        snapshot = read(words)
        self.assertTrue(snapshot.reconciled)
        self.assertEqual(snapshot.rows[-1].instrument_type, "UNKNOWN")
        self.assertFalse(snapshot.rows[-1].is_identified_security)
        self.assertEqual(snapshot.excluded_rows, (snapshot.rows[-1],))

    def test_repo_collateral_is_not_owned_security_even_with_isin(self):
        words = [replace(w, text="TERS REPO") if w.text in ("BORÇLANMA SENETLERİ", "Devlet Tahvili") else w for w in fixture()]
        snapshot = read(words)
        self.assertTrue(snapshot.reconciled)
        row = snapshot.rows[-1]
        self.assertEqual(row.instrument_type, "REPO")
        self.assertIsNotNone(row.isin)
        self.assertFalse(row.is_identified_security)
        self.assertEqual(snapshot.excluded_rows, (row,))

    def test_deposit_money_market_and_margin_types_are_excluded(self):
        for label, expected in [("MEVDUAT", "DEPOSIT"), ("BORSA PARA PİYASASI", "MONEY_MARKET"),
                                ("VIOP NAKİT TEMİNATI", "COLLATERAL")]:
            with self.subTest(label=label):
                words = [replace(w, text=label) if w.text in ("BORÇLANMA SENETLERİ", "Devlet Tahvili") else w for w in fixture()]
                row = read(words).rows[-1]
                self.assertEqual(row.instrument_type, expected)
                self.assertFalse(row.is_identified_security)

    def test_fund_units_do_not_supply_underlying_holdings(self):
        words = [replace(w, text="YATIRIM FONLARI") if w.text in ("BORÇLANMA SENETLERİ", "Devlet Tahvili") else w for w in fixture()]
        snapshot = read(words)
        self.assertEqual(snapshot.rows[-1].instrument_type, "FUND")
        self.assertIn("reported_fund_units_not_underlying_holdings", snapshot.qualifications)

    def test_signed_values_are_retained_and_never_absolute_valued(self):
        words = [replace(w, text="-30,00") if w.y0 == 650 and w.x1 == 817
                 else replace(w, text="30,00") if w.y0 in (680, 695) and w.x1 == 817
                 else replace(w, text="40,00") if (w.y0 == 820 and w.x1 == 817) or (w.y0 == 880 and w.x1 == 329)
                 else w for w in fixture()]
        snapshot = read(words)
        self.assertTrue(snapshot.reconciled, snapshot.problems)
        self.assertEqual(snapshot.rows[1].position_value.value, Decimal("-30.00"))
        self.assertIn("signed_negative_positions_interpretation_unknown", snapshot.qualifications)

    def test_derivative_name_cannot_be_counted_as_a_security(self):
        words = [replace(w, text="F_SYNTH1126") if w.text == "BETA" else w for w in fixture()]
        snapshot = read(words)
        self.assertEqual(snapshot.rows[-1].instrument_type, "DERIVATIVE")
        self.assertFalse(snapshot.rows[-1].is_identified_security)
        self.assertIn("derivatives_excluded_notional_not_owned_security_value", snapshot.qualifications)

    def test_gross_derivative_notional_is_never_a_portfolio_asset_value(self):
        words = [replace(w, y0=w.y0 + 100, y1=w.y1 + 100) if w.y0 >= 820 else w for w in fixture()]
        words += [word("Futures", 20, 85, 820, 10),
                  word("F_SYNTH1126", 20, 85, 850), word("TL", 100, 108, 850),
                  word("1.000,00", 760, 817, 850)]
        for y, height in [(880, 8), (895, 9)]:
            words += [word("GRUP", 24 if height == 8 else 20, 47, y, height),
                      word("TOPLAMI", 50, 86, y, height), word("1.000,00", 760, 817, y, height)]
        snapshot = read(words)
        self.assertTrue(snapshot.reconciled, snapshot.problems)
        self.assertEqual(snapshot.portfolio_total.value, Decimal("100.00"))
        derivative = snapshot.excluded_rows[-1]
        self.assertEqual(derivative.instrument_type, "DERIVATIVE")
        self.assertEqual(derivative.position_value.value, Decimal("1000.00"))
        self.assertIn("derivatives_excluded_notional_not_owned_security_value", snapshot.qualifications)
        self.assertIn("positive_identified_security_subset_is_partial", snapshot.qualifications)

    def test_wrong_derivative_notional_group_total_still_gates(self):
        words = [replace(w, text="F_SYNTH1126") if w.text == "BETA" else w for w in fixture()]
        words = [replace(w, text="11,00") if w.y0 == 780 and w.x1 == 817 else w for w in words]
        self.assertIn("subgroup_total_reconciliation_failed", read(words).problems)

    def test_sales_table_after_first_iv_never_enters_holdings(self):
        words = fixture() + [word("SALES", 20, 75, 1000), word("TRSYNTH00009", 223, 277, 1000),
                             word("999,00", 760, 817, 1000)]
        snapshot = read(words)
        self.assertTrue(snapshot.reconciled)
        self.assertEqual(len(snapshot.rows), 3)

    def test_later_header_and_totals_cannot_supply_section_iv_values(self):
        words = [w for w in fixture() if w.y0 != 880] + [word("A-)FON PORTFÖY DEĞERİ", 20, 180, 1000), word("100,00", 250, 329, 1000)]
        self.assertIn("section_iv_portfolio_total_ambiguous", read(words).problems)

    def test_missing_or_duplicate_section_boundary_is_unavailable(self):
        for words in ([w for w in fixture() if w.y0 != 500],
                      [w for w in fixture() if w.y0 != 850],
                      fixture() + [word("III-FON PORTFÖY DEĞERİ TABLOSU", 20, 250, 1000, 10)]):
            with self.subTest(words=len(words)):
                self.assertFalse(read(words).reconciled)

    def test_repeated_iv_page_boundary_heading_is_accepted(self):
        snapshot = read(fixture() + [word("IV-FON TOPLAM DEĞERİ TABLOSU", 20, 250, 870, 10)])
        self.assertTrue(snapshot.reconciled)

    def test_arithmetic_mismatch_is_a_problem_without_renormalizing(self):
        for y, edge, expected in [(680, 817, "subgroup_total_reconciliation_failed"),
                                  (695, 817, "class_total_reconciliation_failed"),
                                  (820, 817, "portfolio_rows_reconciliation_failed"),
                                  (880, 329, "section_iv_portfolio_reconciliation_failed")]:
            with self.subTest(y=y):
                words = [replace(w, text="123,00") if w.y0 == y and w.x1 == edge else w for w in fixture()]
                self.assertIn(expected, read(words).problems)

    def test_rounding_half_units_not_empirical_tolerance(self):
        words = [replace(w, text="60,0050") if w.y0 == 620 and w.x1 == 817 else w for w in fixture()]
        self.assertTrue(read(words).reconciled)
        words = [replace(w, text="60,1000") if w.y0 == 620 and w.x1 == 817 else w for w in fixture()]
        self.assertFalse(read(words).reconciled)

    def test_ambiguous_identity_and_numeric_cells_gate_metrics(self):
        words = fixture() + [word("TRSYNTH00008", 222, 276, 633)]
        self.assertIn("row_identity_ambiguous", read(words).problems)
        words = [replace(w, text="1.20,00") if w.y0 == 620 and w.x1 == 817 else w for w in fixture()]
        self.assertIn("position_or_group_value_unreadable", read(words).problems)
        words = fixture() + [word("6,00", 770, 817, 620)]
        self.assertIn("position_or_group_value_unreadable", read(words).problems)

    def test_unsupported_geometry_and_columns_do_not_get_fallbacks(self):
        snapshot = read(page_sizes=[(595.0, 842.0)])
        self.assertFalse(snapshot.supported_profile)
        self.assertEqual(snapshot.rows, ())
        self.assertIn("unsupported_page_geometry", snapshot.problems)
        self.assertIn("unsupported_value_or_identity_columns", read([w for w in fixture() if w.text != "ISIN"]).problems)

    def test_nonfinite_and_out_of_range_words_rejected(self):
        for change in ({"x0": float("nan")}, {"page": 2}, {"y1": 1201}, {"page": True}):
            with self.subTest(change=change):
                snapshot = read([replace(fixture()[0], **change), *fixture()[1:]])
                self.assertIn("invalid_source_word", snapshot.problems)

    def test_provenance_and_month_identity_required(self):
        for changes in ({"report_period": "2026-13"}, {"source_sha256": "bad"},
                        {"source_path": ""}, {"published_at": datetime(2026, 9, 2)}):
            with self.subTest(changes=changes), self.assertRaises(HoldingsReadError):
                read(**changes)

    def test_caller_decimal_rounding_and_traps_do_not_change_results(self):
        expected = read()
        with localcontext() as context:
            context.prec = 2
            context.rounding = ROUND_DOWN
            context.traps[Inexact] = True
            context.traps[Rounded] = True
            actual = read()
        self.assertEqual(actual, expected)

    def test_parser_does_not_compute_concentration_or_thresholds(self):
        snapshot = read()
        self.assertFalse(hasattr(snapshot, "hhi"))
        self.assertFalse(hasattr(snapshot, "research_screen"))
        self.assertEqual(SECURITY_TYPES, frozenset({"EQUITY", "BOND", "FUND", "OTHER_SECURITY"}))


if __name__ == "__main__":
    unittest.main()
