"""DEC-035 agent team: validator on agent output, AI-off and mock gates, page notes,
general Raportör paragraphs and the analysis view across a streaming response."""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient

from p50k.product import chat, chat_routes
from p50k.product.agents import general_chat, llm, roles, service, store
from p50k.product.agents.config import AgentConfig
from p50k.product.analysis_context import analysis_scope_key, selection, use_analysis_date
from p50k.product.app import create_app
from p50k.product.chat_tools import ChatContext, HISTORICAL_TOOLS, TOOLS
from p50k.product.egress import Evidence, Packet, allowed_options
from p50k.product.settings import Settings
from tests.unit.test_product_ai import packet


def case_context(evidence: list[Evidence] | None = None, *, anonymous: bool = False) -> roles.CaseContext:
    base = packet()
    if evidence is not None:
        base = base.model_copy(update={'evidence': evidence, 'allowed_options': allowed_options(evidence)})
    context = ChatContext(base, str(uuid4()), 'SYNTHETIC', 'a' * 64)
    run = store.Run(context.run_id, date(2030, 1, 1), 'SYNTHETIC', datetime(2030, 1, 1, 20, tzinfo=timezone.utc))
    return roles.CaseContext('synthetic-case', base.fund_code, base.category, context, run, anonymous)


def reply(value: dict, call: str = 'synthetic-call') -> tuple:
    return json.dumps(value, ensure_ascii=False), call, roles.Decimal('0.01'), 'synthetic-model'


