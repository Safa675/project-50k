"""Database connections use the runtime role's separately mounted credential."""

from __future__ import annotations

import psycopg

from p50k.product.settings import Settings


def connect(settings: Settings, *, autocommit: bool = False) -> psycopg.Connection:
    """Return a context-manageable connection without logging connection arguments."""
    settings.validate()
    return psycopg.connect(**settings.connect_kwargs(), autocommit=autocommit)
