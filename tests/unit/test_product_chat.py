"""Synthetic chat boundaries, tool loop and owner-scoped PostgreSQL audit."""
from __future__ import annotations
from dataclasses import replace
from decimal import Decimal
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor

from p50k.product import chat
from p50k.product.ai_client import AIConfig, AIUnavailable
from p50k.product.chat_tools import ChatContext, bounded_json, invoke_tool, load_context
from p50k.product.db import connect
from p50k.product.settings import Settings
from p50k.product.validator import InvalidOutput
from tests.unit.test_product_ai import packet


def context():
    return ChatContext(packet(), str(uuid4()), 'SYNTHETIC', 'a'*64)


def answer(**changes):
    return {'text_tr':'Bu kanıt inceleme gerektiriyor. {{ev:ev:synthetic}}',
            'cited_evidence_ids':['ev:synthetic'], 'missing_evidence_tr':'', **changes}


class ChatBoundaryTests(unittest.TestCase):
    def test_private_secret_and_raw_numeric_questions_are_blocked_before_egress(self):
        for question in ('mail@example.invalid', 'TR123456789', 'sk-synthetic-secret', 'NAV 100,42',
                         'https://example.invalid', 'şifrem nedir', 'telefon numaram', '   '):
            with self.subTest(question=question), self.assertRaises(AIUnavailable):
                chat.check_question(question, 'TP2')
        self.assertEqual(chat.check_question('TP2 kanıtlarını açıkla', 'TP2'), 'TP2 kanıtlarını açıkla')
        self.assertEqual(chat.check_question('D1 ve AN-DQ-001 neden tetiklendi?', 'THF'), 'D1 ve AN-DQ-001 neden tetiklendi?')
        for question in ('Adım Synthetic Person, portföyümün durumu ne?', 'Adresim Synthetic Street, fon kanıtlarını açıkla'):
            with self.assertRaises(AIUnavailable):chat.check_question(question,'THF')

    def test_four_tools_reject_extra_arguments_scope_unknown_name_and_overflow(self):
        current = context()
        for name, args in (('sql', '{}'), ('get_signals','{"fund_code":"TP2"}'),
                           ('get_signals','{"fund_code":"THF","sql":"SELECT 1"}'),
                           ('search_funds','{"query":"Synthetic","limit":6}')):
            with self.subTest(name=name), self.assertRaises(AIUnavailable):
                invoke_tool(Settings(), current, name, args)
        result = json.loads(invoke_tool(Settings(), current, 'get_signals', '{"fund_code":"THF"}'))
        self.assertEqual(result, current.packet.model_dump())
        self.assertFalse({'prices','nav','investors','email','review_reason'} & result.keys())
        with self.assertRaises(AIUnavailable): bounded_json({'text':'a'*4096})

    def test_answer_numbers_unknown_citations_and_uncited_placeholders_are_rejected(self):
        for raw in (answer(text_tr='Yüzde kırk arttı.'), answer(cited_evidence_ids=['unknown']),
                    answer(cited_evidence_ids=['ev:other'])):
            with self.subTest(raw=raw), self.assertRaises(InvalidOutput):
                chat.validate_answer(raw, context())
        self.assertEqual(chat.validate_answer(answer(), context()).cited_evidence_ids, ['ev:synthetic'])

    def test_abstained_evidence_cannot_support_regulatory_or_positive_assertions(self):
        current=context()
        item=current.packet.evidence[0].model_copy(update={'state':'ABSTAINED'})
        current=replace(current,packet=current.packet.model_copy(update={'evidence':[item]}))
        for text in ('SPK bu fonu onayladı.','Fon tasfiye edildi.','Anomali tespit edildi.','Fonun kanıtları kesin sonuç veriyor.'):
            with self.subTest(text=text),self.assertRaises(InvalidOutput):chat.validate_answer(answer(text_tr=text),current)
        chat.validate_answer(answer(text_tr='Mevcut kanıt yeterli değil.'),current)

    def test_invalid_text_is_not_streamed_and_only_valid_final_answer_is_persisted(self):
        replies = [SimpleNamespace(id='synthetic-bad', output=[], output_text=json.dumps(answer(text_tr='100 kazandırır.'))),
                   SimpleNamespace(id='synthetic-valid', output=[], output_text=json.dumps(answer()))]
        with patch.object(chat,'model_call',side_effect=replies), patch.object(chat,'finish_turn') as saved:
            emitted = list(chat.events(Settings(), AIConfig(mode='live'), chat.ChatBody(fund_code='THF',question='Kanıtları açıkla'), context(), 'thread','turn', []))
        self.assertEqual([name for name,_ in emitted], ['answer'])
        self.assertNotIn('kazandırır', emitted[0][1]['content'])
        self.assertIn('değer: 100; eşik: 50', emitted[0][1]['content'])
        self.assertEqual(saved.call_args.args[3], 'VALID')

    def test_three_invalid_calls_fail_closed_without_assistant_content(self):
        reply = SimpleNamespace(id='synthetic-bad', output=[], output_text=json.dumps(answer(text_tr='satın al')))
        with patch.object(chat,'model_call',return_value=reply) as called, patch.object(chat,'finish_turn') as saved:
            emitted = list(chat.events(Settings(), AIConfig(mode='live'), chat.ChatBody(fund_code='THF',question='Kanıtları açıkla'), context(), 'thread','turn', []))
        self.assertEqual(called.call_count, 3)
        self.assertEqual(emitted, [('error', {'code':'CHAT_VALIDATION_OR_CALL_LIMIT'})])
        self.assertEqual(saved.call_args.args[3], 'FAILED')
        self.assertNotIn('content', saved.call_args.kwargs)

    def test_tool_loop_is_read_only_and_stops_before_seventh_tool(self):
        class Tool:
            type='function_call'
            name='get_signals'
            arguments='{"fund_code":"THF"}'
            call_id='synthetic-call'
            def model_dump(self, **_): return {'type':self.type,'name':self.name,'arguments':self.arguments,'call_id':self.call_id}
        reply = SimpleNamespace(id='synthetic-tools', output=[Tool() for _ in range(7)], output_text='')
        with patch.object(chat,'model_call',return_value=reply) as called, patch.object(chat,'finish_turn'):
            emitted = list(chat.events(Settings(), AIConfig(mode='live'), chat.ChatBody(fund_code='THF',question='Kanıtları açıkla'), context(), 'thread','turn', []))
        self.assertEqual(called.call_count, 1)
        self.assertEqual(sum(name=='tool' for name,_ in emitted), 6)
        self.assertEqual(emitted[-1], ('error', {'code':'CHAT_TOOL_LIMIT'}))

    def test_live_transport_reserves_chat_budget_disables_storage_and_sdk_retries(self):
        with TemporaryDirectory() as folder:
            key=Path(folder)/'synthetic-key'
            key.write_text('synthetic-api-credential',encoding='utf-8')
            with patch.object(chat,'OpenAI') as factory, patch.object(chat,'reserve',return_value='synthetic-reservation') as reserved, patch.object(chat,'settle'), patch.object(chat,'connect'):
                factory.return_value.responses.create.return_value=SimpleNamespace(status='completed', id='synthetic-call', usage=SimpleNamespace(input_tokens=10,output_tokens=10))
                chat.model_call(Settings(), AIConfig(mode='live',key_file=key), [{'role':'user','content':'synthetic'}], 20)
                self.assertEqual(reserved.call_args.args[1], 'chat')
                self.assertGreater(reserved.call_args.args[2], Decimal(0))
                self.assertEqual(factory.call_args.kwargs['max_retries'],0)
                self.assertLessEqual(factory.call_args.kwargs['timeout'],10)
                self.assertGreater(factory.call_args.kwargs['timeout'],0)
                request=factory.return_value.responses.create.call_args.kwargs
                self.assertFalse(request['store'])
                self.assertEqual(len(request['tools']),4)
                self.assertTrue(request['text']['format']['strict'])


