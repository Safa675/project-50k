"""Reject model numbers, unsupported citations, advice and allegations before display."""
from __future__ import annotations
import re
import unicodedata
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from p50k.product.egress import Packet

class DecisionOutput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    decision: Literal['MATERIAL','NOT_MATERIAL','DATA_ISSUE','INSUFFICIENT_EVIDENCE']
    cited_evidence_ids: list[str] = Field(min_length=1,max_length=8)
    rationale_tr: str = Field(min_length=1,max_length=1600)
    missing_evidence_tr: str = Field(max_length=600)

class InvalidOutput(ValueError):
    pass

def fold(text: str) -> str:
    text = text.replace('İ','i').replace('ı','i').replace('I','i').lower()
    return ''.join(char for char in unicodedata.normalize('NFKD',text) if not unicodedata.combining(char))

BANNED = ('dolandir','manipul','usulsuz','suistimal','hile','kara para','satin al','satmali','almali','tutmali',
    'oneririm','tavsiye','kacinin','uzak dur','tahmin','ongoru','tasfiye edilecek','tasfiye edilebilir','batabilir',
    'guvenli','risksiz','sorun yok','spknin gerekcesi','spknin amaci','dogruluk','isabet','onceden yakala','erken uyari',
    'olaganustu','cok uzerinde','teminat','kapsam','tazminat','hasar','prim','police','sigortali','sigorta ettiren',
    'odenecek','hak kazanir','muafiyet','buy','sell','hold','fraud','manipulat','guarantee')
NUMBER_WORD = re.compile(r'\b(bir|iki|uc|dort|bes|alti|yedi|sekiz|dokuz|on|yirmi|otuz|kirk|elli|altmis|yetmis|seksen|doksan|yuz)\s+(gun|ay|yil|kat|puan|yuzde|bin|milyon|milyar)\w*\b')
PLACEHOLDER = re.compile(r'\{\{ev:([^{}]+)\}\}|\{\{fund\}\}')

def validate_text(text: str, packet: Packet) -> None:
    ids = {item.evidence_id for item in packet.evidence}
    for match in PLACEHOLDER.finditer(text):
        if match.group(1) and match.group(1) not in ids:
            raise InvalidOutput('Unknown placeholder')
    plain = PLACEHOLDER.sub('',text)
    normalized = fold(plain).replace("'",'').replace('’','')
    if re.search(r'\d|\{\{|\}\}',plain) or NUMBER_WORD.search(normalized) or re.search(r'\b(yuzde|bin|milyon|milyar|yari|ceyrek|bucuk)\b',normalized):
        raise InvalidOutput('Model numeric claim')
    if any(word in normalized for word in BANNED):
        raise InvalidOutput('Disallowed wording')

def validate_output(raw: dict, packet: Packet) -> DecisionOutput:
    output = DecisionOutput.model_validate(raw)
    items = {item.evidence_id:item for item in packet.evidence}
    if output.decision not in packet.allowed_options or any(item not in items for item in output.cited_evidence_ids):
        raise InvalidOutput('Decision or citation not allowed')
    if output.decision in {'MATERIAL','DATA_ISSUE'} and not any(items[key].state=='TRIGGERED' and not items[key].is_attribute for key in output.cited_evidence_ids):
        raise InvalidOutput('Triggered evidence citation required')
    for text in (output.rationale_tr,output.missing_evidence_tr):
        validate_text(text,packet)
    return output

def render(text: str, packet: Packet) -> str:
    validate_text(text,packet)
    items = {item.evidence_id:item for item in packet.evidence}
    def replacement(match: re.Match) -> str:
        if not match.group(1):
            return packet.fund_name
        item = items[match.group(1)]
        magnitude = 'eşik aşılmadı' if item.state=='NOT_TRIGGERED' else 'eşik aşıldı' if item.state=='TRIGGERED' else 'kanıt yetersiz'
        return f'{item.detector_id} [değer: {item.value if item.value is not None else "bilinmiyor"}; eşik: {item.threshold if item.threshold is not None else "bilinmiyor"}; {magnitude}]'
    return PLACEHOLDER.sub(replacement,text)
