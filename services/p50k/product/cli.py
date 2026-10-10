"""Explicit product jobs; archive inputs are always read-only."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from p50k.product.archive import Archive


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    archive_parser = commands.add_parser("import-archive")
    archive_parser.add_argument("--raw-dir", type=Path, required=True)
    archive_parser.add_argument("--snapshot-db", action="append", type=Path, default=[])
    archive_parser.add_argument("--event-map", type=Path)
    archive_parser.add_argument("--dry-run", action="store_true")
    detector_parser = commands.add_parser("run-detectors")
    detector_parser.add_argument("--cutoff", help="Timezone-aware publication cutoff; default now")
    detector_parser.add_argument("--origin", choices=("DELAYED", "HISTORICAL_REPLAY"), default="DELAYED")
    args = parser.parse_args()
    try:
        if args.command == "run-detectors":
            from p50k.product.db import connect
            from p50k.product.detector_pipeline import run_detectors
            from p50k.product.settings import Settings
            if args.origin == "HISTORICAL_REPLAY" and not args.cutoff:
                raise ValueError("Historical replay requires an explicit cutoff")
            cutoff = datetime.fromisoformat(args.cutoff.replace("Z", "+00:00")) if args.cutoff else datetime.now(timezone.utc).replace(microsecond=0)
            if cutoff.tzinfo is None or cutoff > datetime.now(timezone.utc):
                raise ValueError("Cutoff must be timezone-aware and cannot be in the future")
            with connect(Settings.from_env()) as connection:
                print(json.dumps(run_detectors(connection, cutoff, args.origin)))
            return 0
        archive = Archive(args.raw_dir.resolve(), tuple(path.resolve() for path in args.snapshot_db),
                          args.event_map.resolve() if args.event_map else None)
        if args.dry_run:
            counts = {}
            for reader in ("funds", "prices", "snapshots", "kap_documents", "kap_series", "events"):
                count = missing = 0
                for row in getattr(archive, reader)():
                    count += 1
                    missing += "nav" in row and row["nav"] is None
                counts[reader] = {"input": count, "missing": missing}
            print(json.dumps({"archive_sha256": archive.fingerprint(), "counts": counts}))
        else:
            from p50k.product.db import connect
            from p50k.product.import_archive import import_archive
            from p50k.product.settings import Settings
            with connect(Settings.from_env()) as connection:
                print(json.dumps(import_archive(connection, archive)))
        return 0
    except Exception as error:
        # Driver messages and archive values may contain private data or credentials.
        print(json.dumps({"error_class": type(error).__name__}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
