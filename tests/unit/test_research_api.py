"""Optional FastAPI contract tests using authored synthetic data only."""
from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

try:
    import httpx2  # noqa: F401 - Starlette's current optional TestClient dependency
    from fastapi.testclient import TestClient
    from pydantic import ValidationError
    from p50k.api.app import create_app
    from p50k.api.models import validate_public_bundle
except ImportError:
    API_AVAILABLE = False
else:
    API_AVAILABLE = True

from p50k.research_reviews.bundle import SourceRegistry, canonical_bytes, digest, write_bundle
from p50k.research_reviews.comments import describe, finding_order, summarize
from p50k.research_reviews.contracts import METADATA, SCHEMA, empty_finding


def authored_bundle(base: Path) -> tuple[dict, Path, Path, str]:
    """Seal one synthetic PDF and invented metrics; no private archive is read."""
    pdf = base / "synthetic-report.pdf"
    pdf.write_bytes(b"%PDF-1.4\n% authored synthetic contract fixture\n%%EOF\n")
    series = base / "synthetic-series.json"
    series.write_text('{"origin":"SYNTHETIC","reports":[]}\n')
    registry = SourceRegistry()
    pdf_id = registry.add(pdf, "KAP_PDF", fund_code="S00", published_at="2026-09-01T12:00:00+03:00")
    series_id = registry.add(series, "KAP_SERIES", fund_code="S00")
    records = []
    for index in range(100):
        d1, flow = empty_finding("d1"), empty_finding("flow")
        d1["missing_reasons"] = ["authored_missing_input"]
        flow["missing_reasons"] = ["authored_missing_input"]
        if index < 4:
            d1.update(arithmetic_status="AVAILABLE", research_screen="CROSSING" if index in (0, 2) else "NO_CROSSING",
                      freshness="STALE" if index == 2 else "FRESH", missing_reasons=[],
                      metric_period={"start": "2026-07-01", "end": "2026-09-16"},
                      statistic="0.02" if index in (0, 2) else "0.01", threshold="0.01",
                      usable_observations=60, window_positions=60, eligible_peers=10,
                      latest_contributing_at="2026-09-15" if index == 2 else "2026-09-16",
                      input_refs=[series_id])
        if index in (0, 1, 3):
            rate, assets, residual = ("0.10", "1100", "100") if index == 0 else (
                ("-0.10", "900", "-100") if index == 1 else ("0", "1000", "0"))
            flow.update(arithmetic_status="AVAILABLE", research_screen="NO_CROSSING" if index == 3 else "CROSSING",
                        freshness="FRESH", missing_reasons=[], statistic=rate, previous_assets="1000",
                        current_assets=assets, previous_nav="10", current_nav="10", residual=residual,
                        direction="INFLOW_ESTIMATE" if index == 0 else "OUTFLOW_ESTIMATE" if index == 1 else "NONE",
                        input_refs=[series_id], endpoint_refs=[
                            {"period": period, "source_id": series_id, "record_sha256": hashlib.sha256(period.encode()).hexdigest(),
                             "record_hash_basis": "CONSUMED_ENDPOINT_FIELDS",
                             "published_at": published, "published_at_raw": published, "historical_availability": "UNKNOWN"}
                            for period, published in (("2026-07", "2026-08-01T12:00:00+03:00"),
                                                      ("2026-08", "2026-09-01T12:00:00+03:00"))])
        comment, assessment, crossings = describe(d1, flow)
        records.append({"code": f"S{index:02}", "name": f"Authored synthetic fund {index}",
                        "category": "Authored synthetic category", "comment_tr": comment,
                        "assessment": assessment, "eligible_crossings": crossings, "d1": d1, "flow": flow,
                        "chart": {"status": "UNAVAILABLE", "reason": "authored_missing_chart",
                                  "baseline_date": None, "unit": "INDEX_100", "points": [], "peer_count": 0},
                        "evidence": [pdf_id, series_id] if index == 0 else []})
    records.sort(key=finding_order)
    summary = summarize(records)
    summary.update(d1_assessable=3, flow_assessable=3, d1_stale=1)
    payload = {"schema": SCHEMA, **METADATA, "summary": summary, "funds": records,
               "sources": list(registry.sources.values()), "manifest": list(registry.manifest.values()),
               "registration": {"fixture": "authored synthetic data only"}}
    payload["immutable_bundle_id"] = digest(canonical_bytes(payload))
    directory = write_bundle(base / "sealed", payload)
    return payload, directory, pdf, pdf_id


