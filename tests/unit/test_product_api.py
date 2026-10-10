"""Authenticated read contracts and publication cutoffs, using synthetic data only."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import os
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
from psycopg.types.json import Jsonb

from p50k.product.app import create_app
from p50k.product.db import connect
from p50k.product.models import (
    DailyChart, EventsPage, Fund, FundsPage, PricePoint, RegulatoryEvent,
    Signal, SignalsPage,
)
from p50k.product.queries import FundQueries, coverage_for, evidence_values, price_summary_for, source_reference, source_url
from p50k.product.routes import get_queries, require_session, router
from p50k.product.settings import Settings


CUTOFF = datetime(2020, 1, 5, 12, tzinfo=timezone.utc)
DAY = date(2020, 1, 5)
SHA = "a" * 64


def synthetic_signal(state="ABSTAINED", *, detector="D1", attribute=False) -> Signal:
    return Signal(
        fund_code="ZZZ", detector_id=detector, version_id="synthetic-api-v1",
        run_id=str(uuid4()), state=state, reason="SYNTHETIC_TEST_REASON",
        value=None, threshold=None, evidence_id="synthetic-" + detector,
        as_of=DAY, effective_date=DAY - timedelta(days=2), origin="SYNTHETIC", values={}, thresholds={}, unit="ratio",
        available_at=CUTOFF, is_attribute=attribute,
    )


class SyntheticReader:
    """Test-only dependency; never available from a runtime configuration flag."""
    def __init__(self):
        self.calls = []
        self.record = Fund(fund_code="ZZZ", name="Synthetic API Fund", category=None,
                           tefas_status=None, listing_as_of=date(2026, 1, 1))

    def funds(self, query, limit, offset):
        self.calls.append(("funds", query, limit, offset))
        return FundsPage(items=[self.record], total=1, limit=limit, offset=offset)

    def fund(self, code):
        self.calls.append(("fund", code))
        return self.record if code == "ZZZ" else None

    def chart(self, code, start, end, cutoff):
        self.calls.append(("chart", code, start, end, cutoff))
        return DailyChart(fund_code=code, start_date=start, end_date=end, cutoff=cutoff, points=[
            PricePoint(effective_date=DAY - timedelta(days=2), nav="1.250000",
                       published_at=CUTOFF - timedelta(days=2), available_at=CUTOFF - timedelta(days=2),
                       source_id="TEFAS", source_sha256=SHA, unit="NAV/unit", availability_rule="synthetic",
                       origin="SYNTHETIC"),
            PricePoint(effective_date=DAY - timedelta(days=1), nav=None,
                       published_at=None, available_at=CUTOFF,
                       source_id="TEFAS", source_sha256=SHA, unit="NAV/unit", availability_rule="synthetic",
                       origin="SYNTHETIC"),
        ])

    def signals(self, code, state, as_of, cutoff, limit, offset):
        self.calls.append(("signals", code, state, as_of, cutoff, limit, offset))
        return SignalsPage(items=[synthetic_signal()], total=1, limit=limit, offset=offset, cutoff=cutoff)

    def events(self, code, as_of, cutoff, limit, offset):
        self.calls.append(("events", code, as_of, cutoff, limit, offset))
        event = RegulatoryEvent(
            event_id="synthetic-event", fund_code="ZZZ", event_type="SYNTHETIC_REVIEW_EVENT",
            effective_date=DAY, status="CANDIDATE", review_state="UNDER_REVIEW",
            triggers_regulatory_signal=False, quotation="Synthetic event text.",
            source_id="SPK", source_sha256=SHA, source_url=None, published_at=CUTOFF,
            available_at=CUTOFF, confirmed_at=None, availability_rule="synthetic", origin="SYNTHETIC",
        )
        return EventsPage(items=[event], total=1, limit=limit, offset=offset, cutoff=cutoff)


class ProductReadApiTests(unittest.TestCase):
    def setUp(self):
        self.reader = SyntheticReader()
        # The isolated app has no production middleware or database connection.
        self.application = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
        self.application.include_router(router)
        self.application.dependency_overrides[get_queries] = lambda: self.reader
        self.client = TestClient(self.application, base_url="http://localhost")
        self.addCleanup(self.client.close)

    def authenticate_test_client(self):
        self.application.dependency_overrides[require_session] = lambda: None

    def test_every_registered_real_route_and_docs_require_authentication(self):
        for path in ("/funds", "/funds/ZZZ", "/signals", "/events", "/docs", "/openapi.json"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 401)
        self.assertEqual(self.reader.calls, [])

    def test_runtime_middleware_stays_default_deny_even_if_session_dependency_is_overridden(self):
        application = create_app()
        application.dependency_overrides[require_session] = lambda: None
        with patch("p50k.product.routes.connect", side_effect=AssertionError("must not access data")), \
                TestClient(application, base_url="http://localhost") as client:
            for path in ("/funds", "/funds/ZZZ", "/signals", "/events", "/docs", "/openapi.json", "/unknown"):
                self.assertEqual(client.get(path).status_code, 401, path)

    def test_fund_search_and_pagination_are_bounded(self):
        self.authenticate_test_client()
        response = self.client.get("/funds", params={"q": "  Synthetic  ", "limit": 10, "offset": 3})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.reader.calls, [("funds", "Synthetic", 10, 3)])
        self.assertTrue(response.json()["items"][0]["metadata_current_only"])
        for parameters in ({"q": "x" * 81}, {"limit": 101}, {"limit": 0}, {"offset": -1}, {"offset": 10001}):
            with self.subTest(parameters=parameters):
                self.assertEqual(self.client.get("/funds", params=parameters).status_code, 422)

    def test_detail_has_daily_nav_nulls_evidence_labels_and_unconfirmed_events(self):
        self.authenticate_test_client()
        response = self.client.get("/funds/ZZZ", params={"cutoff": CUTOFF.isoformat(), "days": 5})
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual(result["origin"], "DELAYED")
        self.assertEqual(result["rights_status"], "UNREVIEWED")
        self.assertTrue(result["development_result"])
        self.assertEqual(result["chart"]["cadence"], "DAILY_NAV")
        self.assertEqual([point["nav"] for point in result["chart"]["points"]], ["1.250000", None])
        self.assertEqual(result["price_summary"]["status"], "LATEST_MISSING")
        self.assertEqual(result["price_summary"]["scope"], "CHART_WINDOW")
        self.assertIsNone(result["price_summary"]["latest_observation"]["nav"])
        self.assertEqual(result["price_summary"]["latest_observation"]["effective_date"], "2020-01-04")
        self.assertEqual(result["price_summary"]["last_available"]["effective_date"], "2020-01-03")
        self.assertEqual(result["price_summary"]["last_available"]["nav"], "1.250000")
        self.assertEqual(result["coverage"]["state"], "ABSTAINED")
        self.assertEqual(result["coverage"]["evidence_ids"], ["synthetic-D1"])
        self.assertEqual(result["signals"][0]["as_of"], "2020-01-05")
        self.assertEqual(result["signals"][0]["effective_date"], "2020-01-03")
        self.assertEqual(result["events"][0]["review_state"], "UNDER_REVIEW")
        self.assertFalse(result["events"][0]["triggers_regulatory_signal"])
        chart_call = next(call for call in self.reader.calls if call[0] == "chart")
        self.assertEqual(chart_call[2:4], (date(2020, 1, 1), DAY))

    def test_unknown_fund_bad_code_and_oversized_chart_are_rejected(self):
        self.authenticate_test_client()
        self.assertEqual(self.client.get("/funds/YYY").status_code, 404)
        self.assertEqual(self.client.get("/funds/invalid").status_code, 422)
        self.assertEqual(self.client.get("/funds/ZZZ", params={"days": 732}).status_code, 422)
        self.assertEqual(self.client.get("/funds/ZZZ", params={"days": 0}).status_code, 422)

    def test_cutoff_requires_timezone_and_rejects_future_on_all_observation_routes(self):
        self.authenticate_test_client()
        for path in ("/funds/ZZZ", "/signals", "/events"):
            for cutoff in ("2020-01-01T12:00:00", (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()):
                with self.subTest(path=path, cutoff=cutoff):
                    self.assertEqual(self.client.get(path, params={"cutoff": cutoff}).status_code, 422)
        self.assertEqual(self.reader.calls, [])

    def test_signals_and_events_validate_filters_and_limits(self):
        self.authenticate_test_client()
        for path in ("/signals", "/events"):
            self.assertEqual(self.client.get(path, params={"limit": 101}).status_code, 422)
            self.assertEqual(self.client.get(path, params={"offset": 50001 if path == "/signals" else 10001}).status_code, 422)
            self.assertEqual(self.client.get(path, params={"fund_code": "invalid"}).status_code, 422)
            self.assertEqual(self.client.get(path, params={"fund_code": "ZZZ", "cutoff": CUTOFF.isoformat()}).status_code, 200)
        self.assertEqual(self.client.get("/signals", params={"state": "NORMAL"}).status_code, 422)

    def test_global_signal_pagination_reaches_beyond_ten_thousand_and_remains_bounded(self):
        self.authenticate_test_client()
        for offset in (10001, 50000):
            response = self.client.get("/signals", params={"offset": offset})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["offset"], offset)
        self.assertEqual(self.client.get("/signals", params={"offset": 50001}).status_code, 422)
        self.assertEqual(self.client.get("/signals", params={"offset": -1}).status_code, 422)

    def test_openapi_and_documentation_are_available_only_to_authenticated_client(self):
        self.authenticate_test_client()
        schema = self.client.get("/openapi.json")
        self.assertEqual(schema.status_code, 200)
        self.assertEqual(set(schema.json()["paths"]), {"/funds", "/funds/{fund_code}", "/signals", "/events"})
        self.assertIn("SignalsPage", schema.json()["components"]["schemas"])
        docs = self.client.get("/docs")
        self.assertEqual(docs.status_code, 200)
        self.assertIn("/openapi.json", docs.text)


class ReadContractTests(unittest.TestCase):
    def test_price_summary_excludes_later_availability_and_preserves_dated_missing_row(self):
        chart = SyntheticReader().chart("ZZZ", date(2020, 1, 1), DAY, CUTOFF)
        original = chart.model_dump()
        summary = price_summary_for(chart)
        self.assertEqual(summary.status, "LATEST_MISSING")
        self.assertIsNone(summary.latest_observation.nav)
        self.assertEqual(summary.last_available.effective_date, DAY - timedelta(days=2))
        future = chart.points[0].model_copy(update={"effective_date": DAY, "nav": "9.000000",
                                                   "available_at": CUTOFF + timedelta(seconds=1)})
        chart.points.append(future)
        self.assertEqual(price_summary_for(chart), summary)
        chart.points[-1] = future.model_copy(update={"available_at": CUTOFF,
                                                     "published_at": CUTOFF + timedelta(seconds=1)})
        self.assertEqual(price_summary_for(chart), summary)
        self.assertEqual(chart.model_dump()["points"][:2], original["points"])

    def test_price_summary_reports_conflicting_missing_and_empty_windows_without_filling(self):
        chart = SyntheticReader().chart("ZZZ", date(2020, 1, 1), DAY, CUTOFF)
        chart.points[-1] = chart.points[-1].model_copy(update={"ambiguous_revision": True})
        summary = price_summary_for(chart)
        self.assertEqual(summary.status, "LATEST_CONFLICTING")
        self.assertEqual(summary.last_available.nav, "1.250000")
        self.assertIsNone(chart.points[-1].nav)
        chart.points = [chart.points[-1]]
        self.assertIsNone(price_summary_for(chart).last_available)
        chart.points = []
        self.assertEqual(price_summary_for(chart).status, "NO_OBSERVATIONS")
        self.assertIsNone(price_summary_for(chart).latest_observation)

    def test_unknown_and_attribute_only_coverage_never_become_normal(self):
        for signals in ([], [synthetic_signal()], [synthetic_signal("NOT_TRIGGERED", detector="D5", attribute=True)]):
            with self.subTest(signals=signals):
                self.assertEqual(coverage_for(signals).state, "ABSTAINED")
        self.assertEqual(coverage_for([synthetic_signal("NOT_TRIGGERED")]).state, "NOT_TRIGGERED")
        self.assertEqual(coverage_for([synthetic_signal("TRIGGERED"), synthetic_signal("NOT_TRIGGERED", detector="D2")]).state, "TRIGGERED")

    def test_detector_numbers_are_decimal_strings_and_contract_forbids_extra_fields(self):
        self.assertEqual(evidence_values({"decimal": Decimal("1.000000"), "count": 4,
                                         "ratio": 0.125, "missing": None, "attribute": True}),
                         {"decimal": "1.000000", "count": "4", "ratio": "0.125", "missing": None, "attribute": True})
        payload = synthetic_signal().model_dump()
        payload["value"] = 1.0
        with self.assertRaises(ValidationError):
            Signal(**payload)
        payload["value"] = None
        payload["accuracy"] = "0.99"
        with self.assertRaises(ValidationError):
            Signal(**payload)
        with self.assertRaises(ValueError):
            evidence_values({"value": float("nan")})

    def test_only_official_public_spk_links_are_returned(self):
        self.assertEqual(source_url("https://spk.gov.tr/Synthetic.pdf"), "https://spk.gov.tr/Synthetic.pdf")
        for value in ("http://localhost/raw/a.pdf", "file:///raw/a.pdf", "https://example.invalid", "https://user@spk.gov.tr/a",
                      "https://spk.gov.tr:invalid/a", "https://[broken", None):
            self.assertIsNone(source_url(value))

    def test_source_references_keep_dates_hashes_and_reject_local_paths(self):
        reference = {"source_id": "synthetic-provider", "source_sha256": SHA,
                     "effective_date": DAY.isoformat(), "available_at": CUTOFF.isoformat(),
                     "source_url": "file:///raw/private-file"}
        result = source_reference(reference)
        self.assertEqual(result.effective_date, DAY)
        self.assertEqual(result.available_at, CUTOFF)
        self.assertEqual(result.source_sha256, SHA)
        self.assertIsNone(result.source_url)
        reference["source_path"] = "private-file"
        with self.assertRaises(ValidationError):
            source_reference(reference)


@unittest.skipUnless(os.environ.get("P50K_TEST_DATABASE") == "1", "Requires isolated PostgreSQL p50k_dev")
class ProductReadDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.settings = Settings.from_env()
        if self.settings.db_name != "p50k_dev":
            raise RuntimeError("Synthetic API fixtures require p50k_dev")
        self.connection = connect(self.settings)
        self.addCleanup(self.connection.close)
        self.reader = FundQueries(self.connection)
        self.code = "API" + uuid4().hex[:9].upper()
        self.sha = hashlib.sha256(self.code.encode()).hexdigest()
        self.name = "Synthetic API Fund " + uuid4().hex
        self.connection.execute(
            "INSERT INTO ref.funds (fund_code,name,category,tefas_status,listing_as_of,source_sha256) VALUES (%s,%s,NULL,NULL,%s,%s)",
            (self.code, self.name, date(2026, 1, 1), self.sha),
        )

    def price(self, day, nav, available_at, *, published_at=None, suffix=""):
        digest = hashlib.sha256((self.code + suffix).encode()).hexdigest()
        self.connection.execute("""
            INSERT INTO obs.fund_prices (fund_code,effective_date,nav,source_sha256,origin,
                published_at,available_at,availability_rule)
            VALUES (%s,%s,%s,%s,'SYNTHETIC',%s,%s,'synthetic-api')
        """, (self.code, day, nav, digest, published_at, available_at))

    def test_daily_prices_exclude_future_publication_and_revisions_preserve_known_nulls(self):
        self.price(date(2020, 1, 1), Decimal("1.250000"), CUTOFF - timedelta(days=4), suffix="original")
        self.price(date(2020, 1, 1), Decimal("9.000000"), CUTOFF + timedelta(days=1), suffix="future-revision")
        self.price(date(2020, 1, 2), Decimal("2.000000"), CUTOFF - timedelta(days=3),
                   published_at=CUTOFF + timedelta(days=1), suffix="future-publication")
        self.price(date(2020, 1, 3), None, CUTOFF, suffix="known-missing")
        self.price(date(2020, 1, 4), None, CUTOFF + timedelta(days=1), suffix="future-missing")
        self.price(date(2020, 1, 5), Decimal("3.000000"), None, suffix="unknown-availability")
        chart = self.reader.chart(self.code, date(2020, 1, 1), DAY, CUTOFF)
        self.assertEqual([(point.effective_date, point.nav) for point in chart.points],
                         [(date(2020, 1, 1), "1.250000"), (date(2020, 1, 3), None)])
        self.assertTrue(all(point.available_at <= CUTOFF for point in chart.points))
        summary = price_summary_for(chart)
        self.assertEqual(summary.status, "LATEST_MISSING")
        self.assertEqual(summary.last_available.nav, "1.250000")
        self.assertEqual(summary.last_available.effective_date, date(2020, 1, 1))
        self.assertEqual(summary.latest_observation.effective_date, date(2020, 1, 3))

    def test_chart_conflicting_tied_revisions_remain_unknown_until_a_later_revision_is_available(self):
        pairs = ((date(2020, 1, 1), Decimal("1.1000"), Decimal("1.1000")),
                 (date(2020, 1, 2), Decimal("1.1000"), Decimal("2.2000")),
                 (date(2020, 1, 3), Decimal("1.1000"), None),
                 (date(2020, 1, 4), None, None))
        for day, first, second in pairs:
            self.price(day, first, CUTOFF - timedelta(days=1), suffix=day.isoformat() + "-first")
            self.price(day, second, CUTOFF - timedelta(days=1), suffix=day.isoformat() + "-second")
        self.price(date(2020, 1, 2), Decimal("3.3000"), CUTOFF + timedelta(days=1), suffix="future-resolution")
        chart = self.reader.chart(self.code, date(2020, 1, 1), DAY, CUTOFF)
        self.assertEqual([(point.nav, point.ambiguous_revision) for point in chart.points],
                         [("1.1000", False), (None, True), (None, True), (None, False)])
        later = self.reader.chart(self.code, date(2020, 1, 1), DAY, CUTOFF + timedelta(days=1))
        self.assertEqual(later.points[1].nav, "3.3000")
        self.assertFalse(later.points[1].ambiguous_revision)
        self.assertEqual(price_summary_for(chart).last_available.effective_date, date(2020, 1, 1))
        self.assertEqual(price_summary_for(later).last_available.effective_date, date(2020, 1, 2))

    def test_catalog_search_is_literal_paginated_and_current_only(self):
        result = self.reader.funds(self.name, 1, 0)
        self.assertEqual(result.total, 1)
        self.assertEqual(result.items[0].fund_code, self.code)
        self.assertTrue(result.items[0].metadata_current_only)
        self.assertIsNone(result.items[0].category)
        self.assertEqual(self.reader.funds(self.name, 1, 1).items, [])
        self.assertEqual(self.reader.funds(self.name + "%", 1, 0).total, 0)
        self.assertEqual(self.reader.funds(self.name + "' OR TRUE --", 1, 0).total, 0)

    def test_candidate_event_does_not_confirm_until_confirmation_is_available(self):
        event_id = "synthetic-api-" + uuid4().hex
        for status, confirmed_at in (("CANDIDATE", None), ("CONFIRMED", CUTOFF + timedelta(days=1))):
            self.connection.execute("""
                INSERT INTO obs.regulatory_events (event_id,fund_code,event_type,effective_date,status,
                    confirmed_by,confirmed_at,quotation,source_sha256,origin,published_at,available_at,availability_rule,metadata)
                VALUES (%s,%s,'SPK_LIQUIDATION_ORDER',%s,%s,%s,%s,'Synthetic event.',%s,
                    'SYNTHETIC',%s,%s,'synthetic-api','{"bulletin_id":"2026-61"}')
            """, (event_id, self.code, DAY, status, "synthetic-reviewer" if confirmed_at else None,
                  confirmed_at, self.sha, CUTOFF, CUTOFF))
        earlier = self.reader.events(self.code, DAY, CUTOFF, 10, 0)
        self.assertEqual(earlier.total, 1)
        self.assertEqual(earlier.items[0].status, "CANDIDATE")
        self.assertFalse(earlier.items[0].triggers_regulatory_signal)
        later = self.reader.events(self.code, DAY + timedelta(days=1), CUTOFF + timedelta(days=1), 10, 0)
        self.assertEqual(later.total, 1)
        self.assertEqual(later.items[0].status, "CONFIRMED")
        self.assertTrue(later.items[0].triggers_regulatory_signal)
        self.assertTrue(later.items[0].in_monitoring_scope)
        other_id = "synthetic-outside-scope-" + uuid4().hex
        self.connection.execute("""
            INSERT INTO obs.regulatory_events (event_id,fund_code,event_type,effective_date,status,
                confirmed_by,confirmed_at,source_sha256,origin,published_at,available_at,availability_rule,metadata)
            VALUES (%s,%s,'SPK_LIQUIDATION_ORDER',%s,'CONFIRMED','synthetic-reviewer',%s,%s,
                'SYNTHETIC',%s,%s,'synthetic-api','{"bulletin_id":"synthetic-outside-scope"}')
        """, (other_id, self.code, DAY, CUTOFF, self.sha, CUTOFF, CUTOFF))
        outside = next(item for item in self.reader.events(self.code, DAY, CUTOFF, 10, 0).items
                       if item.event_id == other_id)
        self.assertEqual(outside.status, "CONFIRMED")
        self.assertFalse(outside.in_monitoring_scope)
        self.assertFalse(outside.triggers_regulatory_signal)

    def test_unknown_event_availability_is_visible_for_review_only_when_already_ingested(self):
        event_ids = []
        cases = (("CANDIDATE", CUTOFF - timedelta(hours=1), None),
                 ("CONFIRMED", CUTOFF - timedelta(hours=1), None),
                 ("CANDIDATE", CUTOFF + timedelta(hours=1), None),
                 ("CANDIDATE", CUTOFF - timedelta(hours=1), CUTOFF + timedelta(hours=1)))
        for status, ingested, published in cases:
            event_id = "synthetic-unknown-event-" + uuid4().hex
            event_ids.append(event_id)
            self.connection.execute("""
                INSERT INTO obs.regulatory_events (event_id,fund_code,event_type,effective_date,status,
                    confirmed_by,confirmed_at,source_sha256,origin,published_at,available_at,availability_rule,
                    metadata,ingested_at)
                VALUES (%s,%s,'SPK_LIQUIDATION_ORDER',%s,%s,%s,%s,%s,
                    'SYNTHETIC',%s,NULL,'unknown','{"bulletin_id":"2026-61"}',%s)
            """, (event_id, self.code, DAY, status, "synthetic-reviewer" if status == "CONFIRMED" else None,
                  CUTOFF - timedelta(hours=1) if status == "CONFIRMED" else None, self.sha, published, ingested))
        current = self.reader.events(self.code, DAY, CUTOFF, 10, 0)
        self.assertEqual(current.total, 2)
        self.assertEqual({item.event_id for item in current.items}, set(event_ids[:2]))
        for item in current.items:
            self.assertIsNone(item.available_at)
            self.assertTrue(item.availability_unknown)
            self.assertEqual(item.review_state, "UNDER_REVIEW")
            self.assertFalse(item.triggers_regulatory_signal)
        earlier = self.reader.events(self.code, DAY, CUTOFF - timedelta(hours=2), 10, 0)
        self.assertEqual(earlier.total, 0)

    def detector_run(self, cutoff, *, finalize=True, state="ABSTAINED", available_at=None, origin="DELAYED", effective_date=DAY):
        version_id = "synthetic-api-" + uuid4().hex
        self.connection.execute("""
            INSERT INTO det.detector_versions (version_id,protocol_version,protocol_sha256,code_sha256,
                thresholds,calibration_input_sha256,calibration_cutoff)
            VALUES (%s,'synthetic-api-v1',%s,%s,'{}',%s,%s)
        """, (version_id, self.sha, self.sha, self.sha, CUTOFF - timedelta(days=10)))
        run_id = self.connection.execute("""
            INSERT INTO det.detector_runs (protocol_version,protocol_sha256,origin,cutoff,parameters)
            VALUES ('synthetic-api-v1',%s,%s,%s,'{}') RETURNING run_id
        """, (self.sha, origin, cutoff)).fetchone()[0]
        evidence_id = "synthetic-api-" + uuid4().hex
        triggered = None if state == "ABSTAINED" else state == "TRIGGERED"
        self.connection.execute("""
            INSERT INTO det.evidence_items (evidence_id,fund_code,run_id,detector_id,origin,effective_date,
                available_at,unit,values,thresholds,triggered,state,source_references)
            VALUES (%s,%s,%s,'D1',%s,%s,%s,'ratio',%s,%s,%s,%s,%s)
        """, (evidence_id, self.code, run_id, origin, effective_date, available_at,
              Jsonb({"excess": "1.2500"}), Jsonb({"upper": "0.5000"}), triggered, state,
              Jsonb([{"source_id": "synthetic-provider", "source_sha256": self.sha,
                      "effective_date": effective_date.isoformat() if effective_date else None, "available_at": available_at.isoformat() if available_at else None,
                      "source_url": None}])))
        self.connection.execute("""
            INSERT INTO det.signals (run_id,fund_code,detector_id,state,reason,value,threshold,evidence_id,as_of)
            VALUES (%s,%s,'D1',%s,'SYNTHETIC_TEST_REASON',1.2500,0.5000,%s,%s)
        """, (run_id, self.code, state, evidence_id, DAY))
        if finalize:
            self.connection.execute("""
                INSERT INTO det.run_inputs (run_id,version_id,input_sha256,input_watermark,as_of,origin,cutoff)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (run_id, version_id, self.sha, available_at, DAY, origin, cutoff))
        return run_id

    def test_signals_use_complete_current_run_and_do_not_leak_future_or_replay(self):
        current = self.detector_run(CUTOFF, state="ABSTAINED", effective_date=DAY - timedelta(days=2))
        self.detector_run(CUTOFF + timedelta(hours=1), finalize=False, state="TRIGGERED", available_at=CUTOFF)
        self.detector_run(CUTOFF + timedelta(hours=2), state="TRIGGERED", available_at=CUTOFF, origin="HISTORICAL_REPLAY")
        self.detector_run(CUTOFF + timedelta(days=1), state="TRIGGERED", available_at=CUTOFF)
        result = self.reader.signals(self.code, None, DAY, CUTOFF + timedelta(hours=3), 10, 0)
        self.assertEqual(result.total, 1)
        item, = result.items
        self.assertEqual(item.run_id, str(current))
        self.assertEqual(item.state, "ABSTAINED")
        self.assertEqual(item.as_of, DAY)
        self.assertEqual(item.effective_date, DAY - timedelta(days=2))
        self.assertIsNone(item.available_at)
        self.assertEqual(item.value, "1.2500")
        self.assertEqual(item.threshold, "0.5000")
        self.assertEqual(item.values, {"excess": "1.2500"})
        self.assertEqual(item.source_references[0].source_sha256, self.sha)
        self.assertIsNone(item.source_references[0].available_at)
        self.assertEqual(coverage_for(result.items).state, "ABSTAINED")

    def test_unknown_availability_cannot_create_normal_coverage(self):
        self.detector_run(CUTOFF, state="NOT_TRIGGERED", available_at=None)
        result = self.reader.signals(self.code, None, DAY, CUTOFF, 10, 0)
        self.assertEqual(result.total, 0)
        self.assertEqual(coverage_for(result.items).state, "ABSTAINED")

    def test_global_signal_offset_can_exceed_ten_thousand_without_invalidating_contract(self):
        self.detector_run(CUTOFF, state="ABSTAINED", available_at=None)
        result = self.reader.signals(None, None, DAY, CUTOFF, 100, 50000)
        self.assertEqual(result.offset, 50000)
        self.assertEqual(result.total, 1)
        self.assertEqual(result.items, [])


if __name__ == "__main__":
    unittest.main()
