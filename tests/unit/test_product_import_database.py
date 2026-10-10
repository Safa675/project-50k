"""Real PostgreSQL COPY/idempotency checks using a separate synthetic database only."""
from __future__ import annotations

import json
import os
import unittest
from uuid import uuid4

from p50k.product.db import connect
from p50k.product.archive import Archive
from p50k.product.import_archive import ArchiveRevisionConflict, import_archive
from p50k.product.settings import Settings
from tests.unit import test_product_archive as fixture_module


@unittest.skipUnless(os.environ.get("P50K_TEST_DATABASE") == "1", "Requires isolated PostgreSQL p50k_dev")
class ImportDatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = Settings.from_env()
        if self.settings.db_name != "p50k_dev":
            raise RuntimeError("Synthetic import tests require p50k_dev")
        self.fixture = fixture_module.ArchiveTests(methodName="runTest")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.price_path = self.fixture.price_file()
        payload = json.loads(self.price_path.read_text(encoding="utf-8"))
        payload["synthetic_test_id"] = uuid4().hex
        self.price_path.write_text(json.dumps(payload), encoding="utf-8")

    def test_copy_preserves_null_and_repeat_import_inserts_no_observations(self) -> None:
        with connect(self.settings) as connection:
            first = import_archive(connection, self.fixture.archive)
            second = import_archive(connection, self.fixture.archive)
            self.assertEqual(first["counts"]["obs.fund_prices"]["inserted"], 2)
            self.assertEqual(first["counts"]["obs.fund_prices"]["missing"], 1)
            self.assertEqual(second["counts"]["obs.fund_prices"]["inserted"], 0)
            self.assertEqual(first["archive_sha256"], second["archive_sha256"])
            rows = connection.execute(
                "SELECT nav,available_at,observed_at FROM obs.fund_prices WHERE source_sha256=%s ORDER BY effective_date",
                (self.fixture.archive.digest(self.price_path),),
            ).fetchall()
            self.assertEqual(len(rows), 2)
            self.assertIsNone(rows[1][0])
            self.assertEqual(rows[1][1], rows[1][2])

    def test_failed_input_rolls_back_import_and_records_only_error_class(self) -> None:
        payload = json.loads(self.price_path.read_text(encoding="utf-8"))
        payload["rows"].append(payload["rows"][0])
        self.price_path.write_text(json.dumps(payload), encoding="utf-8")
        with connect(self.settings) as connection:
            with self.assertRaises(ValueError):
                import_archive(connection, self.fixture.archive)
            rows = connection.execute("SELECT count(*) FROM obs.fund_prices WHERE source_sha256=%s",
                                      (self.fixture.archive.digest(self.price_path),)).fetchone()
            self.assertEqual(rows[0], 0)
            result = connection.execute(
                "SELECT status,error_class,counts FROM obs.ingest_runs WHERE archive_sha256=%s ORDER BY started_at DESC LIMIT 1",
                (self.fixture.archive.fingerprint(),),
            ).fetchone()
            self.assertEqual(result, ("FAILED", "ValueError", {}))

    def test_changed_attachment_cannot_be_silently_dropped_as_duplicate(self) -> None:
        disclosure = int(uuid4().hex[:8], 16)
        self.fixture.write("kap/reports/THF/kap_report_list.json", [{"disclosureBasic": {
            "disclosureIndex": disclosure, "publishDate": "03.02.2030 12:00:00",
            "period": "AB", "year": 2030, "donem": 1,
        }}])
        pdf = self.fixture.raw / f"kap/reports/THF/2030-01_{disclosure}.pdf"
        pdf.write_bytes(b"%PDF-1.7\nSynthetic original attachment")
        with connect(self.settings) as connection:
            import_archive(connection, self.fixture.archive)
            pdf.write_bytes(b"%PDF-1.7\nSynthetic revised attachment")
            revised = Archive(self.fixture.raw)
            with self.assertRaises(ArchiveRevisionConflict):
                import_archive(connection, revised)
            count = connection.execute("SELECT count(*) FROM obs.kap_documents WHERE document_key=%s",
                                       (f"THF:{disclosure}",)).fetchone()
            self.assertEqual(count[0], 1)


if __name__ == "__main__":
    unittest.main()
