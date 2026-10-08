"""Offline THF reported-futures counterfactual; actual P&L stays unknown."""
from __future__ import annotations

import argparse
import calendar
import csv
from datetime import date, datetime
from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).absolute().parents[4]
sys.path.insert(0, str(ROOT / "services"))
UTILITY_PATH = "research/events/2026-09-17-spk-liquidations/fund_holdings_divergence/run.py"
_spec = importlib.util.spec_from_file_location("thf_equity_runner_utilities", ROOT / UTILITY_PATH)
_utilities = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_utilities)
ResearchInputError = _utilities.ResearchInputError
canonical_path, sha256 = _utilities.canonical_path, _utilities.sha256
jsonable, committed_code = _utilities.jsonable, _utilities.committed_code
PROTOCOL = "research/events/2026-09-17-spk-liquidations/fund_futures_divergence/PREREGISTRATION.md"
RUNTIME = ("research/events/2026-09-17-spk-liquidations/fund_futures_divergence/run.py",
           "services/p50k/analytics/futures_contribution.py", UTILITY_PATH)
PREREGISTRATION_COMMIT = "96e0c7a"
EQUITY_COMMIT = "96dbbd0"
EQUITY_SHA = "1059eff06a897d1e21103c801b5d92bcf45be4ec88d7f3bcc79cd2b52c5b1d0c"
EQUITY_PATH = "raw/bist/THF/divergence-analysis/4a1ac6d36969dd66e2da6780a72b11804f31276074fb49f9e851a6d5535f7e18/results.json"
INVENTORY_PATH = "raw/bist/THF/futures-audit/source-inventory.json"
INVENTORY_SHA = "892f4f660e1a71693d9d0dd61b88773e30791fd3bbc8d8d63586b2160efe7ebd"
HISTORY_SHA = "3abb345aa0809664aa62003a566180864f024e316eb947b6507f5ec60a264c3a"
ADJUSTMENTS_SHA = "2ca395125373a9c8311dc6496effd35679ad1acef1429ec91a50a46d6f9d88fa"
RECEIPTS = {"official-history-receipt.json": "f0b752955e5c99f42ed32cd9b8de6710e1971a073052fe6b9a949352b8af6f86",
            "official-adjustments-receipt.json": "ea747f54db5b00ab6001874aa7b6313b0aeaa58a439bb8fc61a28b40e736f554"}
SAMPLE_RECEIPTS = {"official-sample-request-receipt.json": "e97945b290ea12c861dc544fd16122319f9d22240b2729f9577f25f9d6c668fb",
                   "official-adjustments-sample-receipt.json": "147d1f92942b467b606060ca1042c8b1027c3d996753bfb6b26e13b6a4baebf9"}
ADMISSION_SHA = "ab3222bcb845c67a419d7c5bf37ff796dae489d355c4a8711c1d5118e06f9f4d"
PERIODS = _utilities.EXPECTED_PERIODS
DAILY_FIELDS = {"trade_date": "TARIH", "maturity_date": "VADE TARIHI",
                "underlying_as_printed": "DAYANAK VARLIK", "settlement_price_raw": "UZLASMA FIYATI",
                "close_price_raw": "KAPANIS FIYATI"}
META_FIELDS = {"maturity_date": "VADE TARIHI", "underlying_as_printed": "DAYANAK VARLIK",
               "multiplier_raw": "SOZLESME BUYUKLUGU", "currency": "PARA BIRIMI",
               "settlement_type": "UZLASMA TIPI", "last_trade_date": "SON ISLEM TARIHI",
               "contract_status": "DURUM", "instrument_type": "SOZLESME TURU"}


def positive_decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool) or str(value).strip() == "":
        return None
    try:
        result = Decimal(str(value).strip())
    except ArithmeticError:
        return None
    return result if result.is_finite() and result > 0 else None


