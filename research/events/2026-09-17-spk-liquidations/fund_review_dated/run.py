"""Seal the registered dated D1 view: 12 bundles plus one date index; never download.

Run from an LF repository root with PYTHONPATH=services, after the protocol and this
runtime are committed. Phase 1 reads only the 100 opened price files and the
bounded snapshot. Phase 2 reads only the named v1 bundle.json and compares it at
2026-09-16. Output stays under ignored raw/research/fund-review-dated/.
"""
from __future__ import annotations

import argparse
import importlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Sequence

from p50k.jobs.fund_snapshots import default_db_path
from p50k.research_reviews.bundle import (
    EVENT_REL, canonical_bytes, digest, load_frozen_detector, read_fund_json, require_opened, safe_file,
    validate_universe,
)
from p50k.research_reviews.contracts import METADATA, SCHEMA
from p50k.research_reviews.dated_bundle import (
    DatedSourceRegistry, bounded_snapshot, build_threshold_provenance, make_date_index,
    results_d1_thresholds, verify_dated_payload, write_date_index, write_dated_bundle,
)
from p50k.research_reviews.dated_contracts import (
    AUDIT_STATUS, DATE_RULE, DEFAULT_DATE, SNAPSHOT_BOUND, WINDOW_END, grid_dates, is_hex64,
)
from p50k.research_reviews.dated_review import assemble_dated, calendar_dates

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
DATED_REL = EVENT_REL / "fund_review_dated"
PROTOCOL_REL = DATED_REL / "PROTOCOL.md"
RUNNER_REL = DATED_REL / "run.py"
ALLOWLIST_REL = EVENT_REL / "top100_funds.txt"
CALIBRATION_REL = EVENT_REL / "price_detectors/results.json"
DETECTOR_REL = EVENT_REL / "price_detectors/detectors.py"
PREREGISTRATION_REL = EVENT_REL / "price_detectors/PREREGISTRATION.md"
DATED_MODULES = tuple(Path("services/p50k/research_reviews") / name for name in (
    "dated_contracts.py", "dated_review.py", "dated_comments.py", "dated_bundle.py"))
V1_RUNTIME = (
    Path("services/p50k/research_reviews/__init__.py"), Path("services/p50k/research_reviews/contracts.py"),
    Path("services/p50k/research_reviews/bundle.py"), Path("services/p50k/research_reviews/comments.py"),
    Path("services/p50k/detectors/fund_flow.py"), Path("services/p50k/evidence_store.py"),
    Path("services/p50k/replay.py"),
)
REGISTERED = (PROTOCOL_REL, RUNNER_REL, *DATED_MODULES, *V1_RUNTIME, DETECTOR_REL, PREREGISTRATION_REL,
              CALIBRATION_REL, ALLOWLIST_REL)


def _module_name(relative: Path) -> str:
    """services/p50k/a/b.py -> p50k.a.b; a package __init__.py names the package."""
    parts = list(relative.with_suffix("").parts[1:])
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


EXECUTED_RUNTIME = tuple((_module_name(relative), relative) for relative in (*DATED_MODULES, *V1_RUNTIME))
OUTPUT_REL = Path("raw/research/fund-review-dated")
V1_OUTPUT_REL = Path("raw/research/fund-review-app")
PRICE_ROOT_REL = Path("raw/tefas/prices")
AUDIT_KINDS = ("PRICE", "UNIVERSE", "CALIBRATION")


def _git(repo: Path, *args: str) -> bytes:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=False)
    if result.returncode:
        raise ValueError("dated protocol or runtime is not committed")
    return result.stdout


