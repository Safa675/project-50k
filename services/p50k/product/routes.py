"""Fund routes protected by one fail-closed session dependency.

Phase 2 registers these routes behind the application's default-deny middleware.
Phase 3 supplies real session validation; dependency overrides are test-only.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
import logging
from typing import Annotated, Literal

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import AwareDatetime

from p50k.product.archive import ISTANBUL
from p50k.product.db import connect
from p50k.product.models import EventsPage, FundDetail, FundsPage, SignalsPage
from p50k.product.queries import FundQueries, coverage_for


async def require_session() -> None:
    """Authentication must exist before any real-data route becomes accessible."""
    raise HTTPException(status_code=401, detail="AUTHENTICATION_REQUIRED")


def get_queries(request: Request) -> Iterator[FundQueries]:
    settings = request.app.state.product_settings
    try:
        with connect(settings) as connection:
            connection.execute("SET TRANSACTION READ ONLY")
            connection.execute("SET LOCAL statement_timeout = '5s'")
            yield FundQueries(connection)
    except psycopg.Error as error:
        logging.getLogger(__name__).warning("fund_query_unavailable", extra={"error_class": type(error).__name__})
        raise HTTPException(status_code=503, detail="DATA_UNAVAILABLE") from None


def resolve_cutoff(cutoff: datetime | None) -> datetime:
    now = datetime.now(timezone.utc)
    if cutoff is None:
        return now
    if cutoff.tzinfo is None or cutoff.utcoffset() is None:
        raise HTTPException(status_code=422, detail="CUTOFF_REQUIRES_TIMEZONE")
    if cutoff > now:
        raise HTTPException(status_code=422, detail="FUTURE_CUTOFF_REJECTED")
    return cutoff.astimezone(timezone.utc)


Reader = Annotated[FundQueries, Depends(get_queries)]
Code = Annotated[str, Path(pattern=r"^[A-Z0-9]{2,12}$")]
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0, le=10000)]
SignalsOffset = Annotated[int, Query(ge=0, le=50000)]
Cutoff = Annotated[AwareDatetime | None, Query(description="Observation availability cutoff with explicit timezone; catalog metadata remains current.")]
router = APIRouter(dependencies=[Depends(require_session)])


@router.get("/funds", response_model=FundsPage, tags=["Funds"])
def list_funds(reader: Reader, q: Annotated[str, Query(max_length=80)] = "",
               limit: Limit = 25, offset: Offset = 0) -> FundsPage:
    """Search the downloaded fund catalog; category and status are current metadata."""
    return reader.funds(q.strip(), limit, offset)


@router.get("/funds/{fund_code}", response_model=FundDetail, tags=["Funds"])
def fund_detail(fund_code: Code, reader: Reader,
                days: Annotated[int, Query(ge=1, le=731)] = 365,
                cutoff: Cutoff = None) -> FundDetail:
    """Published daily NAV, development detector evidence, and regulatory review timeline.

Null observed NAV remains null. Absent dates are absent observations. A candidate
event is under review and cannot trigger a confirmed regulatory signal.
"""
    resolved = resolve_cutoff(cutoff)
    fund = reader.fund(fund_code)
    if fund is None:
        raise HTTPException(status_code=404, detail="FUND_NOT_FOUND")
    as_of = resolved.astimezone(ISTANBUL).date()
    chart = reader.chart(fund_code, as_of - timedelta(days=days - 1), as_of, resolved)
    signals = reader.signals(fund_code, None, as_of, resolved, 100, 0).items
    events = reader.events(fund_code, as_of, resolved, 100, 0)
    return FundDetail(fund=fund, chart=chart, signals=signals, coverage=coverage_for(signals),
                      events=events.items, events_total=events.total, cutoff=resolved)


@router.get("/signals", response_model=SignalsPage, tags=["Evidence"])
def list_signals(reader: Reader,
                 fund_code: Annotated[str | None, Query(pattern=r"^[A-Z0-9]{2,12}$")] = None,
                 state: Annotated[Literal["TRIGGERED", "NOT_TRIGGERED", "ABSTAINED"] | None, Query()] = None,
                 cutoff: Cutoff = None, limit: Limit = 25, offset: SignalsOffset = 0) -> SignalsPage:
    """Latest complete DELAYED detector run; every figure is a development result."""
    resolved = resolve_cutoff(cutoff)
    return reader.signals(fund_code, state, resolved.astimezone(ISTANBUL).date(), resolved, limit, offset)


@router.get("/events", response_model=EventsPage, tags=["Evidence"])
def list_events(reader: Reader,
                fund_code: Annotated[str | None, Query(pattern=r"^[A-Z0-9]{2,12}$")] = None,
                cutoff: Cutoff = None, limit: Limit = 25, offset: Offset = 0) -> EventsPage:
    """Private regulatory timeline, with candidates explicitly under review."""
    resolved = resolve_cutoff(cutoff)
    return reader.events(fund_code, resolved.astimezone(ISTANBUL).date(), resolved, limit, offset)


@router.get("/openapi.json", include_in_schema=False, response_class=JSONResponse)
async def openapi_document(request: Request):
    return request.app.openapi()


@router.get("/docs", include_in_schema=False, response_class=HTMLResponse)
async def documentation():
    return get_swagger_ui_html(openapi_url="/openapi.json", title="BlackSwan API")
