"""Download and check a year of KAP monthly portfolio reports for ten funds (2026-10-06).

Owner-approved batch: about ten funds and 120 PDFs from kap.org.tr. The funds
cover nine fund types and ten management companies, all traded on TEFAS and at
least a year old (TTE and AAL from the spike, then the first fund by code for
each remaining type from a company not yet used). The goal is to see how much
the report layout varies between companies.

Run from the repo root, after spike.py:
    python research/spikes/2026-10-06-tefas/kap_batch.py download [--funds A B ...] [--pause 6] [--log name.json]
    python research/spikes/2026-10-06-tefas/kap_batch.py check [--funds A B ...] [--out results.json]

download: per fund, TEFAS profile -> KAP fund page -> KAP report list (365
days) -> each report's disclosure page -> attachment, plus three years of TEFAS
prices for the cross-check. Sequential, 1.5 s apart, certificate verification
on. Files already in raw/ are reused. Stops after 3 consecutive failures.

check: parses every PDF with kap_pdf_check's line rebuilding and labels, and
cross-checks month-end prices against TEFAS. Writes kap_batch_results.json with
structure and checks only; values stay in the gitignored raw/ folder.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import time
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import httpx
import pymupdf

from kap_pdf_check import LABELS, SECTIONS, page_lines, parse_number, shape

FUNDS = ["TTE", "AAL", "ACC", "ADE", "AHU", "BCO", "AHV", "DBA", "YAK", "AC1"]
PAUSE_SECONDS = 1.5
MAX_CONSECUTIVE_FAILURES = 3
NETWORK_WAIT_SECONDS = 30
NETWORK_WAIT_ATTEMPTS = 40  # up to 20 minutes without a connection
TEFAS_API = "https://www.tefas.gov.tr/api/funds"
KAP = "https://kap.org.tr"
REPORT_TYPE = "8aca490d502e34b801502e380044002b"  # Portföy Dağılım Raporu

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
KAP_DIR = RAW / "kap"
RESULTS = HERE / "kap_batch_results.json"


class Session:
    """Sequential, paced requests with a log, a consecutive-failure stop, and a wait for lost connections."""

    def __init__(self, pause: float = PAUSE_SECONDS) -> None:
        from borsapy._providers.base import BaseProvider

        self.pause = pause
        self.client = httpx.Client(verify=True, timeout=90,
                                   headers={"User-Agent": BaseProvider.DEFAULT_HEADERS["User-Agent"]})
        self.log: list[dict] = []
        self.failures = 0

    def request(self, method: str, url: str, **kwargs) -> httpx.Response | None:
        for attempt in range(NETWORK_WAIT_ATTEMPTS + 1):
            entry = {"method": method, "url": url, "at_utc": datetime.now(timezone.utc).isoformat()}
            response = None
            try:
                response = self.client.request(method, url, **kwargs)
                entry.update(status=response.status_code, bytes=len(response.content),
                             content_type=response.headers.get("content-type"),
                             sha256=hashlib.sha256(response.content).hexdigest())
            except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
                # No connection at all: the local network dropped. Wait for it to come back instead of
                # counting a server failure; nothing reaches KAP while we wait.
                entry["error"] = type(exc).__name__
                if attempt < NETWORK_WAIT_ATTEMPTS:
                    entry["waiting_for_network"] = True
                    self.log.append(entry)
                    time.sleep(NETWORK_WAIT_SECONDS)
                    continue
            except httpx.HTTPError as exc:
                entry["error"] = type(exc).__name__
            break
        self.log.append(entry)
        time.sleep(self.pause)
        ok = response is not None and response.status_code == 200 and bool(response.content.strip())
        self.failures = 0 if ok else self.failures + 1
        if self.failures >= MAX_CONSECUTIVE_FAILURES:
            raise RuntimeError(f"{MAX_CONSECUTIVE_FAILURES} consecutive failures; stopping")
        return response if ok else None


def cached_or_fetch(path: Path, fetch) -> bytes | None:
    if path.exists():
        return path.read_bytes()
    response = fetch()
    if response is None:
        return None
    path.write_bytes(response.content)
    return response.content


def download_fund(session: Session, code: str) -> dict:
    fund_dir = KAP_DIR / code
    fund_dir.mkdir(parents=True, exist_ok=True)
    result: dict = {"fund": code, "reports": 0, "files": 0, "reused": 0, "problems": []}

    spike_profile = RAW / f"fonProfilBilgiGetir_{code}.body"
    profile = cached_or_fetch(
        spike_profile if spike_profile.exists() else fund_dir / "tefas_profile.json",
        lambda: session.request("POST", f"{TEFAS_API}/fonProfilBilgiGetir", json={"fonKodu": code, "dil": "TR"}))
    rows = (json.loads(profile).get("resultList") or []) if profile else []
    link = rows[0].get("kapLink") if rows else None
    url = httpx.URL(link) if isinstance(link, str) else None
    if url is None or url.scheme != "https" or not (url.host == "kap.org.tr" or url.host.endswith(".kap.org.tr")):
        result["problems"].append(f"no usable KAP link: {link!r}")
        return result

    spike_page = RAW / f"kap_page_{code}.body"
    page = cached_or_fetch(spike_page if spike_page.exists() else fund_dir / "kap_fund_page.html",
                           lambda: session.request("GET", link))
    match = re.search(r'objId[\\"\':]+([A-Fa-f0-9]{32})', page.decode("utf-8", "replace")) if page else None
    if not match:
        result["problems"].append("KAP fund id not found")
        return result

    spike_list = RAW / f"kap_portfolio_reports_{code}.body"
    listing = cached_or_fetch(
        spike_list if spike_list.exists() else fund_dir / "kap_report_list.json",
        lambda: session.request("GET", f"{KAP}/tr/api/disclosure/filter/FILTERYFBF/{match.group(1)}/{REPORT_TYPE}/365"))
    reports = [item.get("disclosureBasic", {}) for item in json.loads(listing)] if listing else []
    result["reports"] = len(reports)

    spike_history = RAW / f"fonFiyatBilgiGetir_{code}.body"
    if not spike_history.exists():
        cached_or_fetch(fund_dir / "tefas_history_3y.json",
                        lambda: session.request("POST", f"{TEFAS_API}/fonFiyatBilgiGetir",
                                                json={"fonKodu": code, "dil": "TR", "periyod": 36}))

    for basic in reports:
        index, period = basic["disclosureIndex"], f"{basic['year']}-{basic['donem']:02d}"
        if any(fund_dir.glob(f"{period}_{index}*")):
            result["reused"] += 1
            continue
        earlier = RAW / f"kap_portfoy_dagilim_{code}_{period}.pdf"
        if earlier.exists():
            shutil.copyfile(earlier, fund_dir / f"{period}_{index}.pdf")
            result["reused"] += 1
            continue
        disclosure = session.request("GET", f"{KAP}/tr/Bildirim/{index}")
        file_ids = sorted(set(re.findall(r"file/download/([a-f0-9]{32})", disclosure.text))) if disclosure else []
        if not file_ids:
            result["problems"].append(f"{period}: no attachment found")
            continue
        for n, file_id in enumerate(file_ids):
            response = session.request("GET", f"{KAP}/tr/api/file/download/{file_id}")
            if response is None:
                result["problems"].append(f"{period}: download failed")
                continue
            body = response.content
            start = body.find(b"%PDF-")
            suffix = f"_{n}" if len(file_ids) > 1 else ""
            if start >= 0:
                (fund_dir / f"{period}_{index}{suffix}.pdf").write_bytes(body[start:])
            else:  # not a PDF: keep it as-is and record what it was
                (fund_dir / f"{period}_{index}{suffix}.bin").write_bytes(body)
                result["problems"].append(
                    f"{period}: attachment is not a PDF ({response.headers.get('content-disposition')})")
            result["files"] += 1
    return result


def download(funds: list[str], pause: float, log_name: str) -> None:
    session = Session(pause)
    summary = []
    try:
        for code in funds:
            fund = download_fund(session, code)
            summary.append(fund)
            print(f"{code}: {fund['reports']} reports, {fund['files']} downloaded, {fund['reused']} reused, "
                  f"problems: {fund['problems'] or 'none'}", flush=True)
    finally:
        KAP_DIR.mkdir(parents=True, exist_ok=True)
        (KAP_DIR / log_name).write_text(
            json.dumps({"funds": summary, "requests": session.log}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8")
        print(f"{len(session.log)} requests", flush=True)


def tefas_history(code: str) -> dict[str, Decimal]:
    path = RAW / f"fonFiyatBilgiGetir_{code}.body"
    if not path.exists():
        path = KAP_DIR / code / "tefas_history_3y.json"
    if not path.exists():
        return {}
    rows = json.loads(path.read_text(encoding="utf-8"))["resultList"]
    return {row["tarih"][:10]: Decimal(repr(row["fiyat"])) for row in rows}


def check_pdf(pdf: Path, period: str, history: dict[str, Decimal]) -> dict:
    document = pymupdf.open(pdf)
    lines = [line for page in document for line in page_lines(page)]
    text = "\n".join(lines)
    record = {
        "file": pdf.name, "bytes": pdf.stat().st_size, "pages": document.page_count,
        "text_chars": len(text), "images": sum(len(page.get_images()) for page in document),
        "creator": document.metadata.get("creator"),
        "sections_found": [name for name, marker in SECTIONS.items() if marker in text],
    }
    raw = {}
    for name, label in LABELS.items():
        found = next((re.search(rf"^{label}\s*:\s*(\S+)", line) for line in lines if re.search(rf"^{label}", line)), None)
        if found:
            raw[name] = found.group(1)
    record["fields_found"] = sorted(raw)
    record["fields_missing"] = sorted(set(LABELS) - set(raw))
    record["number_shapes"] = {name: shape(value) for name, value in raw.items()}
    values, unparsed = {}, []
    for name, value in raw.items():
        try:
            values[name] = parse_number(value)
        except (ValueError, ArithmeticError):
            unparsed.append(name)
    record["unparsed"] = unparsed

    year, month = (int(part) for part in period.split("-"))
    month_end = date(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1)
    previous_end = date(year, month, 1) - timedelta(days=1)
    dates = sorted(history)

    def first_after(day: date) -> str | None:
        return next((d for d in dates if d > day.isoformat()), None)

    checks = {}
    if {"units_outstanding", "month_end_price", "total_value"} <= values.keys() and values["total_value"]:
        checks["units_x_price_vs_total_rel_diff"] = float(
            abs(values["units_outstanding"] * values["month_end_price"] - values["total_value"]) / values["total_value"])
    if "month_end_price" in values and first_after(month_end):
        checks["month_end_price_equals_next_business_day_row"] = history[first_after(month_end)] == values["month_end_price"]
        checks["month_end_price_equals_month_end_row"] = history.get(month_end.isoformat()) == values["month_end_price"]
    if "previous_month_price" in values and first_after(previous_end):
        checks["previous_price_equals_next_business_day_row"] = \
            history[first_after(previous_end)] == values["previous_month_price"]
    if {"cash_in_from_unit_issuance", "cash_out_from_unit_redemption"} <= values.keys():
        checks["cash_flow_fields_both_zero"] = (values["cash_in_from_unit_issuance"] == 0
                                                and values["cash_out_from_unit_redemption"] == 0)
    start = next((i for i, l in enumerate(lines) if l.startswith("F-)Aylık Ortalama Portföydeki")), None)
    end = next((i for i, l in enumerate(lines) if l.startswith("G-)Aylık Ortalama Portföy Devir")), None)
    if start is not None and end is not None:
        mix = [m for m in (re.match(r"^([a-z]\d?)-\) ?(.+?)\s*:\s*(\S+)$", l) for l in lines[start + 1:end]) if m]
        try:
            checks["asset_mix_items"] = len(mix)
            checks["asset_mix_sum_pct"] = float(sum(parse_number(m.group(3)) for m in mix))
        except (ValueError, ArithmeticError):
            checks["asset_mix_unparsed"] = True
    checks["investor_count_present"] = bool(re.search(r"yatırımcı say|katılımcı say|kişi say", text, re.IGNORECASE))
    record["checks"] = checks
    return record


def check(funds_to_check: list[str], out: Path) -> None:
    returns = json.loads((RAW / "fonGetiriBazliBilgiGetir_YAT.body").read_text(encoding="utf-8"))["resultList"]
    meta = {row["fonKodu"]: row for row in returns}
    funds = []
    for code in funds_to_check:
        fund_dir = KAP_DIR / code
        history = tefas_history(code)
        reports = []
        for path in sorted(fund_dir.glob("*_*.*")):
            if path.suffix not in (".pdf", ".bin"):
                continue
            period = path.name[:7]
            if path.suffix == ".bin":
                reports.append({"file": path.name, "not_pdf": True})
                continue
            try:
                reports.append({"period": period, **check_pdf(path, period, history)})
            except Exception as exc:  # recorded per file, not hidden
                reports.append({"period": period, "file": path.name, "error": f"{type(exc).__name__}: {exc}"})
        name = meta.get(code, {}).get("fonUnvan", "")
        funds.append({"fund": code, "type": meta.get(code, {}).get("fonTurAciklama"),
                      "company": name.split(" PORTFÖY")[0] if " PORTFÖY" in name else name.split()[0],
                      "reports": reports})
        ok = sum(1 for r in reports if not r.get("fields_missing") and "error" not in r and not r.get("not_pdf"))
        print(f"{code}: {len(reports)} files, {ok} with all {len(LABELS)} fields", flush=True)
    out.write_text(json.dumps({"checked_at_utc": datetime.now(timezone.utc).isoformat(), "funds": funds},
                                  indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("download", "check"))
    parser.add_argument("--funds", nargs="+", default=FUNDS, help="fund codes (default: the original ten)")
    parser.add_argument("--pause", type=float, default=PAUSE_SECONDS, help="seconds between requests")
    parser.add_argument("--log", default="download_log.json", help="download: request log file name in raw/kap/")
    parser.add_argument("--out", type=Path, default=RESULTS, help="check: results file")
    args = parser.parse_args()
    funds = [code.upper() for code in args.funds]
    if args.command == "download":
        download(funds, args.pause, args.log)
    else:
        check(funds, args.out)


if __name__ == "__main__":
    main()
