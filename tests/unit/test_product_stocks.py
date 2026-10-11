"""Synthetic BIST30 import, auth, daily-close and point-in-time checks."""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from p50k.product.archive import sha256_file
from p50k.product.stock_import import import_stocks, seed_browser_stock, stock_decimal, verify_manifest
from p50k.product.stock_routes import get_stock_queries, require_session, router
from p50k.product.stocks import (
    StockChart, StockDetail, StockInstrument, StockListing, StockQueries, StocksPage,
)

CUTOFF=datetime(2020,1,10,12,tzinfo=timezone.utc)


def write_manifest(root: Path, *, symbol: str="TESTA", captured: datetime=CUTOFF,
                   close: str | None="100", include_missing: bool=True) -> Path:
    raw=root/"provider.json"
    raw.write_text(json.dumps({"synthetic":True,"close":close}),encoding="utf-8",newline="\n")
    raw_hash=sha256_file(raw)
    payload={"version":"bist-daily-v1","captured_at":captured.isoformat(),"universe":"XU030","source":"forinvest",
             "capture_kind":"SYNTHETIC_TEST","normalization_version":"synthetic-stock-test-v1",
             "provider_adjustment":"UNVERIFIED",
             "instruments":[{"symbol":symbol,"name":"Synthetic stock","exchange":"BIST","currency":"TRY"}],
             "prices":[{"symbol":symbol,"date":"2020-01-02","close":close,"raw_source_sha256":raw_hash}],
             "corporate_actions":[{"symbol":symbol,"date":"2020-01-03","kind":"PROVIDER_CORPORATE_ACTION","payload":{"synthetic":True},"raw_source_sha256":raw_hash}],
             "raw_sources":[{"path":"provider.json","sha256":raw_hash}]}
    if include_missing:
        payload["prices"].append({"symbol":symbol,"date":"2020-01-03","close":None,"raw_source_sha256":raw_hash})
    path=root/"manifest.json"
    path.write_text(json.dumps(payload),encoding="utf-8",newline="\n")
    Path(str(path)+".sha256").write_text(sha256_file(path),encoding="ascii",newline="\n")
    return path


def rewrite(path: Path, **changes):
    payload=json.loads(path.read_text(encoding="utf-8"))
    payload.update(changes)
    path.write_text(json.dumps(payload),encoding="utf-8",newline="\n")
    Path(str(path)+".sha256").write_text(sha256_file(path),encoding="ascii",newline="\n")