def verify_registration(repo: Path) -> tuple[list[str], dict, dict]:
    """LF preflight, committed-bytes gate and results.json hash bindings."""
    working = {}
    for relative in REGISTERED:
        path = repo / relative
        if not path.is_file():
            raise ValueError(f"registered file is missing: {relative.as_posix()}")
        data = safe_file(path, repo).read_bytes()
        if b"\r\n" in data:
            raise ValueError(f"registered file has CRLF line endings; seal only from an LF checkout: "
                             f"{relative.as_posix()}")
        working[relative] = data
    manifest = {}
    for relative in REGISTERED:
        committed = _git(repo, "show", f"HEAD:{relative.as_posix()}")
        if working[relative] != committed:
            raise ValueError(f"registered file differs from committed HEAD: {relative.as_posix()}")
        manifest[relative.as_posix()] = digest(committed)
    selected = validate_universe(working[ALLOWLIST_REL].decode("utf-8").split())
    stored = json.loads(working[CALIBRATION_REL])
    if stored.get("detectors_sha256") != manifest[DETECTOR_REL.as_posix()]:
        raise ValueError("stored calibration does not bind the frozen detector source")
    if stored.get("preregistration_sha256") != manifest[PREREGISTRATION_REL.as_posix()]:
        raise ValueError("stored calibration does not bind the committed preregistration")
    if stored.get("run_at_utc") != SNAPSHOT_BOUND:
        raise ValueError("snapshot bound differs from the stored calibration run time")
    commit = _git(repo, "log", "-1", "--format=%H", "HEAD", "--", PROTOCOL_REL.as_posix()).decode().strip()
    if not commit:
        raise ValueError("dated protocol has no commit")
    registration = {"protocol_sha256": manifest[PROTOCOL_REL.as_posix()], "protocol_commit": commit,
                    "git_head": _git(repo, "rev-parse", "HEAD").decode().strip(), "date_rule": DATE_RULE,
                    "code_manifest": manifest}
    return selected, registration, working


def executed_sources() -> list[tuple[Path, Path]]:
    """(file actually executed, registered repo path) for this runner and every imported runtime module."""
    executed = [(Path(__file__), RUNNER_REL)]
    for name, relative in EXECUTED_RUNTIME:
        module = sys.modules.get(name) or importlib.import_module(name)
        location = getattr(module, "__file__", None)
        if not location:
            raise ValueError(f"executed module has no source file: {relative.as_posix()}")
        executed.append((Path(location), relative))
    return executed


def verify_executed_runtime(committed: dict) -> None:
    """The code that runs comes from sys.path, not repo_root: its bytes must equal the committed blobs.

    `committed` holds the registered bytes that verify_registration found equal to
    `git show HEAD:<path>`, so byte equality here binds the executed files to HEAD.
    """
    for path, relative in executed_sources():
        if path.read_bytes() != committed[relative]:
            raise ValueError(f"executed module differs from the committed copy: {relative.as_posix()}")


def _canonical_output(repo: Path, out_dir: Path | None) -> Path:
    output = repo / OUTPUT_REL
    if out_dir is not None and Path(out_dir).absolute() != output.absolute():
        raise ValueError("output must be the canonical private fund-review-dated directory")
    if any(path.is_symlink() for path in (output, *output.parents)):
        raise ValueError("output cannot contain symlinks")
    for probe in (output / "bundles" / "probe.json", output / "index" / "probe.json"):
        result = subprocess.run(["git", "-C", str(repo), "check-ignore", "-q", "--", str(probe)],
                                capture_output=True, check=False)
        if result.returncode != 0:
            raise ValueError("dated research output must be Git-ignored")
    return output


def protocol_guard(output: Path, protocol_sha256: str) -> None:
    """No sealed index in the canonical output may record a different protocol."""
    root = output / "index"
    if not root.is_dir():
        return
    for directory in sorted(root.iterdir()):
        if directory.name.startswith("."):
            continue
        try:
            recorded = json.loads(safe_file(directory / "index.json", directory).read_bytes()).get("protocol_sha256")
        except (ValueError, OSError, AttributeError) as exc:
            raise ValueError("an existing sealed index is unreadable; refusing to seal") from exc
        if recorded != protocol_sha256:
            raise ValueError("a sealed index records a different protocol; a changed protocol needs a new "
                             "versioned protocol file")


class PhaseOne:
    """In-memory phase-1 result: the grid, the 12 payloads and their canonical digests."""

    def __init__(self, selected: list[str], grid: list[str], calendar_digest: str, payloads: list[dict],
                 digests: list[str]):
        self.selected, self.grid, self.calendar_digest = selected, grid, calendar_digest
        self.payloads, self.digests = payloads, digests


