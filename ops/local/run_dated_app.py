#!/usr/bin/env python3
"""Run the private dated D1 API on loopback without installation, downloads or computation.

Takes the exact sealed index directory, never the newest one. --check verifies the
index, every indexed bundle, the strict response contract for every date, that the
index's protocol commit is an ancestor of HEAD and that the recorded protocol SHA-256
is the digest of PROTOCOL.md at that commit and of every bundle's PROTOCOL.md source.
Output is ASCII only.
"""
from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
UNIVERSE_REL = Path("research/events/2026-09-17-spk-liquidations/top100_funds.txt")
PROTOCOL_REL = Path("research/events/2026-09-17-spk-liquidations/fund_review_dated/PROTOCOL.md")
DEFAULT_PORT = 8768
# A listener on any of these blocks the API or shadows it for some clients.
PROBE_ADDRESSES = ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET, "0.0.0.0"),
                   (socket.AF_INET6, "::1"), (socket.AF_INET6, "::"))
# Only these mean the address does not exist on this host, so nothing can listen there.
ABSENT_ADDRESS = frozenset(code for code in (errno.EADDRNOTAVAIL, errno.EAFNOSUPPORT,
                                             getattr(errno, "WSAEADDRNOTAVAIL", None),
                                             getattr(errno, "WSAEAFNOSUPPORT", None)) if code is not None)


def port_number(value: str) -> int:
    number = int(value)
    if not 1 <= number <= 65535:
        raise argparse.ArgumentTypeError("Port must be between 1 and 65535")
    return number


def available_port(port: int) -> None:
    """Probe loopback and wildcard, IPv4 and IPv6, without SO_REUSEADDR anywhere.

    On Windows SO_REUSEADDR lets a bind steal an active listener, while
    SO_EXCLUSIVEADDRUSE makes the probe fail against any socket on the port. Any bind
    failure refuses, except an IPv6 address this host does not have (IPv6 disabled).
    """
    exclusive = getattr(socket, "SO_EXCLUSIVEADDRUSE", None)
    for family, address in PROBE_ADDRESSES:
        if family == socket.AF_INET6 and not socket.has_ipv6:
            continue
        try:
            probe = socket.socket(family, socket.SOCK_STREAM)
        except OSError as exc:
            if family == socket.AF_INET6 and exc.errno in ABSENT_ADDRESS:
                continue
            raise ValueError(f"Cannot probe loopback port {port}") from exc
        with probe:
            if sys.platform == "win32" and exclusive is not None:
                probe.setsockopt(socket.SOL_SOCKET, exclusive, 1)
            if family == socket.AF_INET6:
                # Probe the IPv6 address alone; the IPv4 addresses have their own probes.
                probe.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
            try:
                probe.bind((address, port))
            except OSError as exc:
                if family == socket.AF_INET6 and exc.errno in ABSENT_ADDRESS:
                    continue
                raise ValueError(f"Loopback port {port} is occupied; choose another port") from exc


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--index", type=Path, default=os.environ.get("P50K_DATED_INDEX"),
                        help="Exact sealed index directory; no newest-version selection or data generation")
    parser.add_argument("--api-port", type=port_number, default=DEFAULT_PORT)
    parser.add_argument("--check", action="store_true", help="Verify everything without starting the API")
    result = parser.parse_args(argv)
    if result.index is None:
        parser.error("Pass --index or P50K_DATED_INDEX; private data is absent from Git clones")
    return result


def protocol_commit_is_ancestor(commit: str, repo_root: Path) -> None:
    try:
        result = subprocess.run(["git", "-C", str(repo_root), "merge-base", "--is-ancestor", commit, "HEAD"],
                                capture_output=True, check=False, timeout=60)
    except (OSError, subprocess.SubprocessError) as exc:
        raise ValueError("Cannot run git to verify the protocol commit ancestry") from exc
    if result.returncode == 1:
        raise ValueError("The index protocol commit is not an ancestor of HEAD")
    if result.returncode != 0:
        raise ValueError("The index protocol commit is unknown to this repository")


def _same_file(recorded: object, expected: Path) -> bool:
    if not isinstance(recorded, str):
        return False
    return os.path.normcase(os.path.abspath(recorded)) == os.path.normcase(os.path.abspath(expected))


