"""Run the preregistered THF-only conditional archive diagnostic, offline.

Real observations and results remain below gitignored raw/. Runtime files and
the protocol must match committed Git blobs before the arithmetic is invoked.
"""
from __future__ import annotations

import argparse
import calendar
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from decimal import (
    Context, Decimal, DivisionByZero, InvalidOperation, Overflow,
    ROUND_HALF_EVEN, localcontext,
)
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any
from zoneinfo import ZoneInfo


ROOT = Path(__file__).absolute().parents[4]
sys.path.insert(0, str(ROOT / "services"))
PROTOCOL = "research/events/2026-09-17-spk-liquidations/fund_holdings_divergence/PREREGISTRATION.md"
RUNTIME = (
    "research/events/2026-09-17-spk-liquidations/fund_holdings_divergence/run.py",
    "services/p50k/analytics/holdings_divergence.py",
    "services/p50k/providers/thf_holdings.py",
    "services/p50k/providers/kap_report.py",
)
LABEL_CUTOFF = date(2026, 9, 16)
EXPECTED_PERIODS = tuple(f"2025-{month:02d}" for month in range(10, 13)) + tuple(
    f"2026-{month:02d}" for month in range(1, 9))


class ResearchInputError(ValueError):
    """An input cannot be bound to the approved offline experiment."""


def canonical_path(root: Path, value: str | Path) -> Path:
    """Reject escapes and all symlink components, even an in-root symlink."""
    root = root.absolute()
    path = Path(value)
    path = path.absolute() if path.is_absolute() else (root / path).absolute()
    if ".." in path.parts or not path.is_relative_to(root):
        raise ResearchInputError("path outside the repository")
    for component in (path, *path.parents):
        if component.is_symlink():
            raise ResearchInputError("symlink input or output is prohibited")
    return path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def committed_code(root: Path, paths: tuple[str, ...]) -> dict[str, Any]:
    """Unrelated working-tree changes do not bypass or prevent this gate."""
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root,
                            capture_output=True, check=True, text=True).stdout.strip()
    records = []
    for relative in paths:
        path = canonical_path(root, relative)
        blob = subprocess.run(["git", "show", f"HEAD:{relative}"], cwd=root,
                              capture_output=True)
        if blob.returncode or not path.is_file() or blob.stdout != path.read_bytes():
            raise ResearchInputError(f"protocol/runtime is not committed: {relative}")
        records.append({"path": relative, "sha256": hashlib.sha256(blob.stdout).hexdigest()})
    return {"head": commit, "files": records}


def jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return jsonable(asdict(value))
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [jsonable(item) for item in value]
    return value


