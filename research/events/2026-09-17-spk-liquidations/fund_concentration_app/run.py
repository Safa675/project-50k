"""Extend an existing sealed local review with registered descriptive holdings.

Original reports and outputs remain private. No download or detector calibration.
"""
from __future__ import annotations

import argparse
import calendar
import json
import re
import subprocess
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Sequence

from p50k.providers.security_holdings import SecurityHoldingsSnapshot, read_security_holdings
from p50k.providers.thf_holdings import PositionedWord
from p50k.research_reviews.bundle import (
    EVENT_REL, SourceRegistry, digest, publication_time, require_opened, safe_file,
    validate_universe,
)
from p50k.research_reviews.bundle_v2 import (
    extend_bundle, load_research_bundle, write_research_bundle,
)
from p50k.research_reviews.concentration import concentration_finding
from p50k.research_reviews.contracts import CUTOFF_AT

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
PROTOCOL_REL = EVENT_REL / "fund_concentration_app/PROTOCOL.md"
ALLOWLIST_REL = EVENT_REL / "top100_funds.txt"
RUNTIME_FILES = (
    EVENT_REL / "fund_concentration_app/run.py",
    Path("services/p50k/providers/security_holdings.py"),
    Path("services/p50k/providers/thf_holdings.py"),
    Path("services/p50k/providers/kap_report.py"),
    Path("services/p50k/research_reviews/concentration.py"),
    Path("services/p50k/research_reviews/bundle_v2.py"),
)


@dataclass(frozen=True)
class MonthlyCandidate:
    period: str
    published_at: str
    disclosure_id: str
    timing_assumption: str | None


def monthly_candidates(listing: object) -> tuple[list[list[MonthlyCandidate]], list[str]]:
    """Choose reporting periods before reading numbers; never parse-success fallback."""
    if not isinstance(listing, list) or any(not isinstance(row, dict) or
            not isinstance(row.get("disclosureBasic"), dict) for row in listing):
        return [], ["report_list_missing_or_invalid"]
    cutoff = datetime.fromisoformat(CUTOFF_AT)
    grouped: dict[str, list[MonthlyCandidate]] = {}
    reasons = []
    for row in listing:
        basic = row["disclosureBasic"]
        if basic.get("period") != "AB":
            continue
        try:
            year, month = int(basic.get("year")), int(basic.get("donem"))
            month_end = date(year, month, calendar.monthrange(year, month)[1])
        except (TypeError, ValueError, OverflowError):
            reasons.append("monthly_period_invalid")
            continue
        if month_end > cutoff.date():
            continue
        published, assumption = publication_time(basic.get("publishDate"))
        if published is None:
            reasons.append("monthly_publication_missing_or_invalid")
            continue
        if datetime.fromisoformat(published) > cutoff:
            continue
        if datetime.fromisoformat(published).date() < month_end:
            reasons.append("monthly_publication_precedes_period_end")
            continue
        index = str(basic.get("disclosureIndex"))
        if re.fullmatch(r"[1-9][0-9]*", index) is None:
            reasons.append("monthly_disclosure_id_invalid")
            continue
        period = month_end.strftime("%Y-%m")
        grouped.setdefault(period, []).append(MonthlyCandidate(period, published, index, assumption))
    return [grouped[period] for period in sorted(grouped, reverse=True)[:2]], sorted(set(reasons))


def _git(repo: Path, *args: str) -> bytes:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=False)
    if result.returncode:
        raise ValueError("concentration protocol and runtime must be committed")
    return result.stdout


def verify_registration(repo: Path) -> tuple[list[str], dict]:
    hashes = {}
    for relative in (PROTOCOL_REL, ALLOWLIST_REL, *RUNTIME_FILES):
        committed = _git(repo, "show", f"HEAD:{relative.as_posix()}")
        if safe_file(repo / relative, repo).read_bytes() != committed:
            raise ValueError(f"concentration runtime differs from committed HEAD: {relative}")
        hashes[relative.as_posix()] = digest(committed)
    selected = validate_universe((repo / ALLOWLIST_REL).read_text().split())
    return selected, {
        "protocol_sha256": hashes[PROTOCOL_REL.as_posix()],
        "protocol_commit": _git(repo, "log", "-1", "--format=%H", "HEAD", "--",
                                PROTOCOL_REL.as_posix()).decode().strip(),
        "git_head": _git(repo, "rev-parse", "HEAD").decode().strip(),
        "code_manifest": hashes,
    }


