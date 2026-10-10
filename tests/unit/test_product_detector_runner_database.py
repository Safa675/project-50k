"""Actual detector CLI core against synthetic inputs in isolated PostgreSQL."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from uuid import uuid4

try:
    import psycopg
    from p50k.product import detector_pipeline as pipeline
    from p50k.product.db import connect
    from p50k.product.migrate import run_migrations
    from p50k.product.settings import Settings
except ImportError:
    psycopg = None


@unittest.skipUnless(psycopg is not None and os.environ.get("P50K_TEST_DATABASE") == "1",
                     "requires isolated PostgreSQL p50k_dev")
class DetectorRunnerDatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        settings = Settings.from_env()
        if settings.db_name != "p50k_dev" or settings.db_user != "p50k_owner":
            raise RuntimeError("Detector runner tests require owner access to isolated p50k_dev")
        cls.owner_settings = settings
        cls.app_settings = replace(
            settings, db_user="p50k_app", db_password_file=Path(os.environ["P50K_APP_PASSWORD_FILE"]),
        )
        with connect(settings, autocommit=True) as connection:
            run_migrations(connection, app_password=cls.app_settings.database_password().get_secret_value())

    def setUp(self) -> None:
        self.app = connect(self.app_settings, autocommit=True)
        self.addCleanup(self.app.close)
        self.code = "TST" + uuid4().hex[:9].upper()
        self.sha = hashlib.sha256(self.code.encode()).hexdigest()
        self.cutoff = datetime(2030, 2, 1, 12, tzinfo=timezone.utc)
        # Each synthetic test owns its calibration version. Production VERSION_ID
        # is unchanged, and this database never contains real provider values.
        self.version_id = "synthetic-runner-v2-" + uuid4().hex
        self.version_patch = patch.object(pipeline, "VERSION_ID", self.version_id)
        self.version_patch.start()
        self.addCleanup(self.version_patch.stop)
        self.app.execute("""
            INSERT INTO ref.funds (fund_code,name,category,source_sha256)
            VALUES (%s,'Synthetic runner fund','Synthetic runner category',%s)
        """, (self.code, self.sha))
        self.price("2030-01-31", "2030-01-31T12:00:00Z", Decimal("100"), self.sha)

    def price(self, effective: str, available: str, value: Decimal | None, checksum: str) -> None:
        self.app.execute("""
            INSERT INTO obs.fund_prices (fund_code,effective_date,nav,source_sha256,origin,
                available_at,observed_at,availability_rule)
            VALUES (%s,%s,%s,%s,'SYNTHETIC',%s,%s,'synthetic-exact-publication')
        """, (self.code, effective, value, checksum, available, available))

    def test_atomic_eight_signal_batch_and_repeat_input_reuses_completed_run(self) -> None:
        first = pipeline.run_detectors(self.app, self.cutoff, origin="SYNTHETIC")
        self.assertFalse(first["reused"])
        self.assertGreaterEqual(first["funds"], 1)
        rows = self.app.execute("""
            SELECT fund_code,count(*) FROM det.signals WHERE run_id=%s GROUP BY fund_code
        """, (first["run_id"],)).fetchall()
        self.assertEqual(len(rows), first["funds"])
        self.assertTrue(all(count == len(pipeline.DETECTOR_IDS) for _, count in rows))
        coverage = dict(self.app.execute("""
            SELECT detector_id,state FROM det.signals WHERE run_id=%s AND fund_code=%s
        """, (first["run_id"], self.code)).fetchall())
        self.assertEqual(coverage["D1"], "ABSTAINED")
        self.assertEqual(coverage["D5"], "NOT_TRIGGERED")
        self.assertEqual(coverage["AN-DQ-002"], "NOT_TRIGGERED")
        self.assertEqual(coverage["AN-FND-005"], "ABSTAINED")
        completed = self.app.execute(
            "SELECT complete,origin,input_sha256 FROM det.run_inputs WHERE run_id=%s", (first["run_id"],),
        ).fetchone()
        self.assertEqual(completed[:2], (True, "SYNTHETIC"))
        repeated = pipeline.run_detectors(self.app, self.cutoff, origin="SYNTHETIC")
        self.assertTrue(repeated["reused"])
        self.assertEqual(repeated["run_id"], first["run_id"])
        self.assertEqual(self.app.execute(
            "SELECT count(*) FROM det.run_inputs WHERE version_id=%s", (self.version_id,),
        ).fetchone()[0], 1)

    def test_future_publication_does_not_change_fingerprint_run_or_fixed_thresholds(self) -> None:
        first = pipeline.run_detectors(self.app, self.cutoff, origin="SYNTHETIC")
        with self.app.transaction():
            original = pipeline.load_inputs(self.app, self.cutoff)
        original_signal = self.app.execute("""
            SELECT evidence_id,state,value,threshold FROM det.signals
            WHERE run_id=%s AND fund_code=%s AND detector_id='D5'
        """, (first["run_id"], self.code)).fetchone()
        original_version = self.app.execute("""
            SELECT thresholds,calibration_input_sha256 FROM det.detector_versions WHERE version_id=%s
        """, (self.version_id,)).fetchone()
        future_sha = hashlib.sha256((self.sha + "future").encode()).hexdigest()
        revision_sha = hashlib.sha256((self.sha + "later-publication").encode()).hexdigest()
        self.price("2030-02-01", "2030-02-02T12:00:00Z", Decimal("200"), future_sha)
        self.price("2030-01-30", "2030-02-02T12:00:00Z", Decimal("50"), revision_sha)
        with self.app.transaction():
            unchanged = pipeline.load_inputs(self.app, self.cutoff)
        self.assertEqual(unchanged.input_sha256, original.input_sha256)
        self.assertEqual(unchanged.input_watermark, original.input_watermark)
        repeated = pipeline.run_detectors(self.app, self.cutoff, origin="SYNTHETIC")
        self.assertTrue(repeated["reused"])
        self.assertEqual(repeated["run_id"], first["run_id"])
        refreshed = pipeline.run_detectors(
            self.app, datetime(2030, 2, 3, 12, tzinfo=timezone.utc), origin="SYNTHETIC",
        )
        self.assertFalse(refreshed["reused"])
        self.assertNotEqual(refreshed["run_id"], first["run_id"])
        self.assertEqual(self.app.execute("""
            SELECT thresholds,calibration_input_sha256 FROM det.detector_versions WHERE version_id=%s
        """, (self.version_id,)).fetchone(), original_version)
        self.assertEqual(self.app.execute("""
            SELECT evidence_id,state,value,threshold FROM det.signals
            WHERE run_id=%s AND fund_code=%s AND detector_id='D5'
        """, (first["run_id"], self.code)).fetchone(), original_signal)
        self.assertEqual(self.app.execute(
            "SELECT count(*) FROM det.run_inputs WHERE version_id=%s", (self.version_id,),
        ).fetchone()[0], 2)


if __name__ == "__main__":
    unittest.main()
