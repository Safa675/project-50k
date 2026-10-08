"""Synthetic geometry only: no original provider values or fund identities."""
import hashlib
import unittest
from decimal import Decimal, Inexact, Rounded, localcontext

from p50k.providers.kap_allocation import MONTHLY_AVERAGE, TextCell, read_allocation


def cell(text, x=20, y=10, width=None, height=8, page=1):
    return TextCell(page, x, y, x + (width if width is not None else max(4, len(text) * 4)), y + height, text)


def basic_rows(first="40,00", second="60,00"):
    return [
        cell("F-)Aylık Ortalama Portföydeki Menkul Kıymetler Yüzdesi", y=10),
        cell("a-)Hisse Senedi", x=42, y=30), cell(":", x=300, y=31), cell(first, x=330, y=31),
        cell("b-)Mevduat", x=42, y=46), cell(":", x=300, y=47), cell(second, x=330, y=47),
        cell("G-)Aylık Ortalama Portföy Devir Hızı", y=64),
        cell("a-)Hisse Senedi", x=42, y=80), cell(":", x=300, y=81), cell("9,00", x=330, y=81),
        cell("III-FON PORTFÖY DEĞERİ TABLOSU", y=110),
    ]


class ReadAllocationTest(unittest.TestCase):
    def assert_valid(self, cells, expected=None):
        table = read_allocation(cells)
        self.assertEqual(table.problems, ())
        self.assertEqual(table.basis, MONTHLY_AVERAGE)
        self.assertEqual(sum(table.weights.values()), Decimal(1))
        if expected is not None:
            self.assertEqual(table.weights, expected)
        return table

    def assert_invalid(self, cells, reason):
        table = read_allocation(cells)
        self.assertIsNone(table.weights)
        self.assertIsNone(table.category_schema)
        self.assertTrue(any(reason in item for item in table.problems), table.problems)
        return table

    def test_explicit_categories_and_turnover_duplicates_are_separated(self):
        cells = basic_rows()
        cells[7:7] = [cell("g2-)BPP-BPP Borçlanma", x=42, y=56), cell(":", x=300, y=56), cell("0,00", x=330, y=56)]
        table = self.assert_valid(cells, {
            "HISSE SENEDI": Decimal("0.4"), "MEVDUAT": Decimal("0.6"),
            "BPP-BPP BORCLANMA": Decimal(0),
        })
        self.assertEqual(len(table.source_rows), 3)
        self.assertEqual(table.source_rows[0].label, "a-)Hisse Senedi")
        self.assertEqual(table.source_rows[0].weight_percent, Decimal("40.00"))
        self.assertEqual(table.source_rows[0].rect, (42, 30, 350, 39))

    def test_input_order_does_not_control_label_value_pairing(self):
        self.assert_valid(list(reversed(basic_rows())), {
            "HISSE SENEDI": Decimal("0.4"), "MEVDUAT": Decimal("0.6"),
        })

    def test_sparse_inline_six_decimal_profile(self):
        self.assert_valid([
            cell("F - AYLIK ORTALAMA PORTFÖYDEKİ MENKUL KIYMETLER YÜZDESİ", y=10),
            cell("Ters Repo : 25,000001", y=28), cell("Vadeli Mevduat : 74,999999", y=44),
            cell("G - AYLIK ORTALAMA TEDAVÜL ORANI : 20,000000", y=62),
        ], {"TERS REPO": Decimal("0.25000001"), "VADELI MEVDUAT": Decimal("0.74999999")})

    def test_wrapped_four_line_header_and_values_supplied_before_labels(self):
        self.assert_valid([
            cell("E. AYLIK ORTALAMA", y=10), cell("PORTFÖYDEKİ", y=20),
            cell("MENKUL KIYMETLER", y=30), cell(":", x=300, y=34), cell("YÜZDESİ", y=40),
            cell("30.00%", x=350, y=58), cell("Devlet Tahvili", x=24, y=58),
            cell("70.00%", x=350, y=72), cell("Vadeli Mevduat", x=24, y=72),
            cell("F. AYLIK ORTALAMA", y=90), cell(":", x=300, y=90), cell("2.00%", x=350, y=90),
            cell("PORTFÖY DEVİR HIZI", y=100),
        ], {"DEVLET TAHVILI": Decimal("0.3"), "VADELI MEVDUAT": Decimal("0.7")})

    def test_tight_row_spacing_is_not_merged(self):
        self.assert_valid([
            cell("E. AYLIK ORTALAMA PORTFÖYDEKİ MENKUL KIYMETLER YÜZDESİ", y=10, height=3),
            cell("ÖZEL SEKTÖR TAHVİLİ", y=16, height=3), cell("15.50%", x=220, y=16, height=3),
            cell("MEVDUAT", y=21, height=3), cell("84.50%", x=220, y=21, height=3),
            cell("F. AYLIK ORTALAMA TEDAVÜL ORANI", y=26, height=3),
        ])

    def test_orthographic_keys_and_schema_are_order_independent(self):
        a = self.assert_valid(basic_rows())
        b = basic_rows("60.00", "40.00")
        b[1] = cell("B. MEVDUAT", x=42, y=30)
        b[4] = cell("A. HİSSE   SENEDİ", x=42, y=46)
        b = self.assert_valid(b)
        self.assertEqual(a.weights, b.weights)
        self.assertEqual(a.category_schema, b.category_schema)
        self.assertEqual(a.category_schema, hashlib.sha256(b"HISSE SENEDI\nMEVDUAT").hexdigest())

    def test_economic_aliases_are_not_merged(self):
        a = self.assert_valid(basic_rows())
        cells = basic_rows()
        cells[4] = cell("b-)Vadeli Mevduat", x=42, y=46)
        b = self.assert_valid(cells)
        self.assertNotEqual(a.category_schema, b.category_schema)
        self.assertIn("VADELI MEVDUAT", b.weights)
        self.assertNotIn("MEVDUAT", b.weights)

    def test_category_appearance_changes_schema_without_zero_imputation(self):
        before = self.assert_valid(basic_rows())
        cells = basic_rows("40.00", "50.00")
        cells[7:7] = [cell("Taahhütlü İşlemler", x=42, y=56), cell("10.00%", x=330, y=56)]
        after = self.assert_valid(cells)
        self.assertNotEqual(before.category_schema, after.category_schema)
        self.assertNotIn("TAAHHUTLU ISLEMLER", before.weights)

    def test_missing_row_remains_missing(self):
        cells = basic_rows()
        del cells[4:7]
        table = self.assert_invalid(cells, "do not sum to 100")
        self.assertEqual(len(table.source_rows), 1)

    def test_missing_value_does_not_take_the_next_rows_value(self):
        cells = basic_rows()
        del cells[3]
        self.assert_invalid(cells, "invalid weight")

    def test_duplicate_categories_fail_even_when_total_is_100(self):
        cells = basic_rows("0.00", "100.00")
        cells[4] = cell("b-)HİSSE SENEDİ", x=42, y=46)
        table = self.assert_invalid(cells, "duplicate allocation category")
        self.assertEqual(len(table.source_rows), 2)

    def test_bad_numbers_and_signed_exposures_abstain(self):
        for number in ("-1.00", "101.00", "NaN", "Infinity", "1,234", "1,23,456", "−1.00", "(1.00)"):
            with self.subTest(number=number):
                self.assert_invalid(basic_rows(number, "100.00"), "weight")

    def test_no_rounding_tolerance_or_normalization(self):
        for first, second in (("40.00", "59.99"), ("40.00", "60.01"), ("0.00", "0.00")):
            with self.subTest(values=(first, second)):
                self.assert_invalid(basic_rows(first, second), "do not sum to 100")

    def test_multiple_numeric_cells_fail_closed(self):
        cells = basic_rows()
        cells.insert(4, cell("7.00", x=430, y=31))
        self.assert_invalid(cells, "invalid weight")

    def test_orphan_value_is_not_attached_to_a_different_row(self):
        cells = basic_rows()
        cells.insert(7, cell("0.00%", x=330, y=56))
        self.assert_invalid(cells, "value without a category")

    def test_total_is_not_a_category(self):
        self.assert_invalid([
            cell("F-)Aylık Ortalama Portföydeki Menkul Kıymetler Yüzdesi", y=10),
            cell("TOPLAM : 100.00", y=30), cell("G-)Aylık Ortalama Portföy Devir Hızı", y=50),
        ], "total is not an allocation category")

    def test_wrong_basis_and_unbounded_table_fail_closed(self):
        self.assert_invalid([cell("Ay Sonu Varlık Dağılımı"), cell("Hisse Senedi : 100.00", y=30)], "not found")
        self.assert_invalid(basic_rows()[:7], "no same-page, same-column boundary")

    def test_section_on_another_page_does_not_close_this_page(self):
        cells = basic_rows()[:7] + [cell("G-)Aylık Ortalama Portföy Devir Hızı", y=10, page=2)]
        self.assert_invalid(cells, "no same-page, same-column boundary")

    def test_duplicate_allocation_sections_are_ambiguous(self):
        cells = basic_rows() + [cell("E. Aylık Ortalama Portföydeki Menkul Kıymetler Yüzdesi", y=10, page=2)]
        self.assert_invalid(cells, "ambiguous allocation sections")

    def test_parallel_turnover_column_does_not_close_or_pollute_allocation(self):
        cells = basic_rows()
        cells += [
            cell("G-)Aylık Ortalama Portföy Devir Hızı", x=600, y=22),
            cell("Hisse Senedi", x=620, y=30), cell("8.00%", x=840, y=31),
            cell("Diğer", x=620, y=46), cell("2.00%", x=840, y=47),
        ]
        self.assert_valid(cells, {"HISSE SENEDI": Decimal("0.4"), "MEVDUAT": Decimal("0.6")})

    def test_unrecognized_parallel_data_is_ambiguous(self):
        cells = basic_rows() + [cell("Other", x=620, y=30), cell("8.00%", x=840, y=31)]
        self.assert_invalid(cells, "invalid weight")

    def test_left_dedented_zero_category_is_not_silently_discarded(self):
        self.assert_invalid([
            cell("F-)Aylık Ortalama Portföydeki Menkul Kıymetler Yüzdesi", x=100, y=10),
            cell("Hisse Senedi : 100.00", x=100, y=30),
            cell("Diğer : 0.00", x=20, y=46),
            cell("G-)Aylık Ortalama Portföy Devir Hızı", x=100, y=64),
        ], "unsupported left-column data")

    def test_bad_geometry_is_rejected(self):
        for broken in (
            TextCell(1, 20, 10, 20, 18, "text"), TextCell(1, float("nan"), 10, 30, 18, "text"),
            TextCell(0, 20, 10, 30, 18, "text"),
            TextCell(-1, 20, 10, 30, 18, "text"), TextCell(True, 20, 10, 30, 18, "text"),
        ):
            with self.subTest(cell=broken):
                self.assert_invalid(basic_rows() + [broken], "invalid text cell")

    def test_empty_input_and_empty_section_are_not_distributions(self):
        self.assert_invalid([], "not found")
        self.assert_invalid([basic_rows()[0], basic_rows()[7]], "contains no valid rows")

    def test_long_decimal_coefficients_do_not_round_into_closure(self):
        self.assert_invalid(basic_rows("40.00000000000000000000000000001", "60.00"), "do not sum to 100")

    def test_tiny_total_error_is_not_rounded_away(self):
        self.assert_invalid(basic_rows("100", "0." + "0" * 199 + "1"), "do not sum to 100")

    def test_caller_decimal_context_does_not_change_parser_decisions(self):
        with localcontext() as context:
            context.prec = 2
            context.Emin = -2
            context.Emax = 2
            context.traps[Inexact] = True
            context.traps[Rounded] = True
            table = read_allocation(basic_rows("25.000001", "74.999999"))
            self.assertEqual(table.problems, ())
            self.assertEqual(table.weights["HISSE SENEDI"], Decimal("0.25000001"))
            self.assert_invalid(basic_rows("100", "0." + "0" * 199 + "1"), "do not sum to 100")

    def test_untrusted_input_limits_are_explicit(self):
        self.assert_invalid([cell("x" * 4097)], "invalid text cell")
        self.assert_invalid([cell("x")] * 100001, "text cell limit exceeded")


if __name__ == "__main__":
    unittest.main()
