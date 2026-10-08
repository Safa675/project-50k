"""Synthetic scope, immutable-code and official-source gates for THF research."""
from __future__ import annotations

import copy
import csv
from datetime import date, datetime
from decimal import Decimal, Inexact, Rounded, localcontext
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

from p50k.analytics.futures_contribution import ContractSpecification, FuturesPosition, SettlementObservation

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "research/events/2026-09-17-spk-liquidations/fund_futures_divergence/run.py"
SPEC = importlib.util.spec_from_file_location("futures_research_runner", SCRIPT)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def metadata(identity="F_TEST0926", stock=True):
    return {"SOZLESME KODU": identity, "SOZLESME TIPI": "D_EQ_FPD" if stock else "D_IX_FUT",
            "SOZLESME TURU": "Future", "SOZLESME GRUBU": "S", "PARA BIRIMI": "TRY",
            "SOZLESME BUYUKLUGU": "10", "VADE TARIHI": "2026-09-30", "SON ISLEM TARIHI": "2026-09-30",
            "UZLASMA TIPI": "Physical Delivery" if stock else "Cash Settlement", "DURUM": "A",
            "DAYANAK VARLIK": "SYNTHETIC"}


def daily(identity="F_TEST0926"):
    return {"SOZLESME KODU": identity, "TARIH": "2026-08-05", "VADE TARIHI": "2026-09-30",
            "DAYANAK VARLIK": "SYNTHETIC", "UZLASMA FIYATI": "110", "KAPANIS FIYATI": "111"}


def derived(raw, kind="settlements"):
    fields = runner.DAILY_FIELDS if kind == "settlements" else runner.META_FIELDS
    record = {key: raw[column] for key, column in fields.items()}
    record.update(contract_code=raw["SOZLESME KODU"], status="PRESENT", source_csv_row="3")
    if kind == "settlements":
        record.update(settlement_price="110", close_price="111")
    else:
        record["multiplier"] = "10"
    return record


def window():
    return {"snapshot_id": "2026-07", "reported_period_end": "2026-07-31",
        "available_at": "2026-08-03T12:00:00+03:00", "base_date": "2026-08-04", "base_fund_row_label": "2026-08-05",
        "next_publication_date": "2026-09-02", "extraction": {"headline_total_value": {"value": "1000"}},
        "rows": [{"valuation_date": "2026-08-05", "fund_row_label": "2026-08-06", "interval_number": 1,
                  "metric": {"availability": "AVAILABLE", "equity_proxy_return": "0.1", "actual_return": "0.35", "gap": "0.25"}}]}


def synthetic_inputs():
    spec = ContractSpecification("F_TEST0926", Decimal("10"), date(2026, 9, 30), "CASH", "TRY", "INDEX_POINTS", "TRY_PER_INDEX_POINT")
    position = FuturesPosition(spec, "LONG", Decimal("2"))
    quotes = {spec.contract_id: {day: SettlementObservation(spec, day, Decimal(price)) for day, price in ((date(2026, 8, 4), "100"), (date(2026, 8, 5), "110"))}}
    return {"rows": [{"contract": spec.contract_id, "side": "LONG"}]}, [position], quotes