def _normalized(text: str) -> str:
    decomposed = "".join(char for char in unicodedata.normalize("NFKD", text)
                         if not unicodedata.combining(char)).casefold().replace("ı", "i")
    return re.sub(r"[^a-z0-9]+", " ", decomposed).strip()


def printed_monthly_period(text: str) -> str | None:
    """The source header must say one recognized month/year; filenames are not proof."""
    names = {name: index for index, name in enumerate((
        "ocak", "subat", "mart", "nisan", "mayis", "haziran", "temmuz", "agustos",
        "eylul", "ekim", "kasim", "aralik"), 1)}
    normalized = _normalized(text)
    months = "|".join(names)
    found = set()
    for month, year in re.findall(rf"\b({months})\s+(\d{{4}})\b", normalized):
        found.add(f"{year}-{names[month]:02d}")
    for year, month in re.findall(rf"\b(\d{{4}})\s+({months})\b", normalized):
        found.add(f"{year}-{names[month]:02d}")
    return next(iter(found)) if len(found) == 1 else None


def printed_fund_identity(header: str, introduction: str, code: str, name: str) -> bool:
    """Exact printed code may establish identity when the recorded name changed.

    A contradictory masthead code cannot be bypassed by a matching body name.
    Codes mentioned in holdings/body text do not become header identity evidence.
    """
    if not _normalized(name):
        return False
    printed_codes = set(re.findall(r"(?m)^\s*([A-Z0-9]{3})\s*[-–—]\s*\S", header))
    if printed_codes:
        return printed_codes == {code}
    return _normalized(name) in _normalized(introduction)


def _listing(repo: Path, code: str, codes: list[str], registry: SourceRegistry):
    require_opened(code, codes)
    root = repo / "raw/kap/reports"
    paths = (root / code / "kap_report_list.json", root / f"kap_portfolio_reports_{code}.body")
    for path in paths:
        if path.exists():
            safe_file(path, root)
            ref = registry.add(path, "KAP_SERIES", fund_code=code)
            try:
                return json.loads(path.read_bytes()), ref
            except (ValueError, UnicodeDecodeError):
                return None, ref
    return None, None


def _snapshot(repo: Path, code: str, name: str, selected: list[str],
              candidates: list[MonthlyCandidate], registry: SourceRegistry):
    require_opened(code, selected)
    if not candidates:
        return None, None, ["eligible_monthly_report_missing"]
    if len(candidates) != 1:
        return None, None, ["selected_monthly_period_ambiguous"]
    chosen = candidates[0]
    root = repo / "raw/kap/reports" / code
    matching = [path for path in root.glob(f"{chosen.period}_{chosen.disclosure_id}*.pdf")
                if re.fullmatch(rf"{re.escape(chosen.period)}_{chosen.disclosure_id}(?:_\d+)?\.pdf", path.name)]
    if len(matching) != 1:
        return None, None, ["selected_pdf_missing" if not matching else "selected_pdf_attachments_ambiguous"]
    path = safe_file(matching[0], root)
    data = path.read_bytes()
    if not data.startswith(b"%PDF-"):
        return None, None, ["selected_pdf_signature_invalid"]
    ref = registry.add(path, "KAP_PDF", fund_code=code, published_at=chosen.published_at,
                       disclosure_id=chosen.disclosure_id, expected_sha256=digest(data))
    def failed(reason: str):
        snapshot = SecurityHoldingsSnapshot(
            chosen.period, datetime.fromisoformat(chosen.published_at), str(path), digest(data),
            (), None, None, (reason,), (), False, None,
        )
        return snapshot, ref, []
    import fitz  # Installed research extra; no import during provider unit tests.
    try:
        with fitz.open(stream=data, filetype="pdf") as document:
            if not 1 <= len(document) <= 250:
                return failed("selected_pdf_page_bound_exceeded")
            first_page = document[0]
            if (float(first_page.rect.width), float(first_page.rect.height)) != (950.0, 1200.0):
                return failed("unsupported_page_geometry")
            # The audited monthly masthead ends above y=80. Inception dates in
            # section I are body metadata and cannot establish report periods.
            monthly_header = first_page.get_text("text", clip=(0, 0, 950, 80))
            introduction = first_page.get_text("text")[:2000]
            if not printed_fund_identity(monthly_header, introduction, code, name):
                return failed("selected_pdf_fund_identity_unverified")
            printed_period = printed_monthly_period(monthly_header)
            if printed_period is None:
                return failed("selected_pdf_monthly_period_unverified")
            if printed_period != chosen.period:
                return failed("selected_pdf_monthly_period_mismatch")
            words = []
            sizes = []
            for index, page in enumerate(document, 1):
                sizes.append((float(page.rect.width), float(page.rect.height)))
                words.extend(PositionedWord(index, float(w[0]), float(w[1]), float(w[2]),
                                            float(w[3]), w[4]) for w in page.get_text("words"))
                if len(words) > 200000:
                    return failed("selected_pdf_word_bound_exceeded")
            snapshot = read_security_holdings(
                words, page_sizes=sizes, report_period=chosen.period,
                published_at=datetime.fromisoformat(chosen.published_at), source_path=str(path),
                source_sha256=digest(data),
            )
    except (ValueError, RuntimeError):
        return failed("selected_pdf_read_failed")
    return snapshot, ref, []


