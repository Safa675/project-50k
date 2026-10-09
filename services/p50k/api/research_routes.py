"""Read-only routes over one validated, sealed local research bundle."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import Response

from .models import FundResponse, FundsResponse, HealthResponse, SummaryResponse

router = APIRouter(prefix="/research/v1")


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> dict:
    view = request.app.state.bundle_view()
    return {**view.metadata, "health": {"status": "OK", "record_count": 100}}


@router.get("/summary", response_model=SummaryResponse)
def summary(request: Request) -> dict:
    view = request.app.state.bundle_view()
    return {**view.metadata, "summary": view.summary.model_dump(mode="json")}


@router.get("/funds", response_model=FundsResponse)
def funds(request: Request) -> dict:
    view = request.app.state.bundle_view()
    return {**view.metadata, "funds": [fund.model_dump(mode="json") for fund in view.funds]}


@router.get("/funds/{code}", response_model=FundResponse)
def fund_detail(code: str, request: Request) -> dict:
    # Membership is checked before loading or hashing any financial source.
    if code not in request.app.state.universe_codes:
        raise request.app.state.api_error(404, "NOT_FOUND", "Bu fon araştırma kapsamında bulunmuyor.")
    view = request.app.state.bundle_view()
    fund = next((fund for fund in view.funds if fund.code == code), None)
    if fund is None:
        raise request.app.state.api_error(503, "BUNDLE_INVALID", "Araştırma paketi doğrulanamadı.")
    ids = set(fund.evidence + fund.d1.input_refs + fund.flow.input_refs)
    ids.update(reference.source_id for reference in fund.flow.endpoint_refs)
    if fund.concentration is not None:
        ids.update(fund.concentration.input_refs)
        ids.update(fund.concentration.comparison.input_refs)
        ids.update(row.source_id for position in fund.concentration.positions for row in position.source_rows)
    return {
        **view.metadata,
        "fund": fund.model_dump(mode="json"),
        "sources": [source.model_dump(mode="json") for source in view.sources if source.source_id in ids],
    }


@router.get("/sources/{source_id}")
def source_pdf(source_id: str, request: Request) -> Response:
    if not re.fullmatch(r"[a-f0-9]{64}", source_id):
        raise request.app.state.api_error(404, "NOT_FOUND", "Bu kaynak bulunamadı.")
    view = request.app.state.bundle_view()
    source = next((source for source in view.sources if source.source_id == source_id), None)
    if source is None or not source.pdf_available or source.media_type != "application/pdf":
        raise request.app.state.api_error(404, "NOT_FOUND", "Bu kaynağın PDF dosyası bulunmuyor.")
    try:
        path: Path = request.app.state.pdf_resolver(request.app.state.bundle_dir, source_id)
        # Read once and verify the exact response bytes, rather than a later
        # FileResponse read that could race with a changed private copy.
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != source.sha256 or not content.startswith(b"%PDF-"):
            raise ValueError("PDF bytes no longer match the sealed manifest")
    except (OSError, ValueError) as exc:
        raise request.app.state.api_error(503, "BUNDLE_INVALID", "Kaynak dosyası doğrulanamadı.") from exc
    return Response(
        content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="source-{source_id}.pdf"',
            "X-Research-Bundle-Id": view.metadata["immutable_bundle_id"],
            "X-Research-Cutoff-At": view.metadata["cutoff_at"],
            "X-Research-Origin": view.metadata["origin"],
            "X-Research-Analysis-Mode": view.metadata["analysis_mode"],
            "X-Research-Point-In-Time-Verified": "false",
            "X-Research-Rights-Status": "UNKNOWN",
            "X-Content-Type-Options": "nosniff",
        },
    )