class RunnerTests(unittest.TestCase):
    def csv_file(self, root, raw, kind="settlements", extra=None):
        path = root / "synthetic.csv"
        descriptor = {key: "LABEL" for key in raw}
        descriptor["SOZLESME KODU"] = "INSTRUMENT SERIES" if kind in ("settlements", "adjustments") else "CONTRACT CODE"
        with path.open("w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(raw), delimiter=";")
            writer.writeheader(); writer.writerow(descriptor); writer.writerow(raw)
            if extra: writer.writerow(extra)
        return path

    def test_only_settlement_is_used_not_close_or_metadata_last(self):
        raw = daily()
        with tempfile.TemporaryDirectory() as folder:
            parsed = runner.verify_csv(self.csv_file(Path(folder), raw), [derived(raw)], "settlements", "2026-08-05", {raw["SOZLESME KODU"]})
        self.assertEqual(parsed[raw["SOZLESME KODU"]]["UZLASMA FIYATI"], "110")
        self.assertNotEqual(parsed[raw["SOZLESME KODU"]]["UZLASMA FIYATI"], parsed[raw["SOZLESME KODU"]]["KAPANIS FIYATI"])

    def test_csv_missing_contract_stays_absent(self):
        raw = daily()
        record = {"contract_code": "F_OTHER0926", "status": "ABSENT_FROM_OFFICIAL_DAILY_FILE"}
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(runner.verify_csv(self.csv_file(Path(folder), raw), [record], "settlements", "2026-08-05", {"F_OTHER0926"}), {})
            record["settlement_price"] = "0"
            with self.assertRaises(runner.ResearchInputError):
                runner.verify_csv(Path(folder) / "synthetic.csv", [record], "settlements", "2026-08-05", {"F_OTHER0926"})

    def test_zero_and_nonfinite_quotes_stay_missing(self):
        for value in ("0", "-1", "NaN", "Infinity", "", None, True):
            self.assertIsNone(runner.positive_decimal(value))
        raw = daily(); raw["UZLASMA FIYATI"] = "0"; record = derived(raw); record["settlement_price"] = None
        with tempfile.TemporaryDirectory() as folder:
            parsed = runner.verify_csv(self.csv_file(Path(folder), raw), [record], "settlements", "2026-08-05", {raw["SOZLESME KODU"]})
        self.assertIsNone(runner.positive_decimal(parsed[raw["SOZLESME KODU"]]["UZLASMA FIYATI"]))

    def test_csv_duplicate_date_wrong_field_and_coordinates_rejected(self):
        raw = daily()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = self.csv_file(root, raw, extra=raw)
            with self.assertRaises(runner.ResearchInputError): runner.verify_csv(path, [derived(raw)], "settlements", "2026-08-05", {raw["SOZLESME KODU"]})
            path = self.csv_file(root, raw)
            for field, value in (("source_csv_row", "4"), ("settlement_price_raw", "999"), ("settlement_price", "111")):
                record = derived(raw); record[field] = value
                with self.assertRaises(runner.ResearchInputError): runner.verify_csv(path, [record], "settlements", "2026-08-05", {raw["SOZLESME KODU"]})
            with self.assertRaises(runner.ResearchInputError): runner.verify_csv(path, [derived(raw)], "settlements", "2026-08-06", {raw["SOZLESME KODU"]})

    def test_schema_failure_prevents_reading_arithmetic(self):
        raw = daily(); del raw["UZLASMA FIYATI"]
        with tempfile.TemporaryDirectory() as folder, self.assertRaises(runner.ResearchInputError):
            runner.verify_csv(self.csv_file(Path(folder), raw), [], "settlements", "2026-08-05", set())

    def test_metadata_has_different_descriptor_and_physical_stock_type(self):
        raw = metadata()
        with tempfile.TemporaryDirectory() as folder:
            parsed = runner.verify_csv(self.csv_file(Path(folder), raw, "metadata"), [derived(raw, "metadata")], "metadata", "2026-08-05", {raw["SOZLESME KODU"]})
        spec = runner.specification(raw["SOZLESME KODU"], parsed[raw["SOZLESME KODU"]])
        self.assertEqual(spec.settlement_type, "PHYSICAL")
        self.assertEqual((spec.price_unit, spec.multiplier_unit), ("TRY_PER_SHARE", "SHARES_PER_CONTRACT"))
        self.assertEqual(runner.specification("F_TEST0926", metadata(stock=False)).settlement_type, "CASH")

    def test_exact_metadata_identity_currency_and_suffix_required(self):
        for key, changed in (("SOZLESME KODU", "F_OTHER0926"), ("PARA BIRIMI", "USD"), ("SOZLESME GRUBU", "N"), ("SOZLESME TIPI", "UNKNOWN"), ("VADE TARIHI", "2026-10-30")):
            raw = metadata(); raw[key] = changed
            with self.assertRaises(runner.ResearchInputError): runner.specification("F_TEST0926", raw)
        self.assertIsNone(runner.specification("F_TEST0926", None))

    def test_report_before_publication_and_future_intervals_rejected(self):
        published = datetime(2026, 8, 3, 12, tzinfo=ZoneInfo("Europe/Istanbul"))
        runner.validate_window_scope(window(), "2026-07", published)
        for changed in ("2026-08-03", "2026-08-02"):
            w = window(); w["base_date"] = changed
            with self.assertRaises(runner.ResearchInputError): runner.validate_window_scope(w, "2026-07", published)
        for field, changed in (("valuation_date", "2026-09-02"), ("fund_row_label", "2026-09-17")):
            w = window(); w["rows"][0][field] = changed
            with self.assertRaises(runner.ResearchInputError): runner.validate_window_scope(w, "2026-07", published)

    def test_other_fund_rejected_before_any_original_file_read(self):
        with self.assertRaises(runner.ResearchInputError):
            runner.verify_inventory({"fund_code": "OTHER"}, {"fund_code": "THF"}, lambda *a: self.fail("file read"))

    def test_run_stops_at_code_gate_before_any_real_source_or_contribution(self):
        with patch.object(runner, "code_gate", side_effect=runner.ResearchInputError("not committed")), patch("p50k.analytics.futures_contribution.calculate_futures_contribution") as arithmetic:
            with self.assertRaises(runner.ResearchInputError): runner.run()
            arithmetic.assert_not_called()

    def test_real_git_blob_and_original_protocol_are_required(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            paths = (runner.PROTOCOL, *runner.RUNTIME)
            for name in paths:
                path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text("# synthetic fixture\n")
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            def commit(): subprocess.run(["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "synthetic fixture"], cwd=root, check=True)
            commit(); head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, check=True, text=True).stdout.strip()
            with patch.object(runner, "PREREGISTRATION_COMMIT", head):
                self.assertEqual(runner.code_gate(root)["preregistration_commit"], head)
                (root / "unrelated.txt").write_text("unrelated")
                self.assertEqual(runner.code_gate(root)["head"], head)
                (root / runner.RUNTIME[0]).write_text("# uncommitted mutation\n")
                with self.assertRaises(runner.ResearchInputError): runner.code_gate(root)
                (root / runner.RUNTIME[0]).write_text("# synthetic fixture\n")
                (root / runner.PROTOCOL).write_text("# changed protocol\n")
                subprocess.run(["git", "add", runner.PROTOCOL], cwd=root, check=True); commit()
                with self.assertRaises(runner.ResearchInputError): runner.code_gate(root)

    def test_no_reported_positions_actual_activity_remains_unknown(self):
        result = runner.evaluate_window(window(), {"rows": []}, [], {}, [])
        row = result["rows"][0]
        self.assertEqual(row["futures_metric"]["availability"], "NO_REPORTED_POSITIONS_ACTUAL_ACTIVITY_UNKNOWN")
        self.assertIsNone(row["futures_metric"]["contribution"])
        self.assertIsNone(row["remaining_gap"])
        self.assertEqual(row["metric"], window()["rows"][0]["metric"])

    def test_combined_reference_units_and_original_missing_stock_preserved(self):
        source, positions, quotes = synthetic_inputs()
        result = runner.evaluate_window(window(), source, positions, quotes, [])
        row = result["rows"][0]
        self.assertEqual(Decimal(row["futures_metric"]["pnl_try"]), Decimal("200"))
        self.assertEqual(Decimal(row["futures_metric"]["contribution"]), Decimal("0.2"))
        self.assertEqual(Decimal(row["combined_reference_return"]), Decimal("0.3"))
        self.assertEqual(Decimal(row["remaining_gap"]), Decimal("0.05"))
        w = window(); w["rows"][0]["metric"] = {"availability": "UNAVAILABLE", "reasons": ["synthetic_missing_stock"]}
        row = runner.evaluate_window(w, source, positions, quotes, [])["rows"][0]
        self.assertEqual(row["futures_metric"]["availability"], "AVAILABLE")
        self.assertEqual(row["combined_availability"], "UNAVAILABLE")
        self.assertEqual(row["metric"], w["rows"][0]["metric"])
        self.assertIsNone(row["remaining_gap"])

    def test_missing_futures_cannot_be_substituted_with_zero(self):
        source, positions, quotes = synthetic_inputs(); quotes[positions[0].spec.contract_id].pop(date(2026, 8, 5))
        row = runner.evaluate_window(window(), source, positions, quotes, [])["rows"][0]
        self.assertEqual(row["futures_metric"]["availability"], "UNAVAILABLE")
        self.assertIsNone(row["combined_reference_return"])

    def test_future_quote_and_later_report_weights_cannot_change_earlier_window(self):
        source, positions, quotes = synthetic_inputs(); expected = runner.evaluate_window(window(), source, positions, quotes, [])
        spec = positions[0].spec
        quotes[spec.contract_id][date(2026, 8, 6)] = SettlementObservation(spec, date(2026, 8, 6), Decimal("99999"))
        source["later_report_positions"] = [{"contract": "F_OTHER1026", "nominal_quantity": "99999"}]
        self.assertEqual(runner.evaluate_window(window(), source, positions, quotes, []), expected)

    def test_future_adjustment_does_not_invalidate_earlier_row(self):
        source, positions, quotes = synthetic_inputs(); expected = runner.evaluate_window(window(), source, positions, quotes, [])
        change = metadata(stock=False); change["SOZLESME BUYUKLUGU"] = "20"
        future = {date(2026, 8, 6): [change]}
        self.assertEqual(runner.evaluate_window(window(), source, positions, quotes, [], future), expected)
        present = {date(2026, 8, 5): [change]}
        row = runner.evaluate_window(window(), source, positions, quotes, [], present)["rows"][0]
        self.assertEqual(row["futures_metric"]["availability"], "UNAVAILABLE")
        self.assertIn("unresolved_contract_adjustment", row["futures_metric"]["reasons"][0])

    def test_expected_expiration_change_keeps_cash_pnl_and_no_roll(self):
        source, positions, quotes = synthetic_inputs(); spec = positions[0].spec
        expiry = date(2026, 9, 30); quotes[spec.contract_id][expiry] = SettlementObservation(spec, expiry, Decimal("120"))
        w = window(); w["rows"][0].update(valuation_date="2026-10-01", fund_row_label="2026-10-02")
        change = metadata(stock=False); change["DURUM"] = "E"
        expected = runner.evaluate_window(w, source, positions, quotes, [])
        actual = runner.evaluate_window(w, source, positions, quotes, [], {date(2026, 10, 1): [change]})
        self.assertEqual(actual, expected)
        self.assertEqual(actual["rows"][0]["futures_metric"]["items"][0]["mark_date"], "2026-09-30")

    def test_post_expiry_changes_cannot_alter_locked_cash_contribution(self):
        source, positions, quotes = synthetic_inputs(); spec = positions[0].spec
        expiry = date(2026, 9, 30); quotes[spec.contract_id][expiry] = SettlementObservation(spec, expiry, Decimal("120"))
        w = window(); w["rows"][0].update(valuation_date="2026-10-02", fund_row_label="2026-10-03")
        expected = runner.evaluate_window(w, source, positions, quotes, [])
        changed = metadata(stock=False); changed.update({"SOZLESME BUYUKLUGU": "999", "SOZLESME GRUBU": "N", "PARA BIRIMI": "USD"})
        self.assertEqual(runner.evaluate_window(w, source, positions, quotes, [], {date(2026, 10, 1): [changed]}), expected)

    def test_official_admission_requires_every_source_and_unknown_historical_rights(self):
        path = "raw/bist/THF/futures-audit/viop_20260805.csv"; sources = {path: {"sha256": "synthetic_digest"}}
        record = {"path": path, "sha256": "synthetic_digest", "source_url": "https://www.borsaistanbul.com/data/vadeli/viop_20260805.csv", "observed_at": "2026-10-08T12:00:00+00:00", "historical_first_publication_time": None, "point_in_time_admitted": False, "rights_status": "UNKNOWN", "data_mode": "HISTORICAL_REPLAY"}
        admission = {"sources": [record], "source_count": 1}
        runner.verify_admission(admission, sources)
        for key, value in (("rights_status", "APPROVED"), ("point_in_time_admitted", True), ("sha256", "changed"), ("observed_at", "2026-10-08T12:00:00"), ("source_url", "https://example.invalid/prices"), ("historical_first_publication_time", "2026-08-05T12:00:00+00:00")):
            mutated = copy.deepcopy(admission); mutated["sources"][0][key] = value
            with self.assertRaises(runner.ResearchInputError): runner.verify_admission(mutated, sources)
        with self.assertRaises(runner.ResearchInputError): runner.verify_admission(admission, {**sources, "missing.csv": {"sha256": "unknown"}})

    def test_reused_sample_preserves_unknown_final_url_with_original_http_proof(self):
        path = "raw/bist/THF/futures-audit/viopsz_20260805.csv"
        request = {"path": path, "sha256": "synthetic_digest", "bytes": 123, "url": "https://www.borsaistanbul.com/data/vadeli/viopsz_20260805.csv", "status": 200, "observed_at": "2026-10-08T12:00:00+00:00", "reused_existing_sample": True}
        inputs = {path: {"sha256": "synthetic_digest"}}
        original = {"source_receipt_path": "official-adjustments-sample-receipt.json", "request": {key: value for key, value in request.items() if key != "reused_existing_sample"}}
        actual = runner.verify_request(request, inputs, {path: original})
        self.assertIsNone(actual["final_response_url"])
        self.assertEqual(actual["final_response_url_status"], "UNKNOWN")
        self.assertEqual(actual["original_sample_receipt"], "official-adjustments-sample-receipt.json")
        self.assertNotIn("final_url", request)
        original["request"]["final_url"] = request["url"]
        known = runner.verify_request(request, inputs, {path: original})
        self.assertEqual(known["final_response_url"], request["url"])
        self.assertEqual(known["final_response_url_status"], "RECORDED")

    def test_unbound_missing_endpoint_and_changed_original_receipt_are_rejected(self):
        path = "raw/bist/THF/futures-audit/viopsz_20260805.csv"
        request = {"path": path, "sha256": "synthetic_digest", "bytes": 123, "url": "https://www.borsaistanbul.com/data/vadeli/viopsz_20260805.csv", "status": 200, "observed_at": "2026-10-08T12:00:00+00:00", "reused_existing_sample": True}
        inputs = {path: {"sha256": "synthetic_digest"}}
        original = {"source_receipt_path": "official-adjustments-sample-receipt.json", "request": dict(request)}
        with self.assertRaises(runner.ResearchInputError): runner.verify_request(request, inputs, {})
        fresh = dict(request); fresh["reused_existing_sample"] = False
        with self.assertRaises(runner.ResearchInputError): runner.verify_request(fresh, inputs, {path: original})
        for key, changed in (("sha256", "changed"), ("observed_at", "2026-10-08T13:00:00+00:00"), ("status", 500), ("bytes", 124), ("url", "https://example.invalid/file"), ("final_url", "https://example.invalid/redirect")):
            mutated = copy.deepcopy(original); mutated["request"][key] = changed
            with self.assertRaises(runner.ResearchInputError): runner.verify_request(request, inputs, {path: mutated})
        wrong_final = dict(request); wrong_final["final_url"] = "https://example.invalid/redirect"
        with self.assertRaises(runner.ResearchInputError): runner.verify_request(wrong_final, inputs, {path: original})
        complete = dict(request); complete["reused_existing_sample"] = False; complete["final_url"] = request["url"]
        self.assertEqual(runner.verify_request(complete, inputs, {})["final_response_url_status"], "RECORDED")

    def test_adjustment_csv_duplicate_records_are_preserved(self):
        raw = metadata(); raw["TARIH"] = "2026-08-05"
        with tempfile.TemporaryDirectory() as folder:
            path = self.csv_file(Path(folder), raw, "adjustments", extra=raw)
            record = {"reported_contract_records": [{"source_csv_row": 3, "fields": raw}, {"source_csv_row": 4, "fields": raw}], "source_record_count": 2, "status": "EXACT_REPORTED_CODE_RECORDS_PRESENT"}
            self.assertEqual(runner.verify_adjustments(path, record, {raw["SOZLESME KODU"]}), [raw, raw])
            record["reported_contract_records"].pop()
            with self.assertRaises(runner.ResearchInputError): runner.verify_adjustments(path, record, {raw["SOZLESME KODU"]})

    def test_arithmetic_summary_ignores_ambient_precision_and_traps(self):
        source, positions, quotes = synthetic_inputs(); w = window()
        first = w["rows"][0]; first["metric"]["actual_return"] = "0.423456781"
        second = copy.deepcopy(first); second["interval_number"] = 2; second["metric"]["actual_return"] = "0.423456789"; w["rows"].append(second)
        expected = runner.evaluate_window(w, source, positions, quotes, [])
        with localcontext() as context:
            context.prec = 3; context.traps[Inexact] = True; context.traps[Rounded] = True
            actual = runner.evaluate_window(w, source, positions, quotes, [])
        self.assertEqual(actual, expected)
        self.assertEqual(actual["summary"]["largest_absolute_remaining_gap"]["interval_number"], 2)


if __name__ == "__main__": unittest.main()
