"""Public health only; real fund access stays denied until session auth exists."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import asynccontextmanager
import asyncio
import logging
import secrets

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from p50k.product.logging import configure_logging
from p50k.product.settings import Settings


def database_ready(settings: Settings) -> bool:
    try:
        import psycopg
        with psycopg.connect(**settings.connect_kwargs()) as connection:
            return connection.execute("SELECT 1 FROM ops.schema_migrations LIMIT 1").fetchone() == (1,)
    except Exception as error:
        logging.getLogger(__name__).warning("database_unavailable", extra={"error_class": type(error).__name__})
        return False


def create_app(settings: Settings | None = None, readiness: Callable[[Settings], bool] = database_ready) -> FastAPI:
    config = settings or Settings.from_env()
    config.validate()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        configure_logging()
        yield

    application = FastAPI(title="BlackSwan", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    application.add_middleware(TrustedHostMiddleware, allowed_hosts=list(config.allowed_hosts))
    public_paths = {"/health/live", "/health/ready"}
    if config.test_endpoints:
        public_paths.update({"/__test__/login", "/__test__/csrf", "/__test__/sse"})

    @application.middleware("http")
    async def deny_unprotected_routes(request: Request, call_next):
        if request.url.path not in public_paths:
            return JSONResponse({"error": "AUTHENTICATION_REQUIRED"}, status_code=401)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @application.get("/health/live")
    async def live():
        return {"service": "BlackSwan", "status": "alive"}

    @application.get("/health/ready")
    async def ready():
        available = await asyncio.to_thread(readiness, config)
        return JSONResponse({"service": "BlackSwan", "database": "available" if available else "unavailable", "ai_mode": "off"}, status_code=200 if available else 503)

    if config.test_endpoints:
        probe_sessions: dict[str, str] = {}

        def require_origin(request: Request) -> None:
            if request.headers.get("origin") not in config.allowed_origins:
                raise HTTPException(403, "ORIGIN_REJECTED")

        def require_probe_session(request: Request) -> None:
            session = request.cookies.get("p50k_proxy_probe", "")
            expected = probe_sessions.get(session)
            if not expected or not secrets.compare_digest(expected, request.headers.get("x-csrf-token", "")):
                raise HTTPException(403, "CSRF_REJECTED")

        @application.post("/__test__/login")
        async def probe_login(request: Request):
            require_origin(request)
            session, csrf = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
            probe_sessions[session] = csrf
            response = JSONResponse({"csrf": csrf, "test_only": True})
            response.set_cookie("p50k_proxy_probe", session, httponly=True, samesite="strict", path="/", max_age=60)
            response.set_cookie("p50k_proxy_marker", "synthetic", samesite="strict", path="/", max_age=60)
            return response

        @application.post("/__test__/csrf")
        async def probe_csrf(request: Request):
            require_origin(request)
            require_probe_session(request)
            return {"accepted": True, "test_only": True}

        @application.get("/__test__/sse")
        async def probe_sse():
            async def events():
                for index in range(10):
                    yield f"event: probe\ndata: {index}\n\n"
                    await asyncio.sleep(1)
            return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})

    return application


app = create_app()
