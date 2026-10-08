from __future__ import annotations

import unittest

from p50k.research_reviews.comments import describe, finding_order, summarize
from p50k.research_reviews.contracts import empty_finding


def available(kind: str, crossing: bool = False, *, stale: bool = False, negative: bool = False) -> dict:
    finding = empty_finding(kind)
    finding.update(arithmetic_status="AVAILABLE", research_screen="CROSSING" if crossing else "NO_CROSSING",
                   freshness="STALE" if stale else "FRESH", statistic="-0.10" if negative else "0.10")
    if kind == "flow":
        finding["direction"] = "OUTFLOW_ESTIMATE" if negative else "INFLOW_ESTIMATE"
    return finding


class FundReviewCommentTests(unittest.TestCase):
    def test_two_separate_periods_do_not_claim_fraud(self):
        text, assessment, count = describe(available("d1", True), available("flow", True))
        self.assertEqual((assessment, count), ("FULL", 2))
        self.assertIn("Farklı dönemleri", text)
        self.assertIn("tahmini giriş", text)
        self.assertNotIn("dolandır", text)
        self.assertNotIn("güvenli", text)

    def test_negative_crossing_is_outflow_estimate(self):
        text, _, count = describe(available("d1"), available("flow", True, negative=True))
        self.assertEqual(count, 1)
        self.assertIn("tahmini çıkış", text)
        self.assertIn("bildirilmiş nakdi değildir", text)

    def test_missing_is_not_a_negative_or_safety_verdict(self):
        text, assessment, count = describe(empty_finding("d1"), empty_finding("flow"))
        self.assertEqual((assessment, count), ("UNAVAILABLE", 0))
        self.assertIn("yeterli veri yok", text)
        self.assertNotIn("eşiğini aşmadı", text)
        self.assertNotIn("güvenli", text)

    def test_known_crossing_survives_incomplete_other_finding(self):
        text, assessment, count = describe(empty_finding("d1"), available("flow", True))
        self.assertEqual((assessment, count), ("PARTIAL", 1))
        self.assertIn("Değerlendirme eksik", text)

    def test_stale_d1_preserves_separate_description_not_combination(self):
        text, assessment, count = describe(available("d1", True, stale=True), available("flow", True))
        self.assertEqual((assessment, count), ("PARTIAL", 1))
        self.assertIn("son gözlemi güncel değil", text)
        self.assertNotIn("iki ayrı", text)

    def test_order_is_four_groups_then_code(self):
        records = [{"code": code, "assessment": assessment, "eligible_crossings": count}
                   for code, assessment, count in (("Z99", "FULL", 0), ("Z98", "PARTIAL", 0),
                                                    ("Z97", "PARTIAL", 1), ("Z96", "FULL", 2),
                                                    ("Z95", "FULL", 1))]
        ordered = sorted(records, key=finding_order)
        self.assertEqual([r["code"] for r in ordered], ["Z96", "Z95", "Z97", "Z98", "Z99"])
        summary = summarize(records)
        self.assertEqual(summary["two_findings"] + summary["one_finding"] +
                         summary["unassessable_no_findings"] + summary["no_findings"], summary["total"])


if __name__ == "__main__":
    unittest.main()
