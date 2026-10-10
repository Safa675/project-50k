"""COPY through staging and retain immutable observations on repeat imports."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb

from p50k.product.archive import Archive, canonical_json

SOURCES = (
    ("tefas-fund-list", "TEFAS current fund listing"),
    ("tefas-prices", "TEFAS published-cadence daily NAV"),
    ("tefas-snapshots", "TEFAS observed latest-value snapshots"),
    ("kap-reports", "KAP portfolio report document index"),
    ("kap-series", "KAP parsed report index"),
    ("spk-bulletins", "SPK official bulletins"),
)
PROVENANCE = ("source_id", "source_sha256", "origin", "published_at", "available_at",
              "observed_at", "availability_rule", "metadata")
TABLES = (
    ("ref.funds", ("fund_code", "name", "category", "tefas_status", "listing_as_of", "source_id", "source_sha256", "observed_at", "metadata"), "funds"),
    ("obs.fund_prices", ("fund_code", "effective_date", "nav", *PROVENANCE), "prices"),
    ("obs.fund_snapshots", ("fund_code", "snapshot_key", "effective_date", "nav", "total_value", "units_outstanding", "investors", "daily_return_pct", *PROVENANCE), "snapshots"),
    ("obs.kap_documents", ("document_key", "fund_code", "report_period", "relative_path", *PROVENANCE), "kap_documents"),
    ("obs.kap_series", ("fund_code", "series_key", "report_period", "cadence", "document_key", *PROVENANCE), "kap_series"),
    ("obs.regulatory_events", ("event_id", "fund_code", "event_type", "effective_date", "status", *PROVENANCE), "events"),
)


class ArchiveRevisionConflict(ValueError):
    """Changed attachment evidence cannot be discarded under an existing identity."""


def stage_rows(connection: psycopg.Connection, table: str, columns: tuple[str, ...],
               rows: Iterable[dict[str, Any]]) -> dict[str, int]:
    schema, name = table.split(".")
    target = sql.Identifier(schema, name)
    staging = sql.Identifier("stage_" + name)
    fields = sql.SQL(", ").join(map(sql.Identifier, columns))
    input_count = missing_count = 0
    with connection.cursor() as cursor:
        cursor.execute(sql.SQL("CREATE TEMP TABLE {} (LIKE {} INCLUDING DEFAULTS) ON COMMIT DROP").format(staging, target))
        with cursor.copy(sql.SQL("COPY {} ({}) FROM STDIN").format(staging, fields)) as copy:
            for row in rows:
                values = []
                for column in columns:
                    value = row.get(column)
                    values.append(Jsonb(value, dumps=canonical_json) if isinstance(value, (dict, list)) else value)
                copy.write_row(values)
                input_count += 1
                if "nav" in row and row["nav"] is None:
                    missing_count += 1
        if table == "obs.kap_documents":
            conflict = cursor.execute(sql.SQL(
                "SELECT EXISTS (SELECT 1 FROM {} s JOIN {} t "
                "USING (document_key,source_id,source_sha256) "
                "WHERE s.metadata IS DISTINCT FROM t.metadata)"
            ).format(staging, target)).fetchone()
            if conflict and conflict[0]:
                raise ArchiveRevisionConflict("KAP attachment changed without a new source-list version")
        cursor.execute(sql.SQL("INSERT INTO {} ({}) SELECT {} FROM {} ON CONFLICT DO NOTHING").format(target, fields, fields, staging))
        inserted = cursor.rowcount
    return {"input": input_count, "inserted": inserted, "duplicates": input_count - inserted,
            "missing": missing_count}


def import_archive(connection: psycopg.Connection, archive: Archive) -> dict[str, Any]:
    fingerprint = archive.fingerprint()
    run_id = uuid4()
    started = datetime.now(timezone.utc)
    connection.autocommit = True
    with connection.transaction():
        connection.execute("INSERT INTO obs.ingest_runs (run_id, archive_sha256, started_at, status, counts) VALUES (%s,%s,%s,'RUNNING','{}'::jsonb)",
                           (run_id, fingerprint, started))
    counts: dict[str, Any] = {}
    try:
        with connection.transaction():
            for source_id, label in SOURCES:
                connection.execute("INSERT INTO ref.sources (source_id,label) VALUES (%s,%s) ON CONFLICT DO NOTHING", (source_id, label))
            for table, columns, reader in TABLES:
                counts[table] = stage_rows(connection, table, columns, getattr(archive, reader)())
                if table == "obs.fund_prices":
                    counts[table]["non_null"] = counts[table]["input"] - counts[table]["missing"]
            archive.verify_unchanged()
            connection.execute("UPDATE obs.ingest_runs SET finished_at=clock_timestamp(),status='SUCCEEDED',counts=%s WHERE run_id=%s", (Jsonb(counts), run_id))
    except Exception as error:
        with connection.transaction():
            connection.execute("UPDATE obs.ingest_runs SET finished_at=clock_timestamp(),status='FAILED',error_class=%s WHERE run_id=%s", (type(error).__name__, run_id))
        raise
    return {"run_id": str(run_id), "archive_sha256": fingerprint, "counts": counts}
