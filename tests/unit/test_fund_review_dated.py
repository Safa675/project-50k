"""Dated D1 view: grid, cutoff, D1 equivalence, invariance, snapshot bound and copy.

Synthetic, invented codes and values only. numpy-dependent classes skip without
the optional analysis dependency, as in test_fund_review_bundle.py.
"""
from __future__ import annotations

import copy
import json
import math
import re
import sqlite3
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from p50k.research_reviews import bundle as v1_bundle
from p50k.research_reviews import dated_bundle, dated_review
from p50k.research_reviews.bundle import canonical_bytes, d1_context, load_frozen_detector
from p50k.research_reviews.contracts import METADATA, empty_finding
from p50k.research_reviews.dated_bundle import bounded_snapshot, index_entry, load_dated_bundle
from p50k.research_reviews.dated_comments import (
    CROSSING_TR, NO_CROSSING_TR, STALE_TR, TEMPLATES_TR, UNAVAILABLE_TR, dated_order, describe_dated,
    summarize_dated,
)
from p50k.research_reviews.dated_contracts import (
    DENYLIST_TR, EXACT_SENTENCES_TR, FIXED_VIEW_LINK_TR, GUARD_TR, NO_CROSSING_NOTE_TR, NOT_COMPUTED_TR,
    SNAPSHOT_BOUND, SNAPSHOT_LABEL_TEMPLATE_TR, SURVIVORSHIP_TR, THRESHOLD_FIXED, WHY_DATES_TR,
    WINDOW_END_LABEL_TR, cutoff_at_for, d1_state, date_or_month_mentions, denylist_hits, grid_dates,
    metadata_for, validate_cutoff, validate_grid,
)
from p50k.research_reviews.dated_review import (
    assemble_dated, calendar_dates, dated_d1_context, dated_price_rows, has_positive_price,
)

REPO = Path(__file__).resolve().parents[2]
PROTOCOL = REPO / "research/events/2026-09-17-spk-liquidations/fund_review_dated/PROTOCOL.md"
CODES = [f"Z{i:02d}" for i in range(100)]
HOLIDAYS = frozenset({"2025-12-31", "2026-05-27", "2026-05-28", "2026-05-29"})
EXPECTED_GRID = ["2025-10-31", "2025-11-28", "2025-12-30", "2026-01-30", "2026-02-27", "2026-03-31",
                 "2026-04-30", "2026-05-26", "2026-06-30", "2026-07-31", "2026-08-31", "2026-09-16"]
CATEGORY_A, CATEGORY_B, CATEGORY_C = "Synthetic A", "Synthetic B", "Synthetic C"
THRESHOLDS = {CATEGORY_A: "0.0005", CATEGORY_B: None, CATEGORY_C: "0.0005"}
PROVENANCE = {**THRESHOLD_FIXED, "calibration_run_at_utc": SNAPSHOT_BOUND, "results_sha256": "1" * 64,
              "threshold_map_sha256": "2" * 64, "detectors_sha256": "3" * 64, "preregistration_sha256": "4" * 64}
SNAPSHOT = {"bound": SNAPSHOT_BOUND, "latest_retrieved_at": "2026-10-06T18:00:00+00:00", "projection_sha256": "5" * 64}
OFF_GRID = ("2026-01-15", "2026-01-31", "2025-10-06")
MALFORMED = ("2026-1-30", "2026-02-30", "2026-01-30T00:00", " 2026-01-30", "20260130", "", None, 20260130)
OUT_OF_RANGE = ("2025-10-03", "2025-10-05", "2026-09-17", "2026-10-07", "2024-01-31")


def weekdays(start: str, end: str, skip=HOLIDAYS) -> list[str]:
    days, current = [], date.fromisoformat(start)
    while current <= date.fromisoformat(end):
        if current.weekday() < 5 and current.isoformat() not in skip:
            days.append(current.isoformat())
        current += timedelta(days=1)
    return days


def category_of(code: str) -> str | None:
    number_ = int(code[1:])
    return CATEGORY_A if number_ < 30 else CATEGORY_B if number_ < 45 else CATEGORY_C if number_ < 50 else None


def synthetic_prices(calendar: list[str], codes=CODES) -> dict[str, dict]:
    """Invented prices: a fund-specific drift plus a deterministic wiggle."""
    result = {}
    for k, code in enumerate(codes):
        base = 0.002 if code == "Z00" else 0.0003 + 0.00001 * (k % 30)
        level, rows = 0.0, []
        for t, day in enumerate(calendar):
            level += base + 0.0004 * math.sin(0.7 * t + k)
            rows.append([day, repr(100 * math.exp(level))])
        result[code] = {"fund": code, "source": "TEFAS fonFiyatBilgiGetir", "rows": rows}
    return result


def synthetic_identities(codes=CODES) -> dict[str, dict]:
    return {code: {"name": f"Synthetic fund {code}", "category": category_of(code)} for code in codes}


def long_inputs() -> tuple[list[str], dict, dict]:
    calendar = weekdays("2025-07-01", "2026-09-30")
    prices = synthetic_prices(calendar)
    # Z01 has no price on 2026-03-31; Z02 is first priced on 2026-03-12.
    prices["Z01"]["rows"] = [row if row[0] != "2026-03-31" else [row[0], None] for row in prices["Z01"]["rows"]]
    prices["Z02"]["rows"] = [row for row in prices["Z02"]["rows"] if row[0] >= "2026-03-12"]
    return calendar, prices, synthetic_identities()


