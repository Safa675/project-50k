"""Extract the 131 funds SPK ordered liquidated on 17/09/2026 and map them to TEFAS codes.

Source: SPK Bulletin 2026/61 (17/09/2026), section C, which lists the funds by
full name, numbered 1 to 131:
https://spk.gov.tr/data/6aac56ff8f95db07100fd82d/2026-61.pdf

The bulletin PDF sits in raw/spk/ at the repo root (gitignored). Names are
matched to codes using the TEFAS fund list saved in raw/tefas/responses/ by
the 2026-10-06 spike. Run from the repo root:
    python research/events/2026-09-17-spk-liquidations/extract.py
Writes liquidated_funds.json next to this file.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import re
from pathlib import Path

import pymupdf

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
RAW = REPO / "raw"
PDF = RAW / "spk" / "spk-bulten-2026-61.pdf"
FUND_LIST = RAW / "tefas" / "responses" / "fonGetiriBazliBilgiGetir_YAT.body"
OUT = HERE / "liquidated_funds.json"
SOURCE_URL = "https://spk.gov.tr/data/6aac56ff8f95db07100fd82d/2026-61.pdf"
EXPECTED = 131
# Page headers and footers that interrupt the list.
NOISE = re.compile(r"^(_{5,}|MERKEZ |İSTANBUL TEMSİLCİLİĞİ|SERMAYE PİYASASI KURULU|BÜLTENİ|2026/61|\d{2}/\d{2}/2026$)")
COMPANIES = ("A1 CAPİTAL", "ATLAS", "BULLS", "HEDEF", "PARDUS", "PUSULA", "TERA")


def list_section(text: str) -> str:
    start = text.find("C) 17.09.2026")
    if start < 0:
        raise ValueError("section C not found")
    section = text[start:]
    marker = "güncellenmiştir."
    return section[section.find(marker) + len(marker):]


def numbered_entries(section: str) -> dict[int, str]:
    """Follow 1, 2, 3 ... in order, so page numbers can't be mistaken for entries."""
    entries: dict[int, list[str]] = {}
    expected, current = 1, None
    for raw in section.splitlines():
        line = raw.strip()
        if not line or NOISE.match(line):
            continue
        if line == str(expected):
            current, expected = expected, expected + 1
            entries[current] = []
        elif re.fullmatch(r"\d{1,3}", line):
            continue  # a page number
        elif current is not None:
            if re.match(r"^[A-Z]\)\s", line) or re.match(r"^[A-Z]\.\s+[A-ZÇĞİÖŞÜ]", line):
                break  # the bulletin's next section
            entries[current].append(line)
    return {n: " ".join(parts) for n, parts in entries.items()}


def normalize(name: str) -> str:
    name = name.upper()
    for turkish, plain in (("İ", "I"), ("Ş", "S"), ("Ğ", "G"), ("Ü", "U"), ("Ö", "O"), ("Ç", "C")):
        name = name.replace(turkish, plain)
    return re.sub(r"[^A-Z0-9]", "", re.sub(r"\bFONU\b", "FON", name))


def main() -> None:
    pdf_bytes = PDF.read_bytes()
    text = "\n".join(page.get_text() for page in pymupdf.open(PDF))
    names = numbered_entries(list_section(text))
    if sorted(names) != list(range(1, EXPECTED + 1)):
        raise ValueError(f"expected entries 1..{EXPECTED}, got {len(names)}")

    by_name: dict[str, list[str]] = {}
    for row in json.loads(FUND_LIST.read_text(encoding="utf-8"))["resultList"]:
        by_name.setdefault(normalize(row["fonUnvan"]), []).append(row["fonKodu"])

    funds = []
    for n, name in sorted(names.items()):
        key = normalize(name)
        match, method = by_name.get(key, []), "exact name"
        if len(match) != 1:
            close = difflib.get_close_matches(key, list(by_name), n=1, cutoff=0.9)
            match = by_name[close[0]] if close else []
            method = f"closest name ({difflib.SequenceMatcher(None, key, close[0]).ratio():.2f})" if close else "none"
        company = next((c for c in COMPANIES if name.upper().startswith(c)), None)
        funds.append({"n": n, "name": name, "company": company,
                      "code": match[0] if len(match) == 1 else None, "match": method})

    unmatched = [f["n"] for f in funds if f["code"] is None]
    codes = [f["code"] for f in funds if f["code"]]
    if unmatched or len(set(codes)) != EXPECTED:
        raise ValueError(f"unmatched entries {unmatched}; distinct codes {len(set(codes))}")
    OUT.write_text(json.dumps({
        "source": SOURCE_URL,
        "source_sha256": hashlib.sha256(pdf_bytes).hexdigest(),
        "decision": "SPK Kurul Karar Organı 17/09/2026, 57/1707 and 57/1708; list updated in Bulletin 2026/61, section C",
        "matched_against": "TEFAS fund list retrieved 2026-10-06",
        "funds": funds,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(funds)} funds, all matched to TEFAS codes; "
          f"{sum(f['match'] != 'exact name' for f in funds)} by closest name; wrote {OUT.name}")


if __name__ == "__main__":
    main()
