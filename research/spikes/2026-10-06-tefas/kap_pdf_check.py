"""KAP monthly portfolio report check (2026-10-06).

Reads one KAP "Portföy Dağılım Raporu" PDF, pulls the labelled fields from
sections I, II and IV, and cross-checks the month-end prices against the dated
TEFAS price history that spike.py saved. No LLM is involved: the PDF has an
extractable text layer.

The PDF is downloaded only if it is not already in raw/kap/reports/ at the
repo root (two requests: the disclosure page, then the file). Run from the repo root:
    python research/spikes/2026-10-06-tefas/kap_pdf_check.py

Writes kap_pdf_results.json with which fields exist, their number formats and
the date checks. Field values stay under the repo's raw/, which is gitignored
because KAP data rights have not been reviewed.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import httpx
import pymupdf

FUND = "TTE"
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
RAW = REPO / "raw"
KAP_DIR = RAW / "kap" / "reports"
REPORT_LIST = KAP_DIR / f"kap_portfolio_reports_{FUND}.body"  # saved by spike.py
TEFAS_HISTORY = RAW / "tefas" / "responses" / f"fonFiyatBilgiGetir_{FUND}.body"  # saved by spike.py
RESULTS = HERE / "kap_pdf_results.json"

LABELS = {
    "total_value": r"D-\)Toplam Değer/Net Varlık Değeri",
    "units_outstanding": r"E-\) ?Katılma Payı Sayısı",
    "month_end_price": r"A-\)Ay Sonu Pay Fiyatı \(TL\)",
    "previous_month_price": r"B-\)Önceki Ay Pay Fiyatı \(TL\)",
    "monthly_change_pct": r"C-\)Aylık Pay Fiyatı Artış Oranı \(TL\)",
    "ytd_change_pct": r"D-\)Yılbaşına Göre Fiyat Artış Oranı",
    "annual_change_pct": r"E-\)Yıllık Pay Fiyatı Artış Oranı",
    "cash_in_from_unit_issuance": r"I-\)Katılma Payı İhraçlarından Kaynaklanan Nakit Girişleri \(TL\)",
    "cash_out_from_unit_redemption": r"İ-\)Katılma Payı İadelerinden Kaynaklanan Nakit Çıkışları \(TL\)",
}
SECTIONS = {
    "I fund identity": "I-FONU TANITICI BİLGİLER",
    "II performance": "II-FONUN PERFORMANSINA İLİŞKİN BİLGİLER",
    "III holdings": "III-FON PORTFÖY DEĞERİ TABLOSU",
    "IV fund total value": "IV-FON TOPLAM DEĞERİ TABLOSU",
    "V expenses": "V-AY İÇİNDE YAPILAN GİDERLER",
    "VI-A corporate actions": "VI-A-GEÇEN AY İÇİNDE",
    "VII sales from portfolio": "VII-PORTFÖYDEN SATIŞLAR",
}


def page_lines(page: pymupdf.Page) -> list[str]:
    """Rebuild text lines from word positions; labels and values sit in separate blocks."""
    words = sorted(page.get_text("words"), key=lambda w: ((w[1] + w[3]) / 2, w[0]))
    lines, current, center = [], [], None
    for word in words:
        middle = (word[1] + word[3]) / 2
        if current and abs(middle - center) > 2.5:
            lines.append(current)
            current = []
        if not current:
            center = middle
        current.append(word)
    if current:
        lines.append(current)
    return [" ".join(w[4] for w in sorted(line, key=lambda w: w[0])) for line in lines]


def shape(text: str) -> str:
    return re.sub(r"\d", "9", text)


def parse_number(text: str) -> Decimal:
    """Accept 1,234.56 and 1.234,56; reject a lone comma that could mean either."""
    s = text.strip().replace(" ", "")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:
        head, _, tail = s.rpartition(",")
        if s.count(",") != 1 or len(tail) == 3:
            raise ValueError(f"ambiguous number {text!r}")
        s = f"{head}.{tail}"
    return Decimal(s)


def download(disclosure_index: int, target: Path) -> list[dict]:
    from borsapy._providers.base import BaseProvider

    records = []
    headers = {"User-Agent": BaseProvider.DEFAULT_HEADERS["User-Agent"]}
    with httpx.Client(verify=True, timeout=60, headers=headers) as client:
        page = client.get(f"https://kap.org.tr/tr/Bildirim/{disclosure_index}")
        records.append({"url": str(page.url), "status": page.status_code, "bytes": len(page.content)})
        page.raise_for_status()
        file_ids = sorted(set(re.findall(r"file/download/([a-f0-9]{32})", page.text)))
        if len(file_ids) != 1:
            raise RuntimeError(f"expected one attachment, found {len(file_ids)}")
        response = client.get(f"https://kap.org.tr/tr/api/file/download/{file_ids[0]}")
        body = response.content
        records.append({"url": str(response.url), "status": response.status_code, "bytes": len(body),
                        "sha256": hashlib.sha256(body).hexdigest()})
        response.raise_for_status()
    start = body.find(b"%PDF-")  # KAP wraps the file in a Java-serialized byte array
    if start < 0:
        raise RuntimeError("no %PDF- marker in the download")
    target.write_bytes(body[start:])
    return records


def main() -> None:
    latest = json.loads(REPORT_LIST.read_text(encoding="utf-8"))[0]["disclosureBasic"]
    year, month = latest["year"], latest["donem"]
    pdf_path = KAP_DIR / f"kap_portfoy_dagilim_{FUND}_{year}-{month:02d}.pdf"
    requests = [] if pdf_path.exists() else download(latest["disclosureIndex"], pdf_path)

    document = pymupdf.open(pdf_path)
    lines = [line for page in document for line in page_lines(page)]
    text = "\n".join(lines)

    fields, raw_values = {}, {}
    for name, label in LABELS.items():
        match = next((re.search(rf"^{label}\s*:\s*(\S+)", line) for line in lines
                      if re.search(rf"^{label}", line)), None)
        fields[name] = bool(match)
        if match:
            raw_values[name] = match.group(1)
    values = {name: parse_number(raw) for name, raw in raw_values.items()}

    # Section II-F: monthly average share of each asset type, a-) Hisse Senedi ... t-) Vaad ...
    start = next(i for i, line in enumerate(lines) if line.startswith("F-)Aylık Ortalama Portföydeki"))
    end = next(i for i, line in enumerate(lines) if line.startswith("G-)Aylık Ortalama Portföy Devir"))
    mix = [re.match(r"^([a-z]\d?)-\) ?(.+?)\s*:\s*(\S+)$", line) for line in lines[start + 1:end]]
    mix = [m for m in mix if m]
    mix_total = sum(parse_number(m.group(3)) for m in mix)

    section_iv = re.search(r"^FON TOPLAM DEĞERİ\s+(\S+)\s+(\S+)\s*%", text, re.MULTILINE)
    holdings = text[text.find(SECTIONS["III holdings"]):text.find(SECTIONS["IV fund total value"])]

    history = {row["tarih"][:10]: Decimal(repr(row["fiyat"]))
               for row in json.loads(TEFAS_HISTORY.read_text(encoding="utf-8"))["resultList"]}
    tefas_dates = sorted(history)

    def matching_dates(price: Decimal) -> list[str]:
        return [d for d in tefas_dates if history[d] == price]

    def first_row_after(day: date) -> str | None:
        return next((d for d in tefas_dates if d > day.isoformat()), None)

    month_end = date(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1)
    previous_month_end = date(year, month, 1) - timedelta(days=1)

    checks = {
        "units_x_month_end_price_vs_total_rel_diff": float(
            abs(values["units_outstanding"] * values["month_end_price"] - values["total_value"])
            / values["total_value"]),
        "month_end_price_tefas_dates": matching_dates(values["month_end_price"]),
        "previous_month_price_tefas_dates": matching_dates(values["previous_month_price"]),
        "month_end_price_is_first_tefas_row_after_month_end":
            matching_dates(values["month_end_price"]) == [first_row_after(month_end)],
        "previous_price_is_first_tefas_row_after_previous_month_end":
            matching_dates(values["previous_month_price"]) == [first_row_after(previous_month_end)],
        "section_iv_total_equals_section_i_total":
            bool(section_iv) and parse_number(section_iv.group(1)) == values["total_value"],
        "asset_mix_items": len(mix),
        "asset_mix_sum_pct": float(mix_total),
        "cash_flow_fields_both_zero":
            values.get("cash_in_from_unit_issuance") == 0 and values.get("cash_out_from_unit_redemption") == 0,
        "investor_count_present": bool(re.search(r"yatırımcı|katılımcı sayısı|kişi sayısı", text, re.IGNORECASE)),
        "negative_amounts_in_holdings_table": len(re.findall(r"(?<![\w.,])-\d[\d,]*\.\d+", holdings)),
        "decimal_comma_in_section_iv_percent": bool(section_iv) and "," in section_iv.group(2),
    }

    results = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "fund": FUND,
        "report": {"disclosure_index": latest["disclosureIndex"], "year": year, "month": month,
                   "publish_date_raw": latest["publishDate"], "month_end": month_end.isoformat()},
        "requests": requests or "none: used the PDF already in raw/kap/reports/",
        "pdf": {
            "file": pdf_path.relative_to(REPO).as_posix(),
            "bytes": pdf_path.stat().st_size,
            "sha256": hashlib.sha256(pdf_path.read_bytes()).hexdigest(),
            "pages": document.page_count,
            "text_chars": len(text),
            "images": sum(len(page.get_images()) for page in document),
            "creator": document.metadata.get("creator"),
        },
        "sections_found": {name: marker in text for name, marker in SECTIONS.items()},
        "fields_found": fields,
        "number_shapes": {name: shape(raw) for name, raw in raw_values.items()},
        "asset_mix_labels": [m.group(2) for m in mix],
        "checks": checks,
    }
    RESULTS.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(checks, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
