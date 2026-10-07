import unittest
from decimal import Decimal

from p50k.providers.kap_report import normalize, parse_number, read_headline

# Synthetic lines laid out like the five known report families. Values are made up:
# units x price = total value in every example.
IS_FAMILY = [
    "I-FONU TANITICI BİLGİLER",
    "D-)Toplam Değer/Net Varlık Değeri : 1,500.50",
    "E-) Katılma Payı Sayısı : 1,000.000",
    "II-FONUN PERFORMANSINA İLİŞKİN BİLGİLER",
    "A-)Ay Sonu Pay Fiyatı (TL) : 1,500500",
    "B-)Önceki Ay Pay Fiyatı (TL) : 1,490000",
    "C-)Aylık Pay Fiyatı Artış Oranı (TL) : 0,70",
    "I-)Katılma Payı İhraçlarından Kaynaklanan Nakit Girişleri (TL) : 12,50",
    "İ-)Katılma Payı İadelerinden Kaynaklanan Nakit Çıkışları (TL) : 3,25",
]
ZIRAAT_FAMILY = [
    "9 - FONU TANITICI BİLGİLER",
    "D - FON TUTARI : 1.400,25",
    "E - FON TOPLAM DEĞERİ : 1.500,50",
    "F - TEDAVÜLDEKİ PAY SAYISI : 1.000,000",
    "A - AY SONU PAY FİYATI : 1,500500",
    "B - ÖNCEKİ AY PAY FİYATI : 1,490000",
    "C - AYLIK PAY FİYATI ARTIŞ ORANI : 0,700000",
    "J - KATILMA PAYI İHRAÇLARINDAN KAYNAKLANAN NAKİT GİRİŞLERİ : 12,50",
    "K - KATILMA PAYI İADELERİNDEN KAYNAKLANAN NAKİT ÇIKIŞLARI : 3,25",
]
GARANTI_FAMILY = [
    "I- FONU TANITICI BİLGİLER",
    "Ç. FON TUTARI: (TL) 1,400.25",
    "D. TOPLAM DEĞER: (TL) 1,500.50",
    "E. KATILMA PAYI SAYISI : 1,000.000",
    "A. AY SONU KATILMA PAYI FİYATI: 1.500500",
    "B. ÖNCEKİ AY KATILMA PAYI FİYATI: 1.490000",
    "C.AYLIK KATILMA PAYI FİYATI ARTIŞ ORANI: 0.70%",
    "H.KATILMA PAYI İHRÇ. NAKİT GİRİŞLERİ: 12.50",
    "I.KATILMA PAYI İADE. NAKİT ÇIKIŞLARI: 3.25",
]
YAPI_KREDI_FAMILY = [  # labels wrapped over two lines
    "I- FONU TANITICI BİLGİLER",
    "Ç. TOPLAM DEĞER/NET : 1,500.50",
    "VARLIK DEĞERİ",
    "D. KATILMA PAYI SAYISI : 1,000.00",
    "A. AY SONU KATILMA PAYI : 1.500500",
    "FİYATI",
    "B. ÖNCEKİ AY KATILMA : 1.490000",
    "PAYI FİYATI",
    "C. AYLIK KATILMA PAYI : 0.70%",
    "FİYATI ARTIŞ ORANI",
]
WEEKLY_FAMILY = [  # the same form filed weekly: "Haftalık" labels
    "I-FONU TANITICI BİLGİLER",
    "D-)Toplam Değer/Net Varlık Değeri : 1.500,50",
    "E-) Katılma Payı Sayısı : 1.000,000",
    "II-FONUN PERFORMANSINA İLİŞKİN BİLGİLER",
    "A-)Haftalık Pay Fiyatı (TL) : 1,500500",
    "B-)Önceki Hafta Pay Fiyatı (TL) : 1,490000",
    "C-)Haftalik Pay Fiyatı Artış Oranı (TL) : 0,70",
]
PERIOD_END_FAMILY = [  # wrapped labels with "dönem" wording
    "I- FONU TANITICI BİLGİLER",
    "Ç. TOPLAM DEĞER/NET : 1,500.50",
    "VARLIK DEĞERİ",
    "D. KATILMA PAYI SAYISI : 1,000.00",
    "A. DÖNEM SONU KATILMA : 1.500500",
    "PAYI FİYATI",
    "B. ÖNCEKİ DÖNEM : 1.490000",
    "KATILMA PAYI FİYATI",
    "C. DÖNEMSEL KATILMA : 0.70%",
    "PAYI FİYATI ARTIŞ ORANI",
]
VALUES_ON_NEXT_LINE = [
    "D-)Toplam Değer/Net Varlık Değeri :",
    "1.500,50",
    "E-) Katılma Payı Sayısı :",
    "1.000,000",
    "A-)Ay Sonu Pay Fiyatı (TL) : 1,500500",
]


