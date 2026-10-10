"""Deterministic D1-only Turkish comments for the dated view.

Templates refer only to "seçilen tarih": no month names, fixed dates, fraud,
safety, causality, prediction or advice wording (fund_review_dated/PROTOCOL.md).
"""
from __future__ import annotations

from p50k.research_reviews.dated_contracts import DENOMINATOR, NO_CROSSING_NOTE_TR, d1_state

UNAVAILABLE_TR = "Seçilen tarihte benzer fonlarla getiri karşılaştırması için yeterli veri yok."
STALE_TR = ("Benzer fonlarla getiri hesabının son gözlemi seçilen tarihe ait değil; "
            "bu tarihin uygun bulguları arasında sayılmadı.")
CROSSING_TR = ("Seçilen tarihe kadarki son 60 veri konumunda ortanca günlük fazla getiri, "
               "sabit araştırma eşiğinin üzerinde.")
NO_CROSSING_TR = ("Seçilen tarihe kadarki son 60 veri konumunda benzer fonlarla getiri farkı "
                  "sabit araştırma eşiğini aşmadı. " + NO_CROSSING_NOTE_TR)
TEMPLATES_TR = {"UNAVAILABLE": UNAVAILABLE_TR, "STALE": STALE_TR, "ELIGIBLE_CROSSING": CROSSING_TR,
                "ELIGIBLE_NO_CROSSING": NO_CROSSING_TR}
_ORDER = {"ELIGIBLE_CROSSING": 0, "STALE": 1, "UNAVAILABLE": 1, "ELIGIBLE_NO_CROSSING": 2}


def describe_dated(d1: dict) -> str:
    return TEMPLATES_TR[d1_state(d1)]


def dated_order(record: dict) -> tuple[int, str]:
    """Eligible crossing; not eligible (stale or unavailable); eligible no crossing; code."""
    return _ORDER[record["d1_state"]], record["code"]


def summarize_dated(records: list[dict]) -> dict:
    states = [record["d1_state"] for record in records]
    return {
        "denominator": DENOMINATOR, "record_count": len(records),
        "d1_eligible_crossing": states.count("ELIGIBLE_CROSSING"),
        "d1_eligible_no_crossing": states.count("ELIGIBLE_NO_CROSSING"),
        "d1_stale": states.count("STALE"),
        "d1_unavailable": states.count("UNAVAILABLE"),
        "no_price_at_cutoff": sum(not record["date_context"]["has_positive_price_on_or_before_cutoff"]
                                  for record in records),
    }