def protocol_digest_is_committed(index: dict, index_dir: Path, repo_root: Path) -> None:
    """protocol_sha256 must be the committed PROTOCOL.md at protocol_commit, not just well formed.

    Every indexed bundle must also register that PROTOCOL.md as its PROTOCOL source
    with this digest (the bundles were already fully verified against their originals).
    """
    spec = f"{index['protocol_commit']}:{PROTOCOL_REL.as_posix()}"
    try:
        result = subprocess.run(["git", "-C", str(repo_root), "show", spec], capture_output=True, check=False,
                                timeout=60)
    except (OSError, subprocess.SubprocessError) as exc:
        raise ValueError("Cannot run git to read the committed protocol") from exc
    if result.returncode != 0:
        raise ValueError("The index protocol commit does not contain the dated protocol")
    if hashlib.sha256(result.stdout).hexdigest() != index["protocol_sha256"]:
        raise ValueError("The index protocol SHA-256 differs from the protocol committed at its protocol commit")
    from p50k.research_reviews.dated_bundle import default_bundles_dir

    expected = repo_root / PROTOCOL_REL
    bundles = default_bundles_dir(index_dir)
    for entry in index["entries"]:
        try:
            payload = json.loads((bundles / entry["bundle_id"] / "bundle.json").read_bytes())
            sources = {source["source_id"]: source for source in payload["sources"]}
            protocols = [item for item in payload["manifest"]
                         if item["kind"] == "PROTOCOL" and _same_file(item["original_path"], expected)]
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise ValueError(f"Dated bundle for {entry['date']} failed verification ({type(exc).__name__})") from exc
        if len(protocols) != 1:
            raise ValueError(f"Dated bundle for {entry['date']} does not register the dated protocol as a source")
        source = sources.get(protocols[0]["source_id"])
        if protocols[0]["sha256"] != index["protocol_sha256"] or source is None or \
                source.get("kind") != "PROTOCOL" or source.get("sha256") != index["protocol_sha256"]:
            raise ValueError(f"Dated bundle for {entry['date']} has a protocol source that differs from the "
                             "index protocol SHA-256")


def check_index(index_dir: Path, *, repo_root: Path | None = None) -> dict:
    """Index, all bundles, every per-date response and the protocol ancestry."""
    root = Path(repo_root if repo_root is not None else ROOT)
    services = str(root / "services")
    if services not in sys.path:
        sys.path.insert(0, services)
    try:
        from p50k.api.dated_app import create_dated_app
    except ImportError as exc:
        raise ValueError("Install the locked API extras and run this launcher with the project virtualenv") from exc
    universe = frozenset((root / UNIVERSE_REL).read_text(encoding="utf-8").split())
    app = create_dated_app(Path(index_dir).absolute(), universe_codes=universe, repo_root=root)
    index = app.state.verify_all()
    protocol_commit_is_ancestor(index["protocol_commit"], root)
    protocol_digest_is_committed(index, Path(index_dir).absolute(), root)
    return index


def ascii_text(value: object) -> str:
    return str(value).encode("ascii", "backslashreplace").decode("ascii")


def main(argv: list[str] | None = None) -> int:
    options = arguments(argv)
    index_dir = options.index.absolute()
    origin = f"http://127.0.0.1:{options.api_port}"
    children: list[subprocess.Popen] = []
    try:
        available_port(options.api_port)
        index = check_index(index_dir, repo_root=ROOT)
        configured = os.environ.get("P50K_DATED_API_ORIGIN")
        if configured and configured.rstrip("/") != origin:
            print(f"Warning: P50K_DATED_API_ORIGIN is {ascii_text(configured)}, but the dated API uses {origin}",
                  flush=True)
        if options.check:
            print(f"Date index {index['index_id']}, its {len(index['entries'])} sealed bundles, the strict "
                  "per-date response contract, protocol commit ancestry and digest, and the loopback port "
                  "verified.", flush=True)
            print(f"The frontend must use P50K_DATED_API_ORIGIN={origin}", flush=True)
            return 0
        environment = os.environ.copy()
        environment.update(PYTHONPATH=str(ROOT / "services"), PYTHONDONTWRITEBYTECODE="1",
                           P50K_DATED_INDEX=str(index_dir))
        children.append(subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "p50k.api.dated_app:create_dated_app", "--factory",
             "--host", "127.0.0.1", "--port", str(options.api_port)], cwd=ROOT, env=environment))
        print(f"Private dated API: {origin}/research-dated/v1/dates", flush=True)
        print(f"The frontend must use P50K_DATED_API_ORIGIN={origin}", flush=True)
        while all(child.poll() is None for child in children):
            time.sleep(0.25)
        return next((child.returncode or 0 for child in children if child.returncode is not None), 0)
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        # No source paths, data values or tracebacks in output.
        detail = ascii_text(exc) if isinstance(exc, ValueError) else "check the sealed index and documented prerequisites"
        print(f"Cannot start the dated research API: {type(exc).__name__}: {detail}", file=sys.stderr, flush=True)
        return 1
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
        for child in children:
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()


if __name__ == "__main__":
    raise SystemExit(main())
