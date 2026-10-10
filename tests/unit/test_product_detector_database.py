"""Immutable v2 detector records and point-in-time guards in isolated PostgreSQL."""
from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
import hashlib
import os
from pathlib import Path
import unittest
from uuid import uuid4

try:
    import psycopg
    from psycopg import sql
    from psycopg.types.json import Jsonb
    from p50k.product.db import connect
    from p50k.product.migrate import run_migrations
    from p50k.product.settings import Settings
except ImportError:
    psycopg = None


@unittest.skipUnless(psycopg is not None and os.environ.get("P50K_TEST_DATABASE") == "1",
                     "requires isolated PostgreSQL p50k_dev")
class DetectorDatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.settings = Settings.from_env()
        if cls.settings.db_name != "p50k_dev" or cls.settings.db_user != "p50k_owner":
            raise RuntimeError("Detector integration tests require owner access to isolated p50k_dev")
        cls.app_settings = replace(
            cls.settings, db_user="p50k_app", db_password_file=Path(os.environ["P50K_APP_PASSWORD_FILE"]),
        )
        with connect(cls.settings, autocommit=True) as connection:
            run_migrations(connection, app_password=cls.app_settings.database_password().get_secret_value())

    def setUp(self) -> None:
        self.owner = connect(self.settings, autocommit=True)
        self.app = connect(self.app_settings, autocommit=True)
        self.addCleanup(self.app.close)
        self.addCleanup(self.owner.close)
        self.code = "TST" + uuid4().hex[:9].upper()
        self.sha = hashlib.sha256(self.code.encode()).hexdigest()
        self.version_id = "synthetic-v2-" + uuid4().hex
        self.protocol = "synthetic-detector-protocol-v2"
        self.app.execute(
            "INSERT INTO ref.funds (fund_code,name,source_sha256) VALUES (%s,'Synthetic fund',%s)",
            (self.code, self.sha),
        )
        self.version()

    def version(self, *, version_id: str | None = None, protocol: str | None = None) -> str:
        version_id = version_id or self.version_id
        self.app.execute("""
            INSERT INTO det.detector_versions (version_id,protocol_version,protocol_sha256,
                code_sha256,parameters,thresholds,calibration_input_sha256,calibration_cutoff)
            VALUES (%s,%s,%s,%s,%s,%s,%s,'2025-10-05T21:00:00Z')
        """, (version_id, protocol or self.protocol, self.sha, self.sha,
              Jsonb({"fixture": "synthetic", "rights_status": "UNREVIEWED", "development_result": True}),
              Jsonb({"Synthetic category": {"D1": "0.2"}}), self.sha))
        return version_id

    def create_run(self, *, origin: str = "SYNTHETIC", cutoff: str = "2030-02-01T12:00:00Z"):
        return self.app.execute("""
            INSERT INTO det.detector_runs (protocol_version,protocol_sha256,origin,cutoff,parameters)
            VALUES (%s,%s,%s,%s,'{"fixture":"synthetic"}'::jsonb) RETURNING run_id
        """, (self.protocol, self.sha, origin, cutoff)).fetchone()[0]

    def evidence(self, run_id, *, detector: str = "D1", state: str = "TRIGGERED",
                 origin: str = "SYNTHETIC", available: str | None = "2030-01-31T12:00:00Z",
                 effective_date: str | None = "2030-01-31", triggered: bool | None = True) -> str:
        evidence_id = "synthetic:" + uuid4().hex
        self.app.execute("""
            INSERT INTO det.evidence_items (evidence_id,fund_code,run_id,detector_id,origin,
                effective_date,available_at,unit,values,thresholds,triggered,state,source_references,metadata)
            VALUES (%s,%s,%s,%s,%s,%s,%s,'synthetic statistic',%s,%s,%s,%s,%s,%s)
        """, (evidence_id, self.code, run_id, detector, origin, effective_date, available,
              Jsonb({"value": "0.3"}), Jsonb({"threshold": "0.2"}), triggered, state,
              Jsonb([{"source": "SYNTHETIC", "sha256": self.sha}]),
              Jsonb({"is_attribute": detector == "D5"})))
        return evidence_id

    def signal(self, run_id, evidence_id: str, *, detector: str = "D1", state: str = "TRIGGERED",
               value: Decimal | None = Decimal("0.3"), threshold: Decimal | None = Decimal("0.2"),
               as_of: str = "2030-01-31", development_result: bool = True) -> None:
        self.app.execute("""
            INSERT INTO det.signals (run_id,fund_code,detector_id,state,reason,value,threshold,
                evidence_id,as_of,development_result)
            VALUES (%s,%s,%s,%s,'Synthetic coverage reason',%s,%s,%s,%s,%s)
        """, (run_id, self.code, detector, state, value, threshold, evidence_id, as_of, development_result))

    def finish(self, run_id, *, fingerprint: str | None = None, version_id: str | None = None,
               origin: str = "SYNTHETIC", cutoff: str = "2030-02-01T12:00:00Z",
               watermark: str | None = "2030-01-31T12:00:00Z", as_of: str = "2030-01-31",
               complete: bool = True) -> None:
        self.app.execute("""
            INSERT INTO det.run_inputs (run_id,version_id,input_sha256,input_watermark,
                as_of,origin,cutoff,complete) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (run_id, version_id or self.version_id, fingerprint or self.sha,
              watermark, as_of, origin, cutoff, complete))

    def test_repeat_input_is_unique_and_changed_input_retains_old_run(self) -> None:
        first = self.create_run()
        first_evidence = self.evidence(first)
        self.signal(first, first_evidence)
        self.finish(first)
        repeated = self.create_run()
        with self.assertRaises(psycopg.errors.UniqueViolation):
            self.finish(repeated)
        changed = self.create_run()
        changed_sha = hashlib.sha256((self.sha + "changed-input").encode()).hexdigest()
        self.finish(changed, fingerprint=changed_sha)
        self.assertEqual(self.app.execute(
            "SELECT count(*) FROM det.run_inputs WHERE version_id=%s", (self.version_id,),
        ).fetchone()[0], 2)
        self.assertEqual(self.app.execute(
            "SELECT evidence_id,value,threshold FROM det.signals WHERE run_id=%s", (first,),
        ).fetchone(), (first_evidence, Decimal("0.3"), Decimal("0.2")))

    def test_current_and_replay_input_identities_remain_separate(self) -> None:
        current = self.create_run(origin="DELAYED")
        replay = self.create_run(origin="HISTORICAL_REPLAY")
        self.finish(current, origin="DELAYED")
        self.finish(replay, origin="HISTORICAL_REPLAY")
        rows = self.app.execute(
            "SELECT origin FROM det.run_inputs WHERE version_id=%s ORDER BY origin", (self.version_id,),
        ).fetchall()
        self.assertEqual(rows, [("DELAYED",), ("HISTORICAL_REPLAY",)])

    def test_future_or_unknown_trigger_availability_is_rejected(self) -> None:
        run_id = self.create_run(origin="HISTORICAL_REPLAY")
        for available, effective in (("2030-02-01T12:00:01Z", "2030-01-31"),
                                     ("2030-01-31T12:00:00Z", "2030-02-02"),
                                     (None, "2030-01-31")):
            with self.subTest(available=available, effective=effective), \
                    self.assertRaises(psycopg.errors.CheckViolation):
                self.evidence(run_id, origin="HISTORICAL_REPLAY", available=available,
                              effective_date=effective)
        self.evidence(run_id, origin="HISTORICAL_REPLAY", available="2030-02-01T12:00:00Z")

    def test_istanbul_date_boundary_is_used_for_daily_evidence(self) -> None:
        run_id = self.create_run(cutoff="2030-02-01T22:30:00Z")
        evidence_id = self.evidence(run_id, effective_date="2030-02-02",
                                    available="2030-02-01T22:00:00Z")
        self.signal(run_id, evidence_id, as_of="2030-02-02")
        self.finish(run_id, cutoff="2030-02-01T22:30:00Z", as_of="2030-02-02",
                    watermark="2030-02-01T22:00:00Z")

    def test_abstention_preserves_null_and_age_is_an_attribute(self) -> None:
        run_id = self.create_run()
        missing = self.evidence(run_id, state="ABSTAINED", triggered=None, available=None,
                                effective_date=None)
        self.signal(run_id, missing, state="ABSTAINED", value=None, threshold=None)
        age = self.evidence(run_id, detector="D5", state="NOT_TRIGGERED", triggered=False)
        self.signal(run_id, age, detector="D5", state="NOT_TRIGGERED", value=Decimal("20"), threshold=None)
        self.finish(run_id, watermark=None)
        rows = self.app.execute("""
            SELECT signal.detector_id,signal.state,signal.value,signal.threshold,
                evidence.triggered,evidence.metadata->>'is_attribute'
            FROM det.signals signal JOIN det.evidence_items evidence USING(evidence_id)
            WHERE signal.run_id=%s ORDER BY signal.detector_id
        """, (run_id,)).fetchall()
        self.assertEqual(rows, [("D1", "ABSTAINED", None, None, None, "false"),
                                ("D5", "NOT_TRIGGERED", Decimal("20"), None, False, "true")])

    def test_evidence_state_boolean_origin_and_signal_binding_are_enforced(self) -> None:
        first, other = self.create_run(), self.create_run()
        for state, triggered, origin in (("UNKNOWN", None, "SYNTHETIC"),
                                         ("ABSTAINED", False, "SYNTHETIC"),
                                         ("TRIGGERED", False, "SYNTHETIC"),
                                         ("NOT_TRIGGERED", None, "SYNTHETIC"),
                                         ("TRIGGERED", True, "DELAYED")):
            with self.subTest(state=state, triggered=triggered, origin=origin), \
                    self.assertRaises(psycopg.errors.CheckViolation):
                self.evidence(first, state=state, triggered=triggered, origin=origin)
        evidence_id = self.evidence(first)
        for run_id, detector, state in ((other, "D1", "TRIGGERED"),
                                        (first, "D2", "TRIGGERED"),
                                        (first, "D1", "NOT_TRIGGERED")):
            with self.subTest(run_id=run_id, detector=detector, state=state), \
                    self.assertRaises(psycopg.errors.CheckViolation):
                self.signal(run_id, evidence_id, detector=detector, state=state)

    def test_finalization_requires_registered_version_cutoff_and_origin(self) -> None:
        run_id = self.create_run()
        different_version = self.version(version_id="synthetic-mismatch-" + uuid4().hex,
                                         protocol="synthetic-other-protocol")
        attempts = ({"version_id": different_version}, {"origin": "DELAYED"},
                    {"cutoff": "2030-02-01T11:00:00Z"}, {"watermark": "2030-02-01T12:00:01Z"},
                    {"as_of": "2030-02-02"}, {"complete": False})
        for options in attempts:
            with self.subTest(options=options), self.assertRaises(psycopg.errors.CheckViolation):
                self.finish(run_id, **options)
        self.finish(run_id)

    def test_nonfinite_values_and_non_development_results_are_rejected(self) -> None:
        run_id = self.create_run()
        evidence_id = self.evidence(run_id)
        for value in (Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")):
            for field in ("value", "threshold"):
                with self.subTest(value=value, field=field), self.assertRaises(psycopg.errors.CheckViolation):
                    self.signal(run_id, evidence_id, **{field: value})
        with self.assertRaises(psycopg.errors.CheckViolation):
            self.signal(run_id, evidence_id, development_result=False)
        self.signal(run_id, evidence_id)

    def test_versions_inputs_signals_and_evidence_are_append_only(self) -> None:
        run_id = self.create_run()
        evidence_id = self.evidence(run_id)
        self.signal(run_id, evidence_id)
        self.finish(run_id)
        records = (("detector_versions", "version_id", self.version_id),
                   ("run_inputs", "run_id", run_id), ("signals", "run_id", run_id),
                   ("evidence_items", "evidence_id", evidence_id))
        for table, key, identity in records:
            identifier, column = sql.Identifier("det", table), sql.Identifier(key)
            for operation in (sql.SQL("UPDATE {} SET {}={} WHERE {}=%s").format(
                    identifier, column, column, column),
                    sql.SQL("DELETE FROM {} WHERE {}=%s").format(identifier, column)):
                with self.subTest(table=table, role="app"), \
                        self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    self.app.execute(operation, (identity,))
                with self.subTest(table=table, role="owner"), \
                        self.assertRaises(psycopg.errors.ObjectNotInPrerequisiteState):
                    self.owner.execute(operation, (identity,))
            with self.subTest(table=table, operation="truncate"), \
                    self.assertRaises(psycopg.errors.ObjectNotInPrerequisiteState):
                self.owner.execute(sql.SQL("TRUNCATE {} CASCADE").format(identifier))

    def test_failed_batch_does_not_become_a_complete_run(self) -> None:
        before = self.app.execute("SELECT count(*) FROM det.detector_runs").fetchone()[0]
        with self.assertRaises(psycopg.errors.CheckViolation):
            with self.app.transaction():
                run_id = self.create_run()
                evidence_id = self.evidence(run_id)
                self.signal(run_id, evidence_id, state="NOT_TRIGGERED")
                self.finish(run_id)
        self.assertEqual(self.app.execute("SELECT count(*) FROM det.detector_runs").fetchone()[0], before)
        self.assertEqual(self.app.execute(
            "SELECT count(*) FROM det.run_inputs WHERE version_id=%s", (self.version_id,),
        ).fetchone()[0], 0)

    def test_complete_run_rejects_later_evidence_and_signals_for_every_role(self) -> None:
        run_id = self.create_run()
        existing_evidence = self.evidence(run_id)
        self.finish(run_id)
        for connection in (self.app, self.owner):
            with self.subTest(role=connection.info.user, record="evidence"), \
                    self.assertRaises(psycopg.errors.ObjectNotInPrerequisiteState):
                connection.execute("""
                    INSERT INTO det.evidence_items (evidence_id,fund_code,run_id,detector_id,
                        origin,available_at,unit,values,triggered,state,source_references)
                    VALUES (%s,%s,%s,'D2','SYNTHETIC','2030-01-31T12:00:00Z',
                        'synthetic statistic','{}'::jsonb,false,'NOT_TRIGGERED','[]'::jsonb)
                """, ("synthetic:" + uuid4().hex, self.code, run_id))
            with self.subTest(role=connection.info.user, record="signal"), \
                    self.assertRaises(psycopg.errors.ObjectNotInPrerequisiteState):
                connection.execute("""
                    INSERT INTO det.signals (run_id,fund_code,detector_id,state,reason,
                        evidence_id,as_of) VALUES (%s,%s,'D1','TRIGGERED',
                        'Synthetic late append',%s,'2030-01-31')
                """, (run_id, self.code, existing_evidence))
        self.assertEqual(self.app.execute(
            "SELECT count(*) FROM det.evidence_items WHERE run_id=%s", (run_id,),
        ).fetchone()[0], 1)
        self.assertEqual(self.app.execute(
            "SELECT count(*) FROM det.signals WHERE run_id=%s", (run_id,),
        ).fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
