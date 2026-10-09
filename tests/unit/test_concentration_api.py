"""Synthetic concentration API, attribution, and wire-contract checks."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import datetime
from decimal import Inexact, Rounded, localcontext
from pathlib import Path
import tempfile
import unittest

from p50k.research_reviews.bundle import SourceRegistry
from p50k.research_reviews.bundle_v2 import extend_bundle, write_research_bundle
from p50k.research_reviews.concentration import concentration_finding, empty_concentration
from tests.unit.test_research_api import API_AVAILABLE, authored_bundle
from tests.unit.test_security_holdings import read

if API_AVAILABLE:
    from fastapi.testclient import TestClient
    from p50k.api.app import create_app
    from p50k.api.models import Concentration, validate_public_bundle


def authored_concentration_bundle(directory: Path):
    (directory / "base-input").mkdir()
    base, base_dir, original_pdf, pdf_id = authored_bundle(directory / "base-input")
    registry = SourceRegistry()
    base_source = registry.add(base_dir / "bundle.json", "CODE")
    previous_pdf = directory / "synthetic-previous.pdf"
    previous_pdf.write_bytes(b"%PDF-1.4\n% authored synthetic previous holdings\n%%EOF\n")
    previous_id = registry.add(previous_pdf, "KAP_PDF", fund_code="S00", published_at="2026-08-01T12:00:00+03:00")
    concentrations = {row["code"]: empty_concentration(reasons=["authored_missing_holdings"]) for row in base["funds"]}
    current = replace(read(), published_at=datetime.fromisoformat("2026-09-01T12:00:00+03:00"))
    previous = replace(read(), report_period="2026-07", published_at=datetime.fromisoformat("2026-08-01T12:00:00+03:00"))
    concentrations["S00"] = concentration_finding(current, source_id=pdf_id, previous=previous, previous_source_id=previous_id)
    result = extend_bundle(base, concentrations, sources=list(registry.sources.values()), manifest=list(registry.manifest.values()),
                           registration={"base_bundle_source_id": base_source, "fixture": "authored synthetic concentration"})
    sealed = write_research_bundle(directory / "concentration-output", result)
    return base, base_dir, result, sealed, original_pdf, pdf_id, previous_id


@unittest.skipUnless(API_AVAILABLE, "Optional locked API dependencies missing")
class ConcentrationApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        (self.base, self.base_dir, self.payload, self.sealed, self.pdf,
         self.pdf_id, self.previous_id) = authored_concentration_bundle(self.directory)
        self.codes = frozenset(record["code"] for record in self.base["funds"])
        self.app = create_app(self.sealed, universe_codes=self.codes)
        self.client = TestClient(self.app, base_url="http://127.0.0.1:8767")
        self.addCleanup(self.client.close)

    def changed(self):
        return deepcopy(self.payload)

    def target(self, payload):
        return next(row for row in payload["funds"] if row["code"] == "S00")["concentration"]

    def test_all_100_list_detail_records_equal_and_existing_groups_stay_fixed(self):
        response = self.client.get("/research/v1/funds")
        self.assertEqual(response.status_code, 200, response.text[:300])
        self.assertEqual(response.headers["cache-control"], "no-store")
        records = response.json()["funds"]
        self.assertEqual(len(records), 100)
        for record in records:
            detail = self.client.get("/research/v1/funds/" + record["code"])
            self.assertEqual(detail.status_code, 200)
            self.assertEqual(detail.json()["fund"], record)
        summary = self.client.get("/research/v1/summary").json()["summary"]
        for field, value in self.base["summary"].items():
            self.assertEqual(summary[field], value)
        self.assertEqual(summary["concentration_available"], 1)
        self.assertEqual(summary["concentration_partial"], 0)
        self.assertEqual(summary["concentration_unavailable"], 99)

    def test_detail_exact_source_union_retains_selected_current_and_previous_pdfs(self):
        detail = self.client.get("/research/v1/funds/S00").json()
        fund = detail["fund"]
        expected = set(fund["evidence"] + fund["d1"]["input_refs"] + fund["flow"]["input_refs"] + fund["concentration"]["input_refs"])
        expected.update(reference["source_id"] for reference in fund["flow"]["endpoint_refs"])
        self.assertEqual({source["source_id"] for source in detail["sources"]}, expected)
        self.assertIn(self.pdf_id, expected)
        self.assertIn(self.previous_id, expected)
        self.assertEqual(fund["concentration"]["current_source_id"], self.pdf_id)
        self.assertEqual(fund["concentration"]["comparison"]["status"], "UNAVAILABLE")

    def test_old_bundle_is_explicitly_uncalculated_with_nullable_counts(self):
        app = create_app(self.base_dir, universe_codes=self.codes)
        with TestClient(app, base_url="http://127.0.0.1") as client:
            response = client.get("/research/v1/funds/S00")
            self.assertEqual(response.status_code, 200)
            self.assertIsNone(response.json()["fund"]["concentration"])
            summary = client.get("/research/v1/summary").json()["summary"]
            self.assertIsNone(summary["concentration_available"])

    def test_current_and_previous_pdf_bytes_remain_verified_and_private(self):
        for identifier in (self.pdf_id, self.previous_id):
            response = self.client.get("/research/v1/sources/" + identifier)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.content.startswith(b"%PDF-"))
            self.assertEqual(response.headers["cache-control"], "no-store")
            self.assertEqual(response.headers["x-research-bundle-id"], self.payload["immutable_bundle_id"])

    def test_changed_private_source_copy_rejects_all_following_responses(self):
        (self.sealed / "sources" / (self.previous_id + ".pdf")).write_bytes(b"%PDF-1.4\nchanged synthetic bytes\n")
        response = self.client.get("/research/v1/funds")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"]["code"], "BUNDLE_INVALID")

    def test_nonfinite_numeric_and_bool_metrics_rejected(self):
        for value in (0.82, True, "NaN", "Infinity", "bad"):
            payload = self.changed()
            self.target(payload)["hhi"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_public_bundle(payload)

    def test_partial_and_printed_rounding_contracts_are_valid_without_promoting_findings(self):
        from tests.unit.test_fund_concentration import printed, row
        snapshot = replace(read(), published_at=datetime.fromisoformat("2026-09-01T12:00:00+03:00"))
        partial = replace(snapshot, rows=(*snapshot.rows[:-1], replace(snapshot.rows[-1], isin=None)))
        partial_model = Concentration.model_validate(concentration_finding(partial, source_id=self.pdf_id))
        self.assertEqual(partial_model.status, "PARTIAL")
        rounded = replace(snapshot, rows=(replace(snapshot.rows[0], position_value=printed("60.0050")), *snapshot.rows[1:]))
        rounded_model = Concentration.model_validate(concentration_finding(rounded, source_id=self.pdf_id))
        self.assertEqual(rounded_model.portfolio_coverage_ratio, "1.00005")
        self.assertEqual(rounded_model.model_dump(mode="json")["schema"], "p50k.holding-concentration.v1")
        truncated = replace(snapshot, rows=tuple(row(index, "10.00") for index in range(12)), portfolio_total=printed("120.00"))
        metrics = concentration_finding(truncated, source_id=self.pdf_id)
        Concentration.model_validate(metrics)
        metrics["hhi"] = "0.9"
        with self.assertRaises(ValueError):
            Concentration.model_validate(metrics)

    def test_top_n_hhi_and_subset_denominator_are_reproduced(self):
        for field, value in (("hhi", "0.9"), ("top1_ratio", "0.8"), ("top5_ratio", "0.95"),
                             ("portfolio_coverage_ratio", "0.99"), ("subset_value", "95")):
            payload = self.changed()
            self.target(payload)[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_public_bundle(payload)

    def test_negative_position_values_fake_source_lots_and_duplicate_isins_rejected(self):
        for mutation in (lambda c: c["positions"][0].update(value="-90"),
                         lambda c: c["positions"][0]["source_rows"][0].update(reported_value="59"),
                         lambda c: c["positions"][1].update(isin=c["positions"][0]["isin"]),
                         lambda c: c["positions"][0].update(weight="0.8")):
            payload = self.changed()
            mutation(self.target(payload))
            with self.assertRaises(ValueError):
                validate_public_bundle(payload)

    def test_partial_and_unavailable_cannot_masquerade_as_complete_or_safe(self):
        for status in ("SAFE", "CROSSING", "UNAVAILABLE", "PARTIAL"):
            payload = self.changed()
            self.target(payload)["status"] = status
            with self.subTest(status=status), self.assertRaises(ValueError):
                validate_public_bundle(payload)
        payload = self.changed()
        self.target(payload)["research_screen"] = "CROSSING"
        with self.assertRaises(ValueError):
            validate_public_bundle(payload)

    def test_future_publication_monthend_wrong_age_and_monthly_cadence_rejected(self):
        mutations = [("published_at", "2026-09-17T00:00:00+03:00"), ("report_period", "2026-09"),
                     ("effective_date", "2026-08-30"), ("age_days", 0), ("cadence", "WEEKLY")]
        for field, value in mutations:
            payload = self.changed()
            self.target(payload)[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_public_bundle(payload)

    def test_exact_current_pdf_identity_and_foreign_fund_sources_rejected(self):
        payload = self.changed()
        self.target(payload)["current_source_id"] = self.previous_id
        with self.assertRaises(ValueError):
            validate_public_bundle(payload)
        payload = self.changed()
        next(source for source in payload["sources"] if source["source_id"] == self.pdf_id)["fund_code"] = "S01"
        with self.assertRaises(ValueError):
            validate_public_bundle(payload)

    def test_wrong_pdf_publication_or_arbitrary_source_reference_rejected(self):
        for publication in (None, "2026-09-02T12:00:00+03:00", "2026-09-17T12:00:00+03:00"):
            payload = self.changed()
            next(source for source in payload["sources"] if source["source_id"] == self.pdf_id)["published_at"] = publication
            with self.assertRaises(ValueError):
                validate_public_bundle(payload)
        payload = self.changed()
        self.target(payload)["input_refs"].append("f" * 64)
        with self.assertRaises(ValueError):
            validate_public_bundle(payload)

    def test_invalid_rectangle_or_zero_page_rejected(self):
        for field, value in (("bbox", [0.0, 0.0, 951.0, 1200.0]), ("bbox", [0.0, float("nan"), 817.0, 7.0]), ("page", 0)):
            payload = self.changed()
            self.target(payload)["positions"][0]["source_rows"][0][field] = value
            with self.assertRaises(ValueError):
                validate_public_bundle(payload)

    def test_missing_one_record_or_disagreeing_summary_is_rejected(self):
        payload = self.changed()
        payload["funds"][99].pop("concentration")
        with self.assertRaises(ValueError):
            validate_public_bundle(payload)
        payload = self.changed()
        payload["summary"].update(concentration_available=2, concentration_unavailable=98)
        with self.assertRaises(ValueError):
            validate_public_bundle(payload)

    def test_caller_decimal_flags_and_precision_survive_full_validation(self):
        with localcontext() as caller:
            caller.prec = 2
            caller.traps[Inexact] = caller.traps[Rounded] = True
            caller.flags[Inexact] = True
            flags = caller.flags.copy()
            validate_public_bundle(self.payload)
            self.assertEqual(caller.flags, flags)
            self.assertEqual(caller.prec, 2)


if __name__ == "__main__":
    unittest.main()