def decimal_or_missing(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ResearchInputError("boolean observation")
    parsed = Decimal(str(value))
    return parsed if parsed.is_finite() and parsed > 0 else None


def load_nav(document: dict[str, Any]) -> dict[date, Decimal | None]:
    if document.get("fund") != "THF":
        raise ResearchInputError("only THF unit NAV is authorized")
    out = {}
    for row in document["rows"]:
        if not isinstance(row, list) or len(row) != 2:
            raise ResearchInputError("invalid NAV row")
        label = date.fromisoformat(row[0])
        if label > LABEL_CUTOFF:
            continue
        if label in out:
            raise ResearchInputError("duplicate NAV label")
        out[label] = decimal_or_missing(row[1])
    return out


def identity_lookup(universe: dict[str, Any], selection: dict[str, Any]) -> dict[tuple[str, str], str]:
    if universe.get("fund_code") != "THF" or selection.get("fund_code") != "THF":
        raise ResearchInputError("security scope must be THF")
    if universe.get("symbol_to_multiple_ISIN_contradictions"):
        raise ResearchInputError("contradictory reported security identities")
    selected = selection["equity_symbols"]
    if len(selected) != len(set(selected)):
        raise ResearchInputError("duplicate selected price symbol")
    identities = {}
    for security in universe["securities"]:
        if len(security["isins"]) != 1:
            raise ResearchInputError("ambiguous reported ISIN")
        key = (security["symbol"], security["isins"][0])
        if key in identities:
            raise ResearchInputError("duplicate reported identity")
        if security["symbol"] in selected:
            identities[key] = security["symbol"]
    approved = {("IPEKE", "TRENJ"), ("KOZAL", "TRALT")}
    for alias in selection.get("alias_choices", []):
        target, isin = alias["fetch_symbol"], alias["reported_isin"]
        if target not in selected or (target, isin) not in identities:
            raise ResearchInputError("alias target is not a reported same-ISIN security")
        for old in alias["omitted_superseded_labels"]:
            if (old, target) not in approved:
                raise ResearchInputError("alias outside the registered choices")
            found = [item for item in universe["securities"] if item["symbol"] == old]
            if len(found) != 1 or found[0]["isins"] != [isin]:
                raise ResearchInputError("alias does not share the reported ISIN")
            identities[(old, isin)] = target
    return identities


def summary(window: Any) -> dict[str, Any]:
    available = [row for row in window.rows if row.metric.availability == "AVAILABLE"]
    def point(row: Any) -> dict[str, Any] | None:
        if row is None:
            return None
        with localcontext(Context(prec=128, rounding=ROUND_HALF_EVEN,
                                 traps=[InvalidOperation, DivisionByZero, Overflow])):
            return {"valuation_date": row.valuation_date,
                    "fund_row_label": row.fund_row_label,
                    "interval_number": row.interval_number,
                    "fund_return_percent": row.metric.actual_return * 100,
                    "equity_proxy_percent": row.metric.equity_proxy_return * 100,
                    "gap_percentage_points": row.metric.gap * 100}
    positive = [row for row in available if row.metric.gap > 0]
    negative = [row for row in available if row.metric.gap < 0]
    return jsonable({"available_intervals": len(available),
                     "unavailable_intervals": len(window.rows) - len(available),
                     "endpoint": point(window.rows[-1] if window.rows and
                                       window.rows[-1].metric.availability == "AVAILABLE" else None),
                     "last_available": point(available[-1] if available else None),
                     "largest_absolute_gap": point(max(available, key=lambda row: row.metric.gap.copy_abs())
                                                   if available else None),
                     "largest_positive_gap": point(max(positive, key=lambda row: row.metric.gap)
                                                   if positive else None),
                     "most_negative_gap": point(min(negative, key=lambda row: row.metric.gap)
                                                if negative else None)})


def reported_weight_summary(source: Any) -> dict[str, Any]:
    """Distinguish source rows from netted same-ISIN accounting entries."""
    assets = source.headline_total_value.value
    if not assets.is_finite() or assets <= 0:
        return {"availability": "UNAVAILABLE", "reason": "fund_net_assets_invalid"}
    with localcontext(Context(prec=80, rounding=ROUND_HALF_EVEN,
                             traps=[InvalidOperation, DivisionByZero, Overflow])):
        grouped: dict[str, Decimal] = {}
        positive_rows = Decimal(0)
        absolute_negative_rows = Decimal(0)
        negative_row_count = 0
        for row in source.rows:
            value = row.position_value.value
            grouped[row.isin] = grouped.get(row.isin, Decimal(0)) + value
            if value < 0:
                absolute_negative_rows -= value
                negative_row_count += 1
            else:
                positive_rows += value
        positive = sum((value for value in grouped.values() if value >= 0), Decimal(0))
        negative = -sum((value for value in grouped.values() if value < 0), Decimal(0))
        return jsonable({"availability": "AVAILABLE", "net_equity_weight": (positive - negative) / assets,
                         "positive_net_isin_weight": positive / assets,
                         "absolute_negative_net_isin_weight": negative / assets,
                         "gross_net_isin_weight": (positive + negative) / assets,
                         "positive_reported_row_weight": positive_rows / assets,
                         "absolute_negative_reported_row_weight": absolute_negative_rows / assets,
                         "gross_reported_position_weight": (positive_rows + absolute_negative_rows) / assets,
                         "negative_reported_position_count": negative_row_count,
                         "interpretation": "Signed accounting entries; negative values are not verified shorts"})


def run(root: Path = ROOT) -> Path:
    """Read only THF inputs, verify provenance, calculate and atomically save."""
    from p50k.analytics.holdings_divergence import (
        HoldingsSnapshot, StockPosition, build_diagnostic_windows,
    )
    from p50k.providers.thf_holdings import PositionedWord, read_thf_holdings
    import fitz
    import pandas as pd

    code = committed_code(root, (PROTOCOL, *RUNTIME))
    registration = subprocess.run(["git", "rev-parse", "898643c^{commit}"], cwd=root,
                                  capture_output=True, check=True, text=True).stdout.strip()
    registered_blob = subprocess.run(["git", "show", f"{registration}:{PROTOCOL}"], cwd=root,
                                     capture_output=True, check=True).stdout
    if registered_blob != canonical_path(root, PROTOCOL).read_bytes():
        raise ResearchInputError("protocol differs from the original preregistration")
    if subprocess.run(["git", "merge-base", "--is-ancestor", registration, code["head"]],
                      cwd=root, capture_output=True).returncode:
        raise ResearchInputError("runtime commit does not descend from preregistration")
    code["preregistration_commit"] = registration
    inputs: dict[str, dict[str, Any]] = {}

    def register(value: str | Path, expected: str | None = None) -> Path:
        path = canonical_path(root, value)
        relative = str(path.relative_to(root))
        digest = sha256(path)
        if expected is not None and digest != expected:
            raise ResearchInputError(f"source hash changed: {relative}")
        previous = inputs.get(relative)
        if previous and previous["sha256"] != digest:
            raise ResearchInputError(f"input changed during loading: {relative}")
        inputs[relative] = {"path": relative, "sha256": digest, "bytes": path.stat().st_size}
        return path

    def read_json(value: str | Path, expected: str | None = None) -> dict[str, Any]:
        return json.loads(register(value, expected).read_text(), parse_float=Decimal)

    descriptor = read_json("raw/bist/prices/THF_2025-10-01_2026-10-07.json")
    if descriptor.get("fund") != "THF" or descriptor.get("point_in_time_admitted") is not False:
        raise ResearchInputError("invalid research panel scope")
    panel_path = register(descriptor["data_path"], descriptor["data_sha256"])
    for key in ("config", "fetch_selection", "manifest"):
        item = descriptor[key]
        register(item["path"], item["sha256"])
    archive = descriptor["legacy_archive"]
    register(archive["path"], archive["sha256"])
    register(archive["acquisition_path"], archive["acquisition_sha256"])
    sources = {archive["path"]: archive["sha256"]}
    for path, item in descriptor["sdk_response_artifacts"].items():
        register(path, item["sha256"])
        sources[path] = item["sha256"]
    for item in descriptor["symbols"].values():
        register(item["canonical_path"], item["canonical_sha256"])
        register(item["receipt_path"], item["receipt_sha256"])
    selection = read_json(descriptor["fetch_selection"]["path"])
    universe = read_json(selection["source_universe_path"], selection["source_universe_sha256"])
    listing = read_json(universe["source_report_list_path"], universe["source_report_list_sha256"])
    basic_by_id = {item["disclosureBasic"]["disclosureIndex"]: item["disclosureBasic"] for item in listing}
    identity = identity_lookup(universe, selection)
    reports = universe["reports"]
    if tuple(item["report_period"] for item in reports) != EXPECTED_PERIODS:
        raise ResearchInputError("the eleven registered monthly reports are required")
    extracted, snapshots = [], []
    for report in reports:
        path = register(report["source_path"], report["source_sha256"])
        published = datetime.fromisoformat(report["publication_time_assumed_istanbul"])
        basic = basic_by_id.get(report["disclosure_index"])
        if (basic is None or basic["stockCode"] != "THF" or basic["period"] != "AB" or
                f"{basic['year']}-{int(basic['donem']):02d}" != report["report_period"] or
                datetime.strptime(basic["publishDate"], "%d.%m.%Y %H:%M:%S").replace(
                    tzinfo=ZoneInfo("Europe/Istanbul")) != published):
            raise ResearchInputError("report identity/publication differs from original KAP list")
        with fitz.open(path) as document:
            words = [PositionedWord(number, *word[:4], word[4])
                     for number, page in enumerate(document, 1)
                     for word in page.get_text("words")]
            result = read_thf_holdings(words, page_sizes=[tuple(page.rect[2:]) for page in document],
                                      report_period=report["report_period"], published_at=published,
                                      source_path=report["source_path"], source_sha256=report["source_sha256"])
        extracted.append(result)
        year, month = map(int, result.report_period.split("-"))
        positions = tuple(StockPosition(row.isin, identity.get((row.symbol, row.isin)),
                                        row.position_value.value) for row in result.rows)
        snapshots.append(HoldingsSnapshot(result.report_period,
                         date(year, month, calendar.monthrange(year, month)[1]),
                         result.published_at, result.headline_total_value.value,
                         positions, result.problems, result.futures_present))
    panel = pd.read_parquet(panel_path)
    if set(panel["Ticker"]) != set(selection["equity_symbols"]):
        raise ResearchInputError("price panel universe differs from selected scope")
    if len(panel) != descriptor["counts"]["rows"]:
        raise ResearchInputError("price panel row count changed")
    prices: dict[str, dict[date, Decimal | None]] = {}
    market = set()
    for row in panel.to_dict("records"):
        if sources.get(row["SourceArtifactPath"]) != row["SourceArtifactSHA256"]:
            raise ResearchInputError("unregistered panel source artifact")
        if row["Origin"] != "HISTORICAL_REPLAY" or row["PointInTimeAdmitted"] is not False:
            raise ResearchInputError("unapproved price origin/admission")
        session = date.fromisoformat(str(row["Date"]))
        bucket = prices.setdefault(row["Ticker"], {})
        if session in bucket:
            raise ResearchInputError("duplicate price symbol/session")
        bucket[session] = decimal_or_missing(row["Close"])
        market.add(session)
    nav_document = read_json("raw/tefas/prices/THF.json")
    nav = load_nav(nav_document)
    # No source values may change between their validation and calculation.
    for record in tuple(inputs.values()):
        register(record["path"], record["sha256"])
    code_again = committed_code(root, (PROTOCOL, *RUNTIME))
    code_again["preregistration_commit"] = registration
    if code_again != code:
        raise ResearchInputError("runtime revision changed during loading")
    windows = build_diagnostic_windows(snapshots, market_sessions=sorted(market),
                                       fund_nav_by_label=nav, prices=prices,
                                       fund_label_cutoff=LABEL_CUTOFF, max_intervals=20)
    for record in tuple(inputs.values()):
        register(record["path"], record["sha256"])
    manifest = {"fund": "THF", "code": code, "inputs": sorted(inputs.values(), key=lambda item: item["path"]),
                "max_intervals": 20, "fund_label_cutoff": LABEL_CUTOFF.isoformat()}
    bundle = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    out = canonical_path(root, f"raw/bist/THF/divergence-analysis/{bundle}/results.json")
    records = []
    extraction_by_period = {source.report_period: source for source in extracted}
    for window in windows:
        source = extraction_by_period[window.snapshot_id]
        record = jsonable(window)
        record["summary"] = summary(window)
        record["extraction"] = jsonable(source)
        record["futures_present"] = source.futures_present
        record["snapshot_reconciled"] = source.reconciled
        record["reported_equity_weights"] = reported_weight_summary(source)
        record["window_limit"] = {"maximum_following_intervals": 20,
                                  "actual_following_intervals": len(window.rows),
                                  "shortened": len(window.rows) < 20,
                                  "next_publication_date_excluded": jsonable(window.next_publication_date),
                                  "fund_label_cutoff_inclusive": LABEL_CUTOFF.isoformat()}
        record["holdings_age_days_at_baseline"] = ((window.base_date - window.reported_period_end).days
                                                  if window.base_date else None)
        record["classification"] = {"fund_anomaly": "ABSTAINED", "fraud": "ABSTAINED"}
        records.append(record)
    result = {"schema_version": 1, "fund_code": "THF", "bundle_id": bundle,
              "data_mode": "HISTORICAL_REPLAY", "diagnostic_mode": "CONDITIONAL_ARCHIVE_DIAGNOSTIC",
              "point_in_time_admitted": False, "rights_status": "UNKNOWN", "alarm_threshold": None,
              "fund_status": "ABSTAINED", "fraud_status": "ABSTAINED", "manifest": manifest,
              "runtime_dependencies": {"pandas": pd.__version__, "PyMuPDF": fitz.VersionBind,
                                       "python": sys.version},
              "market_calendar": {"basis": "observed scoped panel sessions", "certified": False,
                                  "sessions": len(market)}, "windows": records,
              "limitations": descriptor["limitations"] + [
                  "Equity-only frozen-reference-weight counterfactual; unmodeled P&L assumed zero",
                  "TEFAS prior-common-market-session valuation alignment is assumed",
                  "Negative accounting rows do not establish verified short positions",
                  "No fraud ground truth, controls, success rate or false-alarm rate"]}
    payload = (json.dumps(jsonable(result), ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        if out.read_bytes() != payload:
            raise ResearchInputError("existing bundle result has different bytes")
    else:
        temporary = canonical_path(root, out.with_suffix(".tmp"))
        temporary.write_bytes(payload)
        temporary.replace(out)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()  # No other fund or unregistered window is accepted.
    path = run()
    print(json.dumps({"result_path": str(path), "sha256": sha256(path),
                      "data_mode": "CONDITIONAL_ARCHIVE_DIAGNOSTIC",
                      "point_in_time_admitted": False}))


if __name__ == "__main__":
    main()
