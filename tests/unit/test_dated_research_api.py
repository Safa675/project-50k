"""Optional FastAPI contract tests for the separate dated D1 API (synthetic data only).

Codes Z00..Z99 and every value are invented. Skips without the locked API extras,
as test_research_api.py does.
"""
from __future__ import annotations

import copy
from datetime import date, timedelta
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

try:
    import httpx2  # noqa: F401 - Starlette's current optional TestClient dependency
    from fastapi.testclient import TestClient
    from pydantic import ValidationError
    from p50k.api import dated_app as dated_app_module
    from p50k.api.app import create_app
    from p50k.api.dated_app import MESSAGES_TR, create_dated_app
    from p50k.api.dated_models import (
        DatedErrorResponse, DatedFundsResponse, DatedSummaryResponse, DatesResponse, validate_dated_view,
    )
except ImportError:
    API_AVAILABLE = False
else:
    API_AVAILABLE = True

from p50k.research_reviews.bundle import canonical_bytes, digest
from p50k.research_reviews.contracts import CUTOFF_AT, METADATA
from p50k.research_reviews.dated_bundle import make_date_index, write_date_index, write_dated_bundle
from p50k.research_reviews.dated_comments import dated_order, describe_dated, summarize_dated
from p50k.research_reviews.dated_contracts import (
    date_or_month_mentions, denylist_hits, d1_state, metadata_for,
)
from tests.unit.test_fund_review_dated import EXPECTED_GRID
from tests.unit.test_fund_review_dated_bundle import CODES, OUTPUT, Workspace

PREFIX = "/research-dated/v1"
DATED_LABELS = {key: value for key, value in metadata_for("2026-09-16").items() if key not in ("cutoff_at", "cutoff_date")}


def rich_payload(space: Workspace, cutoff: str, registration: dict | None = None) -> dict:
    """space.manual plus a fresh crossing (with chart), a fresh no-crossing and a stale record."""
    payload = space.manual(cutoff, registration)
    payload.pop("immutable_bundle_id")
    start = (date.fromisoformat(cutoff) - timedelta(days=85)).isoformat()
    prior = (date.fromisoformat(cutoff) - timedelta(days=1)).isoformat()
    records = {record["code"]: record for record in payload["funds"]}
    for code, statistic, latest in (("Z00", "0.0009", cutoff), ("Z01", "0.0001", cutoff), ("Z02", "0.0007", prior)):
        record, d1 = records[code], records[code]["d1"]
        fresh = latest == cutoff
        d1.update(arithmetic_status="AVAILABLE", statistic=statistic,
                  research_screen="CROSSING" if Decimal(statistic) > Decimal(d1["threshold"]) else "NO_CROSSING",
                  freshness="FRESH" if fresh else "STALE",
                  missing_reasons=[] if fresh else ["final_contributing_observation_before_cutoff"],
                  metric_period={"start": start, "end": cutoff}, usable_observations=55, window_positions=60,
                  eligible_peers=12, latest_contributing_at=latest)
        record.update(d1_state=d1_state(d1), comment_tr=describe_dated(d1))
    records["Z00"]["chart"] = {"status": "AVAILABLE", "reason": None, "baseline_date": start, "unit": "INDEX_100",
                               "points": [{"date": start, "fund": "100.0", "peers": "100.0"},
                                          {"date": cutoff, "fund": "101.5", "peers": "100.25"}],
                               "peer_count": 12}
    payload["funds"].sort(key=dated_order)
    payload["summary"] = summarize_dated(payload["funds"])
    payload["immutable_bundle_id"] = digest(canonical_bytes(payload))
    return payload


def seal_index(space: Workspace, base: Path, registration: dict | None = None) -> tuple[dict, Path, list[dict]]:
    """Seal 12 synthetic bundles and their index with B1's writers under base."""
    registration = registration or space.registration
    payloads = [rich_payload(space, day, registration) for day in EXPECTED_GRID]
    for payload in payloads:
        write_dated_bundle(base / "bundles", payload, repo_root=space.root, allowed_codes=CODES)
    index = make_date_index(payloads, protocol_sha256=registration["protocol_sha256"],
                            protocol_commit=registration["protocol_commit"], calendar_digest="8" * 64,
                            v1_bundle_id="9" * 64)
    directory = write_date_index(base / "index", index, repo_root=space.root, allowed_codes=CODES)
    return index, directory, payloads


