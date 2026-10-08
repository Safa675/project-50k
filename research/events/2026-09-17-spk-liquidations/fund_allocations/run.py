"""Explore comparable KAP monthly-average allocations in the opened archive.

This local research screen is not a historical product alert or a fraud label.
The committed protocol and runtime are checked before any source is opened.
"""
from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import os
import re
import subprocess
import tempfile
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Sequence

from p50k.detectors.fund_allocation import calculate_allocation_change
from p50k.providers.kap_allocation import TextCell, read_allocation
from p50k.providers.kap_report import normalize

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
EVENT_REL = Path("research/events/2026-09-17-spk-liquidations")
PROTOCOL_REL = EVENT_REL / "fund_allocations/PROTOCOL.md"
ALLOWLIST_REL = EVENT_REL / "top100_funds.txt"
RUNTIME_FILES = (
    EVENT_REL / "fund_allocations/run.py",
    Path("services/p50k/__init__.py"),
    Path("services/p50k/detectors/__init__.py"),
    Path("services/p50k/detectors/fund_allocation.py"),
    Path("services/p50k/providers/__init__.py"),
    Path("services/p50k/providers/kap_report.py"),
    Path("services/p50k/providers/kap_allocation.py"),
    Path("services/p50k/evidence_store.py"),
    Path("services/p50k/replay.py"),
)
TARGETS = frozenset({"THF", "TP2", "TLY", "DFI", "DOH", "PRY", "KHA", "PNU"})
SCHEMA = "p50k.fund-allocation-archive.v1"
WINDOW_START, WINDOW_END, PRE_ORDER_END = "2025-10", "2026-09", "2026-08"
BASIS = "MONTHLY_AVERAGE"
UNKNOWN_REASONS = (
    "historical_availability_unknown", "source_scope_comparability_unknown",
    "historical_category_mapping_unverified", "data_rights_unverified",
)
WARNINGS = (
    "Exploratory archive arithmetic; not a production alert.",
    "Monthly average allocation is not a month-end portfolio snapshot.",
    "Weights can change through prices without any portfolio trades.",
    "The fixed 20 percentage-point screen is not a fraud classifier or validated baseline.",
    "Publication strings do not prove complete historical source-version availability.",
    "Other selected funds are not known-clean controls or false-positive labels.",
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git(repo: Path, *args: str) -> bytes:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=False)
    if result.returncode:
        raise ValueError("committed research inputs could not be verified")
    return result.stdout


def _committed_file(repo: Path, relative: Path) -> bytes:
    committed = _git(repo, "show", f"HEAD:{relative.as_posix()}")
    path = repo / relative
    if path.is_symlink() or path.read_bytes() != committed:
        raise ValueError(f"working file differs from committed HEAD: {relative.as_posix()}")
    return committed


def verify_registration(repo: Path) -> dict:
    protocol = _committed_file(repo, PROTOCOL_REL)
    allowlist = _committed_file(repo, ALLOWLIST_REL)
    manifest = {path.as_posix(): sha256(_committed_file(repo, path)) for path in RUNTIME_FILES}
    manifest[ALLOWLIST_REL.as_posix()] = sha256(allowlist)
    return {
        "protocol_sha256": sha256(protocol),
        "protocol_commit": _git(repo, "log", "-1", "--format=%H", "HEAD", "--",
                                PROTOCOL_REL.as_posix()).decode().strip(),
        "git_head": _git(repo, "rev-parse", "HEAD").decode().strip(),
        "code_manifest": manifest,
        "core_sha256": manifest["services/p50k/detectors/fund_allocation.py"],
        "parser_sha256": manifest["services/p50k/providers/kap_allocation.py"],
        "allowlist": allowlist.decode("utf-8").split(),
    }


def select_funds(allowlist: Sequence[str], requested: Sequence[str] | None = None) -> list[str]:
    allowed = list(allowlist)
    if not allowed or len(set(allowed)) != len(allowed) or any(
            not re.fullmatch(r"[A-Z0-9]{3}", code) for code in allowed):
        raise ValueError("invalid committed top-100 allowlist")
    selected = allowed if requested is None else list(requested)
    if not selected or len(set(selected)) != len(selected):
        raise ValueError("fund selection must be nonempty and contain no duplicates")
    if any(code not in allowed for code in selected):
        raise ValueError("fund selection must be inside the committed top-100 allowlist")
    return sorted(selected)


