from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError
from decimal import Decimal

from p50k.evidence_store import EvidenceStore, InvalidObservation
from p50k.replay import AmbiguousRevision, ReplayCursor
from tests.unit.test_evidence_store import IMPORTED, LOCATOR, SOURCES, observation

CUTOFF = "2026-10-01T12:00:00Z"


class ReplayCursorTest(unittest.TestCase):
    def setUp(self):
        self.store = EvidenceStore()
        self.addCleanup(self.store.close)

    def seal(self, rows, **changes):
        kwargs = dict(sources=SOURCES, imported_at=IMPORTED)
        kwargs.update(changes)
        return self.store.import_bundle(rows, **kwargs)

    def replay(self, rows, cutoff=CUTOFF):
        return ReplayCursor(self.store, self.seal(rows), cutoff).observations()

    def test_exact_cutoff_and_equivalent_timezones_are_inclusive(self):
        row = observation(available_at="2026-10-01T15:00:00+03:00", published_at=None)
        bundle = self.seal([row])
        for cutoff in (CUTOFF, "2026-10-01T15:00:00+03:00"):
            self.assertEqual(ReplayCursor(self.store, bundle, cutoff).observations(), [row])

    def test_each_future_instant_excludes_the_row(self):
        for field in ("available_at", "published_at", "effective_at", "observed_at"):
            row = observation(**{field: "2026-10-01T12:00:00.000001Z"})
            with self.subTest(field=field):
                self.assertEqual(self.replay([row]), [])

    def test_unknown_availability_is_excluded_even_if_date_is_earlier(self):
        for available in (None, "2026-10-01T10:00:00Z"):
            row = observation(availability_provenance="UNKNOWN", available_at=available)
            self.assertEqual(self.replay([row]), [])

    def test_ingestion_is_not_a_historical_availability_clock(self):
        row = observation(ingested_at="2027-01-01T00:00:00Z")
        self.assertEqual(self.replay([row]), [row])

    def test_latest_eligible_revision_wins_and_future_revision_stays_hidden(self):
        old = observation(available_at="2026-10-01T10:00:00Z", published_at=None)
        later = observation(source_version="v2", available_at="2026-10-01T11:00:00Z", published_at=None,
                            values={"nav": Decimal("20")})
        future = observation(source_version="v3", available_at="2026-10-01T13:00:00Z", published_at=None,
                             values={"nav": Decimal("30")})
        bundle = self.seal([future, old, later])
        self.assertEqual(ReplayCursor(self.store, bundle, "2026-10-01T10:30:00Z").observations(), [old])
        self.assertEqual(ReplayCursor(self.store, bundle, CUTOFF).observations(), [later])

    def test_future_changes_and_additions_leave_every_earlier_observation_unchanged(self):
        past = observation()
        future = observation(observation_key="future", source_version="future-v1", available_at="2026-10-02T00:00:00Z")
        first = self.seal([past, future])
        changed = observation(observation_key="future", source_version="future-v2", available_at="2026-10-02T00:00:00Z",
                              values={"nav": Decimal("999")}, ingested_at="2026-10-08T00:00:00Z")
        added = observation(observation_key="another-future", source_version="future-v3", available_at="2026-10-03T00:00:00Z")
        second = self.seal([observation(ingested_at="2026-10-08T00:00:00Z"), changed, added],
                           sources={LOCATOR: "f" * 64}, imported_at="2026-10-08T00:00:00Z")
        self.assertNotEqual(first, second)
        self.assertEqual(ReplayCursor(self.store, first, CUTOFF).observations(),
                         ReplayCursor(self.store, second, CUTOFF).observations())

    def test_missing_nav_and_synthetic_origin_are_preserved(self):
        row = observation(values={"nav": None})
        result = self.replay([row])[0]
        self.assertIsNone(result.values["nav"])
        self.assertEqual(result.origin, "SYNTHETIC")

    def test_fund_filter_keeps_logical_observation_order(self):
        first = observation()
        other = observation(fund="OTHER", observation_key="TEFAS:OTHER:2026-10-01")
        bundle = self.seal([first, other])
        cursor = ReplayCursor(self.store, bundle, CUTOFF)
        self.assertEqual(cursor.observations("TST"), [first])
        self.assertEqual(cursor.observations("MISSING"), [])
        keys = [row.observation_key for row in cursor.observations()]
        self.assertEqual(keys, sorted(keys))

    def test_tied_latest_revisions_fail_without_an_arbitrary_hash_choice(self):
        first = observation()
        conflicting = observation(source_version="v2", values={"nav": Decimal("50")})
        with self.assertRaises(AmbiguousRevision):
            self.replay([first, conflicting])

    def test_older_tie_does_not_hide_a_later_unambiguous_revision(self):
        first = observation(available_at="2026-10-01T10:00:00Z", published_at=None)
        tie = observation(source_version="v2", available_at="2026-10-01T10:00:00Z", published_at=None)
        latest = observation(source_version="v3", available_at="2026-10-01T11:00:00Z", published_at=None)
        bundle = self.seal([first, tie, latest])
        self.assertEqual(ReplayCursor(self.store, bundle, CUTOFF).observations(), [latest])
        with self.assertRaises(AmbiguousRevision):
            ReplayCursor(self.store, bundle, "2026-10-01T10:30:00Z").observations()

    def test_cursor_rejects_invalid_cutoff_and_unknown_bundle(self):
        bundle = self.seal([observation()])
        for cutoff in ("invalid", "2026-10-01T12:00:00", "2026-10-01T12:00:00+00:60"):
            with self.subTest(cutoff=cutoff), self.assertRaises(InvalidObservation):
                ReplayCursor(self.store, bundle, cutoff)
        with self.assertRaises(KeyError):
            ReplayCursor(self.store, "unknown", CUTOFF)

    def test_cursor_cannot_rebind_its_cutoff_or_bundle_context(self):
        row = observation()
        bundle = self.seal([row])
        cursor = ReplayCursor(self.store, bundle, CUTOFF)
        for field, value in (("cutoff", "2020-01-01T00:00:00Z"), ("bundle_id", "other"),
                             ("store", None), ("_limit", None)):
            with self.subTest(field=field), self.assertRaises(FrozenInstanceError):
                setattr(cursor, field, value)
        self.assertEqual(cursor.observations(), [row])


if __name__ == "__main__":
    unittest.main()
