"""Dated bundles, date index, loaders and the registered runner (synthetic only).

Temp repositories use the hermetic Git helper. numpy-dependent classes skip
without the optional analysis dependency, as in test_fund_review_bundle.py.
"""
from __future__ import annotations

import builtins
import contextlib
import copy
import hashlib
import importlib
import importlib.util
import io
import json
import math
import os
import re
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from p50k.research_reviews import bundle_v2
from p50k.research_reviews.bundle import (
    EVENT_REL, BundleIntegrityError, canonical_bytes, digest, load_bundle, load_frozen_detector, number,
    write_bundle,
)
from p50k.research_reviews.contracts import empty_finding
from p50k.research_reviews.dated_bundle import (
    DatedSourceRegistry, bounded_rows_sha256, build_threshold_provenance, bounded_snapshot, index_entry,
    load_date_index, load_dated_bundle, load_indexed_bundle, make_date_index, verify_dated_payload, write_date_index,
    write_dated_bundle,
)
from p50k.research_reviews.dated_comments import dated_order, describe_dated, summarize_dated
from p50k.research_reviews.dated_contracts import SNAPSHOT_BOUND, metadata_for
from p50k.research_reviews.dated_review import assemble_dated
from tests.unit._hermetic_git import commit_all, copy_registered, git, init_repo, write
from tests.unit.test_fund_review_bundle import all_missing_bundle
from tests.unit.test_fund_review_dated import EXPECTED_GRID, HOLIDAYS, weekdays

REPO = Path(__file__).resolve().parents[2]
CODES = [f"Z{i:02d}" for i in range(100)]
TARGETS = CODES[:8]
RUNNER_PATH = REPO / EVENT_REL / "fund_review_dated/run.py"
V1_RUNNER_PATH = REPO / EVENT_REL / "fund_review_app/run.py"
PRICE_DIR = Path("raw/tefas/prices")
OUTPUT = Path("raw/research/fund-review-dated")
V1_OUTPUT = Path("raw/research/fund-review-app")
DETECTOR_REL = EVENT_REL / "price_detectors/detectors.py"
PREREGISTRATION_REL = EVENT_REL / "price_detectors/PREREGISTRATION.md"
RESULTS_REL = EVENT_REL / "price_detectors/results.json"
REGISTERED_AT = "2026-10-06T18:00:00+00:00"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def has_numpy() -> bool:
    return importlib.util.find_spec("numpy") is not None


def category(code: str) -> str | None:
    index = int(code[1:])
    return "Synthetic A" if index < 14 else "Synthetic B" if index < 17 else None


def results_bytes(detectors: bytes, preregistration: bytes, **overrides) -> bytes:
    """Synthetic calibration file in the committed results.json shape (invented values)."""
    values = {"run_at_utc": SNAPSHOT_BOUND, "detectors_sha256": digest(detectors),
              "preregistration_sha256": digest(preregistration), **overrides}
    targets = ", ".join(f'"{code}": {{"category": "Synthetic A", "evaluable": true}}' for code in TARGETS)
    return ("{" + f'"run_at_utc": {json.dumps(values["run_at_utc"])}, '
            f'"detectors_sha256": "{values["detectors_sha256"]}", '
            f'"preregistration_sha256": "{values["preregistration_sha256"]}", '
            f'"targets": {json.dumps(TARGETS)}, "results": {{"D1": {{"targets": {{{targets}}}}}}}, '
            '"thresholds": {"D1": {"Synthetic A": 0.00050, "Synthetic B": null}}}\n').encode()


def write_inputs(root: Path, *, calendar: list[str] | None = None) -> Path:
    """Invented price files (two missing) and a snapshot database; returns the database path."""
    calendar = calendar or weekdays("2025-08-01", "2026-09-30")
    for k, code in enumerate(CODES):
        if code in ("Z98", "Z99"):
            continue
        base = 0.002 if code == "Z00" else 0.0003 + 0.00002 * k
        level, rows = 0.0, []
        for t, day in enumerate(calendar):
            level += base + 0.0004 * math.sin(0.7 * t + k)
            if code == "Z06" and day < "2026-02-02":
                continue
            rows.append([day, None if (code == "Z05" and day == "2026-03-31") else repr(100 * math.exp(level))])
        write(root, PRICE_DIR / f"{code}.json", json.dumps(
            {"fund": code, "source": "TEFAS fonFiyatBilgiGetir", "retrieved_at": "2026-10-07T09:00:00+03:00",
             "rows": rows}).encode())
    write(root, PRICE_DIR / "AAA.json", b'{"fund": "AAA", "source": "TEFAS fonFiyatBilgiGetir", "rows": []}')
    path = root / "raw" / "snapshots.sqlite3"
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    try:
        connection.execute("CREATE TABLE fund_snapshots(fund TEXT, category TEXT, raw_snapshot TEXT, retrieved_at TEXT)")
        connection.executemany("INSERT INTO fund_snapshots VALUES(?,?,?,?)", [
            (code, category(code), json.dumps({"fonUnvan": f"Synthetic fund {code}", "investors": 1}), REGISTERED_AT)
            for code in CODES[:97]])
        connection.commit()
    finally:
        connection.close()
    return path


def sql(path: Path, statement: str, parameters=()) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute(statement, parameters)
        connection.commit()
    finally:
        connection.close()


def tree_digest(root: Path) -> dict[str, str]:
    return {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(root.rglob("*")) if path.is_file()} if root.exists() else {}


class Workspace:
    """Provenance files, inputs and registered sources for loader tests (no Git)."""

    def __init__(self, root: Path, *, extra_snapshot_rows: tuple = ()):
        self.root = root
        detectors = copy_registered(root, DETECTOR_REL).read_bytes()
        preregistration = write(root, PREREGISTRATION_REL, b"Synthetic preregistration.\n").read_bytes()
        self.results = write(root, RESULTS_REL, results_bytes(detectors, preregistration))
        self.protocol = write(root, "protocol.md", b"Synthetic dated protocol.\n")
        universe = write(root, "universe.txt", ("\n".join(CODES) + "\n").encode())
        self.db = write_inputs(root)
        for row in extra_snapshot_rows:
            sql(self.db, "INSERT INTO fund_snapshots VALUES(?,?,?,?)", row)
        self.provenance = build_threshold_provenance(self.results.read_bytes(), detectors, preregistration)
        projection, latest = bounded_snapshot(self.db, CODES)
        self.identities = json.loads(projection)
        self.snapshot = {"bound": SNAPSHOT_BOUND, "latest_retrieved_at": latest, "projection_sha256": digest(projection)}
        self.registry = DatedSourceRegistry()
        self.global_refs = [self.registry.add(self.protocol, "PROTOCOL"), self.registry.add(universe, "UNIVERSE"),
                            self.registry.add(self.results, "CALIBRATION"),
                            self.registry.add(self.db, "SNAPSHOT", snapshot_codes=CODES, snapshot_bound=SNAPSHOT_BOUND)]
        self.prices, self.price_refs = {}, {}
        for code in CODES:
            path = root / PRICE_DIR / f"{code}.json"
            self.prices[code] = json.loads(path.read_bytes()) if path.exists() else None
            self.price_refs[code] = self.global_refs + ([self.registry.add(path, "PRICE", fund_code=code)]
                                                        if path.exists() else [])
        self.registration = {"protocol_sha256": "6" * 64, "protocol_commit": "7" * 40}

    def manual(self, cutoff: str, registration: dict | None = None) -> dict:
        """All-unavailable dated payload built without numpy."""
        records = []
        thresholds = {"Synthetic A": "0.00050"}
        for code in CODES:
            identity = self.identities.get(code, {"name": code, "category": None})
            d1 = empty_finding("d1")
            threshold = number(thresholds.get(identity["category"]))
            d1.update(threshold=None if threshold is None else str(threshold), input_refs=list(self.global_refs),
                      missing_reasons=["fewer_than_50_usable_excess_observations"])
            d1["qualifications"].append("peer_category_membership_from_current_snapshot")
            records.append({"code": code, "name": identity["name"], "category": identity["category"],
                            "comment_tr": describe_dated(d1), "d1_state": "UNAVAILABLE", "d1": d1,
                            "chart": {"status": "UNAVAILABLE", "reason": "no_common_valid_baseline_with_10_peers",
                                      "baseline_date": None, "unit": "INDEX_100", "points": [], "peer_count": 0},
                            "date_context": {"has_positive_price_on_or_before_cutoff": code != "Z99"},
                            "evidence": sorted(set(self.price_refs[code]))})
        records.sort(key=dated_order)
        payload = {"schema": "p50k.fund-review-dated.v1", **metadata_for(cutoff),
                   "threshold_provenance": self.provenance, "snapshot": self.snapshot,
                   "summary": summarize_dated(records), "funds": records,
                   "sources": sorted(self.registry.sources.values(), key=lambda s: s["source_id"]),
                   "manifest": sorted(self.registry.manifest.values(), key=lambda s: s["source_id"]),
                   "registration": registration or self.registration}
        payload["immutable_bundle_id"] = digest(canonical_bytes(payload))
        return payload

    def assembled(self, cutoff: str, detector) -> dict:
        return assemble_dated(CODES, cutoff_date=cutoff, grid=EXPECTED_GRID, price_payloads=self.prices,
                              identities=self.identities, thresholds=json.loads(self.results.read_bytes(),
                                                                                parse_float=__import__("decimal").Decimal)
                              ["thresholds"]["D1"], price_refs=self.price_refs,
                              sources=list(self.registry.sources.values()),
                              manifest=list(self.registry.manifest.values()), detector=detector,
                              registration=self.registration, threshold_provenance=self.provenance,
                              snapshot=self.snapshot)


