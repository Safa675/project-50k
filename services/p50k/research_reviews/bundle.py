"""Fixed-cutoff arithmetic and immutable, private manifest-backed bundles.

Nothing here emits a production event or upgrades historical availability. The
runner commits its bounded protocol/code before calling this module on real data.
Imports remain standard-library-only; frozen D1/numpy is loaded during analysis.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import re
import shutil
import sqlite3
import tempfile
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path
from typing import Mapping, Sequence

from p50k.detectors.fund_flow import calculate_endpoint_change
from p50k.research_reviews.comments import describe, finding_order, summarize
from p50k.research_reviews.contracts import CUTOFF_AT, CUTOFF_DATE, METADATA, SCHEMA, empty_finding

ISTANBUL = timezone(timedelta(hours=3))
HASH_PATTERN = re.compile(r"[0-9a-f]{64}")
CODE_PATTERN = re.compile(r"[A-Z0-9]{3}")
FLOW_THRESHOLD = Decimal("0.10")
EVENT_REL = Path("research/events/2026-09-17-spk-liquidations")
ENDPOINT_FIELDS = ("period", "cadence", "disclosure_index", "published_at", "total_value", "period_end_price",
                   "currency", "assets_unit", "nav_unit", "fund_scope", "share_class", "valuation_basis",
                   "asset_basis", "nav_basis", "valuation_timezone", "distribution_status",
                   "unit_change_status", "merger_status", "units")


class BundleIntegrityError(ValueError):
    """A sealed bundle or one of its source versions is no longer trustworthy."""


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False,
                       separators=(",", ":")) + "\n").encode("utf-8")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def number(value: object) -> Decimal | None:
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        return None
    try:
        # A failed string conversion signals InvalidOperation even when caught.
        # Keep that signal local: parsing must neither dirty nor clear the caller's
        # Decimal flags, and caller trap choices must not change missingness.
        with localcontext():
            result = Decimal(value)
    except (InvalidOperation, ValueError):
        return None
    return result if result.is_finite() else None


def validate_universe(codes: Sequence[str], *, expected_count: int = 100) -> list[str]:
    selected = list(codes)
    if len(selected) != expected_count or len(set(selected)) != len(selected) or any(
            not isinstance(code, str) or CODE_PATTERN.fullmatch(code) is None for code in selected):
        raise ValueError("universe must contain exactly 100 unique opened fund codes")
    return sorted(selected)


def require_opened(code: str, allowlist: Sequence[str]) -> None:
    if not isinstance(code, str) or CODE_PATTERN.fullmatch(code) is None or code not in allowlist:
        raise ValueError("fund is outside the opened universe")


def read_fund_json(code: str, allowlist: Sequence[str], root: Path, *, kind: str) -> tuple[dict | None, Path]:
    """Membership is checked before even resolving or testing a fund input path."""
    require_opened(code, allowlist)
    path = root / f"{code}.json"
    if not path.exists():
        return None, path
    safe_file(path, root)
    raw = path.read_bytes()
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        return {"fund": code, "_invalid": True, "_source_sha256": digest(raw)}, path
    if not isinstance(payload, dict) or payload.get("fund") != code:
        return {"fund": code, "_invalid": True, "_source_sha256": digest(raw)}, path
    expected = "TEFAS fonFiyatBilgiGetir" if kind == "PRICE" else "KAP Portföy Dağılım Raporu"
    if payload.get("source") != expected:
        return {"fund": code, "_invalid": True, "_source_sha256": digest(raw)}, path
    payload["_source_sha256"] = digest(raw)
    return payload, path


def safe_file(path: Path, root: Path | None = None) -> Path:
    path = path.absolute()
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise BundleIntegrityError("source paths cannot contain symlinks")
    if root is not None and not path.resolve().is_relative_to(root.absolute().resolve()):
        raise BundleIntegrityError("source escapes its approved root")
    if not path.is_file():
        raise BundleIntegrityError("manifest source file is missing")
    return path


def publication_time(value: object) -> tuple[str | None, str | None]:
    if not isinstance(value, str) or not value.strip():
        return None, None
    try:
        parsed = datetime.fromisoformat(value)
        interpretation = None
        if parsed.tzinfo is None:
            # Only the provider's exact timestamp format has a bounded assumption.
            parsed = datetime.strptime(value, "%d.%m.%Y %H:%M:%S").replace(tzinfo=ISTANBUL)
            interpretation = "publication_timezone_assumed_europe_istanbul"
    except ValueError:
        try:
            parsed = datetime.strptime(value, "%d.%m.%Y %H:%M:%S").replace(tzinfo=ISTANBUL)
            interpretation = "publication_timezone_assumed_europe_istanbul"
        except ValueError:
            return None, None
    return parsed.isoformat(), interpretation


def selected_reports(payload: dict | None) -> tuple[dict[str, list[dict]], list[str]]:
    result: dict[str, list[dict]] = {"2026-07": [], "2026-08": []}
    reasons = []
    if payload is None:
        return result, ["kap_series_missing"]
    reports = payload.get("reports")
    if payload.get("_invalid") or not isinstance(reports, list):
        return result, ["kap_series_invalid"]
    reasons.extend(payload.get("_report_list_reasons", []))
    cutoff = datetime.fromisoformat(CUTOFF_AT)
    for report in reports:
        if not isinstance(report, dict) or report.get("period") not in result:
            continue
        if str(report.get("cadence", "")).upper() not in ("MONTHLY", "AB"):
            continue
        published, assumption = publication_time(report.get("published_at"))
        if published is None:
            reasons.append(f"{report['period']}_publication_missing_or_invalid")
            continue
        if datetime.fromisoformat(published) > cutoff:
            continue
        item = dict(report)
        item["_published_at"] = published
        item["_publication_assumption"] = assumption
        # Digest the eligible record, not its position in a mutable full archive.
        projection = {field: report.get(field) for field in ENDPOINT_FIELDS}
        units = report.get("units") if isinstance(report.get("units"), dict) else {}
        projection["units"] = {field: units.get(field) for field in ("total_value", "nav")}
        item["_record_sha256"] = digest(canonical_bytes(projection))
        result[report["period"]].append(item)
    return result, sorted(set(reasons))


def reconcile_report_list(payload: dict | None, listing: object) -> dict | None:
    """Do not inherit the old extractor's one-record-per-month deduplication.

    Independently listed monthly disclosures missing from the extracted series
    remain candidates with missing numbers. That makes duplicate eligible reports
    or incomplete selected reports unavailable, rather than silently picking one.
    """
    if payload is None:
        return payload
    if not isinstance(payload.get("reports"), list):
        return {**payload, "_invalid": True, "reports": []}
    result = {**payload, "reports": list(payload["reports"])}
    if not isinstance(listing, list) or any(not isinstance(record, dict) or
                                            not isinstance(record.get("disclosureBasic"), dict) for record in listing):
        result["_report_list_reasons"] = ["report_list_missing_or_invalid"]
        return result
    result["_report_list_reasons"] = []
    result["_report_list_qualifications"] = []
    existing = {(report.get("period"), str(report.get("disclosure_index"))) for report in result["reports"]
                if isinstance(report, dict)}
    listed_eligible = set()
    for record in listing:
        basic = record.get("disclosureBasic", {}) if isinstance(record, dict) else {}
        if basic.get("period") != "AB" or str(basic.get("year")) != "2026":
            continue
        try:
            period = f"2026-{int(basic.get('donem')):02d}"
        except (TypeError, ValueError):
            continue
        identifier = str(basic.get("disclosureIndex"))
        if period not in ("2026-07", "2026-08") or not identifier.isdigit():
            continue
        listed_publication, interpretation = publication_time(basic.get("publishDate"))
        if listed_publication is not None and datetime.fromisoformat(listed_publication) > datetime.fromisoformat(CUTOFF_AT):
            continue
        if interpretation:
            result["_report_list_qualifications"].append("report_list_publication_timezone_assumed_europe_istanbul")
        listed_eligible.add((period, identifier))
        if (period, identifier) in existing:
            matching = [record for record in result["reports"] if isinstance(record, dict) and
                        record.get("period") == period and str(record.get("disclosure_index")) == identifier]
            if any(publication_time(record.get("published_at"))[0] != listed_publication for record in matching):
                result["_report_list_reasons"].append("report_list_series_publication_mismatch")
            continue
        result["reports"].append({"period": period, "cadence": "monthly",
                                   "disclosure_index": int(identifier), "published_at": basic.get("publishDate")})
        existing.add((period, identifier))
    for record in result["reports"]:
        if not isinstance(record, dict) or record.get("period") not in ("2026-07", "2026-08") or str(record.get("cadence", "")).upper() not in ("MONTHLY", "AB"):
            continue
        published, _ = publication_time(record.get("published_at"))
        if published is not None and datetime.fromisoformat(published) <= datetime.fromisoformat(CUTOFF_AT):
            if (record["period"], str(record.get("disclosure_index"))) not in listed_eligible:
                result["_report_list_reasons"].append("eligible_series_endpoint_missing_from_report_list")
    result["_report_list_reasons"] = sorted(set(result["_report_list_reasons"]))
    result["_report_list_qualifications"] = sorted(set(result["_report_list_qualifications"]))
    return result


def _comparability(previous: dict, current: dict) -> tuple[list[str], list[str]]:
    reasons, qualifications = [], ["baseline_unverified", "endpoint_estimate_not_reported_cash"]
    for field in ("currency", "assets_unit", "nav_unit", "fund_scope", "share_class",
                  "valuation_basis", "asset_basis", "nav_basis", "valuation_timezone"):
        values = [record.get(field) for record in (previous, current)]
        known = [value for value in values if isinstance(value, str) and value.upper() not in
                 ("", "UNKNOWN", "UNVERIFIED")]
        if len(known) == 2 and known[0] != known[1]:
            reasons.append(f"{field}_mismatch")
        if len(known) != 2:
            qualifications.append(f"{field}_unknown_common_report_field_assumption")
    for record in (previous, current):
        for field in ("distribution_status", "unit_change_status", "merger_status"):
            value = record.get(field)
            if value is None or str(value).upper() in ("", "UNKNOWN", "UNVERIFIED"):
                qualifications.append(f"{field}_unknown")
            elif value != "VERIFIED_NONE":
                reasons.append(f"{field}_incompatible")
        if record.get("valuation_basis") not in (None, "UNKNOWN", "UNVERIFIED", "MONTH_END"):
            reasons.append("valuation_basis_incompatible")
        if record.get("asset_basis") not in (None, "UNKNOWN", "UNVERIFIED", "NET_ASSETS"):
            reasons.append("asset_basis_incompatible")
        if record.get("nav_basis") not in (None, "UNKNOWN", "UNVERIFIED", "RAW_TRANSACTION_NAV"):
            reasons.append("nav_basis_incompatible")
        explicit_units = record.get("units") if isinstance(record.get("units"), dict) else {}
        for field, nested in (("assets_unit", "total_value"), ("nav_unit", "nav")):
            if explicit_units.get(nested) and record.get(field) and explicit_units[nested] != record[field]:
                reasons.append(f"{field}_incompatible")
        currency = record.get("currency")
        assets_unit = record.get("assets_unit") or explicit_units.get("total_value")
        nav_unit = record.get("nav_unit") or explicit_units.get("nav")
        if currency and currency not in ("UNKNOWN", "UNVERIFIED"):
            if assets_unit and assets_unit not in (currency, "UNKNOWN", "UNVERIFIED"):
                reasons.append("assets_unit_incompatible")
            if nav_unit and nav_unit not in (f"{currency}/unit", "UNKNOWN", "UNVERIFIED"):
                reasons.append("nav_unit_incompatible")
        if isinstance(assets_unit, str) and re.fullmatch(r"[A-Z]{3}", assets_unit) and isinstance(nav_unit, str):
            if nav_unit not in (f"{assets_unit}/unit", "UNKNOWN", "UNVERIFIED"):
                reasons.append("assets_nav_units_incompatible")
    for field, nested in (("assets_unit", "total_value"), ("nav_unit", "nav")):
        units = [record.get(field) or (record.get("units", {}).get(nested) if isinstance(record.get("units"), dict) else None)
                 for record in (previous, current)]
        if all(isinstance(value, str) and value not in ("", "UNKNOWN", "UNVERIFIED") for value in units) and units[0] != units[1]:
            reasons.append(f"{field}_mismatch")
    return sorted(set(reasons)), sorted(set(qualifications))


def flow_finding(payload: dict | None, source_id: str | None) -> dict:
    finding = empty_finding("flow")
    monthly, issues = selected_reports(payload)
    if payload is not None:
        finding["qualifications"].extend(payload.get("_report_list_qualifications", []))
    finding["input_refs"] = [] if source_id is None else [source_id]
    reasons = list(issues)
    for period, reports in monthly.items():
        if not reports:
            reasons.append(f"{period}_eligible_monthly_endpoint_missing")
        elif len(reports) != 1:
            reasons.append(f"{period}_duplicate_eligible_monthly_endpoint")
    # Missing publication of a second candidate cannot be proven nonduplicate.
    if reasons:
        finding["missing_reasons"] = sorted(set(reasons))
        finding["qualifications"] = sorted(set(finding["qualifications"]))
        return finding
    previous, current = monthly["2026-07"][0], monthly["2026-08"][0]
    finding["endpoint_refs"] = [
        {"period": r["period"], "source_id": source_id, "record_sha256": r["_record_sha256"],
         "published_at": r["_published_at"], "published_at_raw": r.get("published_at"),
         "historical_availability": "UNKNOWN", "record_hash_basis": "CONSUMED_ENDPOINT_FIELDS"}
        for r in (previous, current)]
    incompatible, qualifications = _comparability(previous, current)
    finding["qualifications"].extend(qualifications)
    finding["qualifications"].extend(r["_publication_assumption"] for r in (previous, current)
                                      if r["_publication_assumption"])
    finding["qualifications"] = sorted(set(finding["qualifications"]))
    values = {"previous_assets": number(previous.get("total_value")),
              "current_assets": number(current.get("total_value")),
              "previous_nav": number(previous.get("period_end_price")),
              "current_nav": number(current.get("period_end_price"))}
    finding.update({key: None if value is None else str(value) for key, value in values.items()})
    result = calculate_endpoint_change(**values)
    reasons = [*incompatible, *result.reasons]
    if reasons:
        finding["missing_reasons"] = sorted(set(reasons))
        return finding
    finding.update(arithmetic_status="AVAILABLE", freshness="FRESH", residual=str(result.residual),
                   statistic=str(result.rate), research_screen="CROSSING" if result.rate.copy_abs() >=
                   FLOW_THRESHOLD else "NO_CROSSING", direction="INFLOW_ESTIMATE" if result.rate > 0 else
                   "OUTFLOW_ESTIMATE" if result.rate < 0 else "NONE")
    return finding


def price_rows(payload: dict | None) -> tuple[dict[str, float | None], list[str]]:
    if payload is None:
        return {}, ["price_source_missing"]
    rows = payload.get("rows")
    if payload.get("_invalid") or not isinstance(rows, list):
        return {}, ["price_source_invalid"]
    result, reasons = {}, []
    for row in rows:
        if not isinstance(row, list) or len(row) != 2 or not isinstance(row[0], str):
            reasons.append("price_row_invalid")
            continue
        day, raw = row
        try:
            if date.fromisoformat(day).isoformat() != day:
                raise ValueError
        except ValueError:
            reasons.append("price_date_invalid")
            continue
        if day > CUTOFF_DATE:
            continue
        if day in result:
            reasons.append("duplicate_price_date")
            continue
        value = number(raw)
        try:
            converted = float(value) if value is not None and value > 0 else None
        except (OverflowError, ValueError):
            converted = None
        result[day] = converted if converted is not None and math.isfinite(converted) and converted > 0 else None
    # A structurally ambiguous archive cannot silently pick one duplicate.
    return ({}, sorted(set(reasons))) if reasons else (result, [])


def load_frozen_detector(repo: Path):
    path = repo / EVENT_REL / "price_detectors/detectors.py"
    spec = importlib.util.spec_from_file_location("p50k_frozen_price_detectors", path)
    if spec is None or spec.loader is None:
        raise ValueError("frozen D1 module cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def d1_context(codes: Sequence[str], price_payloads: Mapping[str, dict | None],
               identities: Mapping[str, dict], thresholds: Mapping[str, object],
               source_refs: Mapping[str, list[str]], detector) -> dict[str, tuple[dict, dict]]:
    """Call the original log_returns/peer_median/excess_level without calibration."""
    import numpy as np

    parsed = {code: price_rows(price_payloads.get(code)) for code in codes}
    calendar = sorted({day for rows, _ in parsed.values() for day in rows})
    prices = np.full((len(codes), len(calendar)), np.nan)
    positions = {day: i for i, day in enumerate(calendar)}
    for index, code in enumerate(codes):
        for day, value in parsed[code][0].items():
            if value is not None:
                prices[index, positions[day]] = value
    returns = np.vstack([detector.log_returns(row) for row in prices]) if calendar else prices.copy()
    output = {}
    for own, code in enumerate(codes):
        finding = empty_finding("d1")
        category = identities.get(code, {}).get("category")
        if not isinstance(category, str) or not category.strip():
            category = None
        members = [i for i, peer in enumerate(codes) if category is not None and
                   identities.get(peer, {}).get("category") == category]
        peers = [i for i in members if i != own]
        refs = source_refs.get(code, [])
        finding["input_refs"] = sorted(set(refs + [ref for i in peers for ref in source_refs.get(codes[i], [])]))
        finding["qualifications"].append("peer_category_membership_from_current_snapshot")
        window = calendar[-60:]
        finding["window_positions"] = len(window)
        if window:
            finding["metric_period"] = {"start": window[0], "end": window[-1]}
        threshold = number(thresholds.get(category))
        if threshold is None:
            finding["missing_reasons"].append("stored_category_calibration_missing")
        else:
            finding["threshold"] = str(threshold)
        if category is None:
            finding["missing_reasons"].append("current_category_missing")
        finding["missing_reasons"].extend(parsed[code][1])
        if len(peers) < 10:
            finding["missing_reasons"].append("fewer_than_10_category_peers")
        median_returns = np.full(len(calendar), np.nan)
        counts = np.zeros(len(calendar), dtype=int)
        if len(peers) >= 10 and calendar:
            counts = np.sum(np.isfinite(returns[peers]), axis=0)
            median_returns = detector.peer_median(returns[members], members.index(own))
        excess = returns[own] - median_returns if calendar else median_returns
        valid = np.isfinite(excess[-60:])
        finding["usable_observations"] = int(valid.sum())
        contributing = [index for index in range(max(0, len(calendar) - 60), len(calendar))
                        if np.isfinite(excess[index])]
        if contributing:
            finding["latest_contributing_at"] = calendar[contributing[-1]]
            finding["eligible_peers"] = int(min(counts[index] for index in contributing))
        stat = detector.excess_level(excess)[-1] if calendar else float("nan")
        if not np.isfinite(stat):
            finding["missing_reasons"].append("fewer_than_50_usable_excess_observations")
        if not finding["missing_reasons"]:
            finding.update(arithmetic_status="AVAILABLE", statistic=str(float(stat)),
                           freshness="FRESH" if finding["latest_contributing_at"] == CUTOFF_DATE else "STALE",
                           research_screen="CROSSING" if float(stat) > float(threshold) else "NO_CROSSING")
            if finding["freshness"] == "STALE":
                finding["missing_reasons"].append("final_contributing_observation_before_cutoff")
        chart = _chart(calendar, prices, returns, own, peers, counts)
        output[code] = finding, chart
    return output


def _chart(calendar, prices, returns, own, peers, counts) -> dict:
    import numpy as np

    chart = {"status": "UNAVAILABLE", "reason": "no_common_valid_baseline_with_10_peers",
             "baseline_date": None, "unit": "INDEX_100", "points": [], "peer_count": len(peers)}
    if len(peers) < 10:
        return chart
    for baseline in range(max(0, len(calendar) - 60), len(calendar)):
        common = [peer for peer in peers if np.isfinite(prices[peer, baseline]) and
                  np.isfinite(returns[peer, baseline])]
        if np.isfinite(prices[own, baseline]) and np.isfinite(returns[own, baseline]) and len(common) >= 10:
            break
    else:
        return chart
    chart.update(status="AVAILABLE", reason=None, baseline_date=calendar[baseline], peer_count=len(common))
    for index in range(baseline, len(calendar)):
        with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
            fund = float(prices[own, index] / prices[own, baseline] * 100) if np.isfinite(
                returns[own, index]) and np.isfinite(prices[own, index]) else None
            normalized = [float(prices[peer, index] / prices[peer, baseline] * 100) for peer in common
                          if np.isfinite(prices[peer, index]) and np.isfinite(returns[peer, index])]
        fund = fund if fund is not None and math.isfinite(fund) else None
        normalized = [value for value in normalized if math.isfinite(value)]
        peer_value = float(np.median(normalized)) if len(normalized) >= 10 else None
        chart["points"].append({"date": calendar[index], "fund": None if fund is None else str(fund),
                                "peers": None if peer_value is None else str(peer_value)})
    return chart


def assemble(codes: Sequence[str], *, price_payloads: Mapping[str, dict | None],
             report_payloads: Mapping[str, dict | None], identities: Mapping[str, dict],
             thresholds: Mapping[str, object], price_refs: Mapping[str, list[str]],
             kap_refs: Mapping[str, str], sources: list[dict], manifest: list[dict], detector,
             registration: dict) -> dict:
    selected = validate_universe(codes)
    for mapping in (price_payloads, report_payloads, identities, price_refs, kap_refs):
        if any(code not in selected for code in mapping):
            raise ValueError("input mapping contains an unopened fund")
    contexts = d1_context(selected, price_payloads, identities, thresholds, price_refs, detector)
    records = []
    for code in selected:
        d1, chart = contexts[code]
        flow = flow_finding(report_payloads.get(code), kap_refs.get(code))
        flow["input_refs"] = sorted(set(flow["input_refs"] + [source["source_id"] for source in sources
                                                             if source["fund_code"] == code and source["kind"] == "KAP_SERIES"]))
        comment, assessment, crossings = describe(d1, flow)
        name, category = (identities.get(code, {}).get(field) for field in ("name", "category"))
        name = name if isinstance(name, str) and name.strip() else code
        category = category if isinstance(category, str) and category.strip() else None
        records.append({"code": code, "name": name, "category": category, "comment_tr": comment,
                        "assessment": assessment, "eligible_crossings": crossings,
                        "d1": d1, "flow": flow, "chart": chart,
                        "evidence": sorted(set(d1["input_refs"] + flow["input_refs"] +
                                               [s["source_id"] for s in sources if s["fund_code"] == code]))})
    records.sort(key=finding_order)
    summary = summarize(records)
    summary.update(d1_assessable=sum(r["d1"]["arithmetic_status"] == "AVAILABLE" and
                                    r["d1"]["freshness"] == "FRESH" for r in records),
                   flow_assessable=sum(r["flow"]["arithmetic_status"] == "AVAILABLE" for r in records),
                   d1_stale=sum(r["d1"]["freshness"] == "STALE" for r in records))
    result = {"schema": SCHEMA, **METADATA, "summary": summary, "funds": records,
              "sources": sorted(sources, key=lambda source: source["source_id"]),
              "manifest": sorted(manifest, key=lambda entry: entry["source_id"]), "registration": registration}
    result["immutable_bundle_id"] = digest(canonical_bytes(result))
    return result


def selected_snapshot(path: Path, codes: Sequence[str]) -> bytes:
    """Project only selected names/categories; neither counts nor outcomes enter."""
    validate_universe(codes)
    safe_file(path)
    connection = sqlite3.connect(f"{path.absolute().as_uri()}?mode=ro", uri=True)
    try:
        rows = connection.execute(
            f"SELECT fund, category, raw_snapshot, retrieved_at FROM fund_snapshots WHERE fund IN "
            f"({','.join('?' for _ in codes)}) ORDER BY retrieved_at", list(codes)).fetchall()
    finally:
        connection.close()
    identities = {}
    for code, category, raw, retrieved in rows:
        try:
            row = json.loads(raw)
            name = row.get("fonUnvan") if isinstance(row, dict) else None
        except (ValueError, TypeError):
            name = None
        name = name if isinstance(name, str) and name.strip() else code
        category = category if isinstance(category, str) and category.strip() else None
        identities[code] = {"name": name, "category": category, "retrieved_at": retrieved}
    return canonical_bytes(identities)


class SourceRegistry:
    def __init__(self):
        self.sources: dict[str, dict] = {}
        self.manifest: dict[str, dict] = {}

    def add(self, path: Path, kind: str, *, fund_code: str | None = None,
            published_at: str | None = None, retrieved_at: str | None = None,
            snapshot_codes: Sequence[str] | None = None, disclosure_id: str | None = None,
            expected_sha256: str | None = None) -> str:
        safe_file(path)
        data = selected_snapshot(path, snapshot_codes) if snapshot_codes is not None else path.read_bytes()
        identifier = digest(canonical_bytes({"path": str(path.absolute()), "kind": kind}))
        sha = digest(data)
        if expected_sha256 is not None and sha != expected_sha256:
            raise BundleIntegrityError("source changed between reading and registration")
        if disclosure_id is not None and re.fullmatch(r"[1-9][0-9]*", disclosure_id) is None:
            raise BundleIntegrityError("disclosure identifier must be a positive integer")
        media = "application/pdf" if kind == "KAP_PDF" else "application/json" if kind in (
            "PRICE", "KAP_SERIES", "SNAPSHOT", "CALIBRATION") else "text/plain"
        self.sources[identifier] = {"source_id": identifier, "kind": kind, "label":
                                    f"{fund_code + ' ' if fund_code else ''}{kind}" +
                                    (" (selected name/category projection)" if snapshot_codes is not None else ""),
                                    "fund_code": fund_code,
                                    "sha256": sha, "file_name": path.name, "media_type": media,
                                    "pdf_available": kind == "KAP_PDF", "published_at": published_at,
                                    "retrieved_at": retrieved_at, "historical_availability": "UNKNOWN",
                                    "rights_status": "UNKNOWN", "origin": "HISTORICAL_REPLAY",
                                    "disclosure_id": disclosure_id, "disclosure_url": None if disclosure_id is None else
                                    f"https://www.kap.org.tr/tr/Bildirim/{disclosure_id}"}
        self.manifest[identifier] = {"source_id": identifier, "original_path": str(path.absolute()),
                                     "sha256": sha, "kind": kind,
                                     "copy_path": f"sources/{identifier}.pdf" if kind == "KAP_PDF" else None,
                                     "snapshot_codes": list(snapshot_codes) if snapshot_codes is not None else None}
        return identifier


def _source_bytes(entry: dict) -> bytes:
    path = safe_file(Path(entry["original_path"]))
    if entry.get("snapshot_codes") is not None:
        return selected_snapshot(path, entry["snapshot_codes"])
    return path.read_bytes()


def _verify_payload(payload: dict, directory: Path, allowed_codes: Sequence[str] | None = None,
                    *, check_directory_name: bool = True) -> None:
    if not isinstance(payload, dict) or payload.get("schema") != SCHEMA:
        raise BundleIntegrityError("bundle schema is missing or unsupported")
    if any(payload.get(key) != value for key, value in METADATA.items()):
        raise BundleIntegrityError("bundle provenance differs from fixed research contract")
    fingerprint = payload.get("immutable_bundle_id")
    if not isinstance(fingerprint, str) or HASH_PATTERN.fullmatch(fingerprint) is None:
        raise BundleIntegrityError("bundle fingerprint is missing or invalid")
    content = {key: value for key, value in payload.items() if key != "immutable_bundle_id"}
    if digest(canonical_bytes(content)) != fingerprint or (check_directory_name and directory.name != fingerprint):
        raise BundleIntegrityError("sealed bundle fingerprint mismatch")
    try:
        codes = validate_universe([row["code"] for row in payload["funds"]])
        allowed = validate_universe(allowed_codes) if allowed_codes is not None else codes
        if codes != allowed:
            raise BundleIntegrityError("sealed bundle contains a fund outside the committed opened universe")
        if [row["code"] for row in sorted(payload["funds"], key=finding_order)] != [r["code"] for r in payload["funds"]]:
            raise BundleIntegrityError("bundle finding order is inconsistent")
        expected = summarize(payload["funds"])
        if any(payload["summary"].get(key) != value for key, value in expected.items()):
            raise BundleIntegrityError("bundle summary count mismatch")
        sources = {source["source_id"]: source for source in payload["sources"]}
        entries = payload["manifest"]
        if len(sources) != len(payload["sources"]) or set(sources) != {entry["source_id"] for entry in entries}:
            raise BundleIntegrityError("bundle manifest/source IDs differ")
        # Membership must precede every original file/snapshot read.
        if any(source.get("fund_code") is not None and source["fund_code"] not in allowed for source in sources.values()):
            raise BundleIntegrityError("source refers to an unopened fund")
        if any(source.get("kind") in ("PRICE", "KAP_SERIES", "KAP_PDF") and source.get("fund_code") not in allowed
               for source in sources.values()):
            raise BundleIntegrityError("fund input source must identify an opened fund")
        if any(source.get("kind") not in ("PRICE", "KAP_SERIES", "KAP_PDF", "SNAPSHOT", "CALIBRATION", "UNIVERSE", "PROTOCOL", "CODE")
               for source in sources.values()):
            raise BundleIntegrityError("source kind is outside the bounded protocol")
        if any(entry.get("snapshot_codes") is not None and validate_universe(entry["snapshot_codes"]) != allowed
               for entry in entries):
            raise BundleIntegrityError("snapshot source selection differs from the opened universe")
        for row in payload["funds"]:
            if not set(row["evidence"]).issubset(sources):
                raise BundleIntegrityError("record refers to an unknown source")
        for entry in entries:
            identifier = entry["source_id"]
            if HASH_PATTERN.fullmatch(identifier) is None or not HASH_PATTERN.fullmatch(entry["sha256"]):
                raise BundleIntegrityError("invalid manifest identifier/hash")
            if sources[identifier]["sha256"] != entry["sha256"] or digest(_source_bytes(entry)) != entry["sha256"]:
                raise BundleIntegrityError("manifest-backed original source changed")
            if entry["kind"] == "KAP_PDF":
                expected_copy = f"sources/{identifier}.pdf"
                if entry["copy_path"] != expected_copy:
                    raise BundleIntegrityError("PDF copy path differs from opaque manifest ID")
                copy = safe_file(directory / expected_copy, directory)
                data = copy.read_bytes()
                if digest(data) != entry["sha256"] or not data.startswith(b"%PDF-"):
                    raise BundleIntegrityError("sealed PDF copy is corrupt")
    except (KeyError, TypeError, ValueError, OSError) as exc:
        if isinstance(exc, BundleIntegrityError):
            raise
        raise BundleIntegrityError("bundle content or manifest validation failed") from exc


def load_bundle(directory: Path, allowed_codes: Sequence[str] | None = None) -> dict:
    directory = Path(directory).absolute()
    safe_file(directory / "bundle.json", directory)
    try:
        payload = json.loads((directory / "bundle.json").read_bytes())
    except (ValueError, UnicodeDecodeError, OSError) as exc:
        raise BundleIntegrityError("sealed bundle JSON is unreadable") from exc
    _verify_payload(payload, directory, allowed_codes)
    return payload


def resolve_pdf(directory: Path, source_id: str, allowed_codes: Sequence[str] | None = None) -> Path:
    if not isinstance(source_id, str) or HASH_PATTERN.fullmatch(source_id) is None:
        raise BundleIntegrityError("source ID is not an opaque manifest identifier")
    payload = load_bundle(directory, allowed_codes)
    entry = next((entry for entry in payload["manifest"] if entry["source_id"] == source_id and
                  entry["kind"] == "KAP_PDF"), None)
    if entry is None:
        raise BundleIntegrityError("unknown or non-PDF source ID")
    return safe_file(Path(directory) / entry["copy_path"], Path(directory))


def write_bundle(base: Path, payload: dict) -> Path:
    """Publish a whole directory atomically; never overwrite a sealed version."""
    fingerprint = payload["immutable_bundle_id"]
    if HASH_PATTERN.fullmatch(fingerprint) is None:
        raise BundleIntegrityError("invalid output fingerprint")
    base = base.absolute()
    if any(part.is_symlink() for part in (base, *base.parents)):
        raise BundleIntegrityError("bundle output cannot contain symlinks")
    base.mkdir(parents=True, exist_ok=True)
    destination = base / fingerprint
    if destination.exists():
        existing = load_bundle(destination)
        if canonical_bytes(existing) != canonical_bytes(payload):
            raise BundleIntegrityError("refusing to overwrite an existing bundle")
        return destination
    temporary = Path(tempfile.mkdtemp(prefix=".bundle-", dir=base))
    try:
        (temporary / "sources").mkdir()
        for entry in payload["manifest"]:
            data = _source_bytes(entry)
            if digest(data) != entry["sha256"]:
                raise BundleIntegrityError("source changed during bundle creation")
            if entry["kind"] == "KAP_PDF":
                if not data.startswith(b"%PDF-"):
                    raise BundleIntegrityError("original PDF has no PDF signature")
                (temporary / entry["copy_path"]).write_bytes(data)
        with (temporary / "bundle.json").open("xb") as handle:
            handle.write(canonical_bytes(payload))
            handle.flush()
            os.fsync(handle.fileno())
        _verify_payload(payload, temporary, check_directory_name=False)
        # Rename only after every input and copied PDF has been bound successfully.
        # Nonempty existing destinations are rejected by rename; no file overwrite.
        os.rename(temporary, destination)
        load_bundle(destination)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return destination
