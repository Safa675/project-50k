"""Run the pre-registered price-only detectors on the top 100 funds (PREREGISTRATION.md).

Run from the repo root once the price files are in ../raw/prices/:
    PYTHONPATH=services python research/events/2026-09-17-spk-liquidations/price_detectors/run.py

Categories come from the local snapshot database (fund_snapshots.default_db_path()).
Writes results.json next to this file, which names targets only, and
../raw/price_detectors/funds.json with every fund's detail (gitignored).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import detectors as det  # noqa: E402
from p50k.jobs.fund_snapshots import connect, default_db_path  # noqa: E402
from p50k.jobs.price_history import load  # noqa: E402

EVENT = HERE.parent
WINDOW_START, WINDOW_END = date(2025, 10, 6), date(2026, 9, 16)
ORDER_DATE = date(2026, 9, 17)
REFERENCE_DATES = 250
YOUNG_SENSITIVITY = (365, 1095)
DETECTORS = {  # id: (name, percentile, alarm side)
    "D1": ("persistent excess return", 99, "above"),
    "D2": ("change in excess return", 99, "above"),
    "D3": ("return autocorrelation", 99, "above"),
    "D4": ("correlation with peers", 1, "below"),
}


def categories(codes: list[str]) -> dict[str, str]:
    db = connect(default_db_path())
    rows = dict(db.execute(f"SELECT fund, category FROM fund_snapshots WHERE fund IN ({','.join('?' * len(codes))}) "
                           "ORDER BY retrieved_at", codes).fetchall())  # the newest snapshot wins
    return {code: rows[code] for code in codes}


def statistics(universe: list[str], category: dict[str, str], returns: np.ndarray) -> dict[str, dict]:
    members: dict[str, list[int]] = {}
    for k, code in enumerate(universe):
        members.setdefault(category[code], []).append(k)
    out = {}
    for idx in members.values():
        block = returns[idx]
        for j, k in enumerate(idx):
            r = returns[k]
            if len(idx) > det.MIN_PEERS:
                m = det.peer_median(block, j)
                e = r - m
                peer_based = {"D1": det.excess_level(e), "D2": det.excess_change(e), "D4": det.peer_correlation(r, m)}
            else:  # fewer than 11 universe funds in the category: no 10 peers
                peer_based = {d: np.full(len(r), np.nan) for d in ("D1", "D2", "D4")}
            out[universe[k]] = {**peer_based, "D3": det.autocorrelation(r)}
    return out


def thresholds(stats: dict, universe: list[str], category: dict[str, str], mask: np.ndarray) -> dict:
    return {d: {cat: det.threshold([stats[c][d][mask] for c in universe if category[c] == cat], pct)
                for cat in sorted(set(category.values()))}
            for d, (_, pct, _) in DETECTORS.items()}


def evaluate(values: np.ndarray, hits: np.ndarray, mask: np.ndarray, cal: list[date]) -> dict:
    defined = ~np.isnan(values) & mask
    if not defined.any():
        return {"evaluable": False, "reason": "statistic undefined in the period"}
    hits = hits & defined
    first = cal[int(np.argmax(hits))] if hits.any() else None
    return {"evaluable": True, "flagged": bool(hits.any()),
            "first_alarm": first.isoformat() if first else None,
            "days_before_order": (ORDER_DATE - first).days if first else None,
            "alarm_days": int(hits.sum()), "evaluable_days": int(defined.sum())}


def run_detectors(stats, ages, limits, universe, category, mask, cal, young_days=det.YOUNG_DAYS) -> dict:
    per_fund = {}
    for code in universe:
        results = {}
        for d, (_, _, side) in DETECTORS.items():
            limit = limits[d][category[code]]
            if limit is None:
                results[d] = {"evaluable": False, "reason": "no threshold for the category"}
                continue
            values = stats[code][d]
            with np.errstate(invalid="ignore"):
                hits = values > limit if side == "above" else values < limit
            results[d] = evaluate(values, hits, mask, cal)
        with np.errstate(invalid="ignore"):
            results["D5"] = evaluate(ages[code], ages[code] < young_days, mask, cal)
        per_fund[code] = results
    return per_fund


def summarize(per_fund: dict, detector: str, universe: list[str], targets: list[str], category: dict) -> dict:
    ev = {c for c in universe if per_fund[c][detector]["evaluable"]}
    flagged = {c for c in ev if per_fund[c][detector]["flagged"]}
    others = [c for c in universe if c not in targets and c in ev]
    days = sum(per_fund[c][detector]["evaluable_days"] for c in others)
    by_category = Counter()
    for c in others:
        by_category[(category[c], "evaluable")] += 1
        by_category[(category[c], "flagged")] += c in flagged
    return {
        "targets_flagged": len(flagged & set(targets)), "targets_evaluable": len(ev & set(targets)),
        "nontargets_flagged": len(flagged - set(targets)), "nontargets_evaluable": len(others),
        "expected_targets_flagged_at_random": round(len(flagged) * len(ev & set(targets)) / len(ev), 2) if ev else None,
        "nontarget_alarm_day_rate": round(sum(per_fund[c][detector]["alarm_days"] for c in others) / days, 4) if days else None,
        "nontargets_by_category": {cat: {"flagged": by_category[(cat, "flagged")], "evaluable": by_category[(cat, "evaluable")]}
                                   for cat in sorted({category[c] for c in others})},
        "targets": {c: {"category": category[c], **{k: v for k, v in per_fund[c][detector].items()
                                                     if k not in ("alarm_days", "evaluable_days")}} for c in targets},
    }


def short(summary: dict) -> dict:
    keys = ("targets_flagged", "targets_evaluable", "nontargets_flagged", "nontargets_evaluable",
            "expected_targets_flagged_at_random")
    return {**{k: summary[k] for k in keys},
            "targets_flagged_codes": [c for c, t in summary["targets"].items() if t.get("flagged")]}


def first_defined(values: np.ndarray, mask: np.ndarray, cal: list[date]) -> date | None:
    defined = ~np.isnan(values) & mask
    return cal[int(np.argmax(defined))] if defined.any() else None


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    universe = (EVENT / "top100_funds.txt").read_text(encoding="utf-8").split()
    listed = {f["code"] for f in json.loads((EVENT / "liquidated_funds.json").read_text(encoding="utf-8"))["funds"]}
    targets = [c for c in universe if c in listed]
    category = categories(universe)
    series = {c: load(EVENT / "raw" / "prices" / f"{c}.json") for c in universe}
    days = sorted({d for rows in series.values() for d, _ in rows})
    cal = [date.fromisoformat(d) for d in days]
    pos = {d: i for i, d in enumerate(days)}
    prices = np.full((len(universe), len(days)), np.nan)
    first_priced = {}
    for k, code in enumerate(universe):
        for d, p in series[code]:
            if p is not None:
                prices[k, pos[d]] = float(p)
        priced = [d for d, p in series[code] if p is not None]
        first_priced[code] = date.fromisoformat(priced[0]) if priced else None
    returns = np.vstack([det.log_returns(row) for row in prices])

    stats = statistics(universe, category, returns)
    ages = {c: det.age_days(cal, first_priced[c]) for c in universe}
    when = np.array(cal)
    calibration = when < WINDOW_START
    window = (when >= WINDOW_START) & (when <= WINDOW_END)
    reference = calibration & (np.cumsum(calibration[::-1])[::-1] <= REFERENCE_DATES)

    limits = thresholds(stats, universe, category, calibration)
    primary = run_detectors(stats, ages, limits, universe, category, window, cal)
    summaries = {d: summarize(primary, d, universe, targets, category) for d in [*DETECTORS, "D5"]}
    in_reference = run_detectors(stats, ages, limits, universe, category, reference, cal)
    for d, summary in summaries.items():
        ref = summarize(in_reference, d, universe, targets, category)
        summary["reference_year_nontargets_flagged"] = ref["nontargets_flagged"]
        summary["reference_year_nontargets_evaluable"] = ref["nontargets_evaluable"]

    composite = {c: sum(1 for d in summaries if primary[c][d].get("flagged")) for c in universe}

    last_year_limits = thresholds(stats, universe, category, reference)
    last_year = run_detectors(stats, ages, last_year_limits, universe, category, window, cal)
    young = {n: short(summarize(run_detectors(stats, ages, limits, universe, category, window, cal, n),
                                "D5", universe, targets, category)) for n in YOUNG_SENSITIVITY}

    window_only = returns.copy()
    window_only[:, when <= WINDOW_START] = np.nan  # the first return needs two window prices
    stats_window_only = statistics(universe, category, window_only)
    warmup = {}
    for d in DETECTORS:
        starts = [first_defined(stats_window_only[c][d], window, cal) for c in universe
                  if not np.isnan(stats[c][d][window]).all()]
        lost = sorted(sum(1 for x in cal if WINDOW_START <= x < s) if s else int(window.sum()) for s in starts)
        warmup[d] = {"funds": len(starts), "median_window_dates_lost": lost[len(lost) // 2] if lost else None,
                     "funds_never_defined": sum(1 for s in starts if s is None)}

    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=HERE, capture_output=True, text=True).stdout.strip()
    results = {
        "run_at_utc": datetime.now(timezone.utc).isoformat(), "git_head": commit,
        "preregistration_sha256": sha256(HERE / "PREREGISTRATION.md"), "detectors_sha256": sha256(HERE / "detectors.py"),
        "window": [WINDOW_START.isoformat(), WINDOW_END.isoformat()], "order_date": ORDER_DATE.isoformat(),
        "universe": len(universe), "targets": targets, "calendar": [days[0], days[-1], len(days)],
        "detectors": {d: name for d, (name, _, _) in DETECTORS.items()} | {"D5": f"young fund (< {det.YOUNG_DAYS} days)"},
        "thresholds": limits,
        "results": summaries,
        "composite": {"targets": {c: composite[c] for c in targets},
                      "nontargets_histogram": dict(sorted(Counter(composite[c] for c in universe
                                                                  if c not in targets).items()))},
        "sensitivity": {
            "thresholds_from_last_250_dates_only": {
                "thresholds": last_year_limits,
                "results": {d: short(summarize(last_year, d, universe, targets, category)) for d in DETECTORS}},
            "young_days": young,
            "window_only_history": {"warmup": warmup, "note": "with no earlier prices there is no data before the "
                                    "window to set thresholds, and every fund's first visible price is the window start"},
        },
    }
    (HERE / "results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    detail_dir = EVENT / "raw" / "price_detectors"
    detail_dir.mkdir(parents=True, exist_ok=True)
    (detail_dir / "funds.json").write_text(json.dumps(
        {c: {"category": category[c], "target": c in targets, "first_priced": first_priced[c].isoformat()
             if first_priced[c] else None, "composite": composite[c], "primary": primary[c],
             "last_year_thresholds": last_year[c]} for c in universe}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")

    for d, s in summaries.items():
        print(f"{d}: targets {s['targets_flagged']}/{s['targets_evaluable']} "
              f"(random {s['expected_targets_flagged_at_random']}), non-targets {s['nontargets_flagged']}/"
              f"{s['nontargets_evaluable']}, reference year {s['reference_year_nontargets_flagged']}/"
              f"{s['reference_year_nontargets_evaluable']}")
        for c, t in s["targets"].items():
            print(f"    {c} {t['category']}: " + (f"first alarm {t['first_alarm']} ({t['days_before_order']} days before)"
                                                 if t.get("flagged") else ("no alarm" if t["evaluable"] else t["reason"])))
    print("composite targets:", results["composite"]["targets"])
    print("composite non-targets:", results["composite"]["nontargets_histogram"])


if __name__ == "__main__":
    main()
