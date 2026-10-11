"""Request-scoped analysis time; authentication and budget clocks stay real.

A retrospective selection is one Istanbul day. Every view of that day reads only
the complete detector run computed for that exact day, never an older day's run
(even while the selected day's calculation is still queued) and never a live run.
The live view keeps the latest eligible run and never reads retrospective runs.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from datetime import date, datetime, time, timezone
from typing import Iterator

from p50k.product.archive import ISTANBUL
from p50k.product.settings import Settings

COOKIE = 'p50k_as_of'
EARLIEST = date(2025,10,6)
_selected: ContextVar[str | None] = ContextVar('analysis_date', default=None)


def validate_date(value: str) -> str:
    if value == 'live':
        return value
    parsed = date.fromisoformat(value)
    if parsed.isoformat()!=value or parsed > datetime.now(ISTANBUL).date() or parsed < EARLIEST:
        raise ValueError('ANALYSIS_DATE_OUT_OF_RANGE')
    return value


def selection(settings: Settings | None = None) -> str:
    return _selected.get() or (settings or Settings.from_env()).analysis_date


@contextmanager
def use_analysis_date(value: str) -> Iterator[None]:
    token = _selected.set(validate_date(value))
    try:
        yield
    finally:
        _selected.reset(token)


def historical_mode(settings: Settings | None = None) -> bool:
    return selection(settings)!='live'


def analysis_scope_key(settings: Settings | None = None) -> str:
    value=selection(settings)
    return 'live' if value=='live' else 'asof:'+value


def current_cutoff(settings: Settings | None = None) -> datetime:
    value=selection(settings)
    now=datetime.now(timezone.utc)
    if value=='live':
        return now
    return min(now,datetime.combine(date.fromisoformat(value),time.max,ISTANBUL).astimezone(timezone.utc))


def data_origins(settings: Settings | None = None) -> list[str]:
    return ['HISTORICAL_REPLAY'] if historical_mode(settings) else ['DELAYED']


def run_origins(settings: Settings | None = None, *, database: str | None = None) -> list[str]:
    """Run origins that may describe the selection; synthetic runs only in p50k_dev."""
    origins=data_origins(settings)
    if (database or (settings or Settings.from_env()).db_name)=='p50k_dev':
        origins.append('SYNTHETIC')
    return origins


def run_day(cutoff: datetime, settings: Settings | None = None) -> date | None:
    """The only Istanbul day whose run a retrospective read may use; None when live.

    An explicit earlier cutoff in a retrospective view therefore reads only the run
    computed for that earlier day, if one exists, and otherwise nothing.
    """
    return cutoff.astimezone(ISTANBUL).date() if historical_mode(settings) else None


def page_origin(settings: Settings | None = None) -> str:
    """Page-level data mode: a retrospective page is labelled as a replay."""
    return 'HISTORICAL_REPLAY' if historical_mode(settings) else 'DELAYED'


def public_context(settings: Settings | None = None) -> dict:
    cutoff=current_cutoff(settings)
    return {'as_of_date':cutoff.astimezone(ISTANBUL).date().isoformat(),
            'cutoff':cutoff.isoformat(),'mode':'historical' if historical_mode(settings) else 'live',
            'scope_key':analysis_scope_key(settings),'today':datetime.now(ISTANBUL).date().isoformat(),
            'timezone':'Europe/Istanbul'}
