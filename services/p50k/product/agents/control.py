"""Persistent global admission control; existing leased work and audit stay intact."""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from p50k.product.db import connect
from p50k.product.settings import Settings


class TeamPaused(Exception):
    def __init__(self, calls: list[str] | None = None, cost: Decimal = Decimal(0)):
        super().__init__('TEAM_PAUSED')
        self.calls = calls or []
        self.cost = cost


def allows_new_work(connection) -> bool:
    """Share the row lock until admission commits, serializing with pause/resume."""
    row = connection.execute('SELECT paused FROM agents.team_control WHERE singleton FOR SHARE').fetchone()
    return row is not None and not row[0]


def require_running(settings: Settings) -> None:
    with connect(settings) as connection:
        connection.execute("SET LOCAL statement_timeout='5s'")
        if not allows_new_work(connection):
            raise TeamPaused()


def state(connection) -> dict[str, Any]:
    row = connection.execute('SELECT paused,changed_at FROM agents.team_control WHERE singleton').fetchone()
    if row is None:
        raise RuntimeError('TEAM_CONTROL_UNAVAILABLE')
    running = connection.execute("SELECT count(*) FROM agents.tasks WHERE status='running' AND lease_until>now()").fetchone()[0]
    return {'paused': row[0], 'changed_at': row[1].isoformat(), 'running_tasks': running,
            'finishing': bool(row[0] and running)}


def set_state(settings: Settings, actor_id: str, role: str, action: Literal['PAUSE', 'RESUME']) -> dict[str, Any]:
    if role != 'admin':
        raise PermissionError('ROLE_REQUIRED')
    if action not in {'PAUSE', 'RESUME'}:
        raise ValueError('CONTROL_ACTION_INVALID')
    paused = action == 'PAUSE'
    with connect(settings) as connection:
        connection.execute("SET LOCAL statement_timeout='10s'")
        connection.execute('UPDATE agents.team_control SET paused=%s,changed_at=clock_timestamp(),changed_by=%s WHERE singleton',
                           (paused, actor_id))
        connection.execute('INSERT INTO agents.control_events(action,actor_id,paused) VALUES (%s,%s,%s)',
                           (action, actor_id, paused))
        return state(connection)