def assemble_kwargs(prices, identities, detector, grid=EXPECTED_GRID, refs=None) -> dict:
    return {"grid": grid, "price_payloads": prices, "identities": identities, "thresholds": THRESHOLDS,
            "price_refs": refs or {}, "sources": [], "manifest": [], "detector": detector,
            "registration": {"protocol_sha256": "6" * 64, "protocol_commit": "7" * 40},
            "threshold_provenance": PROVENANCE, "snapshot": SNAPSHOT}


def _normalized_protocol() -> str:
    return re.sub(r"\s+", " ", PROTOCOL.read_text(encoding="utf-8"))


class DatedContractTests(unittest.TestCase):
    def test_validate_cutoff_checks_only_format_calendar_and_range(self):
        for value in ("2025-10-06", "2026-09-16", "2026-01-15", "2026-01-31"):
            self.assertEqual(validate_cutoff(value), value)
        for value in (*MALFORMED, *OUT_OF_RANGE):
            with self.assertRaises(ValueError, msg=repr(value)):
                validate_cutoff(value)

    def test_cutoff_and_metadata_extend_v1_labels(self):
        self.assertEqual(cutoff_at_for("2026-03-31"), "2026-03-31T23:59:59+03:00")
        metadata = metadata_for("2026-03-31")
        self.assertEqual({key: value for key, value in metadata.items() if key in METADATA and key != "cutoff_at"},
                         {key: value for key, value in METADATA.items() if key != "cutoff_at"})
        self.assertEqual(metadata["cutoff_at"], "2026-03-31T23:59:59+03:00")
        self.assertEqual(metadata["cutoff_date"], "2026-03-31")
        self.assertEqual((metadata["knowledge_basis"], metadata["findings_scope"], metadata["date_rule"]),
                         ("RECORDED_SOURCE_DATE_RECONSTRUCTION", "D1_ONLY", "MONTH_END_PLUS_WINDOW_END_V1"))
        self.assertEqual(metadata_for("2026-09-16")["cutoff_at"], METADATA["cutoff_at"])

    def test_d1_state_mapping(self):
        finding = empty_finding("d1")
        self.assertEqual(d1_state(finding), "UNAVAILABLE")
        finding.update(arithmetic_status="AVAILABLE", freshness="STALE", research_screen="CROSSING")
        self.assertEqual(d1_state(finding), "STALE")
        finding.update(freshness="FRESH")
        self.assertEqual(d1_state(finding), "ELIGIBLE_CROSSING")
        finding.update(research_screen="NO_CROSSING")
        self.assertEqual(d1_state(finding), "ELIGIBLE_NO_CROSSING")
        finding.update(freshness="UNKNOWN")
        with self.assertRaises(ValueError):
            d1_state(finding)

    def test_exact_sentences_are_verbatim_from_protocol(self):
        protocol = _normalized_protocol()
        for sentence in EXACT_SENTENCES_TR:
            self.assertIn(sentence, protocol)
        prefix, suffix = SNAPSHOT_LABEL_TEMPLATE_TR.split("{date}")
        self.assertIn(f"{prefix}{{that date}}{suffix}", protocol)
        self.assertIn('"' + '", "'.join(DENYLIST_TR) + '"', protocol)


