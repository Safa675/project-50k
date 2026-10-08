#!/usr/bin/env python3
"""Run private research processes on loopback without installation or downloads."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]


def port_number(value: str) -> int:
    number = int(value)
    if not 1 <= number <= 65535:
        raise argparse.ArgumentTypeError("Port must be between 1 and 65535")
    return number


def available_port(port: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind(("127.0.0.1", port))
        except OSError as exc:
            raise ValueError(f"Loopback port {port} is occupied; choose another port") from exc


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=os.environ.get("P50K_RESEARCH_BUNDLE"),
                        help="Exact sealed directory; no latest-version selection or data generation")
    parser.add_argument("--api-port", type=port_number, default=8767)
    parser.add_argument("--frontend-port", type=port_number, default=3060)
    parser.add_argument("--mode", choices=("dev", "production"), default="dev")
    parser.add_argument("--api-only", action="store_true")
    parser.add_argument("--check", action="store_true", help="Verify prerequisites without starting processes")
    result = parser.parse_args(argv)
    if result.bundle is None:
        parser.error("Pass --bundle or P50K_RESEARCH_BUNDLE; private data is absent from Git clones")
    return result


def main(argv: list[str] | None = None) -> int:
    options = arguments(argv)
    bundle_dir = options.bundle.absolute()
    children: list[subprocess.Popen] = []
    try:
        if options.api_port == options.frontend_port and not options.api_only:
            raise ValueError("API and frontend require separate ports")
        available_port(options.api_port)
        if not options.api_only:
            available_port(options.frontend_port)
        sys.path.insert(0, str(ROOT / "services"))
        try:
            from p50k.api.app import create_app
        except ImportError as exc:
            raise ValueError("Install the locked API extras and run this launcher with .venv/bin/python") from exc
        origin = f"http://127.0.0.1:{options.frontend_port}"
        app = create_app(bundle_dir, frontend_origin=origin)
        app.state.bundle_view()
        node = None
        next_script = ROOT / "frontend/node_modules/next/dist/bin/next"
        if not options.api_only:
            node = shutil.which("node")
            if node is None or not next_script.is_file():
                raise ValueError("Install locked frontend dependencies explicitly with npm ci")
            if options.mode == "production" and not (ROOT / "frontend/.next/BUILD_ID").is_file():
                raise ValueError("Run npm run build explicitly before --mode production")
        if options.check:
            print("Sealed bundle, strict response contract, local dependencies and loopback ports verified.")
            return 0
        environment = os.environ.copy()
        environment.update(PYTHONPATH=str(ROOT / "services"), PYTHONDONTWRITEBYTECODE="1",
                           P50K_RESEARCH_BUNDLE=str(bundle_dir), P50K_FRONTEND_ORIGIN=origin,
                           P50K_API_ORIGIN=f"http://127.0.0.1:{options.api_port}",
                           NEXT_TELEMETRY_DISABLED="1")
        children.append(subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "p50k.api.app:create_app", "--factory",
             "--host", "127.0.0.1", "--port", str(options.api_port)], cwd=ROOT, env=environment))
        if not options.api_only:
            frontend_command = [node, str(next_script), "dev" if options.mode == "dev" else "start"]
            if options.mode == "dev":
                frontend_command.append("--webpack")
            children.append(subprocess.Popen(
                [*frontend_command, "--hostname", "127.0.0.1", "--port", str(options.frontend_port)],
                cwd=ROOT / "frontend", env=environment))
        print(f"Private API: http://127.0.0.1:{options.api_port}/research/v1/health", flush=True)
        if not options.api_only:
            print(f"Private app: {origin}", flush=True)
        while all(child.poll() is None for child in children):
            time.sleep(0.25)
        return next((child.returncode or 0 for child in children if child.returncode is not None), 0)
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        # No original source paths, data values or dependency downloads in output.
        print(f"Cannot start the local research app: {type(exc).__name__}: "
              f"{exc if isinstance(exc, ValueError) else 'check the sealed bundle and documented prerequisites'}",
              file=sys.stderr)
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
