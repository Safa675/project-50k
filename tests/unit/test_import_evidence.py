from __future__ import annotations

import hashlib
import io
import json
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stderr
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from p50k.evidence_store import EvidenceStore
from p50k.jobs.fund_snapshots import SCHEMA
from p50k.jobs.import_evidence import (
    _validate_output, import_files, load_kap_file, load_price_file, load_snapshot_db, main, select_funds,
)
from p50k.replay import ReplayCursor

IMPORTED = "2026-10-10T12:00:00Z"
RETRIEVED = "2026-10-08T12:00:00+03:00"


class ImportEvidenceTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.prices = self.directory / "price" / "THF.json"
        self.kap = self.directory / "kap" / "THF.json"
        self.snapshot = self.directory / "snapshots.sqlite3"
        self.out = self.directory / "evidence.sqlite3"
        self.funds = frozenset({"THF", "TP2"})

    def write_json(self, path, payload):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def price_payload(self, **overrides):
        return {"fund": "THF", "source": "TEFAS fonFiyatBilgiGetir", "origin": "SYNTHETIC", "periyod": 60,
                "retrieved_at": RETRIEVED, "rows": [["2026-10-01", "11.25"], ["2026-10-02", "0"],
                                                     ["2026-10-03", None]], **overrides}

    def kap_payload(self, **overrides):
        return {"fund": "THF", "source": "KAP Portföy Dağılım Raporu", "origin": "SYNTHETIC",
                "reports": [{"period": "2026-08", "cadence": "monthly", "disclosure_index": 90000001,
                             "published_at": "2026-09-02T11:00:00+03:00", "company_title": "Synthetic Company",
                             "total_value": "1125", "units_outstanding": "100", "period_end_price": "11.25",
                             "previous_period_price": "0", "period_change_pct": None, "cash_in": "0",
                             "cash_out": "0", "problems": ["synthetic missing field"]}], **overrides}

    def make_snapshots(self, *, marked=True):
        db = sqlite3.connect(self.snapshot)
        db.executescript(SCHEMA)
        if marked:
            db.execute("CREATE TABLE evidence_import_metadata (key TEXT PRIMARY KEY, value TEXT)")
            db.execute("INSERT INTO evidence_import_metadata VALUES ('origin', 'SYNTHETIC')")
        columns = "fund,retrieved_at,as_of,as_of_rule,price,total_value,units_outstanding,investors,daily_return_pct,category,category_rank,category_size,market_share_pct,raw_snapshot,raw_prices"
        db.executemany(f"INSERT INTO fund_snapshots ({columns}) VALUES ({','.join('?' for _ in range(15))})", [
            ("THF", RETRIEVED, "2026-10-01", "price_equals_newest_dated_price", "0", "1125", "100", 0,
             "0", "Synthetic Category", 0, 2, "0", '{"origin":"SYNTHETIC"}', '[["2026-10-01","0"]]'),
            ("TP2", "2026-10-09T12:00:00+03:00", "2026-10-09", "price_equals_newest_dated_price", "12.50", "1250", "100", 8,
             "0", "Synthetic Category", 1, 2, "0", '{"origin":"SYNTHETIC"}', '[["2026-10-09","12.50"]]'),
            ("TST", RETRIEVED, None, "unknown", "unread numeric content", None, None, None,
             None, "Unread Category", None, None, None, '{}', '[]'),
        ])
        db.commit()
        db.close()

    def load_price(self, **options):
        return load_price_file(self.prices, funds=self.funds, imported_at=IMPORTED, synthetic=True, **options)

    def import_sources(self, **options):
        return import_files(out=self.out, funds=sorted(self.funds), imported_at=IMPORTED, synthetic=True, **options)

    def store(self):
        store = EvidenceStore(self.out)
        self.addCleanup(store.close)
        return store

    def test_prices_preserve_exact_values_missing_and_original_timestamps(self):
        self.write_json(self.prices, self.price_payload())
        loaded = self.load_price()
        self.assertEqual([row.values["nav"] for row in loaded.observations], [Decimal("11.25"), None, None])
        first = loaded.observations[0]
        self.assertIsNone(first.effective_at)
        self.assertIsNone(first.published_at)
        self.assertEqual(first.available_at, "2026-10-08T09:00:00Z")
        self.assertEqual(first.source_timestamps["retrieved_at"], RETRIEVED)
        self.assertEqual(first.attributes["source_row_date"], "2026-10-01")
        self.assertEqual(first.origin, "SYNTHETIC")
        self.assertEqual(first.rights_status, "SYNTHETIC")
        self.assertEqual(loaded.sha256, hashlib.sha256(self.prices.read_bytes()).hexdigest())

    def test_monetary_currency_is_unknown_unless_source_explicitly_provides_it(self):
        self.write_json(self.prices, self.price_payload())
        row = self.load_price().observations[0]
        self.assertEqual(row.units["nav"], "UNKNOWN_CURRENCY/unit")
        self.assertTrue(any("currency" in limitation.lower() for limitation in row.limitations))
        self.write_json(self.prices, self.price_payload(currency="TRY"))
        self.assertEqual(self.load_price().observations[0].units["nav"], "TRY/unit")
        self.write_json(self.kap, self.kap_payload(currency="USD"))
        report = load_kap_file(self.kap, funds=self.funds, imported_at=IMPORTED, synthetic=True).observations[0]
        self.assertEqual(report.units["total_value"], "USD")
        self.assertEqual(report.units["nav"], "USD/unit")
        self.write_json(self.prices, self.price_payload(currency="try"))
        with self.assertRaisesRegex(ValueError, "currency"):
            self.load_price()

    def test_unmarked_real_input_cannot_be_relabelled_as_synthetic(self):
        payload = self.price_payload()
        del payload["origin"]
        self.write_json(self.prices, payload)
        with self.assertRaisesRegex(ValueError, "explicit SYNTHETIC"):
            self.load_price()
        row = load_price_file(self.prices, funds=self.funds, imported_at=IMPORTED).observations[0]
        self.assertEqual((row.origin, row.rights_status), ("HISTORICAL_REPLAY", "UNKNOWN"))

    def test_missing_retrieval_stays_unknown_and_future_source_date_rejected(self):
        self.write_json(self.prices, self.price_payload(retrieved_at=None))
        row = self.load_price().observations[0]
        self.assertEqual(row.availability_provenance, "UNKNOWN")
        self.assertIsNone(row.available_at)
        self.write_json(self.prices, self.price_payload(rows=[["2026-10-09", "11.25"]]))
        with self.assertRaisesRegex(ValueError, "after its retrieval"):
            self.load_price()

    def test_bad_prices_and_duplicate_days_rejected(self):
        for rows in ([["2026-10-01", "NaN"]], [["2026-10-01", "-1"]],
                     [["2026-10-01", True]], [["2026-10-01", "11.25"], ["2026-10-01", "11.50"]]):
            with self.subTest(rows=rows):
                self.write_json(self.prices, self.price_payload(rows=rows))
                with self.assertRaises(ValueError):
                    self.load_price()

    def test_source_date_guard_is_independent_of_retrieval_offset(self):
        accepted = []
        for retrieval in ("2026-10-08T00:30:00+03:00", "2026-10-07T21:30:00Z", "2026-10-07T21:30:00z"):
            with self.subTest(retrieval=retrieval):
                self.write_json(self.prices, self.price_payload(retrieved_at=retrieval, rows=[["2026-10-08", "11.25"]]))
                accepted.append(self.load_price().observations[0].available_at)
                self.write_json(self.prices, self.price_payload(retrieved_at=retrieval, rows=[["2026-10-09", "11.25"]]))
                with self.assertRaisesRegex(ValueError, "after its retrieval"):
                    self.load_price()
        self.assertEqual(accepted, ["2026-10-07T21:30:00Z"] * 3)

    def test_json_source_marker_must_match_loader(self):
        self.write_json(self.prices, self.price_payload(source="unrelated provider"))
        with self.assertRaisesRegex(ValueError, "source marker"):
            self.load_price()
        self.write_json(self.kap, self.kap_payload(source="unrelated provider"))
        with self.assertRaisesRegex(ValueError, "source marker"):
            load_kap_file(self.kap, funds=self.funds, imported_at=IMPORTED, synthetic=True)

    def test_kap_preserves_selected_report_but_does_not_assert_historical_revision(self):
        self.write_json(self.kap, self.kap_payload())
        row = load_kap_file(self.kap, funds=self.funds, imported_at=IMPORTED, synthetic=True).observations[0]
        self.assertEqual(row.values["nav"], Decimal("11.25"))
        self.assertIsNone(row.values["previous_period_price"])
        self.assertEqual(row.values["cash_in"], Decimal(0))
        self.assertEqual(row.source_timestamps["published_at"], "2026-09-02T11:00:00+03:00")
        self.assertEqual(row.published_at, "2026-09-02T08:00:00Z")
        self.assertEqual(row.attributes["period_end_date"], "2026-08-31")
        self.assertIsNone(row.effective_at)
        self.assertIsNone(row.available_at)
        self.assertEqual(row.availability_provenance, "UNKNOWN")
        self.assertTrue(any("revision" in text for text in row.limitations))

    def test_weekly_kap_does_not_invent_effective_period(self):
        payload = self.kap_payload()
        payload["reports"][0].update(period="2026-W36", cadence="weekly")
        self.write_json(self.kap, payload)
        row = load_kap_file(self.kap, funds=self.funds, imported_at=IMPORTED, synthetic=True).observations[0]
        self.assertIsNone(row.attributes["period_end_date"])
        self.assertIsNone(row.effective_at)

    def test_snapshots_read_only_select_funds_preserve_zero_fields_and_no_backdating(self):
        self.make_snapshots()
        before = self.snapshot.read_bytes()
        loaded = load_snapshot_db(self.snapshot, funds=self.funds, imported_at=IMPORTED, synthetic=True)
        self.assertEqual(self.snapshot.read_bytes(), before)
        self.assertEqual([row.fund for row in loaded.observations], ["THF", "TP2"])
        first = loaded.observations[0]
        self.assertIsNone(first.values["nav"])
        self.assertEqual(first.values["investors"], Decimal(0))
        self.assertEqual(first.values["daily_return_pct"], Decimal(0))
        self.assertEqual(first.available_at, "2026-10-08T09:00:00Z")
        self.assertEqual(first.attributes["inferred_price_as_of"], "2026-10-01")
        self.assertIsNone(first.effective_at)
        self.assertEqual(first.attributes["source_row"]["raw_prices"], '[["2026-10-01","0"]]')

    def test_snapshot_synthetic_marker_required_and_mode_cannot_be_silently_changed(self):
        self.make_snapshots(marked=False)
        with self.assertRaisesRegex(ValueError, "explicit SYNTHETIC"):
            load_snapshot_db(self.snapshot, funds=self.funds, imported_at=IMPORTED, synthetic=True)
        self.snapshot.unlink()
        self.make_snapshots()
        with self.assertRaisesRegex(ValueError, "conflicts"):
            load_snapshot_db(self.snapshot, funds=self.funds, imported_at=IMPORTED)

    def test_uncheckpointed_snapshot_wal_is_rejected(self):
        self.make_snapshots()
        Path(f"{self.snapshot}-wal").write_bytes(b"synthetic unfinished WAL")
        with self.assertRaisesRegex(ValueError, "WAL"):
            load_snapshot_db(self.snapshot, funds=self.funds, imported_at=IMPORTED, synthetic=True)

    def test_unknown_fund_or_filename_rejected_before_source_content_opened(self):
        with patch.object(Path, "read_bytes", side_effect=AssertionError("source must remain unopened")):
            with self.assertRaisesRegex(ValueError, "allowlist"):
                import_files(price_files=[self.directory / "ZZZ.json"], out=self.out,
                             funds=["ZZZ"], imported_at=IMPORTED)
            with self.assertRaisesRegex(ValueError, "CODE.json"):
                self.import_sources(price_files=[self.directory / "ZZZ.json"])

    def test_target_cannot_be_repository_source_symlink_or_hardlink(self):
        self.write_json(self.prices, self.price_payload())
        with self.assertRaisesRegex(ValueError, "outside"):
            _validate_output(self.directory / "repo" / "nested" / "out.db", [], repo_root=self.directory / "repo")
        for target in (self.prices, self.directory / "alias.db", self.directory / "hard.db"):
            if target.name == "alias.db":
                target.symlink_to(self.prices)
            elif target.name == "hard.db":
                target.hardlink_to(self.prices)
            with self.subTest(target=target), self.assertRaisesRegex(ValueError, "overwrite"):
                _validate_output(target, [self.prices])

    def test_load_failure_writes_no_partial_target(self):
        self.write_json(self.prices, self.price_payload())
        self.write_json(self.kap, {"fund": "THF", "origin": "SYNTHETIC", "reports": "malformed"})
        with self.assertRaises(ValueError):
            self.import_sources(price_files=[self.prices], kap_files=[self.kap])
        self.assertFalse(self.out.exists())

    def test_bundle_import_idempotent_all_sources_visible_only_when_known(self):
        self.write_json(self.prices, self.price_payload())
        self.write_json(self.kap, self.kap_payload())
        self.make_snapshots()
        options = {"price_files": [self.prices], "kap_files": [self.kap], "snapshot_db": self.snapshot}
        bundle = self.import_sources(**options)
        store = self.store()
        before = store.manifest(bundle)
        repeated = import_files(out=self.out, funds=sorted(self.funds), imported_at="2026-10-11T12:00:00Z",
                                synthetic=True, **options)
        self.assertEqual(bundle, repeated)
        self.assertEqual(before, store.manifest(repeated))
        self.assertEqual(len(store.observations(bundle)), 6)
        self.assertEqual(ReplayCursor(store, bundle, "2026-10-08T08:59:59Z").observations(), [])
        visible = ReplayCursor(store, bundle, "2026-10-08T09:00:00Z").observations()
        self.assertEqual(len(visible), 4)
        self.assertTrue(all(row.source_id.startswith("TEFAS:") for row in visible))
        self.assertTrue(all(row.origin == "SYNTHETIC" for row in visible))

    def test_changing_future_snapshot_leaves_complete_past_rows_unchanged(self):
        self.make_snapshots()
        original = self.import_sources(snapshot_db=self.snapshot)
        store = self.store()
        before = ReplayCursor(store, original, "2026-10-08T09:00:00Z").observations()
        db = sqlite3.connect(self.snapshot)
        db.execute("UPDATE fund_snapshots SET price = '99.50' WHERE fund = 'TP2'")
        db.commit()
        db.close()
        revised = self.import_sources(snapshot_db=self.snapshot)
        after = ReplayCursor(store, revised, "2026-10-08T09:00:00Z").observations()
        self.assertNotEqual(original, revised)
        self.assertEqual(before, after)
        self.assertEqual(len(after), 1)

    def test_cli_requires_explicit_inputs_funds_and_output(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            main([])
        self.assertEqual(caught.exception.code, 2)
        self.assertEqual(select_funds(["thf", "THF"]), frozenset({"THF"}))


if __name__ == "__main__":
    unittest.main()