class DatedGridTests(unittest.TestCase):
    def test_grid_is_last_calendar_date_per_month_in_window(self):
        calendar = weekdays("2025-09-01", "2026-10-07")
        self.assertEqual(grid_dates(calendar), EXPECTED_GRID)
        self.assertEqual(grid_dates(reversed(calendar)), EXPECTED_GRID)
        with self.assertRaises(ValueError):
            grid_dates([day for day in calendar if day != "2026-09-16"])
        with self.assertRaises(ValueError):
            grid_dates([day for day in calendar if not day.startswith("2026-02")])
        with self.assertRaises(ValueError):
            grid_dates([day for day in calendar if not "2025-10-06" <= day <= "2025-10-31"])
        with self.assertRaises(ValueError):
            grid_dates([*calendar, "2026-2-01"])
        # The October date must lie inside the range: early-October rows alone do not count.
        self.assertEqual(grid_dates([d for d in calendar if not "2025-10-07" <= d <= "2025-10-31"])[0], "2025-10-06")

    def test_validate_grid_refuses_structural_changes(self):
        self.assertEqual(validate_grid(EXPECTED_GRID), EXPECTED_GRID)
        bad = [EXPECTED_GRID[:-1], EXPECTED_GRID + ["2026-09-16"], list(reversed(EXPECTED_GRID)),
               EXPECTED_GRID[:-1] + ["2026-09-15"], ["2025-10-03"] + EXPECTED_GRID[1:],
               EXPECTED_GRID[:3] + ["2025-12-31"] + EXPECTED_GRID[4:], tuple(EXPECTED_GRID[:-1]) + ("2026-9-16",),
               "2026-09-16", None]
        for grid in bad:
            with self.assertRaises(ValueError, msg=repr(grid)):
                validate_grid(grid)

    def test_grid_uses_row_dates_only_and_truncates_before_union(self):
        calendar = weekdays("2025-09-01", "2026-10-07")
        prices = synthetic_prices(calendar, CODES[:3])
        prices["Z03"] = None
        with patch.object(v1_bundle, "number", side_effect=AssertionError("value read")), \
                patch.object(dated_review, "number", side_effect=AssertionError("value read")), \
                patch.object(sqlite3, "connect", side_effect=AssertionError("snapshot read")):
            first = calendar_dates(prices, "2026-09-16")
            self.assertEqual(first, [day for day in calendar if day <= "2026-09-16"])
            self.assertEqual(grid_dates(first), EXPECTED_GRID)
            changed = copy.deepcopy(prices)
            for index, row in enumerate(changed["Z00"]["rows"]):
                row[1] = ("0", None, "999999999", "NaN")[index % 4]
            changed["Z01"]["liquidated_after_cutoff"] = True
            changed["Z02"]["rows"].extend([["2026-09-17", "1"], ["2026-10-30", "1"], ["2026-09-17", "2"]])
            permuted = dict(reversed(list(changed.items())))
            self.assertEqual(calendar_dates(permuted, "2026-09-16"), first)
            # Truncation precedes the union: an earlier end never sees later rows.
            self.assertEqual(calendar_dates(changed, "2026-03-31"), [d for d in first if d <= "2026-03-31"])
            # Structural rules as v1: a bad row or date drops that fund's dates entirely.
            only = {"Z00": copy.deepcopy(prices["Z00"])}
            only["Z00"]["rows"].append(["2026-10-01"])
            self.assertEqual(calendar_dates(only, "2026-09-16"), [])
            only["Z00"]["rows"][-1] = ["2026-9-1", "1"]
            self.assertEqual(calendar_dates(only, "2026-09-16"), [])
            only["Z00"]["rows"][-1] = ["2026-01-30", "1"]
            self.assertEqual(calendar_dates(only, "2026-09-16"), [])
            self.assertEqual(calendar_dates(only, "2026-01-29"), [d for d in first if d <= "2026-01-29"])
            self.assertEqual(calendar_dates({"Z00": {"rows": "bad"}, "Z01": {"_invalid": True}}, "2026-09-16"), [])

    def test_out_of_range_malformed_or_off_grid_refused_by_each_layer(self):
        guards = (patch.object(v1_bundle, "read_fund_json", side_effect=AssertionError("fund input read")),
                  patch.object(sqlite3, "connect", side_effect=AssertionError("snapshot read")),
                  patch.object(dated_review, "dated_d1_context", side_effect=AssertionError("computed")))
        with guards[0], guards[1], guards[2]:
            for value in (*MALFORMED, *OUT_OF_RANGE):
                with self.assertRaises(ValueError, msg=repr(value)):
                    validate_cutoff(value)
                with self.assertRaises(ValueError, msg=repr(value)):
                    assemble_dated(CODES, cutoff_date=value, **assemble_kwargs({}, {}, None))
                if value is not None:
                    with patch.object(dated_bundle, "_read_json", side_effect=AssertionError("bundle read")),                             self.assertRaises(ValueError, msg=repr(value)):
                        load_dated_bundle(Path("/synthetic-not-read"), expected_date=value)
                with self.assertRaises(ValueError, msg=repr(value)):
                    index_entry({"entries": []}, value)
            for value in OFF_GRID:
                self.assertEqual(validate_cutoff(value), value)
                with self.assertRaises(ValueError, msg=value):
                    assemble_dated(CODES, cutoff_date=value, **assemble_kwargs({}, {}, None))
                with self.assertRaises(LookupError, msg=value):
                    index_entry({"entries": [{"date": d} for d in EXPECTED_GRID]}, value)