class AgentOutputValidatorTests(unittest.TestCase):
    def setUp(self):
        folder = TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        key = Path(folder.name) / 'synthetic-key'
        key.write_text('synthetic-api-credential', encoding='utf-8')
        self.live = AgentConfig(mode='live', key_file=key)
        self.settings = Settings(db_name='p50k')

    def test_invalid_hypothesis_is_retried_once_and_only_validated_text_is_rendered(self):
        invalid = {'hypotheses': [{'type': 'peer_divergence', 'cited_evidence_ids': ['e1'],
                                   'text_tr': 'Fon yüzde kırk değişti.'}]}
        valid = {'hypotheses': [{'type': 'peer_divergence', 'cited_evidence_ids': ['e1'],
                                 'text_tr': '{{ev:e1}} Fon benzer fonlardan farklı hareket etmiş olabilir.'}]}
        with patch.object(llm, 'call', side_effect=[reply(invalid, 'first'), reply(valid, 'second')]) as called:
            outcome = roles.hypothesizer(self.settings, self.live, case_context(anonymous=True))
        self.assertEqual(outcome.calls, ['first', 'second'])
        message = outcome.messages[0]
        self.assertEqual((message['kind'], message['to_role']), ('hypothesis', 'verifier'))
        self.assertNotIn('{{', message['body'])
        self.assertNotIn('yüzde', message['body'])
        self.assertIn('Benzer fonlara göre getiri farkı', message['body'])
        self.assertEqual(message['payload']['cited_evidence_ids'], ['ev:synthetic'])
        first = called.call_args_list[0].kwargs['payload']
        self.assertEqual(first['evidence_packet']['fund_code'], 'FUND')
        self.assertNotIn('THF', json.dumps(first, ensure_ascii=False))
        self.assertNotIn('Synthetic fund', json.dumps(first, ensure_ascii=False))
        self.assertIn('previous_attempt_rejected', called.call_args_list[1].kwargs['payload'])

    def test_two_invalid_outputs_fail_closed_without_any_message(self):
        invalid = {'hypotheses': [{'type': 'peer_divergence', 'cited_evidence_ids': ['e1'],
                                   'text_tr': 'Bu fonu satın al; manipülasyon var.'}]}
        with patch.object(llm, 'call', side_effect=[reply(invalid, 'a'), reply(invalid, 'b')]):
            with self.assertRaises(roles.Failed) as failure:
                roles.hypothesizer(self.settings, self.live, case_context())
        self.assertEqual(failure.exception.calls, ['a', 'b'])
        self.assertEqual(failure.exception.code, 'VALIDATION_FAILED')

    def test_reporter_cannot_propose_an_option_the_packet_does_not_allow(self):
        abstained = [Evidence(evidence_id='ev:abstained', detector_id='D1', state='ABSTAINED', value=None,
                              threshold=None, effective_date=None, is_attribute=False)]
        case = case_context(abstained)
        output = {'paragraphs': [{'cited_evidence_ids': ['e1'], 'text_tr': 'Ekip kanıtı inceledi.'}],
                  'decision': 'MATERIAL', 'cited_evidence_ids': ['e1'],
                  'rationale_tr': 'İnsan incelemesi gerekiyor.', 'missing_evidence_tr': ''}
        with patch.object(llm, 'call', side_effect=[reply(output, 'a'), reply(output, 'b')]):
            with self.assertRaises(roles.Failed):
                roles.reporter(self.settings, self.live, case, [], [], [], [])

    def test_verifier_needs_a_usable_test_or_triggered_evidence_for_a_verdict(self):
        abstained = [Evidence(evidence_id='ev:abstained', detector_id='D1', state='ABSTAINED', value=None,
                              threshold=None, effective_date=None, is_attribute=False)]
        case = case_context(abstained)
        hypotheses = [{'ref': 'h1', 'type': 'data_issue', 'text_template': 'Kaynak kaydı eksik olabilir.',
                       'cited_evidence_ids': ['ev:abstained']}]
        tests = [('t1', {'test': 'data_quality', 'outcome': 'unavailable', 'values': {}, 'reason': 'NO_PRICE_ROWS'})]
        supported = {'ratings': [{'target': 'h1', 'verdict': 'supported', 'cited_evidence_ids': ['e1'],
                                  'cited_tests': ['t1'], 'text_tr': 'Bu açıklama destekleniyor.'}]}
        undetermined = {'ratings': [{'target': 'h1', 'verdict': 'undetermined', 'cited_evidence_ids': ['e1'],
                                     'cited_tests': ['t1'], 'text_tr': 'Test yapılamadığı için açıklama belirsiz kalıyor.'}]}
        with patch.object(llm, 'call', side_effect=[reply(supported, 'a'), reply(undetermined, 'b')]):
            outcome = roles.verifier_ratings(self.settings, self.live, case, hypotheses, [], tests)
        self.assertEqual(outcome.calls, ['a', 'b'])
        self.assertEqual(outcome.messages[0]['payload']['verdict'], 'undetermined')
        self.assertTrue(outcome.messages[0]['body'].startswith('Veri sorunu: '))

    def test_ai_off_and_mock_outside_development_never_call_a_model(self):
        with patch.object(llm, 'call', side_effect=AssertionError('no model call')):
            with self.assertRaises(roles.Skip) as off:
                roles.hypothesizer(self.settings, AgentConfig(mode='off'), case_context())
            self.assertEqual(off.exception.code, 'AI_OFF')
            with self.assertRaises(roles.Skip) as mock:
                roles.skeptic(self.settings, AgentConfig(mode='mock'), case_context())
            self.assertEqual(mock.exception.code, 'AI_UNAVAILABLE')
            outcome = roles.skeptic(Settings(db_name='p50k_dev'), AgentConfig(mode='mock'), case_context())
        self.assertEqual(outcome.model_id, 'synthetic')
        self.assertEqual(outcome.messages[-1]['kind'], 'test_plan')

    def test_live_budget_gate_checks_the_total_target_before_the_daily_bucket(self):
        config = AgentConfig(mode='live', total_target_usd=roles.Decimal('25'))
        with patch.object(llm, 'connect') as connected, patch.object(llm, 'reserve') as reserved:
            connected.return_value.__enter__.return_value.execute.return_value.fetchone.return_value = (roles.Decimal('24.99'),)
            with self.assertRaises(llm.BudgetWait) as wait:
                llm.reserve_agent_budget(self.settings, config, roles.Decimal('0.05'))
        self.assertEqual(wait.exception.reason, 'TOTAL_TARGET')
        reserved.assert_not_called()
        self.assertTrue(llm.daily_bucket(date(2026, 9, 12)).endswith('2026-09-12'))
        self.assertEqual([store.scope_date(value) for value in ('asof:2026-09-12', 'live')], ['2026-09-12', 'live'])
        self.assertEqual(store.scope_key(store.scope_date('asof:2026-09-12')), 'asof:2026-09-12')
        self.assertEqual(AgentConfig.from_env({}).daily_cap_usd, roles.Decimal('3.00'))


