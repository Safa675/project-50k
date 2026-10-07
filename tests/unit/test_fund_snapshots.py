import json
import logging
import unittest
from datetime import datetime, timedelta, timezone

from p50k.jobs.fund_snapshots import DATED_RULE, connect, run
from p50k.providers.tefas import TefasClient

from tests.unit.test_tefas import SNAPSHOT_ROW, FakeTefas, ok

TODAY_PRICES = [{"tarih": "2026-10-05", "fiyat": 1.2}, {"tarih": "2026-10-06", "fiyat": 1.234567}]


class FakeClock:
    def __init__(self) -> None:
        self.now = datetime(2026, 10, 6, 19, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        self.now += timedelta(seconds=1)
        return self.now


class FundSnapshotCollectorTest(unittest.TestCase):
    def setUp(self):
        self.tefas = FakeTefas()
        self.db = connect(":memory:")
        self.addCleanup(self.db.close)
        self.sleeps = []
        self.clock = FakeClock()
        logger = logging.getLogger("p50k")
        handler = logging.NullHandler()
        logger.addHandler(handler)
        self.addCleanup(logger.removeHandler, handler)

    def collect(self, codes):
        return run(TefasClient(transport=self.tefas), self.db, codes,
                   pause_seconds=1.5, sleep=self.sleeps.append, now=self.clock)

    def rows(self):
        return self.db.execute(
            "SELECT fund, as_of, as_of_rule, price, units_outstanding, investors, "
            "units_x_price_vs_total_rel_diff FROM fund_snapshots ORDER BY retrieved_at").fetchall()

    def test_dates_a_snapshot_whose_price_matches_the_newest_dated_price(self):
        self.tefas.respond("fonBilgiGetir", "TST", ok([SNAPSHOT_ROW]))
        self.tefas.respond("fonFiyatBilgiGetir", "TST", ok(TODAY_PRICES))
        summary = self.collect(["TST"])
        self.assertEqual((summary.dated, summary.undated), (1, 0))
        self.assertEqual(self.rows(), [("TST", "2026-10-06", DATED_RULE, "1.234567", "2000000", None, 0.0)])
        self.assertEqual(self.sleeps, [1.5, 1.5])  # paced, no real sleeping in tests

    def test_leaves_the_date_unknown_when_prices_disagree(self):
        # Snapshot still shows yesterday's price while today's is already published.
        self.tefas.respond("fonBilgiGetir", "TST", ok([{**SNAPSHOT_ROW, "sonFiyat": 1.2}]))
        self.tefas.respond("fonFiyatBilgiGetir", "TST", ok(TODAY_PRICES))
        summary = self.collect(["TST"])
        self.assertEqual((summary.dated, summary.undated), (0, 1))
        [(fund, as_of, rule, *_)] = self.rows()
        self.assertIsNone(as_of)
        self.assertEqual(rule, "unknown:price_differs_from_newest_dated_price")

    def test_a_second_run_on_the_same_day_does_not_duplicate(self):
        self.tefas.respond("fonBilgiGetir", "TST", ok([SNAPSHOT_ROW]))
        self.tefas.respond("fonFiyatBilgiGetir", "TST", ok(TODAY_PRICES))
        self.collect(["TST"])
        summary = self.collect(["TST"])
        self.assertEqual((summary.dated, summary.already_stored), (0, 1))
        self.assertEqual(len(self.rows()), 1)

    def test_unknown_fund_is_recorded_and_the_run_continues(self):
        self.tefas.respond("fonBilgiGetir", "OLD", ok([]))
        self.tefas.respond("fonBilgiGetir", "TST", ok([SNAPSHOT_ROW]))
        self.tefas.respond("fonFiyatBilgiGetir", "TST", ok(TODAY_PRICES))
        summary = self.collect(["OLD", "TST"])
        self.assertEqual(summary.not_found, ["OLD"])
        self.assertEqual(summary.dated, 1)

    def test_retries_then_stops_when_tefas_keeps_failing(self):
        for code in ("AAA", "BBB", "CCC"):
            self.tefas.respond("fonBilgiGetir", code, (503, "text/html", b"busy"))
        summary = self.collect(["AAA", "BBB", "CCC"])
        self.assertEqual(summary.failed, ["AAA"])  # three attempts each
        self.assertIn("BBB", summary.stopped)  # circuit opened during BBB's attempts
        self.assertEqual([call[1] for call in self.tefas.calls], ["AAA"] * 3 + ["BBB"] * 2)
        self.assertEqual(self.rows(), [])

    def test_records_each_run(self):
        self.tefas.respond("fonBilgiGetir", "OLD", ok([]))
        self.collect(["OLD"])
        [(requested, dated, not_found, stopped)] = self.db.execute(
            "SELECT requested, dated, not_found, stopped FROM collector_runs").fetchall()
        self.assertEqual((requested, dated, json.loads(not_found), stopped), (1, 0, ["OLD"], None))


if __name__ == "__main__":
    unittest.main()
