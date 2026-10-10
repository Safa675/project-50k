"""Synthetic AI integrity: schema, egress, numeric prose, reservations and leases."""
from __future__ import annotations
from dataclasses import replace
from datetime import datetime,timezone
from decimal import Decimal
import os
import json
from unittest import TestCase
from unittest.mock import patch
import unittest
from uuid import uuid4
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
from pydantic import ValidationError
from p50k.product.ai_client import AIUnavailable,reserve,settle,AIConfig,decide,materiality_input,resolve_materiality_output,MATERIALITY_PROMPT_VERSION
from p50k.product.decisions import PROMPT_VERSION,render_proposal,validate_proposal_output
from p50k.product.egress import Packet,Evidence,allowed_options
from p50k.product.validator import validate_output,validate_text,InvalidOutput,render
from p50k.product.settings import Settings
from p50k.product.db import connect
from p50k.product.queue import enqueue,claim,finish

def packet():
    item=Evidence(evidence_id='ev:synthetic',detector_id='D1',state='TRIGGERED',value='100',threshold='50',effective_date='2030-01-01',is_attribute=False)
    return Packet(fund_code='THF',fund_name='Synthetic fund',category='Synthetic category',as_of='2030-01-01',evidence=[item],allowed_options=allowed_options([item]))

class AIUnitTests(TestCase):
    def test_semantic_context_is_derived_only_and_does_not_change_the_packet(self):
        original=packet()
        before=original.model_dump_json()
        payload=json.loads(materiality_input(original))
        self.assertEqual(set(payload),{'evidence_packet','evidence_explanations'})
        projected=original.model_dump()
        projected['evidence'][0]['evidence_id']='e1'
        self.assertEqual(payload['evidence_packet'],projected)
        self.assertNotIn(original.evidence[0].evidence_id,materiality_input(original))
        explanation,=payload['evidence_explanations']
        self.assertEqual(explanation['evidence_id'],'e1')
        self.assertEqual(set(explanation),{'evidence_id','name_tr','measures_tr','observed_fact_tr','limits_tr'})
        self.assertIn('ortanca',explanation['measures_tr'])
        self.assertIn('inceleme',explanation['observed_fact_tr'])
        self.assertEqual(original.model_dump_json(),before)
        self.assertEqual(PROMPT_VERSION,MATERIALITY_PROMPT_VERSION)
        self.assertNotEqual(PROMPT_VERSION,'materiality-v1')

    def test_proposal_aliases_resolve_to_canonical_ids_before_validation_and_storage(self):
        original=packet()
        before=original.model_dump_json()
        raw={'decision':'MATERIAL','cited_evidence_ids':['e1'],
             'rationale_tr':'{{ev:e1}} Değişimin nedeni bu kayıttan belirlenemez.',
             'missing_evidence_tr':'{{ev:e1}}'}
        resolved=resolve_materiality_output(raw,original)
        validated=validate_output(resolved,original)
        self.assertEqual(validated.cited_evidence_ids,['ev:synthetic'])
        self.assertIn('{{ev:ev:synthetic}}',validated.rationale_tr)
        self.assertEqual(validated.missing_evidence_tr,'{{ev:ev:synthetic}}')
        self.assertEqual(raw['cited_evidence_ids'],['e1'])
        self.assertEqual(original.model_dump_json(),before)

    def test_alias_projection_does_not_accept_unknown_references_or_model_numbers(self):
        base={'decision':'MATERIAL','cited_evidence_ids':['e1'],
              'rationale_tr':'{{ev:e1}}','missing_evidence_tr':''}
        for changes in ({'cited_evidence_ids':['e9']},{'rationale_tr':'{{ev:e9}}'},
                        {'rationale_tr':'15 gün geçmiş. {{ev:e1}}'}):
            with self.subTest(changes=changes),self.assertRaises(InvalidOutput):
                validate_output(resolve_materiality_output({**base,**changes},packet()),packet())

    def test_new_plain_proposals_require_qualitative_prose_and_preserve_v2_rules(self):
        raw={'decision':'MATERIAL','cited_evidence_ids':['ev:synthetic'],
             'rationale_tr':'Benzer fonlara göre getiri farkı inceleme gerektiriyor. Nedeni bu kayıttan belirlenemez.',
             'missing_evidence_tr':''}
        self.assertEqual(validate_proposal_output(raw,packet(),MATERIALITY_PROMPT_VERSION).decision,'MATERIAL')
        for field in ('rationale_tr','missing_evidence_tr'):
            with self.subTest(field=field):
                templated={**raw,field:'{{ev:ev:synthetic}}'}
                with self.assertRaises(InvalidOutput):
                    validate_proposal_output(templated,packet(),MATERIALITY_PROMPT_VERSION)
                self.assertEqual(validate_proposal_output(templated,packet(),'materiality-v2-plain-language').decision,'MATERIAL')
        with self.assertRaises(InvalidOutput):
            validate_proposal_output({**raw,'rationale_tr':'Yüzde elli arttı.'},packet(),MATERIALITY_PROMPT_VERSION)

    def test_new_proposals_render_meanings_while_old_proposals_keep_the_original_renderer(self):
        text='{{ev:ev:synthetic}} Değişimin nedeni bu kayıttan belirlenemez.'
        current=render_proposal(text,packet(),MATERIALITY_PROMPT_VERSION)
        self.assertIn('Benzer fonlara göre getiri farkı',current)
        self.assertNotIn('D1',current)
        self.assertNotIn('değer:',current)
        legacy=render_proposal(text,packet(),'materiality-v1')
        self.assertIn('değer: 100; eşik: 50',legacy)
        for version in (MATERIALITY_PROMPT_VERSION,'materiality-v1'):
            with self.subTest(version=version),self.assertRaises(InvalidOutput):
                render_proposal('Fiyat yüzde elli arttı.',packet(),version)

    def test_plain_proposal_numbers_are_only_rendered_from_existing_dated_evidence(self):
        value=packet().model_copy(update={'evidence':[Evidence(evidence_id='ev:synthetic',
            detector_id='AN-DQ-001',state='TRIGGERED',value='15',threshold='2',effective_date='2030-01-01',is_attribute=False)]})
        self.assertIn('15 hafta içi gün',render_proposal('{{ev:ev:synthetic}}',value,MATERIALITY_PROMPT_VERSION))
        with self.assertRaises(InvalidOutput):
            render_proposal('15 hafta içi gün geçmiş.',value,MATERIALITY_PROMPT_VERSION)

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
        for text in ('Yüzde kırk arttı.','İki kat yükseldi.','iki yüz seviyesinde','THF hakkında','ev:synthetic','17 Eylül','MANİPÜLASYON','RISKSIZ','ÇOK ÜZERİNDE','SATIN AL','tasfiye edilebilir','teminat','Bir yıl sonra'):
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
        with self.assertRaisesRegex(AIUnavailable,'LIVE_DATABASE_REJECTED'):
            decide(Settings(db_name='p50k_dev'),AIConfig(mode='live'),packet())

    def test_live_boundary_reserves_first_disables_sdk_retries_and_response_storage(self):
        events=[]
        with TemporaryDirectory() as folder:
            path=Path(folder)/'synthetic-key'
            path.write_text('synthetic-api-credential',encoding='utf-8')
            with patch('p50k.product.ai_client.OpenAI') as factory,patch('p50k.product.ai_client.reserve',side_effect=lambda *_:events.append('reserved') or 'synthetic-reservation') as reserved,patch('p50k.product.ai_client.settle') as settled,patch('p50k.product.ai_client.connect') as database:
                client=factory.return_value
                response=SimpleNamespace(status='completed',id='synthetic-call',usage=SimpleNamespace(input_tokens=100,output_tokens=20),
                    output_text=json.dumps({'decision':'MATERIAL','cited_evidence_ids':['e1'],'rationale_tr':'{{ev:e1}}','missing_evidence_tr':''}))
                client.responses.create.side_effect=lambda **kwargs:events.append('called') or response
                output,_,_=decide(Settings(),AIConfig(mode='live',key_file=path),packet())
                self.assertEqual(validate_output(output,packet()).cited_evidence_ids,['ev:synthetic'])
                self.assertEqual(output['rationale_tr'],'{{ev:ev:synthetic}}')
                self.assertEqual(events,['reserved','called'])
                self.assertEqual(factory.call_args.kwargs['max_retries'],0)
                self.assertEqual(factory.call_args.kwargs['timeout'],60)
                request=client.responses.create.call_args.kwargs
                self.assertFalse(request['store'])
                self.assertEqual(request['max_output_tokens'],2000)
                self.assertTrue(request['text']['format']['strict'])
                self.assertEqual(request['text']['format']['schema']['properties']['decision']['enum'],packet().allowed_options)
                self.assertEqual(request['text']['format']['schema']['properties']['cited_evidence_ids']['items']['enum'],['e1'])
                sent=json.loads(request['input'])
                projected=packet().model_dump()
                projected['evidence'][0]['evidence_id']='e1'
                self.assertEqual(sent['evidence_packet'],projected)
                self.assertTrue(sent['evidence_explanations'])
                self.assertIn('everyday Turkish',request['instructions'])
                minimum=(Decimal(len(request['input'].encode())+len(request['instructions'].encode()))*Decimal('2.5')+Decimal(2000)*Decimal('10'))/Decimal(1000000)
                self.assertGreater(reserved.call_args.args[2],minimum)
                inserted=database.return_value.__enter__.return_value.execute.call_args.args
                self.assertIn(MATERIALITY_PROMPT_VERSION,inserted[1])
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

    def test_concurrent_reservations_cannot_exceed_the_bucket_cap(self):
        def attempt(_):
            try:return reserve(self.settings,self.bucket,Decimal('.75'))
            except AIUnavailable:return None
        with ThreadPoolExecutor(max_workers=2) as workers:
            outcomes=list(workers.map(attempt,range(2)))
        self.assertEqual(sum(value is not None for value in outcomes),1)
        settle(self.settings,next(value for value in outcomes if value is not None),Decimal('.75'))

    def test_two_workers_claim_distinct_jobs_and_expired_lease_changes_owner(self):
        jobs={enqueue(self.settings,'THF',uuid4().hex*2),enqueue(self.settings,'TP2',uuid4().hex*2)}
        owners=('synthetic-first-'+uuid4().hex,'synthetic-second-'+uuid4().hex)
        with ThreadPoolExecutor(max_workers=2) as workers:
            claimed=list(workers.map(lambda owner:claim(self.settings,owner),owners))
        self.assertEqual({str(job[0]) for job in claimed},jobs)
        with connect(self.settings) as connection:
            connection.execute("UPDATE ops.jobs SET lease_until=now()-interval '1 second' WHERE job_id=%s",(claimed[0][0],))
        recovered=claim(self.settings,'synthetic-recovery')
        self.assertEqual(recovered[0],claimed[0][0])
        self.assertFalse(finish(self.settings,str(recovered[0]),owners[0]))
        self.assertTrue(finish(self.settings,str(recovered[0]),'synthetic-recovery'))
        self.assertTrue(finish(self.settings,str(claimed[1][0]),owners[1]))