class ParseNumberTest(unittest.TestCase):
    def test_both_formats(self):
        cases = {
            "1.234,56": "1234.56", "1,234.56": "1234.56", "99.999.999.999,999": "99999999999.999",
            "1,000,000": "1000000", "1.000.000": "1000000", "7,654321": "7.654321", "7.654321": "7.654321",
            "0,70": "0.70", "0.70%": "0.70", "-0,41": "-0.41", "0,123": "0.123", "12": "12",
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(parse_number(text), Decimal(expected))

    def test_ambiguous_or_inconsistent_numbers_are_rejected(self):
        for text in ("1,234", "1.234", "1,23,456", "1.234.5", "1,234,56.78", "12,5.5,6", "abc", ""):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_number(text)

    def test_normalize_folds_turkish_letters(self):
        self.assertEqual(normalize("Ay Sonu Pay Fiyatı  (TL)"), "AY SONU PAY FIYATI (TL)")
        self.assertEqual(normalize("ÖNCEKİ AY İŞ ğüşçö"), "ONCEKI AY IS GUSCO")


class ReadHeadlineTest(unittest.TestCase):
    def check(self, lines, cash=True):
        headline = read_headline(lines)
        self.assertEqual(headline.problems if cash else tuple(p for p in headline.problems if "cash" not in p), ())
        self.assertEqual(headline.total_value, Decimal("1500.50"))
        self.assertEqual(headline.units_outstanding, Decimal("1000"))
        self.assertEqual(headline.period_end_price, Decimal("1.5005"))
        self.assertEqual(headline.previous_period_price, Decimal("1.49"))
        self.assertEqual(headline.period_change_pct, Decimal("0.70"))
        self.assertEqual(headline.units_outstanding * headline.period_end_price, headline.total_value)
        return headline

    def test_each_known_layout(self):
        for name, lines, cash in (("is", IS_FAMILY, True), ("ziraat", ZIRAAT_FAMILY, True),
                                  ("garanti", GARANTI_FAMILY, True), ("yapi kredi", YAPI_KREDI_FAMILY, False),
                                  ("weekly", WEEKLY_FAMILY, False), ("period end", PERIOD_END_FAMILY, False)):
            with self.subTest(layout=name):
                headline = self.check(lines, cash)
                if cash:
                    self.assertEqual((headline.cash_in, headline.cash_out),
                                     (Decimal("12.50"), Decimal("3.25")))

    def test_a_price_label_is_never_read_as_the_change_label(self):
        headline = read_headline(WEEKLY_FAMILY[:6])  # the change line is left out
        self.assertEqual(headline.period_end_price, Decimal("1.5005"))
        self.assertIsNone(headline.period_change_pct)

    def test_units_written_as_a_comma_grouped_integer(self):
        headline = read_headline(["E. KATILMA PAYI SAYISI : 2,000,000", "D. TOPLAM DEĞER: (TL) 3,001,000.00"])
        self.assertEqual((headline.units_outstanding, headline.total_value), (Decimal(2000000), Decimal("3001000.00")))

    def test_a_label_without_a_value_falls_back_to_the_next_line(self):
        headline = read_headline(VALUES_ON_NEXT_LINE)
        self.assertEqual((headline.total_value, headline.units_outstanding),
                         (Decimal("1500.50"), Decimal("1000")))

    def test_a_next_line_that_is_not_a_bare_number_is_not_taken(self):
        headline = read_headline(["D-)Toplam Değer/Net Varlık Değeri :", "E-) Katılma Payı Sayısı : 5,000.000"])
        self.assertIsNone(headline.total_value)
        self.assertIn("total_value: not found", headline.problems)
        self.assertEqual(headline.units_outstanding, Decimal("5000"))

    def test_only_the_first_section_is_read(self):
        lines = IS_FAMILY + ["III-FON PORTFÖY DEĞERİ TABLOSU", "FON TOPLAM DEĞERİ : 9.999,99",
                             "A-)Ay Sonu Pay Fiyatı (TL) : 9,999999"]
        headline = read_headline(lines)
        self.assertEqual(headline.total_value, Decimal("1500.50"))
        self.assertEqual(headline.period_end_price, Decimal("1.5005"))

    def test_an_ambiguous_number_is_reported_and_left_missing(self):
        headline = read_headline(["E-) Katılma Payı Sayısı : 1,234"])
        self.assertIsNone(headline.units_outstanding)
        self.assertTrue(any(p.startswith("units_outstanding: ambiguous") for p in headline.problems))

    def test_averages_and_fund_amount_are_not_mistaken_for_headline_fields(self):
        lines = ["D - FON TUTARI : 1.400,25", "G - AYLIK ORTALAMA TEDAVÜL ORANI : 5,0",
                 "F. AYLIK ORTALAMA PORTFÖY DEVİR HIZI: 2.5"]
        headline = read_headline(lines)
        self.assertIsNone(headline.total_value)
        self.assertIsNone(headline.period_change_pct)
        self.assertIsNone(headline.units_outstanding)

    def test_a_report_without_the_section_reads_nothing(self):
        headline = read_headline(["some other text", "FON TOPLAM DEĞERİ 9.999,99 100,00"])
        self.assertEqual(len(headline.problems), 7)
        self.assertTrue(all(getattr(headline, f) is None for f in (
            "total_value", "units_outstanding", "period_end_price")))


if __name__ == "__main__":
    unittest.main()
