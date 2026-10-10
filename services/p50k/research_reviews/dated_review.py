"""Per-date D1 arithmetic for the dated view; the v1 modules are imported read-only.

dated_price_rows and dated_d1_context are copies of bundle.price_rows and
bundle.d1_context with an explicit cutoff date instead of the module constant.
At 2026-09-16 they must equal v1 exactly (tested). Frozen D1/numpy loads lazily.
"""
from __future__ import annotations

import math
from datetime import date
from typing import Mapping, Sequence

from p50k.research_reviews import bundle as v1
from p50k.research_reviews.bundle import canonical_bytes, digest, number, validate_universe
from p50k.research_reviews.contracts import empty_finding
from p50k.research_reviews.dated_comments import dated_order, describe_dated, summarize_dated
from p50k.research_reviews.dated_contracts import (
    DATED_SCHEMA, SNAPSHOT_BOUND, SNAPSHOT_KEYS, SOURCE_KINDS, THRESHOLD_FIXED, THRESHOLD_KEYS,
    d1_state, metadata_for, validate_cutoff, validate_grid,
)


def _row_dates(payload: dict | None, end_date: str) -> set[str]:
    """Same structural, date and duplicate rules as price_rows; values are never read."""
    if payload is None:
        return set()
    rows = payload.get("rows")
    if payload.get("_invalid") or not isinstance(rows, list):
        return set()
    days: set[str] = set()
    for row in rows:
        if not isinstance(row, list) or len(row) != 2 or not isinstance(row[0], str):
            return set()
        day = row[0]
        try:
            if date.fromisoformat(day).isoformat() != day:
                raise ValueError
        except ValueError:
            return set()
        if day > end_date:
            continue
        if day in days:
            return set()
        days.add(day)
    return days


def calendar_dates(price_payloads: Mapping[str, dict | None], end_date: str) -> list[str]:
    """Shared calendar: union of usable row dates on or before end_date."""
    end_date = validate_cutoff(end_date)
    union: set[str] = set()
    for payload in price_payloads.values():
        union |= _row_dates(payload, end_date)
    return sorted(union)


def dated_price_rows(payload: dict | None, cutoff_date: str) -> tuple[dict[str, float | None], list[str]]:
    cutoff_date = validate_cutoff(cutoff_date)
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
        if day > cutoff_date:
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


def has_positive_price(payload: dict | None, cutoff_date: str) -> bool:
    """Any well-formed row dated on or before the cutoff with a positive finite price."""
    cutoff_date = validate_cutoff(cutoff_date)
    rows = payload.get("rows") if isinstance(payload, dict) and not payload.get("_invalid") else None
    if not isinstance(rows, list):
        return False
    for row in rows:
        if not isinstance(row, list) or len(row) != 2 or not isinstance(row[0], str):
            continue
        try:
            if date.fromisoformat(row[0]).isoformat() != row[0] or row[0] > cutoff_date:
                continue
        except ValueError:
            continue
        value = number(row[1])
        try:
            if value is not None and value > 0 and math.isfinite(float(value)) and float(value) > 0:
                return True
        except (OverflowError, ValueError):
            continue
    return False


def dated_d1_context(codes: Sequence[str], price_payloads: Mapping[str, dict | None],
                     identities: Mapping[str, dict], thresholds: Mapping[str, object],
                     source_refs: Mapping[str, list[str]], detector, cutoff_date: str) -> dict[str, tuple[dict, dict]]:
    """Call the original log_returns/peer_median/excess_level without calibration."""
    cutoff_date = validate_cutoff(cutoff_date)
    import numpy as np

    parsed = {code: dated_price_rows(price_payloads.get(code), cutoff_date) for code in codes}
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
                           freshness="FRESH" if finding["latest_contributing_at"] == cutoff_date else "STALE",
                           research_screen="CROSSING" if float(stat) > float(threshold) else "NO_CROSSING")
            if finding["freshness"] == "STALE":
                finding["missing_reasons"].append("final_contributing_observation_before_cutoff")
        chart = v1._chart(calendar, prices, returns, own, peers, counts)
        output[code] = finding, chart
    return output


def check_threshold_provenance(provenance: object) -> dict:
    if not isinstance(provenance, dict) or set(provenance) != THRESHOLD_KEYS:
        raise ValueError("threshold provenance fields differ from the dated contract")
    if any(provenance[key] != value for key, value in THRESHOLD_FIXED.items()):
        raise ValueError("threshold provenance differs from the registered calibration bound")
    return provenance


def check_snapshot(snapshot: object) -> dict:
    if not isinstance(snapshot, dict) or set(snapshot) != SNAPSHOT_KEYS or snapshot["bound"] != SNAPSHOT_BOUND:
        raise ValueError("snapshot provenance differs from the registered bound")
    return snapshot


def assemble_dated(codes: Sequence[str], *, cutoff_date: str, grid: Sequence[str],
                   price_payloads: Mapping[str, dict | None], identities: Mapping[str, dict],
                   thresholds: Mapping[str, object], price_refs: Mapping[str, list[str]],
                   sources: list[dict], manifest: list[dict], detector, registration: dict,
                   threshold_provenance: dict, snapshot: dict) -> dict:
    """One dated bundle payload: 100 D1-only records at one registered grid date."""
    cutoff_date = validate_cutoff(cutoff_date)
    if cutoff_date not in validate_grid(grid):
        raise ValueError("cutoff date is not a registered grid date")
    selected = validate_universe(codes)
    for mapping in (price_payloads, identities, price_refs):
        if any(code not in selected for code in mapping):
            raise ValueError("input mapping contains an unopened fund")
    if any(source.get("kind") not in SOURCE_KINDS for source in [*sources, *manifest]):
        raise ValueError("dated bundles accept only price, snapshot, calibration, universe, protocol and code sources")
    check_threshold_provenance(threshold_provenance)
    check_snapshot(snapshot)
    contexts = dated_d1_context(selected, price_payloads, identities, thresholds, price_refs, detector, cutoff_date)
    records = []
    for code in selected:
        d1, chart = contexts[code]
        name, category = (identities.get(code, {}).get(field) for field in ("name", "category"))
        name = name if isinstance(name, str) and name.strip() else code
        category = category if isinstance(category, str) and category.strip() else None
        records.append({"code": code, "name": name, "category": category, "comment_tr": describe_dated(d1),
                        "d1_state": d1_state(d1), "d1": d1, "chart": chart,
                        "date_context": {"has_positive_price_on_or_before_cutoff":
                                         has_positive_price(price_payloads.get(code), cutoff_date)},
                        "evidence": sorted(set(d1["input_refs"] + [s["source_id"] for s in sources
                                                                   if s.get("fund_code") == code]))})
    records.sort(key=dated_order)
    result = {"schema": DATED_SCHEMA, **metadata_for(cutoff_date),
              "threshold_provenance": dict(threshold_provenance), "snapshot": dict(snapshot),
              "summary": summarize_dated(records), "funds": records,
              "sources": sorted(sources, key=lambda source: source["source_id"]),
              "manifest": sorted(manifest, key=lambda entry: entry["source_id"]), "registration": registration}
    result["immutable_bundle_id"] = digest(canonical_bytes(result))
    return result
