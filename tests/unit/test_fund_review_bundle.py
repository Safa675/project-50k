from __future__ import annotations

import copy
import importlib.util
import json
import math
import tempfile
import unittest
import sqlite3
import subprocess
from datetime import date, timedelta
from decimal import Decimal, Inexact, InvalidOperation, Rounded, ROUND_DOWN, localcontext
from pathlib import Path
from unittest.mock import patch

from p50k.research_reviews.bundle import (
    BundleIntegrityError, SourceRegistry, assemble, canonical_bytes, d1_context, digest,
    flow_finding, load_bundle, load_frozen_detector, price_rows, read_fund_json,
    reconcile_report_list, resolve_pdf, selected_reports, validate_universe, write_bundle,
    selected_snapshot,
    number,
)
from p50k.research_reviews.contracts import METADATA, SCHEMA, empty_finding
from p50k.research_reviews.comments import describe, summarize

REPO = Path(__file__).resolve().parents[2]
CODES = [f"Z{i:02d}" for i in range(100)]


def report(period: str, assets: str, nav: str = "1", **kwargs) -> dict:
    result = {"period": period, "cadence": "monthly", "total_value": assets,
              "period_end_price": nav, "published_at": "2026-09-02T11:00:00+03:00",
              "disclosure_index": 1 if period == "2026-07" else 2}
    result.update(kwargs)
    return result


def payload(closing: str = "110", **kwargs) -> dict:
    return {"fund": "Z00", "reports": [report("2026-07", "100"), report("2026-08", closing, **kwargs)]}


def all_missing_bundle(registry: SourceRegistry | None = None) -> dict:
    records = []
    for code in CODES:
        d1, flow = empty_finding("d1"), empty_finding("flow")
        comment, assessment, crossings = describe(d1, flow)
        records.append({"code": code, "name": code, "category": None, "comment_tr": comment,
                        "assessment": assessment, "eligible_crossings": crossings, "d1": d1,
                        "flow": flow, "evidence": [], "chart": {"status": "UNAVAILABLE", "reason": "missing",
                        "baseline_date": None, "unit": "INDEX_100", "points": [], "peer_count": 0}})
    summary = summarize(records)
    summary.update(d1_assessable=0, flow_assessable=0, d1_stale=0)
    result = {"schema": SCHEMA, **METADATA, "summary": summary, "funds": records,
              "sources": list(registry.sources.values()) if registry else [],
              "manifest": list(registry.manifest.values()) if registry else [], "registration": {}}
    result["immutable_bundle_id"] = digest(canonical_bytes(result))
    return result


