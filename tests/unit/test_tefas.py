import json
import unittest
from datetime import date
from decimal import Decimal

from p50k.providers.tefas import FundNotFound, PricePoint, TefasClient, TefasUnavailable


def ok(rows):
    envelope = {"errorCode": None, "errorMessage": None, "resultList": rows}
    return 200, "application/json;charset=UTF-8", json.dumps(envelope).encode("utf-8")


class FakeTefas:
    """Serves canned responses keyed by (endpoint, fund code or fund type)."""

    def __init__(self) -> None:
        self.responses: dict[tuple[str, str], list] = {}
        self.calls: list[tuple[str, str, dict, dict]] = []

    def respond(self, endpoint, key, *responses):
        self.responses[(endpoint, key)] = list(responses)

    def __call__(self, url, body, headers):
        endpoint = url.rsplit("/", 1)[1]
        payload = json.loads(body)
        key = payload.get("fonKodu") or payload.get("fonTipi")
        self.calls.append((endpoint, key, payload, headers))
        queue = self.responses[(endpoint, key)]
        return queue.pop(0) if len(queue) > 1 else queue[0]


# Synthetic values: units x price = total value exactly.
SNAPSHOT_ROW = {
    "fonKodu": "TST", "fonUnvan": "TEST PORTFÖY HİSSE SENEDİ FONU", "sonFiyat": 1.234567,
    "gunlukGetiri": 0.5, "payAdet": 2000000, "portBuyukluk": 2469134.0, "fonKategori": "Hisse Senedi Fonu",
    "kategoriDerece": 3, "kategoriFonSay": 10, "yatirimciSayi": None, "pazarPayi": 0.01,
}


class TefasClientTest(unittest.TestCase):
    def setUp(self):
        self.tefas = FakeTefas()
        self.client = TefasClient(transport=self.tefas)

    def test_snapshot_keeps_exact_numbers_units_and_missing_values(self):
        self.tefas.respond("fonBilgiGetir", "TST", ok([SNAPSHOT_ROW]))
        snapshot = self.client.snapshot("tst")
        self.assertEqual(snapshot.price, Decimal("1.234567"))
        self.assertEqual(snapshot.units_outstanding, Decimal(2000000))
        self.assertEqual(snapshot.total_value, Decimal("2469134.0"))
        self.assertEqual(snapshot.units_outstanding * snapshot.price, snapshot.total_value)
        self.assertIsNone(snapshot.investors)  # missing stays missing, not 0
        self.assertEqual((snapshot.category_rank, snapshot.category_size), (3, 10))
        endpoint, key, payload, headers = self.tefas.calls[0]
        self.assertEqual((endpoint, key, payload), ("fonBilgiGetir", "TST", {"fonKodu": "TST"}))
        self.assertEqual(headers["Content-Type"], "application/json")

    def test_non_numeric_values_become_none(self):
        row = {**SNAPSHOT_ROW, "sonFiyat": "1,23", "yatirimciSayi": True, "kategoriDerece": 2.5}
        self.tefas.respond("fonBilgiGetir", "TST", ok([row]))
        snapshot = self.client.snapshot("TST")
        self.assertIsNone(snapshot.price)
        self.assertIsNone(snapshot.investors)
        self.assertIsNone(snapshot.category_rank)

    def test_empty_result_list_means_fund_not_found(self):
        self.tefas.respond("fonBilgiGetir", "OLD", ok([]))
        self.tefas.respond("fonFiyatBilgiGetir", "OLD", ok([]))
        with self.assertRaises(FundNotFound):
            self.client.snapshot("OLD")
        with self.assertRaises(FundNotFound):
            self.client.price_history("OLD")

    def test_unusable_responses_are_reported_as_unavailable(self):
        cases = {
            "HTTP error": (503, "text/html", b"busy"),
            "firewall page with 200": (200, "text/html", b"<html>blocked</html>"),
            "empty body": (200, "application/json", b"  "),
            "malformed JSON": (200, "application/json", b"{not json"),
            "TEFAS error message": (200, "application/json",
                                    json.dumps({"errorCode": 9, "errorMessage": "Sistem Hatası!!"}).encode()),
            "list instead of envelope": (200, "application/json", b"[]"),
        }
        for name, response in cases.items():
            with self.subTest(case=name):
                self.tefas.respond("fonBilgiGetir", "TST", response)
                with self.assertRaises(TefasUnavailable):
                    self.client.snapshot("TST")

    def test_price_history_is_sorted_and_skips_rows_without_a_date(self):
        rows = [
            {"tarih": "2026-10-06", "fiyat": 1.234567, "kategoriDerece": 3, "kategoriFonSay": 10},
            {"tarih": "2026-10-02", "fiyat": 1.2},
            {"tarih": "not a date", "fiyat": 1.0},
        ]
        self.tefas.respond("fonFiyatBilgiGetir", "TST", ok(rows))
        self.assertEqual(self.client.price_history("TST"), [
            PricePoint(date(2026, 10, 2), Decimal("1.2")),
            PricePoint(date(2026, 10, 6), Decimal("1.234567")),
        ])
        self.assertEqual(self.tefas.calls[0][2], {"fonKodu": "TST", "dil": "TR", "periyod": 13})

    def test_a_zero_or_missing_price_is_kept_as_a_dated_row_without_a_price(self):
        # TEFAS writes 0 where it has no price: before a fund starts and after its price stops.
        rows = [
            {"tarih": "2026-09-16", "fiyat": 2.5},
            {"tarih": "2026-09-17", "fiyat": 0},
            {"tarih": "2026-09-18", "fiyat": 0.0},
            {"tarih": "2026-09-21", "fiyat": None},
            {"tarih": "2026-09-22", "fiyat": -1},
        ]
        self.tefas.respond("fonFiyatBilgiGetir", "TST", ok(rows))
        points = self.client.price_history("TST")
        self.assertEqual([p.date.isoformat() for p in points],
                         ["2026-09-16", "2026-09-17", "2026-09-18", "2026-09-21", "2026-09-22"])
        self.assertEqual([p.price for p in points], [Decimal("2.5"), None, None, None, None])

    def test_a_zero_snapshot_price_is_none_while_other_zero_fields_are_kept(self):
        row = {**SNAPSHOT_ROW, "sonFiyat": 0, "payAdet": 0, "portBuyukluk": 0, "yatirimciSayi": 12345}
        self.tefas.respond("fonBilgiGetir", "TST", ok([row]))
        snapshot = self.client.snapshot("TST")
        self.assertIsNone(snapshot.price)
        self.assertEqual((snapshot.units_outstanding, snapshot.total_value, snapshot.investors),
                         (Decimal(0), Decimal(0), 12345))
        self.assertEqual(snapshot.raw["sonFiyat"], 0)  # the raw row keeps TEFAS's own zero

    def test_fund_list_requests_the_given_type(self):
        self.tefas.respond("fonGetiriBazliBilgiGetir", "YAT", ok([{"fonKodu": "TST"}]))
        self.assertEqual(self.client.fund_list(), [{"fonKodu": "TST"}])
        self.assertEqual(self.tefas.calls[0][2]["fonTipi"], "YAT")


if __name__ == "__main__":
    unittest.main()
