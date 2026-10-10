"""GET-only routes over one sealed date index and its indexed dated bundles.

Order on every per-date route: date format, calendar validity and range; sealed-index
membership; the optional ?bundle= context; the code allowlist; only then the bundle
load. No route computes, substitutes a nearest date or serves source files.
"""
from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(prefix="/research-dated/v1")


def _context(request: Request, date: str):
    service = request.app.state.dated
    index, entry, context = service.entry(date)
    service.check_bundle(entry, context, request.query_params.getlist("bundle"))
    return service, index, entry, context


@router.get("/dates")
def dates(request: Request) -> dict:
    return request.app.state.dated.dates()


@router.get("/dates/{date}/summary")
def summary(date: str, request: Request) -> dict:
    service, index, entry, context = _context(request, date)
    return service.summary_payload(service.view(index, entry, context))


@router.get("/dates/{date}/funds")
def funds(date: str, request: Request) -> dict:
    service, index, entry, context = _context(request, date)
    return service.funds_payload(service.view(index, entry, context))


@router.get("/dates/{date}/funds/{code}")
def fund_detail(date: str, code: str, request: Request) -> dict:
    service, index, entry, context = _context(request, date)
    # Membership is checked before loading or hashing any bundle or source.
    service.check_code(code, context)
    return service.fund_payload(service.view(index, entry, context), code, context)