class PageAndGeneralChatTests(unittest.TestCase):
    def test_page_notes_are_deterministic_and_suggestions_are_valid_questions(self):
        signals = [('D1', 'TRIGGERED', False), ('AN-DQ-001', 'TRIGGERED', False), ('D5', 'TRIGGERED', True)]
        first = service.fund_note(signals, (uuid4(), 'investigating', 10))
        self.assertEqual(first, service.fund_note(signals, (first['case']['case_id'], 'investigating', 10)))
        self.assertIn('Benzer fonlarla getiri karşılaştırması', first['note_tr'])
        self.assertNotIn('Fiyat geçmişinin uzunluğu', first['note_tr'])
        self.assertIsNotNone(first['warning_tr'])
        quiet = service.fund_note([('D1', 'NOT_TRIGGERED', False)], None)
        self.assertIn('aşılmadı', quiet['note_tr'])
        self.assertIsNone(quiet['case'])
        for note in (first, quiet, service.general_note('home', 3, 1), service.general_note('stock', 0, 0)):
            self.assertLessEqual(len(note['suggestions']), 3)
            for suggestion in note['suggestions']:
                self.assertEqual(chat.check_question(suggestion['prompt_tr'], 'THF'), suggestion['prompt_tr'])
                self.assertEqual(chat.check_question(suggestion['prompt_tr'], None), suggestion['prompt_tr'])
        self.assertEqual([service.page_kind(path) for path in ('/', '/funds', '/funds/THF', '/stocks/X', '/ekip/raportor')],
                         ['home', 'fund_catalog', 'fund_detail', 'stock', 'team'])

    def general(self) -> general_chat.GeneralContext:
        cases = (general_chat.CaseRef('c1', str(uuid4()), 'THF', 'Synthetic fund', 'investigating', 'sentinel',
                                      'Hipotezci çalışıyor', ('Benzer fonlarla getiri karşılaştırması',),
                                      (('ev:synthetic', 'D1'),)),
                 general_chat.CaseRef('c2', str(uuid4()), 'TP2', 'Second synthetic fund', 'reported', 'user',
                                      'Rapor yazıldı', (), ()))
        return general_chat.GeneralContext('asof:2026-09-12', str(uuid4()), str(uuid4()), 'home', 'working', cases)

    def test_general_paragraphs_use_case_placeholders_and_the_existing_validator(self):
        general = self.general()
        rendered = general.paragraph({'cited_case_refs': ['c1'], 'text_tr': '{{case:c1}} için ekip incelemeyi sürdürüyor.'}, 0)
        self.assertEqual(rendered['content'], 'Synthetic fund için ekip incelemeyi sürdürüyor.')
        self.assertEqual(rendered['evidence_ids'], ['ev:synthetic'])
        self.assertEqual(general.labels(rendered['evidence_ids']), {'ev:synthetic': 'Benzer fonlarla getiri karşılaştırması'})
        for raw in ({'cited_case_refs': ['c3'], 'text_tr': 'Ekip çalışıyor.'},
                    {'cited_case_refs': [], 'text_tr': '{{case:c1}} inceleniyor.'},
                    {'cited_case_refs': ['c1'], 'text_tr': 'Ekip üç vakayı inceliyor.'},
                    {'cited_case_refs': ['c1'], 'text_tr': 'THF fonu inceleniyor.'},
                    {'cited_case_refs': [], 'text_tr': '{{fund}} inceleniyor.'},
                    {'cited_case_refs': [], 'text_tr': 'Anomali tespit edildi.'},
                    {'cited_case_refs': ['c2'], 'text_tr': 'Bu fon için tavsiye veriyorum.'}):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                general.paragraph(raw, 0)
        view = json.dumps(general.model_view(), ensure_ascii=False)
        self.assertNotIn('THF', view)
        self.assertNotIn('Synthetic fund', view)
        self.assertEqual({tool['name'] for tool in general_chat.tools_for(general)}, {'get_case_status', 'request_investigation'})
        self.assertIn('search_funds', {tool['name'] for tool in general_chat.tools_for(replace(general, scope='live'))})

    def test_chat_body_accepts_general_threads_and_page_context(self):
        body = chat.ChatBody.model_validate({'fund_code': None, 'question': 'Ekip ne yapıyor?', 'thread_id': None,
                                             'page_context': {'path': '/', 'fund_code': None}})
        self.assertIsNone(body.fund_code)
        self.assertEqual(chat.page_of(body), 'home')
        self.assertEqual(chat.page_of(chat.ChatBody(fund_code='THF', question='Soru')), 'fund_detail')
        with self.assertRaises(ValueError):
            chat.ChatBody.model_validate({'question': 'Soru', 'page_context': {'path': '/', 'scope': 'live'}})
        with self.assertRaises(ValueError):
            chat.ChatBody.model_validate({'question': 'Soru', 'analysis_scope_key': 'live'})
        self.assertEqual(len(TOOLS), 6)
        self.assertEqual(HISTORICAL_TOOLS, {'get_signals', 'get_decision', 'get_case_status', 'request_investigation'})


class ScopeAndAccessTests(unittest.TestCase):
    def test_analysis_view_survives_streaming_response_iteration(self):
        application = FastAPI()

        @application.middleware('http')
        async def view(request, call_next):
            with use_analysis_date('2026-09-12'):
                return await call_next(request)

        @application.get('/stream')
        def stream():
            selected = selection()

            def steps():
                for _ in range(3):
                    yield analysis_scope_key()

            def body():
                for value in chat_routes.scoped(selected, steps()):
                    yield value + '\n'
            return StreamingResponse(body(), media_type='text/plain')

        with TestClient(application) as client:
            lines = client.get('/stream').text.splitlines()
        self.assertEqual(lines, ['asof:2026-09-12'] * 3)

    def test_every_agent_route_requires_a_session(self):
        with TestClient(create_app(), base_url='http://localhost') as client:
            for method, path in (('get', '/agents/team'), ('get', '/agents/queue'), ('get', f'/agents/cases/{uuid4()}'),
                                 ('get', '/agents/workspace/reporter'), ('post', '/agents/page-visit'),
                                 ('post', '/agents/requests')):
                with self.subTest(path=path):
                    self.assertEqual(getattr(client, method)(path).status_code, 401)


if __name__ == '__main__':
    unittest.main()
