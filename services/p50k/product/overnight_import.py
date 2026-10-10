"""Append verified completed downloads without widening the calibrated catalog.

New observations become available at their acquisition time. Historical archive
rows and the v2 calibration remain unchanged. A manifest freezes completed files,
so a downloader may safely add more files for a later import.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
from contextlib import closing
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlsplit
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb

from p50k.product.archive import (
    Archive, ISTANBUL, canonical_json, decimal_value, kap_timestamp, sha256_file, timestamp,
)
from p50k.product.downloads import (
    REPORT_TYPE, TEFAS, _price_payload, cached, kap_listing,
)
from p50k.product.import_archive import ArchiveRevisionConflict, SOURCES, TABLES

AVAILABILITY_RULE = "overnight_acquisition_time_no_retrospective_publication_inference"
KAP_AVAILABILITY_RULE = "overnight_import_admission_upper_bound_unknown_response_completion"
SOURCE_VERSION = "overnight-refresh-v1"
CODE = re.compile(r"^[A-Z0-9]{2,12}$")
SHA = re.compile(r"^[a-f0-9]{64}$")
LOCK_ID = 503001021


@dataclass(frozen=True)
class CompletedFile:
    path: Path
    checksum: str
    metadata_path: Path | None
    metadata_checksum: str | None
    acquired: datetime | None


@dataclass
class OvernightArchive:
    root: Path
    catalog_codes: frozenset[str]
    now: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    _files: dict[str, tuple[CompletedFile, ...]] = field(default_factory=dict, init=False)
    ignored: dict[str, int] = field(default_factory=dict, init=False)

    def _safe_path(self, path: Path) -> None:
        path.resolve().relative_to(self.root.resolve())

    def _completed(self, path: Path, *, kind: str) -> CompletedFile | None:
        self._safe_path(path)
        metadata_path = path.with_suffix(path.suffix + ".meta.json")
        if not metadata_path.is_file():
            self.ignored["unready_files"] += 1
            return None
        self._safe_path(metadata_path)
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if not isinstance(metadata, dict):
            raise ValueError("Download metadata shape is invalid")
        acquired = timestamp(metadata.get("requested_at_utc"))
        if acquired is None or acquired > self.now:
            raise ValueError("Download acquisition time is missing or in the future")
        if kind == "prices":
            code = path.stem
            expected_url = TEFAS + "/fonFiyatBilgiGetir"
            valid = cached(path, _price_payload, expected_url=expected_url,
                           expected_method="POST",
                           expected_payload={"fonKodu": code, "dil": "TR", "periyod": 12})
            raw_hash = metadata.get("raw_response_sha256")
            if not isinstance(raw_hash, str) or not SHA.fullmatch(raw_hash):
                raise ValueError("Normalized price response provenance is missing")
        else:
            expected_url = metadata.get("original_url", metadata.get("url"))
            parsed = urlsplit(expected_url) if isinstance(expected_url, str) else None
            if parsed is None or not re.fullmatch(
                r"/tr/api/disclosure/filter/FILTERYFBF/[a-fA-F0-9]{32}/"
                + re.escape(REPORT_TYPE) + r"/365", parsed.path,
            ) or parsed.query or parsed.fragment:
                raise ValueError("KAP report-list endpoint is invalid")
            valid = cached(path, kap_listing, expected_url=expected_url)
        if not valid:
            raise ValueError("Completed download hash or request provenance differs")
        return CompletedFile(path, sha256_file(path), metadata_path,
                             sha256_file(metadata_path), acquired)

    def freeze(self) -> str:
        if self._files:
            self.verify_unchanged()
            return self.fingerprint()
        if self.now.tzinfo is None:
            raise ValueError("Import cutoff requires a timezone")
        self.ignored = {"unready_files": 0, "outside_catalog_files": 0,
                        "outside_catalog_snapshots": 0}
        for kind, pattern in (("prices", "tefas/prices/*.json"),
                              ("kap_documents", "kap/reports/*/kap_report_list.json")):
            selected = []
            for path in sorted(self.root.glob(pattern)):
                if path.name.endswith(".meta.json"):
                    continue
                code = path.stem if kind == "prices" else path.parent.name
                if not CODE.fullmatch(code):
                    raise ValueError("Downloaded fund identity is invalid")
                if code not in self.catalog_codes:
                    self.ignored["outside_catalog_files"] += 1
                    continue
                record = self._completed(path, kind="prices" if kind == "prices" else "kap")
                if record is not None:
                    selected.append(record)
            self._files[kind] = tuple(selected)
        snapshot = self.root / "snapshots-all.sqlite3"
        if snapshot.is_file():
            self._safe_path(snapshot)
            Archive.check_sqlite_stable(snapshot)
            with closing(sqlite3.connect(snapshot.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)) as db:
                latest = db.execute(
                    "SELECT started_at,finished_at,stopped FROM collector_runs ORDER BY started_at DESC LIMIT 1",
                ).fetchone()
                if latest is None or latest[1] is None or latest[2]:
                    raise ValueError("Snapshot collector has not finished successfully")
                started, finished = timestamp(latest[0]), timestamp(latest[1])
                if started is None or finished is None or started > finished or finished > self.now:
                    raise ValueError("Snapshot completion time is invalid")
            self._files["snapshots"] = (CompletedFile(snapshot, sha256_file(snapshot), None, None, None),)
        else:
            self._files["snapshots"] = ()
        if not any(self._files.values()):
            raise ValueError("No completed catalog downloads are ready")
        return self.fingerprint()

    def fingerprint(self) -> str:
        entries = [(kind, record.path.relative_to(self.root).as_posix(), record.checksum,
                    record.metadata_checksum)
                   for kind, records in sorted(self._files.items()) for record in records]
        return hashlib.sha256(canonical_json({
            "version": SOURCE_VERSION, "catalog": sorted(self.catalog_codes), "inputs": entries,
        }).encode("utf-8")).hexdigest()

    def verify_unchanged(self) -> None:
        for records in self._files.values():
            for record in records:
                if sha256_file(record.path) != record.checksum:
                    raise ValueError("Selected download changed during import")
                if record.metadata_path is not None:
                    if sha256_file(record.metadata_path) != record.metadata_checksum:
                        raise ValueError("Selected acquisition metadata changed during import")
                else:
                    Archive.check_sqlite_stable(record.path)

    @staticmethod
    def _read(record: CompletedFile) -> Any:
        data = record.path.read_bytes()
        if hashlib.sha256(data).hexdigest() != record.checksum:
            raise ValueError("Selected download changed after fingerprinting")
        return json.loads(data.decode("utf-8"))

    def prices(self) -> Iterator[dict[str, Any]]:
        for record in self._files["prices"]:
            payload = self._read(record)
            if payload.get("fund") != record.path.stem or payload.get("periyod") != 12:
                raise ValueError("Price payload does not match requested fund")
            acquired = timestamp(payload.get("retrieved_at"))
            if acquired is None or acquired > self.now or acquired < record.acquired:
                raise ValueError("Price retrieval time differs from acquisition provenance")
            meta = json.loads(record.metadata_path.read_text(encoding="utf-8"))
            seen: set[date] = set()
            for day_text, value in payload["rows"]:
                day = date.fromisoformat(day_text)
                if day in seen or day > acquired.astimezone(ISTANBUL).date():
                    raise ValueError("Price dates are duplicate or after acquisition")
                seen.add(day)
                yield {
                    "fund_code": payload["fund"], "effective_date": day,
                    "nav": decimal_value(value, positive=True), "source_id": "tefas-prices",
                    "source_version": SOURCE_VERSION, "source_sha256": record.checksum,
                    "origin": "DELAYED", "available_at": acquired, "observed_at": acquired,
                    "availability_rule": AVAILABILITY_RULE,
                    "metadata": {"source_path": record.path.relative_to(self.root).as_posix(),
                                 "periyod": 12, "raw_response_sha256": meta["raw_response_sha256"],
                                 "acquisition_metadata_sha256": record.metadata_checksum,
                                 "limitation": "Historical revisions admitted only at acquisition"},
                }

    def snapshots(self) -> Iterator[dict[str, Any]]:
        for record in self._files["snapshots"]:
            for row in Archive(self.root, (record.path,)).snapshots():
                if row["fund_code"] not in self.catalog_codes:
                    self.ignored["outside_catalog_snapshots"] += 1
                    continue
                if row["observed_at"] > self.now:
                    raise ValueError("Snapshot acquisition is after import cutoff")
                row["source_sha256"] = record.checksum
                row["source_version"] = SOURCE_VERSION
                row["metadata"]["source_path"] = record.path.relative_to(self.root).as_posix()
                yield row

    def kap_documents(self) -> Iterator[dict[str, Any]]:
        for record in self._files["kap_documents"]:
            seen: set[str] = set()
            for item in self._read(record):
                basic = item["disclosureBasic"]
                disclosure = basic["disclosureIndex"]
                if type(disclosure) is not int or disclosure <= 0:
                    raise ValueError("KAP disclosure identity is invalid")
                key = f"{record.path.parent.name}:{disclosure}"
                if key in seen:
                    raise ValueError("KAP list has duplicate disclosures")
                seen.add(key)
                published = kap_timestamp(basic.get("publishDate"))
                if published is not None and published > record.acquired:
                    raise ValueError("KAP publication is after acquisition")
                period = None
                cadence = "weekly" if basic.get("period") == "HB" else "monthly"
                if basic.get("year") and basic.get("donem"):
                    period = f"{int(basic['year'])}-{'W' if cadence == 'weekly' else ''}{int(basic['donem']):02d}"
                yield {
                    "document_key": key, "fund_code": record.path.parent.name,
                    "report_period": period, "relative_path": None, "source_id": "kap-reports",
                    "source_version": SOURCE_VERSION, "source_sha256": record.checksum,
                    "origin": "DELAYED", "published_at": published,
                    "available_at": self.now if published is not None else None,
                    "observed_at": self.now,
                    "availability_rule": KAP_AVAILABILITY_RULE if published is not None
                    else "unknown:publication_time",
                    "metadata": {"disclosure_index": disclosure, "cadence": cadence,
                                 "list_path": record.path.relative_to(self.root).as_posix(),
                                 "attachments": [], "acquisition_metadata_sha256": record.metadata_checksum,
                                 "requested_at_utc": record.acquired.isoformat(), "response_completion": "UNKNOWN",
                                 "limitation": "Report index only; no new PDFs or parsed holdings"},
                }


def _stage_incremental(connection: psycopg.Connection, table: str, columns: tuple[str, ...],
                       rows: Iterator[dict[str, Any]]) -> dict[str, int]:
    schema, name = table.split(".")
    target, staging = sql.Identifier(schema, name), sql.Identifier("refresh_" + name)
    columns = (*columns, "source_version")
    fields = sql.SQL(", ").join(map(sql.Identifier, columns))
    selected_fields = sql.SQL(", ").join(sql.SQL("s.{}").format(sql.Identifier(c)) for c in columns)
    count = missing = 0
    with connection.cursor() as cursor:
        cursor.execute(sql.SQL("CREATE TEMP TABLE {} (LIKE {} INCLUDING DEFAULTS) ON COMMIT DROP").format(staging, target))
        with cursor.copy(sql.SQL("COPY {} ({}) FROM STDIN").format(staging, fields)) as copy:
            for row in rows:
                copy.write_row([Jsonb(row.get(c), dumps=canonical_json)
                                if isinstance(row.get(c), (dict, list)) else row.get(c)
                                for c in columns])
                count += 1
                missing += "nav" in row and row["nav"] is None
        if table == "obs.fund_prices":
            # Compare all observations tied at the latest eligible priority. This
            # preserves A->B->A revisions and does not hide an ambiguous tie.
            predicate = sql.SQL("""
                NOT EXISTS (
                    SELECT 1 FROM {target} t
                    WHERE t.fund_code=s.fund_code AND t.effective_date=s.effective_date
                      AND t.source_id=s.source_id AND t.origin=s.origin
                      AND t.available_at<=s.available_at
                      AND (t.available_at,t.observed_at) IS NOT DISTINCT FROM (
                          SELECT ROW(t2.available_at,t2.observed_at) FROM {target} t2
                          WHERE t2.fund_code=s.fund_code AND t2.effective_date=s.effective_date
                            AND t2.source_id=s.source_id AND t2.origin=s.origin
                            AND t2.available_at<=s.available_at
                          ORDER BY t2.available_at DESC,t2.observed_at DESC NULLS LAST LIMIT 1
                      )
                    GROUP BY t.fund_code,t.effective_date
                    HAVING bool_and(t.nav IS NOT DISTINCT FROM s.nav)
                )
            """).format(target=target)
        elif table == "obs.fund_snapshots":
            identities = sql.SQL("t.fund_code=s.fund_code AND t.snapshot_key=s.snapshot_key AND t.source_id=s.source_id")
            same = sql.SQL(" AND ").join(sql.SQL("t.{0} IS NOT DISTINCT FROM s.{0}").format(sql.Identifier(c))
                                           for c in ("effective_date", "nav", "total_value", "units_outstanding", "investors", "daily_return_pct"))
            conflict = cursor.execute(sql.SQL("SELECT EXISTS(SELECT 1 FROM {} s JOIN {} t ON {} WHERE NOT ({}))").format(
                staging, target, identities, same)).fetchone()[0]
            if conflict:
                raise ArchiveRevisionConflict("Snapshot values changed under an existing acquisition identity")
            predicate = sql.SQL("NOT EXISTS(SELECT 1 FROM {} t WHERE {})").format(target, identities)
        else:
            predicate = sql.SQL("""NOT EXISTS(SELECT 1 FROM {target} t
                WHERE t.document_key=s.document_key AND t.source_id=s.source_id
                  AND t.report_period IS NOT DISTINCT FROM s.report_period
                  AND t.published_at IS NOT DISTINCT FROM s.published_at)""").format(target=target)
        cursor.execute(sql.SQL("INSERT INTO {} ({}) SELECT {} FROM {} s WHERE {} ON CONFLICT DO NOTHING").format(
            target, fields, selected_fields, staging, predicate))
        inserted = cursor.rowcount
    return {"input": count, "inserted": inserted, "duplicates": count - inserted, "missing": missing}


def import_overnight(connection: psycopg.Connection, root: Path, *,
                     now: datetime | None = None, dry_run: bool = False) -> dict[str, Any]:
    connection.autocommit = True
    catalog = connection.execute("SELECT fund_code,category,source_sha256 FROM ref.funds ORDER BY fund_code").fetchall()
    if not catalog:
        raise ValueError("Import the fixed catalog before refreshing observations")
    archive = OvernightArchive(root.resolve(), frozenset(row[0] for row in catalog),
                               now or datetime.now(timezone.utc))
    fingerprint = archive.freeze()
    if dry_run:
        counts = {kind: sum(1 for _ in getattr(archive, kind)())
                  for kind in ("prices", "snapshots", "kap_documents")}
        archive.verify_unchanged()
        return {"archive_sha256": fingerprint, "catalog_funds": len(catalog),
                "completed_files": {k: len(v) for k, v in archive._files.items()},
                "counts": counts, "ignored": archive.ignored, "dry_run": True}
    run_id = uuid4()
    connection.execute("INSERT INTO obs.ingest_runs(run_id,archive_sha256,status) VALUES(%s,%s,'RUNNING')",
                       (run_id, fingerprint))
    counts: dict[str, Any] = {}
    try:
        with connection.transaction():
            connection.execute("SELECT pg_advisory_xact_lock(%s)", (LOCK_ID,))
            for source_id, label in SOURCES:
                connection.execute("INSERT INTO ref.sources(source_id,label) VALUES(%s,%s) ON CONFLICT DO NOTHING", (source_id, label))
            for table, columns, kind in TABLES:
                if kind in {"prices", "snapshots", "kap_documents"}:
                    counts[table] = _stage_incremental(connection, table, columns, getattr(archive, kind)())
            archive.verify_unchanged()
            after = connection.execute("SELECT fund_code,category,source_sha256 FROM ref.funds ORDER BY fund_code").fetchall()
            if after != catalog:
                raise ValueError("Calibrated catalog changed while observations were imported")
            counts["boundary"] = {"catalog_funds": len(catalog), "calibration_changed": False,
                                  "completed_files": {k: len(v) for k, v in archive._files.items()},
                                  "ignored": archive.ignored}
            connection.execute("UPDATE obs.ingest_runs SET finished_at=clock_timestamp(),status='SUCCEEDED',counts=%s WHERE run_id=%s",
                               (Jsonb(counts), run_id))
    except Exception as error:
        connection.execute("UPDATE obs.ingest_runs SET finished_at=clock_timestamp(),status='FAILED',error_class=%s WHERE run_id=%s",
                           (type(error).__name__, run_id))
        raise
    return {"run_id": str(run_id), "archive_sha256": fingerprint, "counts": counts}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--overnight-dir", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        from p50k.product.db import connect
        from p50k.product.settings import Settings
        with connect(Settings.from_env()) as connection:
            print(json.dumps(import_overnight(connection, args.overnight_dir, dry_run=args.dry_run)))
        return 0
    except Exception as error:
        print(json.dumps({"error_class": type(error).__name__}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
