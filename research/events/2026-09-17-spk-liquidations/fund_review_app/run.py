"""Seal the committed, fixed-cutoff local top-100 research view; never download.

Run from the repository root with PYTHONPATH=services. Output and source copies
stay under ignored raw/research/fund-review-app/<fingerprint>/.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from decimal import Decimal
from pathlib import Path
from typing import Sequence

from p50k.jobs.fund_snapshots import default_db_path
from p50k.research_reviews.bundle import (
    EVENT_REL, SourceRegistry, assemble, digest, load_frozen_detector, read_fund_json,
    reconcile_report_list, require_opened, safe_file, selected_reports, selected_snapshot,
    validate_universe, write_bundle,
)

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
PROTOCOL_REL = EVENT_REL / "fund_review_app/PROTOCOL.md"
ALLOWLIST_REL = EVENT_REL / "top100_funds.txt"
CALIBRATION_REL = EVENT_REL / "price_detectors/results.json"
DETECTOR_REL = EVENT_REL / "price_detectors/detectors.py"
RUNTIME_FILES = (
    EVENT_REL / "fund_review_app/run.py", Path("services/p50k/research_reviews/__init__.py"),
    Path("services/p50k/research_reviews/contracts.py"), Path("services/p50k/research_reviews/bundle.py"),
    Path("services/p50k/research_reviews/comments.py"), Path("services/p50k/detectors/fund_flow.py"),
    Path("services/p50k/evidence_store.py"), Path("services/p50k/replay.py"),
)


def _git(repo: Path, *args: str) -> bytes:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=False)
    if result.returncode:
        raise ValueError("research protocol or implementation is not committed")
    return result.stdout


def verify_registration(repo: Path) -> tuple[list[str], dict]:
    manifests = {}
    for relative in (PROTOCOL_REL, ALLOWLIST_REL, CALIBRATION_REL, DETECTOR_REL, *RUNTIME_FILES):
        committed = _git(repo, "show", f"HEAD:{relative.as_posix()}")
        path = safe_file(repo / relative, repo)
        if path.read_bytes() != committed:
            raise ValueError(f"research input/code differs from committed HEAD: {relative.as_posix()}")
        manifests[relative.as_posix()] = digest(committed)
    selected = validate_universe((repo / ALLOWLIST_REL).read_text(encoding="utf-8").split())
    stored = json.loads((repo / CALIBRATION_REL).read_bytes())
    if stored.get("detectors_sha256") != manifests[DETECTOR_REL.as_posix()]:
        raise ValueError("stored calibration does not bind the frozen detector source")
    registration = {"protocol_sha256": manifests[PROTOCOL_REL.as_posix()],
                    "protocol_commit": _git(repo, "log", "-1", "--format=%H", "HEAD", "--",
                                            PROTOCOL_REL.as_posix()).decode().strip(),
                    "git_head": _git(repo, "rev-parse", "HEAD").decode().strip(),
                    "code_manifest": manifests}
    return selected, registration


def _report_list(repo: Path, code: str, selected: list[str], registry: SourceRegistry) -> object:
    require_opened(code, selected)
    root = repo / "raw/kap/reports"
    paths = (root / code / "kap_report_list.json", root / f"kap_portfolio_reports_{code}.body")
    for path in paths:
        if path.exists():
            safe_file(path, root)
            registry.add(path, "KAP_SERIES", fund_code=code)
            try:
                return json.loads(path.read_bytes())
            except (ValueError, UnicodeDecodeError):
                return None
    return None


def run_research(*, repo_root: Path = REPO, snapshot_db: Path | None = None,
                 out_dir: Path | None = None, codes: Sequence[str] | None = None) -> dict:
    repo = repo_root.resolve()
    selected, registration = verify_registration(repo)
    if codes is not None:
        for code in codes:
            require_opened(code, selected)
        if sorted(codes) != selected:
            raise ValueError("the app bundle must retain exactly the 100 opened funds")
    output = out_dir if out_dir is not None else repo / "raw/research/fund-review-app"
    canonical_output = repo / "raw/research/fund-review-app"
    if output.absolute() != canonical_output.absolute() or any(path.is_symlink() for path in (output, *output.parents)):
        raise ValueError("output must be the canonical private fund-review-app directory")
    if not _git(repo, "check-ignore", "--", str(output / "bundle.json")).strip():
        raise ValueError("research output must be Git-ignored")
    registry = SourceRegistry()
    global_refs = []
    for relative, kind in ((PROTOCOL_REL, "PROTOCOL"), (ALLOWLIST_REL, "UNIVERSE"),
                           (CALIBRATION_REL, "CALIBRATION"), (DETECTOR_REL, "CODE")):
        global_refs.append(registry.add(repo / relative, kind))
    for relative in RUNTIME_FILES:
        global_refs.append(registry.add(repo / relative, "CODE"))
    db = snapshot_db if snapshot_db is not None else default_db_path()
    identities = {}
    if db.exists():
        identities = json.loads(selected_snapshot(db, selected))
        retrieved = [row["retrieved_at"] for row in identities.values() if isinstance(row.get("retrieved_at"), str)]
        global_refs.append(registry.add(db, "SNAPSHOT", snapshot_codes=selected,
                                       retrieved_at=max(retrieved, default=None)))
    prices, reports, price_refs, kap_refs = {}, {}, {}, {}
    for code in selected:
        payload, path = read_fund_json(code, selected, repo / "raw/tefas/prices", kind="PRICE")
        prices[code] = payload
        refs = list(global_refs)
        if path.exists():
            refs.append(registry.add(path, "PRICE", fund_code=code,
                                     retrieved_at=payload.get("retrieved_at") if payload is not None else None,
                                     expected_sha256=payload.get("_source_sha256") if payload else None))
        price_refs[code] = refs
        payload, path = read_fund_json(code, selected, repo / "raw/kap/series", kind="KAP_SERIES")
        if path.exists():
            kap_refs[code] = registry.add(path, "KAP_SERIES", fund_code=code,
                                         expected_sha256=payload.get("_source_sha256") if payload else None)
        payload = reconcile_report_list(payload, _report_list(repo, code, selected, registry))
        reports[code] = payload
        monthly, _ = selected_reports(payload)
        for period, candidates in monthly.items():
            for candidate in candidates:
                index = str(candidate.get("disclosure_index"))
                if not re.fullmatch(r"[1-9][0-9]*", index):
                    continue
                report_root = repo / "raw/kap/reports" / code
                # The immutable evidence copy is limited to selected eligible endpoints.
                for pdf in sorted(report_root.glob(f"{period}_{index}*.pdf")):
                    if not re.fullmatch(rf"{re.escape(period)}_{re.escape(index)}(?:_\d+)?\.pdf", pdf.name):
                        continue
                    safe_file(pdf, report_root)
                    registry.add(pdf, "KAP_PDF", fund_code=code,
                                 published_at=candidate["_published_at"], disclosure_id=index)
    calibration = json.loads((repo / CALIBRATION_REL).read_bytes(), parse_float=Decimal)
    thresholds = calibration.get("thresholds", {}).get("D1", {})
    result = assemble(selected, price_payloads=prices, report_payloads=reports, identities=identities,
                      thresholds=thresholds, price_refs=price_refs, kap_refs=kap_refs,
                      sources=list(registry.sources.values()), manifest=list(registry.manifest.values()),
                      detector=load_frozen_detector(repo), registration=registration)
    directory = write_bundle(output, result)
    return {"bundle": result, "directory": str(directory)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--snapshot-db", type=Path, help="existing read-only snapshot database")
    parser.add_argument("--out", type=Path, help="canonical ignored fund-review-app directory")
    args = parser.parse_args(argv)
    try:
        result = run_research(snapshot_db=args.snapshot_db, out_dir=args.out)
    except (ValueError, OSError, ImportError) as exc:
        parser.exit(2, f"Research bundle refused: {exc}\n")
    print(json.dumps({"directory": result["directory"], "summary": result["bundle"]["summary"],
                      "immutable_bundle_id": result["bundle"]["immutable_bundle_id"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