class DatedD1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.detector = load_frozen_detector(REPO)
        except ImportError:
            raise unittest.SkipTest("dated D1 requires the optional numpy analysis dependency")
        cls.calendar, cls.prices, cls.identities = long_inputs()

    def short_inputs(self, end: str = "2026-09-16", length: int = 61):
        days, current = [], date.fromisoformat(end)
        while len(days) < length:
            if current.weekday() < 5:
                days.append(current.isoformat())
            current -= timedelta(days=1)
        days.reverse()
        prices = {code: {"rows": [[day, str(math.exp(index * (0.002 if code == "Z00" else 0.001)))]
                                   for index, day in enumerate(days)]} for code in CODES}
        identities = {code: {"category": "Synthetic category"} for code in CODES}
        return days, prices, identities

    def dated(self, prices, identities, cutoff, threshold="0.0001", refs=None):
        return dated_d1_context(CODES, prices, identities, {"Synthetic category": threshold}, refs or {},
                                self.detector, cutoff)

    def reference(self, prices, identities, end: str, valid: set[str]):
        """Frozen detector once over the calendar of the given valid funds up to end."""
        import numpy as np
        rows = {code: {row[0]: row[1] for row in prices[code]["rows"] if row[0] <= end}
                for code in CODES if code in valid and prices.get(code)}
        calendar = sorted({day for values in rows.values() for day in values})
        matrix = np.full((len(CODES), len(calendar)), np.nan)
        for i, code in enumerate(CODES):
            for j, day in enumerate(calendar):
                value = rows.get(code, {}).get(day)
                if value is not None and float(value) > 0:
                    matrix[i, j] = float(value)
        returns = np.vstack([self.detector.log_returns(row) for row in matrix])
        output = {}
        for own, code in enumerate(CODES):
            members = [i for i, peer in enumerate(CODES) if identities[code]["category"] is not None and
                       identities[peer]["category"] == identities[code]["category"]]
            if len(members) < 11:
                continue
            peers = [i for i in members if i != own]
            excess = returns[own] - self.detector.peer_median(returns[members], members.index(own))
            output[code] = (excess, self.detector.excess_level(excess), np.sum(np.isfinite(returns[peers]), axis=0))
        return calendar, output

    def test_dated_d1_at_window_end_equals_v1(self):
        _, prices, identities = self.short_inputs()
        prices["Z03"]["rows"][20][1] = None
        prices["Z04"]["rows"][-1][1] = "0"
        prices["Z05"]["rows"].append(["2026-9-30", "1"])
        prices["Z06"]["rows"].append(prices["Z06"]["rows"][-5])
        for code in CODES[:20]:
            prices[code]["rows"].extend([["2026-09-17", "999999999"], ["2026-09-17", "1"]])
        prices["Z07"] = None
        identities["Z08"]["category"] = None
        refs = {code: [f"{code}-ref", "global-ref"] for code in CODES}
        expected = d1_context(CODES, prices, identities, {"Synthetic category": "0.0001"}, refs, self.detector)
        self.assertEqual(self.dated(prices, identities, "2026-09-16", refs=refs), expected)
        long_expected = d1_context(CODES, self.prices, self.identities, THRESHOLDS, refs, self.detector)
        self.assertEqual(dated_d1_context(CODES, self.prices, self.identities, THRESHOLDS, refs, self.detector,
                                          "2026-09-16"), long_expected)
        states = {d1_state(finding) for finding, _ in long_expected.values()}
        self.assertEqual(states, {"ELIGIBLE_CROSSING", "ELIGIBLE_NO_CROSSING", "UNAVAILABLE"})

    def test_grid_calendar_equals_dated_d1_window(self):
        calendar = calendar_dates(self.prices, "2026-09-16")
        self.assertEqual(grid_dates(calendar), EXPECTED_GRID)
        for cutoff in ("2025-10-31", "2026-05-26", "2026-09-16"):
            truncated = [day for day in calendar if day <= cutoff]
            finding, _ = dated_d1_context(CODES, self.prices, self.identities, THRESHOLDS, {}, self.detector,
                                          cutoff)["Z10"]
            self.assertEqual(finding["metric_period"], {"start": truncated[-60], "end": cutoff})
            self.assertEqual(finding["window_positions"], 60)

    def test_statistic_equals_frozen_value_at_cutoff_index(self):
        import numpy as np
        calendar, reference = self.reference(self.prices, self.identities, "2026-09-16", set(CODES))
        for cutoff in ("2025-10-31", "2026-01-30", "2026-08-31"):
            index = calendar.index(cutoff)
            result = dated_d1_context(CODES, self.prices, self.identities, THRESHOLDS, {}, self.detector, cutoff)
            checked = 0
            for code, (excess, level, counts) in reference.items():
                finding, _ = result[code]
                window = range(max(0, index - 59), index + 1)
                contributing = [i for i in window if np.isfinite(excess[i])]
                self.assertEqual(finding["usable_observations"], len(contributing), code)
                if contributing:
                    self.assertEqual(finding["latest_contributing_at"], calendar[contributing[-1]], code)
                    self.assertEqual(finding["eligible_peers"], int(min(counts[i] for i in contributing)), code)
                if finding["statistic"] is not None:
                    self.assertEqual(float(finding["statistic"]), float(level[index]), code)
                    checked += 1
                elif np.isfinite(level[index]):
                    # The value exists but is not reported without a stored category threshold.
                    self.assertEqual(finding["missing_reasons"], ["stored_category_calibration_missing"], code)
            self.assertGreaterEqual(checked, 28)
        # Strictly above: equal threshold is no crossing, just below crosses.
        finding, _ = result["Z10"]
        stat = finding["statistic"]
        for threshold, screen in ((stat, "NO_CROSSING"), (str(np.nextafter(float(stat), -1.0)), "CROSSING")):
            found, _ = dated_d1_context(CODES, self.prices, self.identities, {**THRESHOLDS, CATEGORY_A: threshold},
                                        {}, self.detector, "2026-08-31")["Z10"]
            self.assertEqual(found["research_screen"], screen)

    def test_frozen_equality_needs_the_same_validity(self):
        prices = copy.deepcopy(self.prices)
        duplicate = next(row for row in prices["Z03"]["rows"] if row[0] == "2026-02-10")
        prices["Z03"]["rows"].append(list(duplicate))
        c1, c2 = "2026-01-30", "2026-02-27"
        self.assertEqual(calendar_dates(prices, "2026-09-16"), calendar_dates(self.prices, "2026-09-16"))
        at_c1 = dated_d1_context(CODES, prices, self.identities, THRESHOLDS, {}, self.detector, c1)
        at_c2 = dated_d1_context(CODES, prices, self.identities, THRESHOLDS, {}, self.detector, c2)
        self.assertNotIn("duplicate_price_date", at_c1["Z03"][0]["missing_reasons"])
        self.assertIn("duplicate_price_date", at_c2["Z03"][0]["missing_reasons"])
        same_calendar, same = self.reference(prices, self.identities, "2026-09-16", set(CODES))
        full_calendar, full = self.reference(prices, self.identities, "2026-09-16", set(CODES) - {"Z03"})
        index = same_calendar.index(c1)
        differing = 0
        for code in same:
            if code == "Z03" or at_c1[code][0]["statistic"] is None:
                continue
            self.assertEqual(float(at_c1[code][0]["statistic"]), float(same[code][1][index]), code)
            differing += float(at_c1[code][0]["statistic"]) != float(full[code][1][full_calendar.index(c1)])
        self.assertGreater(differing, 0)

    def test_later_data_never_changes_an_earlier_cutoff(self):
        c1, c2 = "2026-01-30", "2026-03-31"
        refs = {code: [f"{code}-price"] for code in CODES}
        kwargs = assemble_kwargs(self.prices, self.identities, self.detector, refs=refs)
        first = assemble_dated(CODES, cutoff_date=c1, **kwargs)
        later = assemble_dated(CODES, cutoff_date=c2, **kwargs)
        changed = copy.deepcopy(self.prices)
        for k, code in enumerate(CODES):
            changed[code]["liquidated_after_cutoff"] = True
            for row in changed[code]["rows"]:
                if c1 < row[0]:
                    row[1] = ("999999999", "0", None, str(1 + k))[k % 4] if k % 3 == 0 else row[1]
        existing = {row[0] for row in changed["Z02"]["rows"]}
        changed["Z02"]["rows"].extend([[day, "5"] for day in self.calendar if c1 < day < "2026-03-12"
                                       and day not in existing])
        changed["Z03"]["rows"].append(["2026-09-30", "1"])
        self.assertEqual(calendar_dates(changed, "2026-09-16"), calendar_dates(self.prices, "2026-09-16"))
        kwargs_changed = assemble_kwargs(changed, self.identities, self.detector, refs=refs)
        self.assertEqual(canonical_bytes(assemble_dated(CODES, cutoff_date=c1, **kwargs_changed)),
                         canonical_bytes(first))
        self.assertNotEqual(canonical_bytes(assemble_dated(CODES, cutoff_date=c2, **kwargs_changed)),
                            canonical_bytes(later))

    def test_freshness_relative_to_selected_date(self):
        kwargs = assemble_kwargs(self.prices, self.identities, self.detector)
        stale = assemble_dated(CODES, cutoff_date="2026-03-31", **kwargs)
        record = next(row for row in stale["funds"] if row["code"] == "Z01")
        self.assertEqual(record["d1_state"], "STALE")
        self.assertEqual(record["d1"]["freshness"], "STALE")
        self.assertIn("final_contributing_observation_before_cutoff", record["d1"]["missing_reasons"])
        self.assertIsNotNone(record["d1"]["statistic"])
        self.assertEqual(record["d1"]["latest_contributing_at"], "2026-03-30")
        self.assertEqual(record["comment_tr"], STALE_TR)
        self.assertGreaterEqual(stale["summary"]["d1_stale"], 1)
        fresh = assemble_dated(CODES, cutoff_date="2026-02-27", **kwargs)
        record = next(row for row in fresh["funds"] if row["code"] == "Z01")
        self.assertEqual(record["d1"]["freshness"], "FRESH")
        self.assertEqual(record["d1"]["latest_contributing_at"], "2026-02-27")
        self.assertIn(record["d1_state"], ("ELIGIBLE_CROSSING", "ELIGIBLE_NO_CROSSING"))

    def test_unpriced_fund_present_and_unavailable(self):
        prices = copy.deepcopy(self.prices)
        prices["Z04"]["rows"] = [[row[0], "0"] if row[0] <= "2026-01-30" else row for row in prices["Z04"]["rows"]]
        kwargs = assemble_kwargs(prices, self.identities, self.detector)
        payload = assemble_dated(CODES, cutoff_date="2026-01-30", **kwargs)
        self.assertEqual(len(payload["funds"]), 100)
        for code in ("Z02", "Z04"):
            record = next(row for row in payload["funds"] if row["code"] == code)
            self.assertEqual(record["d1"]["arithmetic_status"], "UNAVAILABLE")
            self.assertEqual(record["d1"]["research_screen"], "UNKNOWN")
            self.assertIsNone(record["d1"]["statistic"])
            self.assertEqual(record["chart"]["status"], "UNAVAILABLE")
            self.assertEqual(record["date_context"], {"has_positive_price_on_or_before_cutoff": False})
            self.assertEqual(record["comment_tr"], UNAVAILABLE_TR)
        summary = payload["summary"]
        self.assertEqual(summary["no_price_at_cutoff"], 2)
        self.assertLessEqual(summary["no_price_at_cutoff"], summary["d1_unavailable"])
        later = assemble_dated(CODES, cutoff_date="2026-03-31", **kwargs)
        self.assertTrue(next(r for r in later["funds"] if r["code"] == "Z02")["date_context"][
            "has_positive_price_on_or_before_cutoff"])
        self.assertFalse(has_positive_price(None, "2026-03-31"))
        self.assertTrue(has_positive_price({"rows": [["bad"], ["2026-03-30", "2"]]}, "2026-03-31"))

    def test_boundaries_at_earlier_cutoff(self):
        cutoff = "2026-01-30"
        for usable in (50, 49):
            _, prices, identities = self.short_inputs(cutoff, usable + 1)
            for code in CODES:
                prices[code]["rows"].extend([["2026-02-02", "999"], ["2026-02-03", "1"]])
            result, _ = self.dated(prices, identities, cutoff)["Z00"]
            self.assertEqual(result["usable_observations"], usable)
            self.assertEqual(result["arithmetic_status"], "AVAILABLE" if usable == 50 else "UNAVAILABLE")
            self.assertEqual(result["freshness"], "FRESH" if usable == 50 else "UNKNOWN")
        for count in (10, 9):
            _, prices, identities = self.short_inputs(cutoff)
            for code in CODES[count + 1:]:
                identities[code]["category"] = "other"
            result, _ = self.dated(prices, identities, cutoff)["Z00"]
            self.assertEqual(result["arithmetic_status"], "AVAILABLE" if count == 10 else "UNAVAILABLE")
            if count == 10:
                self.assertEqual(result["eligible_peers"], 10)

    def test_row_integrity_across_cutoffs(self):
        c1, c2 = "2026-01-30", "2026-02-27"
        base = {cutoff: dated_d1_context(CODES, self.prices, self.identities, THRESHOLDS, {}, self.detector, cutoff)
                for cutoff in (c1, c2)}
        for bad_row in (["2026-09-30"], ["2026-9-30", "1"], "row", ["2026-09-30", "1", "extra"], [20260930, "1"]):
            prices = copy.deepcopy(self.prices)
            prices["Z05"]["rows"].append(bad_row)
            for cutoff in (c1, c2, "2026-09-16"):
                finding, chart = dated_d1_context(CODES, prices, self.identities, THRESHOLDS, {}, self.detector,
                                                  cutoff)["Z05"]
                self.assertEqual(finding["arithmetic_status"], "UNAVAILABLE", repr(bad_row))
                self.assertTrue({"price_row_invalid", "price_date_invalid"} & set(finding["missing_reasons"]))
                self.assertEqual(chart["status"], "UNAVAILABLE")
        prices = copy.deepcopy(self.prices)
        prices["Z05"]["rows"].append(list(next(row for row in prices["Z05"]["rows"] if row[0] == "2026-02-10")))
        at_c1 = dated_d1_context(CODES, prices, self.identities, THRESHOLDS, {}, self.detector, c1)
        at_c2 = dated_d1_context(CODES, prices, self.identities, THRESHOLDS, {}, self.detector, c2)
        self.assertEqual(at_c1, base[c1])
        self.assertIn("duplicate_price_date", at_c2["Z05"][0]["missing_reasons"])
        self.assertNotEqual(at_c2, base[c2])
        rows, reasons = dated_price_rows({"rows": [["2026-01-29", "0"], ["2026-01-30", "NaN"],
                                                   ["2026-02-02", "999"]]}, c1)
        self.assertEqual((rows, reasons), ({"2026-01-29": None, "2026-01-30": None}, []))