def code_gate(root: Path) -> dict[str, Any]:
    code = committed_code(root, (PROTOCOL, *RUNTIME))
    registration = subprocess.run(["git", "rev-parse", f"{PREREGISTRATION_COMMIT}^{{commit}}"],
                                  cwd=root, capture_output=True, check=True, text=True).stdout.strip()
    blob = subprocess.run(["git", "show", f"{registration}:{PROTOCOL}"], cwd=root,
                          capture_output=True, check=True).stdout
    if blob != canonical_path(root, PROTOCOL).read_bytes() or subprocess.run(
            ["git", "merge-base", "--is-ancestor", registration, code["head"]],
            cwd=root, capture_output=True).returncode:
        raise ResearchInputError("protocol differs from the preregistration or lacks ancestry")
    code["preregistration_commit"] = registration
    return code


def verify_csv(path: Path, records: list[dict[str, Any]], kind: str, day: str,
               codes: set[str]) -> dict[str, dict[str, str]]:
    """Reparse exact official rows; absent means missing, never zero."""
    fields = DAILY_FIELDS if kind == "settlements" else META_FIELDS
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, delimiter=";")
        required = {"SOZLESME KODU", *fields.values()}
        if kind == "metadata": required.update(("SOZLESME TIPI", "SOZLESME GRUBU"))
        if not reader.fieldnames or not required <= set(reader.fieldnames):
            raise ResearchInputError("official CSV schema changed")
        descriptor = next(reader, None)
        expected_descriptor = "INSTRUMENT SERIES" if kind == "settlements" else "CONTRACT CODE"
        if descriptor is None or descriptor["SOZLESME KODU"] != expected_descriptor:
            raise ResearchInputError("official English descriptor row missing")
        found = {}
        for line_number, raw in enumerate(reader, 3):
            identity = raw["SOZLESME KODU"]
            if identity not in codes:
                continue
            if identity in found:
                raise ResearchInputError("duplicate exact-contract daily row")
            found[identity] = (line_number, raw)
    if {item["contract_code"] for item in records} != codes or len(records) != len(codes):
        raise ResearchInputError("official history contract scope differs")
    verified = {}
    for item in records:
        identity = item["contract_code"]
        if identity not in found:
            if item != {"contract_code": identity, "status": "ABSENT_FROM_OFFICIAL_DAILY_FILE"}:
                raise ResearchInputError("unproved missing official contract")
            continue
        line_number, raw = found[identity]
        if item.get("status") != "PRESENT" or str(line_number) != str(item.get("source_csv_row")):
            raise ResearchInputError("official row status/coordinate changed")
        if any(item.get(key) != raw[column] for key, column in fields.items()):
            raise ResearchInputError("parsed official value differs from source CSV")
        if kind == "settlements":
            if raw["TARIH"] != day or item.get("settlement_price") != jsonable(
                    positive_decimal(raw["UZLASMA FIYATI"])) or item.get("close_price") != jsonable(
                    positive_decimal(raw["KAPANIS FIYATI"])):
                raise ResearchInputError("official price/date normalization changed")
        elif item.get("multiplier") != jsonable(positive_decimal(raw["SOZLESME BUYUKLUGU"])):
            raise ResearchInputError("official multiplier normalization changed")
        verified[identity] = raw
    return verified


def verify_adjustments(path: Path, record: dict[str, Any], codes: set[str]) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, delimiter=";")
        if not reader.fieldnames or not {"SOZLESME KODU", "SOZLESME BUYUKLUGU", "SOZLESME GRUBU", "DURUM", "VADE TARIHI", "UZLASMA TIPI", "PARA BIRIMI"} <= set(reader.fieldnames):
            raise ResearchInputError("official adjustment schema changed")
        descriptor = next(reader, None)
        if descriptor is None or descriptor["SOZLESME KODU"] != "INSTRUMENT SERIES":
            raise ResearchInputError("adjustment descriptor missing")
        all_rows = list(reader)
    observed = [{"source_csv_row": number, "fields": raw} for number, raw in enumerate(all_rows, 3) if raw["SOZLESME KODU"] in codes]
    status = "EXACT_REPORTED_CODE_RECORDS_PRESENT" if observed else "NO_EXACT_REPORTED_CODE_RECORDS"
    if record["reported_contract_records"] != observed or record["status"] != status or record["source_record_count"] != len(all_rows):
        raise ResearchInputError("adjustment source rows/status changed")
    return [item["fields"] for item in observed]


