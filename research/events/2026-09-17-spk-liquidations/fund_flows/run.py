"""Explore monthly endpoint changes in the approved, already opened KAP archive.

This is private archive arithmetic, not a historical product alarm or exact cash
flow. The committed protocol and runtime code are verified before source reads.
Real output stays in the ignored raw/kap/flow-analysis/ directory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
from collections import Counter
from datetime import datetime, timezone
from decimal import Context, Decimal, DecimalException, DivisionByZero, InvalidOperation, Overflow, ROUND_HALF_EVEN, Underflow, localcontext
from pathlib import Path
from typing import Sequence

from p50k.detectors.fund_flow import calculate_endpoint_change

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
EVENT_REL = Path("research/events/2026-09-17-spk-liquidations")
PROTOCOL_REL = EVENT_REL / "fund_flows/PROTOCOL.md"
ALLOWLIST_REL = EVENT_REL / "top100_funds.txt"
RUNTIME_FILES = (
    EVENT_REL / "fund_flows/run.py",
    Path("services/p50k/__init__.py"),
    Path("services/p50k/detectors/__init__.py"),
    Path("services/p50k/detectors/fund_flow.py"),
    Path("services/p50k/evidence_store.py"),
    Path("services/p50k/replay.py"),
)
TARGETS = frozenset({"THF", "TP2", "TLY", "DFI", "DOH", "PRY", "KHA", "PNU"})
SOURCE_MARKER = "KAP Portföy Dağılım Raporu"
SCHEMA = "p50k.fund-flow-archive.v1"
THRESHOLD = Decimal("0.10")
_CONTEXT = Context(prec=50, rounding=ROUND_HALF_EVEN, Emin=-999999, Emax=999999,
                   traps=[InvalidOperation, DivisionByZero, Overflow, Underflow])
WINDOW_START, WINDOW_END, PRE_ORDER_END = "2025-10", "2026-09", "2026-08"
UNKNOWN_REASONS = (
    "historical_availability_unknown", "currency_comparability_unknown",
    "valuation_scope_unknown", "unit_actions_unknown", "baseline_unverified",
)
WARNINGS = (
    "Exploratory archive endpoint arithmetic; not a production alert.",
    "Endpoint residual is not exact investor cash flow.",
    "Stored publication times do not establish complete historical version availability.",
    "The 10% screen is a fixed heuristic, not a validated baseline or fraud finding.",
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
        "core_sha256": manifest["services/p50k/detectors/fund_flow.py"],
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


def _validate_output(repo: Path, out: Path, sources: Sequence[Path]) -> Path:
    base = repo / "raw/kap/flow-analysis"
    resolved = out.resolve()
    if not resolved.is_relative_to(base.resolve()) or not resolved.is_relative_to(repo / "raw"):
        raise ValueError("output must be under repository raw/kap/flow-analysis")
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
    ignored = _git(repo, "check-ignore", "--", str(destination)).decode().strip()
    if not ignored:
        raise ValueError("output must be Git-ignored")
    return destination


def _number(value) -> Decimal | None:
    if value is None or isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        return None
    try:
        number = Decimal(value)
        return number if number.is_finite() else None
    except (InvalidOperation, ValueError):
        return None


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


def _reference(report: dict) -> dict:
    return {"period": report.get("period"), "disclosure_index": report.get("disclosure_index"),
            "cadence": report.get("cadence"), "published_at_raw": report.get("published_at"),
            "company_title": report.get("company_title"), "parser_problems": report.get("problems", []),
            "source_pointer": report["_archive_pointer"], "record_sha256": report["_archive_sha256"]}


def _diagnostics(previous: dict, current: dict) -> list[str]:
    diagnostics = []
    prior_end = _number(previous.get("period_end_price"))
    reported_prior = _number(current.get("previous_period_price"))
    if prior_end is not None and reported_prior is not None and prior_end != reported_prior:
        diagnostics.append("reported_previous_price_differs_from_previous_endpoint; rounding_or_archive_issue_possible")
    with localcontext(_CONTEXT):
        for name, report in (("previous", previous), ("current", current)):
            units, nav, assets = (_number(report.get(field)) for field in
                                  ("units_outstanding", "period_end_price", "total_value"))
            if all(value is not None for value in (units, nav, assets)):
                try:
                    if units * nav != assets:
                        diagnostics.append(f"{name}_units_times_nav_differs_from_assets; rounding_or_scope_issue_possible")
                except DecimalException:
                    diagnostics.append(f"{name}_units_price_identity_not_representable")
    for name, report in (("previous", previous), ("current", current)):
        if report.get("problems"):
            diagnostics.append(f"{name}_source_parser_reported_problems")
    return diagnostics


def _pair(code: str, period: str, monthly: dict[str, list[dict]], source: dict, core_version: str) -> dict:
    prior_period = previous_month(period)
    previous, current = monthly.get(prior_period, []), monthly[period]
    row = {
        "fund": code, "previous_period": prior_period, "closing_period": period,
        "endpoint_sources": {"previous": [_reference(r) for r in previous],
                             "current": [_reference(r) for r in current]},
        "source_file": source, "core_version": core_version,
        "mode": "EXPLORATORY_ARCHIVE", "production_status": "ABSTAINED",
        "production_reasons": list(UNKNOWN_REASONS), "warnings": list(WARNINGS),
        "eligibility": {name: "UNKNOWN" for name in
                        ("historical_availability", "currency", "valuation_scope", "unit_actions", "baseline")},
        "residual_unit": "UNKNOWN_CURRENCY", "rate_unit": "RATIO",
        "residual": None, "rate": None, "screen_crossing": None,
        "arithmetic_reasons": [], "diagnostics": [], "endpoint_values": None,
    }
    if not previous:
        row["arithmetic_reasons"].append("missing_previous_contiguous_month")
    if len(previous) > 1 or len(current) > 1:
        row["arithmetic_reasons"].append("ambiguous_duplicate_monthly_endpoint")
    if row["arithmetic_reasons"]:
        return row
    a, b = previous[0], current[0]
    values = {"previous_assets": _number(a.get("total_value")), "current_assets": _number(b.get("total_value")),
              "previous_nav": _number(a.get("period_end_price")), "current_nav": _number(b.get("period_end_price"))}
    row["endpoint_values"] = {name: None if value is None else str(value) for name, value in values.items()}
    missing = [f"{name}_missing_or_invalid" for name, value in values.items() if value is None]
    result = calculate_endpoint_change(values["previous_assets"], values["current_assets"],
                                       values["previous_nav"], values["current_nav"])
    row["arithmetic_reasons"] = list(dict.fromkeys([*missing, *result.reasons]))
    row["residual"] = None if result.residual is None else str(result.residual)
    row["rate"] = None if result.rate is None else str(result.rate)
    row["screen_crossing"] = None if result.rate is None else result.rate.copy_abs() >= THRESHOLD
    row["diagnostics"] = _diagnostics(a, b)
    return row


def _brief(row: dict | None) -> dict | None:
    if row is None:
        return None
    return {key: row[key] for key in ("previous_period", "closing_period", "residual", "rate", "screen_crossing")}


def summarize_fund(pairs: list[dict]) -> dict:
    valid = [row for row in pairs if row["rate"] is not None]
    latest = pairs[-1] if pairs else None
    latest_valid = valid[-1] if valid else None
    order = lambda row: (Decimal(row["rate"]).copy_abs().copy_negate(), row["closing_period"])
    peak = min(valid, key=order, default=None)
    prior = [row for row in valid if row["closing_period"] <= PRE_ORDER_END]
    pre_order = min(prior, key=order, default=None)
    return {
        "pair_count": len(pairs), "valid_pair_count": len(valid),
        "crossing_pair_count": sum(row["screen_crossing"] is True for row in valid),
        "latest_reported_pair": _brief(latest),
        "latest_screen_crossing": None if latest is None else latest["screen_crossing"],
        "latest_valid_pair": _brief(latest_valid),
        "latest_valid_pair_stale": latest_valid is not None and latest_valid is not latest,
        "historical_any_screen_crossing": any(row["screen_crossing"] for row in valid) if valid else None,
        "peak_abs_rate": None if peak is None else str(Decimal(peak["rate"]).copy_abs()),
        "peak_signed_rate": None if peak is None else peak["rate"],
        "peak_period": None if peak is None else peak["closing_period"],
        "pre_order_pair_count": len(prior),
        "pre_order_any_screen_crossing": any(row["screen_crossing"] for row in prior) if prior else None,
        "pre_order_crossing_pair_count": sum(row["screen_crossing"] is True for row in prior),
        "pre_order_peak_abs_rate": None if pre_order is None else str(Decimal(pre_order["rate"]).copy_abs()),
        "pre_order_peak_signed_rate": None if pre_order is None else pre_order["rate"],
        "pre_order_peak_period": None if pre_order is None else pre_order["closing_period"],
        "pre_order_note": "Closing months through August 2026; not a claim of availability before the order.",
    }


def analyze_fund(code: str, path: Path, repo: Path, core_version: str) -> dict:
    relative = path.relative_to(repo).as_posix()
    output = {"fund": code, "target": code in TARGETS, "fund_reasons": [], "report_issues": [],
              "ignored_weekly_reports": 0, "ignored_outside_window_reports": 0, "pairs": [],
              "source_file": {"path": relative, "sha256": None, "state": "MISSING"}}
    if not path.exists():
        output["fund_reasons"] = ["source_file_missing"]
        output["summary"] = summarize_fund([])
        return output
    if path.is_symlink() or not path.resolve().is_relative_to(repo / "raw/kap/series"):
        raise ValueError("series input must be a canonical file, not an alias")
    raw = path.read_bytes()
    output["source_file"]["sha256"] = sha256(raw)
    output["source_file"]["state"] = "PRESENT"
    try:
        payload = json.loads(raw, parse_float=Decimal, parse_constant=Decimal)
    except (ValueError, UnicodeDecodeError):
        output["fund_reasons"] = ["source_json_invalid"]
        output["source_file"]["state"] = "INVALID"
        output["summary"] = summarize_fund([])
        return output
    if not isinstance(payload, dict) or payload.get("fund") != code:
        raise ValueError("JSON fund must match selected filename/code")
    if payload.get("source") != SOURCE_MARKER:
        raise ValueError("invalid KAP source marker")
    reports = payload.get("reports")
    if not isinstance(reports, list):
        output["fund_reasons"] = ["source_reports_missing_or_invalid"]
        output["source_file"]["state"] = "INVALID"
        output["summary"] = summarize_fund([])
        return output
    output["source_file"]["origin"] = payload.get("origin", "HISTORICAL_REPLAY")
    output["source_file"]["rights_status"] = "SYNTHETIC" if payload.get("origin") == "SYNTHETIC" else "UNKNOWN"
    monthly: dict[str, list[dict]] = {}
    for index, report in enumerate(reports):
        if not isinstance(report, dict):
            output["report_issues"].append({"index": index, "reason": "report_not_an_object"})
            continue
        if report.get("cadence") == "weekly":
            output["ignored_weekly_reports"] += 1
            continue
        period = report.get("period")
        if report.get("cadence") != "monthly" or not isinstance(period, str) or not re.fullmatch(
                r"\d{4}-(?:0[1-9]|1[0-2])", period):
            output["report_issues"].append({"index": index, "reason": "monthly_period_or_cadence_invalid"})
            continue
        if period < previous_month(WINDOW_START) or period > WINDOW_END:
            output["ignored_outside_window_reports"] += 1
            continue
        record = {**report, "_archive_pointer": f"reports[{index}]", "_archive_sha256": sha256(_json_bytes(report))}
        monthly.setdefault(period, []).append(record)
    output["pairs"] = [_pair(code, period, monthly, output["source_file"], core_version)
                       for period in sorted(monthly) if WINDOW_START <= period <= WINDOW_END]
    if not reports:
        output["fund_reasons"].append("source_reports_empty")
    if not output["pairs"]:
        output["fund_reasons"].append("no_monthly_closing_endpoints_in_window")
    output["summary"] = summarize_fund(output["pairs"])
    return output


def cohort_counts(funds: list[dict]) -> dict:
    result = {}
    for label, cohort in (("known_eight_targets", [f for f in funds if f["target"]]),
                          ("other_selected_funds", [f for f in funds if not f["target"]])):
        result[label] = {
            "selected": len(cohort),
            "missing_sources": sum(f["source_file"]["state"] == "MISSING" for f in cohort),
            "invalid_sources": sum(f["source_file"]["state"] == "INVALID" for f in cohort),
            "monthly_attempts": sum(f["summary"]["pair_count"] for f in cohort),
            "valid_pairs": sum(f["summary"]["valid_pair_count"] for f in cohort),
            "funds_with_valid_pairs": sum(f["summary"]["valid_pair_count"] > 0 for f in cohort),
            "latest_screen_evaluable": sum(f["summary"]["latest_screen_crossing"] is not None for f in cohort),
            "latest_screen_crossing": sum(f["summary"]["latest_screen_crossing"] is True for f in cohort),
            "historical_any_screen_crossing": sum(f["summary"]["historical_any_screen_crossing"] is True for f in cohort),
            "pre_order_any_screen_crossing": sum(f["summary"]["pre_order_any_screen_crossing"] is True for f in cohort),
            "pre_order_valid_pairs": sum(f["summary"]["pre_order_pair_count"] for f in cohort),
            "latest_positive_crossings": sum(f["summary"]["latest_screen_crossing"] is True and
                                              Decimal(f["summary"]["latest_reported_pair"]["rate"]) > 0 for f in cohort),
            "latest_negative_crossings": sum(f["summary"]["latest_screen_crossing"] is True and
                                              Decimal(f["summary"]["latest_reported_pair"]["rate"]) < 0 for f in cohort),
            "positive_crossing_pairs": sum(row["screen_crossing"] is True and Decimal(row["rate"]) > 0
                                           for f in cohort for row in f["pairs"]),
            "negative_crossing_pairs": sum(row["screen_crossing"] is True and Decimal(row["rate"]) < 0
                                           for f in cohort for row in f["pairs"]),
        }
    return result


def _write_results(destination: Path, payload: dict) -> dict:
    if destination.parent.exists() and any(path.name != "results.json" for path in destination.parent.iterdir()):
        raise ValueError("run directory contains unrelated files")
    if destination.exists():
        try:
            old = json.loads(destination.read_bytes())
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
        # Hard-link creation publishes atomically without overwriting a racing file.
        os.link(temporary, destination)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return payload


def run_research(*, repo_root: Path = REPO, codes: Sequence[str] | None = None,
                 out_dir: Path | None = None, run_at: str | None = None,
                 protocol_sha256: str | None = None) -> dict:
    repo = repo_root.resolve()
    registration = verify_registration(repo)
    if protocol_sha256 is not None and protocol_sha256 != registration["protocol_sha256"]:
        raise ValueError("supplied protocol hash differs from committed protocol")
    git_head = registration.pop("git_head")
    selected = select_funds(registration.pop("allowlist"), codes)
    sources = [repo / "raw/kap/series" / f"{code}.json" for code in selected]
    output_base = out_dir if out_dir is not None else repo / "raw/kap/flow-analysis"
    _validate_output(repo, output_base, sources)
    funds = [analyze_fund(code, path, repo, registration["core_sha256"]) for code, path in zip(selected, sources)]
    ranking = sorted((f for f in funds if f["summary"]["peak_abs_rate"] is not None),
                     key=lambda f: (Decimal(f["summary"]["peak_abs_rate"]).copy_negate(), f["fund"]))
    latest_ranking = sorted((f for f in funds if f["summary"]["latest_screen_crossing"] is not None),
                            key=lambda f: (Decimal(f["summary"]["latest_reported_pair"]["rate"]).copy_abs().copy_negate(), f["fund"]))
    result = {
        "schema": SCHEMA, "mode": "EXPLORATORY_ARCHIVE", "production_status": "ABSTAINED",
        "production_reasons": list(UNKNOWN_REASONS), "warnings": list(WARNINGS),
        "registration": registration, "selected_funds": selected,
        "window": {"first_closing_month": WINDOW_START, "last_closing_month": WINDOW_END,
                   "previous_only_month": previous_month(WINDOW_START), "threshold_ratio": str(THRESHOLD)},
        "funds": funds, "cohorts": cohort_counts(funds),
        "source_manifest": {f["fund"]: f["source_file"] for f in funds},
        "ranking_by_latest_abs_rate": [f["fund"] for f in latest_ranking],
        "ranking_by_peak_abs_rate": [f["fund"] for f in ranking],
        "arithmetic_reason_counts": dict(sorted(Counter(reason for f in funds for pair in f["pairs"]
                                                         for reason in pair["arithmetic_reasons"]).items())),
    }
    result["fingerprint"] = sha256(_json_bytes(result))
    destination = _validate_output(repo, output_base / result["fingerprint"], sources)
    result["metadata"] = {"run_at_utc": run_at or datetime.now(timezone.utc).isoformat(),
                          "git_head": git_head, "output_path": str(destination)}
    return _write_results(destination, result)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--funds", nargs="+", help="optional subset of the committed top-100 allowlist")
    parser.add_argument("--out", type=Path, help="ignored directory under raw/kap/flow-analysis")
    parser.add_argument("--protocol-sha256", help="optional expected SHA-256 of the committed protocol")
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
