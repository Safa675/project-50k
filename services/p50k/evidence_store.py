"""Immutable local evidence bundles for offline, provenance-aware replay."""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass, fields
from datetime import datetime, timezone
from decimal import Decimal, DecimalException
from pathlib import Path
from types import MappingProxyType
from typing import Iterable, Mapping

_TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})", re.IGNORECASE)
_SHA256 = re.compile(r"[0-9a-f]{64}")
_SOURCE_TIMES = ("effective_at", "published_at", "available_at", "observed_at")
_APPLICATION_ID = 0x5035304B
_COLUMNS = {
    "evidence_observations": ("observation_id", "payload", "payload_digest"),
    "evidence_bundles": ("bundle_id", "manifest", "manifest_digest", "sealed"),
    "evidence_bundle_rows": ("bundle_id", "ordinal", "observation_id"),
}


class InvalidObservation(ValueError):
    """An observation cannot be stored without inventing evidence."""


class BundleIntegrityError(ValueError):
    """Stored evidence no longer matches its sealed manifest."""


def parse_timestamp(value: str) -> datetime:
    """Accept known-offset RFC 3339 instants without truncating precision."""
    if not isinstance(value, str) or not _TIMESTAMP.fullmatch(value) or value.endswith("-00:00"):
        raise InvalidObservation("Expected RFC 3339 with a known offset and at most six fractional digits")
    if value[-1].upper() != "Z" and (int(value[-5:-3]) >= 24 or int(value[-2:]) >= 60):
        raise InvalidObservation("Invalid timestamp offset")
    try:
        instant = datetime.fromisoformat(value.upper().replace("Z", "+00:00"))
        return instant.astimezone(timezone.utc)
    except (ValueError, OverflowError) as exc:
        raise InvalidObservation("Invalid timestamp") from exc


def normalize_timestamp(value: str) -> str:
    return parse_timestamp(value).isoformat().replace("+00:00", "Z")


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidObservation(f"{name} must be a nonempty string")
    return value


