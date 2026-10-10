"""Session-scoped watchlist endpoints; the application enforces mutation CSRF."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from pydantic import BaseModel, ConfigDict, Field, StrictBool

from p50k.product.auth import Principal, require_session
from p50k.product import watchlists

router = APIRouter(tags=["Watchlist"])
FundCode = Annotated[str, Path(pattern=r"^[A-Z0-9]{2,16}$")]
EvidenceId = Annotated[str, Field(min_length=1, max_length=200, pattern=r"^[A-Za-z0-9_.:-]+$")]


class ReadBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_ids: list[EvidenceId] = Field(min_length=1, max_length=800)


class PreferenceBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: StrictBool


def _call(function, *args, **kwargs):
    try:
        return function(*args, **kwargs)
    except watchlists.WatchlistError as error:
        raise HTTPException(error.status, error.code) from None


@router.get("/watchlist")
def list_saved(request: Request, principal: Principal = Depends(require_session)):
    return watchlists.watchlist(request.app.state.product_settings, principal.user_id)


@router.post("/watchlist/{code}")
def save(code: FundCode, request: Request, principal: Principal = Depends(require_session)):
    return _call(watchlists.save_fund, request.app.state.product_settings, principal.user_id, code)


@router.delete("/watchlist/{code}")
def remove(code: FundCode, request: Request, principal: Principal = Depends(require_session)):
    return _call(watchlists.remove_fund, request.app.state.product_settings, principal.user_id, code)


@router.get("/notifications")
def list_notifications(request: Request, unread_only: bool = False,
                       limit: int = Query(100, ge=1, le=100), offset: int = Query(0, ge=0, le=800),
                       principal: Principal = Depends(require_session)):
    return watchlists.notifications(request.app.state.product_settings, principal.user_id,
                                   unread_only=unread_only, limit=limit, offset=offset)


@router.post("/notifications/read")
def read(body: ReadBody, request: Request, principal: Principal = Depends(require_session)):
    return _call(watchlists.mark_read, request.app.state.product_settings, principal.user_id, body.evidence_ids)


@router.post("/notifications/preferences")
def preferences(body: PreferenceBody, request: Request, principal: Principal = Depends(require_session)):
    return watchlists.set_notifications(request.app.state.product_settings, principal.user_id, body.enabled)


@router.post("/notifications/read-all")
def read_all(request: Request, principal: Principal = Depends(require_session)):
    settings = request.app.state.product_settings
    current = watchlists.watchlist(settings, principal.user_id)
    return _call(watchlists.mark_read, settings, principal.user_id,
                 [item["evidence_id"] for item in current["signals"]])
