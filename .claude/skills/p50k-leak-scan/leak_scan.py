"""Scan new, modified and staged files for real price values, real fund names and non-target fund codes.

Reads only the 100 opened price files and snapshot names; prints counts and file:line locations, never values.
Exit codes: 0 no hits, 1 hits found, 2 private data absent (value/name checks skipped).
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

TARGETS = {"THF", "TP2", "TLY", "DFI", "DOH", "PRY", "KHA", "PNU"}
UNIVERSE = "research/events/2026-09-17-spk-liquidations/top100_funds.txt"


def changed_files(repo: Path) -> list[str]:
    out = subprocess.run(["git", "-C", str(repo), "status", "--porcelain", "-uall"],
                         capture_output=True, text=True, encoding="utf-8", check=True).stdout
    paths = []
    for line in out.splitlines():
        path = line[3:].split(" -> ")[-1].strip().strip('"')
        if path and not path.startswith("raw/") and not line.startswith(" D"):
            paths.append(path)
    return paths


def snapshot_names(raw: Path) -> set[str] | None:
    candidates = [raw / "snapshots/fund_snapshots.sqlite3"]
    if os.environ.get("P50K_DATA_DIR"):
        candidates.append(Path(os.environ["P50K_DATA_DIR"]) / "fund_snapshots.sqlite3")
    candidates.append(Path.home() / ".local/share/project-50k/fund_snapshots.sqlite3")
    for path in candidates:
        if path.is_file():
            names = set()
            connection = sqlite3.connect(f"{path.absolute().as_uri()}?mode=ro", uri=True)
            try:
                for (raw,) in connection.execute("SELECT raw_snapshot FROM fund_snapshots"):
                    try:
                        name = json.loads(raw).get("fonUnvan")
                    except (TypeError, ValueError, AttributeError):
                        continue
                    if isinstance(name, str) and len(name.strip()) >= 12:
                        names.add(name.strip().casefold())
            finally:
                connection.close()
            return names
    return None


def main() -> int:
    repo = Path(__file__).resolve().parents[3]  # the repository that contains this skill
    # A clone without private data (a worktree or second clone) can point at another checkout's raw/.
    raw = Path(os.environ.get("P50K_RAW_DIR") or repo / "raw").resolve()
    codes = (repo / UNIVERSE).read_text(encoding="utf-8").split()
    nontarget = sorted(set(codes) - TARGETS)
    values: set[str] = set()
    for code in codes:
        path = raw / "tefas/prices" / f"{code}.json"
        if path.is_file():
            for token in re.findall(r"\d+\.\d+", path.read_text(encoding="utf-8")):
                if len(token.replace(".", "").lstrip("0")) >= 7:
                    values.add(token)
    names = snapshot_names(raw)
    code_pattern = re.compile(r"(?<![A-Z0-9])(" + "|".join(map(re.escape, nontarget)) + r")(?![A-Z0-9])")
    hits = {"price value": [], "fund name": [], "non-target code": []}
    files = changed_files(repo)
    for rel in files:
        path = repo / rel
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(text.splitlines(), 1):
            if values and any(token in values for token in re.findall(r"\d+\.\d+", line)):
                hits["price value"].append(f"{rel}:{number}")
            if names and any(name in line.casefold() for name in names):
                hits["fund name"].append(f"{rel}:{number}")
            if rel != UNIVERSE:
                hits["non-target code"].extend(f"{rel}:{number}:{m.group(1)}" for m in code_pattern.finditer(line))
    print(f"files scanned: {len(files)}; reference values: {len(values)}; reference names: "
          f"{'absent' if names is None else len(names)}; non-target codes: {len(nontarget)}")
    for kind, found in hits.items():
        print(f"{kind} hits: {len(found)}" + (f" -> {found[:30]}" if found else ""))
    if any(hits.values()):
        return 1
    return 2 if not values or names is None else 0


if __name__ == "__main__":
    raise SystemExit(main())
