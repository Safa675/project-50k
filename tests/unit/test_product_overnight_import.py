"""Synthetic refresh provenance, revision, catalog and point-in-time checks."""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from p50k.product.archive import sha256_file
from p50k.product.downloads import REPORT_TYPE, TEFAS, payload_sha256
from p50k.product.overnight_import import (
    AVAILABILITY_RULE, OvernightArchive, import_overnight,
)

NOW = datetime(2030, 1, 10, 12, tzinfo=timezone.utc)


class RefreshFixture:
    def __init__(self, root: Path, code: str = "THF") -> None:
        self.root, self.code = root, code

    def write(self, relative: str, value: object) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8", newline="\n")
        return path

    def price(self, nav: str | None = "100", *, acquired: str = "2030-01-03T12:00:00Z",
              code: str | None = None, rows: list | None = None) -> Path:
        code = code or self.code
        path = self.write(f"tefas/prices/{code}.json", {
            "fund": code, "source": "Synthetic source", "periyod": 12,
            "retrieved_at": acquired, "rows": rows or [["2030-01-02", nav]],
        })
        self.metadata(path, TEFAS + "/fonFiyatBilgiGetir", acquired, method="POST",
                      payload={"fonKodu": code, "dil": "TR", "periyod": 12}, price=True)
        return path

    def metadata(self, path: Path, url: str, acquired: str, *, method: str = "GET",
                 payload: dict | None = None, price: bool = False) -> Path:
        meta = {"url": url, "method": method, "status": 200,
                "content_type": "application/json", "requested_at_utc": acquired,
                "sha256": sha256_file(path)}
        if payload is not None:
            meta["payload_sha256"] = payload_sha256(payload)
        if price:
            meta["raw_response_sha256"] = "a" * 64
        relative = path.relative_to(self.root).as_posix() + ".meta.json"
        return self.write(relative, meta)

    def kap(self, *, published: str | None = "02.01.2030 12:00:00",
            disclosure: int = 42, acquired: str = "2030-01-03T12:00:00Z") -> Path:
        path = self.write(f"kap/reports/{self.code}/kap_report_list.json", [{
            "disclosureBasic": {"disclosureIndex": disclosure, "publishDate": published,
                                "year": 2030, "donem": 1, "period": "AB"},
        }])
        self.metadata(path, "https://kap.org.tr/tr/api/disclosure/filter/FILTERYFBF/"
                      + "a" * 32 + "/" + REPORT_TYPE + "/365", acquired)
        return path

    def snapshot(self, *, code: str | None = None, complete: bool = True) -> Path:
        path = self.root / "snapshots-all.sqlite3"
        with closing(sqlite3.connect(path)) as db:
            db.execute("CREATE TABLE collector_runs (started_at,finished_at,stopped)")
            db.execute("INSERT INTO collector_runs VALUES ('2030-01-03T11:00:00Z',?,0)", ("2030-01-03T13:00:00Z" if complete else None,))
            db.execute("CREATE TABLE fund_snapshots (fund,retrieved_at,as_of,as_of_rule,price,total_value,units_outstanding,investors,daily_return_pct,category)")
            db.execute("INSERT INTO fund_snapshots VALUES (?,?,?,?,?,?,?,?,?,?)", (
                code or self.code, "2030-01-03T12:00:00Z", "2030-01-02", "synthetic_matched_price",
                "100", "1000", "10", 2, "1", "Synthetic category",
            ))
            db.commit()
        return path


class OvernightArchiveTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.fixture = RefreshFixture(self.root)

    def archive(self) -> OvernightArchive:
        return OvernightArchive(self.root, frozenset({"THF"}), NOW)

    def test_revised_historical_price_is_available_only_at_acquisition(self) -> None:
        self.fixture.price()
        archive = self.archive()
        archive.freeze()
        row, = list(archive.prices())
        self.assertEqual(row["effective_date"], date(2030, 1, 2))
        self.assertEqual(row["available_at"], datetime(2030, 1, 3, 12, tzinfo=timezone.utc))
        self.assertEqual(row["available_at"], row["observed_at"])
        self.assertEqual(row["availability_rule"], AVAILABILITY_RULE)
        self.assertEqual(row["metadata"]["raw_response_sha256"], "a" * 64)

    def test_missing_and_zero_remain_null_and_no_past_timestamp_is_invented(self) -> None:
        self.fixture.price(rows=[["2030-01-01", "0"], ["2030-01-02", None]])
        archive = self.archive()
        archive.freeze()
        rows = list(archive.prices())
        self.assertEqual([r["nav"] for r in rows], [None, None])
        self.assertTrue(all(r["available_at"] == r["observed_at"] for r in rows))

    def test_source_hash_and_metadata_changes_fail_closed(self) -> None:
        path = self.fixture.price()
        path.write_text("{}", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.archive().freeze()
        path = self.fixture.price()
        archive = self.archive()
        archive.freeze()
        meta_path = path.with_suffix(".json.meta.json")
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        metadata["requested_at_utc"] = "2030-01-01T12:00:00Z"
        meta_path.write_text(json.dumps(metadata), encoding="utf-8")
        with self.assertRaises(ValueError):
            archive.verify_unchanged()

    def test_wrong_endpoint_payload_and_raw_response_hash_are_rejected(self) -> None:
        path = self.fixture.price()
        meta_path = path.with_suffix(".json.meta.json")
        original = json.loads(meta_path.read_text(encoding="utf-8"))
        for field, bad in (("url", "https://example.invalid/private"),
                           ("payload_sha256", "b" * 64), ("raw_response_sha256", None)):
            with self.subTest(field=field):
                meta_path.write_text(json.dumps({**original, field: bad}), encoding="utf-8")
                with self.assertRaises(ValueError):
                    self.archive().freeze()

    def test_unready_files_and_new_catalog_codes_are_skipped(self) -> None:
        self.fixture.price()
        self.fixture.price(code="PNU")
        self.fixture.write("tefas/prices/TP2.json", {})
        archive = OvernightArchive(self.root, frozenset({"THF", "TP2"}), NOW)
        archive.freeze()
        self.assertEqual(len(list(archive.prices())), 1)
        self.assertEqual(archive.ignored["outside_catalog_files"], 1)
        self.assertEqual(archive.ignored["unready_files"], 1)

    def test_new_completed_files_do_not_mutate_selected_manifest(self) -> None:
        self.fixture.price()
        archive = OvernightArchive(self.root, frozenset({"THF", "TP2"}), NOW)
        fingerprint = archive.freeze()
        self.fixture.price(code="TP2")
        archive.verify_unchanged()
        self.assertEqual(archive.fingerprint(), fingerprint)
        self.assertEqual(len(list(archive.prices())), 1)

    def test_future_acquisition_and_price_dates_and_duplicate_dates_are_rejected(self) -> None:
        self.fixture.price(acquired="2030-01-11T12:00:00Z")
        with self.assertRaises(ValueError):
            self.archive().freeze()
        for rows in ([["2030-01-04", "100"]], [["2030-01-02", "100"], ["2030-01-02", "101"]]):
            self.fixture.price(rows=rows)
            archive = self.archive()
            archive.freeze()
            with self.assertRaises(ValueError):
                list(archive.prices())

    def test_kap_publication_is_retained_but_new_index_is_not_backdated(self) -> None:
        self.fixture.kap()
        archive = self.archive()
        archive.freeze()
        row, = list(archive.kap_documents())
        self.assertLess(row["published_at"], row["available_at"])
        self.assertEqual(row["available_at"], row["observed_at"])
        self.assertEqual(row["available_at"], NOW)
        self.assertEqual(row["metadata"]["response_completion"], "UNKNOWN")
        self.assertIsNone(row["relative_path"])
        self.assertEqual(row["metadata"]["attachments"], [])

    def test_unknown_kap_publication_stays_unknown(self) -> None:
        self.fixture.kap(published=None)
        archive = self.archive()
        archive.freeze()
        row, = list(archive.kap_documents())
        self.assertIsNone(row["published_at"])
        self.assertIsNone(row["available_at"])
        self.assertIsNotNone(row["observed_at"])

    def test_snapshot_requires_completed_collector_and_stable_input(self) -> None:
        path = self.fixture.snapshot(complete=False)
        with self.assertRaises(ValueError):
            self.archive().freeze()
        path.unlink()
        self.fixture.snapshot()
        Path(str(path) + "-wal").write_bytes(b"Synthetic active journal")
        with self.assertRaises(ValueError):
            self.archive().freeze()

    def test_snapshots_do_not_add_funds_or_modify_source_database(self) -> None:
        path = self.fixture.snapshot(code="PNU")
        before = sha256_file(path)
        archive = self.archive()
        archive.freeze()
        self.assertEqual(list(archive.snapshots()), [])
        self.assertEqual(archive.ignored["outside_catalog_snapshots"], 1)
        self.assertEqual(sha256_file(path), before)

    def test_completed_snapshot_resume_accepts_an_older_stopped_run(self) -> None:
        path = self.fixture.snapshot()
        with closing(sqlite3.connect(path)) as db:
            db.execute("INSERT INTO collector_runs VALUES('2030-01-02T11:00:00Z','2030-01-02T13:00:00Z',1)")
            db.commit()
        archive = self.archive()
        archive.freeze()
        self.assertEqual(len(list(archive.snapshots())), 1)


@unittest.skipUnless(os.environ.get("P50K_TEST_DATABASE") == "1", "requires isolated PostgreSQL p50k_dev")
class OvernightImportDatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        from p50k.product.db import connect
        from p50k.product.settings import Settings
        settings = Settings.from_env()
        if settings.db_name != "p50k_dev":
            raise RuntimeError("Synthetic refresh checks require p50k_dev")
        self.connection = connect(settings, autocommit=True)
        self.addCleanup(self.connection.close)
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.code = "TST" + uuid4().hex[:9].upper()
        self.sha = hashlib.sha256(self.code.encode()).hexdigest()
        self.fixture = RefreshFixture(self.root, self.code)
        self.connection.execute("INSERT INTO ref.funds(fund_code,name,category,source_sha256) VALUES(%s,'Synthetic refresh fund','Synthetic category',%s)",
                                (self.code, self.sha))

    def import_rows(self):
        return import_overnight(self.connection, self.root, now=NOW)

    def price_values(self):
        return self.connection.execute("SELECT nav,available_at FROM obs.fund_prices WHERE fund_code=%s ORDER BY available_at,source_sha256", (self.code,)).fetchall()

    def test_repeat_import_is_idempotent_and_leaves_catalog_fixed(self) -> None:
        self.fixture.price(rows=[["2030-01-01", "100"], ["2030-01-02", None]])
        before = self.connection.execute("SELECT fund_code,category,source_sha256 FROM ref.funds ORDER BY fund_code").fetchall()
        first, second = self.import_rows(), self.import_rows()
        self.assertEqual(first["counts"]["obs.fund_prices"]["inserted"], 2)
        self.assertEqual(first["counts"]["obs.fund_prices"]["missing"], 1)
        self.assertEqual(second["counts"]["obs.fund_prices"]["inserted"], 0)
        self.assertEqual(self.connection.execute("SELECT fund_code,category,source_sha256 FROM ref.funds ORDER BY fund_code").fetchall(), before)

    def test_a_b_a_revisions_append_and_earlier_cutoff_cannot_see_them(self) -> None:
        for nav, acquired in (("100", "2030-01-03T12:00:00Z"),
                              ("101", "2030-01-04T12:00:00Z"),
                              ("100", "2030-01-05T12:00:00Z"),
                              ("100", "2030-01-06T12:00:00Z")):
            self.fixture.price(nav, acquired=acquired)
            self.import_rows()
        rows = self.price_values()
        self.assertEqual([r[0] for r in rows], [Decimal("100"), Decimal("101"), Decimal("100")])
        earlier = self.connection.execute("SELECT nav FROM obs.fund_prices WHERE fund_code=%s AND available_at<='2030-01-03T13:00:00Z' ORDER BY available_at DESC LIMIT 1", (self.code,)).fetchone()[0]
        self.assertEqual(earlier, Decimal("100"))

    def test_ambiguous_tied_revision_is_not_discarded_as_identical(self) -> None:
        self.fixture.price("100")
        self.import_rows()
        self.connection.execute("INSERT INTO obs.fund_prices(fund_code,effective_date,nav,source_id,source_sha256,origin,available_at,observed_at,availability_rule) VALUES(%s,'2030-01-02',101,'tefas-prices',%s,'DELAYED','2030-01-03T12:00:00Z','2030-01-03T12:00:00Z','synthetic_tie')", (self.code, self.sha))
        self.fixture.price("100", acquired="2030-01-04T12:00:00Z")
        imported = self.import_rows()
        self.assertEqual(imported["counts"]["obs.fund_prices"]["inserted"], 1)

    def test_validation_failure_rolls_back_all_observations(self) -> None:
        self.fixture.price()
        self.fixture.kap(published="04.01.2030 12:00:00")
        with self.assertRaises(ValueError):
            self.import_rows()
        self.assertEqual(self.price_values(), [])
        status = self.connection.execute("SELECT status,error_class FROM obs.ingest_runs ORDER BY started_at DESC LIMIT 1").fetchone()
        self.assertEqual(status, ("FAILED", "ValueError"))

    def test_snapshot_and_report_index_semantic_duplicates_are_not_repeated(self) -> None:
        self.fixture.snapshot()
        self.fixture.kap(disclosure=int(uuid4().hex[:8], 16))
        first, second = self.import_rows(), self.import_rows()
        self.assertEqual(first["counts"]["obs.fund_snapshots"]["inserted"], 1)
        self.assertEqual(first["counts"]["obs.kap_documents"]["inserted"], 1)
        self.assertEqual(second["counts"]["obs.fund_snapshots"]["inserted"], 0)
        self.assertEqual(second["counts"]["obs.kap_documents"]["inserted"], 0)

    def test_changed_snapshot_values_at_same_acquisition_are_rejected(self) -> None:
        from p50k.product.import_archive import ArchiveRevisionConflict
        path = self.fixture.snapshot()
        self.import_rows()
        with closing(sqlite3.connect(path)) as db:
            db.execute("UPDATE fund_snapshots SET investors=3")
            db.commit()
        with self.assertRaises(ArchiveRevisionConflict):
            self.import_rows()
        count = self.connection.execute("SELECT count(*) FROM obs.fund_snapshots WHERE fund_code=%s", (self.code,)).fetchone()[0]
        self.assertEqual(count, 1)


if __name__ == "__main__":
    unittest.main()