class StockAdmissionTests(unittest.TestCase):
    def setUp(self):
        temporary=TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)
        self.path=write_manifest(self.root)

    def test_verified_raw_and_manifest_bytes_and_aware_capture_are_required(self):
        manifest,checksum,captured=verify_manifest(self.path)
        self.assertEqual(manifest.prices[0].close,"100")
        self.assertEqual(checksum,sha256_file(self.path))
        self.assertEqual(captured,CUTOFF)
        (self.root/"provider.json").write_text("Synthetic changed source",encoding="utf-8")
        with self.assertRaises(ValueError):verify_manifest(self.path)

    def test_bad_or_missing_sidecar_and_tampered_manifest_fail_closed(self):
        sidecar=Path(str(self.path)+".sha256")
        sidecar.unlink()
        with self.assertRaises(ValueError):verify_manifest(self.path)
        sidecar.write_text("a"*64,encoding="ascii")
        with self.assertRaises(ValueError):verify_manifest(self.path)

    def test_universe_currency_duplicate_dates_future_capture_and_prices_reject(self):
        for changes in ({"universe":"ALL"},{"captured_at":"2020-01-10T12:00:00"},
                        {"captured_at":(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()},
                        {"instruments":[{"symbol":"TESTA","name":"Synthetic stock","exchange":"BIST","currency":"USD"}]},
                        {"prices":[{"symbol":"TESTA","date":"2020-01-11","close":"100"}]},
                        {"prices":[{"symbol":"TESTA","date":"2020-01-02","close":"100"}]*2},
                        {"prices":[{"symbol":"OUTSIDE","date":"2020-01-02","close":"100"}]}):
            with self.subTest(changes=changes):
                write_manifest(self.root)
                rewrite(self.path,**changes)
                with self.assertRaises(ValueError):verify_manifest(self.path)

    def test_decimal_zero_is_missing_and_nonfinite_negative_float_text_rejected(self):
        self.assertIsNone(stock_decimal("0"))
        self.assertEqual(stock_decimal("100.125000"),Decimal("100.125000"))
        self.assertIsNone(stock_decimal(None))
        for value in ("NaN","Infinity","-1","1,25","1e3",100.0):
            with self.subTest(value=value),self.assertRaises(ValueError):stock_decimal(value)

    def test_raw_path_escape_unverified_source_hash_and_unbounded_catalog_reject(self):
        for changes in ({"raw_sources":[{"path":"../outside.json","sha256":"a"*64}]},
                        {"prices":[{"symbol":"TESTA","date":"2020-01-02","close":"100","raw_source_sha256":"b"*64}]},
                        {"instruments":[{"symbol":"TEST"+str(i),"name":"Synthetic stock","exchange":"BIST","currency":"TRY"} for i in range(31)]}):
            with self.subTest(changes=changes):
                write_manifest(self.root)
                rewrite(self.path,**changes)
                with self.assertRaises(ValueError):verify_manifest(self.path)

    def test_synthetic_seed_and_manifest_cannot_write_real_database_origin(self):
        from p50k.product.settings import Settings
        with self.assertRaises(ValueError):seed_browser_stock(Settings())
        with self.assertRaises(ValueError):import_stocks(object(),self.path,origin="DELAYED")


class SyntheticStockQueries:
    def __init__(self):self.calls=[]
    def stocks(self,q,limit,offset,cutoff,*,dated=False):
        self.calls.append((q,limit,offset))
        return StocksPage(items=[StockListing(symbol="TESTA",name="Synthetic stock",last_date=date(2020,1,3),last_close=None)],total=1,limit=limit,offset=offset,catalog_captured_at=CUTOFF)
    def stock(self,symbol,cutoff=None):
        return StockInstrument(symbol=symbol,name="Synthetic stock") if symbol=="TESTA" else None
    def detail(self,stock,start,end,cutoff):
        self.calls.append((stock.symbol,start,end,cutoff))
        return StockDetail(stock=stock,chart=StockChart(start_date=start,end_date=end,cutoff=cutoff,points=[]),signals=[],price_adjustment="UNVERIFIED",cutoff=cutoff)


class StockRouteTests(unittest.TestCase):
    def setUp(self):
        self.reader=SyntheticStockQueries()
        self.app=FastAPI()
        self.app.include_router(router)
        self.app.dependency_overrides[get_stock_queries]=lambda:self.reader
        self.client=TestClient(self.app)
        self.addCleanup(self.client.close)

    def authenticate(self):self.app.dependency_overrides[require_session]=lambda:None

    def test_both_stock_routes_require_session_before_reading(self):
        for path in ("/stocks","/stocks/TESTA"):
            self.assertEqual(self.client.get(path).status_code,401)
        self.assertEqual(self.reader.calls,[])

    def test_catalog_shape_current_membership_and_bounds(self):
        self.authenticate()
        response=self.client.get("/stocks",params={"q":" Synthetic ","limit":5,"offset":2})
        self.assertEqual(response.status_code,200,response.text)
        result=response.json()
        self.assertEqual(result["universe"],"BIST30_CURRENT_CATALOG")
        self.assertEqual(result["items"][0]["exchange"],"BIST")
        self.assertIsNone(result["items"][0]["last_close"])
        self.assertEqual(self.reader.calls,[("Synthetic",5,2)])
        for params in ({"limit":31},{"limit":0},{"offset":31},{"offset":-1},{"q":"x"*81}):
            self.assertEqual(self.client.get("/stocks",params=params).status_code,422)

    def test_daily_chart_empty_states_cutoff_and_length_bounds(self):
        self.authenticate()
        response=self.client.get("/stocks/TESTA",params={"cutoff":CUTOFF.isoformat(),"days":5})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()["chart"]["cadence"],"DAILY_CLOSE")
        self.assertEqual(response.json()["signals"],[])
        self.assertEqual(self.reader.calls[0][1:3],(date(2020,1,6),date(2020,1,10)))
        for params in ({"days":732},{"days":0},{"cutoff":"2020-01-01T12:00:00"},{"cutoff":(datetime.now(timezone.utc)+timedelta(days=2)).isoformat()}):
            self.assertEqual(self.client.get("/stocks/TESTA",params=params).status_code,422)
        self.assertEqual(self.client.get("/stocks/MISSING").status_code,404)
        self.assertEqual(self.client.get("/stocks/invalid").status_code,422)


