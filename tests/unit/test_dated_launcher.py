"""Dated API launcher checks on a hermetic synthetic repository; only test-owned ports are used.

Bundles and the index are sealed with B1's writers; the protocol commit is a real
commit of the temp repository, whose committed PROTOCOL.md is the bundles' PROTOCOL
source and gives the registered protocol SHA-256. Every main() call captures stdout
and stderr.
"""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

try:
    import httpx2  # noqa: F401 - same optional extras as the API suites
    import p50k.api.dated_app  # noqa: F401
except ImportError:
    API_AVAILABLE = False
else:
    API_AVAILABLE = True

from tests.unit import test_fund_review_dated_bundle as bundle_tests
from tests.unit._hermetic_git import commit_all, git, init_repo, write
from tests.unit.test_dated_research_api import seal_index
from tests.unit.test_fund_review_dated_bundle import CODES, OUTPUT, Workspace

PATH = Path(__file__).resolve().parents[2] / "ops/local/run_dated_app.py"
SPEC = importlib.util.spec_from_file_location("p50k_dated_launcher_tests", PATH)
LAUNCHER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LAUNCHER)


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def ipv6_loopback_available() -> bool:
    if not socket.has_ipv6:
        return False
    try:
        with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as probe:
            probe.bind(("::1", 0))
    except OSError:
        return False
    return True


def workspace_with_registered_protocol(root: Path) -> Workspace:
    """B1's Workspace, with its PROTOCOL source written at the dated PROTOCOL.md path."""
    def write_protocol_at_registered_path(base, relative, data):
        return write(base, LAUNCHER.PROTOCOL_REL if str(relative) == "protocol.md" else relative, data)

    with patch.object(bundle_tests, "write", write_protocol_at_registered_path):
        return Workspace(root)


def run(argv: list[str], **environment) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    names = ("P50K_DATED_INDEX", "P50K_DATED_API_ORIGIN")
    cleaned = {key: value for key, value in os.environ.items() if key not in names}
    with patch.dict(os.environ, {**cleaned, **environment}, clear=True), \
            contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = LAUNCHER.main(argv)
        except SystemExit as exc:
            code = exc.code
    return code, out.getvalue(), err.getvalue()


