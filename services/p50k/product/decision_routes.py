"""Analysts review proposals; viewers read effective decisions."""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal
from p50k.product.auth import Principal, require_analyst, require_session
from p50k.product.ai_client import AIConfig, AIUnavailable
from p50k.product.decisions import build_packet, decision_rows, review
from p50k.product.queue import enqueue

router=APIRouter(dependencies=[Depends(require_session)],tags=['Decisions'])
class ReviewBody(BaseModel):
    model_config=ConfigDict(extra='forbid')
    action: Literal['ACCEPT','OVERRIDE','REJECT']
    override_value: Literal['MATERIAL','NOT_MATERIAL','DATA_ISSUE','INSUFFICIENT_EVIDENCE'] | None=None
    reason: str | None=Field(default=None,max_length=1000)

@router.get('/decisions')
def decisions(request: Request, fund_code: str | None=Query(default=None,pattern=r'^[A-Z0-9]{2,12}$')):
    return {'items':decision_rows(request.app.state.product_settings,fund_code)}

@router.get('/review')
def queue(request: Request, _: Principal=Depends(require_analyst)):
    return {'items':decision_rows(request.app.state.product_settings,review_only=True)}

@router.post('/funds/{code}/evaluate',status_code=202)
def reevaluate(code: str, request: Request, _: Principal=Depends(require_analyst)):
    if AIConfig.from_env().mode=='off':
        raise HTTPException(503,'AI_OFF')
    try:
        _,_,digest=build_packet(request.app.state.product_settings,code)
        return {'job_id':enqueue(request.app.state.product_settings,code,digest)}
    except ValueError:
        raise HTTPException(404,'FUND_NOT_FOUND') from None
    except AIUnavailable as error:
        # No complete run of the selected day is available yet; nothing is queued.
        raise HTTPException(409,str(error)) from None

@router.post('/decisions/{decision_id}/reviews')
def submit(decision_id: int, body: ReviewBody, request: Request, actor: Principal=Depends(require_analyst)):
    try:
        return {'review_id':review(request.app.state.product_settings,decision_id,actor.user_id,body.action,body.override_value,body.reason)}
    except ValueError as error:
        raise HTTPException(422,str(error)) from None
