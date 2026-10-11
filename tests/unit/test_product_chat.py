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


def streamed_answer(**changes):
    value=answer(**changes)
    value.pop('missing_evidence_tr')
    return {'paragraphs':[value]}


def transport(reply, paragraphs=()):
    yield from paragraphs
    return reply


class ChatBoundaryTests(unittest.TestCase):
    def test_historical_projection_blinds_identity_and_remaps_only_bounded_tools(self):
        current=replace(context(),origin='HISTORICAL_REPLAY')
        class Tool:
            type='function_call';name='get_signals';arguments='{"fund_code":"FUND"}';call_id='synthetic-historical-tool'
            def model_dump(self,**_):return {'type':self.type,'name':self.name,'arguments':self.arguments,'call_id':self.call_id}
        replies=[SimpleNamespace(id='synthetic-lookup',output=[Tool()],output_text=''),
                 SimpleNamespace(id='synthetic-final',output=[],output_text=json.dumps({'paragraphs':[{'text_tr':'Mevcut bilgi inceleme gerektiriyor.','cited_evidence_ids':['e1']}]}))]
        body=chat.ChatBody(fund_code=current.packet.fund_code,question=current.packet.fund_name+' '+current.packet.fund_code+' neden değişti?')
        with patch.object(chat,'model_call',side_effect=[transport(reply) for reply in replies]) as model, \
                patch.object(chat,'invoke_tool',return_value=current.packet.model_dump_json()) as tool, \
                patch.object(chat,'save_chunk'),patch.object(chat,'finish_turn'):
            emitted=list(chat.events(Settings(),AIConfig(mode='live'),body,current,'thread','turn',[current.packet.fund_code+' önceki soru']))
        self.assertEqual(emitted[-1][0],'answer')
        first=json.loads(model.call_args_list[0].args[2][0]['content'])
        self.assertEqual(first['packet']['fund_code'],'FUND')
        serialized=json.dumps(first,ensure_ascii=False)
        self.assertNotIn(current.packet.fund_code,serialized)
        self.assertNotIn(current.packet.fund_name,serialized)
        self.assertEqual(json.loads(tool.call_args.args[3])['fund_code'],current.packet.fund_code)

    def test_historical_transport_does_not_offer_catalog_or_identity_tools(self):
        current=replace(context(),origin='HISTORICAL_REPLAY')
        with TemporaryDirectory() as folder:
            key=Path(folder)/'synthetic-key';key.write_text('synthetic-api-credential',encoding='utf-8')
            with patch.object(chat,'OpenAI') as factory,patch.object(chat,'reserve',return_value='synthetic-reservation'),patch.object(chat,'settle'),patch.object(chat,'connect'):
                stream=factory.return_value.responses.create.return_value
                stream.__iter__.return_value=iter([SimpleNamespace(type='response.completed',response=SimpleNamespace(status='completed',id='synthetic-call',usage=SimpleNamespace(input_tokens=10,output_tokens=10)))])
                list(chat.model_call(Settings(),AIConfig(mode='live',key_file=key),[{'role':'user','content':'synthetic'}],20,current))
                sent=factory.return_value.responses.create.call_args.kwargs
                # Identity tools stay hidden; the agent tools reveal no fund identity.
                self.assertEqual({item['name'] for item in sent['tools']},{'get_signals','get_decision','get_case_status','request_investigation'})

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
        replies = [SimpleNamespace(id='synthetic-bad', output=[], output_text=json.dumps(streamed_answer(text_tr='100 kazandırır.'))),
                   SimpleNamespace(id='synthetic-valid', output=[], output_text=json.dumps(streamed_answer()))]
        with patch.object(chat,'model_call',side_effect=[transport(reply) for reply in replies]), patch.object(chat,'save_chunk'), patch.object(chat,'finish_turn') as saved:
            emitted = list(chat.events(Settings(), AIConfig(mode='live'), chat.ChatBody(fund_code='THF',question='Kanıtları açıkla'), context(), 'thread','turn', []))
        self.assertEqual([name for name,_ in emitted], ['paragraph','answer'])
        self.assertNotIn('kazandırır', emitted[0][1]['content'])
        self.assertIn('Benzer fonlara göre getiri farkı', emitted[0][1]['content'])
        self.assertNotIn('D1', emitted[0][1]['content'])
        self.assertEqual(saved.call_args.args[3], 'VALID')

    def test_three_invalid_calls_fail_closed_without_assistant_content(self):
        reply = SimpleNamespace(id='synthetic-bad', output=[], output_text=json.dumps(streamed_answer(text_tr='satın al')))
        with patch.object(chat,'model_call',side_effect=lambda *args:transport(reply)) as called, patch.object(chat,'finish_turn') as saved:
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
        with patch.object(chat,'model_call',side_effect=lambda *args:transport(reply)) as called, patch.object(chat,'finish_turn'):
            emitted = list(chat.events(Settings(), AIConfig(mode='live'), chat.ChatBody(fund_code='THF',question='Kanıtları açıkla'), context(), 'thread','turn', []))
        self.assertEqual(called.call_count, 1)
        self.assertEqual(sum(name=='tool' for name,_ in emitted), 6)
        self.assertEqual(emitted[-1], ('error', {'code':'CHAT_TOOL_LIMIT'}))

    def test_live_transport_reserves_chat_budget_disables_storage_and_sdk_retries(self):
        with TemporaryDirectory() as folder:
            key=Path(folder)/'synthetic-key'
            key.write_text('synthetic-api-credential',encoding='utf-8')
            with patch.object(chat,'OpenAI') as factory, patch.object(chat,'reserve',return_value='synthetic-reservation') as reserved, patch.object(chat,'settle'), patch.object(chat,'connect'):
                stream=factory.return_value.responses.create.return_value
                stream.__iter__.return_value=iter([SimpleNamespace(type='response.completed',response=SimpleNamespace(status='completed', id='synthetic-call', usage=SimpleNamespace(input_tokens=10,output_tokens=10)))])
                list(chat.model_call(Settings(), AIConfig(mode='live',key_file=key), [{'role':'user','content':'synthetic'}], 20,context()))
                self.assertEqual(reserved.call_args.args[1], 'chat')
                self.assertGreater(reserved.call_args.args[2], Decimal(0))
                self.assertEqual(factory.call_args.kwargs['max_retries'],0)
                self.assertLessEqual(factory.call_args.kwargs['timeout'],10)
                self.assertGreater(factory.call_args.kwargs['timeout'],0)
                request=factory.return_value.responses.create.call_args.kwargs
                self.assertFalse(request['store'])
                self.assertTrue(request['stream'])
                self.assertEqual(len(request['tools']),6)
                self.assertIn('Raportör',request['instructions'])
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
        self.assertEqual([name for name,_ in emitted],['paragraph','answer'])
        with connect(self.settings) as connection:
            chunk=connection.execute('SELECT content FROM ai.chat_stream_chunks WHERE turn_id=%s',(turn,)).fetchone()
            self.assertEqual(chunk[0],emitted[0][1]['content'])
            with self.assertRaises(Exception):connection.execute('DELETE FROM ai.chat_stream_chunks WHERE turn_id=%s',(turn,))
        self.assertEqual([row['role'] for row in chat.history(self.settings,self.actor,thread,'THF')],['user','assistant'])
        with connect(self.settings) as connection:
            self.assertEqual(connection.execute('SELECT packet_sha256 FROM ai.chat_turns WHERE turn_id=%s',(turn,)).fetchone()[0],self.context.checksum)
        with self.assertRaises(Exception), connect(self.settings) as connection:
            connection.execute('DELETE FROM ai.chat_messages WHERE thread_id=%s',(thread,))

    def test_concurrent_final_daily_turn_allows_exactly_one(self):
        new_conversation=self.body.model_copy(update={'new_thread':True})
        for _ in range(29):chat.begin_turn(self.settings,self.actor,new_conversation,self.context)
        def attempt(_):
            try:return chat.begin_turn(self.settings,self.actor,new_conversation,self.context)[1]
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

    def test_latest_asset_conversation_restores_and_reuses_its_persisted_thread(self):
        with patch.object(chat,'analysis_scope_key',return_value='live'):
            thread,turn,_=chat.begin_turn(self.settings,self.actor,self.body,self.context)
            list(chat.events(self.settings,AIConfig(mode='mock'),self.body,self.context,thread,turn,[]))
            saved=chat.thread_list(self.settings,self.actor,'THF')
            self.assertEqual(saved['items'][0]['thread_id'],thread)
            self.assertEqual(saved['items'][0]['message_count'],2)
            rows=chat.history(self.settings,self.actor,thread,'THF')
            self.assertEqual([r['role'] for r in rows],['user','assistant'])
            self.assertEqual(rows[1]['status'],'VALID')
            self.assertTrue(rows[1]['evidence_labels'])
            # A remounted client can omit its lost React thread id and continue.
            continued,_,previous=chat.begin_turn(self.settings,self.actor,self.body,self.context)
            self.assertEqual(continued,thread)
            self.assertEqual(previous,[self.body.question])
            self.assertEqual(chat.thread_list(self.settings,self.other,'THF')['items'],[])
            self.assertEqual(chat.thread_list(self.settings,self.actor,'TP2')['items'],[])

    def test_analysis_scopes_hide_and_reject_other_dates_without_deleting_history(self):
        with patch.object(chat,'analysis_scope_key',return_value='live'):
            live,turn,_=chat.begin_turn(self.settings,self.actor,self.body,self.context)
            list(chat.events(self.settings,AIConfig(mode='mock'),self.body,self.context,live,turn,[]))
        with patch.object(chat,'analysis_scope_key',return_value='asof:2026-09-12'):
            self.assertEqual(chat.thread_list(self.settings,self.actor,'THF')['items'],[])
            with self.assertRaisesRegex(AIUnavailable,'THREAD_NOT_FOUND'):
                chat.history(self.settings,self.actor,live,'THF')
            with self.assertRaisesRegex(AIUnavailable,'THREAD_NOT_FOUND'):
                chat.begin_turn(self.settings,self.actor,self.body.model_copy(update={'thread_id':live}),self.context)
            dated,_,_=chat.begin_turn(self.settings,self.actor,self.body,self.context)
            self.assertNotEqual(live,dated)
        with patch.object(chat,'analysis_scope_key',return_value='live'):
            self.assertEqual(chat.thread_list(self.settings,self.actor,'THF')['items'][0]['thread_id'],live)
            self.assertEqual(len(chat.history(self.settings,self.actor,live,'THF')),2)

    def test_failed_turn_retains_question_but_never_restores_unvalidated_assistant_content(self):
        thread,turn,_=chat.begin_turn(self.settings,self.actor,self.body,self.context)
        self.assertEqual(chat.history(self.settings,self.actor,thread,'THF')[0]['status'],'PENDING')
        chat.finish_turn(self.settings,thread,turn,'FAILED','synthetic',[],
                         content='Synthetic content from an invalid legacy writer',error='SYNTHETIC_REJECTED')
        rows=chat.history(self.settings,self.actor,thread,'THF')
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['role'],'user')
        self.assertEqual(rows[0]['status'],'FAILED')
        self.assertEqual(rows[0]['error_code'],'SYNTHETIC_REJECTED')

    def test_new_conversation_is_explicit_and_saved_selector_remains_owner_scoped(self):
        first,turn,_=chat.begin_turn(self.settings,self.actor,self.body,self.context)
        list(chat.events(self.settings,AIConfig(mode='mock'),self.body,self.context,first,turn,[]))
        second,_,_=chat.begin_turn(self.settings,self.actor,self.body.model_copy(update={'new_thread':True}),self.context)
        self.assertNotEqual(first,second)
        self.assertEqual([r['thread_id'] for r in chat.thread_list(self.settings,self.actor,'THF')['items']],[second,first])
        with self.assertRaisesRegex(AIUnavailable,'QUESTION_REJECTED'):
            chat.begin_turn(self.settings,self.actor,self.body.model_copy(update={'thread_id':first,'new_thread':True}),self.context)

    def test_history_pages_are_bounded_and_can_recover_older_messages(self):
        thread,turn,_=chat.begin_turn(self.settings,self.actor,self.body,self.context)
        with connect(self.settings) as connection:
            for index in range(65):
                connection.execute("INSERT INTO ai.chat_messages(thread_id,turn_id,role,content) VALUES(%s,%s,'user',%s)",
                                   (thread,turn,'Synthetic saved question '+str(index)))
        recent=chat.history(self.settings,self.actor,thread,'THF')
        self.assertEqual(len(recent),60)
        earlier=chat.history(self.settings,self.actor,thread,'THF',int(recent[0]['message_id']))
        self.assertEqual(len(earlier),6)
        self.assertEqual(len({row['message_id'] for row in earlier+recent}),66)
        with self.assertRaisesRegex(AIUnavailable,'THREAD_NOT_FOUND'):
            chat.history(self.settings,self.other,thread,'THF',int(recent[0]['message_id']))

    def test_thread_selector_can_page_past_twenty_conversations(self):
        for _ in range(23):
            chat.begin_turn(self.settings,self.actor,self.body.model_copy(update={'new_thread':True}),self.context)
        first=chat.thread_list(self.settings,self.actor,'THF')
        older=chat.thread_list(self.settings,self.actor,'THF',offset=20)
        self.assertEqual(len(first['items']),20)
        self.assertEqual(len(older['items']),3)
        self.assertEqual(len({row['thread_id'] for row in first['items']+older['items']}),23)
        self.assertEqual(chat.thread_list(self.settings,self.other,'THF',offset=20)['items'],[])

    def test_http_history_follows_server_date_cookie_and_never_client_supplied_scope(self):
        from fastapi.testclient import TestClient
        from p50k.product.app import create_app
        from p50k.product.auth import Principal,CSRF_COOKIE,digest_token
        from p50k.product.analysis_context import use_analysis_date
        with use_analysis_date('live'):
            thread,turn,_=chat.begin_turn(self.settings,self.actor,self.body,self.context)
            list(chat.events(self.settings,AIConfig(mode='mock'),self.body,self.context,thread,turn,[]))
        csrf='s'*43
        actor=Principal(self.actor,'synthetic@example.invalid','viewer','synthetic-session',digest_token(csrf))
        with patch('p50k.product.auth.AuthService.authenticate',return_value=actor),TestClient(create_app(self.settings,readiness=lambda _:True),base_url='http://127.0.0.1:3071') as client:
            client.cookies.set('p50k_as_of','live')
            self.assertEqual(client.get('/chat/threads?fund_code=THF').json()['items'][0]['thread_id'],thread)
            self.assertEqual(client.get('/chat/'+thread+'?fund_code=THF').status_code,200)
            client.cookies.set('p50k_as_of','2026-09-12')
            hidden=client.get('/chat/threads?fund_code=THF&analysis_scope_key=live').json()
            self.assertEqual(hidden['analysis_scope_key'],'asof:2026-09-12')
            self.assertEqual(hidden['items'],[])
            self.assertEqual(client.get('/chat/'+thread+'?fund_code=THF').status_code,404)
            client.cookies.set(CSRF_COOKIE,csrf)
            headers={'Origin':'http://127.0.0.1:3071','X-CSRF-Token':csrf}
            response=client.post('/chat',headers=headers,json={**self.body.model_dump(),'analysis_scope_key':'live'})
            self.assertEqual(response.status_code,422)
