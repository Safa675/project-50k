"""Authenticated POST/SSE: validated paragraphs stream before the final answer."""
from __future__ import annotations
from dataclasses import replace
import json
import logging
import psycopg
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import StreamingResponse
from p50k.product.auth import Principal, require_session
from p50k.product.ai_client import AIConfig, AIUnavailable
from p50k.product.chat import ChatBody, begin_turn, check_mode, check_question, events, history, page_of, thread_list
from p50k.product.analysis_context import analysis_scope_key, selection, use_analysis_date
from p50k.product.chat_tools import ChatContext, load_context

router = APIRouter(tags=['chat'])


def chat_error(error: AIUnavailable) -> HTTPException:
    code = str(error)
    status = 404 if code in {'THREAD_NOT_FOUND','FUND_NOT_FOUND'} else 429 if code=='CHAT_DAILY_LIMIT' else 409 if code=='THREAD_BUSY' else 422 if code=='QUESTION_REJECTED' else 503
    return HTTPException(status, code)


def scoped(selected: str, generated):
    """Run every step of a response generator inside the request's analysis view.

    A StreamingResponse iterates after the middleware returned, possibly in other
    threads and context copies, so the view is re-applied per step instead of
    relying on the request's ContextVar or holding a token across a yield.
    """
    try:
        while True:
            with use_analysis_date(selected):
                try:
                    item = next(generated)
                except StopIteration:
                    return
            yield item
    finally:
        with use_analysis_date(selected):
            generated.close()


def team_case(settings, scope: str, context: ChatContext) -> dict | None:
    """The fund's agent case as number-free model input; absent when the team has no record."""
    try:
        from p50k.product.agents.service import case_status
        return case_status(settings, scope, context.packet.fund_code, context.packet, context.run_id)['case']
    except Exception as error:
        logging.getLogger(__name__).warning('agent_case_unavailable', extra={'error_class': type(error).__name__})
        return None


@router.post('/chat')
def chat(body: ChatBody, request: Request, actor: Principal=Depends(require_session)):
    settings = request.app.state.product_settings
    selected = selection(settings)
    scope = analysis_scope_key(settings)
    try:
        config = AIConfig.from_env()
        body.question = check_question(body.question, body.fund_code)
        check_mode(settings, config)
        if body.fund_code:
            context = load_context(settings, body.fund_code, body.evidence_id)
            context = replace(context, scope=scope, user_id=actor.user_id)
            context = replace(context, team_case=team_case(settings, scope, context))
            thread, turn, previous = begin_turn(settings, actor.user_id, body, context)
            generated = events(settings, config, body, context, thread, turn, previous)
        else:
            if body.evidence_id:
                raise AIUnavailable('QUESTION_REJECTED')
            from p50k.product.agents import general_chat
            try:
                general = general_chat.load_general(settings, scope, actor.user_id, page_of(body))
            except psycopg.Error as error:
                logging.getLogger(__name__).warning('general_chat_unavailable', extra={'error_class': type(error).__name__})
                raise AIUnavailable('CHAT_UNAVAILABLE') from None
            thread, turn, previous = general_chat.begin(settings, actor.user_id, body, general)
            generated = general_chat.events(settings, config, body, general, thread, turn, previous)
    except AIUnavailable as error:
        raise chat_error(error) from None
    def stream():
        yield f'event: thread\ndata: {json.dumps({"thread_id":thread,"analysis_scope_key":scope})}\n\n'
        for name, value in scoped(selected, generated):
            yield f'event: {name}\ndata: {json.dumps(value,ensure_ascii=False)}\n\n'
    return StreamingResponse(stream(), media_type='text/event-stream', headers={'Cache-Control':'no-store','X-Accel-Buffering':'no'})


@router.get('/chat/threads')
def threads(request: Request, fund_code: str|None=Query(default=None,pattern=r'^[A-Z0-9]{2,12}$'),
            limit: int=Query(default=20,ge=1,le=20),offset: int=Query(default=0,ge=0,le=10000),
            actor: Principal=Depends(require_session)):
    return thread_list(request.app.state.product_settings,actor.user_id,fund_code,limit,offset)


@router.get('/chat/{thread_id}')
def messages(thread_id: str, request: Request, fund_code: str|None=Query(default=None,pattern=r'^[A-Z0-9]{2,12}$'),
             before_message_id: int|None=Query(default=None,ge=1,le=9223372036854775807),
             actor: Principal=Depends(require_session)):
    try:
        settings=request.app.state.product_settings
        return {'thread_id':thread_id,'fund_code':fund_code,'analysis_scope_key':analysis_scope_key(settings),
                'items':history(settings, actor.user_id, thread_id, fund_code,before_message_id)}
    except AIUnavailable as error:
        raise chat_error(error) from None