def adjustment_reasons(positions: list[Any], changes: dict[date, Any], report_date: date,
                       base_date: date, endpoint_date: date) -> list[str]:
    """A later adjustment cannot invalidate an earlier observation."""
    specifications = {position.spec.contract_id: position.spec for position in positions}
    reasons = []
    for day, rows in changes.items():
        if not report_date <= day <= endpoint_date: continue
        for raw in rows:
            identity = raw["SOZLESME KODU"]; spec = specifications.get(identity)
            if spec is None or spec.expiry < base_date: continue
            if spec.settlement_type == "CASH" and day > spec.expiry: continue
            unchanged = (positive_decimal(raw["SOZLESME BUYUKLUGU"]) == spec.multiplier and
                raw["VADE TARIHI"] == spec.expiry.isoformat() and raw["SOZLESME GRUBU"] == "S" and
                raw["PARA BIRIMI"] == spec.currency and raw["UZLASMA TIPI"] == (
                    "Cash Settlement" if spec.settlement_type == "CASH" else "Physical Delivery"))
            expected_expiration = raw["DURUM"] == "E" and day > spec.expiry
            if not unchanged or not (raw["DURUM"] == "A" or expected_expiration):
                reasons.append(f"unresolved_contract_adjustment:{identity}:{day.isoformat()}")
    return reasons


def verify_admission(admission: dict[str, Any], sources: dict[str, Any]) -> None:
    records = admission["sources"]
    if admission["source_count"] != len(records) or len(records) != len(sources) or {r["path"] for r in records} != set(sources):
        raise ResearchInputError("official admission source scope differs")
    for record in records:
        expected_url = f"https://www.borsaistanbul.com/data/vadeli/{Path(record['path']).name}"
        observed = datetime.fromisoformat(record["observed_at"])
        if (sources[record["path"]]["sha256"] != record["sha256"] or record["source_url"] != expected_url or
                observed.tzinfo is None or record["historical_first_publication_time"] is not None or
                record["point_in_time_admitted"] is not False or record["rights_status"] != "UNKNOWN" or
                record["data_mode"] != "HISTORICAL_REPLAY"):
            raise ResearchInputError("official archive admission differs")


def verify_request(request: dict[str, Any], inputs: dict[str, Any], samples: dict[str, Any]) -> dict[str, Any]:
    """Preserve unrecorded redirect endpoints only for bound original samples."""
    path = request["path"]; registered = inputs.get(path)
    expected_url = f"https://www.borsaistanbul.com/data/vadeli/{Path(path).name}"
    if not registered or registered["sha256"] != request["sha256"] or request["status"] != 200 or request["url"] != expected_url:
        raise ResearchInputError("official acquisition receipt differs")
    original = samples.get(path) if request.get("reused_existing_sample") is True else None
    if request.get("reused_existing_sample") is True:
        if original is None or any(request.get(key) != original["request"].get(key) for key in (
                "path", "sha256", "url", "status", "observed_at", "bytes")):
            raise ResearchInputError("reused sample lacks matching original HTTP receipt")
    recorded = request.get("final_url")
    original_final = original["request"].get("final_url") if original else None
    if (recorded is not None and recorded != expected_url) or (original_final is not None and original_final != expected_url):
        raise ResearchInputError("official response endpoint differs")
    if recorded is None and original is None:
        raise ResearchInputError("unbound request lacks a recorded response endpoint")
    final_url = recorded if recorded is not None else original_final
    return {"path": path, "request_url": request["url"], "final_response_url": final_url,
            "final_response_url_status": "RECORDED" if final_url is not None else "UNKNOWN",
            "original_sample_receipt": original["source_receipt_path"] if original else None}