class DatedSnapshotTests(unittest.TestCase):
    def make_db(self, root: Path, rows) -> Path:
        path = root / "snapshots.sqlite3"
        connection = sqlite3.connect(path)
        try:
            connection.execute("CREATE TABLE fund_snapshots(fund TEXT, category TEXT, raw_snapshot TEXT, "
                               "retrieved_at TEXT)")
            connection.executemany("INSERT INTO fund_snapshots VALUES(?,?,?,?)", rows)
            connection.commit()
        finally:
            connection.close()
        return path

    def execute(self, path: Path, sql: str, parameters=()) -> None:
        connection = sqlite3.connect(path)
        try:
            connection.execute(sql, parameters)
            connection.commit()
        finally:
            connection.close()

    def base_rows(self):
        return [(code, category_of(code), json.dumps({"fonUnvan": f"Synthetic fund {code}", "investors": 1}),
                 "2026-10-06T18:00:00+00:00") for code in CODES[:60]] + [
                ("Z00", "Old synthetic", '{"fonUnvan":"Old name"}', "2026-10-05T10:00:00+03:00"),
                ("AAA", "Unopened", '{"fonUnvan":"Unopened"}', "2026-10-06T18:00:00+00:00")]

    def test_projection_bounded_at_calibration_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.make_db(Path(tmp), self.base_rows())
            first, latest = bounded_snapshot(path, CODES)
            projection = json.loads(first)
            self.assertEqual(latest, "2026-10-06T18:00:00+00:00")
            self.assertEqual(projection["Z00"]["category"], CATEGORY_A)
            self.assertEqual(projection["Z00"]["name"], "Synthetic fund Z00")
            self.assertNotIn("AAA", projection)
            self.assertNotIn("Z60", projection)
            # Appended after the bound (UTC and +03:00 forms): bytes unchanged.
            self.execute(path, "INSERT INTO fund_snapshots VALUES(?,?,?,?)",
                         ("Z00", "Moved", '{"fonUnvan":"Renamed"}', "2026-10-07T08:52:12.470548+00:00"))
            self.execute(path, "INSERT INTO fund_snapshots VALUES(?,?,?,?)",
                         ("Z01", "Moved", '{"fonUnvan":"Renamed"}', "2026-10-07T11:53:00+03:00"))
            self.execute(path, "UPDATE fund_snapshots SET raw_snapshot=? WHERE fund=?",
                         ('{"fonUnvan":"Synthetic fund Z02","investors":999,"liquidated":true}', "Z02"))
            self.assertEqual(bounded_snapshot(path, CODES), (first, latest))
            # Exactly at the bound is included.
            self.execute(path, "INSERT INTO fund_snapshots VALUES(?,?,?,?)",
                         ("Z03", "At bound", '{}', "2026-10-07T11:52:12.470547+03:00"))
            at_bound, latest_at_bound = bounded_snapshot(path, CODES)
            self.assertEqual(json.loads(at_bound)["Z03"]["category"], "At bound")
            self.assertEqual(latest_at_bound, "2026-10-07T11:52:12.470547+03:00")
            self.execute(path, "DELETE FROM fund_snapshots WHERE category=?", ("At bound",))
            self.assertEqual(bounded_snapshot(path, CODES), (first, latest))
            # Edited or backdated rows before the bound change the projection.
            self.execute(path, "UPDATE fund_snapshots SET category=? WHERE fund=? AND category=?",
                         ("Edited", "Z05", CATEGORY_A))
            self.assertNotEqual(bounded_snapshot(path, CODES)[0], first)
            self.execute(path, "UPDATE fund_snapshots SET category=? WHERE fund=? AND category=?",
                         (CATEGORY_A, "Z05", "Edited"))
            self.assertEqual(bounded_snapshot(path, CODES)[0], first)
            self.execute(path, "INSERT INTO fund_snapshots VALUES(?,?,?,?)",
                         ("Z06", "Backdated", '{}', "2026-10-07T00:00:00+00:00"))
            self.assertNotEqual(bounded_snapshot(path, CODES)[0], first)
            # On Windows an open connection would block deleting the file.
            path.unlink()
            self.assertFalse(path.exists())

    def test_rows_digest_covers_every_bounded_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.make_db(Path(tmp), self.base_rows())
            projection, rows = bounded_snapshot(path, CODES), dated_bundle.bounded_rows_sha256(path, CODES)
            # Insertion order does not matter; the digest is over a canonical order.
            other = Path(tmp) / "reordered"
            other.mkdir()
            reordered = self.make_db(other, list(reversed(self.base_rows())))
            self.assertEqual(dated_bundle.bounded_rows_sha256(reordered, CODES), rows)
            # After the bound, unopened funds and unselected columns: unchanged.
            self.execute(path, "INSERT INTO fund_snapshots VALUES(?,?,?,?)",
                         ("Z00", "Moved", '{"fonUnvan":"Renamed"}', "2026-10-07T08:52:12.470548+00:00"))
            self.execute(path, "INSERT INTO fund_snapshots VALUES(?,?,?,?)",
                         ("AAA", "Unopened", "{}", "2026-10-01T00:00:00+00:00"))
            self.assertEqual(dated_bundle.bounded_rows_sha256(path, CODES), rows)
            # Behind the newest row: the projection is blind, the rows digest is not.
            for statement, parameters in (
                    ("UPDATE fund_snapshots SET category=? WHERE fund=? AND category=?",
                     ("Edited", "Z00", "Old synthetic")),
                    ("INSERT INTO fund_snapshots VALUES(?,?,?,?)",
                     ("Z05", "Backdated", "{}", "2026-10-01T00:00:00+03:00")),
                    ("DELETE FROM fund_snapshots WHERE fund=? AND category=?", ("Z00", "Edited"))):
                self.execute(path, statement, parameters)
                self.assertEqual(bounded_snapshot(path, CODES), projection)
                self.assertNotEqual(dated_bundle.bounded_rows_sha256(path, CODES), rows)
            self.execute(path, "DELETE FROM fund_snapshots WHERE category=?", ("Backdated",))
            self.execute(path, "INSERT INTO fund_snapshots VALUES(?,?,?,?)", self.base_rows()[60])
            self.assertEqual(dated_bundle.bounded_rows_sha256(path, CODES), rows)

    def test_missing_offset_free_unparseable_or_tied_timestamps_refuse(self):
        for retrieved in (None, "", "2026-10-06T18:00:00", "06.10.2026 18:00:00", "not a time"):
            with tempfile.TemporaryDirectory() as tmp:
                path = self.make_db(Path(tmp), [*self.base_rows(), ("Z07", "x", "{}", retrieved)])
                with self.assertRaises(ValueError, msg=repr(retrieved)):
                    bounded_snapshot(path, CODES)
        with tempfile.TemporaryDirectory() as tmp:
            path = self.make_db(Path(tmp), [*self.base_rows(),
                                            ("Z08", "x", "{}", "2026-10-06T21:00:00+03:00")])
            with self.assertRaises(ValueError):
                bounded_snapshot(path, CODES)
        with tempfile.TemporaryDirectory() as tmp:
            path = self.make_db(Path(tmp), self.base_rows())
            with self.assertRaises(ValueError):
                bounded_snapshot(path, CODES, "2026-10-07T08:52:12")
            with self.assertRaises(ValueError):
                bounded_snapshot(path, CODES[:-1])
            path.write_bytes(b"not a database")
            with self.assertRaises(ValueError):
                bounded_snapshot(path, CODES)