@unittest.skipUnless(os.environ.get("P50K_TEST_DATABASE")=="1","requires isolated PostgreSQL p50k_dev")
class StockDatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from p50k.product.db import connect
        from p50k.product.migrate import run_migrations
        from p50k.product.settings import Settings
        cls.settings=Settings.from_env()
        if cls.settings.db_name!="p50k_dev" or cls.settings.db_user!="p50k_owner":
            raise RuntimeError("Synthetic stock database tests require isolated owner p50k_dev")
        cls.app_settings=replace(cls.settings,db_user="p50k_app",db_password_file=Path(os.environ["P50K_APP_PASSWORD_FILE"]))
        with connect(cls.settings,autocommit=True) as connection:
            run_migrations(connection,app_password=cls.app_settings.database_password().get_secret_value())

    def setUp(self):
        from p50k.product.db import connect
        temporary=TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)
        self.code="T"+uuid4().hex[:9].upper()
        self.captured=datetime.now(timezone.utc)
        self.path=write_manifest(self.root,symbol=self.code,captured=self.captured)
        self.connection=connect(self.app_settings,autocommit=True)
        self.addCleanup(self.connection.close)
        self.reader=StockQueries(self.connection)

    def do_import(self):return import_stocks(self.connection,self.path,origin="SYNTHETIC")

    def test_capture_time_is_only_availability_and_repeated_import_is_idempotent(self):
        first,second=self.do_import(),self.do_import()
        self.assertEqual(first["inserted_prices"],2)
        self.assertEqual(first["inserted_actions"],1)
        self.assertEqual(first["missing_prices"],1)
        self.assertEqual(second["inserted_prices"],0)
        rows=self.connection.execute("SELECT close,available_at,observed_at,raw_source_sha256 FROM obs.stock_prices WHERE symbol=%s ORDER BY effective_date",(self.code,)).fetchall()
        self.assertEqual(rows[0][1],self.captured)
        self.assertEqual(rows[0][1],rows[0][2])
        stock=self.reader.stock(self.code)
        before=self.reader.detail(stock,date(2020,1,1),date.today(),self.captured-timedelta(seconds=1))
        after=self.reader.detail(stock,date(2020,1,1),date.today(),self.captured+timedelta(seconds=1))
        self.assertEqual(before.chart.points,[])
        self.assertEqual(before.corporate_actions,[])
        self.assertEqual([p.close for p in after.chart.points],["100",None])
        self.assertEqual(after.signals,[])
        self.assertEqual(after.corporate_actions_total,1)
        self.assertTrue(after.corporate_actions[0].payload["synthetic"])
        self.assertEqual(after.corporate_actions[0].available_at,self.captured)

    def test_tied_conflicting_revisions_are_null_in_chart_and_catalog(self):
        self.do_import()
        self.connection.execute("""INSERT INTO obs.stock_prices(symbol,effective_date,close,source_id,source_sha256,raw_source_sha256,origin,available_at,observed_at,availability_rule,price_adjustment)
            VALUES(%s,'2020-01-03',101,'forinvest',%s,%s,'SYNTHETIC',%s,%s,'synthetic','UNVERIFIED')""",(self.code,"b"*64,"c"*64,self.captured,self.captured))
        detail=self.reader.detail(self.reader.stock(self.code),date(2020,1,1),date.today(),datetime.now(timezone.utc))
        self.assertTrue(detail.chart.points[-1].ambiguous_revision)
        self.assertIsNone(detail.chart.points[-1].close)
        listing=self.reader.stocks(self.code,30,0,datetime.now(timezone.utc))
        self.assertIsNone(listing.items[0].last_close)

    def test_all_observations_are_immutable_even_to_owner(self):
        from p50k.product.db import connect
        self.do_import()
        for table in ("obs.stock_prices","obs.stock_actions"):
            with self.subTest(table=table),self.assertRaises(Exception),connect(self.settings) as connection:
                connection.execute("UPDATE "+table+" SET metadata='{}' WHERE symbol=%s",(self.code,))
        with self.assertRaises(Exception),connect(self.settings) as connection:
            connection.execute("DELETE FROM ref.stock_catalogs WHERE catalog_sha256=%s",(sha256_file(self.path),))

    def test_catalog_replacement_retains_old_history_without_expanding_membership(self):
        self.do_import()
        newer="T"+uuid4().hex[:9].upper()
        write_manifest(self.root,symbol=newer,captured=datetime.now(timezone.utc))
        self.do_import()
        page=self.reader.stocks("",30,0,datetime.now(timezone.utc))
        self.assertEqual([item.symbol for item in page.items],[newer])
        self.assertIsNone(self.reader.stock(self.code))
        self.assertEqual(self.connection.execute("SELECT count(*) FROM obs.stock_prices WHERE symbol=%s",(self.code,)).fetchone()[0],2)

    def test_older_capture_cannot_roll_current_catalog_back(self):
        self.do_import()
        write_manifest(self.root,symbol=self.code,captured=self.captured-timedelta(seconds=1),close="99")
        with self.assertRaises(ValueError):self.do_import()
        self.assertEqual(self.connection.execute("SELECT count(*) FROM obs.stock_prices WHERE symbol=%s",(self.code,)).fetchone()[0],2)


if __name__=="__main__":unittest.main()
