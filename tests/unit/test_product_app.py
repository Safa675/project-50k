from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from p50k.product.app import create_app
from p50k.product.settings import Settings


class ProductAppTests(unittest.TestCase):
    def test_public_health_has_no_real_data_and_readiness_can_fail(self):
        for available, status in ((True, 200), (False, 503)):
            with self.subTest(available=available), TestClient(create_app(readiness=lambda _: available), base_url="http://localhost") as client:
                response = client.get("/health/ready")
                self.assertEqual(response.status_code, status)
                self.assertEqual(set(response.json()), {"service", "database", "ai_mode"})

    def test_default_deny_and_no_proxy_test_routes_on_real_database(self):
        with TestClient(create_app(), base_url="http://localhost") as client:
            for path in ("/funds", "/docs", "/openapi.json", "/__test__/login", "/unknown"):
                self.assertEqual(client.get(path).status_code, 401, path)

    def test_host_allowlist(self):
        with TestClient(create_app(), base_url="http://evil.example") as client:
            self.assertEqual(client.get("/health/live").status_code, 400)

    def test_cookie_and_csrf_for_both_loopback_origins(self):
        config = Settings.from_env({"P50K_TEST_ENDPOINTS": "true", "P50K_DB_NAME": "p50k_dev"})
        for origin in ("http://127.0.0.1:3071", "http://localhost:3071"):
            with self.subTest(origin=origin), TestClient(create_app(config), base_url="http://localhost") as client:
                response = client.post("/__test__/login", headers={"Origin": origin})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(len(response.headers.get_list("set-cookie")), 2)
                csrf = response.json()["csrf"]
                self.assertEqual(client.post("/__test__/csrf", headers={"Origin": origin, "X-CSRF-Token": csrf}).status_code, 200)
                self.assertEqual(client.post("/__test__/csrf", headers={"Origin": origin}).status_code, 403)
                self.assertEqual(client.post("/__test__/csrf", headers={"X-CSRF-Token": csrf}).status_code, 403)
                self.assertEqual(client.post("/__test__/csrf", headers={"Origin": "http://evil.example:3071", "X-CSRF-Token": csrf}).status_code, 403)

    def test_sse_has_ten_separate_events(self):
        config = Settings.from_env({"P50K_TEST_ENDPOINTS": "true", "P50K_DB_NAME": "p50k_dev"})
        with TestClient(create_app(config), base_url="http://localhost") as client:
            response = client.get("/__test__/sse")
            self.assertEqual(response.headers["x-accel-buffering"], "no")
            self.assertEqual(response.text.count("event: probe"), 10)


if __name__ == "__main__":
    unittest.main()
