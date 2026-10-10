"""Synthetic archive admission, missing values and point-in-time rules."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from p50k.product.archive import Archive, decimal_value, sha256_file, timestamp


class ArchiveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.raw = self.root / "archive"
        self.archive = Archive(self.raw)
        self.write("tefas/responses/fonGetiriBazliBilgiGetir_YAT.body", {
            "errorCode": None, "resultList": [
                {"fonKodu": "THF", "fonUnvan": "Synthetic fund", "fonTurAciklama": "Synthetic category", "tefasDurum": "1"},
            ],
        })
        listing = self.raw / "tefas/responses/fonGetiriBazliBilgiGetir_YAT.body"
        self.write("tefas/responses/requests.json", {"requests": [{
            "raw_file": listing.name, "requested_at_utc": "2030-01-03T12:00:00+00:00",
            "sha256": sha256_file(listing),
        }]})

    def write(self, relative: str, value: object) -> Path:
        path = self.raw / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8", newline="\n")
        return path

    def price_file(self, acquired: str = "2030-01-03T12:00:00+00:00") -> Path:
        return self.write("tefas/prices/THF.json", {
            "fund": "THF", "source": "Synthetic TEFAS", "periyod": 12,
            "retrieved_at": acquired,
            "rows": [["2030-01-02", "100"], ["2030-01-03", None]],
        })

    def test_listing_uses_single_category_source_and_acquisition_metadata(self) -> None:
        fund = next(self.archive.funds())
        self.assertEqual(fund["category"], "Synthetic category")
        self.assertEqual(fund["metadata"]["category_rule"], "current_fonTurAciklama_not_dated_membership")
        self.assertEqual(fund["listing_as_of"].isoformat(), "2030-01-03")

    def test_listing_hash_is_checked(self) -> None:
        self.write("tefas/responses/requests.json", [{"raw_file": "fonGetiriBazliBilgiGetir_YAT.body",
                    "requested_at_utc": "2030-01-03T12:00:00+00:00", "sha256": "bad"}])
        with self.assertRaises(ValueError):
            list(self.archive.funds())

    def test_missing_price_rows_remain_and_availability_is_explicit(self) -> None:
        self.price_file()
        positive, missing = list(self.archive.prices())
        self.assertEqual(positive["nav"], Decimal("100"))
        self.assertEqual(positive["available_at"].isoformat(), "2030-01-02T11:05:00+03:00")
        self.assertIsNone(missing["nav"])
        self.assertEqual(missing["available_at"], missing["observed_at"])
        self.assertEqual(missing["availability_rule"], "missing_row_observed_at_archive_acquisition")

    def test_zero_and_nonfinite_values_cannot_be_prices(self) -> None:
        self.assertIsNone(decimal_value("0", positive=True))
        self.assertIsNone(decimal_value("-1", positive=True))
        with self.assertRaises(ValueError):
            decimal_value("NaN")

    def test_lookahead_rejects_price_before_assumed_publication(self) -> None:
        path = self.price_file("2030-01-02T08:04:00+00:00")
        value = json.loads(path.read_text(encoding="utf-8"))
        value["rows"] = [["2030-01-02", "100"]]
        path.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaises(ValueError):
            list(self.archive.prices())

    def test_lookahead_rejects_future_missing_row(self) -> None:
        path = self.price_file()
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["rows"].append(["2030-01-04", None])
        path.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaises(ValueError):
            list(self.archive.prices())

    def test_changed_source_cannot_keep_an_earlier_hash(self) -> None:
        path = self.price_file()
        self.archive.fingerprint()
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["rows"][0][1] = "101"
        path.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaises(ValueError):
            list(self.archive.prices())
        with self.assertRaises(ValueError):
            self.archive.verify_unchanged()

    def test_new_input_changes_the_fingerprinted_inventory(self) -> None:
        self.price_file()
        self.archive.fingerprint()
        self.write("kap/series/THF.json", {"fund": "THF", "reports": []})
        with self.assertRaises(ValueError):
            self.archive.verify_unchanged()

    def test_official_event_pdf_is_bound_into_input_inventory(self) -> None:
        path = self.raw / "spk/synthetic.pdf"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"Synthetic original event")
        self.archive.fingerprint()
        path.write_bytes(b"Synthetic changed event")
        with self.assertRaises(ValueError):
            self.archive.verify_unchanged()

    def test_sqlite_journal_cannot_be_ignored_by_immutable_reader(self) -> None:
        path = self.root / "snapshots.sqlite3"
        Path(str(path) + "-wal").write_bytes(b"Synthetic journal")
        with self.assertRaises(ValueError):
            list(Archive(self.raw, (path,)).snapshots())

    def test_future_row_does_not_change_earlier_availability(self) -> None:
        path = self.price_file()
        earlier = next(self.archive.prices())
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["rows"].append(["2030-01-04", "110"])
        payload["retrieved_at"] = "2030-01-04T12:00:00+00:00"
        path.write_text(json.dumps(payload), encoding="utf-8")
        changed = next(Archive(self.raw).prices())
        self.assertEqual(earlier["nav"], changed["nav"])
        self.assertEqual(earlier["available_at"], changed["available_at"])

    def test_duplicate_dates_fail_admission(self) -> None:
        path = self.price_file()
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["rows"].append(payload["rows"][0])
        path.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaises(ValueError):
            list(self.archive.prices())

    def test_snapshots_are_read_only_and_unknown_dates_remain_unknown(self) -> None:
        path = self.root / "snapshots.sqlite3"
        connection = sqlite3.connect(path)
        connection.execute("CREATE TABLE fund_snapshots (fund,retrieved_at,as_of,as_of_rule,price,total_value,units_outstanding,investors,daily_return_pct,category)")
        connection.execute("INSERT INTO fund_snapshots VALUES (?,?,?,?,?,?,?,?,?,?)", (
            "THF", "2030-01-03T12:00:00+00:00", None, "unknown:no_price", None, None, None, 0, None, None))
        connection.commit()
        connection.close()
        digest = sha256_file(path)
        row = next(Archive(self.raw, (path,)).snapshots())
        self.assertIsNone(row["effective_date"])
        self.assertIsNone(row["nav"])
        self.assertEqual(row["available_at"], row["observed_at"])
        self.assertEqual(sha256_file(path), digest)

    def test_kap_fallback_deduplicates_and_preserves_weekly_period(self) -> None:
        listing = [{"disclosureBasic": {"disclosureIndex": 42, "publishDate": "03.01.2030 12:30:00",
                                       "year": 2030, "donem": 1, "period": "HB"}}]
        self.write("kap/reports/THF/kap_report_list.json", listing)
        self.write("kap/reports/kap_portfolio_reports_THF.body", listing)
        document, = list(self.archive.kap_documents())
        self.assertEqual(document["report_period"], "2030-W01")
        self.assertEqual(document["available_at"].isoformat(), "2030-01-03T12:30:00+03:00")
        self.assertIsNone(document["relative_path"])

    def test_kap_series_is_a_report_index_with_publication_time(self) -> None:
        self.write("kap/series/THF.json", {"fund": "THF", "reports": [{"period": "2030-01",
                   "disclosure_index": 42, "cadence": "monthly", "published_at": "2030-02-03T12:00:00+03:00"}]})
        row, = list(self.archive.kap_series())
        self.assertEqual(row["document_key"], "THF:42")
        self.assertEqual(row["published_at"], row["available_at"])

    def test_spk_mapping_is_candidate_and_unknown_time_is_not_invented(self) -> None:
        pdf = self.raw / "spk/synthetic.pdf"
        pdf.parent.mkdir(parents=True)
        pdf.write_bytes(b"Synthetic evidence")
        mapping = self.write("mapping.json", {"source": "https://spk.gov.tr/data/synthetic/2026-61.pdf",
            "source_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
            "funds": [{"code": "THF", "n": 1, "match": "exact name"}]})
        row, = list(Archive(self.raw, event_map=mapping).events())
        self.assertEqual(row["status"], "CANDIDATE")
        self.assertNotIn("available_at", row)
        self.assertNotIn("published_at", row)

    def test_fingerprint_changes_with_source_bytes(self) -> None:
        path = self.price_file()
        original = self.archive.fingerprint()
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["rows"][0][1] = "101"
        path.write_text(json.dumps(payload), encoding="utf-8")
        self.assertNotEqual(original, Archive(self.raw).fingerprint())

    def test_naive_timestamps_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            timestamp("2030-01-03T12:00:00")


if __name__ == "__main__":
    unittest.main()
