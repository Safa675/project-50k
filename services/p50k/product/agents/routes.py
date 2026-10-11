"""Agent team API (DEC-035). Every route needs a session; the app middleware checks CSRF on POST.

The analysis view always comes from the server-side request context (the date cookie
the middleware applied); request bodies cannot name a scope or another user.
"""
from __future__ import annotations

import logging
from typing import Literal

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from p50k.product.agents import control, service
from p50k.product.agents.vocabulary import ROLES
from p50k.product.analysis_context import analysis_scope_key
from p50k.product.auth import Principal, require_admin, require_session

router = APIRouter(prefix='/agents', tags=['agents'])
logger = logging.getLogger(__name__)


class PageVisitBody(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    path: str = Field(min_length=1, max_length=300, pattern=r'^/[^\s]*$')
    fund_code: str | None = Field(default=None, pattern=r'^[A-Z0-9]{2,12}$')


class RequestBody(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    fund_code: str = Field(pattern=r'^[A-Z0-9]{2,12}$')
    kind: Literal['investigate']


class ControlBody(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    action: Literal['PAUSE', 'RESUME']


def context(request: Request) -> tuple:
    settings = request.app.state.product_settings
    return settings, analysis_scope_key(settings)


def unavailable(error: Exception) -> HTTPException:
    logger.warning('agents_unavailable', extra={'error_class': type(error).__name__})
    return HTTPException(503, 'AGENTS_UNAVAILABLE')


@router.get('/team')
def team(request: Request, actor: Principal = Depends(require_session)):
    settings, scope = context(request)
    try:
        return service.team(settings, scope)
    except psycopg.Error as error:
        raise unavailable(error) from None


@router.post('/control')
def team_control(body: ControlBody, request: Request, actor: Principal = Depends(require_admin)):
    settings, _ = context(request)
    try:
        return control.set_state(settings, actor.user_id, actor.role, body.action)
    except psycopg.Error as error:
        raise unavailable(error) from None


@router.get('/queue')
def queue(request: Request, limit: int = Query(default=30, ge=1, le=100), actor: Principal = Depends(require_session)):
    settings, scope = context(request)
    try:
        return service.queue(settings, scope, limit)
    except psycopg.Error as error:
        raise unavailable(error) from None


@router.get('/cases/{case_id}')
def case(case_id: str, request: Request, actor: Principal = Depends(require_session)):
    settings, scope = context(request)
    try:
        detail = service.case_detail(settings, scope, case_id)
    except psycopg.Error as error:
        raise unavailable(error) from None
    if detail is None:
        raise HTTPException(404, 'CASE_NOT_FOUND')
    return detail


@router.get('/workspace/{role}')
def workspace(role: str, request: Request, limit: int = Query(default=20, ge=1, le=50),
              actor: Principal = Depends(require_session)):
    if role not in ROLES:
        raise HTTPException(404, 'ROLE_NOT_FOUND')
    settings, scope = context(request)
    try:
        return service.workspace(settings, scope, role, limit)
    except psycopg.Error as error:
        raise unavailable(error) from None


@router.get('/funds/{fund_code}/summary')
def fund_summary(fund_code: str, request: Request, actor: Principal = Depends(require_session)):
    """The fund page's top summary for the request's view; read-only, nothing goes to a model."""
    settings, scope = context(request)
    try:
        summary = service.fund_summary(settings, scope, fund_code)
    except psycopg.Error as error:
        raise unavailable(error) from None
    if summary is None:
        raise HTTPException(404, 'FUND_NOT_FOUND')
    return summary


@router.post('/page-visit')
def page_visit(body: PageVisitBody, request: Request, actor: Principal = Depends(require_session)):
    settings, scope = context(request)
    try:
        return service.page_visit(settings, scope, actor.user_id, body.path, body.fund_code)
    except psycopg.Error as error:
        raise unavailable(error) from None


@router.post('/requests')
def investigation(body: RequestBody, request: Request, actor: Principal = Depends(require_session)):
    settings, scope = context(request)
    try:
        return service.request_investigation(settings, scope, actor.user_id, body.fund_code)
    except service.AgentRequestError as error:
        raise HTTPException(error.status, error.code) from None
    except psycopg.Error as error:
        raise unavailable(error) from None