def _serializable(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {key: _serializable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serializable(item) for item in value]
    return value


def _json_bytes(payload: dict) -> bytes:
    return (json.dumps(_serializable(payload), sort_keys=True, ensure_ascii=False,
                       allow_nan=False, separators=(",", ":")) + "\n").encode("utf-8")


def previous_month(period: str) -> str:
    year, month = map(int, period.split("-"))
    return f"{year - (month == 1):04d}-{12 if month == 1 else month - 1:02d}"


def closing_months() -> tuple[str, ...]:
    months, period = [], WINDOW_END
    while period >= WINDOW_START:
        months.append(period)
        period = previous_month(period)
    return tuple(reversed(months))


def _canonical_input(path: Path, repo: Path) -> None:
    root = repo / "raw/kap/reports"
    if not path.resolve().is_relative_to(root) or not path.resolve().is_relative_to(repo / "raw"):
        raise ValueError("report input must be inside canonical raw/kap/reports")
    for ancestor in (path, *path.parents):
        if ancestor == repo.parent:
            break
        if ancestor.is_symlink():
            raise ValueError("report input must be a canonical file, not an alias")
    if path.exists() and not path.is_file():
        raise ValueError("report input must be a regular file")


def _validate_output(repo: Path, out: Path, sources: Sequence[Path]) -> Path:
    base = repo / "raw/kap/allocation-analysis"
    resolved = out.resolve()
    if not resolved.is_relative_to(base.resolve()) or not resolved.is_relative_to(repo / "raw"):
        raise ValueError("output must be under repository raw/kap/allocation-analysis")
    for ancestor in (out, *out.parents):
        if ancestor == repo.parent:
            break
        if ancestor.is_symlink():
            raise ValueError("output path cannot contain symlinks")
    if out.exists() and not out.is_dir():
        raise ValueError("output must be a directory")
    destination = out / "results.json"
    for source in sources:
        if resolved == source.resolve() or source.resolve().is_relative_to(resolved):
            raise ValueError("output must not alias an input file or directory")
        if destination.exists() and source.exists() and os.path.samefile(destination, source):
            raise ValueError("output must not alias an input file")
    if destination.is_symlink():
        raise ValueError("output file cannot be a symlink")
    if not _git(repo, "check-ignore", "--", str(destination)).decode().strip():
        raise ValueError("output must be Git-ignored")
    return destination


def _extract_rows(raw: bytes) -> tuple[list[TextCell], dict]:
    # Lazy import keeps synthetic tests and service imports standard-library only.
    import pymupdf

    with pymupdf.open(stream=raw, filetype="pdf") as document:
        cells = []
        for page_number, page in enumerate(document, 1):
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    text = " ".join(span["text"] for span in line["spans"]).strip()
                    if text:
                        cells.append(TextCell(page_number, *line["bbox"], text))
        return cells, {"pages": document.page_count, "creator": document.metadata.get("creator"),
                       "pymupdf_version": pymupdf.VersionBind}


_MONTHS = {name: number for number, name in enumerate((
    "OCAK", "SUBAT", "MART", "NISAN", "MAYIS", "HAZIRAN", "TEMMUZ", "AGUSTOS",
    "EYLUL", "EKIM", "KASIM", "ARALIK"), 1)}


def _identity_text(text: str) -> str:
    return re.sub(r"[^A-Z0-9]+", " ", normalize(text)).strip()


def _pdf_identity(cells: Sequence[TextCell], code: str, period: str, basic: dict) -> dict:
    # Only the first-page heading/fund-information section may identify the fund
    # and report period. Footer timestamps and security tables are not evidence.
    header, period_header = [], []
    period_section_closed = False
    for cell in sorted((cell for cell in cells if cell.page == 1), key=lambda cell: (cell.y0, cell.x0)):
        text = normalize(cell.text)
        if re.match(r"(?:II|2)\s*[-.) :]+", text):
            break
        if re.match(r"(?:I|1)\s*[-.) :]+\s*FON", text):
            period_section_closed = True
        if not period_section_closed:
            period_header.append(cell.text)
        header.append(cell.text)
        if len(header) >= 150:
            break
    joined = _identity_text(" ".join(period_header))
    title = basic.get("companyTitle")
    normalized_title = _identity_text(title) if isinstance(title, str) else ""
    title_match = False
    if normalized_title:
        for start in range(len(header)):
            for end in range(start + 1, min(start + 6, len(header)) + 1):
                candidate = _identity_text(" ".join(header[start:end]))
                candidate = re.sub(r"^(?:[A-Z]\s+)?FONUN\s+ADI\s*", "", candidate)
                candidate = re.sub(rf"^{re.escape(code)}\s+", "", candidate).strip()
                if candidate == normalized_title:
                    title_match = True
                    break
            if title_match:
                break
    reasons = []
    if basic.get("stockCode") != code:
        reasons.append("metadata_fund_identity_unverified")
    if not title_match:
        reasons.append("pdf_full_fund_title_missing_or_mismatched")
    found_periods = set()
    for month_name, month in _MONTHS.items():
        for expression in (rf"\b{month_name}\s+(\d{{4}})\b", rf"\b(\d{{4}})\s+{month_name}\b"):
            for match in re.finditer(expression, joined):
                found_periods.add(f"{int(match.group(1)):04d}-{month:02d}")
    # One observed layout names an explicit full-month date interval instead.
    original = normalize(" ".join(period_header))
    interval = re.search(r"RAPOR DONEMI\s*[:\-]?\s*(\d{2})/(\d{2})/(\d{4})\s+VE\s+(\d{2})/(\d{2})/(\d{4})", original)
    if interval:
        first_day, first_month, first_year, last_day, last_month, last_year = map(int, interval.groups())
        if (1 <= first_year <= 9999 and 1 <= first_month <= 12 and first_day == 1
                and (first_year, first_month) == (last_year, last_month)
                and last_day == calendar.monthrange(first_year, first_month)[1]):
            found_periods.add(f"{first_year:04d}-{first_month:02d}")
    if not found_periods:
        reasons.append("pdf_report_period_unverified")
    elif found_periods != {period}:
        reasons.append("pdf_report_period_ambiguous_or_mismatched")
    return {"metadata_stock_code": basic.get("stockCode"), "full_title_matched": title_match,
            "printed_report_periods": sorted(found_periods), "problems": reasons}


def _read_pdf(path: Path, repo: Path, code: str, period: str, basic: dict) -> dict:
    _canonical_input(path, repo)
    raw = path.read_bytes()
    source = {"path": path.relative_to(repo).as_posix(), "sha256": sha256(raw), "bytes": len(raw)}
    try:
        cells, extraction = _extract_rows(raw)
        table = read_allocation(cells)
        identity = _pdf_identity(cells, code, period, basic)
    except Exception as exc:
        # A damaged or unsupported document is an explicit missing endpoint.
        return {"source": source, "weights": None, "category_schema": None, "basis": None,
                "source_rows": [], "extraction": None, "identity": None,
                "problems": [f"pdf_extraction_failed:{type(exc).__name__}"]}
    return {"source": source, "weights": None if identity["problems"] else table.weights,
            "category_schema": table.category_schema, "basis": table.basis,
            "problems": [*table.problems, *identity["problems"]], "extraction": extraction, "identity": identity,
            "source_rows": [asdict(row) for row in table.source_rows]}


def _reference(report: dict) -> dict:
    return {key: report.get(key) for key in (
        "period", "cadence", "disclosure_index", "published_at_raw", "company_title",
        "metadata_pointer", "metadata_record_sha256", "basis", "category_schema", "problems",
        "attachments", "selected_attachment_path",
    )}


def _pair(code: str, period: str, monthly: dict[str, list[dict]], source: dict, core_version: str) -> dict:
    prior_period = previous_month(period)
    previous, current = monthly.get(prior_period, []), monthly.get(period, [])
    row = {
        "fund": code, "previous_period": prior_period, "closing_period": period,
        "endpoint_sources": {"previous": [_reference(r) for r in previous],
                             "current": [_reference(r) for r in current]},
        "source_file": source, "core_version": core_version,
        "mode": "EXPLORATORY_ARCHIVE", "origin": "HISTORICAL_REPLAY", "rights_status": "UNKNOWN",
        "production_status": "ABSTAINED", "production_reasons": list(UNKNOWN_REASONS),
        "warnings": list(WARNINGS), "distance": None, "max_category_delta": None,
        "category_deltas": {}, "screen_crossing": None, "arithmetic_reasons": [],
        "endpoint_weights": None, "basis": None, "category_schema": None,
    }
    if not previous:
        row["arithmetic_reasons"].append("missing_previous_contiguous_month")
    if not current:
        row["arithmetic_reasons"].append("missing_current_scheduled_month")
    if len(previous) > 1 or len(current) > 1:
        row["arithmetic_reasons"].append("ambiguous_duplicate_monthly_endpoint")
    if row["arithmetic_reasons"]:
        return row
    a, b = previous[0], current[0]
    for name, report in (("previous", a), ("current", b)):
        if report["weights"] is None:
            row["arithmetic_reasons"].append(f"{name}_allocation_missing_or_invalid")
    if a["basis"] != BASIS or b["basis"] != BASIS:
        row["arithmetic_reasons"].append("monthly_average_basis_unverified")
    if not a["category_schema"] or a["category_schema"] != b["category_schema"]:
        row["arithmetic_reasons"].append("category_schema_missing_or_mismatched")
    if row["arithmetic_reasons"]:
        return row
    row["endpoint_weights"] = {"previous": a["weights"], "current": b["weights"]}
    row["basis"], row["category_schema"] = a["basis"], a["category_schema"]
    metric = calculate_allocation_change(a["weights"], b["weights"])
    row["arithmetic_reasons"] = list(metric.reasons)
    row["distance"], row["max_category_delta"] = metric.distance, metric.max_category_delta
    row["category_deltas"] = dict(metric.category_deltas)
    row["screen_crossing"] = metric.screen_crossing
    return row


def _brief(row: dict | None) -> dict | None:
    if row is None:
        return None
    return {key: row[key] for key in (
        "previous_period", "closing_period", "distance", "max_category_delta", "screen_crossing")}


def summarize_fund(pairs: list[dict]) -> dict:
    valid = [row for row in pairs if row["distance"] is not None]
    latest = pairs[-1] if pairs else None
    reported = [row for row in pairs if row["endpoint_sources"]["current"]]
    latest_reported = reported[-1] if reported else None
    latest_valid = valid[-1] if valid else None
    order = lambda row: (row["distance"].copy_negate(), row["max_category_delta"].copy_negate(), row["closing_period"])
    peak = min(valid, key=order, default=None)
    prior = [row for row in valid if row["closing_period"] <= PRE_ORDER_END]
    pre_order = min(prior, key=order, default=None)
    return {
        "pair_count": len(pairs), "reported_closing_month_count": len(reported),
        "valid_pair_count": len(valid),
        "crossing_pair_count": sum(row["screen_crossing"] is True for row in valid),
        "latest_scheduled_pair": _brief(latest),
        "latest_screen_crossing": None if latest is None else latest["screen_crossing"],
        "latest_reported_pair": _brief(latest_reported),
        "latest_reported_screen_crossing": None if latest_reported is None else latest_reported["screen_crossing"],
        "latest_reported_pair_stale": latest_reported is not None and latest_reported is not latest,
        "latest_valid_pair": _brief(latest_valid),
        "latest_valid_pair_stale": latest_valid is not None and latest_valid is not latest,
        "historical_any_screen_crossing": any(row["screen_crossing"] for row in valid) if valid else None,
        "peak_distance": None if peak is None else peak["distance"],
        "peak_max_category_delta": None if peak is None else peak["max_category_delta"],
        "peak_period": None if peak is None else peak["closing_period"],
        "pre_order_pair_count": len(prior),
        "pre_order_any_screen_crossing": any(row["screen_crossing"] for row in prior) if prior else None,
        "pre_order_crossing_pair_count": sum(row["screen_crossing"] is True for row in prior),
        "pre_order_peak_distance": None if pre_order is None else pre_order["distance"],
        "pre_order_peak_period": None if pre_order is None else pre_order["closing_period"],
        "pre_order_note": "Closing months through August 2026; not evidence of availability before the order.",
    }


def _integer(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def analyze_fund(code: str, repo: Path, core_version: str) -> dict:
    fund_dir = repo / "raw/kap/reports" / code
    candidates = [fund_dir / "kap_report_list.json",
                  repo / "raw/kap/reports" / f"kap_portfolio_reports_{code}.body"]
    for path in candidates:
        _canonical_input(path, repo)
    present = [path for path in candidates if path.exists()]
    path = present[0] if present else candidates[0]
    source = {"path": path.relative_to(repo).as_posix(), "sha256": None, "state": "MISSING",
              "origin": "HISTORICAL_REPLAY", "rights_status": "UNKNOWN", "list_sources": []}
    output = {"fund": code, "target": code in TARGETS, "source_file": source,
              "fund_reasons": [], "report_issues": [], "reports": [], "pairs": [],
              "ignored_weekly_reports": 0, "ignored_outside_window_reports": 0}
    monthly: dict[str, list[dict]] = {}
    if not present:
        output["fund_reasons"].append("source_file_missing")
    else:
        lists = []
        for candidate in present:
            raw = candidate.read_bytes()
            source["list_sources"].append({"path": candidate.relative_to(repo).as_posix(),
                                           "sha256": sha256(raw), "bytes": len(raw)})
            try:
                lists.append(json.loads(raw, parse_float=Decimal, parse_constant=Decimal))
            except (ValueError, UnicodeDecodeError):
                lists.append(None)
        source.update(sha256=source["list_sources"][0]["sha256"], state="PRESENT")
        listing = lists[0]
        if len(lists) > 1 and any(_json_bytes({"list": other}) != _json_bytes({"list": listing}) for other in lists[1:]):
            source["state"] = "INVALID"
            output["fund_reasons"].append("ambiguous_conflicting_report_list_sources")
            listing = None
        if not isinstance(listing, list):
            source["state"] = "INVALID"
            if not output["fund_reasons"]:
                output["fund_reasons"].append("source_report_list_invalid")
        else:
            if not listing:
                output["fund_reasons"].append("source_report_list_empty")
            for offset, item in enumerate(listing):
                basic = item.get("disclosureBasic") if isinstance(item, dict) else None
                if not isinstance(basic, dict):
                    output["report_issues"].append({"index": offset, "reason": "report_metadata_invalid"})
                    continue
                # Explicit conflicting identity is rejected before any PDF read.
                if basic.get("stockCode") not in (None, "", code):
                    raise ValueError("report metadata fund must match selected filename/code")
                if basic.get("period") == "HB":
                    output["ignored_weekly_reports"] += 1
                    continue
                year, month = _integer(basic.get("year")), _integer(basic.get("donem"))
                index = _integer(basic.get("disclosureIndex"))
                if basic.get("period") != "AB" or year is None or not 1 <= year <= 9999 or month is None or not 1 <= month <= 12 or index is None or index <= 0:
                    output["report_issues"].append({"index": offset, "reason": "monthly_period_cadence_or_id_invalid"})
                    continue
                period = f"{year:04d}-{month:02d}"
                if period < previous_month(WINDOW_START) or period > WINDOW_END:
                    output["ignored_outside_window_reports"] += 1
                    continue
                expression = re.compile(rf"{period}_{index}(?:_\d+)?\.pdf")
                pdfs = sorted(pdf for pdf in fund_dir.glob(f"{period}_{index}*.pdf") if expression.fullmatch(pdf.name))
                attachments = [_read_pdf(pdf, repo, code, period, basic) for pdf in pdfs]
                plausible = [attachment for attachment in attachments if attachment["basis"] == BASIS or attachment["source_rows"]]
                selected = plausible[0] if len(plausible) == 1 else None
                problems = []
                if not attachments:
                    problems.append("report_pdf_missing")
                elif not plausible or (selected is not None and selected["weights"] is None):
                    problems.append("allocation_table_missing_or_invalid")
                elif len(plausible) > 1:
                    problems.append("ambiguous_multiple_allocation_attachments")
                record = {
                    "period": period, "cadence": "monthly", "disclosure_index": index,
                    "published_at_raw": basic.get("publishDate"), "company_title": basic.get("companyTitle"),
                    "metadata_pointer": f"[{offset}].disclosureBasic",
                    "metadata_record_sha256": sha256(_json_bytes(basic)),
                    "weights": None if selected is None else selected["weights"],
                    "basis": None if selected is None else selected["basis"],
                    "category_schema": None if selected is None else selected["category_schema"],
                    "selected_attachment_path": None if selected is None else selected["source"]["path"],
                    "problems": problems, "attachments": attachments,
                }
                output["reports"].append(record)
                monthly.setdefault(period, []).append(record)
    output["pairs"] = [_pair(code, period, monthly, source, core_version) for period in closing_months()]
    if not monthly:
        output["fund_reasons"].append("no_monthly_endpoints_in_window")
    output["summary"] = summarize_fund(output["pairs"])
    output["summary"].update(
        parsed_report_count=sum(record["weights"] is not None for record in output["reports"]),
        source_pdf_count=sum(len(record["attachments"]) for record in output["reports"]),
        duplicate_month_count=sum(len(records) > 1 for records in monthly.values()),
        ambiguous_attachment_report_count=sum(
            "ambiguous_multiple_allocation_attachments" in record["problems"] for record in output["reports"]),
    )
    return output


def cohort_counts(funds: list[dict]) -> dict:
    result = {}
    for label, cohort in (("known_eight_targets", [f for f in funds if f["target"]]),
                          ("other_selected_funds", [f for f in funds if not f["target"]])):
        result[label] = {
            "selected": len(cohort),
            "missing_sources": sum(f["source_file"]["state"] == "MISSING" for f in cohort),
            "invalid_sources": sum(f["source_file"]["state"] == "INVALID" for f in cohort),
            "present_sources": sum(f["source_file"]["state"] == "PRESENT" for f in cohort),
            "funds_with_parsed_reports": sum(f["summary"]["parsed_report_count"] > 0 for f in cohort),
            "parsed_reports": sum(f["summary"]["parsed_report_count"] for f in cohort),
            "source_pdfs": sum(f["summary"]["source_pdf_count"] for f in cohort),
            "duplicate_months": sum(f["summary"]["duplicate_month_count"] for f in cohort),
            "ambiguous_attachment_reports": sum(f["summary"]["ambiguous_attachment_report_count"] for f in cohort),
            "ignored_weekly_reports": sum(f["ignored_weekly_reports"] for f in cohort),
            "monthly_attempts": sum(f["summary"]["pair_count"] for f in cohort),
            "reported_closing_months": sum(f["summary"]["reported_closing_month_count"] for f in cohort),
            "valid_pairs": sum(f["summary"]["valid_pair_count"] for f in cohort),
            "funds_with_valid_pairs": sum(f["summary"]["valid_pair_count"] > 0 for f in cohort),
            "latest_screen_evaluable": sum(f["summary"]["latest_screen_crossing"] is not None for f in cohort),
            "latest_screen_crossing": sum(f["summary"]["latest_screen_crossing"] is True for f in cohort),
            "latest_reported_screen_evaluable": sum(f["summary"]["latest_reported_screen_crossing"] is not None for f in cohort),
            "latest_reported_screen_crossing": sum(f["summary"]["latest_reported_screen_crossing"] is True for f in cohort),
            "historical_any_screen_crossing": sum(f["summary"]["historical_any_screen_crossing"] is True for f in cohort),
            "pre_order_any_screen_crossing": sum(f["summary"]["pre_order_any_screen_crossing"] is True for f in cohort),
            "pre_order_valid_pairs": sum(f["summary"]["pre_order_pair_count"] for f in cohort),
        }
    return result


def _write_results(destination: Path, payload: dict) -> dict:
    if destination.parent.exists() and any(path.name != "results.json" for path in destination.parent.iterdir()):
        raise ValueError("run directory contains unrelated files")
    if destination.exists():
        try:
            old = json.loads(destination.read_bytes(), parse_float=Decimal)
        except (ValueError, UnicodeDecodeError) as exc:
            raise ValueError("refusing to overwrite unrelated output") from exc
        prior = {key: value for key, value in old.items() if key != "metadata"} if isinstance(old, dict) else None
        proposed = {key: value for key, value in payload.items() if key != "metadata"}
        if prior is None or old.get("schema") != SCHEMA or _json_bytes(prior) != _json_bytes(proposed):
            raise ValueError("refusing to overwrite output with a different schema or source fingerprint")
        metadata = old.get("metadata")
        if not isinstance(metadata, dict) or metadata.get("output_path") != str(destination) or any(
                not isinstance(metadata.get(name), str) or not metadata[name] for name in ("run_at_utc", "git_head")):
            raise ValueError("refusing to reuse output with unrelated or missing metadata")
        return old
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".results-", suffix=".tmp", dir=destination.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(_json_bytes(payload))
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, destination)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return payload


def run_research(*, repo_root: Path = REPO, codes: Sequence[str] | None = None,
                 out_dir: Path | None = None, run_at: str | None = None,
                 protocol_sha256: str | None = None) -> dict:
    repo = repo_root.resolve()
    registration = verify_registration(repo)
    if protocol_sha256 is None:
        raise ValueError("exact committed protocol hash is required before source reads")
    if protocol_sha256 != registration["protocol_sha256"]:
        raise ValueError("supplied protocol hash differs from committed protocol")
    git_head = registration.pop("git_head")
    selected = select_funds(registration.pop("allowlist"), codes)
    source_roots = [repo / "raw/kap/reports" / code for code in selected]
    output_base = out_dir if out_dir is not None else repo / "raw/kap/allocation-analysis"
    _validate_output(repo, output_base, source_roots)
    funds = [analyze_fund(code, repo, registration["core_sha256"]) for code in selected]
    ranking = sorted((f for f in funds if f["summary"]["peak_distance"] is not None),
                     key=lambda f: (f["summary"]["peak_distance"].copy_negate(),
                                    f["summary"]["peak_max_category_delta"].copy_negate(), f["fund"]))
    latest_ranking = sorted((f for f in funds if f["summary"]["latest_screen_crossing"] is not None),
                            key=lambda f: (f["summary"]["latest_scheduled_pair"]["distance"].copy_negate(),
                                           f["summary"]["latest_scheduled_pair"]["max_category_delta"].copy_negate(), f["fund"]))
    ranked_pairs = sorted((row for f in funds for row in f["pairs"] if row["distance"] is not None),
                          key=lambda row: (row["distance"].copy_negate(), row["max_category_delta"].copy_negate(),
                                           row["fund"], row["closing_period"]))
    result = {
        "schema": SCHEMA, "mode": "EXPLORATORY_ARCHIVE", "origin": "HISTORICAL_REPLAY",
        "rights_status": "UNKNOWN", "production_status": "ABSTAINED",
        "production_reasons": list(UNKNOWN_REASONS), "warnings": list(WARNINGS),
        "registration": registration, "selected_funds": selected,
        "window": {"first_closing_month": WINDOW_START, "last_closing_month": WINDOW_END,
                   "previous_only_month": previous_month(WINDOW_START),
                   "distance_threshold_ratio": "0.20", "single_category_threshold_ratio": "0.20",
                   "required_basis": BASIS, "scheduled_pairs_per_fund": len(closing_months())},
        "funds": funds, "cohorts": cohort_counts(funds),
        "source_manifest": {f["fund"]: {"report_list": f["source_file"], "pdfs": [
            attachment["source"] for report in f["reports"] for attachment in report["attachments"]]} for f in funds},
        "ranking_by_latest_distance": [f["fund"] for f in latest_ranking],
        "ranking_by_peak_distance": [f["fund"] for f in ranking],
        "ranking_by_distance": [{"fund": row["fund"], **_brief(row)} for row in ranked_pairs],
        "arithmetic_reason_counts": dict(sorted(Counter(reason for f in funds for pair in f["pairs"]
                                                         for reason in pair["arithmetic_reasons"]).items())),
        "pdf_parser_reason_counts": dict(sorted(Counter(reason for f in funds for report in f["reports"]
                                                         for attachment in report["attachments"]
                                                         for reason in attachment["problems"]).items())),
        "report_reason_counts": dict(sorted(Counter(reason for f in funds for report in f["reports"]
                                                     for reason in report["problems"]).items())),
    }
    result = _serializable(result)
    result["fingerprint"] = sha256(_json_bytes(result))
    destination = _validate_output(repo, output_base / result["fingerprint"], source_roots)
    result["metadata"] = {"run_at_utc": run_at or datetime.now(timezone.utc).isoformat(),
                          "git_head": git_head, "output_path": str(destination)}
    return _write_results(destination, result)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--funds", nargs="+", help="optional subset of the committed top-100 allowlist")
    parser.add_argument("--out", type=Path, help="ignored directory under raw/kap/allocation-analysis")
    parser.add_argument("--protocol-sha256", required=True, help="exact SHA-256 of the committed protocol")
    args = parser.parse_args(argv)
    try:
        result = run_research(codes=args.funds, out_dir=args.out, protocol_sha256=args.protocol_sha256)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Research run refused: {exc}\n")
    print(json.dumps({"selected_funds": len(result["selected_funds"]), "cohorts": result["cohorts"],
                      "arithmetic_reason_counts": result["arithmetic_reason_counts"],
                      "output_path": result["metadata"]["output_path"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