def specification(identity: str, raw: dict[str, str] | None) -> Any:
    from p50k.analytics.futures_contribution import ContractSpecification
    if raw is None:
        return None
    expiry = date.fromisoformat(raw["VADE TARIHI"])
    index = raw["SOZLESME TIPI"] == "D_IX_FUT"
    if (raw["SOZLESME KODU"] != identity or raw["SOZLESME TURU"] != "Future" or raw["SOZLESME GRUBU"] != "S" or
            raw["PARA BIRIMI"] != "TRY" or raw["SON ISLEM TARIHI"] != expiry.isoformat() or
            identity[-4:] != expiry.strftime("%m%y") or raw["SOZLESME TIPI"] not in ("D_IX_FUT", "D_EQ_FPD")):
        raise ResearchInputError("unresolved exact-contract specification")
    settlement_type = {"Cash Settlement": "CASH", "Physical Delivery": "PHYSICAL"}.get(raw["UZLASMA TIPI"], "UNKNOWN")
    return ContractSpecification(identity, positive_decimal(raw["SOZLESME BUYUKLUGU"]), expiry,
           settlement_type, "TRY", "INDEX_POINTS" if index else "TRY_PER_SHARE",
           "TRY_PER_INDEX_POINT" if index else "SHARES_PER_CONTRACT")


def validate_window_scope(window: dict[str, Any], period: str, published: datetime) -> None:
    year, month = map(int, period.split("-"))
    period_end = date(year, month, calendar.monthrange(year, month)[1])
    baseline = date.fromisoformat(window["base_date"])
    if (window["snapshot_id"] != period or window["reported_period_end"] != period_end.isoformat() or
            window["available_at"] != published.isoformat() or baseline <= published.date()):
        raise ResearchInputError("window uses a report before publication or a different period")
    for row in window["rows"]:
        day = date.fromisoformat(row["valuation_date"])
        if day < baseline or row["fund_row_label"] > "2026-09-16" or (
                window["next_publication_date"] and row["valuation_date"] >= window["next_publication_date"]):
            raise ResearchInputError("existing publication/cutoff window changed")


def verify_inventory(inventory: dict[str, Any], equity: dict[str, Any], register: Any) -> None:
    """Check source words, sides and every original report/list identity."""
    import fitz
    if (inventory.get("fund_code") != "THF" or equity.get("fund_code") != "THF" or
            tuple(x["report_period"] for x in inventory["reports"]) != PERIODS or
            tuple(x["snapshot_id"] for x in equity["windows"]) != PERIODS):
        raise ResearchInputError("only the eleven registered THF reports are authorized")
    listing = json.loads(register("raw/kap/reports/THF/kap_report_list.json",
                                 inventory["report_list_sha256"]).read_text())
    basics = {x["disclosureBasic"]["disclosureIndex"]: x["disclosureBasic"] for x in listing}
    for report, window in zip(inventory["reports"], equity["windows"], strict=True):
        basic = basics.get(report["disclosure_index"])
        published = datetime.strptime(report["published_at_label"], "%d.%m.%Y %H:%M:%S").replace(tzinfo=ZoneInfo("Europe/Istanbul"))
        validate_window_scope(window, report["report_period"], published)
        if (not basic or basic["stockCode"] != "THF" or basic["period"] != "AB" or
                basic["publishDate"] != report["published_at_label"] or
                f"{basic['year']}-{int(basic['donem']):02d}" != report["report_period"] or
                published.isoformat() != window["available_at"] or
                window["base_date"] <= published.date().isoformat() or
                window["extraction"]["source_sha256"] != report["source_sha256"]):
            raise ResearchInputError("report identity or publication window differs")
        path = register(report["source_path"], report["source_sha256"])
        if not str(path).endswith(f"/raw/kap/reports/THF/{report['report_period']}_{report['disclosure_index']}.pdf"):
            raise ResearchInputError("report path is outside THF scope")
        with fitz.open(path) as document:
            side, actual_rows = None, []
            for page_number, page in enumerate(document, 1):
                words = page.get_text("words")
                for anchor in sorted((w for w in words if w[0] < 80 and (
                        w[4] in ("Uzun", "Kısa") or w[4].startswith("F_"))), key=lambda w: w[1]):
                    if anchor[4] in ("Uzun", "Kısa"):
                        side = "LONG" if anchor[4] == "Uzun" else "SHORT"
                        continue
                    actual_rows.append((anchor[4], side, page_number, sorted(
                        (w for w in words if abs(w[1] - anchor[1]) < 1), key=lambda w: w[0])))
            if len(actual_rows) != len(report["rows"]):
                raise ResearchInputError("futures inventory silently added/dropped positions")
            for (identity, side, page, words), row in zip(actual_rows, report["rows"], strict=True):
                reproduced = [{"raw": w[4], "page": page, "bbox": list(w[:4])} for w in words]
                if (identity != row["contract"] or side != row["side"] or reproduced != row["all_row_words"]):
                    raise ResearchInputError("futures source geometry/side changed")
                for field in ("nominal_quantity", "unit_purchase_price", "daily_valuation_price", "reported_total_value", "group_pct", "portfolio_pct", "fund_pct"):
                    value = row[field]
                    if not any(w[4] == value["raw"] and list(w[:4]) == value["bbox"] for w in words) or value["page"] != page or Decimal(value["raw"].replace(".", "").replace(",", ".")) != Decimal(value["value"]):
                        raise ResearchInputError("numeric source coordinate/token differs")
                if not any(w[4] == "TL" for w in words):
                    raise ResearchInputError("source currency must explicitly be TL")


