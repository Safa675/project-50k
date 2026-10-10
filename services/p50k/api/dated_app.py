"""Separate loopback-only dated D1 research adapter; startup does not collect or compute data.

Unlike the fixed-date app, nothing here keeps metadata between requests. The sealed
index is re-verified on every request, a date maps only to its indexed bundle
fingerprint, and every error carries the provenance of its own request.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from p50k.research_reviews.dated_bundle import (
    REPO, default_bundles_dir, index_entry, load_date_index, load_indexed_bundle,
)
from p50k.research_reviews.dated_contracts import (
    DATE_RULE, FINDINGS_SCOPE, KNOWLEDGE_BASIS, validate_cutoff,
)
from p50k.research_reviews.contracts import METADATA

from .dated_models import (
    DatedErrorResponse, DatedFundResponse, DatedFundsResponse, DatedSummaryResponse, DatedView,
    DatesResponse, LABEL_FIELDS, validate_dated_view,
)
from .dated_routes import router

UNIVERSE_REL = Path("research/events/2026-09-17-spk-liquidations/top100_funds.txt")
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
# The raw Host header, whole: a parsed hostname would accept "127.0.0.1/x" or fail on "[".
LOOPBACK_HOST_HEADER = re.compile(r"(127\.0\.0\.1|localhost|\[::1\])(:\d{1,5})?")
LABELS = {**{key: value for key, value in METADATA.items() if key != "cutoff_at"},
          "knowledge_basis": KNOWLEDGE_BASIS, "findings_scope": FINDINGS_SCOPE, "date_rule": DATE_RULE}
if set(LABELS) != set(LABEL_FIELDS):
    raise RuntimeError("Dated labels differ from the dated response models")
NO_CONTEXT = {"cutoff_at": None, "cutoff_date": None, "index_id": None}
MESSAGES_TR = {
    "DATE_INVALID": "Tarih biçimi geçersiz ya da kayıtlı tarih aralığının dışında.",
    "DATE_NOT_REGISTERED": "Bu tarih için kayıtlı bir arşiv kesiti yok.",
    "FUND_NOT_FOUND": "Bu fon araştırma kapsamında bulunmuyor.",
    "CONTEXT_MISMATCH": "İstenen araştırma paketi, bu tarih için kayıtlı paketle aynı değil.",
    "INDEX_UNAVAILABLE": "Tarih dizini bulunamadı; yerel veri kurulumu gerekiyor.",
    "INDEX_INVALID": "Tarih dizini doğrulanamadı.",
    "BUNDLE_INVALID": "Bu tarihin araştırma paketi veya kaynakları doğrulanamadı.",
    "NOT_FOUND": "Bu adres bulunamadı.",
    "INVALID_REQUEST": "Bu istek desteklenmiyor.",
    "HOST_REJECTED": "Yalnızca yerel erişim destekleniyor.",
    "INTERNAL_ERROR": "Araştırma yanıtı şu anda alınamıyor.",
}


class DatedApiError(Exception):
    """An error response with the provenance of the request that raised it."""

    def __init__(self, status: int, code: str, context: dict | None = None):
        super().__init__(code)
        self.status, self.code = status, code
        self.context = dict(context) if context is not None else dict(NO_CONTEXT)


def error_payload(code: str, context: dict | None = None) -> dict:
    payload = DatedErrorResponse.model_validate({
        **LABELS, **(context or NO_CONTEXT), "immutable_bundle_id": None,
        "error": {"code": code, "message_tr": MESSAGES_TR[code]}})
    return payload.model_dump(mode="json")


class DatedService:
    """Request-scoped steps; the routes call them in the registered validation order."""

    def __init__(self, index_dir: Path | None, *, universe_codes: frozenset[str], repo_root: Path,
                 bundles_dir: Path | None = None):
        self.index_dir = index_dir
        self.universe_codes = universe_codes
        self.repo_root = repo_root
        self.bundles_dir = bundles_dir

    # 1. date format, calendar validity and range: nothing is opened.
    @staticmethod
    def check_date(value: str) -> str:
        try:
            return validate_cutoff(value)
        except ValueError as exc:
            raise DatedApiError(400, "DATE_INVALID") from exc

    # The index is verified on every request; its bundles are verified per date.
    def read_index(self) -> dict:
        if self.index_dir is None or not (self.index_dir / "index.json").is_file():
            raise DatedApiError(503, "INDEX_UNAVAILABLE")
        try:
            return load_date_index(self.index_dir, repo_root=self.repo_root, allowed_codes=sorted(self.universe_codes),
                                   verify_bundles=False)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise DatedApiError(503, "INDEX_INVALID") from exc

    def dates(self) -> dict:
        index = self.read_index()
        try:
            response = DatesResponse.model_validate({**LABELS, "index_id": index["index_id"],
                                                     "default_date": index["default_date"],
                                                     "entries": index["entries"]})
        except ValidationError as exc:
            raise DatedApiError(503, "INDEX_INVALID") from exc
        return response.model_dump(mode="json")

    # 2. sealed-index membership: a date maps to its indexed fingerprint, never a path.
    def entry(self, value: str) -> tuple[dict, dict, dict]:
        selected = self.check_date(value)
        index = self.read_index()
        try:
            entry = index_entry(index, selected)
        except LookupError as exc:
            raise DatedApiError(404, "DATE_NOT_REGISTERED", {**NO_CONTEXT, "index_id": index["index_id"]}) from exc
        except ValueError as exc:
            raise DatedApiError(400, "DATE_INVALID") from exc
        context = {"cutoff_at": entry["cutoff_at"], "cutoff_date": entry["date"], "index_id": index["index_id"]}
        return index, entry, context

    @staticmethod
    def check_bundle(entry: dict, context: dict, requested: list[str]) -> None:
        if len(requested) > 1:
            raise DatedApiError(400, "INVALID_REQUEST", context)
        if requested and requested[0] != entry["bundle_id"]:
            raise DatedApiError(409, "CONTEXT_MISMATCH", context)

    # 3. code allowlist, before any bundle or source is opened or hashed.
    def check_code(self, code: str, context: dict) -> str:
        if code not in self.universe_codes:
            raise DatedApiError(404, "FUND_NOT_FOUND", context)
        return code

    # 4. load and validate the indexed bundle explicitly (no response_model context).
    def view(self, index: dict, entry: dict, context: dict) -> DatedView:
        bundles = self.bundles_dir if self.bundles_dir is not None else default_bundles_dir(self.index_dir)
        try:
            bundle = load_indexed_bundle(index, entry["date"], bundles_dir=bundles, repo_root=self.repo_root,
                                         allowed_codes=sorted(self.universe_codes))
            view = validate_dated_view(bundle, index["index_id"])
            if {record.code for record in view.funds.funds} != set(self.universe_codes) or \
                    view.metadata["immutable_bundle_id"] != entry["bundle_id"] or \
                    view.metadata["cutoff_at"] != entry["cutoff_at"] or view.metadata["cutoff_date"] != entry["date"]:
                raise ValueError("Bundle differs from its index entry or the committed selection")
        except (OSError, ValueError, KeyError, TypeError, LookupError, ValidationError) as exc:
            raise DatedApiError(503, "BUNDLE_INVALID", context) from exc
        return view

    @staticmethod
    def summary_payload(view: DatedView) -> dict:
        return DatedSummaryResponse.model_validate(view.summary.model_dump(mode="json")).model_dump(mode="json")

    @staticmethod
    def funds_payload(view: DatedView) -> dict:
        return DatedFundsResponse.model_validate(view.funds.model_dump(mode="json")).model_dump(mode="json")

    @staticmethod
    def fund_payload(view: DatedView, code: str, context: dict) -> dict:
        try:
            detail = view.detail(code)
        except ValidationError as exc:
            raise DatedApiError(503, "BUNDLE_INVALID", context) from exc
        if detail is None:
            raise DatedApiError(503, "BUNDLE_INVALID", context)
        return detail.model_dump(mode="json")

    def verify_all(self) -> dict:
        """Launcher check: the index, all bundles and every per-date response contract."""
        if self.index_dir is None:
            raise ValueError("No dated index is configured")
        try:
            index = self.read_index()
            self.dates()
        except DatedApiError as exc:
            raise ValueError(f"Date index failed verification ({exc.code})") from exc
        # Each indexed bundle is fully verified here (originals, provenance, index binding).
        for item in index["entries"]:
            try:
                entry = index_entry(index, item["date"])
                context = {"cutoff_at": entry["cutoff_at"], "cutoff_date": entry["date"], "index_id": index["index_id"]}
                view = self.view(index, entry, context)
                listed = self.funds_payload(view)["funds"]
                self.summary_payload(view)
                for record in listed:
                    if self.fund_payload(view, record["code"], context)["fund"] != record:
                        raise ValueError("List and detail records differ")
            except DatedApiError as exc:
                raise ValueError(f"Dated bundle for {item['date']} failed verification ({exc.code})") from exc
            except (OSError, ValueError, KeyError, TypeError, LookupError, ValidationError) as exc:
                raise ValueError(f"Dated bundle for {item['date']} failed verification ({type(exc).__name__})") from exc
        return index


def _loopback_origin(origin: str) -> str:
    parsed = urlsplit(origin)
    if (parsed.scheme != "http" or parsed.hostname not in LOOPBACK_HOSTS or parsed.path
            or parsed.query or parsed.fragment or parsed.username or parsed.password):
        raise ValueError("The frontend origin must be a loopback HTTP origin")
    try:
        parsed.port
    except ValueError as exc:
        raise ValueError("Invalid frontend origin port") from exc
    return origin


def create_dated_app(index_dir: Path | str | None = None, frontend_origin: str | None = None,
                     universe_codes: frozenset[str] | None = None, *, repo_root: Path | str | None = None,
                     bundles_dir: Path | str | None = None) -> FastAPI:
    """Construct the private dated app; no index means explicit 503, never fake data.

    Also the uvicorn factory: without arguments it reads P50K_DATED_INDEX. The browser
    reaches it only through the same-origin proxy, so no CORS access is granted; the
    frontend origin is validated as loopback and recorded. The universe and repository
    injections exist for authored synthetic tests and the launcher check only.
    """
    origin = _loopback_origin(frontend_origin or os.environ.get("P50K_FRONTEND_ORIGIN", "http://127.0.0.1:3060"))
    root = Path(repo_root).absolute() if repo_root is not None else REPO
    configured = index_dir if index_dir is not None else os.environ.get("P50K_DATED_INDEX")
    codes = universe_codes if universe_codes is not None else frozenset(
        (root / UNIVERSE_REL).read_text(encoding="utf-8").split())
    app = FastAPI(title="Project 50K private dated archive research", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.frontend_origin = origin
    app.state.dated = DatedService(Path(configured).absolute() if configured else None, universe_codes=frozenset(codes),
                                   repo_root=root, bundles_dir=Path(bundles_dir).absolute() if bundles_dir else None)
    app.state.verify_all = app.state.dated.verify_all

    def error_response(status: int, code: str, context: dict | None = None) -> JSONResponse:
        return JSONResponse(error_payload(code, context), status_code=status)

    @app.exception_handler(DatedApiError)
    async def dated_error_handler(request: Request, exc: DatedApiError) -> JSONResponse:
        return error_response(exc.status, exc.code, exc.context)

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return error_response(exc.status_code, "NOT_FOUND" if exc.status_code == 404 else "INVALID_REQUEST")

    @app.exception_handler(RequestValidationError)
    async def request_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return error_response(422, "INVALID_REQUEST")

    @app.exception_handler(ResponseValidationError)
    async def response_error_handler(request: Request, exc: ResponseValidationError) -> JSONResponse:
        return error_response(503, "BUNDLE_INVALID")

    @app.middleware("http")
    async def private_responses(request: Request, call_next):
        host = request.headers.get("host")
        if host is None or LOOPBACK_HOST_HEADER.fullmatch(host) is None:
            response = error_response(400, "HOST_REJECTED")
        else:
            try:
                response = await call_next(request)
            except Exception:
                # Do not expose private filesystem paths or tracebacks.
                response = error_response(500, "INTERNAL_ERROR")
        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    app.include_router(router)
    return app
