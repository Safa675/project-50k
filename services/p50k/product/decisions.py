"""Append-only materiality proposals, immutable packets and human review."""
from __future__ import annotations
import hashlib
from typing import Any
from uuid import uuid4
from psycopg.types.json import Jsonb
from p50k.product.ai_client import AIConfig, AIUnavailable, decide
from p50k.product.archive import canonical_json
from p50k.product.db import connect
from p50k.product.egress import Evidence, Packet, allowed_options
from p50k.product.settings import Settings
from p50k.product.validator import validate_output, render

PROMPT_VERSION='materiality-v1'
SCHEMA_VERSION='decision-v1'

def build_packet(settings: Settings, code: str) -> tuple[Packet,int,str]:
    with connect(settings) as connection:
        fund=connection.execute('SELECT name,category FROM ref.funds WHERE fund_code=%s',(code,)).fetchone()
        if not fund:
            raise ValueError('FUND_NOT_FOUND')
        run=connection.execute("SELECT run.run_id,input.as_of,run.origin,run.cutoff FROM det.detector_runs run JOIN det.run_inputs input USING(run_id) WHERE run.origin IN ('DELAYED','SYNTHETIC') AND input.complete ORDER BY run.created_at DESC,run.run_id DESC LIMIT 1").fetchone()
        if not run:
            raise AIUnavailable('EVIDENCE_UNAVAILABLE')
        rows=connection.execute('SELECT item.evidence_id,item.detector_id,item.state,signal.value,signal.threshold,item.effective_date,item.metadata FROM det.signals signal JOIN det.evidence_items item USING(evidence_id) WHERE signal.run_id=%s AND signal.fund_code=%s ORDER BY signal.detector_id',(run[0],code)).fetchall()
        items=[Evidence(evidence_id=row[0],detector_id=row[1],state=row[2],value=str(row[3]) if row[3] is not None else None,
            threshold=str(row[4]) if row[4] is not None else None,effective_date=row[5].isoformat() if row[5] else None,is_attribute=bool(row[6].get('is_attribute'))) for row in rows]
        if not items:
            raise AIUnavailable('EVIDENCE_UNAVAILABLE')
        packet=Packet(fund_code=code,fund_name=fund[0],category=fund[1],as_of=run[1].isoformat(),evidence=items,allowed_options=allowed_options(items))
        payload={**packet.model_dump(),'run_id':str(run[0]),'origin':run[2],'cutoff':run[3].isoformat()}
        digest=hashlib.sha256(canonical_json(payload).encode()).hexdigest()
        connection.execute("INSERT INTO ai.packets(fund_code,packet_sha256,origin,as_of,cutoff,payload,allowed_options) VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            (code,digest,run[2],run[1],None if run[2]=='DELAYED' else run[3],Jsonb(payload),Jsonb(packet.allowed_options)))
        packet_id=connection.execute('SELECT packet_id FROM ai.packets WHERE fund_code=%s AND packet_sha256=%s',(code,digest)).fetchone()[0]
        return packet,packet_id,digest

def evaluate(settings: Settings, code: str, config: AIConfig | None=None) -> dict[str,Any]:
    config=config or AIConfig.from_env()
    if config.mode=='mock' and settings.db_name!='p50k_dev':
        raise AIUnavailable('MOCK_DATABASE_REJECTED')
    packet,packet_id,digest=build_packet(settings,code)
    with connect(settings) as connection:
        existing=connection.execute("SELECT decision_id,validation_state FROM ai.decisions WHERE packet_id=%s AND ai_mode=%s AND model_id=%s AND prompt_version=%s AND schema_version=%s AND effort=%s ORDER BY decision_id DESC LIMIT 1",
            (packet_id,config.mode,config.model if config.mode=='live' else 'synthetic' if config.mode=='mock' else 'deterministic',PROMPT_VERSION,SCHEMA_VERSION,config.effort if config.mode!='off' else 'none')).fetchone()
        if existing:
            return {'decision_id':existing[0],'cached':existing[1]=='VALID','blocked':existing[1]=='INVALID','validation_state':existing[1]}
    if config.mode=='off' and packet.allowed_options!=['INSUFFICIENT_EVIDENCE']:
        raise AIUnavailable('AI_OFF')
    call_id,model,mode,valid='deterministic:'+uuid4().hex,'deterministic','off',None
    for attempt in range(2):
        try:
            if packet.allowed_options==['INSUFFICIENT_EVIDENCE']:
                raw={'decision':'INSUFFICIENT_EVIDENCE','cited_evidence_ids':[packet.evidence[0].evidence_id],
                     'rationale_tr':'Mevcut detektörler değerlendirme için yeterli kanıt sağlamıyor.','missing_evidence_tr':'Uygun geçmiş ve kaynak kapsamı gerekli.'}
            else:
                raw,call_id,model=decide(settings,config,packet)
                mode=config.mode
            valid=validate_output(raw,packet)
            break
        except AIUnavailable as error:
            if str(error)=='MODEL_CALL_FAILED':
                model=config.model if config.mode=='live' else 'synthetic'
                mode=config.mode
                call_id=error.call_id or 'failed:'+uuid4().hex
                break
            if str(error) in {'BUDGET_UNAVAILABLE','TUNING_CALL_LIMIT'}:
                model,mode,call_id='budget-gate','off','gate:'+uuid4().hex
                break
            raise
        except Exception:
            if attempt==1:
                valid=None
    with connect(settings) as connection:
        decision_id=connection.execute("""INSERT INTO ai.decisions
            (packet_id,fund_code,packet_sha256,decision_value,validation_state,evidence_ids,rationale,output,model_id,prompt_version,schema_version,ai_mode,call_id,effort)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING decision_id""",
            (packet_id,code,digest,valid.decision if valid else None,'VALID' if valid else 'INVALID',
             Jsonb(valid.cited_evidence_ids if valid else []),valid.rationale_tr if valid else None,
             Jsonb(valid.model_dump()) if valid else None,model,PROMPT_VERSION,SCHEMA_VERSION,mode,call_id,config.effort if mode!='off' else 'none')).fetchone()[0]
    return {'decision_id':decision_id,'cached':False,'validation_state':'VALID' if valid else 'INVALID'}

def decision_rows(settings: Settings, code: str | None=None, review_only: bool=False) -> list[dict[str,Any]]:
    with connect(settings) as connection:
        rows=connection.execute("""SELECT effective.fund_code,effective.packet_sha256,effective.decision_id,
            effective.effective_value,effective.effective_source,effective.review_id,effective.has_current_review,
            effective.stale_review_exists,decision.validation_state,decision.rationale,packet.payload,packet.allowed_options,decision.model_id,
            decision.decision_value,actual_review.reason,actual_review.created_at,reviewer.email,decision.ai_mode
            FROM (SELECT DISTINCT ON (value.fund_code) value.* FROM ai.effective_decisions value
                JOIN ai.packets current_packet USING(packet_id)
                WHERE value.origin IN ('DELAYED','SYNTHETIC')
                ORDER BY value.fund_code,current_packet.created_at DESC,current_packet.packet_id DESC) effective
            JOIN ai.packets packet USING(packet_id)
            LEFT JOIN ai.decisions decision ON decision.decision_id=effective.decision_id
            LEFT JOIN ai.decision_reviews actual_review ON actual_review.review_id=effective.review_id
            LEFT JOIN auth.users reviewer ON reviewer.user_id=actual_review.reviewer_id
            WHERE (%s::text IS NULL OR effective.fund_code=%s) AND (%s=false OR NOT effective.has_current_review)
              AND packet.origin IN ('DELAYED','SYNTHETIC') ORDER BY effective.fund_code LIMIT 100""",(code,code,review_only)).fetchall()
    results=[]
    for row in rows:
        packet=Packet.model_validate({key:row[10][key] for key in Packet.model_fields})
        results.append({'fund_code':row[0],'packet_sha256':row[1],'decision_id':row[2],
            'effective_value':row[3],'decided_by':'DETERMINISTIC' if row[4]!='HUMAN' and row[12]=='deterministic' else row[4],'review_id':row[5],'has_current_review':row[6],
            'stale_review_exists':row[7],'validation_state':row[8],
            'rationale_tr':render(row[9],packet) if row[9] else 'Yapay zekâ önerisi üretilemedi; insan incelemesi gerekli',
            'allowed_options':row[11],'evidence_ids':[item.evidence_id for item in packet.evidence],
            'original_value':row[13],'review_reason':row[14],'reviewed_at':row[15].isoformat() if row[15] else None,
            'reviewer_email':row[16],'ai_mode':row[17]})
    return results

def review(settings: Settings, decision_id: int, actor: str, action: str, override: str | None, reason: str | None) -> int:
    if action not in {'ACCEPT','OVERRIDE','REJECT'} or (action!='ACCEPT' and not (reason and reason.strip())):
        raise ValueError('REVIEW_REASON_REQUIRED')
    with connect(settings) as connection:
        row=connection.execute('SELECT decision.packet_sha256,packet.allowed_options,decision.validation_state FROM ai.decisions decision JOIN ai.packets packet USING(packet_id) WHERE decision_id=%s',(decision_id,)).fetchone()
        if not row or (action=='OVERRIDE' and override not in row[1]) or (action=='ACCEPT' and row[2]!='VALID'):
            raise ValueError('REVIEW_NOT_ALLOWED')
        return connection.execute('INSERT INTO ai.decision_reviews(decision_id,packet_sha256,action,override_value,reason,reviewer_id) VALUES (%s,%s,%s,%s,%s,%s) RETURNING review_id',
            (decision_id,row[0],action,override if action=='OVERRIDE' else None,reason,actor)).fetchone()[0]
