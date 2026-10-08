"""Loopback-only research adapter; startup does not collect or compute data."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .models import CUTOFF_AT, ErrorResponse, Fund, Provenance, Source, Summary, validate_public_bundle
from .research_routes import router

ROOT = Path(__file__).resolve().parents[3]
UNIVERSE_FILE = ROOT / "research/events/2026-09-17-spk-liquidations/top100_funds.txt"
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
ERROR_PROVENANCE = {
    "origin": "HISTORICAL_REPLAY",
    "analysis_mode": "EXPLORATORY_ARCHIVE",
    "cutoff_at": CUTOFF_AT,
    "cutoff_semantics": "RECORDED_SOURCE_DATE_FILTER",
    "point_in_time_verified": False,
    "historical_availability": "UNKNOWN",
    "rights_status": "UNKNOWN",
    "universe_basis": "OCTOBER_2026_INVESTOR_SNAPSHOT",
    "category_basis": "CURRENT_SNAPSHOT",
    # Missing or invalid bundles have no authenticated fingerprint.
    "immutable_bundle_id": None,
}


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message


@dataclass(frozen=True)
class BundleView:
    provenance: Provenance
    summary: Summary
    funds: tuple[Fund, ...]
    sources: tuple[Source, ...]

    @property
    def metadata(self) -> dict:
        return self.provenance.model_dump(mode="json")


def create_app(bundle_dir: Path | str | None = None, *, frontend_origin: str | None = None,
               universe_codes: frozenset[str] | None = None) -> FastAPI:
    """Construct a private app. No bundle means explicit 503, never fake data.

    The universe injection exists for authored synthetic contract tests only;
    the launcher uses the committed selected-universe file.
    """
    origin = frontend_origin or os.environ.get("P50K_FRONTEND_ORIGIN", "http://127.0.0.1:3060")
    parsed = urlsplit(origin)
    if (parsed.scheme != "http" or parsed.hostname not in LOOPBACK_HOSTS or parsed.path
            or parsed.query or parsed.fragment or parsed.username or parsed.password):
        raise ValueError("The frontend origin must be a loopback HTTP origin")
    try:
        parsed.port
    except ValueError as exc:
        raise ValueError("Invalid frontend origin port") from exc

    from p50k.research_reviews.bundle import load_bundle, resolve_pdf

    configured_dir = bundle_dir if bundle_dir is not None else os.environ.get("P50K_RESEARCH_BUNDLE")
    app = FastAPI(title="Project 50K private archive research", docs_url=None,
                  redoc_url=None, openapi_url=None)
    app.state.bundle_dir = Path(configured_dir).resolve() if configured_dir else None
    app.state.universe_codes = universe_codes if universe_codes is not None else frozenset(UNIVERSE_FILE.read_text().split())
    app.state.pdf_resolver = lambda directory, source_id: resolve_pdf(directory, source_id, allowed_codes=app.state.universe_codes)
    app.state.last_metadata = None
    app.state.api_error = ApiError

    def bundle_view() -> BundleView:
        if app.state.bundle_dir is None:
            raise ApiError(503, "BUNDLE_UNAVAILABLE", "Araştırma paketi bulunamadı; yerel veri kurulumu gerekiyor.")
        try:
            bundle = load_bundle(app.state.bundle_dir, allowed_codes=app.state.universe_codes)
            view = BundleView(*validate_public_bundle(bundle))
            if {fund.code for fund in view.funds} != set(app.state.universe_codes):
                raise ValueError("Bundle universe differs from the committed selection")
        except (OSError, ValueError, KeyError, TypeError, ValidationError) as exc:
            app.state.last_metadata = None
            raise ApiError(503, "BUNDLE_INVALID", "Araştırma paketi veya kaynakları doğrulanamadı.") from exc
        app.state.last_metadata = view.metadata
        return view

    app.state.bundle_view = bundle_view

    app.add_middleware(CORSMiddleware, allow_origins=[origin], allow_credentials=False,
                       allow_methods=["GET"], allow_headers=[], max_age=0,
                       expose_headers=["X-Research-Bundle-Id", "X-Research-Cutoff-At"])

    def error_response(status: int, code: str, message: str) -> JSONResponse:
        payload = ErrorResponse.model_validate({**(app.state.last_metadata or ERROR_PROVENANCE),
                                               "error": {"code": code, "message_tr": message}})
        return JSONResponse(payload.model_dump(mode="json"), status_code=status)

    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
        return error_response(exc.status, exc.code, exc.message)

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        message = "Bu adres bulunamadı." if exc.status_code == 404 else "Bu istek desteklenmiyor."
        return error_response(exc.status_code, "NOT_FOUND" if exc.status_code == 404 else "INVALID_REQUEST", message)

    @app.exception_handler(RequestValidationError)
    async def request_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return error_response(422, "INVALID_REQUEST", "İstek biçimi geçersiz.")

    @app.exception_handler(ResponseValidationError)
    async def response_error_handler(request: Request, exc: ResponseValidationError) -> JSONResponse:
        return error_response(503, "BUNDLE_INVALID", "Araştırma yanıtı doğrulanamadı.")

    @app.middleware("http")
    async def private_responses(request: Request, call_next):
        if request.url.hostname not in LOOPBACK_HOSTS:
            response = error_response(400, "HOST_REJECTED", "Yalnızca yerel erişim destekleniyor.")
        elif request.method == "OPTIONS" and request.headers.get("origin") != origin:
            response = error_response(400, "INVALID_REQUEST", "Bu yerel arayüz kaynağı desteklenmiyor.")
        else:
            try:
                response = await call_next(request)
            except Exception:
                # Do not expose private filesystem paths or tracebacks.
                response = error_response(500, "INTERNAL_ERROR", "Araştırma yanıtı şu anda alınamıyor.")
        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    app.include_router(router)
    return app
