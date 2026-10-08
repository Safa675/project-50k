from __future__ import annotations

import hashlib
import sqlite3
import tempfile
import unittest
from pathlib import Path
from decimal import Decimal

from p50k.evidence_store import BundleIntegrityError, EvidenceStore, InvalidObservation, Observation, normalize_timestamp

LOCATOR = "synthetic://fund-prices"
SOURCES = {LOCATOR: hashlib.sha256(b"synthetic price fixture").hexdigest()}
IMPORTED = "2026-10-07T12:00:00Z"


def observation(**changes) -> Observation:
    payload = dict(
        observation_key="TEFAS:TST:2026-10-01", fund="TST", source_id="TEFAS", source_version="v1",
        locator=LOCATOR, origin="SYNTHETIC", values={"nav": Decimal("12.345678901234567890")},
        units={"nav": "TRY/unit"}, effective_at=None, published_at="2026-10-01T11:00:00Z",
        available_at="2026-10-01T11:00:00Z", observed_at=None, ingested_at=IMPORTED,
        availability_provenance="OBSERVED", rights_status="SYNTHETIC",
        source_timestamps={"source_row_date": "2026-10-01"}, attributes={"cadence": "daily"},
        limitations=(),
    )
    payload.update(changes)
    return Observation(**payload)


