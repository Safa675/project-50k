"""A synthetic packet flows through proposal, queue, human override and rerun."""
from __future__ import annotations
from datetime import datetime,timezone
from hashlib import sha256
import os
from unittest import TestCase
from unittest.mock import patch
import unittest
from uuid import uuid4
from p50k.product.ai_client import AIConfig
from p50k.product.db import connect
from p50k.product.decisions import build_packet,evaluate,decision_rows,review
from p50k.product.settings import Settings
from p50k.product import detector_pipeline as pipeline

@unittest.skipUnless(os.environ.get('P50K_TEST_DATABASE')=='1','Requires isolated p50k_dev')
class DecisionFlowTests(TestCase):
    def test_immutable_mock_proposal_human_override_and_cache_survive_rerun(self):
        settings=Settings.from_env()
        self.assertEqual(settings.db_name,'p50k_dev')
        code='TST'+uuid4().hex[:9].upper()
        checksum=sha256(code.encode()).hexdigest()
        with connect(settings) as connection:
            connection.execute("INSERT INTO ref.funds(fund_code,name,category,source_sha256) VALUES (%s,'Synthetic review fund','Synthetic review category',%s)",(code,checksum))
            connection.execute("INSERT INTO obs.fund_prices(fund_code,effective_date,nav,source_sha256,origin,available_at,observed_at,availability_rule) VALUES (%s,'2030-01-30',100,%s,'SYNTHETIC','2030-01-30T12:00:00Z','2030-01-30T12:00:00Z','synthetic')",(code,checksum))
            actor=connection.execute("INSERT INTO auth.users(email,password_hash) VALUES (%s,'synthetic-hash') RETURNING user_id",(uuid4().hex+'@example.invalid',)).fetchone()[0]
        with patch.object(pipeline,'VERSION_ID','synthetic-decision-'+uuid4().hex),connect(settings) as connection:
            pipeline.run_detectors(connection,datetime(2030,2,6,12,tzinfo=timezone.utc),'SYNTHETIC')
        packet,_,_=build_packet(settings,code)
        self.assertNotIn('nav',packet.model_dump())
        first=evaluate(settings,code,AIConfig(mode='mock'))
        self.assertEqual(first['validation_state'],'VALID')
        changed=next(option for option in packet.allowed_options if option!='INSUFFICIENT_EVIDENCE')
        review_id=review(settings,first['decision_id'],str(actor),'OVERRIDE',changed,'Synthetic human reason')
        repeated=evaluate(settings,code,AIConfig(mode='mock'))
        self.assertTrue(repeated['cached'])
        effective=decision_rows(settings,code)[0]
        self.assertEqual(effective['effective_value'],changed)
        self.assertEqual(effective['review_id'],review_id)
        self.assertEqual(effective['decided_by'],'HUMAN')
        with self.assertRaises(ValueError):review(settings,first['decision_id'],str(actor),'OVERRIDE',changed,'')
        review(settings,first['decision_id'],str(actor),'REJECT',None,'Synthetic rejection')
        self.assertEqual(decision_rows(settings,code)[0]['effective_value'],'UNDECIDED')
