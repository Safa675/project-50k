from __future__ import annotations

import io
import logging
from pathlib import Path
import tempfile
import unittest

from p50k.product.logging import RedactingFormatter, redact
from p50k.product.settings import Settings


class ProductSettingsTests(unittest.TestCase):
    def test_test_endpoints_require_isolated_database(self):
        with self.assertRaisesRegex(ValueError, "isolated"):
            Settings.from_env({"P50K_TEST_ENDPOINTS": "true"})
        settings = Settings.from_env({"P50K_TEST_ENDPOINTS": "true", "P50K_DB_NAME": "p50k_dev"})
        self.assertTrue(settings.test_endpoints)

    def test_ai_modes_are_explicit_and_mock_requires_development_database(self):
        self.assertEqual(Settings.from_env({}).ai_mode, "off")
        self.assertEqual(Settings.from_env({"P50K_AI_MODE":"live"}).ai_mode, "live")
        with self.assertRaises(ValueError):
            Settings.from_env({"P50K_AI_MODE":"mock"})
        self.assertEqual(Settings.from_env({"P50K_AI_MODE":"mock","P50K_DB_NAME":"p50k_dev"}).ai_mode, "mock")
        with self.assertRaises(ValueError):
            Settings.from_env({"P50K_AI_MODE":"invalid"})

    def test_external_or_wildcard_hosts_and_origins_rejected(self):
        for env in ({"P50K_ALLOWED_HOSTS": "*"}, {"P50K_ALLOWED_HOSTS": "evil.example"}, {"P50K_ALLOWED_ORIGINS": "http://evil.example:3070"}, {"P50K_ALLOWED_ORIGINS": "http://localhost:3070/path"}):
            with self.subTest(env=env), self.assertRaises(ValueError):
                Settings.from_env(env)

    def test_loopback_origins_allowed(self):
        settings = Settings.from_env({})
        self.assertIn("http://localhost:3070", settings.allowed_origins)
        self.assertIn("http://127.0.0.1:3070", settings.allowed_origins)

    def test_credentials_are_lazy_and_secret_repr(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic-password"
            settings = Settings.from_env({"P50K_DB_PASSWORD_FILE": str(path)})
            path.write_text("synthetic-credential-for-tests-only", encoding="utf-8")
            self.assertNotIn("synthetic-credential", repr(settings.database_password()))
            self.assertEqual(settings.connect_kwargs()["password"], "synthetic-credential-for-tests-only")


class ProductRedactionTests(unittest.TestCase):
    def test_nested_private_fields_and_embedded_credentials_redacted(self):
        result = redact({"body": "private question", "nested": {"email": "person@example.invalid"}, "event": "password=synthetic bearer example-token postgresql://app:synthetic@db/db sk-synthetic-test-value"})
        self.assertEqual(result["body"], "[REDACTED]")
        self.assertEqual(result["nested"]["email"], "[REDACTED]")
        self.assertNotIn("example-token", result["event"])
        self.assertNotIn(":synthetic@", result["event"])
        self.assertNotIn("sk-synthetic", result["event"])

    def test_exception_details_are_not_logged(self):
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(RedactingFormatter())
        logger = logging.Logger("synthetic")
        logger.addHandler(handler)
        try:
            raise ValueError("private chat and password details")
        except ValueError:
            logger.exception("operation_failed")
        output = stream.getvalue()
        self.assertIn('"error_class": "ValueError"', output)
        self.assertNotIn("private chat", output)

    def test_structured_arguments_are_redacted_before_interpolation(self):
        record = logging.LogRecord("synthetic", logging.INFO, "test", 1, "request %s", ({"body": "private prompt", "password": "synthetic-private"},), None)
        output = RedactingFormatter().format(record)
        self.assertNotIn("private prompt", output)
        self.assertNotIn("synthetic-private", output)


if __name__ == "__main__":
    unittest.main()