@unittest.skipUnless(API_AVAILABLE, "Optional API dependencies missing; run locked .venv API suite")
class ResearchApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.payload, self.directory, self.original_pdf, self.pdf_id = authored_bundle(self.base)
        self.codes = frozenset(f"S{index:02}" for index in range(100))
        self.app = create_app(self.directory, universe_codes=self.codes)
        self.client = TestClient(self.app, base_url="http://127.0.0.1:8767")
        self.addCleanup(self.client.close)

    def assert_private(self, response, *, code=200):
        self.assertEqual(response.status_code, code, response.text[:500])
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(response.headers["pragma"], "no-cache")
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")

    def assert_metadata(self, payload, *, fingerprint=True):
        for key, value in METADATA.items():
            self.assertEqual(payload[key], value)
        self.assertEqual(payload["immutable_bundle_id"], self.payload["immutable_bundle_id"] if fingerprint else None)

    def test_health_is_bound_to_sealed_bundle(self):
        response = self.client.get("/research/v1/health")
        self.assert_private(response)
        self.assert_metadata(response.json())
        self.assertEqual(response.json()["health"], {"status": "OK", "record_count": 100})

    def test_summary_four_groups_do_not_call_missing_negative(self):
        response = self.client.get("/research/v1/summary")
        self.assert_private(response)
        self.assert_metadata(response.json())
        summary = response.json()["summary"]
        self.assertEqual(summary["two_findings"], 1)
        self.assertEqual(summary["one_finding"], 1)
        self.assertEqual(summary["no_findings"], 1)
        self.assertEqual(summary["unassessable_no_findings"], 97)
        self.assertEqual(summary["denominator"], 100)

    def test_all_100_list_and_detail_records_match(self):
        response = self.client.get("/research/v1/funds")
        self.assert_private(response)
        self.assert_metadata(response.json())
        records = response.json()["funds"]
        self.assertEqual(len(records), 100)
        for record in records:
            detail = self.client.get("/research/v1/funds/" + record["code"])
            self.assert_private(detail)
            self.assert_metadata(detail.json())
            self.assertEqual(detail.json()["fund"], record)
        self.assertEqual(records[0]["flow"]["statistic"], "0.10")
        self.assertIsNone(next(record for record in records if record["code"] == "S99")["flow"]["statistic"])

    def test_detail_includes_only_referenced_public_sources(self):
        response = self.client.get("/research/v1/funds/S00")
        sources = response.json()["sources"]
        self.assertEqual(len(sources), 2)
        self.assertTrue(all("original_path" not in source and "copy_path" not in source for source in sources))
        self.assertEqual(self.client.get("/research/v1/funds/S99").json()["sources"], [])

    def test_unopened_code_rejected_before_bundle_source_reads(self):
        with patch.object(self.app.state, "bundle_view", side_effect=AssertionError("Financial source read")):
            response = self.client.get("/research/v1/funds/ZZZ")
        self.assert_private(response, code=404)
        self.assertEqual(response.json()["error"]["code"], "NOT_FOUND")

    def test_unopened_bundle_code_rejected_before_original_source_hashes(self):
        changed = deepcopy(self.payload)
        next(fund for fund in changed["funds"] if fund["code"] == "S99")["code"] = "ZZZ"
        changed.pop("immutable_bundle_id")
        changed["immutable_bundle_id"] = digest(canonical_bytes(changed))
        directory = write_bundle(self.base / "malicious-sealed", changed)
        app = create_app(directory, universe_codes=self.codes)
        with patch("p50k.research_reviews.bundle._source_bytes", side_effect=AssertionError("Original source read")):
            with TestClient(app, base_url="http://127.0.0.1") as client:
                response = client.get("/research/v1/health")
        self.assert_private(response, code=503)
        self.assertEqual(response.json()["error"]["code"], "BUNDLE_INVALID")

    def test_pdf_response_bytes_and_provenance_match_manifest(self):
        response = self.client.get("/research/v1/sources/" + self.pdf_id)
        self.assert_private(response)
        self.assertEqual(response.content, self.original_pdf.read_bytes())
        self.assertEqual(response.headers["content-type"], "application/pdf")
        self.assertEqual(response.headers["x-research-bundle-id"], self.payload["immutable_bundle_id"])
        self.assertEqual(response.headers["x-research-cutoff-at"], METADATA["cutoff_at"])

    def test_unknown_source_stays_missing(self):
        response = self.client.get("/research/v1/sources/" + "a" * 64)
        self.assert_private(response, code=404)
        self.assert_metadata(response.json())

    def test_non_pdf_source_stays_missing(self):
        identifier = next(source["source_id"] for source in self.payload["sources"] if source["kind"] != "KAP_PDF")
        response = self.client.get("/research/v1/sources/" + identifier)
        self.assert_private(response, code=404)

    def test_path_and_url_traversal_never_resolve(self):
        for path in ("..%2F..%2Fetc%2Fpasswd", "https%3A%2F%2Fexample.com", "%2Fetc%2Fpasswd", "not-a-hash"):
            with self.subTest(path=path), patch.object(self.app.state, "bundle_view", side_effect=AssertionError("Source read")):
                response = self.client.get("/research/v1/sources/" + path)
                self.assert_private(response, code=404)

    def test_missing_bundle_is_not_a_synthetic_success(self):
        app = create_app(self.base / "missing", universe_codes=self.codes)
        with TestClient(app, base_url="http://127.0.0.1") as client:
            response = client.get("/research/v1/health")
        self.assert_private(response, code=503)
        self.assert_metadata(response.json(), fingerprint=False)

    def test_no_configured_bundle_is_explicit_unavailable(self):
        with patch.dict("os.environ", {}, clear=True):
            app = create_app(universe_codes=self.codes)
        with TestClient(app, base_url="http://127.0.0.1") as client:
            response = client.get("/research/v1/health")
        self.assert_private(response, code=503)
        self.assertEqual(response.json()["error"]["code"], "BUNDLE_UNAVAILABLE")
        self.assert_metadata(response.json(), fingerprint=False)

    def test_corrupt_bundle_fingerprint_rejected(self):
        path = self.directory / "bundle.json"
        path.write_bytes(path.read_bytes().replace(b"Authored synthetic fund 0", b"Changed synthetic fund 0"))
        response = self.client.get("/research/v1/funds")
        self.assert_private(response, code=503)
        self.assert_metadata(response.json(), fingerprint=False)

    def test_missing_fingerprint_rejected(self):
        payload = deepcopy(self.payload)
        payload.pop("immutable_bundle_id")
        (self.directory / "bundle.json").write_bytes(canonical_bytes(payload))
        self.assert_private(self.client.get("/research/v1/summary"), code=503)

    def test_changed_original_pdf_rejected_on_next_request(self):
        self.assert_private(self.client.get("/research/v1/health"))
        self.original_pdf.write_bytes(b"%PDF-1.4\nchanged authored source\n%%EOF")
        response = self.client.get("/research/v1/health")
        self.assert_private(response, code=503)
        self.assert_metadata(response.json(), fingerprint=False)

    def test_changed_private_pdf_copy_rejected(self):
        copy = self.directory / "sources" / (self.pdf_id + ".pdf")
        copy.write_bytes(b"%PDF-1.4\nchanged authored copy\n%%EOF")
        self.assert_private(self.client.get("/research/v1/sources/" + self.pdf_id), code=503)

    def test_pdf_exact_response_bytes_rechecked_after_resolve(self):
        changed = self.base / "changed.pdf"
        changed.write_bytes(b"%PDF-1.4\nchanged fixture after manifest validation\n%%EOF")
        with patch.object(self.app.state, "pdf_resolver", return_value=changed):
            response = self.client.get("/research/v1/sources/" + self.pdf_id)
        self.assert_private(response, code=503)

    def test_api_has_no_write_endpoints(self):
        response = self.client.post("/research/v1/funds", json={"anything": "authored"})
        self.assert_private(response, code=405)
        self.assert_metadata(response.json(), fingerprint=False)

    def test_cors_allows_only_configured_loopback_ui(self):
        allowed = self.client.get("/research/v1/health", headers={"Origin": "http://127.0.0.1:3060"})
        self.assert_private(allowed)
        self.assertEqual(allowed.headers["access-control-allow-origin"], "http://127.0.0.1:3060")
        denied = self.client.get("/research/v1/health", headers={"Origin": "https://example.com"})
        self.assert_private(denied)
        self.assertNotIn("access-control-allow-origin", denied.headers)

    def test_cors_preflight_and_errors_are_no_store(self):
        for origin, code in (("http://127.0.0.1:3060", 200), ("https://example.com", 400)):
            response = self.client.options("/research/v1/funds", headers={"Origin": origin, "Access-Control-Request-Method": "GET"})
            self.assert_private(response, code=code)
            if code == 400:
                self.assert_metadata(response.json(), fingerprint=False)

    def test_non_loopback_configuration_and_host_rejected(self):
        for origin in ("http://0.0.0.0:3060", "https://example.com", "http://localhost:3060/path"):
            with self.assertRaises(ValueError):
                create_app(self.directory, frontend_origin=origin, universe_codes=self.codes)
        response = self.client.get("/research/v1/health", headers={"Host": "example.com"})
        self.assert_private(response, code=400)

    def test_full_response_validation_rejects_financial_numbers_and_nonfinite(self):
        for value in (0.1, True, "NaN", "Infinity", "not-a-number"):
            changed = deepcopy(self.payload)
            changed["funds"][0]["flow"]["statistic"] = value
            with self.subTest(value=value), self.assertRaises((ValidationError, ValueError)):
                validate_public_bundle(changed)

    def test_full_response_validation_rejects_status_unit_and_false_substitutes(self):
        edits = [("production_status", "TRIGGERED"), ("research_screen", "SAFE"), ("freshness", "NORMAL")]
        for field, value in edits:
            changed = deepcopy(self.payload)
            changed["funds"][0]["flow"][field] = value
            with self.assertRaises(ValidationError):
                validate_public_bundle(changed)
        changed = deepcopy(self.payload)
        changed["funds"][0]["flow"]["units"]["statistic"] = "TRY"
        with self.assertRaises(ValidationError):
            validate_public_bundle(changed)
        changed = deepcopy(self.payload)
        changed["point_in_time_verified"] = 0
        with self.assertRaises(ValidationError):
            validate_public_bundle(changed)

    def test_validation_rejects_count_assessment_screen_and_direction_claims(self):
        edits = [("eligible_crossings", 0), ("eligible_crossings", True), ("assessment", "UNAVAILABLE")]
        for field, value in edits:
            changed = deepcopy(self.payload)
            changed["funds"][0][field] = value
            with self.assertRaises(ValidationError):
                validate_public_bundle(changed)
        for field, value in (("research_screen", "NO_CROSSING"), ("direction", "OUTFLOW_ESTIMATE"), ("residual", "99")):
            changed = deepcopy(self.payload)
            changed["funds"][0]["flow"][field] = value
            with self.assertRaises(ValidationError):
                validate_public_bundle(changed)

    def test_d1_threshold_equality_is_not_a_crossing(self):
        changed = deepcopy(self.payload)
        changed["funds"][0]["d1"]["statistic"] = "0.01"
        with self.assertRaises(ValidationError):
            validate_public_bundle(changed)

    def test_validation_rejects_future_or_missing_endpoint_time_and_bad_freshness(self):
        for time in (None, "2026-09-17T00:00:00+03:00", "2026-09-01 12:00:00", "bad"):
            changed = deepcopy(self.payload)
            changed["funds"][0]["flow"]["endpoint_refs"][0]["published_at"] = time
            with self.assertRaises(ValidationError):
                validate_public_bundle(changed)
        changed = deepcopy(self.payload)
        changed["funds"][0]["d1"]["latest_contributing_at"] = "2026-09-15"
        with self.assertRaises(ValidationError):
            validate_public_bundle(changed)

    def test_validation_rejects_arbitrary_disclosure_url_and_unreferenced_ids(self):
        changed = deepcopy(self.payload)
        changed["sources"][0]["disclosure_url"] = "http://127.0.0.1/private"
        with self.assertRaises(ValidationError):
            validate_public_bundle(changed)
        changed = deepcopy(self.payload)
        changed["funds"][0]["evidence"].append("f" * 64)
        with self.assertRaises(ValueError):
            validate_public_bundle(changed)

    def test_validation_rejects_inconsistent_summary_and_universe(self):
        changed = deepcopy(self.payload)
        changed["summary"]["fully_assessable"] += 1
        with self.assertRaises(ValidationError):
            validate_public_bundle(changed)
        changed = deepcopy(self.payload)
        changed["summary"]["total"] = 100.0
        with self.assertRaises(ValidationError):
            validate_public_bundle(changed)
        changed = deepcopy(self.payload)
        changed["funds"] = changed["funds"][:-1]
        with self.assertRaises(ValueError):
            validate_public_bundle(changed)

    def test_schema_invalid_resealed_response_is_still_rejected_by_api(self):
        changed = deepcopy(self.payload)
        changed["funds"][0]["flow"]["units"]["statistic"] = "TRY"
        changed.pop("immutable_bundle_id")
        changed["immutable_bundle_id"] = digest(canonical_bytes(changed))
        # A maliciously re-fingerprinted dictionary must fail strict public
        # validation independently of byte-integrity validation.
        with patch("p50k.research_reviews.bundle.load_bundle", return_value=changed):
            app = create_app(self.directory, universe_codes=self.codes)
            with TestClient(app, base_url="http://127.0.0.1") as client:
                response = client.get("/research/v1/funds")
        self.assert_private(response, code=503)

    def test_strict_contract_accepts_synthetic_frozen_builder_output(self):
        from tests.unit.test_fund_review_bundle import CODES, D1ReviewTests, REPO, all_missing_bundle, payload
        from p50k.research_reviews.bundle import assemble, load_frozen_detector
        validate_public_bundle(all_missing_bundle())
        _, prices, identities = D1ReviewTests().inputs()
        sources = deepcopy(self.payload["sources"])
        for source in sources:
            source["fund_code"] = None
        series_id = next(source["source_id"] for source in sources if source["kind"] == "KAP_SERIES")
        built = assemble(CODES, price_payloads=prices, report_payloads={"Z00": payload()},
                         identities=identities, thresholds={"Synthetic category": "0.0001"},
                         price_refs={code: [series_id] for code in CODES}, kap_refs={"Z00": series_id},
                         sources=sources, manifest=self.payload["manifest"], detector=load_frozen_detector(REPO),
                         registration={"fixture": "authored synthetic contract integration"})
        _, summary, funds, _ = validate_public_bundle(built)
        self.assertEqual(summary.total, 100)
        self.assertEqual(next(fund for fund in funds if fund.code == "Z00").eligible_crossings, 2)


if __name__ == "__main__":
    unittest.main()
