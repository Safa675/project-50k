import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from p50k.providers.disk_cache import DiskCache

T0 = datetime(2026, 10, 6, 16, 0, tzinfo=timezone.utc)


class FakeClock:
    def __init__(self) -> None:
        self.now = T0

    def __call__(self) -> datetime:
        return self.now


class DiskCacheTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.root = self.tmp / "cache"
        self.clock = FakeClock()
        self.cache = DiskCache(self.root, default_ttl_seconds=60,
                               ttl_by_category={"history": 3600}, clock=self.clock)

    def test_round_trip_keeps_value_and_when_it_was_cached(self):
        value = {"fonKodu": "TTE", "fiyat": 1.25, "fonUnvan": "İŞ PORTFÖY", "payAdet": None}
        stored = self.cache.set_json("snapshot", "TTE", value, source="tefas:fonBilgiGetir")
        self.clock.now = T0 + timedelta(seconds=30)
        entry = self.cache.get_json("snapshot", "TTE")
        self.assertEqual(entry.value, value)
        self.assertEqual(entry.cached_at, T0)
        self.assertEqual(entry.expires_at, T0 + timedelta(seconds=60))
        self.assertEqual(entry.source, "tefas:fonBilgiGetir")
        self.assertEqual(stored, entry)

    def test_returned_value_matches_what_reads_back(self):
        stored = self.cache.set_json("snapshot", "PAIR", (1, 2), source="s")
        self.assertEqual(stored.value, [1, 2])
        self.assertEqual(self.cache.get_json("snapshot", "PAIR").value, [1, 2])

    def test_expires_after_ttl(self):
        self.cache.set_json("snapshot", "TTE", {"a": 1}, source="s")
        self.clock.now = T0 + timedelta(seconds=59)
        self.assertTrue(self.cache.is_valid("snapshot", "TTE"))
        self.clock.now = T0 + timedelta(seconds=60)
        self.assertIsNone(self.cache.get_json("snapshot", "TTE"))
        self.assertFalse(self.cache.is_valid("snapshot", "TTE"))

    def test_ttl_precedence(self):
        by_category = self.cache.set_json("history", "TTE", [], source="s")
        explicit = self.cache.set_json("history", "AAL", [], source="s", ttl_seconds=5)
        default = self.cache.set_json("snapshot", "TTE", [], source="s")
        self.assertEqual(by_category.expires_at, T0 + timedelta(hours=1))
        self.assertEqual(explicit.expires_at, T0 + timedelta(seconds=5))
        self.assertEqual(default.expires_at, T0 + timedelta(seconds=60))

    def test_missing_entry_is_none(self):
        self.assertIsNone(self.cache.get_json("snapshot", "NOPE"))

    def test_rejects_nan_and_non_json_values_before_writing(self):
        cases = ((float("nan"), ValueError), ({"aum": float("inf")}, ValueError),
                 ({"when": T0}, TypeError), ({1, 2}, TypeError))
        for value, error in cases:
            with self.subTest(value=value), self.assertRaises(error):
                self.cache.set_json("snapshot", "BAD", value, source="s")
        self.assertFalse((self.root / "snapshot").exists())

    def test_rejects_unsafe_names(self):
        cases = (("snapshot", "../escape"), ("snapshot", "a/b"), ("../x", "k"),
                 ("snapshot", ".hidden"), ("snapshot", ""), ("", "k"))
        for category, key in cases:
            with self.subTest(category=category, key=key), self.assertRaises(ValueError):
                self.cache.set_json(category, key, 1, source="s")
        self.assertEqual([p.name for p in self.tmp.iterdir()], ["cache"])
        self.assertEqual(list(self.root.iterdir()), [])

    def test_requires_a_source(self):
        with self.assertRaises(ValueError):
            self.cache.set_json("snapshot", "TTE", 1, source="")

    def test_corrupt_entry_is_removed_and_reported_missing(self):
        self.cache.set_json("snapshot", "TTE", {"a": 1}, source="s")
        path = self.root / "snapshot" / "TTE.json"
        path.write_text("{not json", encoding="utf-8")
        with self.assertLogs("p50k.providers.disk_cache", level="WARNING"):
            self.assertIsNone(self.cache.get_json("snapshot", "TTE"))
        self.assertFalse(path.exists())

    def test_overwrite_leaves_one_file_and_no_temporary_files(self):
        self.cache.set_json("snapshot", "TTE", {"a": 1}, source="s")
        self.cache.set_json("snapshot", "TTE", {"a": 2}, source="s")
        self.assertEqual([p.name for p in (self.root / "snapshot").iterdir()], ["TTE.json"])
        self.assertEqual(self.cache.get_json("snapshot", "TTE").value, {"a": 2})

    def test_clear_expired_keeps_live_entries(self):
        self.cache.set_json("snapshot", "OLD", 1, source="s", ttl_seconds=10)
        self.cache.set_json("snapshot", "NEW", 1, source="s", ttl_seconds=100)
        self.clock.now = T0 + timedelta(seconds=50)
        self.assertEqual(self.cache.clear_expired(), 1)
        self.assertEqual([entry["key"] for entry in self.cache.inspect()["snapshot"]], ["NEW"])

    def test_clear_one_category_then_all(self):
        self.cache.set_json("snapshot", "TTE", 1, source="s")
        self.cache.set_json("history", "TTE", 1, source="s")
        self.assertEqual(self.cache.clear("snapshot"), 1)
        self.assertEqual(list(self.cache.inspect()), ["history"])
        self.assertEqual(self.cache.clear(), 1)
        self.assertEqual(self.cache.inspect(), {})

    def test_inspect_reports_metadata_without_values(self):
        self.cache.set_json("snapshot", "TTE", {"secret": 1}, source="tefas")
        self.clock.now = T0 + timedelta(seconds=61)
        self.assertEqual(self.cache.inspect(), {"snapshot": [{
            "key": "TTE",
            "cached_at": T0.isoformat(),
            "expires_at": (T0 + timedelta(seconds=60)).isoformat(),
            "source": "tefas",
            "expired": True,
        }]})

    def test_rejects_bad_ttls_and_a_naive_clock(self):
        with self.assertRaises(ValueError):
            DiskCache(self.root, default_ttl_seconds=0)
        for ttl in (0, -1, 1.5, True):
            with self.subTest(ttl=ttl), self.assertRaises(ValueError):
                self.cache.set_json("snapshot", "TTE", 1, source="s", ttl_seconds=ttl)
        naive = DiskCache(self.root, default_ttl_seconds=60, clock=lambda: datetime(2026, 10, 6))
        with self.assertRaises(ValueError):
            naive.set_json("snapshot", "TTE", 1, source="s")

    def test_entries_persist_across_instances(self):
        self.cache.set_json("snapshot", "TTE", {"a": 1}, source="s")
        other = DiskCache(self.root, default_ttl_seconds=60, clock=self.clock)
        self.assertEqual(other.get_json("snapshot", "TTE").value, {"a": 1})


if __name__ == "__main__":
    unittest.main()