def forge(base: Path, payload: dict, key: str = "immutable_bundle_id", filename: str = "bundle.json") -> Path:
    """Re-fingerprint and write a tampered payload directly, bypassing the writers."""
    payload = copy.deepcopy(payload)
    payload.pop(key, None)
    payload[key] = digest(canonical_bytes(payload))
    directory = base / payload[key]
    directory.mkdir(parents=True, exist_ok=True)
    (directory / filename).write_bytes(canonical_bytes(payload))
    return directory


class DatedBundleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.space = Workspace(self.root)
        self.bundles = self.root / OUTPUT / "bundles"

    def tearDown(self):
        self.tmp.cleanup()

    def load(self, directory: Path) -> dict:
        return load_dated_bundle(directory, repo_root=self.root, allowed_codes=CODES)

    def test_atomic_idempotent_seal_and_snapshot_bound_on_load(self):
        payload = self.space.manual("2026-03-31")
        directory = write_dated_bundle(self.bundles, payload, repo_root=self.root)
        self.assertEqual(directory.name, payload["immutable_bundle_id"])
        before = tree_digest(self.bundles)
        self.assertEqual(write_dated_bundle(self.bundles, payload, repo_root=self.root), directory)
        self.assertEqual(tree_digest(self.bundles), before)
        self.assertEqual(self.load(directory), payload)
        self.assertEqual([path.name for path in self.bundles.iterdir()], [directory.name])
        # Rows appended after the bound are harmless.
        sql(self.space.db, "INSERT INTO fund_snapshots VALUES(?,?,?,?)",
            ("Z00", "Moved", '{"fonUnvan":"Renamed"}', "2026-10-08T00:00:00+00:00"))
        self.assertEqual(self.load(directory), payload)
        # Edited or backdated rows before the bound refuse.
        sql(self.space.db, "UPDATE fund_snapshots SET category=? WHERE fund=? AND retrieved_at=?",
            ("Edited", "Z01", REGISTERED_AT))
        with self.assertRaisesRegex(BundleIntegrityError, "original source changed"):
            self.load(directory)
        sql(self.space.db, "UPDATE fund_snapshots SET category=? WHERE fund=? AND retrieved_at=?",
            ("Synthetic A", "Z01", REGISTERED_AT))
        self.assertEqual(self.load(directory), payload)
        sql(self.space.db, "INSERT INTO fund_snapshots VALUES(?,?,?,?)",
            ("Z02", "Backdated", "{}", "2026-10-07T01:00:00+00:00"))
        with self.assertRaisesRegex(BundleIntegrityError, "changed"):
            self.load(directory)
        sql(self.space.db, "DELETE FROM fund_snapshots WHERE category=?", ("Backdated",))
        sql(self.space.db, "INSERT INTO fund_snapshots VALUES(?,?,?,?)", ("Z03", "x", "{}", "2026-10-01T00:00:00"))
        with self.assertRaisesRegex(BundleIntegrityError, "UTC offset"):
            self.load(directory)

    def test_older_bounded_rows_are_bound_on_load(self):
        """Edits or backdated inserts behind each fund's newest bounded row refuse; later rows do not."""
        older = ("Z01", "Synthetic A", '{"fonUnvan":"Older synthetic name"}', "2026-10-01T00:00:00+00:00")
        with tempfile.TemporaryDirectory() as tmp:
            space = Workspace(Path(tmp), extra_snapshot_rows=(older,))
            payload = space.manual("2026-04-30")
            bundles = Path(tmp) / OUTPUT / "bundles"
            directory = write_dated_bundle(bundles, payload, repo_root=space.root)

            def load():
                return load_dated_bundle(directory, repo_root=space.root, allowed_codes=CODES)

            self.assertEqual(load(), payload)
            projection = bounded_snapshot(space.db, CODES)
            rows = bounded_rows_sha256(space.db, CODES)
            self.assertEqual(set(payload["snapshot"]), {"bound", "latest_retrieved_at", "projection_sha256"})
            entry = next(entry for entry in payload["manifest"] if entry["kind"] == "SNAPSHOT")
            self.assertEqual(entry["snapshot_rows_sha256"], rows)
            self.assertNotIn("snapshot_rows_sha256", json.dumps(payload["sources"]))
            # Rows appended after the bound change neither digest.
            sql(space.db, "INSERT INTO fund_snapshots VALUES(?,?,?,?)",
                ("Z01", "Moved", '{"fonUnvan":"Renamed"}', "2026-10-08T00:00:00+00:00"))
            self.assertEqual((bounded_snapshot(space.db, CODES), bounded_rows_sha256(space.db, CODES)),
                             (projection, rows))
            self.assertEqual(load(), payload)
            changes = (
                ("edited older row", "UPDATE fund_snapshots SET category=? WHERE fund=? AND retrieved_at=?",
                 ("Edited", older[0], older[3]),
                 "UPDATE fund_snapshots SET category=? WHERE fund=? AND retrieved_at=?",
                 (older[1], older[0], older[3])),
                ("edited older raw", "UPDATE fund_snapshots SET raw_snapshot=? WHERE fund=? AND retrieved_at=?",
                 ('{"fonUnvan":"Edited"}', older[0], older[3]),
                 "UPDATE fund_snapshots SET raw_snapshot=? WHERE fund=? AND retrieved_at=?",
                 (older[2], older[0], older[3])),
                ("backdated older insert", "INSERT INTO fund_snapshots VALUES(?,?,?,?)",
                 ("Z02", "Backdated", "{}", "2026-10-02T00:00:00+00:00"),
                 "DELETE FROM fund_snapshots WHERE category=?", ("Backdated",)),
                ("deleted older row", "DELETE FROM fund_snapshots WHERE fund=? AND retrieved_at=?",
                 (older[0], older[3]), "INSERT INTO fund_snapshots VALUES(?,?,?,?)", older),
            )
            for label, statement, parameters, undo, undo_parameters in changes:
                sql(space.db, statement, parameters)
                with self.subTest(label):
                    # The newest-row projection alone cannot see this change.
                    self.assertEqual(bounded_snapshot(space.db, CODES), projection)
                    self.assertNotEqual(bounded_rows_sha256(space.db, CODES), rows)
                    with self.assertRaisesRegex(BundleIntegrityError, "snapshot rows changed"):
                        load()
                sql(space.db, undo, undo_parameters)
                self.assertEqual(load(), payload)

    def test_snapshot_rows_digest_required_only_on_the_snapshot_entry(self):
        payload = self.space.manual("2026-02-27")
        write_dated_bundle(self.bundles, payload, repo_root=self.root)
        snapshot = next(i for i, entry in enumerate(payload["manifest"]) if entry["kind"] == "SNAPSHOT")
        other = next(i for i, entry in enumerate(payload["manifest"]) if entry["kind"] != "SNAPSHOT")
        cases = []
        for value in (None, "not-a-digest", "A" * 64):
            forged = copy.deepcopy(payload)
            forged["manifest"][snapshot]["snapshot_rows_sha256"] = value
            cases.append((repr(value), forged, "bounded rows digest"))
        forged = copy.deepcopy(payload)
        forged["manifest"][snapshot]["snapshot_rows_sha256"] = "0" * 64
        cases.append(("wrong digest", forged, "snapshot rows changed"))
        forged = copy.deepcopy(payload)
        del forged["manifest"][snapshot]["snapshot_rows_sha256"]
        cases.append(("missing key", forged, "manifest entry differs"))
        forged = copy.deepcopy(payload)
        forged["manifest"][other]["snapshot_rows_sha256"] = "0" * 64
        cases.append(("non-snapshot entry", forged, "only the snapshot source"))
        for label, forged, message in cases:
            with self.subTest(label), self.assertRaisesRegex(BundleIntegrityError, message):
                self.load(forge(self.bundles, forged))

    def test_threshold_provenance_enforced_on_load(self):
        payload = self.space.manual("2025-10-31")
        write_dated_bundle(self.bundles, payload, repo_root=self.root)
        early = copy.deepcopy(payload)
        early.update(metadata_for("2025-10-06"))
        early.update(cutoff_date="2025-10-03", cutoff_at="2025-10-03T23:59:59+03:00")
        with self.assertRaisesRegex(BundleIntegrityError, "outside the registered range"):
            self.load(forge(self.bundles, early))
        for key in ("results_sha256", "threshold_map_sha256", "detectors_sha256", "preregistration_sha256"):
            forged = copy.deepcopy(payload)
            forged["threshold_provenance"][key] = "0" * 64
            with self.assertRaisesRegex(BundleIntegrityError, "committed calibration files"):
                self.load(forge(self.bundles, forged))
        forged = copy.deepcopy(payload)
        forged["threshold_provenance"]["crossing"] = "AT_OR_ABOVE"
        with self.assertRaisesRegex(BundleIntegrityError, "calibration bound"):
            self.load(forge(self.bundles, forged))
        forged = copy.deepcopy(payload)
        record = next(row for row in forged["funds"] if row["category"] == "Synthetic A")
        record["d1"]["threshold"] = "0.0004"
        with self.assertRaisesRegex(BundleIntegrityError, "record threshold"):
            self.load(forge(self.bundles, forged))
        forged = copy.deepcopy(payload)
        record = next(row for row in forged["funds"] if row["category"] is None)
        record["d1"]["threshold"] = "0.00050"
        with self.assertRaisesRegex(BundleIntegrityError, "record threshold"):
            self.load(forge(self.bundles, forged))
        # Changing the committed calibration after sealing retires the bundle.
        directory = self.bundles / payload["immutable_bundle_id"]
        original = self.space.results.read_bytes()
        self.space.results.write_bytes(original.replace(b"0.00050", b"0.00051"))
        with self.assertRaises(BundleIntegrityError):
            self.load(directory)
        self.space.results.write_bytes(original)
        self.assertEqual(self.load(directory), payload)

    def test_scope_metadata_summary_and_identity_tampering_rejected(self):
        payload = self.space.manual("2026-06-30")
        write_dated_bundle(self.bundles, payload, repo_root=self.root)
        kap = copy.deepcopy(payload)
        kap["sources"][0]["kind"] = kap["manifest"][0]["kind"] = "KAP_SERIES"
        cases = [("KAP", kap, "outside the dated protocol")]
        for key in ("flow", "concentration", "assessment", "eligible_crossings"):
            forged = copy.deepcopy(payload)
            forged["funds"][0][key] = {"status": "UNAVAILABLE"}
            cases.append((key, forged, "D1-only contract"))
        for key, value in (("ever_crossed", {}), ("first_crossing_dates", {}), ("concentration_extension_schema", "x")):
            forged = copy.deepcopy(payload)
            forged[key] = value
            cases.append((key, forged, "D1-only contract"))
        for key, value in (("origin", "LIVE"), ("findings_scope", "ALL"), ("cutoff_at", "2026-06-30T20:59:59+00:00"),
                           ("knowledge_basis", "POINT_IN_TIME"), ("date_rule", "OTHER")):
            forged = copy.deepcopy(payload)
            forged[key] = value
            cases.append((key, forged, "provenance differs"))
        forged = copy.deepcopy(payload)
        forged["summary"]["d1_unavailable"] -= 1
        forged["summary"]["d1_stale"] += 1
        cases.append(("summary", forged, "summary"))
        forged = copy.deepcopy(payload)
        forged["funds"][0]["date_context"]["has_positive_price_on_or_before_cutoff"] = False
        cases.append(("no-price summary", forged, "summary"))
        forged = copy.deepcopy(payload)
        forged["funds"][3]["category"] = "Synthetic B"
        forged["funds"][3]["d1"]["threshold"] = None
        cases.append(("category", forged, "bounded snapshot"))
        forged = copy.deepcopy(payload)
        forged["funds"][3]["name"] = "Renamed fund"
        cases.append(("name", forged, "bounded snapshot"))
        forged = copy.deepcopy(payload)
        forged["funds"][0]["comment_tr"] = "Seçilen tarihte uyarı yok."
        cases.append(("comment", forged, "comment"))
        forged = copy.deepcopy(payload)
        forged["funds"] = list(reversed(forged["funds"]))
        cases.append(("order", forged, "order"))
        forged = copy.deepcopy(payload)
        forged["funds"][0]["evidence"].append("f" * 64)
        cases.append(("evidence", forged, "unknown source"))
        forged = copy.deepcopy(payload)
        forged["snapshot"]["bound"] = "2026-10-08T00:00:00+00:00"
        cases.append(("bound", forged, "registered bound"))
        forged = copy.deepcopy(payload)
        forged["funds"][5]["code"] = "AAA"
        cases.append(("universe", forged, "universe|100 unique"))
        for label, forged, message in cases:
            with self.subTest(label), self.assertRaisesRegex(BundleIntegrityError, message):
                self.load(forge(self.bundles, forged))
        directory = self.bundles / payload["immutable_bundle_id"]
        raw = json.loads((directory / "bundle.json").read_bytes())
        raw["funds"][0]["name"] = "changed without fingerprint"
        (directory / "bundle.json").write_bytes(canonical_bytes(raw))
        with self.assertRaisesRegex(BundleIntegrityError, "fingerprint"):
            self.load(directory)

    def test_manifest_backed_originals_checked_on_load(self):
        payload = self.space.manual("2026-07-31")
        directory = write_dated_bundle(self.bundles, payload, repo_root=self.root)
        for path in (self.root / PRICE_DIR / "Z10.json", self.space.protocol):
            original = path.read_bytes()
            path.write_bytes(original + b" ")
            with self.subTest(path.name), self.assertRaisesRegex(BundleIntegrityError, "original source changed"):
                self.load(directory)
            path.write_bytes(original)
        self.assertEqual(self.load(directory), payload)
        with self.assertRaisesRegex(BundleIntegrityError, "outside the opened universe"):
            with patch("p50k.research_reviews.dated_bundle._source_bytes", side_effect=AssertionError("read")):
                load_dated_bundle(directory, repo_root=self.root, allowed_codes=CODES[:-1] + ["AAA"])
        with self.assertRaisesRegex(BundleIntegrityError, "requested date"):
            load_dated_bundle(directory, repo_root=self.root, expected_date="2026-06-30")

    def test_loaders_reject_each_others_bundles(self):
        dated = write_dated_bundle(self.bundles, self.space.manual("2026-09-16"), repo_root=self.root)
        with self.assertRaises(BundleIntegrityError):
            load_bundle(dated)
        with self.assertRaises(BundleIntegrityError):
            bundle_v2.load_research_bundle(dated)
        v1_base = self.root / V1_OUTPUT
        original = write_bundle(v1_base, all_missing_bundle())
        with self.assertRaisesRegex(BundleIntegrityError, "schema"):
            self.load(original)
        extended = all_missing_bundle()
        extended.pop("immutable_bundle_id")
        extended["concentration_extension_schema"] = "p50k.fund-concentration.v1"
        extended["immutable_bundle_id"] = digest(canonical_bytes(extended))
        with self.assertRaisesRegex(BundleIntegrityError, "schema"):
            self.load(forge(v1_base, extended))
        relabelled = json.loads((dated / "bundle.json").read_bytes())
        relabelled["schema"] = "p50k.fund-review.v1"
        with self.assertRaises(BundleIntegrityError):
            load_bundle(forge(v1_base, relabelled))

    def test_index_binds_exact_dates_and_rejects_tampering(self):
        payloads = [self.space.manual(day) for day in EXPECTED_GRID]
        for payload in payloads:
            write_dated_bundle(self.bundles, payload, repo_root=self.root)
        index = make_date_index(payloads, protocol_sha256="6" * 64, protocol_commit="7" * 40,
                                calendar_digest="8" * 64, v1_bundle_id="9" * 64)
        base = self.root / OUTPUT / "index"
        directory = write_date_index(base, index, repo_root=self.root, allowed_codes=CODES)
        bundles_before = tree_digest(self.bundles)
        loaded = load_date_index(directory, repo_root=self.root, allowed_codes=CODES)
        self.assertEqual(loaded, index)
        self.assertEqual([entry["date"] for entry in index["entries"]], EXPECTED_GRID)
        self.assertEqual(index["entries"][4]["cutoff_at"], "2026-02-27T23:59:59+03:00")
        self.assertEqual(index["default_date"], "2026-09-16")
        self.assertEqual(index["audit"], {"status": "D1_AND_CHART_EQUAL", "v1_bundle_id": "9" * 64})
        self.assertEqual(sorted(index), sorted(["schema", "date_rule", "default_date", "entries", "protocol_sha256",
                                                "protocol_commit", "calendar_digest", "threshold_provenance",
                                                "snapshot", "audit", "index_id"]))
        text = json.dumps(index)
        for forbidden in ("summary", "Z00", "\"funds\"", "first", "ever", "lead"):
            self.assertNotIn(forbidden, text)
        self.assertEqual(write_date_index(base, index, repo_root=self.root, allowed_codes=CODES), directory)
        self.assertEqual(tree_digest(self.bundles), bundles_before)
        self.assertEqual(load_indexed_bundle(index, "2026-05-26", bundles_dir=self.bundles, repo_root=self.root),
                         payloads[7])
        with self.assertRaises(LookupError):
            index_entry(index, "2026-05-29")
        with self.assertRaises(ValueError):
            index_entry(index, "2026-5-26")

        def mutated(change):
            forged = copy.deepcopy(index)
            change(forged)
            return forged

        other = self.space.manual("2026-01-30", {"protocol_sha256": "a" * 64, "protocol_commit": "7" * 40})
        write_dated_bundle(self.bundles, other, repo_root=self.root)
        cases = {
            "date": lambda i: i["entries"][3].update(date="2026-01-29"),
            "cutoff": lambda i: i["entries"][3].update(cutoff_at="2026-01-30T20:59:59+00:00"),
            "bundle": lambda i: i["entries"][3].update(bundle_id="a" * 64),
            "default": lambda i: i.update(default_date="2026-08-31"),
            "order": lambda i: i["entries"].insert(2, i["entries"].pop(3)),
            "drop": lambda i: i["entries"].pop(5),
            "add": lambda i: i["entries"].append({"date": "2026-09-15", "cutoff_at": "2026-09-15T23:59:59+03:00",
                                                  "bundle_id": "b" * 64}),
            "swap": lambda i: (i["entries"][0].update(bundle_id=index["entries"][1]["bundle_id"]),
                               i["entries"][1].update(bundle_id=index["entries"][0]["bundle_id"])),
            "audit": lambda i: i["audit"].update(status="NOT_RUN"),
            "protocol": lambda i: i.update(protocol_sha256="a" * 64),
            "registration": lambda i: i["entries"][3].update(bundle_id=other["immutable_bundle_id"]),
            "provenance": lambda i: i["threshold_provenance"].update(results_sha256="0" * 64),
            "snapshot": lambda i: i["snapshot"].update(latest_retrieved_at="2026-10-01T00:00:00+00:00"),
            "extra": lambda i: i.update(first_crossing={}),
            "rule": lambda i: i.update(date_rule="OTHER"),
        }
        for label, change in cases.items():
            with self.subTest(label), self.assertRaises(BundleIntegrityError):
                load_date_index(forge(base, mutated(change), "index_id", "index.json"), repo_root=self.root,
                                bundles_dir=self.bundles, allowed_codes=CODES)
        raw = json.loads((directory / "index.json").read_bytes())
        raw["default_date"] = "2026-08-31"
        (directory / "index.json").write_bytes(canonical_bytes(raw))
        with self.assertRaisesRegex(BundleIntegrityError, "fields differ|fingerprint"):
            load_date_index(directory, repo_root=self.root)
        with self.assertRaises(BundleIntegrityError):
            make_date_index([*payloads[:3], other, *payloads[4:]], protocol_sha256="6" * 64,
                            protocol_commit="7" * 40, calendar_digest="8" * 64, v1_bundle_id="9" * 64)
        self.assertEqual(tree_digest(self.bundles) | {}, tree_digest(self.bundles))

    def test_index_refuses_missing_or_corrupt_bundle(self):
        payloads = [self.space.manual(day) for day in EXPECTED_GRID]
        for payload in payloads:
            write_dated_bundle(self.bundles, payload, repo_root=self.root)
        index = make_date_index(payloads, protocol_sha256="6" * 64, protocol_commit="7" * 40,
                                calendar_digest="8" * 64, v1_bundle_id="9" * 64)
        directory = write_date_index(self.root / OUTPUT / "index", index, repo_root=self.root)
        target = self.bundles / payloads[2]["immutable_bundle_id"] / "bundle.json"
        original = target.read_bytes()
        target.write_bytes(original.replace(b'"Synthetic fund Z10"', b'"Synthetic fund Z1X"'))
        with self.assertRaises(BundleIntegrityError):
            load_date_index(directory, repo_root=self.root)
        self.assertEqual(load_date_index(directory, repo_root=self.root, verify_bundles=False), index)
        target.unlink()
        with self.assertRaises(BundleIntegrityError):
            load_date_index(directory, repo_root=self.root)


