"""Official Borsa Istanbul daily bulletin admission (DEC-036), synthetic fixtures only."""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from email.utils import format_datetime
import hashlib
import io
import json
import os
from pathlib import Path
import random
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4
import zipfile

from p50k.product.stock_bulletin import (
    FALLBACK_RULE, RULE, SOURCE_ID, load_capture, main, read_bulletin, read_folder, summary,
)

HEADER = ["TRADE DATE", "INSTRUMENT SERIES CODE", "INSTRUMENT NAME", "INSTRUMENT GROUP", "BIST 30 INDEX", "SUSPENDED",
          "CORPORATE ACTION", "PREVIOUS LAST PRICE", "CLOSING PRICE", "CHANGE TO PREVIOUS CLOSING (%)", "VWAP",
          "TOTAL TRADED VALUE", "TOTAL TRADED VOLUME"]
TRADE = date(2020, 1, 2)


def symbols(prefix: str="ZQX", count: int=30) -> list[str]:
    return [f"{prefix}{index:02d}" for index in range(count)]


def write_bulletin(root: Path, trade: date=TRADE, members: list[str] | None=None, *, close: str="10.5",
                   row_date: date | None=None, inner: tuple[int, ...] | None=None,
                   published: datetime | None=None, captured: datetime | None=None) -> tuple[Path, dict]:
    """Write a tiny bulletin-like ZIP and its capture record; values are synthetic."""
    name = f"thb{trade:%Y%m%d}1"
    lines = [";".join(["SENTETIK"] * len(HEADER)), ";".join(HEADER)]
    for symbol in members if members is not None else symbols():
        lines.append(";".join([(row_date or trade).isoformat(), f"{symbol}.E", f"Synthetic {symbol}", "EQT", "1", "0", "",
                               "10", close, "-1.25", "10.2", "1000.5", "100"]))
    lines.append(";".join([trade.isoformat(), "OTHER.E", "Synthetic other", "EQT", "0", "0", "", "1", "1", "0", "1", "1", "1"]))
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(zipfile.ZipInfo(name + ".csv", date_time=inner or (trade.year, trade.month, trade.day, 18, 25, 28)),
                         "\n".join(lines) + "\n")
    path = root / (name + ".zip")
    path.write_bytes(buffer.getvalue())
    published = published or datetime(trade.year, trade.month, trade.day, 15, 28, 6, tzinfo=timezone.utc)
    capture = {"trade_date": trade.isoformat(), "url": f"https://borsaistanbul.com/data/thb/{trade:%Y}/{trade:%m}/{name}.zip",
               "file": path.name, "status": 200, "last_modified": format_datetime(published, usegmt=True),
               "etag": '"synthetic"', "captured_at": (captured or published + timedelta(days=3)).isoformat(),
               "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    return path, capture


class BulletinParsingTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def read(self, **options):
        path, capture = write_bulletin(self.root, **options)
        return read_bulletin(path, load_capture(capture))

    def test_thirty_flagged_members_with_last_modified_availability(self):
        bulletin = self.read()
        self.assertEqual(bulletin.trade_date, TRADE)
        self.assertEqual(len(bulletin.members), 30)
        self.assertNotIn("OTHER", [member.symbol for member in bulletin.members])
        member = bulletin.members[0]
        self.assertEqual((member.symbol, member.series, str(member.close)), ("ZQX00", "ZQX00.E", "10.5"))
        self.assertEqual((member.fields["previous_close"], member.fields["change_pct"], member.fields["volume"]), ("10", "-1.25", "100"))
        self.assertEqual(bulletin.available_at, datetime(2020, 1, 2, 15, 28, 6, tzinfo=timezone.utc))
        self.assertEqual(bulletin.availability_rule, RULE)
        self.assertTrue(bulletin.inner_consistent)

    def test_inconsistent_or_missing_publication_evidence_falls_back_to_capture_time(self):
        captured = datetime(2020, 1, 6, 9, tzinfo=timezone.utc)
        late_inner = self.read(inner=(2020, 1, 2, 19, 0, 0), captured=captured)
        self.assertEqual((late_inner.available_at, late_inner.availability_rule), (captured, FALLBACK_RULE))
        path, capture = write_bulletin(self.root, captured=captured)
        capture["last_modified"] = None
        self.assertEqual(read_bulletin(path, load_capture(capture)).available_at, captured)
        early = self.read(published=datetime(2020, 1, 1, 12, tzinfo=timezone.utc), captured=captured)
        self.assertEqual(early.availability_rule, FALLBACK_RULE)

    def test_trade_date_member_count_closes_and_bytes_fail_closed(self):
        for options in ({"row_date": date(2020, 1, 3)}, {"members": symbols(count=29)}, {"members": symbols()[:29] + ["ZQX00"]},
                        {"close": "abc"}, {"close": ""}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                self.read(**options)
        path, capture = write_bulletin(self.root)
        for change in ({"sha256": "0" * 64}, {"url": "https://example.com/data/thb/2020/01/thb202001021.zip"},
                       {"url": "https://borsaistanbul.com/data/thb/2020/02/thb202001021.zip"}, {"status": 404}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                read_bulletin(path, load_capture({**capture, **change}))
        with self.assertRaises(ValueError):
            load_capture({**capture, "captured_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()})

    def test_zero_close_is_missing_never_a_price(self):
        self.assertTrue(all(member.close is None for member in self.read(close="0").members))

    def test_folder_manifest_reads_each_day_and_reports_gaps(self):
        entries = [write_bulletin(self.root, trade)[1] for trade in (date(2020, 1, 2), date(2020, 1, 3))]
        entries.insert(0, {"trade_date": "2020-01-01", "url": "https://borsaistanbul.com/data/thb/2020/01/thb202001011.zip",
                           "status": 404, "skipped": "not_published"})
        (self.root / "manifest.json").write_text(json.dumps({"source": SOURCE_ID, "entries": entries}), encoding="utf-8")
        bulletins, gaps = read_folder(self.root)
        self.assertEqual([item.trade_date for item in bulletins], [date(2020, 1, 2), date(2020, 1, 3)])
        self.assertEqual(gaps, [{"trade_date": "2020-01-01", "reason": "not_published"}])
        self.assertEqual(summary(bulletins)["rows"], 60)
        entries[1]["file"] = "../thb202001021.zip"
        (self.root / "manifest.json").write_text(json.dumps({"entries": entries}), encoding="utf-8")
        with self.assertRaises(ValueError):
            read_folder(self.root)

    def test_cli_dry_run_reports_without_database(self):
        path, capture = write_bulletin(self.root)
        record = self.root / "capture.json"
        record.write_text(json.dumps(capture), encoding="utf-8")
        output = io.StringIO()
        from contextlib import redirect_stdout
        with redirect_stdout(output):
            self.assertEqual(main(["import", "--zip", str(path), "--capture-json", str(record), "--dry-run"]), 0)
        result = json.loads(output.getvalue())
        self.assertEqual((result["bulletins"], result["rows"], result["dry_run"]), (1, 30, True))
        self.assertEqual(main(["import", "--zip", str(path), "--dry-run"]), 1)


@unittest.skipUnless(os.environ.get("P50K_TEST_DATABASE") == "1", "requires isolated PostgreSQL p50k_dev")
class BulletinDatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from p50k.product.db import connect
        from p50k.product.migrate import run_migrations
        from p50k.product.settings import Settings
        cls.settings = Settings.from_env()
        if cls.settings.db_name != "p50k_dev" or cls.settings.db_user != "p50k_owner":
            raise RuntimeError("Synthetic bulletin database tests require isolated owner p50k_dev")
        cls.app_settings = replace(cls.settings, db_user="p50k_app", db_password_file=Path(os.environ["P50K_APP_PASSWORD_FILE"]))
        with connect(cls.settings, autocommit=True) as connection:
            run_migrations(connection, app_password=cls.app_settings.database_password().get_secret_value())

    def setUp(self):
        from p50k.product.db import connect
        from p50k.product.stocks import StockQueries
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.trade = date(2001, 1, 1) + timedelta(days=random.randrange(0, 6000))
        self.members = symbols("Z" + uuid4().hex[:6].upper())
        path, capture = write_bulletin(self.root, self.trade, self.members,
                                       published=datetime(self.trade.year, self.trade.month, self.trade.day, 15, 28,
                                                          random.randrange(60), tzinfo=timezone.utc))
        self.bulletin = read_bulletin(path, load_capture(capture))
        self.connection = connect(self.app_settings, autocommit=True)
        self.addCleanup(self.connection.close)
        self.reader = StockQueries(self.connection)

    def do_import(self):
        from p50k.product.stock_bulletin import import_bulletins
        return import_bulletins(self.connection, [self.bulletin], origin="SYNTHETIC")

    def test_import_is_idempotent_and_keeps_publication_evidence(self):
        first, second = self.do_import(), self.do_import()
        self.assertEqual((first["inserted_prices"], first["inserted_instruments"]), (30, 30))
        self.assertEqual((second["inserted_prices"], second["inserted_instruments"]), (0, 0))
        row = self.connection.execute("""SELECT available_at,origin,price_adjustment,availability_rule,source_sha256,metadata
            FROM obs.stock_prices WHERE symbol=%s AND source_id=%s""", (self.members[0], SOURCE_ID)).fetchone()
        self.assertEqual(row[:5], (self.bulletin.available_at, "SYNTHETIC", "UNADJUSTED", RULE, self.bulletin.zip_sha256))
        self.assertEqual((row[5]["source_version"], row[5]["volume"]), ("thb-v1", "100"))
        instrument = self.connection.execute("SELECT source_id,metadata FROM ref.stock_instruments WHERE symbol=%s", (self.members[0],)).fetchone()
        self.assertEqual(instrument[0], SOURCE_ID)
        self.assertTrue(instrument[1]["dated_bulletin_member"])

    def test_dated_membership_appears_only_once_the_bulletin_is_available(self):
        self.do_import()
        available = self.bulletin.available_at
        before = self.reader.stocks("", 30, 0, available - timedelta(seconds=1), dated=True)
        self.assertNotEqual(before.membership_source_sha256, self.bulletin.zip_sha256)
        self.assertIsNone(self.reader.stock(self.members[0], available - timedelta(seconds=1)))
        after = self.reader.stocks("", 30, 0, available + timedelta(minutes=1), dated=True)
        self.assertEqual((after.universe, after.membership_date, after.total), ("BIST30_DATED_BULLETIN", self.trade, 30))
        self.assertEqual(after.membership_source_sha256, self.bulletin.zip_sha256)
        self.assertFalse(after.metadata_current_only)
        item = after.items[0]
        self.assertEqual((item.symbol, item.last_close, item.change_pct, item.volume, item.source_id),
                         (self.members[0], "10.5", "-1.25", "100", SOURCE_ID))
        searched = self.reader.stocks(self.members[3], 30, 0, available + timedelta(minutes=1), dated=True)
        self.assertEqual([entry.symbol for entry in searched.items], [self.members[3]])
        live = self.reader.stocks("", 30, 0, available + timedelta(minutes=1), dated=False)
        self.assertEqual(live.universe, "BIST30_CURRENT_CATALOG")
        self.assertNotIn(self.members[0], [entry.symbol for entry in live.items])

    def test_official_close_is_preferred_and_each_point_names_its_source(self):
        self.do_import()
        symbol, later = self.members[1], self.bulletin.available_at + timedelta(days=1)
        checksum = hashlib.sha256(symbol.encode()).hexdigest()
        self.connection.execute("""INSERT INTO obs.stock_prices(symbol,effective_date,close,source_id,source_sha256,raw_source_sha256,
            origin,available_at,observed_at,availability_rule,price_adjustment) VALUES(%s,%s,99,'forinvest',%s,%s,'SYNTHETIC',%s,%s,
            'synthetic_capture','UNVERIFIED'),(%s,%s,98,'forinvest',%s,%s,'SYNTHETIC',%s,%s,'synthetic_capture','UNVERIFIED')""",
            (symbol, self.trade, checksum, checksum, later, later, symbol, self.trade + timedelta(days=1), checksum, checksum, later, later))
        stock = self.reader.stock(symbol, later)
        detail = self.reader.detail(stock, self.trade - timedelta(days=5), self.trade + timedelta(days=1), later)
        self.assertEqual([(point.effective_date, point.close, point.source_id) for point in detail.chart.points],
                         [(self.trade, "10.5", SOURCE_ID), (self.trade + timedelta(days=1), "98", "forinvest")])
        self.assertEqual(detail.chart.points[0].change_pct, "-1.25")
        self.assertIsNone(detail.chart.points[1].change_pct)
        self.assertEqual(detail.price_adjustment, "MIXED")
        self.assertEqual(detail.dated_member_on, self.trade)
        early = self.reader.detail(stock, self.trade - timedelta(days=5), self.trade, self.bulletin.available_at - timedelta(seconds=1))
        self.assertEqual(early.chart.points, [])


if __name__ == "__main__":
    unittest.main()