class EvidenceStoreTest(unittest.TestCase):
    def setUp(self):
        self.store = EvidenceStore()
        self.addCleanup(self.store.close)

    def seal(self, rows, **changes):
        kwargs = dict(sources=SOURCES, imported_at=IMPORTED)
        kwargs.update(changes)
        return self.store.import_bundle(rows, **kwargs)

    def test_decimal_missing_values_and_provenance_survive_round_trip(self):
        row = observation(values={"nav": None, "cash": Decimal("0.000000000000000001")},
                          units={"nav": "TRY/unit", "cash": "TRY"})
        bundle = self.seal([row])
        self.assertEqual(self.store.observations(bundle), [row])
        stored = self.store.observations(bundle)[0]
        self.assertIsNone(stored.values["nav"])
        self.assertEqual(stored.values["cash"], Decimal("0.000000000000000001"))
        self.assertEqual((stored.source_id, stored.source_version, stored.origin), ("TEFAS", "v1", "SYNTHETIC"))
        self.assertEqual(self.store.manifest(bundle)["sources"], SOURCES)

    def test_original_offsets_and_date_granularity_are_preserved(self):
        row = observation(available_at="2026-10-01T14:00:00+03:00")
        self.assertEqual(row.available_at, "2026-10-01T11:00:00Z")
        self.assertEqual(row.source_timestamps["available_at"], "2026-10-01T14:00:00+03:00")
        self.assertEqual(row.source_timestamps["source_row_date"], "2026-10-01")
        self.assertIsNone(row.effective_at)

    def test_observation_copies_and_freezes_nested_metadata(self):
        values, attributes = {"nav": Decimal("2")}, {"periods": ["2026-10"]}
        row = observation(values=values, attributes=attributes)
        values["nav"], attributes["periods"][0] = Decimal("8"), "changed"
        self.assertEqual(row.values["nav"], Decimal("2"))
        self.assertEqual(row.attributes["periods"], ("2026-10",))
        with self.assertRaises(TypeError):
            row.values["nav"] = Decimal("4")

    def test_same_content_import_is_idempotent_across_import_clocks(self):
        bundle = self.seal([observation()])
        before = self.store.manifest(bundle)
        again = self.seal([observation(ingested_at="2026-10-08T12:00:00Z")], imported_at="2026-10-08T12:00:00Z")
        self.assertEqual(bundle, again)
        self.assertEqual(self.store.manifest(again), before)
        self.assertEqual(self.store.observations(again)[0].ingested_at, IMPORTED)

    def test_order_and_duplicate_input_do_not_change_bundle_identity(self):
        first = observation()
        second = observation(observation_key="TEFAS:TST:2026-10-02", source_version="v2")
        bundle = self.seal([second, first, first], config={"b": 2, "a": 1})
        self.assertEqual(bundle, self.seal([first, second], config={"a": 1, "b": 2}))
        self.assertEqual(len(self.store.observations(bundle)), 2)

    def test_unchanged_records_reuse_first_ingestion_in_new_bundles(self):
        row = observation()
        old = self.seal([row])
        new = self.seal([observation(ingested_at="2026-10-08T12:00:00Z"),
                         observation(observation_key="future", source_version="v2", available_at="2027-01-01T00:00:00Z")],
                        imported_at="2026-10-08T12:00:00Z")
        self.assertNotEqual(old, new)
        unchanged = next(item for item in self.store.observations(new) if item.observation_key == row.observation_key)
        self.assertEqual(unchanged, self.store.observations(old)[0])

    def test_unknown_availability_is_retained_for_audit(self):
        row = observation(availability_provenance="UNKNOWN", available_at=None)
        self.assertEqual(self.store.observations(self.seal([row])), [row])

    def test_conflicting_same_version_and_logical_key_are_rejected(self):
        for changed in (observation(values={"nav": Decimal("99")}),
                        observation(fund="OTHER", source_version="v2")):
            with self.subTest(changed=changed), self.assertRaises(InvalidObservation):
                self.seal([observation(), changed])
        self.assertEqual(self.store._db.execute("SELECT COUNT(*) FROM evidence_bundles").fetchone()[0], 0)

    def test_source_manifest_is_required_for_every_row(self):
        for sources in ({}, {"other": "a" * 64}, {LOCATOR: "not-a-digest"}):
            with self.subTest(sources=sources), self.assertRaises(InvalidObservation):
                self.seal([observation()], sources=sources)

    def test_numeric_and_metadata_inputs_are_strict(self):
        cases = [dict(values={"nav": value}) for value in
                 (True, 1.5, "2.5", Decimal("NaN"), Decimal("Infinity"))]
        cases += [dict(units={}), dict(attributes={"bad": float("nan")}),
                  dict(origin="HISTORICAL_REPLAY"), dict(availability_provenance="OBSERVED", available_at=None)]
        for changes in cases:
            with self.subTest(changes=changes), self.assertRaises(InvalidObservation):
                observation(**changes)

    def test_timestamp_inputs_reject_unknown_offsets_and_normalized_invalid_minutes(self):
        invalid = ("2026-10-01", "2026-10-01T12:00:00", "2026-10-01T12:00:00-00:00",
                   "2026-10-01T12:00:00.0000001Z", "2026-10-01T12:00:00+00:60",
                   "2026-10-01T12:00:00-00:60", "2026-10-01T12:00:00+01:99",
                   "2026-10-01T12:00:00-01:99", "2026-10-01T12:00:00+24:00",
                   "9999-12-31T23:59:59-01:00")
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(InvalidObservation):
                normalize_timestamp(value)

    def test_sealed_rows_and_manifest_reject_sql_mutation(self):
        bundle = self.seal([observation()])
        statements = (
            ("UPDATE evidence_observations SET payload = '{}'", ()),
            ("DELETE FROM evidence_observations", ()),
            ("UPDATE evidence_bundles SET sealed = 0 WHERE bundle_id = ?", (bundle,)),
            ("DELETE FROM evidence_bundles", ()),
            ("UPDATE evidence_bundle_rows SET ordinal = 2", ()),
            ("DELETE FROM evidence_bundle_rows", ()),
            ("INSERT INTO evidence_bundle_rows SELECT bundle_id, 9, observation_id FROM evidence_bundle_rows", ()),
        )
        for statement, parameters in statements:
            with self.subTest(statement=statement), self.assertRaises(sqlite3.IntegrityError):
                self.store._db.execute(statement, parameters)
        self.assertEqual(len(self.store.observations(bundle)), 1)

    def test_observation_tampering_is_detected_on_every_read(self):
        bundle = self.seal([observation()])
        self.store._db.execute("DROP TRIGGER evidence_observations_no_update")
        self.store._db.execute("UPDATE evidence_observations SET payload = '{}' ")
        for read in (self.store.observations, self.store.manifest):
            with self.subTest(read=read), self.assertRaises(BundleIntegrityError):
                read(bundle)

    def test_manifest_tampering_is_detected(self):
        bundle = self.seal([observation()])
        self.store._db.execute("DROP TRIGGER evidence_bundles_no_update")
        self.store._db.execute("UPDATE evidence_bundles SET manifest = '{}' ")
        with self.assertRaises(BundleIntegrityError):
            self.store.manifest(bundle)

    def test_partial_write_failure_rolls_back_whole_import(self):
        self.store._db.execute("CREATE TRIGGER synthetic_failure BEFORE INSERT ON evidence_bundle_rows "
                               "BEGIN SELECT RAISE(ABORT, 'Synthetic failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.seal([observation()])
        for table in ("evidence_observations", "evidence_bundles", "evidence_bundle_rows"):
            self.assertEqual(self.store._db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0], 0)

    def test_foreign_database_is_rejected_without_modifying_its_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "foreign.sqlite3"
            with sqlite3.connect(path) as db:
                db.execute("CREATE TABLE source_rows(value TEXT)")
                db.execute("INSERT INTO source_rows VALUES ('synthetic')")
            before = path.read_bytes()
            with self.assertRaises(InvalidObservation):
                EvidenceStore(path)
            self.assertEqual(path.read_bytes(), before)

    def test_persistent_store_reopens_with_same_sealed_bundle(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.sqlite3"
            store = EvidenceStore(path)
            bundle = store.import_bundle([observation()], sources=SOURCES, imported_at=IMPORTED)
            store.close()
            reopened = EvidenceStore(path)
            try:
                self.assertEqual(reopened.observations(bundle), [observation()])
            finally:
                reopened.close()

    def test_empty_foreign_database_is_rejected_without_resetting_ownership(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "empty-foreign.sqlite3"
            with sqlite3.connect(path) as db:
                db.execute("PRAGMA application_id = 12345")
                db.execute("PRAGMA user_version = 9")
            before = path.read_bytes()
            with self.assertRaises(InvalidObservation):
                EvidenceStore(path)
            self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