@unittest.skipUnless(os.environ.get('P50K_TEST_DATABASE')=='1','Requires isolated p50k_dev')
class ChatDatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from p50k.product import detector_pipeline as pipeline
        settings=Settings.from_env()
        if settings.db_name!='p50k_dev':raise RuntimeError('Synthetic chat tests require p50k_dev')
        with connect(settings) as connection:
            connection.execute("INSERT INTO ref.funds(fund_code,name,category,source_sha256) VALUES ('THF','Synthetic chat fund','Synthetic chat category',%s) ON CONFLICT DO NOTHING",('b'*64,))
            connection.execute("INSERT INTO obs.fund_prices(fund_code,effective_date,nav,source_sha256,origin,available_at,observed_at,availability_rule) VALUES ('THF','2030-01-30',100,%s,'SYNTHETIC','2030-01-30T12:00:00Z','2030-01-30T12:00:00Z','synthetic') ON CONFLICT DO NOTHING",('b'*64,))
        with patch.object(pipeline,'VERSION_ID','synthetic-chat-'+uuid4().hex),connect(settings) as connection:
            pipeline.run_detectors(connection,datetime(2030,2,6,12,tzinfo=timezone.utc),'SYNTHETIC')

    def setUp(self):
        self.settings=Settings.from_env()
        self.assertEqual(self.settings.db_name,'p50k_dev')
        with connect(self.settings) as connection:
            self.actor=str(connection.execute("INSERT INTO auth.users(email,password_hash) VALUES (%s,'synthetic-hash') RETURNING user_id",(uuid4().hex+'@example.invalid',)).fetchone()[0])
            self.other=str(connection.execute("INSERT INTO auth.users(email,password_hash) VALUES (%s,'synthetic-hash') RETURNING user_id",(uuid4().hex+'@example.invalid',)).fetchone()[0])
            run=connection.execute('SELECT run_id FROM det.detector_runs ORDER BY created_at DESC LIMIT 1').fetchone()
        if not run: self.fail('Seed the isolated detector fixture before chat database tests')
        self.context=replace(context(),run_id=str(run[0]))
        self.body=chat.ChatBody(fund_code='THF',question='Kanıtları açıkla')

    def test_thread_owner_scope_busy_turn_and_append_only_audit(self):
        thread,turn,previous=chat.begin_turn(self.settings,self.actor,self.body,self.context)
        self.assertEqual(previous,[])
        repeated=chat.ChatBody(fund_code='THF',question='Kanıtları açıkla',thread_id=thread)
        with self.assertRaisesRegex(AIUnavailable,'THREAD_NOT_FOUND'):chat.begin_turn(self.settings,self.other,repeated,self.context)
        with self.assertRaisesRegex(AIUnavailable,'THREAD_NOT_FOUND'):chat.history(self.settings,self.other,thread,'THF')
        with self.assertRaisesRegex(AIUnavailable,'THREAD_BUSY'):chat.begin_turn(self.settings,self.actor,repeated,self.context)
        emitted=list(chat.events(self.settings,AIConfig(mode='mock'),self.body,self.context,thread,turn,[]))
        self.assertEqual(emitted[0][0],'answer')
        self.assertEqual([row['role'] for row in chat.history(self.settings,self.actor,thread,'THF')],['user','assistant'])
        with connect(self.settings) as connection:
            self.assertEqual(connection.execute('SELECT packet_sha256 FROM ai.chat_turns WHERE turn_id=%s',(turn,)).fetchone()[0],self.context.checksum)
        with self.assertRaises(Exception), connect(self.settings) as connection:
            connection.execute('DELETE FROM ai.chat_messages WHERE thread_id=%s',(thread,))

    def test_concurrent_final_daily_turn_allows_exactly_one(self):
        for _ in range(29):chat.begin_turn(self.settings,self.actor,self.body,self.context)
        def attempt(_):
            try:return chat.begin_turn(self.settings,self.actor,self.body,self.context)[1]
            except AIUnavailable as error:return str(error)
        with ThreadPoolExecutor(max_workers=2) as pool:outcomes=list(pool.map(attempt,range(2)))
        self.assertEqual(outcomes.count('CHAT_DAILY_LIMIT'),1)
        with connect(self.settings) as connection:
            self.assertEqual(connection.execute('SELECT count(*) FROM ai.chat_turns WHERE user_id=%s',(self.actor,)).fetchone()[0],30)

    def test_future_detector_run_cannot_leak_into_chat(self):
        # Future fixtures must be excluded, even if an earlier real-clock seed exists.
        try:
            selected=load_context(self.settings,'THF')
        except AIUnavailable as error:
            self.assertEqual(str(error),'EVIDENCE_UNAVAILABLE')
        else:
            with connect(self.settings) as connection:
                cutoff=connection.execute('SELECT cutoff FROM det.detector_runs WHERE run_id=%s',(selected.run_id,)).fetchone()[0]
            self.assertLessEqual(cutoff,datetime.now(timezone.utc))
            self.assertLessEqual(selected.packet.as_of,datetime.now(timezone.utc).date().isoformat())