class FlowReviewTests(unittest.TestCase):
    def test_number_parsing_preserves_caller_flags_traps_and_precision(self):
        for invalid_trap in (True, False):
            with localcontext() as caller:
                caller.clear_flags()
                caller.prec = 2
                caller.rounding = ROUND_DOWN
                caller.traps[InvalidOperation] = invalid_trap
                caller.traps[Inexact] = True
                caller.traps[Rounded] = True
                caller.flags[Inexact] = True  # Existing signals must survive too.
                before_flags, before_traps = caller.flags.copy(), caller.traps.copy()
                for value in ("bad", "1e999999999999999999999", "NaN", "Infinity", "sNaN", None, True, 1.5):
                    self.assertIsNone(number(value))
                self.assertEqual(number("123456789.123456789"), Decimal("123456789.123456789"))
                self.assertEqual(caller.flags, before_flags)
                self.assertEqual(caller.traps, before_traps)
                self.assertEqual((caller.prec, caller.rounding), (2, ROUND_DOWN))

    def test_invalid_flow_inputs_preserve_caller_context(self):
        with localcontext() as caller:
            caller.clear_flags()
            caller.prec = 2
            caller.traps[InvalidOperation] = True
            caller.traps[Inexact] = True
            caller.traps[Rounded] = True
            flags, traps = caller.flags.copy(), caller.traps.copy()
            result = flow_finding(payload(period_end_price="bad"), None)
            self.assertEqual(result["arithmetic_status"], "UNAVAILABLE")
            self.assertEqual(caller.flags, flags)
            self.assertEqual(caller.traps, traps)
            self.assertEqual(caller.prec, 2)

    def test_both_signed_boundary_equalities_cross(self):
        for closing, direction in (("110", "INFLOW_ESTIMATE"), ("90", "OUTFLOW_ESTIMATE")):
            with self.subTest(closing=closing):
                result = flow_finding(payload(closing), "a" * 64)
                self.assertEqual(result["research_screen"], "CROSSING")
                self.assertEqual(result["direction"], direction)
                self.assertEqual(abs(Decimal(result["statistic"])), Decimal("0.10"))
                self.assertEqual(result["production_status"], "ABSTAINED")
                self.assertIn("currency_unknown_common_report_field_assumption", result["qualifications"])

    def test_below_boundary_non_crossing_and_zero_closing_allowed(self):
        self.assertEqual(flow_finding(payload("109.999"), None)["research_screen"], "NO_CROSSING")
        self.assertEqual(flow_finding(payload("0"), None)["statistic"], "-1")

    def test_decimal_helper_reused_for_price_adjustment(self):
        result = flow_finding(payload("132", period_end_price="1.2"), None)
        self.assertEqual(Decimal(result["residual"]), Decimal("12.0"))
        self.assertEqual(Decimal(result["statistic"]), Decimal("0.12"))

    def test_invalid_and_missing_values_remain_unknown(self):
        for value in (None, "NaN", "Infinity", "0", "-1", True, 1.5, "bad"):
            with self.subTest(value=value):
                result = flow_finding(payload(period_end_price=value), None)
                self.assertEqual(result["arithmetic_status"], "UNAVAILABLE")
                self.assertIsNone(result["statistic"])
                self.assertEqual(result["research_screen"], "UNKNOWN")

    def test_wrong_pair_not_replaced_by_earlier_valid_pair(self):
        data = payload()
        data["reports"][1]["period"] = "2026-09"
        data["reports"].append(report("2026-06", "100"))
        self.assertEqual(flow_finding(data, None)["arithmetic_status"], "UNAVAILABLE")

    def test_duplicate_eligible_and_missing_publication_disable_pair(self):
        for extra in (report("2026-08", "999"), report("2026-08", "999", published_at=None)):
            data = payload()
            data["reports"].append(extra)
            self.assertEqual(flow_finding(data, None)["arithmetic_status"], "UNAVAILABLE")

    def test_weekly_and_late_duplicate_do_not_enter(self):
        data = payload()
        expected = flow_finding(data, None)
        data["reports"].extend([report("2026-08", "999", cadence="weekly"),
                                report("2026-08", "999", published_at="2026-09-17T00:00:00+03:00")])
        self.assertEqual(expected, flow_finding(data, None))

    def test_cutoff_inclusive_and_publication_unambiguous(self):
        self.assertEqual(flow_finding(payload(published_at="2026-09-16T23:59:59+03:00"), None)[
            "arithmetic_status"], "AVAILABLE")
        for timing in (None, "2026-09-02", "2026-09-02T11:00:00", "bad", "2026-09-17T00:00:00+03:00"):
            self.assertEqual(flow_finding(payload(published_at=timing), None)["arithmetic_status"], "UNAVAILABLE")
        result = flow_finding(payload(published_at="02.09.2026 11:00:00"), None)
        self.assertEqual(result["arithmetic_status"], "AVAILABLE")
        self.assertIn("publication_timezone_assumed_europe_istanbul", result["qualifications"])

    def test_known_units_scope_or_actions_incompatible(self):
        for field, value in (("currency", "USD"), ("fund_scope", "different"), ("share_class", "B"),
                             ("assets_unit", "USD"), ("nav_unit", "USD/unit"),
                             ("distribution_status", "YES"), ("unit_change_status", "SPLIT"),
                             ("merger_status", "MERGED"), ("valuation_basis", "WEEK_END"),
                             ("asset_basis", "GROSS_ASSETS"), ("nav_basis", "ADJUSTED_NAV")):
            with self.subTest(field=field):
                data = payload()
                data["reports"][0].update(currency="TRY", assets_unit="TRY", nav_unit="TRY/unit",
                                            fund_scope="whole", share_class="A")
                data["reports"][1].update(currency="TRY", assets_unit="TRY", nav_unit="TRY/unit",
                                            fund_scope="whole", share_class="A")
                data["reports"][1][field] = value
                self.assertEqual(flow_finding(data, None)["arithmetic_status"], "UNAVAILABLE")

    def test_reconciles_duplicate_disclosures_hidden_by_extractor(self):
        data = payload()
        listing = [{"disclosureBasic": {"year": 2026, "donem": month, "period": "AB",
                    "disclosureIndex": index, "publishDate": "02.09.2026 11:00:00"}}
                   for month, index in ((7, 1), (8, 2), (8, 3))]
        result = reconcile_report_list(data, listing)
        self.assertEqual(flow_finding(result, None)["arithmetic_status"], "UNAVAILABLE")
        listing[-1]["disclosureBasic"]["publishDate"] = "17.09.2026 11:00:00"
        self.assertEqual(flow_finding(reconcile_report_list(data, listing), None),
                         flow_finding(reconcile_report_list(data, listing[:-1]), None))
        self.assertIn("report_list_publication_timezone_assumed_europe_istanbul",
                      flow_finding(reconcile_report_list(data, listing), None)["qualifications"])

    def test_missing_malformed_or_conflicting_report_list_disables_flow(self):
        data = payload()
        for listing in (None, {"bad": True}, [{"bad": True}], []):
            self.assertEqual(flow_finding(reconcile_report_list(data, listing), None)["arithmetic_status"], "UNAVAILABLE")
        listing = [{"disclosureBasic": {"year": 2026, "donem": month, "period": "AB",
                    "disclosureIndex": index, "publishDate": "03.09.2026 11:00:00"}}
                   for month, index in ((7, 1), (8, 2))]
        result = flow_finding(reconcile_report_list(data, listing), None)
        self.assertIn("report_list_series_publication_mismatch", result["missing_reasons"])

    def test_malformed_report_array_retains_unavailable_fund(self):
        listing = [{"disclosureBasic": {"year": 2026, "donem": 8, "period": "AB",
                                        "disclosureIndex": 2, "publishDate": "02.09.2026 11:00:00"}}]
        for reports in (None, {}, 123, "bad"):
            result = flow_finding(reconcile_report_list({"reports": reports}, listing), None)
            self.assertEqual(result["arithmetic_status"], "UNAVAILABLE")
            self.assertIn("kap_series_invalid", result["missing_reasons"])

    def test_nested_known_unit_mismatch_is_not_unknown_assumption(self):
        data = payload()
        for item in data["reports"]:
            item["currency"] = "TRY"
            item["units"] = {"total_value": "TRY", "nav": "USD/unit"}
        self.assertEqual(flow_finding(data, None)["arithmetic_status"], "UNAVAILABLE")


