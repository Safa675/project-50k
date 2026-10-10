"""Authenticated JSON POST/SSE with session CSRF; no raw token stream."""
from __future__ import annotations
import json
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import StreamingResponse
from p50k.product.auth import Principal, require_session
from p50k.product.ai_client import AIConfig, AIUnavailable
from p50k.product.chat import ChatBody, begin_turn, check_mode, check_question, events, history
from p50k.product.chat_tools import load_context

router = APIRouter(tags=['chat'])


def chat_error(error: AIUnavailable) -> HTTPException:
    code = str(error)
    status = 404 if code in {'THREAD_NOT_FOUND','FUND_NOT_FOUND'} else 429 if code=='CHAT_DAILY_LIMIT' else 409 if code=='THREAD_BUSY' else 422 if code=='QUESTION_REJECTED' else 503
    return HTTPException(status, code)


@router.post('/chat')
def chat(body: ChatBody, request: Request, actor: Principal=Depends(require_session)):
    settings = request.app.state.product_settings
    config = AIConfig.from_env()
    try:
        body.question = check_question(body.question, body.fund_code)
        check_mode(settings, config)
        context = load_context(settings, body.fund_code, body.evidence_id)
        thread, turn, previous = begin_turn(settings, actor.user_id, body, context)
    except AIUnavailable as error:
        raise chat_error(error) from None
    def stream():
        for name, value in events(settings, config, body, context, thread, turn, previous):
            yield f'event: {name}\ndata: {json.dumps(value,ensure_ascii=False)}\n\n'
    return StreamingResponse(stream(), media_type='text/event-stream', headers={'Cache-Control':'no-store','X-Accel-Buffering':'no'})


@router.get('/chat/{thread_id}')
def messages(thread_id: str, request: Request, fund_code: str=Query(pattern=r'^[A-Z0-9]{2,12}$'), actor: Principal=Depends(require_session)):
    try:
        return {'thread_id':thread_id, 'items':history(request.app.state.product_settings, actor.user_id, thread_id, fund_code)}
    except AIUnavailable as error:
        raise chat_error(error) from None
