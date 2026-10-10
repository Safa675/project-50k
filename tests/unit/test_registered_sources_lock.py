"""Tripwire: registered v1/v2 sources must keep their committed bytes.

Every sealed fund-review bundle re-hashes these files on load, so an in-place edit
retires every sealed bundle and the research API answers 503.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LOCK_PATH = Path(__file__).resolve().with_name("registered_sources.lock.json")
EVENT = "research/events/2026-09-17-spk-liquidations"
FAILURE = ("Registered source bytes changed: {paths}. Editing these files retires every sealed "
           "v1/v2 bundle (API 503); add a new versioned file instead.")


def load_lock() -> dict:
    return json.loads(LOCK_PATH.read_bytes())


def lock_mismatches(root: Path, lock: dict) -> list[str]:
    """Paths whose working bytes (CRLF normalised to LF) differ from the lock."""
    changed = []
    for entry in lock["files"]:
        path = Path(root) / entry["path"]
        if not path.is_file():
            changed.append(entry["path"])
            continue
        data = path.read_bytes().replace(b"\r\n", b"\n")
        if len(data) != entry["bytes"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
            changed.append(entry["path"])
    return changed


def _load_runner(relative: str, name: str):
    spec = importlib.util.spec_from_file_location(name, REPO / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class RegisteredSourceLockTests(unittest.TestCase):
    def test_registered_files_match_lock(self):
        lock = load_lock()
        changed = lock_mismatches(REPO, lock)
        self.assertEqual(changed, [], FAILURE.format(paths=", ".join(changed)))

    def test_committed_head_blobs_match_lock(self):
        lock = load_lock()
        changed = []
        for entry in lock["files"]:
            result = subprocess.run(["git", "-C", str(REPO), "show", f"HEAD:{entry['path']}"],
                                    capture_output=True, check=False)
            if result.returncode:
                self.skipTest("repository HEAD is not readable with git")
            if hashlib.sha256(result.stdout).hexdigest() != entry["sha256"] or len(result.stdout) != entry["bytes"]:
                changed.append(entry["path"])
        self.assertEqual(changed, [], FAILURE.format(paths=", ".join(changed)))

    def test_negative_control_reports_one_changed_byte(self):
        lock = load_lock()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for entry in lock["files"]:
                destination = root / entry["path"]
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes((REPO / entry["path"]).read_bytes().replace(b"\r\n", b"\n"))
            self.assertEqual(lock_mismatches(root, lock), [])
            target = root / lock["files"][-1]["path"]
            data = bytearray(target.read_bytes())
            data[0] ^= 1
            target.write_bytes(bytes(data))
            self.assertEqual(lock_mismatches(root, lock), [lock["files"][-1]["path"]])
            (root / lock["files"][0]["path"]).write_bytes((REPO / lock["files"][0]["path"]).read_bytes() + b"\r\n")
            self.assertEqual(lock_mismatches(root, lock), [lock["files"][0]["path"], lock["files"][-1]["path"]])

    def test_lock_covers_both_runner_registration_lists(self):
        v1 = _load_runner(f"{EVENT}/fund_review_app/run.py", "lock_check_fund_review_runner")
        v2 = _load_runner(f"{EVENT}/fund_concentration_app/run.py", "lock_check_concentration_runner")
        registered = {path.as_posix() for path in (v1.PROTOCOL_REL, v1.ALLOWLIST_REL, v1.CALIBRATION_REL,
                                                   v1.DETECTOR_REL, *v1.RUNTIME_FILES, v2.PROTOCOL_REL,
                                                   v2.ALLOWLIST_REL, *v2.RUNTIME_FILES)}
        self.assertEqual(len(registered), 19)
        locked = [entry["path"] for entry in load_lock()["files"]]
        self.assertEqual(len(locked), len(set(locked)))
        self.assertEqual(set(locked), registered | {f"{EVENT}/price_detectors/PREREGISTRATION.md"})
        self.assertRegex(load_lock()["commit"], r"^[0-9a-f]{40}$")


if __name__ == "__main__":
    unittest.main()