def evaluate_window(window: dict[str, Any], source: dict[str, Any], positions: list[Any],
                    settlements: dict[str, Any], source_reasons: list[str],
                    changes: dict[date, Any] | None = None) -> dict[str, Any]:
    from p50k.analytics.futures_contribution import calculate_futures_contribution
    output = {key: window[key] for key in ("snapshot_id", "reported_period_end", "available_at", "base_date", "base_fund_row_label", "next_publication_date")}
    output.update({"reported_futures_rows": source["rows"], "actual_futures_pnl_status": "UNKNOWN", "rows": []})
    for original in window["rows"]:
        record = dict(original)
        reasons = source_reasons + adjustment_reasons(positions, changes or {},
            date.fromisoformat(window["reported_period_end"]), date.fromisoformat(window["base_date"]),
            date.fromisoformat(original["valuation_date"]))
        if not source["rows"]:
            metric = {"availability": "NO_REPORTED_POSITIONS_ACTUAL_ACTIVITY_UNKNOWN", "contribution": None, "pnl_try": None, "reasons": ["monthly_snapshot_does_not_establish_intramonth_activity"]}
        elif reasons:
            metric = {"availability": "UNAVAILABLE", "contribution": None, "pnl_try": None, "reasons": reasons}
        else:
            metric = jsonable(calculate_futures_contribution(positions,
                base_date=date.fromisoformat(window["base_date"]), endpoint_date=date.fromisoformat(original["valuation_date"]),
                fund_net_assets=Decimal(window["extraction"]["headline_total_value"]["value"]), settlements=settlements))
        record["futures_metric"] = metric
        record["combined_reference_return"] = record["remaining_gap"] = None
        record["combined_availability"] = "UNAVAILABLE"
        if original["metric"]["availability"] == "AVAILABLE" and metric["availability"] == "AVAILABLE":
            with localcontext(Context(prec=128, rounding=ROUND_HALF_EVEN)):
                combined = Decimal(original["metric"]["equity_proxy_return"]) + Decimal(metric["contribution"])
                record.update(combined_availability="AVAILABLE", combined_reference_return=str(combined),
                              remaining_gap=str(Decimal(original["metric"]["actual_return"]) - combined))
        output["rows"].append(record)
    available = [r for r in output["rows"] if r["combined_availability"] == "AVAILABLE"]
    output["summary"] = {"candidate_intervals": len(output["rows"]), "available_combined_intervals": len(available),
        "futures_status_counts": {status: sum(r["futures_metric"]["availability"] == status for r in output["rows"]) for status in sorted({r["futures_metric"]["availability"] for r in output["rows"]})},
        "endpoint": output["rows"][-1] if output["rows"] and output["rows"][-1]["combined_availability"] == "AVAILABLE" else None,
        "largest_absolute_remaining_gap": max(available, key=lambda r: Decimal(r["remaining_gap"]).copy_abs()) if available else None}
    return output