class BundleIntegrityTests(unittest.TestCase):
    def test_exactly_100_including_all_missing(self):
        bundle = all_missing_bundle()
        self.assertEqual(bundle["summary"]["total"], 100)
        self.assertEqual(bundle["summary"]["unavailable"], 100)
        self.assertEqual(len(bundle["funds"]), 100)
        self.assertEqual(bundle["summary"]["no_findings"], 0)

    def test_unopened_and_traversal_rejected_before_file_read(self):
        with patch.object(Path, "exists", side_effect=AssertionError("input path was touched")):
            for code in ("AAA", "../", "https://example.com", "Z100"):
                with self.assertRaises(ValueError):
                    read_fund_json(code, CODES, Path("/synthetic"), kind="PRICE")

    def test_rejects_bad_universe(self):
        for codes in (CODES[:-1], CODES + ["AAA"], CODES[:-1] + [CODES[0]]):
            with self.assertRaises(ValueError):
                validate_universe(codes)

    def test_atomic_idempotent_seal_hash_corruption_and_missing_fingerprint(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = write_bundle(Path(tmp), all_missing_bundle())
            self.assertEqual(load_bundle(directory)["summary"]["total"], 100)
            self.assertEqual(write_bundle(Path(tmp), all_missing_bundle()), directory)
            data = json.loads((directory / "bundle.json").read_bytes())
            data["funds"][0]["name"] = "changed"
            (directory / "bundle.json").write_bytes(canonical_bytes(data))
            with self.assertRaises(BundleIntegrityError):
                load_bundle(directory)
            data.pop("immutable_bundle_id")
            (directory / "bundle.json").write_bytes(canonical_bytes(data))
            with self.assertRaises(BundleIntegrityError):
                load_bundle(directory)

    def test_original_and_pdf_copy_changes_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf = root / "synthetic.pdf"
            original = b"%PDF-1.4\nsynthetic only\n"
            pdf.write_bytes(original)
            registry = SourceRegistry()
            identifier = registry.add(pdf, "KAP_PDF", fund_code="Z00", disclosure_id="2")
            directory = write_bundle(root / "bundles", all_missing_bundle(registry))
            copy_path = resolve_pdf(directory, identifier)
            self.assertEqual(copy_path.read_bytes(), original)
            pdf.write_bytes(b"%PDF-1.4\nchanged\n")
            with self.assertRaises(BundleIntegrityError):
                load_bundle(directory)
            pdf.write_bytes(original)
            copy_path.write_bytes(b"%PDF-1.4\nchanged copy\n")
            with self.assertRaises(BundleIntegrityError):
                resolve_pdf(directory, identifier)

    def test_opaque_source_identifier_stable_after_future_only_bytes_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "synthetic.json"
            path.write_bytes(b'{"future":"one"}')
            first = SourceRegistry()
            a = first.add(path, "PRICE", fund_code="Z00")
            path.write_bytes(b'{"future":"two"}')
            second = SourceRegistry()
            b = second.add(path, "PRICE", fund_code="Z00")
            self.assertEqual(a, b)
            self.assertNotEqual(first.sources[a]["sha256"], second.sources[b]["sha256"])

    def test_unknown_source_and_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = write_bundle(Path(tmp), all_missing_bundle())
            for source in ("../bundle.json", "https://example.com", "a" * 64):
                with self.assertRaises(BundleIntegrityError):
                    resolve_pdf(directory, source)
            alias = Path(tmp) / "alias.json"
            alias.symlink_to(directory / "bundle.json")
            with self.assertRaises(BundleIntegrityError):
                SourceRegistry().add(alias, "PRICE")

    def test_price_zeros_gaps_nonfinite_and_duplicates(self):
        rows, reasons = price_rows({"rows": [["2026-09-15", "0"], ["2026-09-16", "NaN"],
                                            ["2026-09-17", "999"]]})
        self.assertEqual(rows, {"2026-09-15": None, "2026-09-16": None})
        self.assertEqual(reasons, [])
        rows, reasons = price_rows({"rows": [["2026-09-16", "1"], ["2026-09-16", "2"]]})
        self.assertEqual(rows, {})
        self.assertIn("duplicate_price_date", reasons)

    def test_selected_snapshot_projection_ignores_unopened_and_investor_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "snapshots.sqlite3"
            connection = sqlite3.connect(path)
            connection.execute("CREATE TABLE fund_snapshots(fund TEXT,category TEXT,raw_snapshot TEXT,retrieved_at TEXT)")
            connection.execute("INSERT INTO fund_snapshots VALUES(?,?,?,?)", ("Z00", "Synthetic", '{"fonUnvan":"Synthetic zero","investors":1}', "2026-10-08T00:00:00+03:00"))
            connection.execute("INSERT INTO fund_snapshots VALUES(?,?,?,?)", ("AAA", "Unopened", '{"fonUnvan":"Unopened","investors":999}', "2026-10-08T00:00:00+03:00"))
            connection.commit()
            first = selected_snapshot(path, CODES)
            connection.execute("UPDATE fund_snapshots SET raw_snapshot=? WHERE fund=?", ('{"fonUnvan":"Synthetic zero","investors":1000,"liquidated_after_cutoff":true}', "Z00"))
            connection.execute("UPDATE fund_snapshots SET category=? WHERE fund=?", ("Changed unopened", "AAA"))
            connection.commit()
            second = selected_snapshot(path, CODES)
            connection.close()
            self.assertEqual(first, second)
            self.assertNotIn("AAA", json.loads(first))

    def test_registry_rejects_changed_input_between_read_and_register(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "synthetic.json"
            path.write_bytes(b'{}')
            expected = digest(path.read_bytes())
            path.write_bytes(b'{"changed":true}')
            with self.assertRaises(BundleIntegrityError):
                SourceRegistry().add(path, "PRICE", expected_sha256=expected)

    def test_actual_allowlist_checked_before_original_manifest_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "synthetic.json"
            path.write_bytes(b'{}')
            registry = SourceRegistry()
            registry.add(path, "PRICE", fund_code="Z00")
            directory = write_bundle(root / "bundles", all_missing_bundle(registry))
            import p50k.research_reviews.bundle as module
            with patch.object(module, "_source_bytes", side_effect=AssertionError("original source touched")):
                with self.assertRaises(BundleIntegrityError):
                    load_bundle(directory, allowed_codes=CODES[:-1] + ["AAA"])


class FundReviewRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = REPO / "research/events/2026-09-17-spk-liquidations/fund_review_app/run.py"
        spec = importlib.util.spec_from_file_location("test_fund_review_runner", path)
        cls.runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.runner)

    def synthetic_repo(self, root: Path) -> None:
        for relative in (self.runner.DETECTOR_REL, *self.runner.RUNTIME_FILES):
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((REPO / relative).read_bytes())
        (root / self.runner.PROTOCOL_REL).write_text("Synthetic fixed protocol, no real fund observations.\n")
        (root / self.runner.ALLOWLIST_REL).write_text("\n".join(CODES) + "\n")
        (root / self.runner.CALIBRATION_REL).write_bytes(canonical_bytes({
            "detectors_sha256": digest((root / self.runner.DETECTOR_REL).read_bytes()),
            "thresholds": {"D1": {"Synthetic category": "0.001"}}}))
        (root / ".gitignore").write_text("/raw/\n")
        subprocess.run(["git", "init", "-q", str(root)], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(root), "add", "."], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(root), "-c", "user.name=Synthetic Test", "-c",
                        "user.email=synthetic@example.invalid", "commit", "-qm", "Synthetic registration"],
                       check=True, capture_output=True)

    def test_uncommitted_runtime_rejected_before_any_fund_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.synthetic_repo(root)
            (root / self.runner.RUNTIME_FILES[0]).write_text("changed runtime")
            with patch.object(self.runner, "read_fund_json", side_effect=AssertionError("fund source touched")):
                with self.assertRaises(ValueError):
                    self.runner.run_research(repo_root=root)

    def test_subset_unopened_and_noncanonical_output_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.synthetic_repo(root)
            with patch.object(self.runner, "read_fund_json", side_effect=AssertionError("fund source touched")):
                for codes in (["AAA"], CODES[:-1]):
                    with self.assertRaises(ValueError):
                        self.runner.run_research(repo_root=root, codes=codes)
                with self.assertRaises(ValueError):
                    self.runner.run_research(repo_root=root, out_dir=root / "public")

    def test_committed_missing_data_run_retains_100_records(self):
        try:
            import numpy  # noqa: F401
        except ImportError:
            self.skipTest("bundle runner requires optional numpy analysis dependency")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.synthetic_repo(root)
            output = self.runner.run_research(repo_root=root, snapshot_db=root / "missing.sqlite3")
            self.assertEqual(output["bundle"]["summary"]["unavailable"], 100)
            self.assertEqual(len(output["bundle"]["funds"]), 100)
            self.assertEqual(load_bundle(Path(output["directory"]))["immutable_bundle_id"],
                             output["bundle"]["immutable_bundle_id"])


