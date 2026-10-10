"""Scan new, modified and staged files for real price values, real fund names and non-target fund codes.

Reads every price file and the fund names in the snapshot databases (all funds are open, DEC-029); prints counts
and file:line locations, never values.
Staged copies are scanned as well as working copies. Changed paths under raw/ or other ignored paths are hits.
Exit codes: 0 no hits, 1 hits found, 2 private data absent (value/name checks skipped).
"""
from __future__ import annotations

import csv
import json
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

TARGETS = {"THF", "TP2", "TLY", "DFI", "DOH", "PRY", "KHA", "PNU"}
UNIVERSE = "research/events/2026-09-17-spk-liquidations/top100_funds.txt"
PRIVATE = re.compile(r"^(raw|research/(spikes|events)/[^/]+/raw)(/|$)")


def git(repo: Path, *args: str, stdin: bytes | None = None, ok: tuple[int, ...] = (0,)) -> bytes:
    result = subprocess.run(["git", "-C", str(repo), *args], input=stdin, capture_output=True)
    if result.returncode not in ok:
        raise subprocess.CalledProcessError(result.returncode, result.args, result.stdout, result.stderr)
    return result.stdout


def changed_files(repo: Path) -> list[tuple[str, bool]]:
    """(path, staged) for every new, modified or staged path; -z keeps non-ASCII names intact."""
    entries = git(repo, "status", "--porcelain=v1", "-z", "-uall").decode("utf-8").split("\0")
    paths: list[tuple[str, bool]] = []
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if len(entry) < 4:
            continue
        status, path = entry[:2], entry[3:]
        if status[0] in "RC":
            index += 1  # the next entry is the rename source
        if status != " D" and status[0] != "D":
            paths.append((path, status[0] not in " ?"))
    return paths


def snapshot_names(raw: Path) -> set[str] | None:
    """Fund names from every snapshot database found; None when there is none."""
    data_dir = Path(os.environ["P50K_DATA_DIR"]) if os.environ.get("P50K_DATA_DIR") else None
    home = Path.home() / ".local/share/project-50k"
    candidates = [raw / "snapshots/fund_snapshots.sqlite3", home / "fund_snapshots.sqlite3",
                  home / "fund_snapshots_forward.sqlite3"]
    if data_dir:
        candidates += [data_dir / "fund_snapshots.sqlite3", data_dir / "fund_snapshots_forward.sqlite3"]
    names: set[str] | None = None
    listing = raw / "tefas/responses/fonGetiriBazliBilgiGetir_YAT.body"
    if listing.is_file():
        names = set()
        for row in json.loads(listing.read_text(encoding="utf-8")).get("resultList", []):
            name = row.get("fonUnvan")
            if isinstance(name, str) and len(name.strip()) >= 12:
                names.add(name.strip().casefold())
    for path in dict.fromkeys(candidates):
        if not path.is_file():
            continue
        names = names or set()
        connection = sqlite3.connect(f"{path.absolute().as_uri()}?mode=ro", uri=True)
        try:
            for (raw_row,) in connection.execute("SELECT raw_snapshot FROM fund_snapshots"):
                try:
                    name = json.loads(raw_row).get("fonUnvan")
                except (TypeError, ValueError, AttributeError):
                    continue
                if isinstance(name, str) and len(name.strip()) >= 12:
                    names.add(name.strip().casefold())
        finally:
            connection.close()
    return names


def code_pattern(codes: list[str]) -> re.Pattern[str]:
    """A ticker is a complete token, not a substring of a mixed-case hash or word."""
    return re.compile(r"(?<![A-Za-z0-9])(" + "|".join(map(re.escape, codes)) + r")(?![A-Za-z0-9])")


def fixture_code_pattern(codes: list[str]) -> re.Pattern[str]:
    """All-fund IDs in string values and file paths; not units, env names or licenses."""
    alternatives = "|".join(map(re.escape, codes))
    return re.compile(r"(?<=[\"'])((?:" + alternatives + r"))(?=[\"'])"
                      r"|(?<=[/\\\"'])((?:" + alternatives + r"))(?=[_.][0-9]|\.json|\.csv|\.pdf)")


def csv_codes(line: str, codes: set[str]) -> set[str]:
    return {cell.strip() for row in csv.reader([line]) for cell in row if cell.strip() in codes}