def run(root: Path = ROOT) -> Path:
    from p50k.analytics.futures_contribution import FuturesPosition, SettlementObservation
    import fitz
    code = code_gate(root)
    inputs = {}
    def register(value: str | Path, expected: str | None = None) -> Path:
        path = canonical_path(root, value); relative = str(path.relative_to(root)); digest = sha256(path)
        if (expected is not None and digest != expected) or (relative in inputs and inputs[relative]["sha256"] != digest):
            raise ResearchInputError(f"source changed: {relative}")
        inputs[relative] = {"path": relative, "sha256": digest, "bytes": path.stat().st_size}
        return path
    equity = json.loads(register(EQUITY_PATH, EQUITY_SHA).read_text())
    anchor = subprocess.run(["git", "rev-parse", f"{EQUITY_COMMIT}^{{commit}}"], cwd=root, capture_output=True, check=True, text=True).stdout.strip()
    if equity["manifest"]["code"]["head"] != anchor:
        raise ResearchInputError("equity result is not anchored to the registered runtime")
    for item in equity["manifest"]["inputs"]: register(item["path"], item["sha256"])
    inventory = json.loads(register(INVENTORY_PATH, INVENTORY_SHA).read_text())
    verify_inventory(inventory, equity, register)
    history = json.loads(register("raw/bist/THF/futures-audit/official-contract-history.json", HISTORY_SHA).read_text())
    codes = {r["contract"] for report in inventory["reports"] for r in report["rows"]}
    if history["source_contract_codes"] != sorted(codes) or history["input_result_sha256"] != EQUITY_SHA or history["no_returns_calculated"] is not True:
        raise ResearchInputError("official history scope/lineage differs")
    raw_by_day = {}
    for day, files in history["dates"].items():
        if set(files) != {"metadata", "settlements"}: raise ResearchInputError("both official sources are required")
        for kind, item in files.items():
            prefix = "viop" if kind == "settlements" else "viopms"
            if item["source_path"] != f"raw/bist/THF/futures-audit/{prefix}_{day.replace('-', '')}.csv":
                raise ResearchInputError("official source path/date differs")
        raw_by_day[date.fromisoformat(day)] = {kind: verify_csv(register(item["source_path"], item["source_sha256"]), item["contracts"], kind, day, codes) for kind, item in files.items()}
    adjustments = json.loads(register("raw/bist/THF/futures-audit/official-contract-adjustments.json", ADJUSTMENTS_SHA).read_text())
    if set(adjustments["dates"]) != set(history["dates"]) or adjustments["no_returns_calculated"] is not True:
        raise ResearchInputError("adjustment dates/scope differ")
    changes = {date.fromisoformat(day): verify_adjustments(register(item["source_path"], item["source_sha256"]), item, codes) for day, item in adjustments["dates"].items()}
    samples, request_provenance = {}, []
    for name, digest in SAMPLE_RECEIPTS.items():
        sample = json.loads(register(f"raw/bist/THF/futures-audit/{name}", digest).read_text())
        for request in sample["requests"]:
            normalized = dict(request)
            normalized["path"] = str(canonical_path(root, request["path"]).relative_to(root))
            if normalized["path"] in samples: raise ResearchInputError("duplicate original sample receipt")
            samples[normalized["path"]] = {"source_receipt_path": name, "request": normalized}
    for name, digest in RECEIPTS.items():
        receipt = json.loads(register(f"raw/bist/THF/futures-audit/{name}", digest).read_text())
        if receipt["point_in_time_admitted"] is not False or receipt["rights_status"] != "UNKNOWN" or receipt.get("historical_first_publication_time") is not None:
            raise ResearchInputError("unqualified archive admission must remain explicit")
        for request in receipt["requests"]:
            request_provenance.append(verify_request(request, inputs, samples))
    source_admission = json.loads(register("raw/bist/THF/futures-audit/official-source-admission.json", ADMISSION_SHA).read_text())
    csv_sources = {name: item for name, item in inputs.items() if name.startswith("raw/bist/THF/futures-audit/") and name.endswith(".csv")}
    verify_admission(source_admission, csv_sources)
    # Check immutable source quantities against official report-date contract size.
    prepared = []
    for source, window in zip(inventory["reports"], equity["windows"], strict=True):
        positions, observations, reasons = [], {}, []
        report_day = date.fromisoformat(window["reported_period_end"])
        for row in source["rows"]:
            identity = row["contract"]
            spec = specification(identity, raw_by_day.get(report_day, {}).get("metadata", {}).get(identity))
            if spec is None:
                reasons.append(f"report_date_metadata_missing:{identity}"); continue
            quantity = Decimal(row["nominal_quantity"]["value"])
            with localcontext(Context(prec=128, rounding=ROUND_HALF_EVEN)):
                reconciled = (quantity >= 0 and spec.multiplier is not None and quantity * Decimal(row["daily_valuation_price"]["value"]) * spec.multiplier == Decimal(row["reported_total_value"]["value"]))
            if not reconciled:
                reasons.append(f"reported_notional_reconciliation_failed:{identity}")
            positions.append(FuturesPosition(spec, row["side"], quantity))
            observations[identity] = {}
            for day, files in raw_by_day.items():
                metadata, quote = files["metadata"].get(identity), files["settlements"].get(identity)
                if metadata and quote:
                    try: quote_spec = specification(identity, metadata)
                    except ResearchInputError: continue
                    if quote["VADE TARIHI"] != quote_spec.expiry.isoformat() or quote["DAYANAK VARLIK"] != metadata["DAYANAK VARLIK"]:
                        raise ResearchInputError("settlement identity/specification mismatch")
                    observations[identity][day] = SettlementObservation(quote_spec, day, positive_decimal(quote["UZLASMA FIYATI"]))
        prepared.append((window, source, positions, observations, reasons, changes))
    for item in tuple(inputs.values()): register(item["path"], item["sha256"])
    if code_gate(root) != code: raise ResearchInputError("runtime changed before calculation")
    windows = [evaluate_window(*arguments) for arguments in prepared]
    for item in tuple(inputs.values()): register(item["path"], item["sha256"])
    manifest = {"code": code, "equity_result_sha256": EQUITY_SHA, "inputs": sorted(inputs.values(), key=lambda i: i["path"]), "official_request_provenance": request_provenance}
    bundle = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    out = canonical_path(root, f"raw/bist/THF/futures-divergence/{bundle}/results.json")
    result = {"schema_version": 1, "fund_code": "THF", "data_mode": "HISTORICAL_REPLAY", "diagnostic_mode": "CONDITIONAL_ARCHIVE_DIAGNOSTIC", "point_in_time_admitted": False, "rights_status": "UNKNOWN", "alarm_threshold": None, "fund_status": "ABSTAINED", "fraud_status": "ABSTAINED", "actual_futures_pnl_status": "UNKNOWN", "manifest": manifest, "runtime_dependencies": {"python": sys.version, "PyMuPDF": fitz.VersionBind}, "windows": windows, "limitations": ["Static reported quantities, stale report NAV, no actual trades or daily positions", "Exact official settlement prices; no inferred rollover, interest or reinvestment", "Historical archive publication/revision times and data rights unqualified", "Observed agreement or residual does not establish actual causal attribution"]}
    unknown_endpoints = [record["path"] for record in request_provenance if record["final_response_url_status"] == "UNKNOWN"]
    if unknown_endpoints:
        result["limitations"].append(f"Final response URL UNKNOWN for {len(unknown_endpoints)} bound reused HTTP-200 samples: {', '.join(unknown_endpoints)}; recorded request URLs are official BIST")
    payload = (json.dumps(jsonable(result), ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists() and out.read_bytes() != payload: raise ResearchInputError("existing bundle bytes differ")
    if not out.exists():
        temporary = canonical_path(root, out.with_suffix(".tmp")); temporary.write_bytes(payload); temporary.replace(out)
    return out


def main() -> None:
    argparse.ArgumentParser(description=__doc__).parse_args()
    path = run()
    print(json.dumps({"result_path": str(path), "sha256": sha256(path)}))


if __name__ == "__main__":
    main()