def _plain(value: object) -> object:
    if isinstance(value, Mapping):
        return {_text(key, "metadata key"): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _json(value: object) -> str:
    try:
        return json.dumps(_plain(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise InvalidObservation("Metadata must be finite JSON data") from exc


def _freeze(value: object) -> object:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Observation:
    observation_key: str
    fund: str
    source_id: str
    source_version: str
    locator: str
    origin: str
    values: Mapping[str, Decimal | None]
    units: Mapping[str, str]
    effective_at: str | None
    published_at: str | None
    available_at: str | None
    observed_at: str | None
    ingested_at: str
    availability_provenance: str
    rights_status: str
    source_timestamps: Mapping[str, str | None]
    attributes: Mapping[str, object]
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in ("observation_key", "fund", "source_id", "source_version", "locator"):
            _text(getattr(self, name), name)
        if self.origin not in ("HISTORICAL_REPLAY", "SYNTHETIC"):
            raise InvalidObservation("Only historical replay and synthetic origins are supported")
        if self.availability_provenance not in ("OBSERVED", "ARCHIVE_VERIFIED", "UNKNOWN"):
            raise InvalidObservation("Invalid availability provenance")
        if self.rights_status not in ("UNKNOWN", "RESTRICTED", "APPROVED", "SYNTHETIC"):
            raise InvalidObservation("Invalid rights status")
        if (self.origin == "SYNTHETIC") != (self.rights_status == "SYNTHETIC"):
            raise InvalidObservation("Synthetic origin and rights must agree")
        if not isinstance(self.values, Mapping) or not self.values:
            raise InvalidObservation("At least one named value is required")
        checked = {}
        for name, value in self.values.items():
            _text(name, "value name")
            if value is not None and (not isinstance(value, Decimal) or not value.is_finite()):
                raise InvalidObservation("Financial values must be finite Decimal values or None")
            checked[name] = value
        if not isinstance(self.units, Mapping) or set(self.units) != set(checked):
            raise InvalidObservation("Every value must have exactly one unit")
        object.__setattr__(self, "values", MappingProxyType(checked))
        object.__setattr__(self, "units", MappingProxyType({key: _text(value, "unit") for key, value in self.units.items()}))
        if not isinstance(self.source_timestamps, Mapping):
            raise InvalidObservation("Source timestamps must be a mapping")
        originals = dict(self.source_timestamps)
        for name, value in originals.items():
            _text(name, "source timestamp name")
            if value is not None and not isinstance(value, str):
                raise InvalidObservation("Original source timestamps must be strings or None")
        for name in _SOURCE_TIMES:
            value = getattr(self, name)
            if value is not None:
                originals.setdefault(name, value)
                object.__setattr__(self, name, normalize_timestamp(value))
        object.__setattr__(self, "ingested_at", normalize_timestamp(self.ingested_at))
        if self.availability_provenance != "UNKNOWN" and self.available_at is None:
            raise InvalidObservation("Known availability needs an available_at timestamp")
        object.__setattr__(self, "source_timestamps", MappingProxyType(originals))
        if not isinstance(self.attributes, Mapping):
            raise InvalidObservation("Attributes must be a mapping")
        object.__setattr__(self, "attributes", _freeze(json.loads(_json(self.attributes))))
        if not isinstance(self.limitations, (tuple, list)):
            raise InvalidObservation("Limitations must be a sequence of strings")
        object.__setattr__(self, "limitations", tuple(_text(item, "limitation") for item in self.limitations))


def _payload(observation: Observation) -> dict:
    payload = {field.name: _plain(getattr(observation, field.name)) for field in fields(Observation)}
    payload["values"] = {key: None if value is None else format(value, "f") for key, value in observation.values.items()}
    return payload


def _identity(payload: dict) -> dict:
    return {key: value for key, value in payload.items() if key != "ingested_at"}


def _observation(payload: dict) -> Observation:
    payload = dict(payload)
    payload["values"] = {key: None if value is None else Decimal(value) for key, value in payload["values"].items()}
    return Observation(**payload)


_SCHEMA = """
CREATE TABLE IF NOT EXISTS evidence_observations (
    observation_id TEXT PRIMARY KEY, payload TEXT NOT NULL, payload_digest TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS evidence_bundles (
    bundle_id TEXT PRIMARY KEY, manifest TEXT NOT NULL, manifest_digest TEXT NOT NULL,
    sealed INTEGER NOT NULL CHECK (sealed IN (0, 1))
);
CREATE TABLE IF NOT EXISTS evidence_bundle_rows (
    bundle_id TEXT NOT NULL REFERENCES evidence_bundles(bundle_id),
    ordinal INTEGER NOT NULL,
    observation_id TEXT NOT NULL REFERENCES evidence_observations(observation_id),
    PRIMARY KEY (bundle_id, ordinal), UNIQUE (bundle_id, observation_id)
);
CREATE TRIGGER IF NOT EXISTS evidence_observations_no_update BEFORE UPDATE ON evidence_observations
BEGIN SELECT RAISE(ABORT, 'Evidence is immutable'); END;
CREATE TRIGGER IF NOT EXISTS evidence_observations_no_delete BEFORE DELETE ON evidence_observations
BEGIN SELECT RAISE(ABORT, 'Evidence is immutable'); END;
CREATE TRIGGER IF NOT EXISTS evidence_bundles_no_update BEFORE UPDATE ON evidence_bundles WHEN OLD.sealed = 1
BEGIN SELECT RAISE(ABORT, 'Bundle is sealed'); END;
CREATE TRIGGER IF NOT EXISTS evidence_bundles_no_delete BEFORE DELETE ON evidence_bundles
BEGIN SELECT RAISE(ABORT, 'Bundle is immutable'); END;
CREATE TRIGGER IF NOT EXISTS evidence_bundle_rows_no_insert BEFORE INSERT ON evidence_bundle_rows
WHEN (SELECT sealed FROM evidence_bundles WHERE bundle_id = NEW.bundle_id) = 1
BEGIN SELECT RAISE(ABORT, 'Bundle is sealed'); END;
CREATE TRIGGER IF NOT EXISTS evidence_bundle_rows_no_update BEFORE UPDATE ON evidence_bundle_rows
BEGIN SELECT RAISE(ABORT, 'Bundle is immutable'); END;
CREATE TRIGGER IF NOT EXISTS evidence_bundle_rows_no_delete BEFORE DELETE ON evidence_bundle_rows
BEGIN SELECT RAISE(ABORT, 'Bundle is immutable'); END;
"""


class EvidenceStore:
    def __init__(self, path: Path | str = ":memory:") -> None:
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path)
        try:
            tables = {row[0] for row in self._db.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")}
            objects = self._db.execute("SELECT 1 FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' LIMIT 1").fetchone()
            application_id = self._db.execute("PRAGMA application_id").fetchone()[0]
            version = self._db.execute("PRAGMA user_version").fetchone()[0]
            if objects:
                if application_id != _APPLICATION_ID or version != 1 or tables != set(_COLUMNS):
                    raise InvalidObservation("Refusing to modify a nonempty database that is not an evidence store")
                for table, expected in _COLUMNS.items():
                    actual = tuple(row[1] for row in self._db.execute(f"PRAGMA table_info({table})"))
                    if actual != expected:
                        raise InvalidObservation("Unsupported evidence-store schema")
            else:
                if application_id != 0 or version != 0:
                    raise InvalidObservation("Refusing to modify an empty database owned by another application")
                self._db.executescript(_SCHEMA)
                self._db.execute(f"PRAGMA application_id = {_APPLICATION_ID}")
                self._db.execute("PRAGMA user_version = 1")
                self._db.commit()
            self._db.execute("PRAGMA foreign_keys = ON")
        except BaseException:
            self._db.close()
            raise

    def close(self) -> None:
        self._db.close()

    def import_bundle(self, observations: Iterable[Observation], *, sources: dict[str, str],
                      imported_at: str, config: dict | None = None) -> str:
        imported_at = normalize_timestamp(imported_at)
        if not isinstance(sources, Mapping) or not sources:
            raise InvalidObservation("A bundle requires source-file hashes")
        source_hashes = {}
        for locator, digest in sources.items():
            _text(locator, "source locator")
            if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
                raise InvalidObservation("Source hashes must be lowercase SHA-256 digests")
            source_hashes[locator] = digest
        configuration = json.loads(_json({} if config is None else config))
        if not isinstance(configuration, dict):
            raise InvalidObservation("Bundle configuration must be a mapping")
        records, versions, logical_keys = {}, {}, {}
        for observation in observations:
            if not isinstance(observation, Observation):
                raise InvalidObservation("Expected Observation instances")
            if observation.locator not in source_hashes:
                raise InvalidObservation("Every observation locator must appear in the source manifest")
            payload = _payload(observation)
            identity = _json(_identity(payload))
            logical_identity = (observation.fund, observation.source_id, observation.origin)
            if (observation.observation_key in logical_keys
                    and logical_keys[observation.observation_key] != logical_identity):
                raise InvalidObservation("A logical observation cannot change fund, source or origin")
            logical_keys[observation.observation_key] = logical_identity
            key = (observation.observation_key, observation.source_version)
            if key in versions and versions[key] != identity:
                raise InvalidObservation("One source version cannot contain conflicting observations")
            versions[key] = identity
            records.setdefault(_digest(identity), payload)
        ordered = sorted(records)
        identity = {"schema_version": 1, "sources": source_hashes, "config": configuration,
                    "observations": [_identity(records[key]) for key in ordered]}
        bundle_id = _digest(_json(identity))
        if self._db.execute("SELECT 1 FROM evidence_bundles WHERE bundle_id = ?", (bundle_id,)).fetchone():
            self._load_bundle(bundle_id)
            return bundle_id
        with self._db:
            stored = []
            for key in ordered:
                row = self._db.execute("SELECT payload, payload_digest FROM evidence_observations WHERE observation_id = ?", (key,)).fetchone()
                if row is None:
                    text = _json(records[key])
                    self._db.execute("INSERT INTO evidence_observations VALUES (?, ?, ?)", (key, text, _digest(text)))
                    stored.append(records[key])
                else:
                    stored.append(self._read_observation(key, *row))
            manifest = {"schema_version": 1, "bundle_id": bundle_id, "sources": source_hashes,
                        "config": configuration, "imported_at": imported_at, "observation_count": len(stored),
                        "content_digest": _digest(_json(stored))}
            text = _json(manifest)
            self._db.execute("INSERT INTO evidence_bundles VALUES (?, ?, ?, 0)", (bundle_id, text, _digest(text)))
            self._db.executemany("INSERT INTO evidence_bundle_rows VALUES (?, ?, ?)",
                                 ((bundle_id, index, key) for index, key in enumerate(ordered)))
            self._db.execute("UPDATE evidence_bundles SET sealed = 1 WHERE bundle_id = ?", (bundle_id,))
        return bundle_id

    def _read_observation(self, observation_id: str, text: str, digest: str) -> dict:
        try:
            if _digest(text) != digest:
                raise BundleIntegrityError("Observation content digest mismatch")
            payload = json.loads(text)
            if _digest(_json(_identity(payload))) != observation_id or _json(_payload(_observation(payload))) != text:
                raise BundleIntegrityError("Observation identity or canonical form mismatch")
            return payload
        except (KeyError, TypeError, ValueError, DecimalException) as exc:
            if isinstance(exc, BundleIntegrityError):
                raise
            raise BundleIntegrityError("Invalid stored observation") from exc

    def _load_bundle(self, bundle_id: str) -> tuple[dict, list[dict]]:
        row = self._db.execute("SELECT manifest, manifest_digest, sealed FROM evidence_bundles WHERE bundle_id = ?", (bundle_id,)).fetchone()
        if row is None:
            raise KeyError(bundle_id)
        text, digest, sealed = row
        try:
            if sealed != 1 or _digest(text) != digest:
                raise BundleIntegrityError("Bundle is unsealed or its manifest digest changed")
            manifest = json.loads(text)
            rows = self._db.execute(
                "SELECT r.ordinal, r.observation_id, o.payload, o.payload_digest FROM evidence_bundle_rows r "
                "JOIN evidence_observations o ON o.observation_id = r.observation_id "
                "WHERE r.bundle_id = ? ORDER BY r.ordinal", (bundle_id,)).fetchall()
            payloads = [self._read_observation(key, payload, payload_digest) for _, key, payload, payload_digest in rows]
            if [ordinal for ordinal, *_ in rows] != list(range(len(payloads))):
                raise BundleIntegrityError("Bundle row order changed")
            identity = {"schema_version": manifest["schema_version"], "sources": manifest["sources"],
                        "config": manifest["config"], "observations": [_identity(payload) for payload in payloads]}
            if (manifest["bundle_id"] != bundle_id or manifest["schema_version"] != 1
                    or manifest["observation_count"] != len(payloads)
                    or manifest["content_digest"] != _digest(_json(payloads))
                    or bundle_id != _digest(_json(identity))):
                raise BundleIntegrityError("Bundle content does not match the sealed identity")
            return manifest, payloads
        except (KeyError, TypeError, ValueError) as exc:
            if isinstance(exc, BundleIntegrityError):
                raise
            raise BundleIntegrityError("Invalid stored bundle") from exc

    def observations(self, bundle_id: str) -> list[Observation]:
        return [_observation(payload) for payload in self._load_bundle(bundle_id)[1]]

    def manifest(self, bundle_id: str) -> dict:
        return self._load_bundle(bundle_id)[0]