class DatedCommentTests(unittest.TestCase):
    def finding(self, status="AVAILABLE", freshness="FRESH", screen="CROSSING"):
        finding = empty_finding("d1")
        if status == "AVAILABLE":
            finding.update(arithmetic_status=status, freshness=freshness, research_screen=screen, statistic="0.1")
        return finding

    def test_d1_only_templates_and_denylist(self):
        templates = list(TEMPLATES_TR.values())
        self.assertEqual(len(set(templates)), 4)
        for text in templates:
            self.assertEqual(denylist_hits(text), [], text)
            self.assertEqual(date_or_month_mentions(text), [], text)
            self.assertIn("seçilen tarih", text.casefold())
            for word in ("kuruluş", "başlangıç", "launch", "hiç", "ilk", "son kesit", "neden", "yakala"):
                self.assertNotIn(word, text.casefold())
            for digit_date in re.findall(r"\d+", text):
                self.assertEqual(digit_date, "60")
        self.assertTrue(NO_CROSSING_TR.endswith(NO_CROSSING_NOTE_TR))
        self.assertNotIn(NO_CROSSING_NOTE_TR, CROSSING_TR + STALE_TR + UNAVAILABLE_TR)
        for sentence in (GUARD_TR, NO_CROSSING_NOTE_TR, WHY_DATES_TR, SURVIVORSHIP_TR):
            self.assertEqual(denylist_hits(sentence), [])
        for sentence in (WINDOW_END_LABEL_TR, NOT_COMPUTED_TR, FIXED_VIEW_LINK_TR,
                         SNAPSHOT_LABEL_TEMPLATE_TR.format(date="7 Ekim 2026")):
            self.assertEqual(denylist_hits(sentence), [], sentence)
        # Negative controls: every denylisted term is caught outside the exempt sentences.
        for term in DENYLIST_TR:
            self.assertEqual(denylist_hits(f"Örnek metin {term} burada."), [term])
            upper = term.replace("i", "İ").replace("ı", "I").upper()
            self.assertEqual(denylist_hits(f"{upper} ÖRNEK"), [term])
        self.assertEqual(denylist_hits(GUARD_TR + " önceden"), ["önceden"])
        self.assertEqual(date_or_month_mentions("Seçilen tarih 2026-03-31 ve Mart ayı."), ["2026-03-31", "Mart"])

    def test_comment_state_order_and_summary(self):
        cases = {"ELIGIBLE_CROSSING": self.finding(), "STALE": self.finding(freshness="STALE"),
                 "UNAVAILABLE": self.finding("UNAVAILABLE"), "ELIGIBLE_NO_CROSSING": self.finding(screen="NO_CROSSING")}
        for state, finding in cases.items():
            self.assertEqual(describe_dated(finding), TEMPLATES_TR[state])
        self.assertIn(NO_CROSSING_NOTE_TR, describe_dated(cases["ELIGIBLE_NO_CROSSING"]))
        records = []
        for index, code in enumerate(reversed(CODES)):
            state = list(cases)[index % 4]
            records.append({"code": code, "d1_state": state,
                            "date_context": {"has_positive_price_on_or_before_cutoff": index % 8 != 2}})
        records.sort(key=dated_order)
        groups = [row["d1_state"] for row in records]
        self.assertEqual(groups[:25], ["ELIGIBLE_CROSSING"] * 25)
        self.assertEqual(set(groups[25:75]), {"STALE", "UNAVAILABLE"})
        self.assertEqual(groups[75:], ["ELIGIBLE_NO_CROSSING"] * 25)
        self.assertEqual([row["code"] for row in records[25:75]], sorted(row["code"] for row in records[25:75]))
        summary = summarize_dated(records)
        self.assertEqual(summary, {"denominator": 100, "record_count": 100, "d1_eligible_crossing": 25,
                                   "d1_eligible_no_crossing": 25, "d1_stale": 25, "d1_unavailable": 25,
                                   "no_price_at_cutoff": 13})
        self.assertLessEqual(summary["no_price_at_cutoff"], summary["d1_unavailable"])
        self.assertEqual(sum(summary[key] for key in ("d1_eligible_crossing", "d1_eligible_no_crossing",
                                                      "d1_stale", "d1_unavailable")), 100)
        summary_text = json.dumps(summary)
        for forbidden in ("ever", "first", "lead", "hit", "false_alarm", "days_before"):
            self.assertNotIn(forbidden, summary_text)

    def test_outcome_keys_in_findings_change_nothing(self):
        finding = self.finding(screen="NO_CROSSING")
        marked = {**finding, "liquidated_after_cutoff": True}
        self.assertEqual(describe_dated(finding), describe_dated(marked))
        self.assertEqual(d1_state(finding), d1_state(marked))


if __name__ == "__main__":
    unittest.main()
