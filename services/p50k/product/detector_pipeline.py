"""Versioned causal detector runs, separate from the sealed research runtime."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import numpy as np
import psycopg
from psycopg.types.json import Jsonb

from p50k.product.archive import ISTANBUL, canonical_json
from p50k.product import detector_math as math

PROTOCOL_VERSION = "all-funds-v2"
PROTOCOL_COMMIT = "e9b7ba779cb7cfdebfb6bfac18b9dc7e8ff42ec3"
PROTOCOL_SHA256 = "e8cf9c22c8ba3d47384bd658872edf2e36bdc7e8516cea670f0ed1deb16a9a7a"
PROTOCOL_PATH = Path(__file__).resolve().parents[3] / "research/events/2026-09-17-spk-liquidations/all_funds_v2/PROTOCOL.md"
VERSION_ID = "all-funds-v2-" + PROTOCOL_SHA256[:16]
CALIBRATION_CUTOFF = datetime(2025, 10, 6, tzinfo=ISTANBUL)
PERCENTILES = {"D1": 99, "D2": 99, "D3": 99, "D4": 1}
DETECTOR_IDS = (*PERCENTILES, "D5", "AN-DQ-001", "AN-DQ-002", "AN-FND-005")
PARAMETERS = {
    "protocol_commit": PROTOCOL_COMMIT, "category_source": "fonTurAciklama_2026-10-06",
    "calibration_cutoff": CALIBRATION_CUTOFF.isoformat(), "percentiles": PERCENTILES,
    "percentile_method": "linear", "minimum_peers": 10, "minimum_calibration_values": 1000,
    "minimum_calibration_funds": 5, "level_window": 60, "level_minimum": 50,
    "before_window": 120, "before_minimum": 100, "smooth_window": 120,
    "smooth_minimum": 100, "short_history_days": 730, "stale_elapsed_weekdays": 2,
    "development_result": True, "rights_status": "UNREVIEWED",
    "label_tr": "geliştirme sonucu; eşikler olaydan sonra belirlendi",
    "limitations": ["Current category/universe; survivorship bias", "NAV currency comparability unverified",
                    "Publication availability inferred", "Historical revisions unverified",
                    "Fund age is an observed-history lower bound", "Official holidays unverified"],
}


@dataclass
class DataSet:
    codes: tuple[str, ...]
    categories: tuple[str | None, ...]
    days: tuple[date, ...]
    prices: np.ndarray
    present: np.ndarray
    ambiguous: np.ndarray
    source_hashes: dict[str, tuple[str, ...]]
    input_sha256: str
    input_watermark: datetime | None
    events: dict[str, tuple[dict[str, Any], ...]] = field(default_factory=dict)
    latest_availability: dict[str, datetime] = field(default_factory=dict)


@dataclass(frozen=True)
class Signal:
    detector_id: str
    state: str
    reason: str
    value: Decimal | None
    threshold: Decimal | None
    effective_date: date | None
    available_at: datetime | None
    metadata: dict[str, Any] = field(default_factory=dict)


def code_sha256() -> str:
    digest = hashlib.sha256()
    for path in (Path(math.__file__), Path(__file__)):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def verify_protocol() -> None:
    if hashlib.sha256(PROTOCOL_PATH.read_bytes()).hexdigest() != PROTOCOL_SHA256:
        raise ValueError("Committed v2 protocol bytes differ")


def load_inputs(connection: psycopg.Connection, cutoff: datetime) -> DataSet:
    if cutoff.tzinfo is None:
        raise ValueError("A timezone-aware cutoff is required")
    local_date = cutoff.astimezone(ISTANBUL).date()
    funds = connection.execute("SELECT fund_code,category,source_sha256,listing_as_of,observed_at FROM ref.funds ORDER BY fund_code").fetchall()
    codes, categories = tuple(row[0] for row in funds), tuple(row[1] for row in funds)
    calendar_rows = connection.execute(
        "SELECT DISTINCT effective_date FROM obs.fund_prices WHERE available_at<=%s AND effective_date<=%s AND (published_at IS NULL OR published_at<=%s) ORDER BY effective_date",
        (cutoff, local_date, cutoff),
    ).fetchall()
    days = tuple(row[0] for row in calendar_rows)
    prices = np.full((len(codes), len(days)), np.nan)
    present = np.zeros(prices.shape, dtype=bool)
    ambiguous = np.zeros(prices.shape, dtype=bool)
    code_index, day_index = {code: i for i, code in enumerate(codes)}, {day: i for i, day in enumerate(days)}
    source_hashes: dict[str, set[str]] = {code: set() for code in codes}
    latest_availability: dict[str, datetime] = {}
    digest = hashlib.sha256(canonical_json({"catalog": funds}).encode())
    watermark = None
    previous_key = previous_priority = previous_value = None
    with connection.cursor(name="detector_price_inputs") as cursor:
        cursor.itersize = 10000
        cursor.execute("""
            SELECT fund_code,effective_date,nav,available_at,observed_at,source_sha256,published_at
            FROM obs.fund_prices WHERE available_at<=%s AND effective_date<=%s
              AND (published_at IS NULL OR published_at<=%s)
            ORDER BY fund_code,effective_date,available_at DESC,observed_at DESC NULLS LAST,source_sha256
        """, (cutoff, local_date, cutoff))
        for code, day, nav, available, observed, source_hash, published in cursor:
            digest.update(canonical_json((code, day.isoformat(), nav, available, observed, source_hash, published)).encode())
            source_hashes[code].add(source_hash)
            latest_availability[code] = max(latest_availability.get(code, available), available)
            watermark = available if watermark is None else max(watermark, available)
            key, priority = (code, day), (available, observed)
            row, column = code_index[code], day_index[day]
            if key != previous_key:
                present[row, column] = True
                prices[row, column] = float(nav) if nav is not None else np.nan
                previous_key, previous_priority, previous_value = key, priority, nav
            elif priority == previous_priority and nav != previous_value:
                prices[row, column] = np.nan
                ambiguous[row, column] = True
    events: dict[str, list[dict[str, Any]]] = {code: [] for code in codes}
    for row in connection.execute("""
        SELECT event_id,fund_code,event_type,status,effective_date,available_at,source_id,source_sha256,metadata,confirmed_at,published_at
        FROM obs.regulatory_events WHERE effective_date<=%s
          AND (available_at<=%s OR (available_at IS NULL AND ingested_at<=%s))
          AND (status<>'CONFIRMED' OR confirmed_at<=%s)
          AND (published_at IS NULL OR published_at<=%s)
        ORDER BY event_id,status,source_sha256
    """, (local_date, cutoff, cutoff, cutoff, cutoff)):
        event = dict(zip(("event_id", "fund_code", "event_type", "status", "effective_date", "available_at",
                          "source_id", "source_sha256", "metadata", "confirmed_at", "published_at"), row))
        events[row[1]].append(event)
        digest.update(canonical_json(event).encode())
        if row[5] is not None:
            watermark = row[5] if watermark is None else max(watermark, row[5])
    return DataSet(codes, categories, days, prices, present, ambiguous,
                   {code: tuple(sorted(hashes)) for code, hashes in source_hashes.items()}, digest.hexdigest(), watermark,
                   {code: tuple(items) for code, items in events.items()}, latest_availability)


def calculate_scores(dataset: DataSet) -> dict[str, dict[str, np.ndarray]]:
    returns = np.vstack([math.log_returns(row) for row in dataset.prices]) if dataset.codes else np.empty(dataset.prices.shape)
    groups: dict[str | None, list[int]] = {}
    for index, category in enumerate(dataset.categories):
        groups.setdefault(category, []).append(index)
    scores: dict[str, dict[str, np.ndarray]] = {}
    for category, members in groups.items():
        block = returns[members]
        medians = math.leave_one_out_peer_medians(block) if category else np.full(block.shape, np.nan)
        for relative, index in enumerate(members):
            own, peers = returns[index], medians[relative]
            values = math.score_series(own, peers)
            for detector, series in values.items():
                admitted = np.isfinite(own)
                if detector != "D3":
                    admitted &= np.isfinite(peers)
                series[~admitted] = np.nan
            scores[dataset.codes[index]] = values
    return scores


def calibrate_dataset(dataset: DataSet) -> dict[str, dict[str, str | None]]:
    # The database loader also selects by availability. Keep this guard for synthetic callers.
    mask = np.array([day < CALIBRATION_CUTOFF.date() for day in dataset.days], dtype=bool)
    scores = calculate_scores(dataset)
    categories = sorted({category for category in dataset.categories if category})
    thresholds: dict[str, dict[str, str | None]] = {detector: {} for detector in PERCENTILES}
    for category in categories:
        members = [code for code, value in zip(dataset.codes, dataset.categories) if value == category]
        for detector, percentile in PERCENTILES.items():
            threshold = None
            if detector == "D3" or len(members) >= math.MIN_PEERS + 1:
                threshold = math.threshold([scores[code][detector][mask] for code in members], percentile)
            thresholds[detector][category] = str(threshold) if threshold is not None else None
    return thresholds


def decimal_scalar(value: float | None) -> Decimal | None:
    return Decimal(str(value)) if value is not None and np.isfinite(value) else None


def evaluate_fund(dataset: DataSet, code: str, cutoff: datetime,
                  thresholds: dict[str, dict[str, str | None]],
                  scores: dict[str, np.ndarray] | None = None) -> list[Signal]:
    index = dataset.codes.index(code)
    category = dataset.categories[index]
    effective = dataset.days[-1] if dataset.days else None
    available = dataset.input_watermark
    values = scores if scores is not None else calculate_scores(dataset)[code]
    results: list[Signal] = []
    for detector in PERCENTILES:
        value = decimal_scalar(values[detector][-1]) if dataset.days else None
        raw_threshold = thresholds.get(detector, {}).get(category) if category else None
        threshold = Decimal(raw_threshold) if raw_threshold is not None else None
        if not category:
            state, reason = "ABSTAINED", "CATEGORY_MISSING"
        elif threshold is None:
            state, reason = "ABSTAINED", "NO_CATEGORY_THRESHOLD"
        elif value is None:
            state, reason = "ABSTAINED", "CURRENT_INPUT_OR_HISTORY_UNAVAILABLE"
        else:
            triggered = value < threshold if detector == "D4" else value > threshold
            state, reason = ("TRIGGERED", "THRESHOLD_EXCEEDED") if triggered else ("NOT_TRIGGERED", "WITHIN_THRESHOLD")
        results.append(Signal(detector, state, reason, value, threshold, effective, available,
                              {"category_current_only": True, "category": category,
                               "ambiguous_input": bool(dataset.ambiguous[index].any()),
                               "is_attribute": False}))
    positive = np.isfinite(dataset.prices[index]) & (dataset.prices[index] > 0)
    priced_positions = np.flatnonzero(positive)
    first = dataset.days[int(priced_positions[0])] if len(priced_positions) else None
    last = dataset.days[int(priced_positions[-1])] if len(priced_positions) else None
    observed_days = (cutoff.astimezone(ISTANBUL).date() - first).days if first else None
    results.append(Signal("D5", "NOT_TRIGGERED" if first else "ABSTAINED", "OBSERVED_HISTORY_ATTRIBUTE" if first else "NO_POSITIVE_HISTORY",
                          Decimal(observed_days) if observed_days is not None else None, Decimal(730), effective, available,
                          {"is_attribute": True, "first_visible_price_date": first.isoformat() if first else None,
                           "short_visible_history": observed_days < 730 if observed_days is not None else None,
                           "age_is_lower_bound": True}))
    weekdays = max(0, int(np.busday_count(last + timedelta(days=1), cutoff.astimezone(ISTANBUL).date()))) if last else None
    stale_state = "ABSTAINED" if weekdays is None else "TRIGGERED" if weekdays >= 2 else "NOT_TRIGGERED"
    results.append(Signal("AN-DQ-001", stale_state, "NO_POSITIVE_HISTORY" if last is None else "STALE_DAILY_PRICE" if weekdays >= 2 else "WITHIN_PUBLISHED_CADENCE",
                          Decimal(weekdays) if weekdays is not None else None, Decimal(2), last, available,
                          {"official_holidays_unverified": True, "is_attribute": False}))
    explicit_positions = np.flatnonzero(dataset.present[index])
    latest_explicit = int(explicit_positions[-1]) if len(explicit_positions) else None
    missing = not len(priced_positions) or latest_explicit is None or not positive[latest_explicit]
    results.append(Signal("AN-DQ-002", "TRIGGERED" if missing else "NOT_TRIGGERED",
                          "NO_ADMISSIBLE_PRICE_HISTORY" if not len(priced_positions) else "LATEST_NAV_MISSING" if missing else "LATEST_NAV_AVAILABLE",
                          Decimal(1 if missing else 0), Decimal(1), dataset.days[latest_explicit] if latest_explicit is not None else None, available or cutoff,
                          {"missing_nav": missing, "is_attribute": False}))
    events = dataset.events.get(code, ())
    eligible = [event for event in events if event.get("status") == "CONFIRMED"
                and event.get("event_type") == "SPK_LIQUIDATION_ORDER"
                and event.get("source_id") in {"SPK", "spk-bulletins"}
                and event.get("metadata", {}).get("bulletin_id") == "2026-61"
                and event.get("confirmed_at") is not None and event["confirmed_at"] <= cutoff
                and (event.get("published_at") is None or event["published_at"] <= cutoff)
                and event.get("available_at") is not None and event["available_at"] <= cutoff
                and event.get("effective_date") is not None and event["effective_date"] <= cutoff.astimezone(ISTANBUL).date()]
    event = max(eligible, key=lambda item: item["available_at"]) if eligible else None
    results.append(Signal("AN-FND-005", "TRIGGERED" if event else "ABSTAINED",
                          "CONFIRMED_SPK_EVENT" if event else "EVENT_UNCONFIRMED_OR_UNDATED" if events else "SOURCE_SCOPE_LIMITED",
                          None, None, event["effective_date"] if event else None,
                          event["available_at"] if event else None,
                          {"event_ids": [item["event_id"] for item in eligible], "source_scope": "SPK 2026/61 only", "is_attribute": False}))
    return results


def get_version(connection: psycopg.Connection) -> dict[str, Any] | None:
    row = connection.execute("SELECT code_sha256,thresholds,calibration_input_sha256 FROM det.detector_versions WHERE version_id=%s", (VERSION_ID,)).fetchone()
    if row is None:
        return None
    if row[0] != code_sha256():
        raise ValueError("Detector runtime changed after immutable calibration; a new protocol is required")
    return {"thresholds": row[1], "calibration_input_sha256": row[2]}


def ensure_version(connection: psycopg.Connection) -> dict[str, Any]:
    existing = get_version(connection)
    if existing:
        return existing
    calibration = load_inputs(connection, CALIBRATION_CUTOFF - timedelta(microseconds=1))
    thresholds = calibrate_dataset(calibration)
    connection.execute("""
        INSERT INTO det.detector_versions (version_id,protocol_version,protocol_sha256,code_sha256,parameters,thresholds,calibration_input_sha256,calibration_cutoff)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING
    """, (VERSION_ID, PROTOCOL_VERSION, PROTOCOL_SHA256, code_sha256(), Jsonb(PARAMETERS), Jsonb(thresholds),
          calibration.input_sha256, CALIBRATION_CUTOFF))
    return get_version(connection) or {"thresholds": thresholds, "calibration_input_sha256": calibration.input_sha256}


def references(dataset: DataSet, code: str, signal: Signal) -> list[dict[str, Any]]:
    refs = [{"source_id": "tefas-prices", "source_sha256": checksum,
             "effective_date": signal.effective_date.isoformat() if signal.effective_date else None,
             "available_at": dataset.latest_availability[code].isoformat() if code in dataset.latest_availability else None,
             "source_url": None} for checksum in dataset.source_hashes.get(code, ())]
    if signal.detector_id in {"D1", "D2", "D4"}:
        refs.append({"source_id": "derived-category-peers", "source_sha256": dataset.input_sha256,
                     "effective_date": signal.effective_date.isoformat() if signal.effective_date else None,
                     "available_at": dataset.input_watermark.isoformat() if dataset.input_watermark else None,
                     "source_url": None})
    if signal.detector_id == "AN-FND-005":
        refs = [{"source_id": item["source_id"], "source_sha256": item["source_sha256"],
                 "effective_date": item["effective_date"].isoformat(), "available_at": item["available_at"].isoformat(),
                 "source_url": item.get("metadata", {}).get("source_url")}
                for item in dataset.events.get(code, ()) if item["event_id"] in signal.metadata["event_ids"]
                and item["available_at"] is not None]
    return refs


def run_detectors(connection: psycopg.Connection, cutoff: datetime, origin: str = "DELAYED") -> dict[str, Any]:
    verify_protocol()
    if cutoff.tzinfo is None or origin not in {"DELAYED", "HISTORICAL_REPLAY", "SYNTHETIC"}:
        raise ValueError("Run requires a timezone-aware cutoff and an explicit data origin")
    connection.autocommit = True
    with connection.transaction():
        # Version creation and inputs share a consistent read snapshot; the final batch is atomic.
        connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        connection.execute("SELECT pg_advisory_xact_lock(50000022)")
        version = ensure_version(connection)
        dataset = load_inputs(connection, cutoff)
        existing = connection.execute("SELECT run_id FROM det.run_inputs WHERE version_id=%s AND input_sha256=%s AND origin=%s AND cutoff=%s",
                                      (VERSION_ID, dataset.input_sha256, origin, cutoff)).fetchone()
        if existing:
            return {"run_id": str(existing[0]), "reused": True, "funds": len(dataset.codes)}
        scores = calculate_scores(dataset)
        run_id = uuid4()
        as_of = dataset.days[-1] if dataset.days else cutoff.astimezone(ISTANBUL).date()
        connection.execute("INSERT INTO det.detector_runs (run_id,protocol_version,protocol_sha256,origin,cutoff,parameters) VALUES (%s,%s,%s,%s,%s,%s)",
                           (run_id, PROTOCOL_VERSION, PROTOCOL_SHA256, origin, cutoff,
                            Jsonb({**PARAMETERS, "version_id": VERSION_ID, "input_sha256": dataset.input_sha256, "as_of": as_of.isoformat()})))
        counts: dict[str, dict[str, int]] = {detector: {} for detector in DETECTOR_IDS}
        for code in dataset.codes:
            for signal in evaluate_fund(dataset, code, cutoff, version["thresholds"], scores[code]):
                triggered = None if signal.state == "ABSTAINED" else signal.state == "TRIGGERED"
                values: dict[str, Any] = {"score": str(signal.value) if signal.value is not None else None}
                if signal.detector_id == "D5":
                    values = {"observed_history_days": values["score"], "short_visible_history": signal.metadata["short_visible_history"]}
                limits = {"threshold": str(signal.threshold) if signal.threshold is not None else None}
                refs = references(dataset, code, signal)
                payload = {"run_id": str(run_id), "fund_code": code, "detector_id": signal.detector_id,
                           "state": signal.state, "reason": signal.reason, "values": values, "thresholds": limits,
                           "source_references": refs, "cutoff": cutoff.isoformat()}
                evidence_id = "ev:" + hashlib.sha256(canonical_json(payload).encode()).hexdigest()
                unit = "days" if signal.detector_id == "D5" else "weekdays" if signal.detector_id == "AN-DQ-001" else "indicator" if signal.detector_id.startswith("AN-") else "log_return" if signal.detector_id in {"D1", "D2"} else "correlation"
                connection.execute("""INSERT INTO det.evidence_items
                    (evidence_id,fund_code,run_id,detector_id,origin,effective_date,available_at,unit,values,thresholds,triggered,state,source_references,metadata)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (evidence_id, code, run_id, signal.detector_id, origin, signal.effective_date, signal.available_at, unit,
                     Jsonb(values), Jsonb(limits), triggered, signal.state, Jsonb(refs), Jsonb({**signal.metadata, "reason": signal.reason,
                     "label_tr": PARAMETERS["label_tr"], "rights_status": "UNREVIEWED", "limitations": PARAMETERS["limitations"]})))
                connection.execute("""INSERT INTO det.signals
                    (run_id,fund_code,detector_id,state,reason,value,threshold,evidence_id,as_of)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (run_id, code, signal.detector_id, signal.state, signal.reason, signal.value, signal.threshold, evidence_id, as_of))
                counts[signal.detector_id][signal.state] = counts[signal.detector_id].get(signal.state, 0) + 1
        connection.execute("INSERT INTO det.run_inputs (run_id,version_id,input_sha256,input_watermark,as_of,complete,origin,cutoff) VALUES (%s,%s,%s,%s,%s,true,%s,%s)",
                           (run_id, VERSION_ID, dataset.input_sha256, dataset.input_watermark, as_of, origin, cutoff))
        return {"run_id": str(run_id), "reused": False, "version_id": VERSION_ID, "funds": len(dataset.codes),
                "as_of": as_of.isoformat(), "origin": origin, "development_result": True, "counts": counts}