def run_research(*, base_bundle: Path, repo_root: Path = REPO,
                 out_dir: Path | None = None, codes: Sequence[str] | None = None) -> dict:
    repo = repo_root.resolve()
    selected, registration = verify_registration(repo)
    if codes is not None and list(codes) != selected:
        raise ValueError("only the entire registered opened universe is supported")
    output = repo / "raw/research/fund-review-app"
    if out_dir is not None and out_dir.absolute() != output.absolute():
        raise ValueError("concentration output must use the canonical private bundle directory")
    if not base_bundle.absolute().is_relative_to(output.absolute()):
        raise ValueError("base bundle must be an existing canonical private bundle")
    base = load_research_bundle(base_bundle, allowed_codes=selected)
    if base.get("concentration_extension_schema") is not None:
        raise ValueError("concentration extends an original v1 bundle, not an earlier extension")
    registry = SourceRegistry()
    registration["base_bundle_source_id"] = registry.add(base_bundle / "bundle.json", "CODE")
    global_refs = [registry.add(repo / PROTOCOL_REL, "PROTOCOL")]
    global_refs.append(registry.add(repo / ALLOWLIST_REL, "UNIVERSE"))
    global_refs.extend(registry.add(repo / relative, "CODE") for relative in RUNTIME_FILES)
    results = {}
    for fund in base["funds"]:
        code = fund["code"]
        listing, list_ref = _listing(repo, code, selected, registry)
        periods, list_reasons = monthly_candidates(listing)
        current, current_ref, reasons = _snapshot(repo, code, fund["name"], selected,
                                                periods[0] if periods else [], registry)
        previous, previous_ref, prior_reasons = _snapshot(repo, code, fund["name"], selected,
                                                       periods[1] if len(periods) > 1 else [], registry)
        finding = concentration_finding(
            current, source_id=current_ref, previous=previous, previous_source_id=previous_ref,
            input_refs=[*global_refs, *([list_ref] if list_ref else [])],
            missing_reasons=[*list_reasons, *reasons], previous_missing_reasons=prior_reasons,
            comparison_basis_verified=False,
        )
        for group in periods:
            for candidate in group:
                if candidate.timing_assumption:
                    finding["qualifications"] = sorted(set(finding["qualifications"] + [candidate.timing_assumption]))
        results[code] = finding
    payload = extend_bundle(base, results, sources=list(registry.sources.values()),
                            manifest=list(registry.manifest.values()), registration=registration)
    destination = write_research_bundle(output, payload)
    return {"directory": str(destination), "bundle": payload}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base-bundle", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = run_research(base_bundle=args.base_bundle)
    except (ValueError, OSError, ImportError) as exc:
        parser.exit(2, f"Concentration extension refused: {type(exc).__name__}: {exc}\n")
    print(json.dumps({"directory": result["directory"],
                      "immutable_bundle_id": result["bundle"]["immutable_bundle_id"],
                      "summary": result["bundle"]["summary"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
