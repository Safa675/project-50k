import json
import logging
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from p50k.jobs.price_history import download, load
from p50k.providers.tefas import TefasClient

from tests.unit.test_tefas import FakeTefas, ok

ROWS = [
    {"tarih": "2026-10-06", "fiyat": 1.234567, "kategoriDerece": 3, "kategoriFonSay": 10},
    {"tarih": "2026-10-05", "fiyat": 1.2, "kategoriDerece": 3, "kategoriFonSay": 10},
]
NOW = datetime(2026, 10, 7, 9, 0, tzinfo=timezone.utc)


class PriceHistoryDownloadTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.out = Path(tmp.name) / "prices"
        self.tefas = FakeTefas()
        self.sleeps = []
        logger = logging.getLogger("p50k")
        handler = logging.NullHandler()
        logger.addHandler(handler)
        self.addCleanup(logger.removeHandler, handler)

    def run_download(self, codes, **kwargs):
        return download(TefasClient(transport=self.tefas), codes, self.out,
                        sleep=self.sleeps.append, now=lambda: NOW, **kwargs)

    def test_saves_sorted_dated_rows_with_exact_prices(self):
        self.tefas.respond("fonFiyatBilgiGetir", "TST", ok(ROWS))
        summary = self.run_download(["tst"], periyod=12)
        self.assertEqual(summary.saved, {"TST": 2})
        saved = json.loads((self.out / "TST.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["rows"], [["2026-10-05", "1.2"], ["2026-10-06", "1.234567"]])
        self.assertEqual((saved["fund"], saved["periyod"], saved["retrieved_at"]),
                         ("TST", 12, NOW.isoformat()))
        self.assertEqual(load(self.out / "TST.json"), [("2026-10-05", "1.2"), ("2026-10-06", "1.234567")])
        self.assertEqual(self.tefas.calls[0][2]["periyod"], 12)
        self.assertNotIn("kategoriDerece", json.dumps(saved))

    def test_a_stopped_price_is_saved_as_null_not_zero(self):
        rows = [{"tarih": "2026-09-16", "fiyat": 2.5}, {"tarih": "2026-09-17", "fiyat": 0}]
        self.tefas.respond("fonFiyatBilgiGetir", "TST", ok(rows))
        self.run_download(["TST"])
        self.assertEqual(load(self.out / "TST.json"), [("2026-09-16", "2.5"), ("2026-09-17", None)])

    def test_unknown_fund_is_reported_and_not_written(self):
        self.tefas.respond("fonFiyatBilgiGetir", "OLD", ok([]))
        self.tefas.respond("fonFiyatBilgiGetir", "TST", ok(ROWS))
        summary = self.run_download(["OLD", "TST"])
        self.assertEqual((summary.not_found, list(summary.saved)), (["OLD"], ["TST"]))
        self.assertEqual(sorted(p.name for p in self.out.iterdir()), ["TST.json"])

    def test_paces_requests_and_leaves_no_temporary_files(self):
        self.tefas.respond("fonFiyatBilgiGetir", "TST", ok(ROWS))
        self.run_download(["TST"], pause_seconds=2.0)
        self.assertEqual(self.sleeps, [2.0])
        self.assertEqual([p.name for p in self.out.iterdir()], ["TST.json"])

    def test_stops_when_tefas_keeps_failing(self):
        for code in ("AAA", "BBB", "CCC"):
            self.tefas.respond("fonFiyatBilgiGetir", code, (503, "text/html", b"busy"))
        summary = self.run_download(["AAA", "BBB", "CCC"])
        self.assertEqual(summary.failed, ["AAA"])
        self.assertIn("BBB", summary.stopped)
        self.assertEqual(summary.saved, {})
        self.assertEqual(list(self.out.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
