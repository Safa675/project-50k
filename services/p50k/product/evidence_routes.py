"""Bounded source detail, current catalog filters and owner-scoped feedback."""
from __future__ import annotations

from datetime import datetime
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from psycopg.rows import dict_row

from p50k.product.analysis_context import run_day, run_origins
from p50k.product.archive import ISTANBUL
from p50k.product.auth import Principal, require_session
from p50k.product.db import connect
from p50k.product.models import Fund, Signal
from p50k.product.queries import FundQueries, decimal_text, evidence_values, source_reference
from p50k.product.routes import Code, Cutoff, Reader, resolve_cutoff

router = APIRouter(dependencies=[Depends(require_session)],tags=['Evidence detail'])


def evidence_detail(reader: FundQueries, evidence_id: str, actor: str, cutoff: datetime) -> dict | None:
    # Only evidence of the selected analysis is visible: live runs in the live view,
    # and in a retrospective view only the run of the cutoff's own day.
    origins=run_origins(database=getattr(getattr(reader.connection,'info',None),'dbname',None) or 'unknown')
    day=run_day(cutoff)
    rows = reader._rows("""SELECT signal.fund_code,signal.detector_id,input.version_id,
        signal.run_id,signal.state,signal.reason,signal.value,signal.threshold,signal.evidence_id,
        signal.as_of,item.effective_date,item.origin,item.values,item.thresholds,item.unit,
        item.available_at,item.source_references,COALESCE((item.metadata->>'is_attribute')::boolean,false) is_attribute
        FROM det.signals signal JOIN det.evidence_items item USING(evidence_id)
        JOIN det.detector_runs run ON run.run_id=signal.run_id
        JOIN det.run_inputs input ON input.run_id=run.run_id
        WHERE signal.evidence_id=%s AND input.complete AND run.cutoff<=%s AND run.origin=ANY(%s)
          AND (%s::date IS NULL OR (run.cutoff AT TIME ZONE 'Europe/Istanbul')::date=%s::date)
          AND signal.as_of<=%s AND (item.effective_date IS NULL OR item.effective_date<=%s)
          AND (item.available_at<=%s OR (item.available_at IS NULL AND signal.state='ABSTAINED'))
        LIMIT 1""",(evidence_id,cutoff,origins,day,day,cutoff.astimezone(ISTANBUL).date(),cutoff.astimezone(ISTANBUL).date(),cutoff))
    if not rows:
        return None
    row=rows[0]
    row['run_id']=str(row['run_id'])
    row['value']=decimal_text(row['value']);row['threshold']=decimal_text(row['threshold'])
    row['values']=evidence_values(row['values']);row['thresholds']=evidence_values(row['thresholds'])
    row['source_references']=[source_reference(item) for item in row['source_references']]
    signal=Signal(**row)
    fund=reader.fund(signal.fund_code)
    # "Current" means the run the evidence lists of this same selection would show.
    latest=reader.connection.execute("""SELECT run.run_id FROM det.detector_runs run
        JOIN det.run_inputs input USING(run_id) WHERE input.complete AND run.origin=ANY(%s) AND run.cutoff<=%s
          AND (%s::date IS NULL OR (run.cutoff AT TIME ZONE 'Europe/Istanbul')::date=%s::date)
        ORDER BY run.cutoff DESC,run.created_at DESC,run.run_id DESC LIMIT 1""",(origins,cutoff,day,day)).fetchone()
    feedback=reader.connection.execute('SELECT helpful FROM b2b.evidence_feedback WHERE user_id=%s AND evidence_id=%s ORDER BY feedback_id DESC LIMIT 1',(actor,evidence_id)).fetchone()
    return {'fund':fund,'signal':signal,'cutoff':cutoff,'is_current':bool(latest and str(latest[0])==signal.run_id),
            'helpful':feedback[0] if feedback else None,'development_result':True,'rights_status':'UNREVIEWED'}


@router.get('/evidence')
def detail(reader: Reader, actor: Principal=Depends(require_session),
           evidence_id: str=Query(min_length=1,max_length=100), cutoff: Cutoff=None):
    result=evidence_detail(reader,evidence_id,actor.user_id,resolve_cutoff(cutoff))
    if result is None:raise HTTPException(404,'EVIDENCE_NOT_FOUND')
    return result


@router.get('/fund-categories')
def categories(reader: Reader):
    rows=reader.connection.execute("SELECT DISTINCT category FROM ref.funds WHERE category IS NOT NULL AND btrim(category)<>'' ORDER BY category LIMIT 100").fetchall()
    return {'items':[row[0] for row in rows],'metadata_current_only':True}


@router.get('/funds/{fund_code}/documents')
def documents(fund_code: Code, reader: Reader, limit: Annotated[int,Query(ge=1,le=50)]=20,cutoff: Cutoff=None):
    resolved=resolve_cutoff(cutoff)
    if reader.fund(fund_code) is None:raise HTTPException(404,'FUND_NOT_FOUND')
    statement="""WITH selected AS (SELECT DISTINCT ON(document_key) document_key,report_period,published_at,
        available_at,source_sha256,relative_path,metadata FROM obs.kap_documents
        WHERE fund_code=%s AND (published_at IS NULL OR published_at<=%s)
        AND (available_at<=%s OR (available_at IS NULL AND COALESCE(observed_at,ingested_at)<=%s))
        ORDER BY document_key,available_at DESC NULLS LAST,observed_at DESC,source_sha256 DESC) """
    args=(fund_code,resolved,resolved,resolved)
    total=reader.connection.execute(statement+'SELECT count(*) FROM selected',args).fetchone()[0]
    rows=reader._rows(statement+'SELECT * FROM selected ORDER BY published_at DESC NULLS LAST,document_key LIMIT %s',args+(limit,))
    result=[]
    for row in rows:
        metadata=row.pop('metadata');index=metadata.get('disclosure_index')
        source_url=f'https://www.kap.org.tr/tr/Bildirim/{index}' if type(index) is int and index>0 else None
        row['source_url']=source_url
        row['has_local_document']=bool(row.pop('relative_path'))
        result.append(row)
    return {'items':result,'total':total,'cutoff':resolved,'rights_status':'UNREVIEWED'}


class FeedbackBody(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    evidence_id: str=Field(min_length=1,max_length=100)
    helpful: bool


@router.post('/evidence-feedback')
def feedback(body: FeedbackBody,request: Request,actor: Principal=Depends(require_session)):
    with connect(request.app.state.product_settings) as connection:
        connection.execute("SET LOCAL statement_timeout='5s'")
        if evidence_detail(FundQueries(connection),body.evidence_id,actor.user_id,resolve_cutoff(None)) is None:
            raise HTTPException(404,'EVIDENCE_NOT_FOUND')
        row=connection.execute('INSERT INTO b2b.evidence_feedback(user_id,evidence_id,helpful) VALUES (%s,%s,%s) RETURNING feedback_id',(actor.user_id,body.evidence_id,body.helpful)).fetchone()
    return {'feedback_id':row[0],'helpful':body.helpful}
