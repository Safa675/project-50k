"""Session-protected, read-only after-the-fact evaluation of the 12 September scan."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from p50k.product import evaluation
from p50k.product.auth import Principal, require_session
from p50k.product.db import connect

router = APIRouter(tags=["Evaluation"])


@router.get("/evaluation/retrospective")
def retrospective(request: Request, _: Principal = Depends(require_session)):
    from p50k.product.detector_pipeline import VERSION_ID
    settings = request.app.state.product_settings
    with connect(settings) as connection:
        connection.execute("SET TRANSACTION READ ONLY")
        report = evaluation.retrospective(connection, version_id=VERSION_ID,
                                          include_synthetic=settings.db_name == 'p50k_dev')
    if report is None:
        raise HTTPException(404, "RETROSPECTIVE_RUN_MISSING")
    return report


@router.get('/evaluation/kap-scale-experiment')
def kap_scale(request: Request, _: Principal = Depends(require_session)):
    from p50k.product import kap_experiment
    from p50k.product.detector_pipeline import VERSION_ID
    settings = request.app.state.product_settings
    with connect(settings) as connection:
        connection.execute('SET TRANSACTION READ ONLY')
        connection.execute("SET LOCAL statement_timeout='8s'")
        result = kap_experiment.report(connection,version_id=VERSION_ID,include_synthetic=settings.db_name=='p50k_dev')
    if result is None:
        raise HTTPException(404,'RETROSPECTIVE_RUN_MISSING')
    return result
