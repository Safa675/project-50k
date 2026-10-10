"""Synthetic historical evidence access, category filters and feedback isolation."""
from __future__ import annotations
from datetime import timedelta
from unittest.mock import patch
from fastapi.testclient import TestClient
from psycopg.errors import CheckViolation
from p50k.product.app import create_app
from p50k.product.auth import Principal,CSRF_COOKIE,digest_token
from p50k.product.ai_client import AIUnavailable
from p50k.product.chat_tools import load_context
from p50k.product.db import connect
from p50k.product.evidence_routes import evidence_detail
from p50k.product.queries import FundQueries
from tests.unit import test_product_watchlists as watchlist_tests
from uuid import uuid4


class EvidenceDetailTests(watchlist_tests.WatchlistDatabaseTests):
    # Reuse only the synthetic database fixture, not its inherited test cases.
    def test_focused_chat_uses_original_run_and_rejects_unavailable_or_other_fund_evidence(self):
        old=self._run(self.now-timedelta(minutes=2))
        self._run(self.now-timedelta(minutes=1))
        with self.assertRaises(CheckViolation):
            self._run(self.now, evidence_delay=timedelta(days=1))
        unavailable=self._run(self.now+timedelta(days=1))
        with connect(self.settings) as connection:
            before=connection.execute('SELECT count(*) FROM ai.packets').fetchone()[0]
        context=load_context(self.settings,self.code,old)
        self.assertEqual([item.evidence_id for item in context.packet.evidence],[old])
        for fund,focus in ((self.code,unavailable),(self.other_code,old)):
            with self.assertRaisesRegex(AIUnavailable,'EVIDENCE_UNAVAILABLE'):
                load_context(self.settings,fund,focus)
        with connect(self.settings) as connection:
            self.assertEqual(connection.execute('SELECT count(*) FROM ai.packets').fetchone()[0],before)

    def test_evidence_details_are_point_in_time_and_owner_feedback_is_private(self):
        old=self._run(self.now-timedelta(minutes=2))
        current=self._run(self.now-timedelta(minutes=1))
        future=self._run(self.now+timedelta(days=1))
        with connect(self.settings) as connection:
            reader=FundQueries(connection)
            data=evidence_detail(reader,old,self.owners[0],self.now)
            self.assertFalse(data['is_current'])
            self.assertEqual(data['signal'].value,'3')
            self.assertIsNone(evidence_detail(reader,future,self.owners[0],self.now))
            self.assertIsNone(evidence_detail(reader,current,self.owners[0],self.now-timedelta(minutes=2)))
            connection.execute('INSERT INTO b2b.evidence_feedback(user_id,evidence_id,helpful) VALUES(%s,%s,true)',(self.owners[0],current))
            self.assertTrue(evidence_detail(reader,current,self.owners[0],self.now)['helpful'])
            self.assertIsNone(evidence_detail(reader,current,self.owners[1],self.now)['helpful'])

    def test_category_filter_is_literal_and_does_not_widen_search(self):
        with connect(self.settings) as connection:
            code='CAT'+uuid4().hex[:9].upper()
            connection.execute("INSERT INTO ref.funds(fund_code,name,category,source_sha256) VALUES (%s,'Synthetic filtered fund','Synthetic target',%s)",(code,self.checksum))
            reader=FundQueries(connection)
            self.assertEqual(reader.funds(code,10,0,'Synthetic target').total,1)
            self.assertEqual(reader.funds(code,10,0,'Synthetic%').total,0)
            self.assertEqual(reader.funds(self.other_code,10,0,'Synthetic target').total,0)

    def test_feedback_requires_csrf_and_rejects_future_evidence(self):
        evidence=self._run(self.now-timedelta(seconds=1))
        future=self._run(self.now+timedelta(days=1))
        csrf='c'*43
        actor=Principal(self.owners[0],'synthetic@example.invalid','viewer','synthetic-session',digest_token(csrf))
        with patch('p50k.product.auth.AuthService.authenticate',return_value=actor),TestClient(create_app(self.settings,readiness=lambda _:True),base_url='http://127.0.0.1:3071') as client:
            client.cookies.set(CSRF_COOKIE,csrf)
            body={'evidence_id':evidence,'helpful':True}
            self.assertEqual(client.post('/evidence-feedback',json=body).status_code,403)
            headers={'Origin':'http://127.0.0.1:3071','X-CSRF-Token':csrf}
            self.assertEqual(client.post('/evidence-feedback',json=body,headers=headers).status_code,200)
            self.assertEqual(client.post('/evidence-feedback',json={'evidence_id':future,'helpful':True},headers=headers).status_code,404)
            self.assertEqual(client.post('/evidence-feedback',json={'evidence_id':evidence,'helpful':'yes'},headers=headers).status_code,422)


# The imported base supplies setup helpers. Suppress duplicated inherited cases.
for _name in tuple(name for name in watchlist_tests.WatchlistDatabaseTests.__dict__ if name.startswith('test_')):
    setattr(EvidenceDetailTests,_name,None)