def phase_one(repo: Path, selected: list[str], registration: dict, working: dict,
              snapshot_db: Path) -> PhaseOne:
    """Price files of the opened funds and the bounded snapshot only; no KAP, no v1 bundle."""
    registry = DatedSourceRegistry()
    # PREREGISTRATION.md is a PROTOCOL source so that the audited kinds match v1.
    kinds = [(PROTOCOL_REL, "PROTOCOL"), (ALLOWLIST_REL, "UNIVERSE"), (CALIBRATION_REL, "CALIBRATION"),
             (PREREGISTRATION_REL, "PROTOCOL"), (DETECTOR_REL, "CODE"),
             *((relative, "CODE") for relative in (RUNNER_REL, *DATED_MODULES, *V1_RUNTIME))]
    global_refs = [registry.add(repo / relative, kind, expected_sha256=digest(working[relative]))
                   for relative, kind in kinds]
    if not Path(snapshot_db).is_file():
        raise ValueError("the snapshot database is required for names and categories")
    projection, latest = bounded_snapshot(snapshot_db, selected, SNAPSHOT_BOUND)
    if latest is None:
        raise ValueError("no snapshot row lies at or before the bound")
    global_refs.append(registry.add(snapshot_db, "SNAPSHOT", snapshot_codes=selected, snapshot_bound=SNAPSHOT_BOUND,
                                    retrieved_at=latest, expected_sha256=digest(projection)))
    identities = json.loads(projection)
    stored = json.loads(working[CALIBRATION_REL])
    targets = stored.get("targets")
    if not isinstance(targets, list) or len(targets) != 8 or len(set(targets)) != 8 or             any(code not in selected for code in targets):
        raise ValueError("results.json must name eight opened targets")
    stored_targets = stored.get("results")
    for key in ("D1", "targets"):
        stored_targets = stored_targets.get(key) if isinstance(stored_targets, dict) else None
    if not isinstance(stored_targets, dict) or any(
            not isinstance(stored_targets.get(code), dict) or not isinstance(identities.get(code), dict) or
            identities[code].get("category") != stored_targets[code].get("category") for code in targets):
        raise ValueError("bounded target categories differ from results.json categories")
    prices, price_refs = {}, {}
    root = repo / PRICE_ROOT_REL
    for code in selected:
        payload, path = read_fund_json(code, selected, root, kind="PRICE")
        prices[code] = payload
        refs = list(global_refs)
        if payload is not None:
            refs.append(registry.add(path, "PRICE", fund_code=code, retrieved_at=payload.get("retrieved_at"),
                                     expected_sha256=payload.get("_source_sha256")))
        price_refs[code] = refs
    calendar = calendar_dates(prices, WINDOW_END)
    grid = grid_dates(calendar)
    provenance = build_threshold_provenance(working[CALIBRATION_REL], working[DETECTOR_REL],
                                            working[PREREGISTRATION_REL])
    thresholds = results_d1_thresholds(working[CALIBRATION_REL])
    snapshot = {"bound": SNAPSHOT_BOUND, "latest_retrieved_at": latest, "projection_sha256": digest(projection)}
    detector = load_frozen_detector(repo)
    payloads = [assemble_dated(selected, cutoff_date=cutoff, grid=grid, price_payloads=prices,
                               identities=identities, thresholds=thresholds, price_refs=price_refs,
                               sources=list(registry.sources.values()), manifest=list(registry.manifest.values()),
                               detector=detector, registration=registration, threshold_provenance=provenance,
                               snapshot=snapshot) for cutoff in grid]
    return PhaseOne(selected, grid, digest(canonical_bytes(calendar)), payloads,
                    [digest(canonical_bytes(payload)) for payload in payloads])


def _audit_refs(refs: list[str], sources: dict[str, dict]) -> list[tuple]:
    mapped = {(sources[ref]["kind"], sources[ref]["fund_code"], sources[ref]["sha256"])
              for ref in refs if sources[ref]["kind"] in AUDIT_KINDS}
    return sorted(mapped, key=lambda item: (item[0], item[1] or "", item[2]))


def v1_bundle_directory(repo: Path, v1_bundle: Path) -> Path:
    """Checked by name only, before phase 1; nothing is opened."""
    directory = Path(v1_bundle).absolute()
    if directory.parent != (repo / V1_OUTPUT_REL).absolute() or not is_hex64(directory.name):
        raise ValueError("--v1-bundle must name a sealed bundle directory under raw/research/fund-review-app")
    return directory


def read_v1_bundle(repo: Path, v1_bundle: Path) -> dict:
    """Only bundle.json of the named sealed v1 bundle; its sources are verified by run_app.py --check."""
    directory = v1_bundle_directory(repo, v1_bundle)
    payload = json.loads(safe_file(directory / "bundle.json", directory).read_bytes())
    if not isinstance(payload, dict) or payload.get("schema") != SCHEMA or \
            any(payload.get(key) != value for key, value in METADATA.items()):
        raise ValueError("--v1-bundle is not a fixed-cutoff v1 research bundle")
    content = {key: value for key, value in payload.items() if key != "immutable_bundle_id"}
    if payload.get("immutable_bundle_id") != directory.name or digest(canonical_bytes(content)) != directory.name:
        raise ValueError("--v1-bundle fingerprint mismatch")
    return payload