@unittest.skipUnless(API_AVAILABLE, "Optional API dependencies missing; run locked .venv API suite")
class DatedResearchApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.space = Workspace(cls.root)
        cls.index, cls.index_dir, payloads = seal_index(cls.space, cls.root / OUTPUT)
        cls.payloads = {payload["cutoff_date"]: payload for payload in payloads}
        cls.entries = {entry["date"]: entry for entry in cls.index["entries"]}

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.app = self.dated_app()
        self.client = TestClient(self.app, base_url="http://127.0.0.1:8768")
        self.addCleanup(self.client.close)

    def dated_app(self, index_dir=None, **kwargs):
        return create_dated_app(self.index_dir if index_dir is None else index_dir,
                                universe_codes=frozenset(CODES), repo_root=self.root, **kwargs)

    def assert_private(self, response, code=200):
        self.assertEqual(response.status_code, code, response.text[:500])
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(response.headers["pragma"], "no-cache")
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        self.assertNotIn("access-control-allow-origin", response.headers)
        return response.json()

    def assert_error(self, response, status, code, *, day=None, index_id=None):
        body = self.assert_private(response, status)
        self.assertEqual(body["error"]["code"], code)
        self.assertEqual(body["error"]["message_tr"], MESSAGES_TR[code])
        for key, value in DATED_LABELS.items():
            self.assertEqual(body[key], value)
        self.assertEqual(body["cutoff_date"], day)
        self.assertEqual(body["cutoff_at"], None if day is None else f"{day}T23:59:59+03:00")
        self.assertEqual(body["index_id"], index_id)
        self.assertIsNone(body["immutable_bundle_id"])
        DatedErrorResponse.model_validate(body)
        return body

    def assert_bound(self, body, day):
        entry = self.entries[day]
        self.assertEqual(body["cutoff_date"], day)
        self.assertEqual(body["cutoff_at"], entry["cutoff_at"])
        self.assertEqual(body["immutable_bundle_id"], entry["bundle_id"])
        self.assertEqual(body["index_id"], self.index["index_id"])
        for key, value in DATED_LABELS.items():
            self.assertEqual(body[key], value)

    def test_dates_route_exposes_only_dates_cutoffs_and_bundle_ids(self):
        body = self.assert_private(self.client.get(PREFIX + "/dates"))
        self.assertEqual(sorted(body), sorted([*DATED_LABELS, "index_id", "default_date", "entries"]))
        self.assertEqual(body["entries"], self.index["entries"])
        self.assertEqual([entry["date"] for entry in body["entries"]], EXPECTED_GRID)
        self.assertEqual(body["default_date"], "2026-09-16")
        self.assertEqual(body["index_id"], self.index["index_id"])
        text = json.dumps(body)
        for forbidden in ("summary", "funds", "Z00", "crossing", "CROSSING", "threshold", "first", "lead"):
            self.assertNotIn(forbidden, text)
        DatesResponse.model_validate(body)

    def test_malformed_and_unregistered_dates_rejected_before_any_bundle_load(self):
        malformed = ("2026-9-16", "2026-02-30", "2025-10-05", "2026-09-17", "abcd", "2026-09-16T00:00",
                     "20260916", "2025-10-31 ", "%20026-09-16")
        with patch.object(dated_app_module, "load_indexed_bundle", side_effect=AssertionError("bundle read")), \
                patch.object(dated_app_module, "load_date_index", side_effect=AssertionError("index read")):
            for value in malformed:
                for suffix in ("summary", "funds", "funds/Z00"):
                    with self.subTest(value=value, suffix=suffix):
                        self.assert_error(self.client.get(f"{PREFIX}/dates/{value}/{suffix}"), 400, "DATE_INVALID")
        with patch.object(dated_app_module, "load_indexed_bundle", side_effect=AssertionError("bundle read")):
            for value in ("2026-09-15", "2025-10-06", "2026-05-29", "2026-01-31"):
                for suffix in ("summary", "funds", "funds/Z00", "funds/ZZZ"):
                    with self.subTest(value=value, suffix=suffix):
                        self.assert_error(self.client.get(f"{PREFIX}/dates/{value}/{suffix}"), 404,
                                          "DATE_NOT_REGISTERED", index_id=self.index["index_id"])
            # A malformed date still wins over a bundle parameter and an unopened code.
            self.assert_error(self.client.get(f"{PREFIX}/dates/2026-9-16/funds/ZZZ?bundle={'a' * 64}"), 400,
                              "DATE_INVALID")

    def test_each_registered_date_binds_index_cutoff_and_bundle(self):
        for day in EXPECTED_GRID:
            with self.subTest(day=day):
                payload = self.payloads[day]
                summary = self.assert_private(self.client.get(f"{PREFIX}/dates/{day}/summary"))
                self.assert_bound(summary, day)
                self.assertEqual(summary["summary"], payload["summary"])
                self.assertEqual(summary["threshold_provenance"], self.index["threshold_provenance"])
                self.assertEqual(summary["snapshot"], self.index["snapshot"])
                self.assertEqual(summary["summary"]["d1_eligible_crossing"], 1)
                self.assertEqual(summary["summary"]["d1_stale"], 1)
                self.assertEqual(summary["summary"]["no_price_at_cutoff"], 1)
                listed = self.assert_private(self.client.get(f"{PREFIX}/dates/{day}/funds?bundle={self.entries[day]['bundle_id']}"))
                self.assert_bound(listed, day)
                self.assertEqual(listed["funds"], payload["funds"])
                self.assertEqual([record["code"] for record in listed["funds"][:2]], ["Z00", "Z02"])
                self.assertEqual(listed["funds"][-1]["code"], "Z01")
                detail = self.assert_private(self.client.get(f"{PREFIX}/dates/{day}/funds/Z00"))
                self.assert_bound(detail, day)
                self.assertEqual(sorted(detail), sorted([*DATED_LABELS, "cutoff_at", "cutoff_date", "index_id",
                                                         "immutable_bundle_id", "fund", "sources"]))
                self.assertNotIn("summary", listed)
                self.assertNotIn("funds", summary)
                self.assertNotIn("fund", summary)

    def test_all_list_records_equal_detail_records(self):
        for day in ("2025-10-31", "2026-09-16"):
            listed = self.assert_private(self.client.get(f"{PREFIX}/dates/{day}/funds"))["funds"]
            self.assertEqual(len(listed), 100)
            for record in listed:
                detail = self.assert_private(self.client.get(f"{PREFIX}/dates/{day}/funds/{record['code']}"))
                self.assertEqual(detail["fund"], record)
                self.assertEqual([source["source_id"] for source in detail["sources"]], record["evidence"])
                for source in detail["sources"]:
                    self.assertNotIn("original_path", source)
                    self.assertIn(source["kind"], ("PRICE", "SNAPSHOT", "CALIBRATION", "UNIVERSE", "PROTOCOL", "CODE"))
                    self.assertTrue(source["kind"] != "PRICE" or source["fund_code"] == record["code"])

    def test_bundle_parameter_mismatch_returns_409(self):
        day, other = "2026-02-27", "2026-03-31"
        own, foreign = self.entries[day]["bundle_id"], self.entries[other]["bundle_id"]
        for suffix in ("summary", "funds", "funds/Z00"):
            with self.subTest(suffix=suffix):
                self.assert_private(self.client.get(f"{PREFIX}/dates/{day}/{suffix}?bundle={own}"))
                for value in (foreign, "f" * 64, "not-a-bundle", own.upper()):
                    self.assert_error(self.client.get(f"{PREFIX}/dates/{day}/{suffix}?bundle={value}"), 409,
                                      "CONTEXT_MISMATCH", day=day, index_id=self.index["index_id"])
                self.assert_error(self.client.get(f"{PREFIX}/dates/{day}/{suffix}?bundle={own}&bundle={own}"), 400,
                                  "INVALID_REQUEST", day=day, index_id=self.index["index_id"])

    def test_unopened_code_404_before_any_load_or_hash(self):
        with patch.object(dated_app_module, "load_indexed_bundle", side_effect=AssertionError("bundle read")), \
                patch("p50k.research_reviews.dated_bundle._source_bytes", side_effect=AssertionError("hash")), \
                patch("p50k.research_reviews.dated_bundle.bounded_snapshot", side_effect=AssertionError("snapshot")):
            for code in ("ZZZ", "AAA", "z00", "Z0", "Z000"):
                with self.subTest(code=code):
                    self.assert_error(self.client.get(f"{PREFIX}/dates/2025-11-28/funds/{code}"), 404,
                                      "FUND_NOT_FOUND", day="2025-11-28", index_id=self.index["index_id"])

    def test_error_provenance_is_per_request_and_corruption_confined_to_its_date(self):
        broken_day = EXPECTED_GRID[2]
        target = self.root / OUTPUT / "bundles" / self.entries[broken_day]["bundle_id"] / "bundle.json"
        original = target.read_bytes()
        self.addCleanup(target.write_bytes, original)
        target.write_bytes(original.replace(b'"Synthetic fund Z10"', b'"Synthetic fund Z1X"'))
        index_id = self.index["index_id"]
        self.assert_private(self.client.get(f"{PREFIX}/dates/2026-09-16/funds"))
        for suffix in ("summary", "funds", "funds/Z10"):
            self.assert_error(self.client.get(f"{PREFIX}/dates/{broken_day}/{suffix}"), 503, "BUNDLE_INVALID",
                              day=broken_day, index_id=index_id)
        # A success between errors leaves no metadata behind for the next error.
        for day in EXPECTED_GRID:
            if day != broken_day:
                self.assert_bound(self.assert_private(self.client.get(f"{PREFIX}/dates/{day}/summary")), day)
        self.assert_error(self.client.get(f"{PREFIX}/dates/2026-09-15/funds"), 404, "DATE_NOT_REGISTERED",
                          index_id=index_id)
        self.assert_error(self.client.get(f"{PREFIX}/dates/2025-10-31/funds/ZZZ"), 404, "FUND_NOT_FOUND",
                          day="2025-10-31", index_id=index_id)
        self.assert_error(self.client.get(f"{PREFIX}/dates/x/funds"), 400, "DATE_INVALID")
        self.assert_error(self.client.get(PREFIX + "/nothing"), 404, "NOT_FOUND")
        self.assert_private(self.client.get(PREFIX + "/dates"))
        target.unlink()
        self.assert_error(self.client.get(f"{PREFIX}/dates/{broken_day}/funds"), 503, "BUNDLE_INVALID",
                          day=broken_day, index_id=index_id)
        self.assert_private(self.client.get(f"{PREFIX}/dates/2026-08-31/funds/Z00"))
        with self.assertRaisesRegex(ValueError, broken_day):
            self.app.state.verify_all()

    def test_index_unavailable_or_invalid_is_explicit(self):
        for app in (create_dated_app(None, universe_codes=frozenset(CODES), repo_root=self.root),
                    self.dated_app(self.root / "missing-index")):
            with TestClient(app, base_url="http://127.0.0.1") as client:
                self.assert_error(client.get(PREFIX + "/dates"), 503, "INDEX_UNAVAILABLE")
                self.assert_error(client.get(PREFIX + "/dates/2026-09-16/funds"), 503, "INDEX_UNAVAILABLE")
                self.assert_error(client.get(PREFIX + "/dates/2026-9-16/funds"), 400, "DATE_INVALID")
        target = self.index_dir / "index.json"
        original = target.read_bytes()
        self.addCleanup(target.write_bytes, original)
        target.write_bytes(original.replace(b'"default_date":"2026-09-16"', b'"default_date":"2026-08-31"'))
        self.assert_error(self.client.get(PREFIX + "/dates"), 503, "INDEX_INVALID")
        self.assert_error(self.client.get(PREFIX + "/dates/2026-09-16/summary"), 503, "INDEX_INVALID")
        target.write_bytes(original)
        self.assert_private(self.client.get(PREFIX + "/dates"))
        # The index directory name is its fingerprint; a renamed copy is refused.
        with patch.object(dated_app_module, "load_indexed_bundle", side_effect=AssertionError("bundle read")):
            moved = self.root / "renamed-index"
            moved.mkdir(exist_ok=True)
            (moved / "index.json").write_bytes(original)
            with TestClient(self.dated_app(moved, bundles_dir=self.root / OUTPUT / "bundles"),
                            base_url="http://127.0.0.1") as client:
                self.assert_error(client.get(PREFIX + "/dates/2026-09-16/funds"), 503, "INDEX_INVALID")

    def test_responses_are_validated_explicitly_against_their_own_cutoff(self):
        from p50k.research_reviews.dated_bundle import load_indexed_bundle as real_loader
        day = "2026-04-30"

        def loader(mutation):
            def load(*args, **kwargs):
                bundle = copy.deepcopy(real_loader(*args, **kwargs))
                mutation(bundle)
                return bundle
            return load

        def stale_window_end(bundle):
            record = next(record for record in bundle["funds"] if record["code"] == "Z02")
            record["d1"]["metric_period"]["end"] = record["d1"]["latest_contributing_at"]

        def future_chart(bundle):
            record = next(record for record in bundle["funds"] if record["code"] == "Z00")
            record["chart"]["points"][-1]["date"] = "2026-05-01"

        def float_statistic(bundle):
            next(record for record in bundle["funds"] if record["code"] == "Z00")["d1"]["statistic"] = 0.0009

        def kap_source(bundle):
            bundle["sources"][0]["kind"] = "KAP_PDF"

        for label, mutation in (("window", stale_window_end), ("chart", future_chart),
                                ("float", float_statistic), ("kind", kap_source)):
            with self.subTest(label), patch.object(dated_app_module, "load_indexed_bundle", side_effect=loader(mutation)):
                self.assert_error(self.client.get(f"{PREFIX}/dates/{day}/funds"), 503, "BUNDLE_INVALID",
                                  day=day, index_id=self.index["index_id"])
                self.assert_error(self.client.get(f"{PREFIX}/dates/{day}/funds/Z01"), 503, "BUNDLE_INVALID",
                                  day=day, index_id=self.index["index_id"])

    def test_models_bind_nested_dates_to_their_own_cutoff(self):
        payload = self.payloads["2026-01-30"]
        view = validate_dated_view(payload, self.index["index_id"])
        listed = view.funds.model_dump(mode="json")
        summary = view.summary.model_dump(mode="json")

        def rejected(model, change, base):
            changed = copy.deepcopy(base)
            change(changed)
            with self.assertRaises(ValidationError):
                model.model_validate(changed)

        z00 = next(index for index, record in enumerate(listed["funds"]) if record["code"] == "Z00")
        cases = {
            "cutoff_at": lambda p: p.update(cutoff_at="2026-09-16T23:59:59+03:00"),
            "cutoff_date": lambda p: p.update(cutoff_date="2026-02-27"),
            "range": lambda p: p.update(cutoff_date="2025-10-03", cutoff_at="2025-10-03T23:59:59+03:00"),
            "latest": lambda p: p["funds"][z00]["d1"].update(latest_contributing_at="2026-01-31"),
            "baseline": lambda p: p["funds"][z00]["chart"].update(baseline_date="2026-02-02"),
            "equal_threshold": lambda p: p["funds"][z00]["d1"].update(statistic="0.00050"),
            "state": lambda p: p["funds"][z00].update(d1_state="ELIGIBLE_NO_CROSSING"),
            "comment": lambda p: p["funds"][z00].update(comment_tr="Önceden bilinen bir uyarı."),
            "order": lambda p: p["funds"].reverse(),
            "flow": lambda p: p["funds"][z00].update(flow={}),
            "bool": lambda p: p["funds"][z00]["d1"].update(usable_observations=True),
            "label": lambda p: p.update(findings_scope="ALL"),
        }
        for label, change in cases.items():
            with self.subTest(label):
                rejected(DatedFundsResponse, change, listed)
        rejected(DatedSummaryResponse, lambda p: p["summary"].update(d1_stale=2), summary)
        rejected(DatedSummaryResponse, lambda p: p["summary"].update(no_price_at_cutoff=101), summary)
        rejected(DatedSummaryResponse, lambda p: p["snapshot"].update(latest_retrieved_at="2026-10-08T00:00:00+00:00"),
                 summary)
        rejected(DatedSummaryResponse, lambda p: p["threshold_provenance"].update(percentile=95), summary)
        broken = copy.deepcopy(payload)
        broken["summary"]["d1_stale"], broken["summary"]["d1_unavailable"] = 0, 98
        with self.assertRaisesRegex(ValueError, "Summary counts"):
            validate_dated_view(broken, self.index["index_id"])
        with self.assertRaises(ValidationError):
            DatedErrorResponse.model_validate({**DATED_LABELS, "cutoff_at": "2026-09-16T23:59:59+03:00",
                                               "cutoff_date": None, "index_id": None, "immutable_bundle_id": None,
                                               "error": {"code": "DATE_INVALID", "message_tr": "x"}})
        dates = self.assert_private(self.client.get(PREFIX + "/dates"))
        rejected(DatesResponse, lambda p: p["entries"].pop(4), dates)
        rejected(DatesResponse, lambda p: p["entries"][0].update(cutoff_at="2025-10-31T20:59:59+00:00"), dates)

    def test_error_messages_are_short_turkish_without_denied_wording(self):
        for code, message in MESSAGES_TR.items():
            with self.subTest(code):
                self.assertEqual(denylist_hits(message), [])
                self.assertEqual(date_or_month_mentions(message), [])
                self.assertLess(len(message), 90)

    def test_no_write_methods_sources_route_or_cors(self):
        for route in self.app.routes:
            if getattr(route, "path", "").startswith("/research-dated"):
                self.assertEqual(route.methods, {"GET"}, route.path)
        for method in ("post", "put", "patch", "delete"):
            for path in ("/dates", "/dates/2026-09-16/funds", "/dates/2026-09-16/funds/Z00"):
                with self.subTest(method=method, path=path):
                    self.assert_error(getattr(self.client, method)(PREFIX + path), 405, "INVALID_REQUEST")
        self.assert_error(self.client.options(PREFIX + "/dates", headers={
            "Origin": "http://127.0.0.1:3060", "Access-Control-Request-Method": "GET"}), 405, "INVALID_REQUEST")
        self.assert_private(self.client.get(PREFIX + "/dates", headers={"Origin": "http://127.0.0.1:3060"}))
        for path in ("/sources/" + "a" * 64, "/dates/2026-09-16/sources", "/dates/2026-09-16/funds/Z00/sources",
                     "/dates/2026-09-16", "/dates/2026-09-16/funds/Z00/../../summary/x"):
            self.assert_error(self.client.get(PREFIX + path), 404, "NOT_FOUND")

    def test_loopback_host_and_origin_only(self):
        self.assert_error(self.client.get(PREFIX + "/dates", headers={"Host": "example.com"}), 400, "HOST_REJECTED")
        for host in ("localhost:8768", "localhost", "127.0.0.1", "127.0.0.1:8768", "[::1]", "[::1]:8768"):
            with self.subTest(host=host):
                self.assert_private(self.client.get(PREFIX + "/dates", headers={"Host": host}))
        # The raw header is matched whole; a parsed hostname would fail open or raise on these.
        for host in ("[", "[::1", "127.0.0.1@evil.com", "evil.com#@127.0.0.1", "127.0.0.1/x", "127.0.0.1:",
                     "127.0.0.1:123456", "localhost.evil.com", "127.0.0.1 ", "::1", "[::1]:x", "LOCALHOST.", ""):
            with self.subTest(host=host):
                self.assert_error(self.client.get(PREFIX + "/dates", headers={"Host": host}), 400, "HOST_REJECTED")
        for origin in ("http://0.0.0.0:3060", "https://example.com", "http://localhost:3060/path",
                       "http://user@127.0.0.1:3060"):
            with self.assertRaises(ValueError):
                self.dated_app(frontend_origin=origin)

    def test_v1_app_unchanged_alongside_dated_app(self):
        from tests.unit.test_research_api import authored_bundle

        base = self.root / "v1-authored"
        base.mkdir(exist_ok=True)
        v1_payload, v1_dir, _, _ = authored_bundle(base)
        v1_codes = frozenset(f"S{index:02}" for index in range(100))
        paths = ("/research/v1/health", "/research/v1/summary", "/research/v1/funds", "/research/v1/funds/S00",
                 "/research/v1/funds/ZZZ", PREFIX + "/dates")

        def responses(client):
            return [(response.status_code, response.json(), response.headers["cache-control"])
                    for response in (client.get(path) for path in paths)]

        with TestClient(create_app(v1_dir, universe_codes=v1_codes), base_url="http://127.0.0.1:8767") as alone:
            before = responses(alone)
        v1_app = create_app(v1_dir, universe_codes=v1_codes)
        with TestClient(v1_app, base_url="http://127.0.0.1:8767") as v1_client:
            self.assert_private(self.client.get(f"{PREFIX}/dates/2026-09-16/funds"))
            after = responses(v1_client)
            self.assert_error(self.client.get(f"{PREFIX}/dates/2026-09-16/funds/S00"), 404, "FUND_NOT_FOUND",
                              day="2026-09-16", index_id=self.index["index_id"])
            self.assertEqual(responses(v1_client), before)
            v1_post = v1_client.post("/research/v1/funds")
            self.assertEqual(v1_post.status_code, 405)
            self.assertEqual(v1_client.get("/research/v1/health", headers={"Host": "example.com"}).status_code, 400)
        self.assertEqual(after, before)
        self.assertEqual(before[0][1]["immutable_bundle_id"], v1_payload["immutable_bundle_id"])
        for key, value in METADATA.items():
            self.assertEqual(before[0][1][key], value)
        self.assertEqual(before[-1][0], 404)
        self.assertNotIn("knowledge_basis", before[-1][1])
        self.assertEqual(before[4][1]["cutoff_at"], CUTOFF_AT)
        dated_on_v1 = self.client.get("/research/v1/health")
        self.assert_error(dated_on_v1, 404, "NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
