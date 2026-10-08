"""Read the headline fields of every downloaded KAP monthly report into per-fund monthly series (2026-10-07).

Run from the repo root:
    PYTHONPATH=services python research/spikes/2026-10-06-tefas/kap_series.py [--funds A B ...]

Reads raw/kap/{code}/{period}_{index}[_n].pdf and each fund's report list (for publish
times). When 5-year TEFAS prices are in the liquidation case folder it also checks the
month-end prices against them. Writes raw/kap_series/{code}.json with the values
(gitignored) and kap_series_coverage.json with structure and checks only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pymupdf

from kap_pdf_check import page_lines
from p50k.providers.kap_report import read_headline

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
KAP_DIR = RAW / "kap"
SERIES_DIR = RAW / "kap_series"
COVERAGE = HERE / "kap_series_coverage.json"
PRICES = HERE.parents[1] / "events" / "2026-09-17-spk-liquidations" / "raw" / "prices"
ISTANBUL = timezone(timedelta(hours=3))
HEADER_PAGES = 3
TOLERANCE = Decimal("0.0001")  # units x price against total value, relative
TARGETS = {f["code"] for f in json.loads((HERE.parents[1] / "events" / "2026-09-17-spk-liquidations"
                                           / "liquidated_funds.json").read_text(encoding="utf-8"))["funds"]}
REQUIRED = ("total_value", "units_outstanding", "period_end_price", "previous_period_price")


def report_list(code: str) -> dict[int, dict]:
    for path in (KAP_DIR / code / "kap_report_list.json", RAW / f"kap_portfolio_reports_{code}.body"):
        if path.exists():
            return {item["disclosureBasic"]["disclosureIndex"]: item["disclosureBasic"]
                    for item in json.loads(path.read_text(encoding="utf-8"))}
    return {}


def publish_time(text: str | None) -> str | None:
    try:
        return datetime.strptime(text, "%d.%m.%Y %H:%M:%S").replace(tzinfo=ISTANBUL).isoformat()
    except (TypeError, ValueError):
        return None


def tefas_prices(code: str) -> dict[str, Decimal] | None:
    path = PRICES / f"{code}.json"
    if not path.exists():
        return None
    rows = json.loads(path.read_text(encoding="utf-8"))["rows"]
    return {day: Decimal(price) for day, price in rows if price is not None}


def next_row_price(prices: dict[str, Decimal], month_end: date) -> Decimal | None:
    """TEFAS dates a price one business day after its valuation date."""
    later = [day for day in prices if day > month_end.isoformat()]
    return prices[min(later)] if later else None


def month_end(period: str) -> date:
    year, month = (int(part) for part in period.split("-"))
    return date(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1)


def read_pdf(path: Path):
    document = pymupdf.open(path)
    lines = [line for page in list(document)[:HEADER_PAGES] for line in page_lines(page)]
    headline = read_headline(lines)
    if not lines:
        headline = replace(headline, problems=("no text layer (image-only PDF)", *headline.problems))
    return headline, document.metadata.get("creator")


def build_fund(code: str) -> tuple[list[dict], dict]:
    listing = report_list(code)
    prices = tefas_prices(code)
    by_period: dict[str, dict] = {}
    creators = Counter()
    for pdf in sorted((KAP_DIR / code).glob("*.pdf")):
        match = re.match(r"(\d{4}-\d{2})_(\d+)", pdf.name)
        if not match:
            continue
        period, index = match.group(1), int(match.group(2))
        headline, creator = read_pdf(pdf)
        creators[creator] += 1
        found = sum(getattr(headline, name) is not None for name in REQUIRED)
        if period in by_period and by_period[period]["_found"] >= found:
            continue  # a second attachment with fewer fields (for example a sales section)
        basic = listing.get(index, {})
        weekly = basic.get("period") == "HB"
        if basic.get("year") and basic.get("donem"):
            period = f"{basic['year']}-W{basic['donem']:02d}" if weekly else f"{basic['year']}-{basic['donem']:02d}"
        by_period[period] = {
            "period": period, "cadence": "weekly" if weekly else "monthly", "disclosure_index": index,
            "published_at": publish_time(basic.get("publishDate")),
            "company_title": basic.get("companyTitle"), "_found": found,
            **{name: (None if getattr(headline, name) is None else str(getattr(headline, name)))
               for name in (*REQUIRED, "period_change_pct", "cash_in", "cash_out")},
            "problems": list(headline.problems)}
    series = [{k: v for k, v in by_period[p].items() if k != "_found"} for p in sorted(by_period)]

    complete = [r for r in series if all(r[name] for name in REQUIRED)]
    checks = Counter()
    problems = Counter(re.sub(r": .*", "", problem) + ": " + ("not found" if "not found" in problem else "other")
                       for r in series for problem in r["problems"] if not problem.startswith(("cash_", "period_change")))
    previous, worst_gap = None, Decimal(0)
    for r in series:
        if all(r[name] for name in REQUIRED):
            units, price, total = Decimal(r["units_outstanding"]), Decimal(r["period_end_price"]), Decimal(r["total_value"])
            if total:
                gap = abs(units * price - total) / total
                checks["units_x_price_matches_total"] += gap <= TOLERANCE
                checks["units_x_price_within_one_percent"] += gap <= Decimal("0.01")
                worst_gap = max(worst_gap, gap)
            if prices and r["cadence"] == "monthly":
                for name, end in (("period_end_price", month_end(r["period"])),
                                  ("previous_period_price", month_end(r["period"]).replace(day=1) - timedelta(days=1))):
                    checks[f"{name}_checked"] += 1
                    checks[f"{name}_matches_next_tefas_row"] += next_row_price(prices, end) == Decimal(r[name])
        if previous and r["cadence"] == previous["cadence"] == "monthly" and r["previous_period_price"] and previous["period_end_price"]:
            checks["consecutive_reports_checked"] += 1
            checks["previous_price_equals_last_months_price"] += r["previous_period_price"] == previous["period_end_price"]
        previous = r
    coverage = {"reports": len(series), "complete": len(complete), "creators": dict(creators),
                "company_title": next((r["company_title"] for r in series if r["company_title"]), None),
                "missing_fields": dict(problems), "checks": dict(checks), "units_x_price_worst_relative_gap": float(round(worst_gap, 4)),
                "has_publish_time": sum(1 for r in series if r["published_at"]),
                "weekly_reports": sum(r["cadence"] == "weekly" for r in series)}
    if coverage["weekly_reports"] and code in TARGETS:
        coverage["first_weekly_report_published"] = min(
            r["published_at"] for r in series if r["cadence"] == "weekly" and r["published_at"])
    return series, coverage


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--funds", nargs="+", help="fund codes (default: every folder in raw/kap/ with PDFs)")
    args = parser.parse_args()
    codes = [c.upper() for c in args.funds] if args.funds else sorted(
        d.name for d in KAP_DIR.iterdir() if d.is_dir() and any(d.glob("*.pdf")))
    SERIES_DIR.mkdir(parents=True, exist_ok=True)
    coverage = {}
    for code in codes:
        series, coverage[code] = build_fund(code)
        (SERIES_DIR / f"{code}.json").write_text(json.dumps(
            {"fund": code, "source": "KAP Portföy Dağılım Raporu", "reports": series}, indent=1, ensure_ascii=False) + "\n",
            encoding="utf-8")
        c = coverage[code]
        print(f"{code}: {c['complete']}/{c['reports']} complete", flush=True)
    summary = {
        "funds": len(coverage), "reports": sum(c["reports"] for c in coverage.values()),
        "complete": sum(c["complete"] for c in coverage.values()),
        "funds_with_no_complete_report": sorted(code for code, c in coverage.items() if not c["complete"]),
        "funds_with_weekly_reports": {"targets": sorted(c for c, v in coverage.items() if v["weekly_reports"] and c in TARGETS),
                                      "non_targets": sum(1 for c, v in coverage.items() if v["weekly_reports"] and c not in TARGETS)},
    }
    COVERAGE.write_text(json.dumps({"checked_at_utc": datetime.now(timezone.utc).isoformat(), "summary": summary,
                                    "funds": coverage}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
