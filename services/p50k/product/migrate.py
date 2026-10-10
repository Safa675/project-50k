"""Apply immutable, checksummed SQL files under one PostgreSQL advisory lock."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
import argparse
import hashlib
import os
import re
import sys

import psycopg
from psycopg import sql

from p50k.product.db import connect
from p50k.product.settings import Settings

MIGRATION_LOCK = 50_000_014
DEFAULT_DIRECTORY = Path(__file__).resolve().parents[3] / "db" / "migrations"
FILENAME = re.compile(r"^[0-9]{3}_[a-z0-9_]+\.sql$")


class MigrationError(RuntimeError):
    """A migration cannot be applied without violating the registered history."""


@dataclass(frozen=True)
class Migration:
    filename: str
    sha256: str
    statement: str


def load_migrations(directory: Path) -> tuple[Migration, ...]:
    if not directory.is_dir() or directory.is_symlink():
        raise MigrationError("Migration directory is absent or is a symlink")
    paths = sorted(directory.glob("*.sql"))
    if not paths:
        raise MigrationError("No SQL migrations found")
    migrations: list[Migration] = []
    versions: set[str] = set()
    for path in paths:
        if not FILENAME.fullmatch(path.name) or path.is_symlink() or not path.is_file():
            raise MigrationError("Invalid migration path")
        version = path.name.split("_", 1)[0]
        if version in versions:
            raise MigrationError("Duplicate migration version")
        versions.add(version)
        payload = path.read_bytes()
        if b"\r" in payload or not payload:
            raise MigrationError("Migrations must be non-empty LF bytes")
        try:
            statement = payload.decode("utf-8")
        except UnicodeDecodeError as error:
            raise MigrationError("Migration is not UTF-8") from error
        if statement.startswith("\ufeff"):
            raise MigrationError("Migration cannot contain a byte-order mark")
        migrations.append(Migration(path.name, hashlib.sha256(payload).hexdigest(), statement))
    return tuple(migrations)


def pending_migrations(
    migrations: tuple[Migration, ...], applied: Mapping[str, str],
) -> tuple[Migration, ...]:
    current = {migration.filename: migration for migration in migrations}
    for filename, checksum in applied.items():
        if filename not in current or current[filename].sha256 != checksum:
            raise MigrationError("Previously applied migration bytes changed or disappeared")
    applied_names = set(applied)
    if applied_names and any(
        migration.filename < max(applied_names) and migration.filename not in applied_names
        for migration in migrations
    ):
        raise MigrationError("Migration cannot be inserted before an applied version")
    return tuple(migration for migration in migrations if migration.filename not in applied_names)


def ensure_application_role(connection: psycopg.Connection, password: str) -> None:
    if len(password) < 24 or "\x00" in password:
        raise MigrationError("Application credential is absent or invalid")
    with connection.transaction():
        exists = connection.execute(
            "SELECT 1 FROM pg_roles WHERE rolname = 'p50k_app'",
        ).fetchone()
        if not exists:
            connection.execute("CREATE ROLE p50k_app NOLOGIN")
        connection.execute(sql.SQL(
            "ALTER ROLE p50k_app WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
            "NOINHERIT NOREPLICATION NOBYPASSRLS PASSWORD {}",
        ).format(sql.Literal(password)))
        connection.execute(sql.SQL("GRANT CONNECT, TEMPORARY ON DATABASE {} TO p50k_app").format(
            sql.Identifier(connection.info.dbname),
        ))


def run_migrations(
    connection: psycopg.Connection, *, directory: Path = DEFAULT_DIRECTORY,
    app_password: str,
) -> tuple[str, ...]:
    """Each SQL file and its registry row commit or roll back together."""
    if not connection.autocommit:
        raise MigrationError("Migration connection must use autocommit")
    migrations = load_migrations(directory)
    owner = connection.execute("SELECT current_user").fetchone()
    if owner is None or owner[0] != "p50k_owner":
        raise MigrationError("Migrations require the p50k_owner role")
    connection.execute("SELECT pg_advisory_lock(%s)", (MIGRATION_LOCK,))
    try:
        with connection.transaction():
            connection.execute("CREATE SCHEMA IF NOT EXISTS ops")
            connection.execute("""
                CREATE TABLE IF NOT EXISTS ops.schema_migrations (
                    filename TEXT PRIMARY KEY,
                    sha256 TEXT NOT NULL CHECK (sha256 ~ '^[a-f0-9]{64}$'),
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
                )
            """)
        applied = dict(connection.execute(
            "SELECT filename, sha256 FROM ops.schema_migrations ORDER BY filename",
        ).fetchall())
        pending = pending_migrations(migrations, applied)
        ensure_application_role(connection, app_password)
        completed: list[str] = []
        for migration in pending:
            with connection.transaction():
                connection.execute(migration.statement, prepare=False)
                connection.execute(
                    "INSERT INTO ops.schema_migrations (filename, sha256) VALUES (%s, %s)",
                    (migration.filename, migration.sha256),
                )
            completed.append(migration.filename)
        return tuple(completed)
    finally:
        connection.execute("SELECT pg_advisory_unlock(%s)", (MIGRATION_LOCK,))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Apply BlackSwan SQL migrations")
    parser.add_argument("--directory", type=Path, default=DEFAULT_DIRECTORY)
    args = parser.parse_args(argv)
    try:
        settings = Settings.from_env()
        if settings.db_user != "p50k_owner":
            raise MigrationError("Migrations require owner configuration")
        password_path = os.environ.get("P50K_APP_PASSWORD_FILE")
        if not password_path:
            raise MigrationError("Application credential path is not configured")
        app_password = Path(password_path).read_text(encoding="utf-8").strip()
        with connect(settings, autocommit=True) as connection:
            completed = run_migrations(connection, directory=args.directory, app_password=app_password)
        print(f"Migrations applied: {len(completed)}")
        return 0
    except (OSError, ValueError, psycopg.Error, MigrationError) as error:
        # Database errors can contain credential-bearing SQL: expose the class only.
        print(f"Migration failed: {type(error).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
