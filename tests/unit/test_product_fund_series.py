"""Synthetic KAP period values: source timing, parsing and revision integrity."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import os
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb

from p50k.product.analysis_context import use_analysis_date
from p50k.product.db import connect
from p50k.product.fund_series_routes import FundSeriesPage, SeriesCoverage, period_end, router, series_page
from p50k.product.queries import FundQueries
from p50k.product.routes import get_queries, require_session
from p50k.product.settings import Settings

CUTOFF = datetime(2026, 9, 12, 20, 59, 59, tzinfo=timezone.utc)


class FundSeriesRouteTests(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(router)
        self.reader = type('SyntheticReader', (), {'fund': lambda _, code: object() if code == 'ZZZ' else None})()
        self.app.dependency_overrides[get_queries] = lambda: self.reader
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)

    def test_authentication_is_required_and_bounds_are_server_validated(self):
        self.assertEqual(self.client.get('/funds/ZZZ/series').status_code, 401)
        self.app.dependency_overrides[require_session] = lambda: None
        self.assertEqual(self.client.get('/funds/YYY/series').status_code, 404)
        self.assertEqual(self.client.get('/funds/invalid/series').status_code, 422)
        for params in ({'limit':61}, {'limit':0}, {'offset':501}, {'offset':-1},
                       {'cutoff':'2026-09-12T12:00:00'},
                       {'cutoff':(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()}):
            with self.subTest(params=params):
                self.assertEqual(self.client.get('/funds/ZZZ/series',params=params).status_code,422)

    def test_default_cutoff_uses_selected_analysis_date_and_explicit_cutoff_is_preserved(self):
        self.app.dependency_overrides[require_session] = lambda: None
        def response(reader,code,cutoff,limit,offset,*,historical):
            return FundSeriesPage(fund_code=code,items=[],total=0,limit=limit,offset=offset,
                cutoff=cutoff,mode='HISTORICAL_REPLAY' if historical else 'DELAYED',status='SOURCE_MISSING',
                coverage=SeriesCoverage(published_documents=0,local_documents=0,parsed_periods=0,
                    parser_missing_periods=0,ambiguous_periods=0,known_unpublished_documents=0,unknown_publication_documents=0))
        with patch('p50k.product.fund_series_routes.series_page',side_effect=response), use_analysis_date('2026-09-12'):
            result=self.client.get('/funds/ZZZ/series')
            self.assertEqual(result.status_code,200,result.text)
            self.assertEqual(result.json()['cutoff'],'2026-09-12T20:59:59.999999Z')
            self.assertEqual(result.json()['mode'],'HISTORICAL_REPLAY')
            earlier=self.client.get('/funds/ZZZ/series',params={'cutoff':'2026-08-15T12:00:00Z'})
            self.assertEqual(earlier.json()['cutoff'],'2026-08-15T12:00:00Z')

    def test_weekly_valuation_day_and_currency_are_not_invented(self):
        self.assertEqual(period_end('2024-02','monthly').isoformat(),'2024-02-29')
        self.assertIsNone(period_end('2026-W36','weekly'))


@unittest.skipUnless(os.environ.get('P50K_TEST_DATABASE')=='1','Requires isolated PostgreSQL p50k_dev')
class FundSeriesDatabaseTests(unittest.TestCase):
    def setUp(self):
        settings=Settings.from_env()
        self.assertEqual(settings.db_name,'p50k_dev')
        self.connection=connect(settings)
        self.addCleanup(self.connection.close)
        self.reader=FundQueries(self.connection)
        self.code='TST'+uuid4().hex[:9].upper()
        self.connection.execute("INSERT INTO ref.funds(fund_code,name,category,source_sha256) VALUES(%s,'Synthetic period fund','Synthetic category',%s)",(self.code,'a'*64))

    def add(self, period='2026-08', *, total='1000000.2500', units='10000.1250',
            published=CUTOFF-timedelta(days=2), available=CUTOFF-timedelta(days=2),
            observed=None, cadence='monthly', disclosure=12345):
        key=uuid4().hex
        report={'total_value':total,'units_outstanding':units,'disclosure_index':disclosure,
                'cash_in':'9000000','company_title':'Synthetic company','problems':[]}
        self.connection.execute('''INSERT INTO obs.kap_series(fund_code,series_key,report_period,cadence,
            source_sha256,origin,published_at,available_at,observed_at,availability_rule,metadata)
            VALUES(%s,%s,%s,%s,%s,'SYNTHETIC',%s,%s,%s,'synthetic-period',%s)''',
            (self.code,key,period,cadence,sha256(key.encode()).hexdigest(),published,available,observed,Jsonb({'report':report,'source_path':'private-synthetic-input'})))

    def document(self, *, published, available, observed, local=False):
        key=uuid4().hex
        self.connection.execute('''INSERT INTO obs.kap_documents(document_key,fund_code,report_period,
            relative_path,source_sha256,origin,published_at,available_at,observed_at,availability_rule)
            VALUES(%s,%s,'2026-08',%s,%s,'SYNTHETIC',%s,%s,%s,'synthetic-period')''',
            (key,self.code,'synthetic.pdf' if local else None,sha256(key.encode()).hexdigest(),published,available,observed))

    def page(self,cutoff=CUTOFF):
        return series_page(self.reader,self.code,cutoff)

    def test_publication_cutoff_preserves_exact_values_and_does_not_leak_later_reports(self):
        self.add()
        before=self.page()
        self.add('2026-07',total='999999999',published=CUTOFF+timedelta(days=1),available=CUTOFF+timedelta(days=1))
        self.add('2026-06',total='7777777',published=CUTOFF-timedelta(days=1),available=CUTOFF+timedelta(days=1))
        self.document(published=CUTOFF+timedelta(days=1),available=CUTOFF+timedelta(days=1),observed=CUTOFF+timedelta(days=1))
        self.assertEqual(self.page(),before)
        item,=before.items
        self.assertEqual((item.total_value,item.units_outstanding),('1000000.2500','10000.1250'))
        self.assertEqual(item.period_end.isoformat(),'2026-08-31')
        self.assertEqual(item.source_url,'https://www.kap.org.tr/tr/Bildirim/12345')
        self.assertIsNone(item.total_value_currency)
        payload=before.model_dump_json()
        self.assertNotIn('private-synthetic-input',payload)
        self.assertNotIn('cash_in',payload)
        self.assertNotIn('company_title',payload)
        self.assertFalse(before.interpolated)

    def test_parser_missing_values_stay_missing_but_reported_zero_is_retained(self):
        self.add(total='0',units='0')
        self.add('2026-07',total='not-a-number',units=None)
        result=self.page()
        self.assertEqual(result.status,'PARTIAL')
        rows={item.report_period:item for item in result.items}
        self.assertEqual((rows['2026-08'].total_value,rows['2026-08'].units_outstanding),('0','0'))
        self.assertEqual(rows['2026-07'].status,'PARSER_MISSING')
        self.assertEqual(rows['2026-07'].missing_fields,['total_value','units_outstanding'])

    def test_future_revisions_do_not_change_history_and_tied_conflicts_hide_values(self):
        self.add()
        before=self.page()
        self.add(total='2000000',available=CUTOFF+timedelta(days=1),published=CUTOFF+timedelta(days=1))
        self.assertEqual(self.page(),before)
        later=self.page(CUTOFF+timedelta(days=2))
        self.assertEqual(later.items[0].total_value,'2000000')
        self.add(total='3000000')
        conflicted=self.page()
        self.assertEqual(conflicted.items[0].status,'AMBIGUOUS_REVISION')
        self.assertIsNone(conflicted.items[0].total_value)
        self.assertIsNone(conflicted.items[0].units_outstanding)

    def test_source_missing_parser_missing_and_known_unpublished_have_distinct_states(self):
        self.assertEqual(self.page().status,'SOURCE_MISSING')
        self.document(published=CUTOFF+timedelta(days=1),available=CUTOFF+timedelta(days=1),observed=CUTOFF-timedelta(days=1))
        scheduled=self.page()
        self.assertEqual(scheduled.status,'REPORT_NOT_YET_PUBLISHED')
        self.assertEqual(scheduled.items,[])
        self.document(published=CUTOFF-timedelta(days=1),available=CUTOFF-timedelta(days=1),observed=CUTOFF-timedelta(days=1),local=True)
        self.assertEqual(self.page().status,'PARSER_MISSING')

    def test_unknown_publication_and_unfinished_month_cannot_supply_period_values(self):
        self.add(published=None,available=CUTOFF-timedelta(days=1))
        self.add('2026-09',published=CUTOFF-timedelta(days=1),available=CUTOFF-timedelta(days=1))
        result=self.page()
        self.assertEqual(result.items,[])
        self.assertEqual(result.status,'PUBLICATION_TIME_UNKNOWN')

    def test_weekly_reports_remain_separate_without_a_fabricated_period_end(self):
        self.add()
        self.add('2026-W36',cadence='weekly')
        result=self.page()
        self.assertEqual(result.total,2)
        weekly=next(item for item in result.items if item.cadence=='weekly')
        self.assertIsNone(weekly.period_end)
        self.assertEqual(weekly.report_period,'2026-W36')
        self.assertEqual(series_page(self.reader,self.code,CUTOFF,1,1).total,2)
        self.assertEqual(len(series_page(self.reader,self.code,CUTOFF,1,1).items),1)
