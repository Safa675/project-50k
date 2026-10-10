"""Authenticated aggregate workflow read surface; no actions or secret metadata."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone
import logging
from typing import Annotated

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Request

from p50k.product.auth import require_session
from p50k.product.db import connect
from p50k.product.workflow import WorkflowOverview, WorkflowQueries
from p50k.product.analysis_context import current_cutoff


def get_workflow_queries(request: Request) -> Iterator[WorkflowQueries]:
    try:
        with connect(request.app.state.product_settings) as connection:
            connection.execute("SET TRANSACTION READ ONLY")
            connection.execute("SET LOCAL statement_timeout='5s'")
            yield WorkflowQueries(connection)
    except psycopg.Error as error:
        logging.getLogger(__name__).warning("workflow_unavailable", extra={"error_class": type(error).__name__})
        raise HTTPException(503, "DATA_UNAVAILABLE") from None


Reader = Annotated[WorkflowQueries, Depends(get_workflow_queries)]
router = APIRouter(dependencies=[Depends(require_session)], tags=["Workflow"])


@router.get("/workflow", response_model=WorkflowOverview)
def workflow(request: Request, reader: Reader) -> WorkflowOverview:
    """Actual pipeline counts; fund decisions and reviews match the current complete run."""
    return reader.overview(current_cutoff(request.app.state.product_settings), synthetic=request.app.state.product_settings.db_name == "p50k_dev")
