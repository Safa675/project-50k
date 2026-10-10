"""A synthetic packet flows through proposal, queue, human override and rerun."""
from __future__ import annotations
from datetime import datetime,timedelta,timezone
from hashlib import sha256
import os
from unittest import TestCase
from unittest.mock import patch
import unittest
from uuid import uuid4
from psycopg.errors import CheckViolation
from p50k.product.ai_client import AIConfig,AIUnavailable
from p50k.product.archive import ISTANBUL
from p50k.product.db import connect
from p50k.product.decisions import build_packet,evaluate,decision_rows,review
from p50k.product.settings import Settings
from p50k.product import detector_pipeline as pipeline
from p50k.product import decisions as decision_module
from p50k.product.queue import enqueue
from p50k.product.ai_worker import step

@unittest.skipUnless(os.environ.get('P50K_TEST_DATABASE')=='1','Requires isolated p50k_dev')
class DecisionFlowTests(TestCase):
    def test_immutable_mock_proposal_human_override_and_cache_survive_rerun(self):
        settings=Settings.from_env()
        self.assertEqual(settings.db_name,'p50k_dev')
        code='TST'+uuid4().hex[:9].upper()
        checksum=sha256(code.encode()).hexdigest()
        cutoff=datetime.now(timezone.utc)
        observed=cutoff-timedelta(days=8)
        with connect(settings) as connection:
            connection.execute("INSERT INTO ref.funds(fund_code,name,category,source_sha256) VALUES (%s,'Synthetic review fund','Synthetic review category',%s)",(code,checksum))
            connection.execute("INSERT INTO obs.fund_prices(fund_code,effective_date,nav,source_sha256,origin,available_at,observed_at,availability_rule) VALUES (%s,%s,100,%s,'SYNTHETIC',%s,%s,'synthetic')",(code,observed.date(),checksum,observed,observed))
            actor=connection.execute("INSERT INTO auth.users(email,password_hash) VALUES (%s,'synthetic-hash') RETURNING user_id",(uuid4().hex+'@example.invalid',)).fetchone()[0]
        with patch.object(pipeline,'VERSION_ID','synthetic-decision-'+uuid4().hex),connect(settings) as connection:
            pipeline.run_detectors(connection,cutoff,'SYNTHETIC')
        packet,packet_id,packet_hash=build_packet(settings,code)
        self.assertNotIn('nav',packet.model_dump())
        with patch.dict(os.environ,{'P50K_AI_MODE':'mock'}):
            job=enqueue(settings,code,packet_hash)
            self.assertTrue(step(settings,'synthetic-flow-worker'))
        with connect(settings) as connection:
            self.assertEqual(connection.execute('SELECT status FROM ops.jobs WHERE job_id=%s',(job,)).fetchone()[0],'SUCCEEDED')
            decision_id,validation=connection.execute('SELECT decision_id,validation_state FROM ai.decisions WHERE packet_id=%s ORDER BY decision_id DESC LIMIT 1',(packet_id,)).fetchone()
        first={'decision_id':decision_id,'validation_state':validation}
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
        bad={'decision':'MATERIAL','cited_evidence_ids':[packet.evidence[0].evidence_id],
             'rationale_tr':'İki katına çıktı.','missing_evidence_tr':''}
        with patch.object(decision_module,'PROMPT_VERSION','synthetic-invalid-v2'),patch.object(decision_module,'decide',return_value=(bad,'synthetic-bad-call','synthetic')) as model:
            failed=evaluate(settings,code,AIConfig(mode='mock'))
            self.assertEqual(failed['validation_state'],'INVALID')
            blocked=evaluate(settings,code,AIConfig(mode='mock'))
            self.assertTrue(blocked['blocked'])
            self.assertFalse(blocked['cached'])
            self.assertEqual(model.call_count,2)
        self.assertEqual(decision_rows(settings,code)[0]['decided_by'],'HUMAN')
        with patch.object(decision_module,'PROMPT_VERSION','synthetic-failure-v3'),patch.object(decision_module,'decide',side_effect=AIUnavailable('MODEL_CALL_FAILED','synthetic-failure')):
            failed=evaluate(settings,code,AIConfig(mode='mock'))
            self.assertEqual(failed['validation_state'],'INVALID')
            with connect(settings) as connection:
                original=connection.execute('SELECT rationale,call_id,decision_value FROM ai.decisions WHERE decision_id=%s',(failed['decision_id'],)).fetchone()
                self.assertEqual(original,(None,'synthetic-failure',None))
            review(settings,failed['decision_id'],str(actor),'OVERRIDE',changed,'Synthetic failure review')
        self.assertEqual(decision_rows(settings,code)[0]['effective_value'],changed)

    def test_packet_excludes_future_runs_and_unavailable_or_future_dated_evidence(self):
        settings=Settings.from_env()
        self.assertEqual(settings.db_name,'p50k_dev')
        code='TST'+uuid4().hex[:9].upper()
        checksum=sha256(code.encode()).hexdigest()
        now=datetime.now(timezone.utc)
        cutoff=now
        as_of=cutoff.date()-timedelta(days=1)
        version='synthetic-packet-cutoff-'+uuid4().hex
        with connect(settings) as connection:
            connection.execute("INSERT INTO ref.funds(fund_code,name,category,source_sha256) VALUES (%s,'Synthetic cutoff fund','Synthetic category',%s)",(code,checksum))
            connection.execute("INSERT INTO det.detector_versions(version_id,protocol_version,protocol_sha256,code_sha256,thresholds,calibration_input_sha256,calibration_cutoff) VALUES (%s,'synthetic',%s,%s,'{}',%s,%s)",(version,checksum,checksum,checksum,cutoff-timedelta(days=1)))
            for run_cutoff in (cutoff,now+timedelta(days=1)):
                run_id=connection.execute("INSERT INTO det.detector_runs(protocol_version,protocol_sha256,origin,cutoff,parameters) VALUES ('synthetic',%s,'SYNTHETIC',%s,'{}') RETURNING run_id",(checksum,run_cutoff)).fetchone()[0]
                cases=[('D1','TRIGGERED',cutoff,as_of),
                       ('D2','TRIGGERED',cutoff+timedelta(days=1),as_of),
                       ('D3','NOT_TRIGGERED',None,as_of),
                       ('D4','ABSTAINED',None,None),
                       ('AN-DQ-001','TRIGGERED',cutoff,cutoff.date()),
                       ('AN-DQ-002','TRIGGERED',None,as_of),
                       ('D5','TRIGGERED',cutoff,cutoff.date()+timedelta(days=2))]
                for detector,state,available,effective in cases:
                    evidence_id='ev:synthetic-'+uuid4().hex
                    statement="INSERT INTO det.evidence_items(evidence_id,fund_code,run_id,detector_id,origin,effective_date,available_at,unit,values,thresholds,triggered,state,source_references) VALUES (%s,%s,%s,%s,'SYNTHETIC',%s,%s,'ratio','{}','{}',%s,%s,'[]')"
                    args=(evidence_id,code,run_id,detector,effective,available,None if state=='ABSTAINED' else state=='TRIGGERED',state)
                    rejected=(available is not None and available>run_cutoff) or (effective is not None and effective>run_cutoff.astimezone(ISTANBUL).date()) or (state=='TRIGGERED' and available is None)
                    if rejected:
                        with self.assertRaises(CheckViolation),connection.transaction():
                            connection.execute(statement,args)
                        continue
                    connection.execute(statement,args)
                    connection.execute("INSERT INTO det.signals(run_id,fund_code,detector_id,state,reason,value,threshold,evidence_id,as_of) VALUES (%s,%s,%s,%s,'SYNTHETIC',%s,%s,%s,%s)",
                        (run_id,code,detector,state,None if state=='ABSTAINED' else 100,None if state=='ABSTAINED' else 50,evidence_id,as_of))
                connection.execute("INSERT INTO det.run_inputs(run_id,version_id,input_sha256,input_watermark,as_of,origin,cutoff) VALUES (%s,%s,%s,%s,%s,'SYNTHETIC',%s)",(run_id,version,checksum,cutoff,as_of,run_cutoff))
        packet,packet_id,_=build_packet(settings,code)
        self.assertEqual([item.detector_id for item in packet.evidence],['D1','D4'])
        with connect(settings) as connection:
            stored=connection.execute('SELECT payload FROM ai.packets WHERE packet_id=%s',(packet_id,)).fetchone()[0]
        self.assertEqual(stored['cutoff'],cutoff.isoformat())