def compare_with_v1(dated: dict, v1_payload: dict) -> list[str]:
    """Field names that differ at 2026-09-16; values are never reported."""
    differences = set()
    dated_rows = {row["code"]: row for row in dated["funds"]}
    v1_rows = {row["code"]: row for row in v1_payload.get("funds", [])}
    if set(dated_rows) != set(v1_rows):
        differences.add("code")
    dated_sources = {source["source_id"]: source for source in dated["sources"]}
    v1_sources = {source["source_id"]: source for source in v1_payload.get("sources", [])}
    for code in sorted(set(dated_rows) & set(v1_rows)):
        new, old = dated_rows[code], v1_rows[code]
        for field in ("name", "category", "chart"):
            if new.get(field) != old.get(field):
                differences.add(field)
        old_d1 = old.get("d1", {})
        for field in sorted(set(new["d1"]) | set(old_d1)):
            if field != "input_refs" and new["d1"].get(field) != old_d1.get(field):
                differences.add(f"d1.{field}")
        try:
            if _audit_refs(new["d1"]["input_refs"], dated_sources) != _audit_refs(old_d1["input_refs"], v1_sources):
                differences.add("d1.input_refs")
        except (KeyError, TypeError):
            differences.add("d1.input_refs")
    return sorted(differences)


def phase_two(repo: Path, first: PhaseOne, v1_bundle: Path) -> dict:
    v1_payload = read_v1_bundle(repo, v1_bundle)
    dated = first.payloads[first.grid.index(DEFAULT_DATE)]
    differences = compare_with_v1(dated, v1_payload)
    if differences:
        raise ValueError("v1 equivalence audit failed; differing fields: " + ", ".join(differences))
    if [digest(canonical_bytes(payload)) for payload in first.payloads] != first.digests:
        raise ValueError("phase-1 payloads changed during the audit")
    return {"status": AUDIT_STATUS, "v1_bundle_id": v1_payload["immutable_bundle_id"]}


def run_research(*, v1_bundle: Path, repo_root: Path = REPO, snapshot_db: Path | None = None,
                 out_dir: Path | None = None, codes: Sequence[str] | None = None) -> dict:
    repo = Path(repo_root).resolve()
    selected, registration, working = verify_registration(repo)
    verify_executed_runtime(working)
    if codes is not None:
        for code in codes:
            require_opened(code, selected)
        if sorted(codes) != selected:
            raise ValueError("the dated view must retain exactly the 100 opened funds")
    output = _canonical_output(repo, out_dir)
    protocol_guard(output, registration["protocol_sha256"])
    v1_bundle_directory(repo, v1_bundle)
    first = phase_one(repo, selected, registration, working,
                      Path(snapshot_db) if snapshot_db is not None else default_db_path())
    audit = phase_two(repo, first, v1_bundle)
    # Seal only after every payload and the audit passed; bundles first, index last.
    for payload in first.payloads:
        verify_dated_payload(payload, repo_root=repo, allowed_codes=selected)
    directories = [write_dated_bundle(output / "bundles", payload, repo_root=repo, allowed_codes=selected)
                   for payload in first.payloads]
    index = make_date_index(first.payloads, protocol_sha256=registration["protocol_sha256"],
                            protocol_commit=registration["protocol_commit"], calendar_digest=first.calendar_digest,
                            v1_bundle_id=audit["v1_bundle_id"])
    directory = write_date_index(output / "index", index, repo_root=repo, bundles_dir=output / "bundles",
                                 allowed_codes=selected)
    return {"index": index, "index_directory": str(directory), "bundle_directories": [str(d) for d in directories],
            "grid": first.grid}


def _ascii(text: str) -> str:
    return text.encode("ascii", "backslashreplace").decode("ascii")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    parser.add_argument("--v1-bundle", required=True, type=Path,
                        help="exact sealed v1 bundle directory, verified beforehand with run_app.py --check")
    parser.add_argument("--snapshot-db", type=Path, help="existing read-only snapshot database")
    parser.add_argument("--out", type=Path, help="canonical ignored fund-review-dated directory")
    args = parser.parse_args(argv)
    try:
        result = run_research(v1_bundle=args.v1_bundle, snapshot_db=args.snapshot_db, out_dir=args.out)
    except (ValueError, OSError, ImportError) as exc:
        parser.exit(2, _ascii(f"Dated research refused: {type(exc).__name__}: {exc}") + "\n")
    print(json.dumps({"index_directory": result["index_directory"], "index_id": result["index"]["index_id"],
                      "grid": result["grid"], "audit": result["index"]["audit"]["status"]},
                     sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
