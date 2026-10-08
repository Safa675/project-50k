"""Synthetic positioned words; no real KAP values are fixtures."""
from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal, Inexact, Rounded, ROUND_DOWN, localcontext

from p50k.providers.thf_holdings import HoldingsReadError, PositionedWord, read_thf_holdings


def word(text, x0, x1, y0, page=1):
    return PositionedWord(page, x0, y0, x1, y0 + 7, text)


def fixture():
    words = [word("D-)Toplam", 20, 63, 128), word("1.000,00", 334, 400, 134),
             word("HİSSE", 20, 45, 800)]
    # Same ISIN repeated, with a negative nominal entry preserved verbatim.
    for y, quantity, value, group, fpd, ftd in (
        (850, "12,00", "120,00", "120,00", "6,00", "12,00"),
        (900, "-2,00", "-20,00", "-20,00", "-1,00", "-2,00"),
    ):
        words += [word("ABCD", 20, 45, y), word("TL", 100, 108, y),
                  word("TRABCDEFGHIJ", 220, 275, y + 9),
                  word(quantity, 360, 413, y), word("10,000000", 710, 752, y),
                  word(value, 760, 817, y), word(group, 830, 850, y),
                  word(fpd, 860, 880, y), word(ftd, 890, 910, y)]
    for y in (950, 965):
        words += [word("GRUP", 20, 45, y), word("10,00", 370, 413, y),
                  word("100,00", 760, 817, y), word("5,00", 860, 880, y),
                  word("10,00", 890, 910, y)]
    words += [word("F_ABCD1126", 20, 75, 990), word("IV-FON", 20, 54, 1010),
              word("A-)FON", 20, 55, 1050), word("2.000,00", 260, 329, 1050),
              word("FON", 20, 40, 1090), word("1.000,00", 260, 331, 1090),
              word("V-AY", 20, 43, 1120)]
    return words


def read(words=None, **changes):
    arguments = dict(page_sizes=[(950.0, 1200.0)], report_period="2026-10",
                     published_at=datetime(2026, 11, 3, tzinfo=timezone.utc),
                     source_path="synthetic/THF.pdf", source_sha256="a" * 64)
    arguments.update(changes)
    return read_thf_holdings(fixture() if words is None else words, **arguments)


