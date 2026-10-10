"""Incremental checked paragraphs and plain explanations, using synthetic evidence."""
from __future__ import annotations
from dataclasses import replace
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

from p50k.product import chat
from p50k.product.ai_client import AIConfig
from p50k.product.chat_language import evidence_fact, explanations, render_chat
from p50k.product.settings import Settings
from p50k.product.validator import InvalidOutput
from p50k.product.evidence_aliases import model_packet
from tests.unit.test_product_chat import context, streamed_answer, transport


class ChatStreamingTests(TestCase):
    def test_model_aliases_resolve_to_real_audit_ids_and_reject_unknown_refs(self):
        current=context()
        self.assertEqual(model_packet(current.packet).evidence[0].evidence_id,'e1')
        output=chat.paragraph_payload({'text_tr':'{{ev:e1}}','cited_evidence_ids':['e1']},current,0)
        self.assertEqual(output['evidence_ids'],['ev:synthetic'])
        self.assertNotIn('e1',output['content'])
        with self.assertRaises(InvalidOutput):chat.paragraph_payload({'text_tr':'{{ev:e9}}','cited_evidence_ids':['e9']},current,0)
    def test_partial_objects_never_display_and_escaped_braces_are_not_boundaries(self):
        paragraph={'cited_evidence_ids':['ev:synthetic'],'text_tr':'Kaynak {metni} ve "açıklama".'}
        prefix='{"paragraphs":['
        encoded=json.dumps(paragraph,ensure_ascii=False)
        for length in range(len(encoded)):
            self.assertEqual(chat.completed_paragraphs(prefix+encoded[:length]),[])
        self.assertEqual(chat.completed_paragraphs(prefix+encoded+','),[paragraph])
        with self.assertRaises(Exception):chat.completed_paragraphs('x'*24001)

    def test_data_quality_facts_are_human_readable_and_never_zero_price_claims(self):
        current=context().packet
        stale=current.evidence[0].model_copy(update={'detector_id':'AN-DQ-001','value':'4','threshold':'2'})
        missing=stale.model_copy(update={'detector_id':'AN-DQ-002','value':'1','threshold':'1'})
        unavailable=stale.model_copy(update={'detector_id':'AN-FND-005','state':'ABSTAINED','value':None,'threshold':None})
        self.assertIn('4 hafta içi gün',evidence_fact(stale))
        self.assertIn('kullanılabilir bir fiyat bulunmuyor',evidence_fact(missing))
        self.assertNotIn('1',evidence_fact(missing))
        self.assertNotIn('bilinmiyor',evidence_fact(unavailable))
        explained=explanations(current.model_copy(update={'evidence':[missing]}))
        self.assertIn('sıfır',explained[0]['limits_tr'])
        for item in (stale,missing,unavailable):
            rendered=render_chat('{{ev:ev:synthetic}}',current.model_copy(update={'evidence':[item]}))
            self.assertNotIn(item.detector_id,rendered)
            self.assertNotIn('ev:',rendered)

    def test_semantics_are_supplied_without_raw_observations_or_private_metadata(self):
        value=explanations(context().packet)[0]
        self.assertIn('getiri',value['measures_tr'])
        self.assertEqual(set(value),{'evidence_id','name_tr','measures_tr','observed_fact_tr','limits_tr'})
        item=context().packet.evidence[0].model_copy(update={'state':'ABSTAINED'})
        self.assertIn('türü kaynakta belirtilmediği',evidence_fact(item,'CATEGORY_MISSING'))
        self.assertIn('sınırı belirlemeye',evidence_fact(item,'NO_CATEGORY_THRESHOLD'))
        self.assertIn('güncel fiyat veya geçmiş',evidence_fact(item,'CURRENT_INPUT_OR_HISTORY_UNAVAILABLE'))

    def test_model_paragraph_is_available_before_response_completion(self):
        raw=streamed_answer()
        first=json.dumps(raw,ensure_ascii=False)[:-2]
        final=SimpleNamespace(status='completed',id='synthetic-call',usage=SimpleNamespace(input_tokens=10,output_tokens=10))
        source=MagicMock()
        source.__iter__.return_value=iter([SimpleNamespace(type='response.output_text.delta',delta=first),
            SimpleNamespace(type='response.output_text.delta',delta=']}'),SimpleNamespace(type='response.completed',response=final)])
        with TemporaryDirectory() as folder:
            key=Path(folder)/'synthetic-key';key.write_text('synthetic-only',encoding='utf-8')
            with patch.object(chat,'OpenAI') as sdk,patch.object(chat,'reserve',return_value='synthetic-reservation'),patch.object(chat,'settle') as settled,patch.object(chat,'connect'):
                sdk.return_value.responses.create.return_value=source
                generated=chat.model_call(Settings(),AIConfig(mode='live',key_file=key),[],20,context())
                name,value=next(generated)
                self.assertEqual(name,'paragraph')
                self.assertIn('Benzer fonlara göre',value['content'])
                settled.assert_not_called()
                self.assertEqual(list(generated),[])
                settled.assert_called_once()
                source.close.assert_called_once()

    def test_invalid_paragraph_is_withheld_and_open_stream_is_closed(self):
        raw=json.dumps(streamed_answer(text_tr='100 kazandırır.'))
        source=MagicMock();source.__iter__.return_value=iter([SimpleNamespace(type='response.output_text.delta',delta=raw)])
        with TemporaryDirectory() as folder:
            key=Path(folder)/'synthetic-key';key.write_text('synthetic-only',encoding='utf-8')
            with patch.object(chat,'OpenAI') as sdk,patch.object(chat,'reserve',return_value='synthetic-reservation'),patch.object(chat,'settle') as settled:
                sdk.return_value.responses.create.return_value=source
                with self.assertRaises(InvalidOutput):list(chat.model_call(Settings(),AIConfig(mode='live',key_file=key),[],20,context()))
                settled.assert_called_once();source.close.assert_called_once()

    def test_audit_is_saved_before_paragraph_reaches_browser(self):
        raw=streamed_answer();value=chat.paragraph_payload(raw['paragraphs'][0],context(),0)
        reply=SimpleNamespace(id='synthetic',output=[],output_text=json.dumps(raw))
        with patch.object(chat,'model_call',return_value=transport(reply,[('paragraph',value)])),patch.object(chat,'save_chunk') as saved,patch.object(chat,'finish_turn'):
            generated=chat.events(Settings(),AIConfig(mode='live'),chat.ChatBody(fund_code='THF',question='Bu ne anlama geliyor?'),context(),'thread','turn',[])
            self.assertEqual(next(generated),('paragraph',value))
            saved.assert_called_once()
            self.assertEqual([name for name,_ in generated],['answer'])