@unittest.skipUnless(API_AVAILABLE, "Optional API dependencies missing; run locked .venv API suite")
class DatedLauncherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = init_repo(Path(cls.temp.name) / "repo")
        write(cls.root, ".gitignore", b"/raw/\n")
        cls.space = workspace_with_registered_protocol(cls.root)
        write(cls.root, LAUNCHER.UNIVERSE_REL, ("\n".join(CODES) + "\n").encode())
        cls.head = commit_all(cls.root)
        cls.protocol_sha256 = hashlib.sha256((cls.root / LAUNCHER.PROTOCOL_REL).read_bytes()).hexdigest()
        registration = {"protocol_sha256": cls.protocol_sha256, "protocol_commit": cls.head}
        cls.index, cls.index_dir, cls.payloads = seal_index(cls.space, cls.root / OUTPUT, registration)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        patcher = patch.object(LAUNCHER, "ROOT", self.root)
        patcher.start()
        self.addCleanup(patcher.stop)

    def check(self, index_dir: Path, **environment) -> tuple[int, str, str]:
        return run(["--index", str(index_dir), "--check", "--api-port", str(free_port())], **environment)

    def assert_refused(self, result: tuple[int, str, str], pattern: str) -> None:
        code, out, err = result
        self.assertEqual(code, 1, out + err)
        self.assertRegex(err, pattern)
        self.assertNotIn(str(self.root), out + err)
        self.assertTrue((out + err).isascii())

    def test_exact_index_required_and_never_listed(self):
        code, out, err = run(["--check"])
        self.assertEqual(code, 2)
        self.assertIn("--index", err)
        self.assertTrue((out + err).isascii())
        code, _, err = run(["--ind", str(self.index_dir), "--check"], P50K_DATED_INDEX=str(self.index_dir))
        self.assertEqual(code, 2, "abbreviated options are refused")
        # An output root or a bundles directory is not an index: never the newest one.
        self.assert_refused(self.check(self.root / OUTPUT), "Date index failed verification")
        self.assert_refused(self.check(self.root / OUTPUT / "index"), "Date index failed verification")
        listed = []

        def recording(original):
            def wrapper(path=".", *args, **kwargs):
                listed.append(str(path))
                return original(path, *args, **kwargs)
            return wrapper

        with patch("os.listdir", recording(os.listdir)), patch("os.scandir", recording(os.scandir)):
            code, out, err = self.check(self.index_dir)
        self.assertEqual(code, 0, out + err)
        output = str((self.root / OUTPUT).absolute())
        self.assertFalse([path for path in listed if str(Path(path).absolute()).startswith(output)], listed)

    def test_check_passes_on_valid_index_and_prints_frontend_origin(self):
        port = free_port()
        code, out, err = run(["--index", str(self.index_dir), "--check", "--api-port", str(port)])
        self.assertEqual(code, 0, out + err)
        self.assertIn(self.index["index_id"], out)
        self.assertIn("12 sealed bundles", out)
        self.assertIn(f"P50K_DATED_API_ORIGIN=http://127.0.0.1:{port}", out)
        self.assertNotIn("Warning", out)
        self.assertEqual(err, "")
        self.assertTrue(out.isascii())
        code, out, err = run(["--check", "--api-port", str(port)], P50K_DATED_INDEX=str(self.index_dir),
                             P50K_DATED_API_ORIGIN="http://127.0.0.1:9999")
        self.assertEqual(code, 0, out + err)
        self.assertIn("Warning: P50K_DATED_API_ORIGIN is http://127.0.0.1:9999", out)
        self.assertTrue(out.isascii())

    def test_check_fails_on_missing_or_corrupt_bundle(self):
        day = self.index["entries"][5]["date"]
        directory = self.root / OUTPUT / "bundles" / self.index["entries"][5]["bundle_id"]
        target = directory / "bundle.json"
        original = target.read_bytes()
        self.addCleanup(target.write_bytes, original)
        target.write_bytes(original.replace(b'"Synthetic fund Z10"', b'"Synthetic fund Z1X"'))
        self.assert_refused(self.check(self.index_dir), f"Dated bundle for {day} failed verification")
        target.write_bytes(original)
        moved = directory.with_name("moved-away")
        directory.rename(moved)
        self.addCleanup(lambda: moved.exists() and moved.rename(directory))
        self.assert_refused(self.check(self.index_dir), f"Dated bundle for {day} failed verification")
        moved.rename(directory)
        index_file = self.index_dir / "index.json"
        index_bytes = index_file.read_bytes()
        self.addCleanup(index_file.write_bytes, index_bytes)
        index_file.write_bytes(index_bytes.replace(b'"default_date":"2026-09-16"', b'"default_date":"2026-08-31"'))
        self.assert_refused(self.check(self.index_dir), r"Date index failed verification \(INDEX_INVALID\)")
        index_file.write_bytes(index_bytes)
        # A changed manifest-backed original fails every date that depends on it.
        price = self.root / "raw/tefas/prices/Z03.json"
        price_bytes = price.read_bytes()
        self.addCleanup(price.write_bytes, price_bytes)
        price.write_bytes(price_bytes + b" ")
        self.assert_refused(self.check(self.index_dir), "failed verification")
        price.write_bytes(price_bytes)
        self.assertEqual(self.check(self.index_dir)[0], 0)

    def test_protocol_commit_must_be_an_ancestor_of_head(self):
        side = git(self.root, "commit-tree", "HEAD^{tree}", "-m", "Synthetic side commit").decode().strip()
        self.assertNotEqual(side, self.head)
        for commit, pattern in ((side, "not an ancestor of HEAD"), ("7" * 40, "unknown to this repository")):
            with self.subTest(commit=commit):
                base = self.root / "raw/alternative" / commit[:8]
                _, index_dir, _ = seal_index(self.space, base, {"protocol_sha256": self.protocol_sha256,
                                                                "protocol_commit": commit})
                self.assert_refused(self.check(index_dir), pattern)
        # A later commit keeps the sealed protocol commit in HEAD's history.
        write(self.root, "later.txt", b"later synthetic commit\n")
        later = commit_all(self.root, "Later synthetic commit")
        self.addCleanup(git, self.root, "reset", "-q", "--hard", self.head)
        self.assertNotEqual(later, self.head)
        self.assertEqual(self.check(self.index_dir)[0], 0)

    def test_protocol_digest_must_be_the_committed_protocol(self):
        # Well formed, and index and bundles agree, but unrelated to the committed PROTOCOL.md.
        _, index_dir, _ = seal_index(self.space, self.root / "raw/unrelated-protocol",
                                     {"protocol_sha256": "6" * 64, "protocol_commit": self.head})
        self.assert_refused(self.check(index_dir), "protocol SHA-256 differs from the protocol committed")
        # The committed digest, but bundles sealed from an uncommitted working PROTOCOL.md.
        protocol = self.root / LAUNCHER.PROTOCOL_REL
        committed = protocol.read_bytes()
        source_id = self.space.global_refs[0]

        def restore():
            protocol.write_bytes(committed)
            self.assertEqual(self.space.registry.add(protocol, "PROTOCOL"), source_id)

        self.addCleanup(restore)
        protocol.write_bytes(committed + b"Uncommitted synthetic amendment.\n")
        self.assertEqual(self.space.registry.add(protocol, "PROTOCOL"), source_id)
        _, index_dir, _ = seal_index(self.space, self.root / "raw/uncommitted-protocol",
                                     {"protocol_sha256": self.protocol_sha256, "protocol_commit": self.head})
        self.assert_refused(self.check(index_dir), "protocol source that differs from the index protocol SHA-256")
        restore()
        self.assertEqual(self.check(self.index_dir)[0], 0)

    def assert_listener_rejected(self, server: socket.socket, port: int, connect: tuple) -> None:
        with self.assertRaisesRegex(ValueError, "occupied"):
            LAUNCHER.available_port(port)
        code, out, err = run(["--index", str(self.index_dir), "--check", "--api-port", str(port)])
        self.assertEqual(code, 1)
        self.assertIn(f"Loopback port {port} is occupied", err)
        self.assertTrue((out + err).isascii())
        # Rejection leaves the listener usable; no foreign server is involved.
        with socket.create_connection(connect, timeout=2) as client:
            connection, _ = server.accept()
            with connection:
                client.sendall(b"authored dated launcher probe")
                self.assertEqual(connection.recv(128), b"authored dated launcher probe")

    def test_wildcard_and_ipv6_listeners_rejected(self):
        listeners = [(socket.AF_INET, "0.0.0.0", "127.0.0.1")]
        if ipv6_loopback_available():  # otherwise only the IPv4 wildcard listener is exercised
            listeners += [(socket.AF_INET6, "::1", "::1"), (socket.AF_INET6, "::", "::1")]
        for family, address, connect in listeners:
            with self.subTest(address=address), socket.socket(family, socket.SOCK_STREAM) as server:
                if family == socket.AF_INET6:
                    server.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
                server.settimeout(2)
                server.bind((address, 0))
                server.listen(1)
                self.assert_listener_rejected(server, server.getsockname()[1], (connect, server.getsockname()[1]))

    def test_active_listener_rejected_on_every_platform(self):
        for reuse in (True, False):
            with self.subTest(reuse=reuse), socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
                if reuse:
                    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server.settimeout(2)
                server.bind(("127.0.0.1", 0))
                server.listen(1)
                port = server.getsockname()[1]
                with self.assertRaisesRegex(ValueError, "occupied"):
                    LAUNCHER.available_port(port)
                code, out, err = run(["--index", str(self.index_dir), "--check", "--api-port", str(port)])
                self.assertEqual(code, 1)
                self.assertIn(f"Loopback port {port} is occupied", err)
                self.assertTrue((out + err).isascii())
                # Rejection leaves the listener usable; no foreign server is involved.
                with socket.create_connection(("127.0.0.1", port), timeout=2) as client:
                    connection, _ = server.accept()
                    with connection:
                        client.sendall(b"authored dated launcher probe")
                        self.assertEqual(connection.recv(128), b"authored dated launcher probe")
        LAUNCHER.available_port(free_port())

    def test_serving_starts_only_the_dated_api_and_terminates_it_on_exit(self):
        class Child:
            def __init__(self, command, cwd, env):
                self.command, self.cwd, self.env = command, cwd, env
                self.terminated = self.waited = False

            def poll(self):
                return 0 if self.terminated else None

            def terminate(self):
                self.terminated = True

            def wait(self, timeout=None):
                self.waited = True
                return 0

        children, real_popen = [], LAUNCHER.subprocess.Popen

        def popen(command, *args, **kwargs):
            if command[0] == "git":  # the real ancestry check still runs
                return real_popen(command, *args, **kwargs)
            children.append(Child(command, kwargs.get("cwd"), kwargs.get("env")))
            return children[-1]

        port = free_port()
        with patch.object(LAUNCHER.subprocess, "Popen", side_effect=popen), \
                patch.object(LAUNCHER.time, "sleep", side_effect=KeyboardInterrupt):
            code, out, err = run(["--index", str(self.index_dir), "--api-port", str(port)])
        self.assertEqual(code, 0, out + err)
        self.assertEqual(len(children), 1)
        child = children[0]
        self.assertEqual(child.command[1:], ["-m", "uvicorn", "p50k.api.dated_app:create_dated_app", "--factory",
                                             "--host", "127.0.0.1", "--port", str(port)])
        self.assertEqual(child.env["P50K_DATED_INDEX"], str(self.index_dir.absolute()))
        self.assertTrue(child.terminated and child.waited)
        self.assertIn(f"http://127.0.0.1:{port}/research-dated/v1/dates", out)
        self.assertIn(f"P50K_DATED_API_ORIGIN=http://127.0.0.1:{port}", out)
        self.assertTrue(out.isascii())


if __name__ == "__main__":
    unittest.main()
