"""Immutable concentration extension over an unchanged v1 research bundle.

The outer seal stays v1-compatible. The independently versioned extension and its
base-source binding are checked here, without modifying manifested v1 runtime.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Mapping, Sequence

from p50k.research_reviews import bundle as core_bundle
from p50k.research_reviews.bundle import (
    BundleIntegrityError, HASH_PATTERN, canonical_bytes, digest,
    resolve_pdf, safe_file, validate_universe, write_bundle,
)
from p50k.research_reviews.concentration import CONCENTRATION_SCHEMA
from p50k.research_reviews.contracts import METADATA, SCHEMA

CONCENTRATION_COUNTS = ("concentration_available", "concentration_partial", "concentration_unavailable")


def _core_row(row: dict) -> dict:
    return {key: value for key, value in row.items() if key not in ("concentration", "evidence")}


def _preserved(base: dict, payload: dict) -> None:
    if payload.get("base_immutable_bundle_id") != base.get("immutable_bundle_id"):
        raise BundleIntegrityError("Concentration extension must bind its original base bundle")
    if payload.get("registration") != base.get("registration"):
        raise BundleIntegrityError("The original base registration cannot change")
    if [{key: row[key] for key in ("code",)} for row in payload["funds"]] != [
            {key: row[key] for key in ("code",)} for row in base["funds"]]:
        raise BundleIntegrityError("Concentration must preserve original fund ordering")
    for old, new in zip(base["funds"], payload["funds"]):
        if _core_row(old) != _core_row(new):
            raise BundleIntegrityError("Concentration cannot change original findings, comments, or charts")
        expected_evidence = sorted(set(old["evidence"] + new["concentration"]["input_refs"]))
        if new["evidence"] != expected_evidence:
            raise BundleIntegrityError("Concentration evidence must be the exact base/extension source union")
    if any(payload["summary"].get(key) != value for key, value in base["summary"].items()):
        raise BundleIntegrityError("Concentration cannot change original summary counts")
    for field in ("sources", "manifest"):
        original = {row["source_id"]: row for row in base[field]}
        merged = {row["source_id"]: row for row in payload[field]}
        if any(identifier not in merged or original[identifier] != merged[identifier] for identifier in original):
            raise BundleIntegrityError("Concentration cannot replace original manifest/source records")


def _validate_extension(payload: dict) -> None:
    marker = payload.get("concentration_extension_schema")
    if marker is None:
        if any("concentration" in row for row in payload["funds"]):
            raise BundleIntegrityError("Concentration fields require a versioned extension")
        return
    if marker != CONCENTRATION_SCHEMA:
        raise BundleIntegrityError("Unsupported concentration extension schema")
    registration = payload.get("concentration_registration")
    identifier = registration.get("base_bundle_source_id") if isinstance(registration, dict) else None
    if not isinstance(identifier, str) or HASH_PATTERN.fullmatch(identifier) is None:
        raise BundleIntegrityError("Concentration extension requires a manifest-backed base bundle")
    entry = next((entry for entry in payload["manifest"] if entry["source_id"] == identifier and
                  entry["kind"] == "CODE"), None)
    if entry is None:
        raise BundleIntegrityError("The registered base bundle source is missing")
    try:
        data = safe_file(Path(entry["original_path"])).read_bytes()
        if digest(data) != entry["sha256"]:
            raise BundleIntegrityError("Original base bundle source changed")
        base = json.loads(data)
        if base.get("schema") != SCHEMA or any(base.get(key) != value for key, value in METADATA.items()):
            raise BundleIntegrityError("Original base bundle provenance changed")
        if base.get("concentration_extension_schema") is not None:
            raise BundleIntegrityError("The concentration input must be an original unextended v1 bundle")
        content = {key: value for key, value in base.items() if key != "immutable_bundle_id"}
        if digest(canonical_bytes(content)) != base.get("immutable_bundle_id"):
            raise BundleIntegrityError("Original base bundle fingerprint mismatch")
        validate_universe([row["code"] for row in base["funds"]])
        _preserved(base, payload)
        if any(row["concentration"].get("schema") != marker for row in payload["funds"]):
            raise BundleIntegrityError("All 100 funds require the same concentration schema")
        actual = {"concentration_" + status.lower(): sum(row["concentration"]["status"] == status
                                                         for row in payload["funds"])
                  for status in ("AVAILABLE", "PARTIAL", "UNAVAILABLE")}
        if sum(actual.values()) != 100 or any(payload["summary"].get(key) != value for key, value in actual.items()):
            raise BundleIntegrityError("Concentration summary must retain all 100 funds")
    except (OSError, TypeError, KeyError, ValueError) as exc:
        if isinstance(exc, BundleIntegrityError):
            raise
        raise BundleIntegrityError("Concentration extension validation failed") from exc


def extend_bundle(base: dict, concentrations: Mapping[str, dict], *, sources: list[dict],
                  manifest: list[dict], registration: dict) -> dict:
    """Copy the original calculations; concentration never contributes crossings."""
    codes = validate_universe([row["code"] for row in base["funds"]])
    if sorted(concentrations) != codes:
        raise ValueError("Concentration extension must retain exactly the 100 opened funds")
    if base.get("concentration_extension_schema") is not None:
        raise ValueError("Concentration requires an original unextended base bundle")
    result = deepcopy(base)
    result.pop("immutable_bundle_id")
    result["base_immutable_bundle_id"] = base["immutable_bundle_id"]
    result["concentration_extension_schema"] = CONCENTRATION_SCHEMA
    result["concentration_registration"] = deepcopy(registration)
    for record in result["funds"]:
        concentration = deepcopy(concentrations[record["code"]])
        record["concentration"] = concentration
        record["evidence"] = sorted(set(record["evidence"] + concentration["input_refs"]))
    for field, additions in (("sources", sources), ("manifest", manifest)):
        merged = {row["source_id"]: row for row in result[field]}
        for row in additions:
            previous = merged.get(row["source_id"])
            if previous is not None and previous != row:
                raise BundleIntegrityError("New source registration conflicts with an original source")
            merged[row["source_id"]] = deepcopy(row)
        result[field] = sorted(merged.values(), key=lambda row: row["source_id"])
    result["summary"].update({"concentration_" + status.lower(): sum(row["concentration"]["status"] == status
                                                                      for row in result["funds"])
                              for status in ("AVAILABLE", "PARTIAL", "UNAVAILABLE")})
    result["immutable_bundle_id"] = digest(canonical_bytes(result))
    _validate_extension(result)
    return result


def load_research_bundle(directory: Path, allowed_codes: Sequence[str] | None = None) -> dict:
    payload = core_bundle.load_bundle(directory, allowed_codes=allowed_codes)
    _validate_extension(payload)
    return payload


def write_research_bundle(base: Path, payload: dict) -> Path:
    _validate_extension(payload)
    directory = write_bundle(base, payload)
    load_research_bundle(directory)
    return directory


def resolve_research_pdf(directory: Path, source_id: str,
                         allowed_codes: Sequence[str] | None = None) -> Path:
    load_research_bundle(directory, allowed_codes)
    return resolve_pdf(directory, source_id, allowed_codes)
