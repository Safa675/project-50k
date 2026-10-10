"""Sealed dated D1 bundles and their date index (fund_review_dated/PROTOCOL.md).

Bundles are content-addressed, written atomically and never overwritten. Loading
re-verifies the fixed dated contract, the temporal threshold bound against the
committed calibration files, every nested date against the bundle's own cutoff and
every manifest-backed original, including the bounded snapshot projection and a
digest over every bounded snapshot row of the opened funds (recorded only in the
internal manifest, so the public snapshot record keeps its shape).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Mapping, Sequence

from p50k.research_reviews.bundle import (
    BundleIntegrityError, EVENT_REL, canonical_bytes, digest, number, safe_file, validate_universe,
)
from p50k.research_reviews.contracts import METADATA, empty_finding
from p50k.research_reviews.dated_comments import dated_order, describe_dated, summarize_dated
from p50k.research_reviews.dated_contracts import (
    AUDIT_STATUS, DATE_RULE, DATED_SCHEMA, DEFAULT_DATE, DENOMINATOR, INDEX_SCHEMA, RECORD_KEYS,
    SNAPSHOT_BOUND, SOURCE_KINDS, THRESHOLD_FIXED, cutoff_at_for, d1_state, is_hex64, metadata_for,
    parse_instant, validate_cutoff, validate_grid,
)
from p50k.research_reviews.dated_review import check_snapshot, check_threshold_provenance

REPO = Path(__file__).resolve().parents[3]
RESULTS_REL = EVENT_REL / "price_detectors/results.json"
DETECTOR_REL = EVENT_REL / "price_detectors/detectors.py"
PREREGISTRATION_REL = EVENT_REL / "price_detectors/PREREGISTRATION.md"
BUNDLE_KEYS = frozenset({"schema", *METADATA, "cutoff_date", "knowledge_basis", "findings_scope", "date_rule",
                         "threshold_provenance", "snapshot", "summary", "funds", "sources", "manifest",
                         "registration", "immutable_bundle_id"})
INDEX_KEYS = frozenset({"schema", "date_rule", "default_date", "entries", "protocol_sha256", "protocol_commit",
                        "calendar_digest", "threshold_provenance", "snapshot", "audit", "index_id"})
CHART_KEYS = frozenset({"status", "reason", "baseline_date", "unit", "points", "peer_count"})
D1_KEYS = frozenset(empty_finding("d1"))
MANIFEST_KEYS = frozenset({"source_id", "original_path", "sha256", "kind", "copy_path", "snapshot_codes",
                           "snapshot_bound", "snapshot_rows_sha256"})
COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")


# ---------------------------------------------------------------- snapshot


def _bounded_rows(path: Path, codes: Sequence[str], bound: str) -> dict[str, list[tuple]]:
    """Every row of the opened funds retrieved at or before the bound, per fund.

    Every selected row needs an offset-aware retrieved_at, so a row cannot hide on
    either side of the bound.
    """
    selected = validate_universe(codes)
    limit = parse_instant(bound)
    path = safe_file(Path(path))
    try:
        connection = sqlite3.connect(f"{path.absolute().as_uri()}?mode=ro", uri=True)
        try:
            rows = connection.execute(
                f"SELECT fund, category, raw_snapshot, retrieved_at FROM fund_snapshots WHERE fund IN "
                f"({','.join('?' for _ in selected)})", selected).fetchall()
        finally:
            connection.close()
    except sqlite3.Error as exc:
        raise ValueError("snapshot database cannot be read") from exc
    candidates: dict[str, list[tuple]] = {}
    for code, category, raw, retrieved in rows:
        instant = parse_instant(retrieved)
        if instant <= limit:
            candidates.setdefault(code, []).append((instant, category, raw, retrieved))
    return candidates


def _cell(value: object) -> object:
    return {"blob_hex": bytes(value).hex()} if isinstance(value, (bytes, bytearray, memoryview)) else value


def bounded_rows_sha256(path: Path, codes: Sequence[str], bound: str = SNAPSHOT_BOUND) -> str:
    """Digest of ALL bounded (fund, category, raw_snapshot, retrieved_at) rows of the opened funds.

    Canonical order: fund code, parsed retrieval instant, then the row's canonical
    bytes. An edited or deleted older row, or a backdated insert older than a fund's
    newest bounded row, changes it; rows appended after the bound do not.
    """
    candidates = _bounded_rows(path, codes, bound)
    ordered = []
    for code in sorted(candidates):
        rows = sorted(((instant, [code, _cell(category), _cell(raw), retrieved])
                       for instant, category, raw, retrieved in candidates[code]),
                      key=lambda pair: (pair[0], canonical_bytes(pair[1])))
        ordered.extend(row for _, row in rows)
    return digest(canonical_bytes(ordered))


def bounded_snapshot(path: Path, codes: Sequence[str], bound: str = SNAPSHOT_BOUND) -> tuple[bytes, str | None]:
    """Newest name/category row per opened fund retrieved at or before the bound.

    Rows appended after the bound never change the bytes. Older bounded rows are
    covered by bounded_rows_sha256, which the manifest records and loading checks.
    """
    candidates = _bounded_rows(path, codes, bound)
    identities, newest = {}, []
    for code in sorted(candidates):
        latest = max(row[0] for row in candidates[code])
        chosen = [row for row in candidates[code] if row[0] == latest]
        if len(chosen) != 1:
            raise ValueError("two snapshot rows of one fund share the newest bounded retrieval instant")
        _, category, raw, retrieved = chosen[0]
        try:
            row = json.loads(raw)
            name = row.get("fonUnvan") if isinstance(row, dict) else None
        except (ValueError, TypeError):
            name = None
        name = name if isinstance(name, str) and name.strip() else code
        category = category if isinstance(category, str) and category.strip() else None
        identities[code] = {"name": name, "category": category, "retrieved_at": retrieved}
        newest.append((latest, retrieved))
    return canonical_bytes(identities), max(newest)[1] if newest else None


class DatedSourceRegistry:
    """Like bundle.SourceRegistry, limited to the dated kinds and the bounded snapshot."""

    def __init__(self):
        self.sources: dict[str, dict] = {}
        self.manifest: dict[str, dict] = {}

    def add(self, path: Path, kind: str, *, fund_code: str | None = None, retrieved_at: str | None = None,
            snapshot_codes: Sequence[str] | None = None, snapshot_bound: str | None = None,
            expected_sha256: str | None = None) -> str:
        if kind not in SOURCE_KINDS:
            raise BundleIntegrityError("source kind is outside the dated protocol")
        if (kind == "SNAPSHOT") != (snapshot_codes is not None) or (snapshot_codes is None) != (snapshot_bound is None):
            raise BundleIntegrityError("only the snapshot source carries a bounded code projection")
        if kind == "PRICE" and fund_code is None:
            raise BundleIntegrityError("a price source must identify its fund")
        path = safe_file(Path(path))
        rows_sha256 = None
        if snapshot_codes is not None:
            data, _ = bounded_snapshot(path, snapshot_codes, snapshot_bound)
            rows_sha256 = bounded_rows_sha256(path, snapshot_codes, snapshot_bound)
        else:
            data = path.read_bytes()
        identifier = digest(canonical_bytes({"path": str(path.absolute()), "kind": kind}))
        sha = digest(data)
        if expected_sha256 is not None and sha != expected_sha256:
            raise BundleIntegrityError("source changed between reading and registration")
        self.sources[identifier] = {
            "source_id": identifier, "kind": kind,
            "label": f"{fund_code + ' ' if fund_code else ''}{kind}" +
                     (" (bounded name/category projection)" if snapshot_codes is not None else ""),
            "fund_code": fund_code, "sha256": sha, "file_name": path.name,
            "media_type": "application/json" if kind in ("PRICE", "SNAPSHOT", "CALIBRATION") else "text/plain",
            "pdf_available": False, "published_at": None, "retrieved_at": retrieved_at,
            "historical_availability": "UNKNOWN", "rights_status": "UNKNOWN", "origin": "HISTORICAL_REPLAY",
            "disclosure_id": None, "disclosure_url": None}
        self.manifest[identifier] = {
            "source_id": identifier, "original_path": str(path.absolute()), "sha256": sha, "kind": kind,
            "copy_path": None, "snapshot_codes": list(snapshot_codes) if snapshot_codes is not None else None,
            "snapshot_bound": snapshot_bound, "snapshot_rows_sha256": rows_sha256}
        return identifier


def _source_bytes(entry: dict) -> bytes:
    path = safe_file(Path(entry["original_path"]))
    if entry["kind"] == "SNAPSHOT":
        return bounded_snapshot(path, entry["snapshot_codes"], entry["snapshot_bound"])[0]
    return path.read_bytes()


# ------------------------------------------------------- threshold provenance


def results_d1_thresholds(results_bytes: bytes) -> dict:
    stored = json.loads(results_bytes, parse_float=Decimal)
    thresholds = stored.get("thresholds", {}).get("D1") if isinstance(stored, dict) else None
    if not isinstance(thresholds, dict):
        raise ValueError("results.json has no D1 threshold map")
    return thresholds


def threshold_map_digest(thresholds: Mapping[str, object]) -> str:
    """Digest of the D1 map with each number kept as its literal decimal text."""
    return digest(canonical_bytes({str(key): None if value is None else str(value)
                                   for key, value in thresholds.items()}))


def build_threshold_provenance(results_bytes: bytes, detectors_bytes: bytes, preregistration_bytes: bytes) -> dict:
    stored = json.loads(results_bytes, parse_float=Decimal)
    run_at = stored.get("run_at_utc") if isinstance(stored, dict) else None
    parse_instant(run_at)
    return {**THRESHOLD_FIXED, "calibration_run_at_utc": run_at,
            "results_sha256": digest(results_bytes),
            "threshold_map_sha256": threshold_map_digest(results_d1_thresholds(results_bytes)),
            "detectors_sha256": digest(detectors_bytes),
            "preregistration_sha256": digest(preregistration_bytes)}


def committed_threshold_provenance(repo_root: Path) -> tuple[dict, dict]:
    root = Path(repo_root)
    results = safe_file(root / RESULTS_REL).read_bytes()
    provenance = build_threshold_provenance(results, safe_file(root / DETECTOR_REL).read_bytes(),
                                            safe_file(root / PREREGISTRATION_REL).read_bytes())
    return provenance, results_d1_thresholds(results)


# ---------------------------------------------------------------- bundles


def _date_at_most(value: object, cutoff: str, field: str, *, nullable: bool = True) -> None:
    if value is None and nullable:
        return
    if validate_date_text(value) > cutoff:
        raise BundleIntegrityError(f"{field} is dated after the bundle cutoff")


def validate_date_text(value: object) -> str:
    """Complete canonical date (any range); comparisons are never on partial strings."""
    if not isinstance(value, str) or re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is None:
        raise BundleIntegrityError("nested date is not a canonical YYYY-MM-DD date")
    try:
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError
    except ValueError as exc:
        raise BundleIntegrityError("nested date is not a calendar date") from exc
    return value


def _verify_record(record: dict, cutoff: str, thresholds: Mapping[str, object], sources: Mapping[str, dict]) -> None:
    if not isinstance(record, dict) or set(record) != RECORD_KEYS:
        raise BundleIntegrityError("dated record fields differ from the D1-only contract")
    d1, chart = record["d1"], record["chart"]
    if not isinstance(d1, dict) or set(d1) != D1_KEYS or d1["production_status"] != "ABSTAINED":
        raise BundleIntegrityError("dated D1 finding fields differ from the v1 D1 shape")
    if not isinstance(chart, dict) or set(chart) != CHART_KEYS:
        raise BundleIntegrityError("dated chart fields differ from the v1 chart shape")
    if record["date_context"] != {"has_positive_price_on_or_before_cutoff": True} and \
            record["date_context"] != {"has_positive_price_on_or_before_cutoff": False}:
        raise BundleIntegrityError("date context differs from the dated contract")
    if not isinstance(record["name"], str) or not record["name"].strip():
        raise BundleIntegrityError("record name is missing")
    category = record["category"]
    if category is not None and (not isinstance(category, str) or not category.strip()):
        raise BundleIntegrityError("record category is invalid")
    period = d1["metric_period"]
    if not isinstance(period, dict) or set(period) != {"start", "end"}:
        raise BundleIntegrityError("D1 metric period is invalid")
    _date_at_most(period["start"], cutoff, "D1 metric period start")
    _date_at_most(period["end"], cutoff, "D1 metric period end")
    if period["start"] is not None and period["end"] is not None and period["start"] > period["end"]:
        raise BundleIntegrityError("D1 metric period is reversed")
    _date_at_most(d1["latest_contributing_at"], cutoff, "D1 latest contributing observation")
    _date_at_most(chart["baseline_date"], cutoff, "chart baseline")
    points = chart["points"]
    if not isinstance(points, list):
        raise BundleIntegrityError("chart points are invalid")
    for point in points:
        if not isinstance(point, dict) or set(point) != {"date", "fund", "peers"}:
            raise BundleIntegrityError("chart point fields are invalid")
        _date_at_most(point["date"], cutoff, "chart point", nullable=False)
    if [point["date"] for point in points] != sorted({point["date"] for point in points}):
        raise BundleIntegrityError("chart points are not in strict date order")
    if chart["status"] == "UNAVAILABLE" and (points or chart["baseline_date"] is not None):
        raise BundleIntegrityError("unavailable chart carries points")
    # Thresholds are bound to the committed calibration, never recalibrated.
    expected = number(thresholds.get(category)) if category is not None else None
    if d1["threshold"] != (None if expected is None else str(expected)):
        raise BundleIntegrityError("record threshold differs from the committed calibration")
    if d1["arithmetic_status"] == "AVAILABLE":
        statistic = number(d1["statistic"])
        if statistic is None or d1["threshold"] is None or d1["latest_contributing_at"] is None:
            raise BundleIntegrityError("available D1 finding lacks its statistic, threshold or last observation")
        fresh = d1["latest_contributing_at"] == cutoff
        stale_reason = "final_contributing_observation_before_cutoff" in d1["missing_reasons"]
        if d1["freshness"] != ("FRESH" if fresh else "STALE") or stale_reason == fresh:
            raise BundleIntegrityError("D1 freshness disagrees with the bundle cutoff")
        crossing = float(d1["statistic"]) > float(d1["threshold"])
        if d1["research_screen"] != ("CROSSING" if crossing else "NO_CROSSING"):
            raise BundleIntegrityError("D1 research screen disagrees with the stored threshold")
    elif d1["arithmetic_status"] == "UNAVAILABLE":
        if d1["freshness"] != "UNKNOWN" or d1["research_screen"] != "UNKNOWN" or d1["statistic"] is not None:
            raise BundleIntegrityError("unavailable D1 finding carries a result")
    else:
        raise BundleIntegrityError("D1 arithmetic status is invalid")
    try:
        state = d1_state(d1)
    except ValueError as exc:
        raise BundleIntegrityError("D1 state cannot be derived") from exc
    if record["d1_state"] != state or record["comment_tr"] != describe_dated(d1):
        raise BundleIntegrityError("record state or comment disagrees with its D1 finding")
    if not record["date_context"]["has_positive_price_on_or_before_cutoff"] and state != "UNAVAILABLE":
        raise BundleIntegrityError("a fund without a price at the cutoff cannot have a D1 result")
    evidence = record["evidence"]
    if not isinstance(evidence, list) or evidence != sorted(set(evidence)) or not set(evidence).issubset(sources):
        raise BundleIntegrityError("record refers to an unknown source")
    if not isinstance(d1["input_refs"], list) or not set(d1["input_refs"]).issubset(evidence):
        raise BundleIntegrityError("D1 inputs are not part of the record evidence")


def verify_dated_payload(payload: dict, *, repo_root: Path = REPO, directory: Path | None = None,
                         allowed_codes: Sequence[str] | None = None, expected_date: str | None = None,
                         check_originals: bool = True) -> dict:
    """Verify one dated payload; the cutoff is range-checked before any input is opened."""
    if not isinstance(payload, dict) or payload.get("schema") != DATED_SCHEMA:
        raise BundleIntegrityError("dated bundle schema is missing or unsupported")
    try:
        cutoff = validate_cutoff(payload.get("cutoff_date"))
        if expected_date is not None and validate_cutoff(expected_date) != cutoff:
            raise BundleIntegrityError("dated bundle cutoff differs from the requested date")
    except ValueError as exc:
        raise BundleIntegrityError(f"dated bundle cutoff refused: {exc}") from exc
    if set(payload) != BUNDLE_KEYS:
        raise BundleIntegrityError("dated bundle fields differ from the D1-only contract")
    if any(payload.get(key) != value for key, value in metadata_for(cutoff).items()):
        raise BundleIntegrityError("dated bundle provenance differs from the fixed dated contract")
    fingerprint = payload["immutable_bundle_id"]
    if not is_hex64(fingerprint):
        raise BundleIntegrityError("dated bundle fingerprint is missing or invalid")
    content = {key: value for key, value in payload.items() if key != "immutable_bundle_id"}
    if digest(canonical_bytes(content)) != fingerprint or (directory is not None and Path(directory).name != fingerprint):
        raise BundleIntegrityError("sealed dated bundle fingerprint mismatch")
    try:
        check_threshold_provenance(payload["threshold_provenance"])
        committed, thresholds = committed_threshold_provenance(repo_root)
        if payload["threshold_provenance"] != committed:
            raise BundleIntegrityError("threshold provenance differs from the committed calibration files")
        snapshot = check_snapshot(payload["snapshot"])
        if not is_hex64(snapshot["projection_sha256"]) or \
                parse_instant(snapshot["latest_retrieved_at"]) > parse_instant(snapshot["bound"]):
            raise BundleIntegrityError("snapshot provenance is invalid")
        funds = payload["funds"]
        codes = validate_universe([row["code"] for row in funds])
        allowed = validate_universe(allowed_codes) if allowed_codes is not None else codes
        if codes != allowed:
            raise BundleIntegrityError("dated bundle contains a fund outside the opened universe")
        if [row["code"] for row in sorted(funds, key=dated_order)] != [row["code"] for row in funds]:
            raise BundleIntegrityError("dated bundle order is inconsistent")
        sources = {source["source_id"]: source for source in payload["sources"]}
        entries = payload["manifest"]
        if len(sources) != len(payload["sources"]) or len(entries) != len(sources) or \
                set(sources) != {entry["source_id"] for entry in entries}:
            raise BundleIntegrityError("dated bundle manifest/source IDs differ")
        if any(source.get("kind") not in SOURCE_KINDS for source in sources.values()) or \
                any(entry.get("kind") not in SOURCE_KINDS for entry in entries):
            raise BundleIntegrityError("source kind is outside the dated protocol")
        for record in funds:
            _verify_record(record, cutoff, thresholds, sources)
        summary = summarize_dated(funds)
        if payload["summary"] != summary or summary["record_count"] != DENOMINATOR or \
                sum(summary[key] for key in ("d1_eligible_crossing", "d1_eligible_no_crossing", "d1_stale",
                                             "d1_unavailable")) != DENOMINATOR or \
                summary["no_price_at_cutoff"] > summary["d1_unavailable"]:
            raise BundleIntegrityError("dated bundle summary count mismatch")
        # Membership precedes every original file or snapshot read.
        if any(source.get("fund_code") is not None and source["fund_code"] not in allowed
               for source in sources.values()):
            raise BundleIntegrityError("source refers to an unopened fund")
        if any(source["kind"] == "PRICE" and source.get("fund_code") not in allowed for source in sources.values()):
            raise BundleIntegrityError("price source must identify an opened fund")
        snapshots = [entry for entry in entries if entry["kind"] == "SNAPSHOT"]
        if len(snapshots) != 1:
            raise BundleIntegrityError("dated bundle needs exactly one bounded snapshot source")
        for entry in entries:
            if not isinstance(entry, dict) or set(entry) != MANIFEST_KEYS or entry["copy_path"] is not None:
                raise BundleIntegrityError("manifest entry differs from the dated contract")
            if not is_hex64(entry["source_id"]) or not is_hex64(entry["sha256"]) or \
                    sources[entry["source_id"]]["sha256"] != entry["sha256"] or \
                    sources[entry["source_id"]]["kind"] != entry["kind"]:
                raise BundleIntegrityError("invalid manifest identifier/hash")
            if entry["kind"] == "SNAPSHOT":
                if validate_universe(entry["snapshot_codes"]) != allowed or entry["snapshot_bound"] != SNAPSHOT_BOUND:
                    raise BundleIntegrityError("snapshot selection or bound differs from the dated contract")
                if entry["sha256"] != snapshot["projection_sha256"]:
                    raise BundleIntegrityError("snapshot digest differs from the bundle snapshot record")
                if not is_hex64(entry["snapshot_rows_sha256"]):
                    raise BundleIntegrityError("snapshot source lacks its bounded rows digest")
            elif entry["snapshot_codes"] is not None or entry["snapshot_bound"] is not None or \
                    entry["snapshot_rows_sha256"] is not None:
                raise BundleIntegrityError("only the snapshot source carries a code projection")
        if check_originals:
            for entry in entries:
                if entry["kind"] == "SNAPSHOT":
                    data, latest = bounded_snapshot(safe_file(Path(entry["original_path"])),
                                                    entry["snapshot_codes"], entry["snapshot_bound"])
                    if latest != snapshot["latest_retrieved_at"]:
                        raise BundleIntegrityError("bounded snapshot latest retrieval changed")
                else:
                    data = _source_bytes(entry)
                if digest(data) != entry["sha256"]:
                    raise BundleIntegrityError("manifest-backed original source changed")
                if entry["kind"] == "SNAPSHOT" and bounded_rows_sha256(
                        safe_file(Path(entry["original_path"])), entry["snapshot_codes"],
                        entry["snapshot_bound"]) != entry["snapshot_rows_sha256"]:
                    raise BundleIntegrityError("bounded snapshot rows changed: an older row was edited, deleted "
                                               "or backdated before the bound")
                if entry["kind"] == "SNAPSHOT":
                    projection = json.loads(data)
                    for record in funds:
                        identity = projection.get(record["code"], {"name": record["code"], "category": None})
                        if (record["name"], record["category"]) != (identity["name"], identity["category"]):
                            raise BundleIntegrityError("record name or category differs from the bounded snapshot")
        if not isinstance(payload["registration"], dict):
            raise BundleIntegrityError("dated bundle registration is missing")
    except (KeyError, TypeError, ValueError, OSError, AttributeError) as exc:
        if isinstance(exc, BundleIntegrityError):
            raise
        raise BundleIntegrityError(f"dated bundle validation failed: {exc}") from exc
    return payload


def _read_json(path: Path, root: Path, label: str) -> dict:
    safe_file(path, root)
    try:
        return json.loads(path.read_bytes())
    except (ValueError, UnicodeDecodeError, OSError) as exc:
        raise BundleIntegrityError(f"sealed {label} JSON is unreadable") from exc


def load_dated_bundle(directory: Path, *, repo_root: Path = REPO, allowed_codes: Sequence[str] | None = None,
                      expected_date: str | None = None) -> dict:
    directory = Path(directory).absolute()
    if expected_date is not None:
        try:
            validate_cutoff(expected_date)
        except ValueError as exc:
            raise BundleIntegrityError(f"dated bundle cutoff refused: {exc}") from exc
    payload = _read_json(directory / "bundle.json", directory, "dated bundle")
    return verify_dated_payload(payload, repo_root=repo_root, directory=directory, allowed_codes=allowed_codes,
                                expected_date=expected_date)


def _publish(base: Path, name: str, filename: str, data: bytes, verify_existing) -> Path:
    """Write verified bytes to a temp directory and rename; an existing version is only reused."""
    base = Path(base).absolute()
    if any(part.is_symlink() for part in (base, *base.parents)):
        raise BundleIntegrityError("dated output cannot contain symlinks")
    base.mkdir(parents=True, exist_ok=True)
    destination = base / name
    if destination.exists():
        if safe_file(destination / filename, destination).read_bytes() != data:
            raise BundleIntegrityError("refusing to overwrite an existing sealed dated output")
        verify_existing(destination)
        return destination
    temporary = Path(tempfile.mkdtemp(prefix=".dated-", dir=base))
    try:
        with (temporary / filename).open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if (temporary / filename).read_bytes() != data:
            raise BundleIntegrityError("sealed bytes differ from the verified payload")
        # Nonempty existing destinations are rejected by rename; no file overwrite.
        os.rename(temporary, destination)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return destination


def write_dated_bundle(base: Path, payload: dict, *, repo_root: Path = REPO,
                       allowed_codes: Sequence[str] | None = None) -> Path:
    """Verify fully, then publish atomically; never overwrite a sealed version."""
    verify_dated_payload(payload, repo_root=repo_root, allowed_codes=allowed_codes)
    return _publish(base, payload["immutable_bundle_id"], "bundle.json", canonical_bytes(payload),
                    lambda path: load_dated_bundle(path, repo_root=repo_root, allowed_codes=allowed_codes))


# ------------------------------------------------------------------ index


def make_date_index(bundles: Sequence[dict], *, protocol_sha256: str, protocol_commit: str,
                    calendar_digest: str, v1_bundle_id: str) -> dict:
    if not bundles:
        raise ValueError("a date index needs its sealed bundles")
    index = {"schema": INDEX_SCHEMA, "date_rule": DATE_RULE, "default_date": DEFAULT_DATE,
             "entries": [{"date": bundle["cutoff_date"], "cutoff_at": bundle["cutoff_at"],
                          "bundle_id": bundle["immutable_bundle_id"]} for bundle in bundles],
             "protocol_sha256": protocol_sha256, "protocol_commit": protocol_commit,
             "calendar_digest": calendar_digest,
             "threshold_provenance": bundles[0]["threshold_provenance"], "snapshot": bundles[0]["snapshot"],
             "audit": {"status": AUDIT_STATUS, "v1_bundle_id": v1_bundle_id}}
    index["index_id"] = digest(canonical_bytes(index))
    verify_index_structure(index)
    for bundle in bundles:
        _check_bound_bundle(index, index_entry(index, bundle["cutoff_date"]), bundle)
    return index


def verify_index_structure(index: dict, directory: Path | None = None) -> dict:
    try:
        if not isinstance(index, dict) or index.get("schema") != INDEX_SCHEMA:
            raise BundleIntegrityError("date index schema is missing or unsupported")
        if set(index) != INDEX_KEYS or index["date_rule"] != DATE_RULE or index["default_date"] != DEFAULT_DATE:
            raise BundleIntegrityError("date index fields differ from the dated contract")
        entries = index["entries"]
        if not isinstance(entries, list) or any(not isinstance(entry, dict) or
                                                set(entry) != {"date", "cutoff_at", "bundle_id"} for entry in entries):
            raise BundleIntegrityError("date index entries are invalid")
        dates = validate_grid([entry["date"] for entry in entries])
        if index["default_date"] not in dates:
            raise BundleIntegrityError("default date is not a registered entry")
        if any(entry["cutoff_at"] != cutoff_at_for(entry["date"]) for entry in entries):
            raise BundleIntegrityError("date index cutoff differs from its date")
        identifiers = [entry["bundle_id"] for entry in entries]
        if not all(is_hex64(value) for value in identifiers) or len(set(identifiers)) != len(identifiers):
            raise BundleIntegrityError("date index bundle IDs are invalid or repeated")
        if not is_hex64(index["protocol_sha256"]) or not is_hex64(index["calendar_digest"]) or \
                not isinstance(index["protocol_commit"], str) or COMMIT_PATTERN.fullmatch(index["protocol_commit"]) is None:
            raise BundleIntegrityError("date index registration digests are invalid")
        check_threshold_provenance(index["threshold_provenance"])
        snapshot = check_snapshot(index["snapshot"])
        if not is_hex64(snapshot["projection_sha256"]) or \
                parse_instant(snapshot["latest_retrieved_at"]) > parse_instant(snapshot["bound"]):
            raise BundleIntegrityError("date index snapshot provenance is invalid")
        audit = index["audit"]
        if not isinstance(audit, dict) or set(audit) != {"status", "v1_bundle_id"} or \
                audit["status"] != AUDIT_STATUS or not is_hex64(audit["v1_bundle_id"]):
            raise BundleIntegrityError("date index audit result is invalid")
        fingerprint = index["index_id"]
        content = {key: value for key, value in index.items() if key != "index_id"}
        if not is_hex64(fingerprint) or digest(canonical_bytes(content)) != fingerprint or \
                (directory is not None and Path(directory).name != fingerprint):
            raise BundleIntegrityError("sealed date index fingerprint mismatch")
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        if isinstance(exc, BundleIntegrityError):
            raise
        raise BundleIntegrityError(f"date index validation failed: {exc}") from exc
    return index


def index_entry(index: dict, value: object) -> dict:
    """Format and range first (ValueError), then registration (LookupError)."""
    selected = validate_cutoff(value)
    entry = next((entry for entry in index["entries"] if entry["date"] == selected), None)
    if entry is None:
        raise LookupError("date is not registered in the sealed index")
    return entry


def _check_bound_bundle(index: dict, entry: dict, bundle: dict) -> None:
    registration = bundle.get("registration", {})
    if bundle["immutable_bundle_id"] != entry["bundle_id"] or bundle["cutoff_date"] != entry["date"] or \
            bundle["cutoff_at"] != entry["cutoff_at"]:
        raise BundleIntegrityError("indexed bundle differs from its index entry")
    if bundle["threshold_provenance"] != index["threshold_provenance"] or bundle["snapshot"] != index["snapshot"]:
        raise BundleIntegrityError("indexed bundle provenance differs from the index")
    if not isinstance(registration, dict) or registration.get("protocol_sha256") != index["protocol_sha256"] or \
            registration.get("protocol_commit") != index["protocol_commit"]:
        raise BundleIntegrityError("indexed bundle registration differs from the index")


def default_bundles_dir(index_directory: Path) -> Path:
    return Path(index_directory).absolute().parent.parent / "bundles"


def load_indexed_bundle(index: dict, value: object, *, bundles_dir: Path, repo_root: Path = REPO,
                        allowed_codes: Sequence[str] | None = None) -> dict:
    """Date to its indexed fingerprint only; never a path built from the request."""
    entry = index_entry(index, value)
    bundle = load_dated_bundle(Path(bundles_dir) / entry["bundle_id"], repo_root=repo_root,
                               allowed_codes=allowed_codes, expected_date=entry["date"])
    _check_bound_bundle(index, entry, bundle)
    return bundle


def load_date_index(directory: Path, *, repo_root: Path = REPO, bundles_dir: Path | None = None,
                    allowed_codes: Sequence[str] | None = None, verify_bundles: bool = True) -> dict:
    directory = Path(directory).absolute()
    index = verify_index_structure(_read_json(directory / "index.json", directory, "date index"), directory)
    if verify_bundles:
        base = bundles_dir if bundles_dir is not None else default_bundles_dir(directory)
        for entry in index["entries"]:
            load_indexed_bundle(index, entry["date"], bundles_dir=base, repo_root=repo_root,
                                allowed_codes=allowed_codes)
    return index


def write_date_index(base: Path, index: dict, *, repo_root: Path = REPO, bundles_dir: Path | None = None,
                     allowed_codes: Sequence[str] | None = None) -> Path:
    verify_index_structure(index)
    base = Path(base).absolute()
    bundles = bundles_dir if bundles_dir is not None else base.parent / "bundles"
    for entry in index["entries"]:
        load_indexed_bundle(index, entry["date"], bundles_dir=bundles, repo_root=repo_root,
                            allowed_codes=allowed_codes)
    return _publish(base, index["index_id"], "index.json", canonical_bytes(index),
                    lambda path: verify_index_structure(_read_json(path / "index.json", path, "date index"), path))
