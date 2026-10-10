"""The selected research date is a browser preference, never the system clock."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from p50k.product.analysis_context import COOKIE, public_context, use_analysis_date, validate_date
from p50k.product.auth import require_session
from p50k.product.analysis_jobs import analysis_status,enqueue_analysis

router=APIRouter(tags=['Analysis date'])


class ContextBody(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    date: str=Field(min_length=4,max_length=10)


@router.get('/context')
def context(request: Request):
    settings=request.app.state.product_settings
    data=public_context(settings)
    try:data['analysis_status']=analysis_status(settings)
    except Exception:data['analysis_status']='unavailable'
    return data


@router.post('/context',dependencies=[Depends(require_session)])
def set_context(body: ContextBody,request: Request,response: Response):
    try:
        selected=validate_date(body.date)
    except ValueError:
        raise HTTPException(422,'ANALYSIS_DATE_OUT_OF_RANGE') from None
    try:state=enqueue_analysis(request.app.state.product_settings,selected)
    except ValueError as error:raise HTTPException(409,str(error)) from None
    response.set_cookie(COOKIE,selected,httponly=True,samesite='lax',secure=request.app.state.product_settings.cookie_secure,
                        max_age=30*24*60*60,path='/')
    with use_analysis_date(selected):
        return {**public_context(request.app.state.product_settings),'analysis_status':state}
