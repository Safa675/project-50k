"""Synthetic session, CSRF, expiry, revocation and login throttling checks."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4
from fastapi.testclient import TestClient
from pydantic import SecretStr
from p50k.product.app import create_app
from p50k.product.auth import (AuthService, AuthenticationError, CSRF_COOKIE, SESSION_COOKIE,
    digest_token, hash_password, login_challenge, valid_login_challenge, verify_password)
from p50k.product.db import connect
from p50k.product.settings import Settings

class AuthUnitTests(unittest.TestCase):
    def test_password_is_argon2id_with_pepper_and_wrong_values_fail(self):
        pepper = SecretStr("synthetic-pepper-value-long-enough-for-test")
        value = SecretStr("synthetic-password-value")
        stored = hash_password(value, pepper)
        self.assertTrue(stored.startswith("$argon2id$"))
        self.assertTrue(verify_password(stored, value, pepper))
        self.assertFalse(verify_password(stored, SecretStr("synthetic-other-password"), pepper))
        self.assertFalse(verify_password(stored, value, SecretStr("different-pepper")))

    def test_signed_login_challenge_cannot_be_forged_or_replayed_after_expiry(self):
        pepper, now = SecretStr("synthetic-pepper"), datetime.now(timezone.utc)
        challenge = login_challenge(pepper, now)
        self.assertTrue(valid_login_challenge(challenge, pepper, now))
        self.assertFalse(valid_login_challenge(challenge + "x", pepper, now))
        self.assertFalse(valid_login_challenge(challenge, pepper, now + timedelta(minutes=11)))

    def test_every_nonpublic_route_denies_anonymous_clients(self):
        with TestClient(create_app(Settings(), readiness=lambda _: True)) as client:
            for path in ("/funds", "/funds/THF", "/signals", "/events", "/docs", "/openapi.json", "/auth/me"):
                self.assertEqual(client.get(path).status_code, 401, path)
            self.assertEqual(client.post("/auth/logout").status_code, 401)


@unittest.skipUnless(os.environ.get("P50K_TEST_DATABASE") == "1", "Requires isolated p50k_dev")
class AuthDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.settings = Settings.from_env()
        self.assertEqual(self.settings.db_name, "p50k_dev")
        self.service = AuthService(self.settings)
        self.email = uuid4().hex + "@example.invalid"
        self.password = SecretStr("synthetic-password-value")
        with connect(self.settings) as connection:
            connection.execute("INSERT INTO auth.users(email,password_hash) VALUES (%s,%s)",
                (self.email, hash_password(self.password, self.settings.auth_pepper())))

    def test_login_rotation_logout_and_absolute_idle_expiry(self):
        now = datetime.now(timezone.utc)
        principal, token, csrf = self.service.login(self.email, self.password, uuid4().hex, now=now)
        self.assertEqual(self.service.authenticate(token, now + timedelta(minutes=1)).role, "viewer")
        with self.assertRaises(AuthenticationError):
            self.service.authenticate(token, now + timedelta(hours=3))
        principal2, token2, _ = self.service.login(self.email, self.password, uuid4().hex, previous_token=token, now=now)
        with self.assertRaises(AuthenticationError):
            self.service.authenticate(token, now)
        self.service.logout(principal2, now)
        with self.assertRaises(AuthenticationError):
            self.service.authenticate(token2, now)
        _, token3, _ = self.service.login(self.email, self.password, uuid4().hex, now=now)
        with self.assertRaises(AuthenticationError):
            self.service.authenticate(token3, now + timedelta(hours=13))
        self.assertNotEqual(token, csrf)

    def test_five_failed_attempts_persist_and_throttle(self):
        ip = uuid4().hex
        for _ in range(5):
            with self.assertRaises(AuthenticationError) as error:
                self.service.login(self.email, SecretStr("synthetic-incorrect-password"), ip)
            self.assertEqual(error.exception.status, 401)
        with self.assertRaises(AuthenticationError) as error:
            self.service.login(self.email, self.password, ip)
        self.assertEqual(error.exception.status, 429)

    def test_http_cookie_origin_csrf_and_password_change_revoke_sessions(self):
        with TestClient(create_app(self.settings, readiness=lambda _: True), base_url="http://localhost") as client:
            headers = {"Origin": "http://localhost:3071"}
            challenge = client.get("/auth/csrf").json()["csrf_token"]
            body = {"email": self.email, "password": self.password.get_secret_value()}
            self.assertEqual(client.post("/auth/login", json=body).status_code, 403)
            response = client.post("/auth/login", json=body, headers={**headers, "X-CSRF-Token": challenge})
            self.assertEqual(response.status_code, 200)
            self.assertIn("HttpOnly", response.headers.get_list("set-cookie")[0])
            self.assertEqual(client.get("/auth/me").status_code, 200)
            self.assertEqual(client.post("/auth/logout", headers=headers).status_code, 403)
            csrf = client.cookies.get(CSRF_COOKIE)
            token = client.cookies.get(SESSION_COOKIE)
            changed = client.post("/auth/password", json={"current_password": body["password"], "new_password": "synthetic-new-password"},
                                  headers={**headers, "X-CSRF-Token": csrf})
            self.assertEqual(changed.status_code, 200)
            with self.assertRaises(AuthenticationError):
                self.service.authenticate(token)

    def test_disabled_user_cannot_use_existing_session(self):
        principal, token, _ = self.service.login(self.email, self.password, uuid4().hex)
        with connect(self.settings) as connection:
            connection.execute("UPDATE auth.users SET disabled_at=clock_timestamp() WHERE user_id=%s", (principal.user_id,))
        with self.assertRaises(AuthenticationError):
            self.service.authenticate(token)

if __name__ == "__main__":
    unittest.main()
