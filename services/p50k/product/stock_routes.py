"""Authenticated bounded stock catalog and daily close chart endpoints."""
from __future__ import annotations

from collections.abc import Iterator
from datetime import timedelta
import logging
from typing import Annotated

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from pydantic import AwareDatetime

from p50k.product.analysis_context import historical_mode
from p50k.product.archive import ISTANBUL
from p50k.product.auth import require_session
from p50k.product.db import connect
from p50k.product.routes import resolve_cutoff
from p50k.product.stocks import StockDetail, StockQueries, StocksPage


def get_stock_queries(request: Request) -> Iterator[StockQueries]:
    try:
        with connect(request.app.state.product_settings) as connection:
            connection.execute("SET TRANSACTION READ ONLY")
            connection.execute("SET LOCAL statement_timeout='5s'")
            yield StockQueries(connection)
    except psycopg.Error as error:
        logging.getLogger(__name__).warning("stock_query_unavailable",extra={"error_class":type(error).__name__})
        raise HTTPException(503,"DATA_UNAVAILABLE") from None


Reader = Annotated[StockQueries, Depends(get_stock_queries)]
Cutoff = Annotated[AwareDatetime | None, Query(description="Availability cutoff with timezone; dated membership comes only from bulletins available by then.")]
router = APIRouter(dependencies=[Depends(require_session)], tags=["Stocks"])


@router.get("/stocks", response_model=StocksPage)
def list_stocks(reader: Reader, q: Annotated[str, Query(max_length=80)]="",
                limit: Annotated[int, Query(ge=1,le=30)]=30,
                offset: Annotated[int, Query(ge=0,le=30)]=0) -> StocksPage:
    return reader.stocks(q.strip(),limit,offset,resolve_cutoff(None),dated=historical_mode())


@router.get("/stocks/{symbol}", response_model=StockDetail)
def stock_detail(symbol: Annotated[str, Path(pattern=r"^[A-Z][A-Z0-9]{1,11}$")], reader: Reader,
                 days: Annotated[int, Query(ge=1,le=731)]=365, cutoff: Cutoff=None) -> StockDetail:
    resolved = resolve_cutoff(cutoff)
    stock = reader.stock(symbol,resolved)
    if stock is None:
        raise HTTPException(404,"STOCK_NOT_FOUND")
    end = resolved.astimezone(ISTANBUL).date()
    return reader.detail(stock,end-timedelta(days=days-1),end,resolved)