def texts(repo: Path, path: str, staged: bool) -> list[str]:
    """The working copy and, when staged, the index copy; undecodable (binary) content is skipped."""
    blobs = []
    if (repo / path).is_file():
        blobs.append((repo / path).read_bytes())
    if staged:
        try:
            blobs.append(git(repo, "show", f":{path}"))
        except subprocess.CalledProcessError:
            pass
    decoded = []
    for blob in blobs:
        try:
            decoded.append(blob.decode("utf-8"))
        except UnicodeDecodeError:
            continue
    return decoded


def main() -> int:
    repo = Path(__file__).resolve().parents[3]  # the repository that contains this skill
    # A clone without private data (a worktree or second clone) can point at another checkout's raw/.
    raw = Path(os.environ.get("P50K_RAW_DIR") or repo / "raw").resolve()
    codes = (repo / UNIVERSE).read_text(encoding="utf-8").split()
    nontarget = sorted(set(codes) - TARGETS)
    values: set[str] = set()
    prices = raw / "tefas/prices"
    price_paths = list(prices.glob("*.json")) if prices.is_dir() else []
    overnight = Path.home() / ".local/share/project-50k/overnight"
    price_paths += list(overnight.glob("*/prices/*.json")) if overnight.is_dir() else []
    price_paths += list(overnight.glob("*/tefas/prices/*.json")) if overnight.is_dir() else []
    for path in sorted(price_paths):
        for token in re.findall(r"\d+\.\d+", path.read_text(encoding="utf-8")):
            if len(token.replace(".", "").lstrip("0")) >= 7:
                values.add(token)
    names = snapshot_names(raw)
    top100_pattern = code_pattern(nontarget)
    listing = raw / "tefas/responses/fonGetiriBazliBilgiGetir_YAT.body"
    all_codes = set(codes)
    if listing.is_file():
        all_codes.update(row["fonKodu"] for row in json.loads(listing.read_text(encoding="utf-8")).get("resultList", []))
    all_fund_pattern = fixture_code_pattern(sorted(all_codes - TARGETS))
    hits: dict[str, list[str]] = {"private or ignored path": [], "price value": [], "fund name": [], "non-target code": []}
    files = changed_files(repo)
    ignored = set()
    if files:
        listed = "\0".join(path for path, _ in files).encode("utf-8") + b"\0"
        ignored = {p for p in git(repo, "check-ignore", "--no-index", "-z", "--stdin", stdin=listed, ok=(0, 1)).decode("utf-8").split("\0") if p}
    scanned = 0
    for rel, staged in files:
        if PRIVATE.match(rel) or rel in ignored:
            hits["private or ignored path"].append(rel)
            continue
        contents = texts(repo, rel, staged)
        scanned += bool(contents)
        seen: set[str] = set()
        for text in contents:
            for number, line in enumerate(text.splitlines(), 1):
                if values and any(token in values for token in re.findall(r"\d+\.\d+", line)):
                    seen.add(f"price value|{rel}:{number}")
                if names and any(name in line.casefold() for name in names):
                    seen.add(f"fund name|{rel}:{number}")
                if rel != UNIVERSE:
                    pattern = all_fund_pattern if rel.endswith((".json", ".csv")) or rel.startswith(("tests/", "fixtures/", "seeds/")) else top100_pattern
                    seen.update(f"non-target code|{rel}:{number}:{m.group(1) or m.group(2)}" for m in pattern.finditer(line))
                    if rel.endswith(".csv"):
                        seen.update(f"non-target code|{rel}:{number}:{code}" for code in csv_codes(line, all_codes - TARGETS))
        for item in sorted(seen):
            kind, location = item.split("|", 1)
            hits[kind].append(location)
    print(f"changed paths: {len(files)}; text files scanned: {scanned}; reference values: {len(values)}; "
          f"reference names: {'absent' if names is None else len(names)}; non-target codes: {len(nontarget)}")
    for kind, found in hits.items():
        print(f"{kind} hits: {len(found)}" + (f" -> {found[:30]}" if found else ""))
    if any(hits.values()):
        return 1
    return 2 if not values or names is None else 0


if __name__ == "__main__":
    sys.exit(main())
