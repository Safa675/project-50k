"""Synthetic session, CSRF, expiry, revocation and login throttling checks."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import contextlib
import io
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from uuid import uuid4
from fastapi.testclient import TestClient
import psycopg
from pydantic import SecretStr
from p50k.product import auth_cli
from p50k.product.app import create_app
from p50k.product.auth import (AVATAR_PATH_PATTERN, AuthService, AuthenticationError, CSRF_COOKIE, SESSION_COOKIE,
    Principal, digest_token, hash_password, login_challenge, valid_login_challenge, verify_password)
from p50k.product.db import connect
from p50k.product.settings import Settings

MIGRATION_014 = Path(__file__).resolve().parents[2] / "db" / "migrations" / "014_user_avatar.sql"


class FakeConnection:
    """Records statements; an UPDATE returns the configured row."""
    def __init__(self, row=("00000000-0000-4000-8000-000000000001",)):
        self.row, self.calls = row, []

    def execute(self, statement, params=()):
        self.calls.append((" ".join(statement.split()), params))
        row = self.row if statement.startswith("UPDATE") else None
        return type("Cursor", (), {"fetchone": staticmethod(lambda: row)})()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

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


class LocalOpenModeTests(unittest.TestCase):
    """Single-user local mode: opt-in, off by default, one existing enabled user, no cookie or CSRF."""
    EMAIL = "synthetic-local@example.invalid"

    def client(self, **values):
        settings = Settings.from_env({"P50K_LOCAL_OPEN_EMAIL": self.EMAIL} if values.get("enabled", True) else {})
        return TestClient(create_app(settings, readiness=lambda _: True), base_url="http://127.0.0.1:3071")

    def test_mode_is_off_unless_explicitly_configured(self):
        self.assertEqual(Settings.from_env({}).local_open_email, "")
        self.assertEqual(Settings().local_open_email, "")
        with self.client(enabled=False) as client:
            self.assertEqual(client.get("/auth/me").status_code, 401)

    def test_configured_email_is_normalized_and_validated(self):
        self.assertEqual(Settings.from_env({"P50K_LOCAL_OPEN_EMAIL": " Local@Example.Invalid "}).local_open_email,
                         "local@example.invalid")
        with self.assertRaises(ValueError):
            Settings.from_env({"P50K_LOCAL_OPEN_EMAIL": "not-an-email"})

    def test_requests_act_as_the_local_user_without_cookie_or_csrf(self):
        principal = Principal(str(uuid4()), self.EMAIL, "admin", "local-open-mode", "", None)
        with patch("p50k.product.auth.AuthService.local_principal", return_value=principal) as lookup, \
                patch("p50k.product.auth.AuthService.authenticate") as authenticate, \
                self.client() as client:
            me = client.get("/auth/me")
            self.assertEqual(me.status_code, 200, me.text)
            self.assertEqual(me.json()["user"]["email"], self.EMAIL)
            self.assertEqual(me.json()["user"]["role"], "admin")
            # A mutating request without session or CSRF cookie reaches validation instead of 401/403.
            self.assertEqual(client.post("/auth/password", json={}).status_code, 422)
            self.assertEqual(client.post("/auth/logout").json(), {"logged_out": False, "local_open": True})
        lookup.assert_called_with(self.EMAIL)
        authenticate.assert_not_called()

    def test_missing_local_user_fails_closed_with_service_unavailable(self):
        with patch("p50k.product.auth.connect", return_value=FakeConnection()), self.client() as client:
            response = client.get("/auth/me")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"error": "LOCAL_USER_MISSING"})

    def test_local_principal_reads_one_enabled_user_by_normalized_email(self):
        user_id = str(uuid4())
        connection = FakeConnection()
        connection.execute = lambda statement, params=(): (
            connection.calls.append((" ".join(statement.split()), params)),
            type("Cursor", (), {"fetchone": staticmethod(lambda: (user_id, self.EMAIL, "analyst", None))})())[1]
        with patch("p50k.product.auth.connect", return_value=connection):
            principal = AuthService(Settings()).local_principal("  " + self.EMAIL.upper() + " ")
        self.assertEqual((principal.user_id, principal.role, principal.avatar_path), (user_id, "analyst", None))
        statement, params = connection.calls[0]
        self.assertIn("disabled_at IS NULL", statement)
        self.assertEqual(params, (self.EMAIL,))


class AvatarUnitTests(unittest.TestCase):
    def test_avatar_paths_are_same_origin_static_files_only(self):
        for value in ("/avatars/mirza.jpg", "/avatars/a.png", "/avatars/team-1.webp", "/avatars/" + "a" * 40 + ".jpg"):
            self.assertTrue(AVATAR_PATH_PATTERN.fullmatch(value), value)
        for value in ("https://example.invalid/avatars/a.jpg", "//example.invalid/avatars/a.jpg", "/avatars/../a.jpg",
                      "/avatars/A.jpg", "/avatars/-a.jpg", "/avatars/a.gif", "/avatars/.jpg", "/avatars/a.jpg?x=1",
                      "/avatars/a.jpg\n", "/avatars/sub/a.jpg", "/design/a.jpg", "/avatars/" + "a" * 41 + ".jpg", ""):
            self.assertIsNone(AVATAR_PATH_PATTERN.fullmatch(value), value)

    def test_database_check_uses_the_same_pattern(self):
        self.assertIn("'" + AVATAR_PATH_PATTERN.pattern + "'", MIGRATION_014.read_text(encoding="utf-8"))

    def test_current_user_reports_avatar_path_or_null(self):
        token = "k" * 43
        for avatar in ("/avatars/mirza.jpg", None):
            with self.subTest(avatar=avatar):
                principal = Principal(str(uuid4()), "synthetic@example.invalid", "admin", "synthetic-session",
                                      digest_token(token), avatar)
                with patch("p50k.product.auth.AuthService.authenticate", return_value=principal), \
                        TestClient(create_app(Settings.from_env({}), readiness=lambda _: True),
                                   base_url="http://127.0.0.1:3071") as client:
                    client.cookies.set(SESSION_COOKIE, token)
                    response = client.get("/auth/me")
                self.assertEqual(response.status_code, 200, response.text)
                self.assertIn("avatar_path", response.json()["user"])
                self.assertEqual(response.json()["user"]["avatar_path"], avatar)
        legacy = Principal(str(uuid4()), "synthetic@example.invalid", "viewer", "synthetic-session", digest_token(token))
        self.assertIsNone(legacy.user()["avatar_path"])

    def test_set_avatar_updates_one_user_by_normalized_email_and_audits(self):
        connection = FakeConnection()
        user_id = auth_cli.set_avatar(connection, " Synthetic@Example.Invalid ", "/avatars/synthetic.jpg")
        self.assertEqual(user_id, connection.row[0])
        (update, update_params), (audit, audit_params) = connection.calls
        self.assertEqual(update, "UPDATE auth.users SET avatar_path=%s WHERE email=%s RETURNING user_id")
        self.assertEqual(update_params, ("/avatars/synthetic.jpg", "synthetic@example.invalid"))
        self.assertTrue(audit.startswith("INSERT INTO ops.audit_log"))
        self.assertEqual(audit_params, ("USER_AVATAR_SET", user_id))
        cleared = FakeConnection()
        auth_cli.set_avatar(cleared, "synthetic@example.invalid", None)
        self.assertEqual(cleared.calls[0][1], (None, "synthetic@example.invalid"))
        self.assertEqual(cleared.calls[1][1][0], "USER_AVATAR_CLEARED")

    def test_set_avatar_rejects_unknown_users_and_unsafe_paths_without_auditing(self):
        missing = FakeConnection(row=None)
        with self.assertRaises(LookupError):
            auth_cli.set_avatar(missing, "synthetic@example.invalid", "/avatars/synthetic.jpg")
        self.assertEqual(len(missing.calls), 1)
        unsafe = FakeConnection()
        with self.assertRaises(ValueError):
            auth_cli.set_avatar(unsafe, "synthetic@example.invalid", "https://example.invalid/a.jpg")
        self.assertEqual(unsafe.calls, [])

    def run_cli(self, *argv, settings=None, connection=None):
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch("p50k.product.auth_cli.Settings.from_env", return_value=settings or Settings(db_user="p50k_owner")) as from_env, \
                patch("p50k.product.auth_cli.connect", return_value=connection or FakeConnection()), \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = auth_cli.main(list(argv))
        return code, stdout.getvalue(), stderr.getvalue(), from_env

    def test_cli_sets_and_clears_with_the_owner_role_only(self):
        connection = FakeConnection()
        code, stdout, stderr, _ = self.run_cli("set-avatar", "--email", "synthetic@example.invalid",
                                               "--avatar-path", "/avatars/synthetic.jpg", connection=connection)
        self.assertEqual((code, stdout, stderr), (0, "Profile photo updated.\n", ""))
        self.assertEqual(connection.calls[0][1], ("/avatars/synthetic.jpg", "synthetic@example.invalid"))
        connection = FakeConnection()
        code, stdout, _, _ = self.run_cli("set-avatar", "--email", "synthetic@example.invalid", "--clear", connection=connection)
        self.assertEqual(code, 0)
        self.assertIn("cleared", stdout)
        self.assertEqual(connection.calls[0][1], (None, "synthetic@example.invalid"))
        connection = FakeConnection()
        code, _, stderr, _ = self.run_cli("set-avatar", "--email", "synthetic@example.invalid", "--avatar-path",
                                          "/avatars/synthetic.jpg", settings=Settings(db_user="p50k_app"), connection=connection)
        self.assertEqual((code, json.loads(stderr)), (1, {"error_class": "ValueError"}))
        self.assertEqual(connection.calls, [])

    def test_cli_rejects_bad_input_before_reading_settings(self):
        for argv in (("set-avatar", "--email", "synthetic@example.invalid"),
                     ("set-avatar", "--email", "synthetic@example.invalid", "--avatar-path", "/avatars/../x.jpg"),
                     ("create-user", "--email", "synthetic@example.invalid", "--avatar-path", "/avatars/synthetic.jpg")):
            with self.subTest(argv=argv):
                code, stdout, stderr, from_env = self.run_cli(*argv)
                self.assertEqual((code, stdout, json.loads(stderr)), (1, "", {"error_class": "ValueError"}))
                from_env.assert_not_called()
        code, _, stderr, _ = self.run_cli("set-avatar", "--email", "synthetic@example.invalid", "--clear",
                                          connection=FakeConnection(row=None))
        self.assertEqual((code, json.loads(stderr)), (1, {"error_class": "LookupError"}))


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

    def test_new_user_has_no_avatar_and_the_application_role_cannot_set_one(self):
        principal, token, _ = self.service.login(self.email, self.password, uuid4().hex)
        self.assertIsNone(principal.avatar_path)
        self.assertIsNone(self.service.authenticate(token).user()["avatar_path"])
        with self.assertRaises(psycopg.errors.InsufficientPrivilege), connect(self.settings) as connection:
            connection.execute("UPDATE auth.users SET avatar_path='/avatars/synthetic.jpg' WHERE user_id=%s", (principal.user_id,))

    def test_disabled_user_cannot_use_existing_session(self):
        principal, token, _ = self.service.login(self.email, self.password, uuid4().hex)
        with connect(self.settings) as connection:
            connection.execute("UPDATE auth.users SET disabled_at=clock_timestamp() WHERE user_id=%s", (principal.user_id,))
        with self.assertRaises(AuthenticationError):
            self.service.authenticate(token)

if __name__ == "__main__":
    unittest.main()
