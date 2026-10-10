"""Synthetic owner isolation, current-run availability and CSRF acceptance tests."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import os
from unittest import TestCase, skipUnless
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from p50k.product.app import create_app
from p50k.product.auth import CSRF_COOKIE, Principal, digest_token
from p50k.product.db import connect
from p50k.product.settings import Settings
from p50k.product.watchlist_routes import router
from p50k.product.watchlists import (WatchlistError, mark_read, notifications,
    remove_fund, save_fund, set_notifications, watchlist)


@skipUnless(os.environ.get("P50K_TEST_DATABASE") == "1", "Requires isolated p50k_dev")
class WatchlistDatabaseTests(TestCase):
    def setUp(self):
        self.settings = Settings.from_env()
        self.assertEqual(self.settings.db_name, "p50k_dev")
        self.code = "TST" + uuid4().hex[:9].upper()
        self.other_code = "TST" + uuid4().hex[:9].upper()
        self.checksum = sha256(self.code.encode()).hexdigest()
        with connect(self.settings) as connection:
            self.owners = [str(connection.execute("INSERT INTO auth.users(email,password_hash) VALUES(%s,'synthetic-hash') RETURNING user_id", (uuid4().hex + "@example.invalid",)).fetchone()[0]) for _ in range(2)]
            for code in (self.code, self.other_code):
                connection.execute("INSERT INTO ref.funds(fund_code,name,category,source_sha256) VALUES(%s,'Synthetic watchlist fund','Synthetic',%s)", (code, self.checksum))
        self.now = datetime.now(timezone.utc)

    def _run(self, cutoff: datetime, state: str = "TRIGGERED", available: bool = True,
             evidence_delay: timedelta = timedelta(0)) -> str:
        version = "synthetic-watch-" + uuid4().hex
        evidence_id = "synthetic-watch-" + uuid4().hex
        day = cutoff.date()
        with connect(self.settings) as connection:
            connection.execute("""INSERT INTO det.detector_versions(version_id,protocol_version,protocol_sha256,code_sha256,
                thresholds,calibration_input_sha256,calibration_cutoff) VALUES(%s,%s,%s,%s,'{}',%s,'2020-01-01T00:00:00Z')""",
                (version, version, self.checksum, self.checksum, self.checksum))
            run = connection.execute("INSERT INTO det.detector_runs(protocol_version,protocol_sha256,origin,cutoff,parameters) VALUES(%s,%s,'SYNTHETIC',%s,'{}') RETURNING run_id", (version, self.checksum, cutoff)).fetchone()[0]
            connection.execute("""INSERT INTO det.evidence_items(evidence_id,fund_code,run_id,detector_id,origin,effective_date,
                available_at,unit,values,thresholds,triggered,state,source_references)
                VALUES(%s,%s,%s,'D1','SYNTHETIC',%s,%s,'ratio','{"value":"3"}','{"threshold":"2"}',%s,%s,'[{"source_id":"synthetic","source_sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}]')""",
                (evidence_id, self.code, run, day, cutoff + evidence_delay if available else None, None if state == "ABSTAINED" else state == "TRIGGERED", state))
            connection.execute("INSERT INTO det.signals(run_id,fund_code,detector_id,state,reason,value,threshold,evidence_id,as_of) VALUES(%s,%s,'D1',%s,'THRESHOLD_EXCEEDED',3,2,%s,%s)", (run, self.code, state, evidence_id, day))
            connection.execute("INSERT INTO det.run_inputs(run_id,version_id,input_sha256,as_of,origin,cutoff) VALUES(%s,%s,%s,%s,'SYNTHETIC',%s)", (run, version, self.checksum, day, cutoff))
        return evidence_id

    def test_save_is_idempotent_owner_scoped_and_unknown_fund_rejected(self):
        save_fund(self.settings, self.owners[0], self.code)
        save_fund(self.settings, self.owners[0], self.code)
        save_fund(self.settings, self.owners[1], self.code)
        self.assertEqual(watchlist(self.settings, self.owners[0])["total"], 1)
        remove_fund(self.settings, self.owners[0], self.code)
        self.assertEqual(watchlist(self.settings, self.owners[0])["total"], 0)
        self.assertEqual(watchlist(self.settings, self.owners[1])["total"], 1)
        with self.assertRaises(WatchlistError) as error:
            save_fund(self.settings, self.owners[0], "NO" + uuid4().hex[:10].upper())
        self.assertEqual(error.exception.status, 404)

    def test_current_run_preserves_values_source_and_excludes_future_run(self):
        save_fund(self.settings, self.owners[0], self.code)
        current = self._run(self.now)
        future = self._run(self.now + timedelta(days=1))
        result = notifications(self.settings, self.owners[0])
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["evidence_id"], current)
        self.assertNotEqual(result["items"][0]["evidence_id"], future)
        self.assertEqual(result["items"][0]["value"], "3")
        self.assertEqual(result["items"][0]["threshold"], "2")
        self.assertEqual(result["items"][0]["source_references"][0]["source_id"], "synthetic")
        self.assertEqual(notifications(self.settings, self.owners[1])["total"], 0)

    def test_read_state_cannot_cross_owner_or_mutate_evidence(self):
        evidence_id = self._run(self.now)
        for owner in self.owners:
            save_fund(self.settings, owner, self.code)
        self.assertEqual(mark_read(self.settings, self.owners[0], [evidence_id])["marked_read"], 1)
        self.assertEqual(mark_read(self.settings, self.owners[0], [evidence_id])["marked_read"], 0)
        self.assertEqual(notifications(self.settings, self.owners[0], unread_only=True)["unread"], 0)
        self.assertEqual(notifications(self.settings, self.owners[1], unread_only=True)["unread"], 1)
        with self.assertRaises(WatchlistError):
            mark_read(self.settings, self.owners[0], ["unknown-evidence"])
        remove_fund(self.settings, self.owners[0], self.code)
        with self.assertRaises(WatchlistError):
            mark_read(self.settings, self.owners[0], [evidence_id])
        with connect(self.settings) as connection:
            self.assertEqual(connection.execute("SELECT state FROM det.evidence_items WHERE evidence_id=%s", (evidence_id,)).fetchone(), ("TRIGGERED",))

    def test_unknown_availability_and_abstention_are_not_notifications(self):
        save_fund(self.settings, self.owners[0], self.code)
        self._run(self.now, "ABSTAINED", False)
        self.assertEqual(notifications(self.settings, self.owners[0])["total"], 0)
        saved = watchlist(self.settings, self.owners[0])["items"][0]
        self.assertEqual(saved["abstained_count"], 1)
        self.assertEqual(saved["signal_count"], 1)

    def test_in_app_preferences_persist_without_affecting_another_owner(self):
        evidence_id = self._run(self.now)
        for owner in self.owners:
            save_fund(self.settings, owner, self.code)
        set_notifications(self.settings, self.owners[0], False)
        self.assertEqual(notifications(self.settings, self.owners[0])["total"], 0)
        self.assertEqual(notifications(self.settings, self.owners[1])["total"], 1)
        set_notifications(self.settings, self.owners[0], True)
        self.assertEqual(notifications(self.settings, self.owners[0])["items"][0]["evidence_id"], evidence_id)

    def test_http_mutations_require_origin_csrf_and_server_bound_arguments(self):
        app = create_app(self.settings, readiness=lambda _: True)
        if "/watchlist" not in app.openapi()["paths"]:
            app.include_router(router)
        with TestClient(app, base_url="http://localhost") as client:
            self.assertEqual(client.get("/watchlist").status_code, 401)
            token = "a" * 43
            principal = Principal(self.owners[0], "synthetic@example.invalid", "viewer", str(uuid4()), digest_token(token))
            with patch("p50k.product.auth.AuthService.authenticate", return_value=principal):
                self.assertEqual(client.post("/watchlist/" + self.code).status_code, 403)
                client.cookies.set(CSRF_COOKIE, token)
                headers = {"Origin": self.settings.allowed_origins[0], "X-CSRF-Token": token}
                self.assertEqual(client.post("/watchlist/" + self.code, headers=headers).status_code, 200)
                self.assertEqual(client.post("/watchlist/invalid!", headers=headers).status_code, 422)
                self.assertEqual(client.get("/notifications?limit=1000").status_code, 422)
                self.assertEqual(client.post("/notifications/preferences", headers=headers, json={"enabled": False, "user_id": self.owners[1]}).status_code, 422)
                self.assertEqual(client.post("/notifications/preferences", headers=headers, json={"enabled": "false"}).status_code, 422)
                self.assertEqual(client.post("/notifications/read", headers=headers, json={"evidence_ids": []}).status_code, 422)
                self.assertEqual(client.delete("/watchlist/" + self.code, headers=headers).status_code, 200)
                self.assertEqual(client.get("/watchlist").json()["total"], 0)
