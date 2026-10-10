"""Synthetic AI integrity: schema, egress, numeric prose, reservations and leases."""
from __future__ import annotations
from dataclasses import replace
from datetime import datetime,timezone
from decimal import Decimal
import os
from unittest import TestCase
from unittest.mock import patch
import unittest
from uuid import uuid4
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from pydantic import ValidationError
from p50k.product.ai_client import AIUnavailable,reserve,settle,AIConfig,decide
from p50k.product.egress import Packet,Evidence,allowed_options
from p50k.product.validator import validate_output,validate_text,InvalidOutput,render
from p50k.product.settings import Settings
from p50k.product.db import connect
from p50k.product.queue import enqueue,claim,finish

def packet():
    item=Evidence(evidence_id='ev:synthetic',detector_id='D1',state='TRIGGERED',value='100',threshold='50',effective_date='2030-01-01',is_attribute=False)
    return Packet(fund_code='THF',fund_name='Synthetic fund',category='Synthetic category',as_of='2030-01-01',evidence=[item],allowed_options=allowed_options([item]))

class AIUnitTests(TestCase):
    def test_egress_rejects_raw_series_and_personal_fields(self):
        for field in ('prices','investors','total_value','kap_text','email'):
            with self.assertRaises(ValidationError):
                Packet.model_validate({**packet().model_dump(),field:'synthetic'})

    def test_unknown_and_age_only_cannot_justify_normal_or_material(self):
        item=Evidence(evidence_id='ev:age',detector_id='D5',state='NOT_TRIGGERED',value='100',threshold='730',effective_date='2030-01-01',is_attribute=True)
        self.assertEqual(allowed_options([item]),['INSUFFICIENT_EVIDENCE'])
        item=Evidence(evidence_id='ev:event',detector_id='AN-FND-005',state='TRIGGERED',value=None,threshold=None,effective_date='2030-01-01',is_attribute=False)
        self.assertEqual(allowed_options([item]),['MATERIAL','INSUFFICIENT_EVIDENCE'])

    def test_validator_accepts_article_and_server_placeholders(self):
        validate_text('Bu, ayrı bir inceleme gerektiriyor. {{ev:ev:synthetic}}',packet())
        self.assertIn('değer: 100; eşik: 50',render('{{ev:ev:synthetic}}',packet()))

    def test_turkish_corpus_rejects_numbers_intensity_allegations_advice_and_safety(self):
        for text in ('Yüzde kırk arttı.','İki kat yükseldi.','17 Eylül','MANİPÜLASYON','RISKSIZ','ÇOK ÜZERİNDE','SATIN AL','tasfiye edilebilir','teminat','Bir yıl sonra'):
            with self.subTest(text=text),self.assertRaises(InvalidOutput):
                validate_text(text,packet())

    def test_invalid_citation_and_disallowed_choice_never_validate(self):
        output={'decision':'MATERIAL','cited_evidence_ids':['ev:unknown'],'rationale_tr':'İnceleme gerekiyor.','missing_evidence_tr':''}
        with self.assertRaises(InvalidOutput):validate_output(output,packet())
        output['cited_evidence_ids']=['ev:synthetic']
        self.assertEqual(validate_output(output,packet()).decision,'MATERIAL')

    def test_mock_never_enters_real_database(self):
        with self.assertRaises(AIUnavailable):decide(Settings(),AIConfig(mode='mock'),packet())
        with self.assertRaises(AIUnavailable):decide(Settings(),AIConfig(mode='off'),packet())

    def test_live_boundary_reserves_first_disables_sdk_retries_and_response_storage(self):
        events=[]
        with TemporaryDirectory() as folder:
            path=Path(folder)/'synthetic-key'
            path.write_text('synthetic-api-credential',encoding='utf-8')
            with patch('p50k.product.ai_client.OpenAI') as factory,patch('p50k.product.ai_client.reserve',side_effect=lambda *_:events.append('reserved') or 'synthetic-reservation'),patch('p50k.product.ai_client.settle') as settled,patch('p50k.product.ai_client.connect'):
                client=factory.return_value
                response=SimpleNamespace(status='completed',id='synthetic-call',usage=SimpleNamespace(input_tokens=100,output_tokens=20),output_text='{}')
                client.responses.create.side_effect=lambda **kwargs:events.append('called') or response
                decide(Settings(),AIConfig(mode='live',key_file=path),packet())
                self.assertEqual(events,['reserved','called'])
                self.assertEqual(factory.call_args.kwargs['max_retries'],0)
                self.assertEqual(factory.call_args.kwargs['timeout'],60)
                request=client.responses.create.call_args.kwargs
                self.assertFalse(request['store'])
                self.assertEqual(request['max_output_tokens'],2000)
                self.assertTrue(request['text']['format']['strict'])
                self.assertEqual(request['text']['format']['schema']['properties']['decision']['enum'],packet().allowed_options)
                settled.assert_called_once()

@unittest.skipUnless(os.environ.get('P50K_TEST_DATABASE')=='1','Requires isolated p50k_dev')
class AIRuntimeDatabaseTests(TestCase):
    def setUp(self):
        self.settings=Settings.from_env()
        self.assertEqual(self.settings.db_name,'p50k_dev')
        self.bucket='synthetic-'+uuid4().hex
        with connect(self.settings) as connection:
            connection.execute('INSERT INTO ai.budget_buckets(bucket,cap_usd) VALUES (%s,1)',(self.bucket,))

    def test_reservation_is_atomic_capped_and_settled_once(self):
        reservation=reserve(self.settings,self.bucket,Decimal('.75'))
        with self.assertRaises(AIUnavailable):reserve(self.settings,self.bucket,Decimal('.30'))
        settle(self.settings,reservation,Decimal('.25'));settle(self.settings,reservation,Decimal('.25'))
        with connect(self.settings) as connection:
            self.assertEqual(connection.execute('SELECT spent_usd,reserved_usd FROM ai.budget_buckets WHERE bucket=%s',(self.bucket,)).fetchone(),(Decimal('.25'),Decimal('0')))

    def test_queue_deduplicates_and_wrong_owner_cannot_finish(self):
        digest=uuid4().hex*2
        first=enqueue(self.settings,'THF',digest)
        self.assertEqual(enqueue(self.settings,'THF',digest),first)
        job=claim(self.settings,'synthetic-owner')
        self.assertIsNotNone(job)
        self.assertFalse(finish(self.settings,str(job[0]),'wrong-owner'))
        self.assertTrue(finish(self.settings,str(job[0]),'synthetic-owner'))