class ThfHoldingsTests(unittest.TestCase):
    def test_signed_duplicate_rows_and_denominators_are_preserved(self):
        snapshot = read()
        self.assertTrue(snapshot.reconciled)
        self.assertEqual(snapshot.percentage_warnings, ())
        self.assertEqual(len(snapshot.rows), 2)
        self.assertEqual(snapshot.rows[0].isin, snapshot.rows[1].isin)
        self.assertEqual(snapshot.rows[1].nominal_quantity.value, Decimal("-2.00"))
        self.assertEqual(snapshot.rows[1].position_value.value, Decimal("-20.00"))
        self.assertEqual(snapshot.rows[1].negative_quantity_interpretation, "UNKNOWN")
        self.assertEqual(snapshot.headline_total_value.value, Decimal("1000.00"))
        self.assertEqual(snapshot.portfolio_total_value.value, Decimal("2000.00"))
        self.assertEqual(snapshot.equity_group_total.value, Decimal("100.00"))
        self.assertTrue(snapshot.futures_present)

    def test_raw_precision_and_coordinates_are_retained(self):
        row = read().rows[0]
        self.assertEqual(row.valuation_price.raw, "10,000000")
        self.assertEqual(row.valuation_price.value.as_tuple().exponent, -6)
        self.assertEqual(row.position_value.source_bbox, (760, 850, 817, 857))
        self.assertEqual(row.source_isin_page, 1)

    def test_futures_are_not_spot_rows(self):
        self.assertEqual([r.symbol for r in read().rows], ["ABCD", "ABCD"])

    def test_missing_aligned_numeric_field_is_rejected(self):
        with self.assertRaises(HoldingsReadError):
            read([w for w in fixture() if not (w.y0 == 850 and w.x1 == 752)])

    def test_extra_isin_is_rejected(self):
        with self.assertRaises(HoldingsReadError):
            read(fixture() + [word("TRKLMNOPQRST", 220, 275, 870)])

    def test_unsupported_currency_is_rejected(self):
        words = [replace(w, text="USD") if w.text == "TL" else w for w in fixture()]
        with self.assertRaises(HoldingsReadError):
            read(words)

    def test_ambiguous_numeric_token_is_rejected(self):
        words = [replace(w, text="12,345") if w.y0 == 850 and w.x1 == 413 else w for w in fixture()]
        with self.assertRaises(HoldingsReadError):
            read(words)

    def test_malformed_grouping_is_rejected(self):
        words = [replace(w, text="1.20,00") if w.y0 == 850 and w.x1 == 817 else w for w in fixture()]
        with self.assertRaises(HoldingsReadError):
            read(words)

    def test_contradictory_repeated_group_total_is_rejected(self):
        words = [replace(w, text="101,00") if w.y0 == 965 and w.x1 == 817 else w for w in fixture()]
        with self.assertRaises(HoldingsReadError):
            read(words)

    def test_header_and_section_iv_disagreement_is_recorded(self):
        words = [replace(w, text="1.001,00") if w.y0 == 1090 and w.x1 == 331 else w for w in fixture()]
        self.assertIn("headline and section IV fund totals disagree", read(words).problems)

    def test_signed_group_quantity_disagreement_is_recorded(self):
        words = [replace(w, text="11,00") if w.y0 in (950, 965) and w.x1 == 413 else w for w in fixture()]
        self.assertIn("signed nominal sum disagrees with printed equity group total", read(words).problems)

    def test_quantity_price_disagreement_is_recorded(self):
        words = [replace(w, text="11,000000") if w.y0 == 850 and w.x1 == 752 else w for w in fixture()]
        self.assertTrue(any("quantity times" in p for p in read(words).problems))

    def test_percentages_are_audited_and_never_replace_position_values(self):
        words = [replace(w, text="19,00") if w.y0 == 850 and w.x1 == 910 else w for w in fixture()]
        snapshot = read(words)
        self.assertTrue(snapshot.reconciled)
        self.assertTrue(any("FTD" in p for p in snapshot.percentage_warnings))
        self.assertEqual(snapshot.rows[0].position_value.value, Decimal("120.00"))

    def test_non_positive_denominator_is_a_problem(self):
        words = [replace(w, text="0,00") if w.y0 == 134 else w for w in fixture()]
        self.assertIn("headline_total_value: non-positive", read(words).problems)

    def test_wrong_geometry_is_rejected(self):
        with self.assertRaises(HoldingsReadError):
            read(page_sizes=[(595.0, 842.0)])

    def test_non_finite_coordinates_are_rejected(self):
        with self.assertRaises(HoldingsReadError):
            read(fixture() + [replace(fixture()[0], x0=float("nan"))])

    def test_aware_publication_and_valid_period_and_provenance_are_required(self):
        for changes in ({"published_at": datetime(2026, 11, 3)},
                        {"report_period": "2026-13"}, {"source_sha256": "bad"},
                        {"source_path": ""}):
            with self.subTest(changes=changes), self.assertRaises(HoldingsReadError):
                read(**changes)

    def test_repeated_section_iv_heading_at_page_boundary_is_allowed(self):
        snapshot = read(fixture() + [word("IV-FON", 20, 54, 1030)])
        self.assertTrue(snapshot.reconciled)

    def test_caller_decimal_rounding_and_traps_do_not_change_reconciliation(self):
        # The negative row and group produce repeating ratios with this NAV.
        words = [replace(w, text="3.000,00") if (w.y0 == 134 or (w.y0 == 1090 and w.x1 == 331))
                 else replace(w, text="6.000,00") if w.y0 == 1050 and w.x1 == 329
                 else w for w in fixture()]
        expected = read(words)
        with localcontext() as context:
            context.prec = 2
            context.rounding = ROUND_DOWN
            context.traps[Inexact] = True
            context.traps[Rounded] = True
            actual = read(words)
        self.assertEqual(actual, expected)
        self.assertTrue(actual.reconciled)


if __name__ == "__main__":
    unittest.main()
