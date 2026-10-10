"""Synthetic checks for T1.4; PostgreSQL integration is explicitly opt-in on p50k_dev."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import contextlib
import hashlib
import io
import os
import unittest
import uuid

try:
    import psycopg
    from psycopg import sql
    from psycopg.types.json import Jsonb
    from p50k.product.db import connect
    from p50k.product.migrate import (
        DEFAULT_DIRECTORY, Migration, MigrationError, load_migrations,
        main, pending_migrations, run_migrations,
    )
    from p50k.product.settings import Settings
except ImportError:
    psycopg = None


@unittest.skipIf(psycopg is None, "product extra is not installed")
class MigrationRegistrationTests(unittest.TestCase):
    def test_lf_bytes_are_registered_exactly(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            payload = b"SELECT 1;\n"
            (directory / "001_synthetic.sql").write_bytes(payload)
            migration, = load_migrations(directory)
            self.assertEqual(migration.sha256, hashlib.sha256(payload).hexdigest())
            self.assertEqual(migration.statement, "SELECT 1;\n")

    def test_crlf_bom_invalid_utf8_and_empty_files_are_rejected(self):
        for payload in (b"SELECT 1;\r\n", b"\xef\xbb\xbfSELECT 1;\n", b"\xff\n", b""):
            with self.subTest(payload=payload), TemporaryDirectory() as temporary:
                directory = Path(temporary)
                (directory / "001_synthetic.sql").write_bytes(payload)
                with self.assertRaises(MigrationError):
                    load_migrations(directory)

    def test_duplicate_versions_and_invalid_names_are_rejected(self):
        for names in (("001_first.sql", "001_second.sql"), ("migration.sql",)):
            with self.subTest(names=names), TemporaryDirectory() as temporary:
                directory = Path(temporary)
                for filename in names:
                    (directory / filename).write_bytes(b"SELECT 1;\n")
                with self.assertRaises(MigrationError):
                    load_migrations(directory)

    def test_registered_mutation_removal_and_old_insertion_are_rejected(self):
        first = Migration("001_first.sql", "a" * 64, "SELECT 1;")
        second = Migration("002_second.sql", "b" * 64, "SELECT 2;")
        with self.assertRaises(MigrationError):
            pending_migrations((first, second), {first.filename: "c" * 64})
        with self.assertRaises(MigrationError):
            pending_migrations((second,), {first.filename: first.sha256})
        with self.assertRaises(MigrationError):
            pending_migrations((first, second), {second.filename: second.sha256})
        self.assertEqual(pending_migrations((first, second), {first.filename: first.sha256}), (second,))

    def test_runtime_database_error_reports_only_the_class(self):
        with TemporaryDirectory() as temporary:
            credential_path = Path(temporary) / "synthetic-credential"
            credential_path.write_text("synthetic-runtime-credential-long-enough", encoding="utf-8")
            settings = Settings(db_user="p50k_owner")
            stderr = io.StringIO()
            with patch.dict(os.environ, {"P50K_APP_PASSWORD_FILE": str(credential_path)}), \
                    patch("p50k.product.migrate.Settings.from_env", return_value=settings), \
                    patch("p50k.product.migrate.connect", side_effect=psycopg.OperationalError("sensitive-runtime-detail")), \
                    contextlib.redirect_stderr(stderr):
                self.assertEqual(main([]), 1)
            self.assertEqual(stderr.getvalue(), "Migration failed: OperationalError\n")
            self.assertNotIn("sensitive-runtime-detail", stderr.getvalue())


@unittest.skipUnless(psycopg is not None and os.environ.get("P50K_TEST_DATABASE") == "1",
                     "requires the isolated p50k_dev PostgreSQL smoke database")
class PostgreSQLFoundationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.settings = Settings.from_env()
        if cls.settings.db_name != "p50k_dev" or cls.settings.db_user != "p50k_owner":
            raise RuntimeError("Integration checks require owner access to the isolated p50k_dev database")
        app_path = Path(os.environ["P50K_APP_PASSWORD_FILE"])
        app_password = app_path.read_text(encoding="utf-8").strip()
        cls.app_settings = replace(cls.settings, db_user="p50k_app", db_password_file=app_path)
        with connect(cls.settings, autocommit=True) as connection:
            run_migrations(connection, app_password=app_password)

    def setUp(self):
        self.owner = connect(self.settings, autocommit=True)
        self.app = connect(self.app_settings, autocommit=True)
        self.addCleanup(self.app.close)
        self.addCleanup(self.owner.close)
        self.code = "TST" + uuid.uuid4().hex[:9].upper()
        self.sha = hashlib.sha256(self.code.encode()).hexdigest()
        self.app.execute(
            "INSERT INTO ref.funds (fund_code, name, source_sha256) VALUES (%s, %s, %s)",
            (self.code, "Synthetic fund", self.sha),
        )
        self.user_id = self.owner.execute(
            "INSERT INTO auth.users (email, password_hash, role) VALUES (%s, %s, 'analyst') RETURNING user_id",
            (uuid.uuid4().hex + "@example.invalid", "synthetic-not-an-authenticator"),
        ).fetchone()[0]

    def packet(self, *, suffix="first", origin="SYNTHETIC", cutoff=None, options=None):
        packet_sha = hashlib.sha256((self.code + suffix).encode()).hexdigest()
        packet_id = self.app.execute("""
            INSERT INTO ai.packets (fund_code, packet_sha256, origin, cutoff, payload, allowed_options)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING packet_id
        """, (self.code, packet_sha, origin, cutoff, Jsonb({"fixture": "synthetic"}),
              Jsonb(options or ["MATERIAL", "NOT_MATERIAL", "DATA_ISSUE", "INSUFFICIENT_EVIDENCE"]))).fetchone()[0]
        return packet_id, packet_sha

    def decision(self, packet, *, value="MATERIAL", method="SINGLE", validation="VALID"):
        packet_id, packet_sha = packet
        return self.app.execute("""
            INSERT INTO ai.decisions (packet_id, fund_code, packet_sha256, decision_value,
                validation_state, evidence_ids, model_id, prompt_version, schema_version,
                ai_mode, method, call_id)
            VALUES (%s, %s, %s, %s, %s, %s, 'synthetic-model', 'synthetic-v1', 'synthetic-v1',
                'mock', %s, %s) RETURNING decision_id
        """, (packet_id, self.code, packet_sha, value, validation, Jsonb(["synthetic-evidence"]),
              method, uuid.uuid4().hex)).fetchone()[0]

    def review(self, decision_id, packet, *, action="OVERRIDE", value="NOT_MATERIAL"):
        return self.app.execute("""
            INSERT INTO ai.decision_reviews (decision_id, packet_sha256, action, override_value,
                reason, reviewer_id) VALUES (%s, %s, %s, %s, 'Synthetic review reason', %s)
            RETURNING review_id
        """, (decision_id, packet[1], action, value, self.user_id)).fetchone()[0]

    def effective(self, *, origin="SYNTHETIC"):
        return self.app.execute("""
            SELECT effective_value, effective_source, review_id, stale_review_exists, has_current_review
            FROM ai.effective_decisions WHERE fund_code = %s AND origin = %s
        """, (self.code, origin)).fetchone()

    def test_owner_roles_and_application_privileges(self):
        roles = self.owner.execute("""
            SELECT rolsuper, rolcreatedb, rolcreaterole, rolbypassrls
            FROM pg_roles WHERE rolname = 'p50k_app'
        """).fetchone()
        self.assertEqual(roles, (False, False, False, False))
        owners = self.owner.execute("""
            SELECT DISTINCT pg_get_userbyid(c.relowner) FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname IN ('ref', 'obs', 'det', 'ai', 'auth', 'b2b', 'ops')
                AND c.relkind IN ('r', 'p')
        """).fetchall()
        self.assertEqual(owners, [("p50k_owner",)])
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):
            self.app.execute("SET ROLE p50k_owner")
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):
            self.app.execute("UPDATE auth.users SET role = 'admin' WHERE user_id = %s", (self.user_id,))
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):
            self.app.execute("INSERT INTO auth.users (email, password_hash, role) VALUES ('synthetic@example.invalid', 'synthetic', 'admin')")

    def test_decimal_missing_and_versioned_provenance_round_trip(self):
        value = Decimal("12.345678901234567890123456789")
        insert = """
            INSERT INTO obs.fund_prices (fund_code, effective_date, nav, source_sha256,
                origin, availability_rule) VALUES (%s, %s, %s, %s, 'SYNTHETIC', 'synthetic-unknown')
            ON CONFLICT DO NOTHING
        """
        self.app.execute(insert, (self.code, "2026-01-01", value, self.sha))
        self.app.execute(insert, (self.code, "2026-01-01", value, self.sha))
        self.app.execute(insert, (self.code, "2026-01-02", None, self.sha))
        revised_sha = hashlib.sha256((self.sha + "revision").encode()).hexdigest()
        self.app.execute(insert, (self.code, "2026-01-01", Decimal("13.1"), revised_sha))
        rows = self.app.execute("""
            SELECT nav, published_at, available_at, observed_at, rights_status, unit
            FROM obs.fund_prices WHERE fund_code = %s ORDER BY effective_date, nav
        """, (self.code,)).fetchall()
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0][0], value)
        self.assertEqual(rows[2][0], None)
        for row in rows:
            self.assertEqual(row[1:5], (None, None, None, "UNREVIEWED"))
            self.assertEqual(row[5], "NAV/unit (currency unreported)")
        for bad in (Decimal("0"), Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")):
            with self.subTest(value=bad), self.assertRaises(psycopg.errors.CheckViolation):
                self.app.execute(insert, (self.code, "2026-01-03", bad, self.sha))

    def test_unknown_snapshot_date_and_timestamps_are_not_filled(self):
        self.app.execute("""
            INSERT INTO obs.fund_snapshots (fund_code, snapshot_key, source_sha256, origin,
                observed_at, availability_rule) VALUES (%s, 'synthetic-snapshot', %s, 'SYNTHETIC',
                '2026-01-02T12:00:00Z', 'synthetic-no-as-of')
        """, (self.code, self.sha))
        row = self.app.execute("""
            SELECT effective_date, nav, published_at, available_at,
                observed_at = '2026-01-02T12:00:00Z'::timestamptz
            FROM obs.fund_snapshots WHERE fund_code = %s
        """, (self.code,)).fetchone()
        self.assertEqual(row, (None, None, None, None, True))

    def test_append_only_application_and_owner_guards(self):
        packet = self.packet()
        decision_id = self.decision(packet)
        review_id = self.review(decision_id, packet)
        evidence_id = "synthetic:" + self.code
        self.app.execute("""
            INSERT INTO det.evidence_items (evidence_id, fund_code, detector_id, origin, unit,
                values, state, source_references) VALUES (%s, %s, 'synthetic-detector', 'SYNTHETIC',
                'synthetic unit', '{}'::jsonb, 'UNKNOWN', '[]'::jsonb)
        """, (evidence_id, self.code))
        audit_id = self.app.execute("""
            INSERT INTO ops.audit_log (action, target_type, target_id)
            VALUES ('synthetic-check', 'synthetic', %s) RETURNING audit_id
        """, (self.code,)).fetchone()[0]
        records = (
            ("ai", "packets", "packet_id", packet[0]),
            ("ai", "decisions", "decision_id", decision_id),
            ("ai", "decision_reviews", "review_id", review_id),
            ("det", "evidence_items", "evidence_id", evidence_id),
            ("ops", "audit_log", "audit_id", audit_id),
        )
        for schema, table, key, value in records:
            identifier = sql.Identifier(schema, table)
            column = sql.Identifier(key)
            update = sql.SQL("UPDATE {} SET created_at = created_at WHERE {} = %s").format(identifier, column)
            delete = sql.SQL("DELETE FROM {} WHERE {} = %s").format(identifier, column)
            for statement in (update, delete):
                with self.subTest(table=table, role="app"), self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    self.app.execute(statement, (value,))
                with self.subTest(table=table, role="owner"), self.assertRaises(psycopg.errors.ObjectNotInPrerequisiteState):
                    self.owner.execute(statement, (value,))
        self.app.execute("""
            INSERT INTO obs.fund_prices (fund_code, effective_date, nav, source_sha256,
                origin, availability_rule) VALUES (%s, '2026-01-01', NULL, %s, 'SYNTHETIC', 'synthetic')
        """, (self.code, self.sha))
        with self.assertRaises(psycopg.errors.ObjectNotInPrerequisiteState):
            self.owner.execute("TRUNCATE obs.fund_prices")

    def test_human_review_survives_ai_methods_and_rejection_fails_closed(self):
        packet = self.packet()
        single_id = self.decision(packet)
        review_id = self.review(single_id, packet)
        self.decision(packet, method="TEAM")
        self.assertEqual(self.effective(), ("NOT_MATERIAL", "HUMAN", review_id, False, True))
        rejection_id = self.review(single_id, packet, action="REJECT", value=None)
        self.assertEqual(self.effective(), ("UNDECIDED", "HUMAN", rejection_id, False, True))
        self.packet(suffix="changed-evidence")
        self.assertEqual(self.effective(), ("UNDECIDED", "UNDECIDED", None, True, False))

    def test_latest_review_across_methods_wins(self):
        packet = self.packet()
        single_id = self.decision(packet)
        team_id = self.decision(packet, method="TEAM", value="DATA_ISSUE")
        self.review(team_id, packet, value="DATA_ISSUE")
        acceptance_id = self.review(single_id, packet, action="ACCEPT", value=None)
        self.assertEqual(self.effective(), ("MATERIAL", "HUMAN", acceptance_id, False, True))

    def test_replay_cutoff_does_not_replace_current_published_packet(self):
        current = self.packet(origin="DELAYED")
        decision_id = self.decision(current)
        review_id = self.review(decision_id, current)
        with self.assertRaises(psycopg.errors.CheckViolation):
            self.packet(suffix="missing-cutoff", origin="HISTORICAL_REPLAY")
        self.packet(suffix="earlier-replay", origin="HISTORICAL_REPLAY", cutoff="2026-01-01T11:00:00Z")
        self.assertEqual(self.effective(origin="DELAYED"), ("NOT_MATERIAL", "HUMAN", review_id, False, True))
        self.assertEqual(self.effective(origin="HISTORICAL_REPLAY"), ("UNDECIDED", "UNDECIDED", None, False, False))

    def test_invalid_or_disallowed_model_output_stays_undecided(self):
        packet = self.packet(options=["MATERIAL", "INSUFFICIENT_EVIDENCE"])
        with self.assertRaises(psycopg.errors.CheckViolation):
            self.decision(packet, value="NOT_MATERIAL")
        self.decision(packet, value=None, validation="INVALID")
        self.assertEqual(self.effective(), ("UNDECIDED", "UNDECIDED", None, False, False))
        with self.assertRaises(psycopg.errors.NotNullViolation):
            self.app.execute("""
                INSERT INTO ai.decisions (packet_id, fund_code, packet_sha256, validation_state,
                    evidence_ids, prompt_version, schema_version, ai_mode, call_id)
                VALUES (%s, %s, %s, 'INVALID', '[]'::jsonb, 'synthetic-v1', 'synthetic-v1', 'mock', 'synthetic')
            """, (packet[0], self.code, packet[1]))

    def test_changed_migration_is_rejected_before_pending_sql(self):
        app_password = self.app_settings.database_password().get_secret_value()
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            for path in DEFAULT_DIRECTORY.glob("*.sql"):
                (directory / path.name).write_bytes(path.read_bytes())
            original = directory / "001_foundations.sql"
            original.write_bytes(original.read_bytes() + b"\n-- synthetic mutation\n")
            (directory / "005_synthetic.sql").write_bytes(b"CREATE TABLE ops.synthetic_must_not_exist (value INTEGER);\n")
            with self.assertRaises(MigrationError):
                run_migrations(self.owner, directory=directory, app_password=app_password)
            self.assertIsNone(self.owner.execute("SELECT to_regclass('ops.synthetic_must_not_exist')").fetchone()[0])

    def test_sql_file_and_registration_roll_back_together(self):
        app_password = self.app_settings.database_password().get_secret_value()
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            for path in DEFAULT_DIRECTORY.glob("*.sql"):
                (directory / path.name).write_bytes(path.read_bytes())
            (directory / "005_synthetic_failure.sql").write_bytes(
                b"CREATE TABLE ops.synthetic_rollback (value INTEGER);\nSELECT 1 / 0;\n",
            )
            with self.assertRaises(psycopg.errors.DivisionByZero):
                run_migrations(self.owner, directory=directory, app_password=app_password)
            self.assertIsNone(self.owner.execute("SELECT to_regclass('ops.synthetic_rollback')").fetchone()[0])
            self.assertIsNone(self.owner.execute(
                "SELECT filename FROM ops.schema_migrations WHERE filename = '005_synthetic_failure.sql'",
            ).fetchone())

    def test_mock_and_synthetic_guards_outside_development_database(self):
        # This database is created only on the explicitly enabled isolated smoke server.
        database_name = "p50k_guard_test_" + uuid.uuid4().hex
        self.owner.execute(sql.SQL("CREATE DATABASE {} OWNER p50k_owner").format(sql.Identifier(database_name)))
        try:
            guard_settings = replace(self.settings, db_name=database_name, test_endpoints=False)
            app_password = self.app_settings.database_password().get_secret_value()
            with connect(guard_settings, autocommit=True) as connection:
                run_migrations(connection, app_password=app_password)
                connection.execute(
                    "INSERT INTO ref.funds (fund_code, name, source_sha256) VALUES (%s, 'Synthetic guard fixture', %s)",
                    (self.code, self.sha),
                )
                with self.assertRaises(psycopg.errors.CheckViolation):
                    connection.execute("""
                        INSERT INTO obs.fund_prices (fund_code, effective_date, source_sha256, origin,
                            availability_rule) VALUES (%s, '2026-01-01', %s, 'SYNTHETIC', 'synthetic')
                    """, (self.code, self.sha))
                with self.assertRaises(psycopg.errors.CheckViolation):
                    connection.execute("""
                        INSERT INTO ai.packets (fund_code, packet_sha256, origin, payload, allowed_options, ai_mode)
                        VALUES (%s, %s, 'DELAYED', '{}'::jsonb, '["MATERIAL"]'::jsonb, 'mock')
                    """, (self.code, self.sha))
                packet_id = connection.execute("""
                    INSERT INTO ai.packets (fund_code, packet_sha256, origin, payload, allowed_options)
                    VALUES (%s, %s, 'DELAYED', '{}'::jsonb, '["MATERIAL"]'::jsonb) RETURNING packet_id
                """, (self.code, self.sha)).fetchone()[0]
                with self.assertRaises(psycopg.errors.CheckViolation):
                    connection.execute("""
                        INSERT INTO ai.decisions (packet_id, fund_code, packet_sha256, decision_value,
                            validation_state, evidence_ids, model_id, prompt_version, schema_version, ai_mode, call_id)
                        VALUES (%s, %s, %s, 'MATERIAL', 'VALID', '[]'::jsonb, 'synthetic', 'synthetic',
                            'synthetic', 'mock', 'synthetic')
                    """, (packet_id, self.code, self.sha))
        finally:
            self.owner.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(database_name)))


if __name__ == "__main__":
    unittest.main()