class DatedBundleContentTests(unittest.TestCase):
    """Load-time checks on assembled payloads with real chart and D1 content."""

    @classmethod
    def setUpClass(cls):
        if not has_numpy():
            raise unittest.SkipTest("dated assembly requires the optional numpy analysis dependency")
        cls.detector = load_frozen_detector(REPO)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.space = Workspace(self.root)
        self.bundles = self.root / OUTPUT / "bundles"
        self.payload = self.space.assembled("2026-03-31", self.detector)
        write_dated_bundle(self.bundles, self.payload, repo_root=self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def load(self, directory: Path) -> dict:
        return load_dated_bundle(directory, repo_root=self.root, allowed_codes=CODES)

    def record(self, payload: dict, state: str) -> dict:
        return next(row for row in payload["funds"] if row["d1_state"] == state and row["chart"]["points"])

    def test_assembled_payload_states_and_summary(self):
        loaded = self.load(self.bundles / self.payload["immutable_bundle_id"])
        summary = loaded["summary"]
        self.assertEqual(summary["record_count"], 100)
        self.assertGreaterEqual(summary["d1_eligible_crossing"], 1)
        self.assertGreaterEqual(summary["d1_eligible_no_crossing"], 1)
        self.assertGreaterEqual(summary["d1_stale"], 1)
        self.assertEqual(summary["no_price_at_cutoff"], 2)
        self.assertEqual(next(row for row in loaded["funds"] if row["code"] == "Z05")["d1_state"], "STALE")
        self.assertEqual(loaded["funds"][0]["code"], "Z00")
        self.assertEqual(loaded["funds"][0]["d1_state"], "ELIGIBLE_CROSSING")
        self.assertTrue(all(row["d1"]["threshold"] in (None, "0.00050") for row in loaded["funds"]))
        kinds = {source["kind"] for source in loaded["sources"]}
        self.assertEqual(kinds, {"PROTOCOL", "UNIVERSE", "CALIBRATION", "SNAPSHOT", "PRICE"})

    def test_nested_dates_and_freshness_checked_on_load(self):
        cutoff = self.payload["cutoff_date"]
        cases = []
        forged = copy.deepcopy(self.payload)
        self.record(forged, "ELIGIBLE_NO_CROSSING")["chart"]["points"].append(
            {"date": "2026-04-01", "fund": "101.0", "peers": "100.5"})
        cases.append(("chart point", forged, "after the bundle cutoff"))
        forged = copy.deepcopy(self.payload)
        self.record(forged, "ELIGIBLE_NO_CROSSING")["d1"]["metric_period"]["end"] = "2026-04-01"
        cases.append(("metric period", forged, "after the bundle cutoff"))
        forged = copy.deepcopy(self.payload)
        self.record(forged, "ELIGIBLE_NO_CROSSING")["chart"]["baseline_date"] = "2026-4-01"
        cases.append(("non-canonical", forged, "canonical"))
        forged = copy.deepcopy(self.payload)
        self.record(forged, "ELIGIBLE_NO_CROSSING")["d1"]["latest_contributing_at"] = "2026-04-01"
        cases.append(("latest", forged, "after the bundle cutoff"))
        forged = copy.deepcopy(self.payload)
        stale = self.record(forged, "STALE")
        stale["d1"].update(freshness="FRESH", missing_reasons=[])
        cases.append(("fresh but old", forged, "freshness"))
        forged = copy.deepcopy(self.payload)
        fresh = self.record(forged, "ELIGIBLE_NO_CROSSING")
        fresh["d1"]["freshness"] = "STALE"
        fresh["d1"]["missing_reasons"] = ["final_contributing_observation_before_cutoff"]
        cases.append(("stale at cutoff", forged, "freshness"))
        forged = copy.deepcopy(self.payload)
        self.record(forged, "ELIGIBLE_NO_CROSSING")["d1"]["research_screen"] = "CROSSING"
        cases.append(("screen", forged, "research screen"))
        forged = copy.deepcopy(self.payload)
        self.record(forged, "ELIGIBLE_NO_CROSSING")["d1_state"] = "ELIGIBLE_CROSSING"
        cases.append(("state", forged, "state or comment|order"))
        forged = copy.deepcopy(self.payload)
        self.record(forged, "ELIGIBLE_NO_CROSSING")["chart"]["points"].reverse()
        cases.append(("point order", forged, "strict date order"))
        bundles = self.root / "forged"
        for label, forged, message in cases:
            with self.subTest(label), self.assertRaisesRegex(BundleIntegrityError, message):
                self.load(forge(bundles, forged))
        later = copy.deepcopy(self.payload)
        later.update(metadata_for("2026-04-30"))
        with self.assertRaises(BundleIntegrityError):
            self.load(forge(bundles, later))
        self.assertEqual(cutoff, "2026-03-31")


AUDIT_FIELD = re.compile(r"(code|name|category|chart|d1\.[a-z_]+)")
AUDIT_SOURCES = (("PROTOCOL", None), ("PREREG", None), ("UNIVERSE", None), ("CALIBRATION", None), ("CODE", None),
                 ("SNAPSHOT", None), ("PRICE", "Z00"), ("PRICE", "Z01"), ("PRICE", "Z02"))


def audit_pair() -> tuple[dict, dict]:
    """A matching dated/v1 pair at 2026-09-16 with different source IDs (invented values)."""
    def sources(prefix: str) -> list[dict]:
        result = []
        for number_, (label, code) in enumerate(AUDIT_SOURCES):
            kind = "PROTOCOL" if label == "PREREG" else label
            # Code and snapshot digests legitimately differ between the two views.
            sha = f"{number_ + 1:x}" * 64 if kind in ("PRICE", "UNIVERSE", "CALIBRATION") else \
                hashlib.sha256(f"{prefix}{label}".encode()).hexdigest()
            result.append({"source_id": f"{prefix}-{label}{'-' + code if code else ''}", "kind": kind,
                           "fund_code": code, "sha256": sha, "label": f"{prefix} label"})
        return result

    def record(prefix: str, code: str, statistic: str) -> dict:
        d1 = empty_finding("d1")
        d1.update(arithmetic_status="AVAILABLE", research_screen="NO_CROSSING", freshness="FRESH",
                  statistic=statistic, threshold="0.00050", metric_period={"start": "2026-06-22", "end": "2026-09-16"},
                  usable_observations=55, window_positions=60, eligible_peers=12, latest_contributing_at="2026-09-16",
                  input_refs=[f"{prefix}-{label}{'-' + fund if fund else ''}" for label, fund in AUDIT_SOURCES])
        chart = {"status": "AVAILABLE", "reason": None, "baseline_date": "2026-06-22", "unit": "INDEX_100",
                 "points": [{"date": "2026-06-22", "fund": "100", "peers": "100"},
                            {"date": "2026-09-16", "fund": "101.25", "peers": "100.75"}], "peer_count": 12}
        return {"code": code, "name": f"Synthetic fund {code}", "category": "Synthetic A", "d1": d1, "chart": chart,
                "comment_tr": f"{prefix} comment", "evidence": list(d1["input_refs"])}

    dated = {"funds": [record("dated", "Z00", "0.00012"), record("dated", "Z01", "0.00034")],
             "sources": sources("dated")}
    v1 = {"funds": [record("v1", "Z00", "0.00012"), record("v1", "Z01", "0.00034")], "sources": sources("v1")}
    for row in v1["funds"]:
        row["flow"] = {"status": "UNAVAILABLE"}
    for row in dated["funds"]:
        row.update(d1_state="ELIGIBLE_NO_CROSSING", date_context={"has_positive_price_on_or_before_cutoff": True})
    return dated, v1


class V1EquivalenceAuditTests(unittest.TestCase):
    """Direct tests of the phase-2 comparison: exact field names, never values."""

    @classmethod
    def setUpClass(cls):
        cls.runner = load_module(RUNNER_PATH, "synthetic_dated_runner_audit")

    def assert_reports(self, dated: dict, v1: dict, expected: list[str], *values: str) -> None:
        differences = self.runner.compare_with_v1(dated, v1)
        self.assertEqual(differences, expected)
        for field in differences:
            self.assertIsNotNone(AUDIT_FIELD.fullmatch(field), field)
        text = ", ".join(differences)
        for value in (*values, "Z00", "Z01", "Z02", "Synthetic", "dated-", "v1-", "0.000"):
            self.assertNotIn(value, text)

    @staticmethod
    def source(payload: dict, label: str) -> dict:
        return next(source for source in payload["sources"] if source["source_id"].split("-", 1)[1] == label)

    def test_matching_pair_reports_nothing(self):
        dated, v1 = audit_pair()
        self.assertNotEqual({s["source_id"] for s in dated["sources"]}, {s["source_id"] for s in v1["sources"]})
        self.assert_reports(dated, v1, [])

    def test_one_d1_field_reports_exactly_that_field(self):
        changes = (
            ("statistic", lambda d, v: d["funds"][1]["d1"].update(statistic="0.00099"), "d1.statistic", "0.00099"),
            ("missing reason", lambda d, v: v["funds"][0]["d1"]["missing_reasons"].append("synthetic_reason"),
             "d1.missing_reasons", "synthetic_reason"),
            ("metric period", lambda d, v: d["funds"][0]["d1"]["metric_period"].update(start="2026-06-23"),
             "d1.metric_period", "2026-06-23"),
            ("latest", lambda d, v: d["funds"][0]["d1"].update(latest_contributing_at="2026-09-15"),
             "d1.latest_contributing_at", "2026-09-15"),
            ("threshold", lambda d, v: v["funds"][1]["d1"].update(threshold="0.00051"), "d1.threshold", "0.00051"),
            ("screen", lambda d, v: d["funds"][1]["d1"].update(research_screen="CROSSING"), "d1.research_screen",
             "CROSSING"),
            ("extra key", lambda d, v: d["funds"][0]["d1"].update(first_crossing="2026-01-30"),
             "d1.first_crossing", "2026-01-30"),
        )
        for label, change, field, value in changes:
            dated, v1 = audit_pair()
            change(dated, v1)
            with self.subTest(label):
                self.assert_reports(dated, v1, [field], value)

    def test_one_chart_point_reports_chart(self):
        for label, change in (("value", lambda c: c["points"][1].update(fund="101.26")),
                              ("dropped", lambda c: c["points"].pop()),
                              ("baseline", lambda c: c.update(baseline_date="2026-06-19"))):
            dated, v1 = audit_pair()
            change(dated["funds"][0]["chart"])
            with self.subTest(label):
                self.assert_reports(dated, v1, ["chart"], "101.26", "2026-06-19")
        dated, v1 = audit_pair()
        dated["funds"][1]["chart"]["points"][0]["peers"] = "99.5"
        dated["funds"][1]["d1"]["statistic"] = "0.00035"
        self.assert_reports(dated, v1, ["chart", "d1.statistic"], "99.5", "0.00035")

    def test_audited_reference_changes_report_input_refs(self):
        def drop(payload: dict, code: str, label: str) -> None:
            row = next(row for row in payload["funds"] if row["code"] == code)
            row["d1"]["input_refs"].remove(self.source(payload, label)["source_id"])

        changes = (
            ("price sha", lambda d, v: self.source(d, "PRICE-Z00").update(sha256="e" * 64)),
            ("peer price sha", lambda d, v: self.source(v, "PRICE-Z02").update(sha256="e" * 64)),
            ("price fund code", lambda d, v: self.source(d, "PRICE-Z01").update(fund_code="Z02")),
            ("price relabelled as code", lambda d, v: self.source(d, "PRICE-Z02").update(kind="CODE")),
            ("peer price dropped", lambda d, v: drop(d, "Z00", "PRICE-Z02")),
            ("own price dropped from v1", lambda d, v: drop(v, "Z01", "PRICE-Z01")),
            ("universe sha", lambda d, v: self.source(d, "UNIVERSE").update(sha256="e" * 64)),
            ("calibration dropped", lambda d, v: drop(d, "Z01", "CALIBRATION")),
        )
        for label, change in changes:
            dated, v1 = audit_pair()
            change(dated, v1)
            with self.subTest(label):
                self.assert_reports(dated, v1, ["d1.input_refs"], "e" * 64)

    def test_unaudited_reference_kinds_report_nothing(self):
        def add(payload: dict, kind: str) -> None:
            source = {"source_id": f"extra-{kind}", "kind": kind, "fund_code": None, "sha256": "d" * 64}
            payload["sources"].append(source)
            for row in payload["funds"]:
                row["d1"]["input_refs"].append(source["source_id"])

        def drop(payload: dict, label: str) -> None:
            identifier = self.source(payload, label)["source_id"]
            for row in payload["funds"]:
                row["d1"]["input_refs"].remove(identifier)

        changes = (
            ("code added", lambda d, v: add(d, "CODE")), ("protocol added", lambda d, v: add(v, "PROTOCOL")),
            ("snapshot added", lambda d, v: add(d, "SNAPSHOT")), ("code removed", lambda d, v: drop(d, "CODE")),
            ("protocol removed", lambda d, v: drop(v, "PREREG")), ("snapshot removed", lambda d, v: drop(d, "SNAPSHOT")),
            ("snapshot sha", lambda d, v: self.source(d, "SNAPSHOT").update(sha256="d" * 64)),
            ("code sha", lambda d, v: self.source(v, "CODE").update(sha256="d" * 64)),
        )
        for label, change in changes:
            dated, v1 = audit_pair()
            change(dated, v1)
            with self.subTest(label):
                self.assert_reports(dated, v1, [])

    def test_reference_missing_from_sources_reports_input_refs(self):
        def missing(payload: dict, label: str) -> None:
            identifier = self.source(payload, label)["source_id"]
            payload["sources"] = [s for s in payload["sources"] if s["source_id"] != identifier]

        changes = (
            ("unknown dated ref", lambda d, v: d["funds"][0]["d1"]["input_refs"].append("dated-unknown")),
            ("unknown v1 ref", lambda d, v: v["funds"][1]["d1"]["input_refs"].append("v1-unknown")),
            ("dated code source missing", lambda d, v: missing(d, "CODE")),
            ("v1 price source missing", lambda d, v: missing(v, "PRICE-Z00")),
            ("v1 input_refs absent", lambda d, v: v["funds"][0]["d1"].pop("input_refs")),
            ("v1 input_refs not a list", lambda d, v: v["funds"][0]["d1"].update(input_refs=None)),
        )
        for label, change in changes:
            dated, v1 = audit_pair()
            change(dated, v1)
            with self.subTest(label):
                self.assert_reports(dated, v1, ["d1.input_refs"], "unknown")

    def test_identity_and_universe_differences(self):
        for field in ("name", "category"):
            dated, v1 = audit_pair()
            v1["funds"][0][field] = "Synthetic changed"
            with self.subTest(field):
                self.assert_reports(dated, v1, [field], "changed")
        dated, v1 = audit_pair()
        v1["funds"].pop()
        self.assert_reports(dated, v1, ["code"])
        dated, v1 = audit_pair()
        dated["funds"][0]["comment_tr"] = "different dated comment"
        v1["funds"][1]["flow"] = {"status": "AVAILABLE"}
        self.assert_reports(dated, v1, [])


class FakeRepo:
    """Hermetic synthetic repository with the dated and v1 registrations committed."""

    def __init__(self, root: Path, *, crlf: Path | None = None, results_overrides: dict | None = None,
                 ignore_raw: bool = True):
        self.root = init_repo(root)
        self.runner = load_module(RUNNER_PATH, "synthetic_dated_runner")
        for relative in (self.runner.RUNNER_REL, *self.runner.DATED_MODULES, *self.runner.V1_RUNTIME,
                         DETECTOR_REL, EVENT_REL / "fund_review_app/run.py"):
            copy_registered(root, relative)
        write(root, self.runner.PROTOCOL_REL, b"Synthetic dated protocol for tests only.\n")
        write(root, EVENT_REL / "fund_review_app/PROTOCOL.md", b"Synthetic fixed protocol for tests only.\n")
        preregistration = write(root, PREREGISTRATION_REL, b"Synthetic preregistration.\n").read_bytes()
        write(root, RESULTS_REL, results_bytes((root / DETECTOR_REL).read_bytes(), preregistration,
                                               **(results_overrides or {})))
        write(root, self.runner.ALLOWLIST_REL, ("\n".join(CODES) + "\n").encode())
        write(root, ".gitignore", b"/raw/\n" if ignore_raw else b"")
        if crlf is not None:
            path = root / crlf
            path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
        self.head = commit_all(root)
        self.db = write_inputs(root)
        write(root, "raw/kap/series/Z00.json", json.dumps({"fund": "Z00", "source": "KAP Portföy Dağılım Raporu",
                                                          "reports": []}).encode())

    def run(self, v1_bundle: Path, **kwargs) -> dict:
        return self.runner.run_research(v1_bundle=v1_bundle, repo_root=self.root, snapshot_db=self.db, **kwargs)

    def v1(self) -> Path:
        runner = load_module(V1_RUNNER_PATH, "synthetic_v1_runner")
        return Path(runner.run_research(repo_root=self.root, snapshot_db=self.db)["directory"])


class ReadScope:
    """Record file reads; any raw/kap access or listing of the price directory raises."""

    def __init__(self):
        self.events: list[tuple[str, str]] = []
        self._patches = []

    def check(self, path, action: str) -> None:
        text = Path(os.fsdecode(path)).absolute().as_posix()
        if "/raw/kap" in text:
            raise AssertionError(f"KAP path touched ({action})")
        if action == "list" and "/raw/tefas/prices" in text:
            raise AssertionError("price directory listed")
        self.events.append((action, text))

    def __enter__(self):
        scope = self

        def wrap(original, action):
            def wrapper(path, *args, **kwargs):
                scope.check(path, action)
                return original(path, *args, **kwargs)
            return wrapper

        for name, action in (("read_bytes", "read"), ("read_text", "read"), ("open", "read"), ("exists", "stat"),
                             ("is_file", "stat"), ("is_dir", "stat"), ("stat", "stat"), ("iterdir", "list"),
                             ("glob", "list"), ("rglob", "list"), ("walk", "list")):
            self._patches.append(patch.object(Path, name, wrap(getattr(Path, name), action)))
        for name in ("listdir", "scandir"):
            original = getattr(os, name)

            def lister(path=".", *args, __original=original):
                if not isinstance(path, int):
                    scope.check(path, "list")
                return __original(path, *args)
            self._patches.append(patch.object(os, name, lister))
        open_original = builtins.open

        def opener(file, *args, **kwargs):
            if isinstance(file, (str, bytes, os.PathLike)):
                scope.check(file, "read")
            return open_original(file, *args, **kwargs)
        self._patches.append(patch.object(builtins, "open", opener))
        connect_original = sqlite3.connect

        def connect(database, *args, **kwargs):
            scope.events.append(("sqlite", str(database)))
            return connect_original(database, *args, **kwargs)
        self._patches.append(patch.object(sqlite3, "connect", connect))
        for item in self._patches:
            item.start()
        return self

    def __exit__(self, *exc):
        for item in reversed(self._patches):
            item.stop()
        return False


class DatedRunnerRefusalTests(unittest.TestCase):
    """Registration gates; no numpy needed because every case refuses before D1."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "repo"
        self.repo = FakeRepo(self.root)
        self.runner = self.repo.runner

    def tearDown(self):
        self.tmp.cleanup()

    @contextlib.contextmanager
    def no_fund_reads(self):
        with patch.object(self.runner, "read_fund_json", side_effect=AssertionError("fund input read")), \
                patch.object(self.runner, "bounded_snapshot", side_effect=AssertionError("snapshot read")):
            yield

    def refuse(self, pattern: str, **kwargs) -> None:
        with self.no_fund_reads(), self.assertRaisesRegex(ValueError, pattern):
            self.repo.run(self.root / V1_OUTPUT / ("0" * 64), **kwargs)

    def test_registration_refusals_before_any_fund_read(self):
        with self.no_fund_reads(), self.assertRaisesRegex(AssertionError, "snapshot read"):
            self.repo.run(self.root / V1_OUTPUT / ("0" * 64))
        for relative in self.runner.REGISTERED:
            path = self.root / relative
            original = path.read_bytes()
            path.write_bytes(original + b"\n")
            with self.subTest(relative.as_posix()):
                self.refuse("differs from committed HEAD: " + relative.as_posix())
            path.write_bytes(original)
            path.unlink()
            with self.subTest(f"missing {relative.as_posix()}"):
                self.refuse("registered file is missing")
            path.write_bytes(original)
        module = self.runner.DATED_MODULES[2]
        git(self.root, "rm", "-q", "--cached", module.as_posix())
        git(self.root, "commit", "-q", "--no-verify", "-m", "Synthetic: untrack a dated module")
        self.refuse("not committed")

    def test_executed_runtime_must_equal_committed_bytes(self):
        """The modules that actually run come from sys.path; their bytes must equal the committed blobs."""
        executed = self.runner.executed_sources()
        self.assertEqual([relative for _, relative in executed],
                         [self.runner.RUNNER_REL, *self.runner.DATED_MODULES, *self.runner.V1_RUNTIME])
        self.assertEqual(len({path for path, _ in executed}), len(executed))
        # A committed copy in the sealing repository that differs from the code that runs.
        relative = self.runner.DATED_MODULES[1]
        path = self.root / relative
        path.write_bytes(path.read_bytes() + b"# synthetic committed edit\n")
        commit_all(self.root, "Synthetic: commit a different dated module")
        self.refuse("executed module differs from the committed copy: " + relative.as_posix())
        git(self.root, "reset", "-q", "--hard", self.repo.head)
        # Every executed file, including the runner itself, is checked separately.
        with tempfile.TemporaryDirectory() as tmp:
            for index, (source, relative) in enumerate(executed):
                changed = Path(tmp) / f"executed_{index}.py"
                changed.write_bytes(source.read_bytes() + b"\n")
                if relative == self.runner.RUNNER_REL:
                    target = self.runner
                else:
                    target = importlib.import_module(dict((rel, name) for name, rel in
                                                          self.runner.EXECUTED_RUNTIME)[relative])
                with self.subTest(relative.as_posix()), patch.object(target, "__file__", str(changed)):
                    self.refuse("executed module differs from the committed copy: " + relative.as_posix())
        with self.no_fund_reads(), self.assertRaisesRegex(AssertionError, "snapshot read"):
            self.repo.run(self.root / V1_OUTPUT / ("0" * 64))

    def test_crlf_and_calibration_bindings_refuse(self):
        for relative in (self.runner.DATED_MODULES[1], self.runner.PROTOCOL_REL):
            with tempfile.TemporaryDirectory() as tmp:
                repo = FakeRepo(Path(tmp) / "crlf", crlf=relative)
                self.assertIn(b"\r\n", git(repo.root, "show", f"HEAD:{relative.as_posix()}"))
                with patch.object(repo.runner, "read_fund_json", side_effect=AssertionError("fund input read")), \
                        self.assertRaisesRegex(ValueError, "CRLF line endings.*" + relative.as_posix()):
                    repo.run(repo.root / V1_OUTPUT / ("0" * 64))
        for overrides, message in (({"detectors_sha256": "0" * 64}, "frozen detector"),
                                   ({"preregistration_sha256": "0" * 64}, "preregistration"),
                                   ({"run_at_utc": "2026-10-07T08:52:12+00:00"}, "snapshot bound")):
            with tempfile.TemporaryDirectory() as tmp:
                repo = FakeRepo(Path(tmp) / "calibration", results_overrides=overrides)
                with patch.object(repo.runner, "read_fund_json", side_effect=AssertionError("fund input read")), \
                        self.assertRaisesRegex(ValueError, message):
                    repo.run(repo.root / V1_OUTPUT / ("0" * 64))

    def test_protocol_change_guard_and_output_refusals(self):
        index_dir = self.root / OUTPUT / "index" / ("c" * 64)
        write(index_dir, "index.json", json.dumps({"protocol_sha256": "0" * 64}).encode())
        self.refuse("different protocol")
        (index_dir / "index.json").write_bytes(b"{not json")
        self.refuse("unreadable")
        (index_dir / "index.json").unlink()
        index_dir.rmdir()
        self.refuse("canonical", out_dir=self.root / "public")
        self.refuse("canonical", out_dir=self.root / V1_OUTPUT)
        for codes in (["AAA"], CODES[:-1], CODES + ["AAA"]):
            with patch.object(Path, "exists", side_effect=AssertionError("path resolved")):
                with self.subTest(len(codes)), self.assertRaises(ValueError):
                    self.runner.run_research(v1_bundle=self.root, repo_root=self.root, codes=codes)
        self.assertFalse((self.root / V1_OUTPUT).exists())
        self.assertEqual(tree_digest(self.root / OUTPUT), {})
        with tempfile.TemporaryDirectory() as tmp:
            repo = FakeRepo(Path(tmp) / "unignored", ignore_raw=False)
            with patch.object(repo.runner, "read_fund_json", side_effect=AssertionError("fund input read")), \
                    self.assertRaisesRegex(ValueError, "Git-ignored"):
                repo.run(repo.root / V1_OUTPUT / ("0" * 64))

    def test_cli_has_no_cutoff_argument_and_prints_ascii(self):
        for argv in (["--cutoff", "2026-01-30"], ["--date", "2026-01-30"], ["--v1", "x"],
                     ["--v1-bundle", "x", "--cutoff", "2026-01-30"], []):
            stderr = io.StringIO()
            with patch.object(self.runner, "run_research", side_effect=AssertionError("ran")), \
                    contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(io.StringIO()), \
                    self.assertRaises(SystemExit) as raised:
                self.runner.main(argv)
            self.assertEqual(raised.exception.code, 2, argv)
        stderr = io.StringIO()
        with patch.object(self.runner, "run_research", side_effect=ValueError("ş refused")), \
                contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit) as raised:
            self.runner.main(["--v1-bundle", "x"])
        self.assertEqual(raised.exception.code, 2)
        self.assertTrue(stderr.getvalue().isascii())
        self.assertIn("Dated research refused", stderr.getvalue())


class DatedRunnerSealTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not has_numpy():
            raise unittest.SkipTest("the dated runner requires the optional numpy analysis dependency")
        cls.tmp = tempfile.TemporaryDirectory()
        cls.repo = FakeRepo(Path(cls.tmp.name) / "repo")
        cls.root = cls.repo.root
        cls.v1_bundle = cls.repo.v1()
        cls.v1_before = tree_digest(cls.root / V1_OUTPUT)
        cls.stdout = io.StringIO()
        with ReadScope() as scope, contextlib.redirect_stdout(cls.stdout):
            cls.result = cls.repo.run(cls.v1_bundle)
        cls.scope = scope

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_committed_run_seals_12_bundles_and_index(self):
        index = self.result["index"]
        self.assertEqual(self.result["grid"], EXPECTED_GRID)
        self.assertEqual(index["audit"], {"status": "D1_AND_CHART_EQUAL",
                                          "v1_bundle_id": self.v1_bundle.name})
        self.assertEqual(index["protocol_commit"], self.repo.head)
        loaded = load_date_index(Path(self.result["index_directory"]), repo_root=self.root, allowed_codes=CODES)
        self.assertEqual(loaded, index)
        self.assertEqual(len(list((self.root / OUTPUT / "bundles").iterdir())), 12)
        for entry in index["entries"]:
            bundle = load_dated_bundle(self.root / OUTPUT / "bundles" / entry["bundle_id"], repo_root=self.root,
                                       expected_date=entry["date"])
            self.assertEqual(len(bundle["funds"]), 100)
            self.assertEqual(bundle["summary"]["record_count"], 100)
            self.assertEqual(bundle["registration"]["protocol_commit"], self.repo.head)
            self.assertFalse(any(source["kind"].startswith("KAP") for source in bundle["sources"]))
        early = load_dated_bundle(self.root / OUTPUT / "bundles" / index["entries"][0]["bundle_id"],
                                  repo_root=self.root)
        self.assertEqual(early["summary"]["no_price_at_cutoff"], 3)
        self.assertEqual(tree_digest(self.root / V1_OUTPUT), self.v1_before)
        self.assertEqual(self.stdout.getvalue(), "")

    def test_reads_only_opened_price_files_and_never_kap(self):
        reads = [path for action, path in self.scope.events if action == "read"]
        prices = (self.root / PRICE_DIR).absolute().as_posix() + "/"
        price_reads = {path for path in reads if path.startswith(prices)}
        self.assertEqual(price_reads, {f"{prices}{code}.json" for code in CODES[:98]})
        registered = {(self.root / relative).absolute().as_posix() for relative in self.runner_registered()}
        # The executed runtime files are read once to compare them with the committed blobs.
        executed = {path.absolute().as_posix() for path, _ in self.repo.runner.executed_sources()}
        self.assertTrue(executed <= set(reads))
        v1_json = (self.v1_bundle / "bundle.json").absolute().as_posix()
        output = (self.root / OUTPUT).absolute().as_posix() + "/"
        unexpected = {path for path in reads if path not in registered and path not in price_reads and
                      path not in executed and path != v1_json and not path.startswith(output)}
        self.assertEqual(unexpected, set())
        first_v1 = next(i for i, event in enumerate(self.scope.events) if event == ("read", v1_json))
        first_price = {path: next(i for i, event in enumerate(self.scope.events) if event == ("read", path))
                       for path in price_reads}
        self.assertLess(max(first_price.values()), first_v1)
        sqlite_events = [i for i, event in enumerate(self.scope.events) if event[0] == "sqlite"]
        self.assertTrue(sqlite_events)
        self.assertLess(sqlite_events[0], first_v1)
        self.assertEqual({path for path in reads if path.startswith((self.root / V1_OUTPUT).absolute().as_posix())},
                         {v1_json})

    def runner_registered(self):
        return self.repo.runner.REGISTERED

    def test_identical_rerun_reuses_bytes(self):
        before = tree_digest(self.root / OUTPUT)
        with contextlib.redirect_stdout(io.StringIO()):
            again = self.repo.run(self.v1_bundle)
        self.assertEqual(again["index"]["index_id"], self.result["index"]["index_id"])
        self.assertEqual(tree_digest(self.root / OUTPUT), before)

    def test_equivalence_audit_precedes_any_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = FakeRepo(Path(tmp) / "audit")
            # A post-bound snapshot row moves one fund for the unbounded v1 view only.
            sql(repo.db, "INSERT INTO fund_snapshots VALUES(?,?,?,?)",
                ("Z10", "Synthetic Moved", '{"fonUnvan":"Synthetic fund Z10"}', "2026-10-09T00:00:00+00:00"))
            moved = repo.v1()
            with self.assertRaises(ValueError) as raised:
                repo.run(moved)
            message = str(raised.exception)
            self.assertIn("differing fields: ", message)
            self.assertIn("category", message)
            for leaked in ("Synthetic Moved", "Z10", "0.0", "Synthetic A"):
                self.assertNotIn(leaked, message)
            self.assertEqual(tree_digest(Path(tmp) / "audit" / OUTPUT), {})
            sql(repo.db, "DELETE FROM fund_snapshots WHERE category=?", ("Synthetic Moved",))
            matching = repo.v1()
            # A v1 bundle that differs only in one d1 field: refused by field name, nothing written.
            v1_payload = json.loads((matching / "bundle.json").read_bytes())
            record = next(row for row in v1_payload["funds"] if row["d1"]["statistic"] is not None)
            record["d1"]["statistic"] = "0.987654321"
            forged_v1 = forge(Path(tmp) / "audit" / V1_OUTPUT, v1_payload)
            with self.assertRaises(ValueError) as raised:
                repo.run(forged_v1)
            message = str(raised.exception)
            self.assertTrue(message.endswith("differing fields: d1.statistic"), message)
            for leaked in ("0.987654321", record["code"], record["name"]):
                self.assertNotIn(leaked, message)
            self.assertEqual(tree_digest(Path(tmp) / "audit" / OUTPUT), {})
            original = repo.runner.compare_with_v1

            def tampering(dated, v1_payload):
                dated["funds"][0]["comment_tr"] = "changed during phase 2"
                return original(dated, v1_payload)
            with patch.object(repo.runner, "compare_with_v1", tampering), \
                    self.assertRaisesRegex(ValueError, "phase-1 payloads changed"):
                repo.run(matching)
            self.assertEqual(tree_digest(Path(tmp) / "audit" / OUTPUT), {})
            with self.assertRaisesRegex(ValueError, "v1-bundle"):
                repo.run(Path(tmp) / "audit" / OUTPUT / ("d" * 64))
            self.assertEqual(tree_digest(Path(tmp) / "audit" / OUTPUT), {})


if __name__ == "__main__":
    unittest.main()