class D1ReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.detector = load_frozen_detector(REPO)
        except ImportError:
            raise unittest.SkipTest("frozen D1 equivalence requires the optional numpy analysis dependency")

    def inputs(self, length: int = 61):
        days = []
        current = date(2026, 9, 16)
        while len(days) < length:
            if current.weekday() < 5:
                days.append(current.isoformat())
            current -= timedelta(days=1)
        days.reverse()
        prices = {code: {"rows": [[day, str(math.exp(index * (0.002 if code == "Z00" else 0.001)))]
                                   for index, day in enumerate(days)]} for code in CODES}
        identities = {code: {"category": "Synthetic category"} for code in CODES}
        return days, prices, identities

    def evaluate(self, prices, identities, threshold="0.0001"):
        return d1_context(CODES, prices, identities, {"Synthetic category": threshold}, {}, self.detector)

    def test_frozen_equivalence_and_strict_equality(self):
        import numpy as np
        days, prices, identities = self.inputs()
        result, _ = self.evaluate(prices, identities)["Z00"]
        own = np.array([float(row[1]) for row in prices["Z00"]["rows"]])
        peer = np.array([float(row[1]) for row in prices["Z01"]["rows"]])
        expected = self.detector.excess_level(self.detector.log_returns(own) - self.detector.log_returns(peer))[-1]
        self.assertEqual(float(result["statistic"]), expected)
        equal, _ = self.evaluate(prices, identities, str(expected))["Z00"]
        self.assertEqual(equal["research_screen"], "NO_CROSSING")
        self.assertEqual(result["usable_observations"], 60)

    def test_50_and_49_usable_observation_boundary(self):
        for usable in (50, 49):
            _, prices, identities = self.inputs(usable + 1)
            result, _ = self.evaluate(prices, identities)["Z00"]
            self.assertEqual(result["usable_observations"], usable)
            self.assertEqual(result["arithmetic_status"], "AVAILABLE" if usable == 50 else "UNAVAILABLE")

    def test_10_and_9_peer_boundary(self):
        for count in (10, 9):
            _, prices, identities = self.inputs()
            for code in CODES[count + 1:]:
                identities[code]["category"] = "other"
            result, _ = self.evaluate(prices, identities)["Z00"]
            self.assertEqual(result["arithmetic_status"], "AVAILABLE" if count == 10 else "UNAVAILABLE")
            if count == 10:
                self.assertEqual(result["eligible_peers"], 10)

    def test_missing_calibration_and_category_remain_unknown(self):
        _, prices, identities = self.inputs()
        result, _ = self.evaluate(prices, identities, None)["Z00"]
        self.assertEqual(result["research_screen"], "UNKNOWN")
        identities["Z00"]["category"] = None
        result, _ = self.evaluate(prices, identities)["Z00"]
        self.assertIn("current_category_missing", result["missing_reasons"])

    def test_finite_but_stale_statistic_retained(self):
        _, prices, identities = self.inputs()
        prices["Z00"]["rows"][-1][1] = None
        result, chart = self.evaluate(prices, identities)["Z00"]
        self.assertEqual(result["arithmetic_status"], "AVAILABLE")
        self.assertEqual(result["freshness"], "STALE")
        self.assertIsNotNone(result["statistic"])
        self.assertEqual(result["latest_contributing_at"], "2026-09-15")
        self.assertIsNone(chart["points"][-1]["fund"])

    def test_common_baseline_100_and_gap_preservation(self):
        _, prices, identities = self.inputs()
        prices["Z00"]["rows"][10][1] = None
        _, chart = self.evaluate(prices, identities)["Z00"]
        self.assertEqual(chart["status"], "AVAILABLE")
        self.assertEqual(Decimal(chart["points"][0]["fund"]), Decimal(100))
        self.assertEqual(Decimal(chart["points"][0]["peers"]), Decimal(100))
        gaps = [point for point in chart["points"] if point["fund"] is None]
        self.assertEqual(len(gaps), 2)

    def test_future_prices_reports_outcomes_do_not_change_joined_findings(self):
        _, prices, identities = self.inputs()
        reports = {"Z00": payload()}
        kwargs = {"identities": identities, "thresholds": {"Synthetic category": "0.0001"},
                  "price_refs": {}, "kap_refs": {}, "sources": [], "manifest": [],
                  "detector": self.detector, "registration": {}}
        first = assemble(CODES, price_payloads=prices, report_payloads=reports, **kwargs)
        changed = copy.deepcopy(prices)
        for code in CODES:
            changed[code]["rows"].append(["2026-09-17", "999999999"])
            changed[code]["liquidated_after_cutoff"] = True
        report_changed = copy.deepcopy(reports)
        for item in report_changed["Z00"]["reports"]:
            item["liquidated_after_cutoff"] = True
            item["units"] = {"liquidated_after_cutoff": True}
        report_changed["Z00"]["reports"].extend([report("2026-09", "9999999"),
                                                  report("2026-08", "9999999", published_at="2026-09-17T00:00:00+03:00")])
        second = assemble(CODES, price_payloads=changed, report_payloads=report_changed, **kwargs)
        self.assertEqual(first, second)
        self.assertEqual(len(first["funds"]), 100)

    def test_chart_overflow_becomes_gap(self):
        from p50k.research_reviews.bundle import _chart
        import numpy as np
        calendar = ["2026-09-15", "2026-09-16"]
        prices = np.array([[1e-300, 1e300] for _ in range(11)])
        returns = np.array([[0.001, 0.001] for _ in range(11)])
        chart = _chart(calendar, prices, returns, 0, list(range(1, 11)), np.array([10, 10]))
        self.assertEqual(chart["points"][0]["fund"], "100.0")
        self.assertEqual(chart["points"][-1], {"date": "2026-09-16", "fund": None, "peers": None})


if __name__ == "__main__":
    unittest.main()
