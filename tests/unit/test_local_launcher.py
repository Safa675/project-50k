"""Loopback socket integration checks; only test-owned ephemeral ports are used."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import socket
import sys
import unittest

PATH = Path(__file__).resolve().parents[2] / "ops/local/run_app.py"
SPEC = importlib.util.spec_from_file_location("p50k_local_launcher_socket_tests", PATH)
LAUNCHER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LAUNCHER)


class LocalLauncherSocketTests(unittest.TestCase):
    def listener(self) -> socket.socket:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.addCleanup(server.close)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.settimeout(2)
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        return server

    def test_active_listener_rejected_and_remains_usable(self):
        server = self.listener()
        port = server.getsockname()[1]
        with self.assertRaisesRegex(ValueError, "occupied"):
            LAUNCHER.available_port(port)
        # Rejection must leave the listener alive; no foreign server is involved.
        with socket.create_connection(("127.0.0.1", port), timeout=2) as client:
            connection, _ = server.accept()
            with connection:
                client.sendall(b"authored launcher probe")
                self.assertEqual(connection.recv(128), b"authored launcher probe")

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux TIME_WAIT bind semantics")
    def test_recently_closed_connection_time_wait_allows_restart(self):
        server = self.listener()
        port = server.getsockname()[1]
        with socket.create_connection(("127.0.0.1", port), timeout=2) as client:
            connection, _ = server.accept()
            with connection:
                connection.settimeout(2)
                # The server endpoint actively closes first, placing its local
                # port in TIME_WAIT after the peer's FIN is acknowledged.
                connection.shutdown(socket.SHUT_WR)
                self.assertEqual(client.recv(1), b"")
                client.shutdown(socket.SHUT_WR)
                self.assertEqual(connection.recv(1), b"")
        server.close()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as old_probe:
            # Demonstrate the original false positive, rather than merely
            # checking an unrelated unused ephemeral port.
            with self.assertRaises(OSError):
                old_probe.bind(("127.0.0.1", port))
        LAUNCHER.available_port(port)


if __name__ == "__main__":
    unittest.main()
