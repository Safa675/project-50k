"""Fixed contract of the dated D1 research view (fund_review_dated/PROTOCOL.md).

Standard library only. Nothing here reads a fund input; the v1 contract module is
imported read-only for the shared labels.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Iterable, Sequence

from p50k.research_reviews.contracts import METADATA

DATED_SCHEMA = "p50k.fund-review-dated.v1"
INDEX_SCHEMA = "p50k.fund-review-dated-index.v1"
WINDOW_START = "2025-10-06"
WINDOW_END = "2026-09-16"
DEFAULT_DATE = WINDOW_END
CALIBRATION_END_EXCLUSIVE = "2025-10-06"
DATE_RULE = "MONTH_END_PLUS_WINDOW_END_V1"
SNAPSHOT_BOUND = "2026-10-07T08:52:12.470547+00:00"
KNOWLEDGE_BASIS = "RECORDED_SOURCE_DATE_RECONSTRUCTION"
FINDINGS_SCOPE = "D1_ONLY"
AUDIT_STATUS = "D1_AND_CHART_EQUAL"
GRID_SIZE = 12
GRID_MONTHS = ("2025-10", "2025-11", "2025-12", "2026-01", "2026-02", "2026-03",
               "2026-04", "2026-05", "2026-06", "2026-07", "2026-08")
DENOMINATOR = 100

D1_STATES = ("ELIGIBLE_CROSSING", "ELIGIBLE_NO_CROSSING", "STALE", "UNAVAILABLE")
SOURCE_KINDS = frozenset({"PRICE", "SNAPSHOT", "CALIBRATION", "UNIVERSE", "PROTOCOL", "CODE"})
RECORD_KEYS = frozenset({"code", "name", "category", "comment_tr", "d1_state", "d1", "chart",
                         "date_context", "evidence"})
SUMMARY_KEYS = ("denominator", "record_count", "d1_eligible_crossing", "d1_eligible_no_crossing",
                "d1_stale", "d1_unavailable", "no_price_at_cutoff")
DATED_METADATA_KEYS = ("cutoff_date", "knowledge_basis", "findings_scope", "date_rule")
THRESHOLD_FIXED = {
    "calibration_end_exclusive": CALIBRATION_END_EXCLUSIVE,
    "percentile": 99,
    "crossing": "STRICTLY_ABOVE",
    "calibration_universe_basis": "OCTOBER_2026_INVESTOR_SNAPSHOT",
    "calibration_category_basis": "2026-10-06 snapshot",
    "note": "Thresholds were computed over a post-event universe that includes the evaluated funds.",
}
THRESHOLD_DIGEST_KEYS = ("results_sha256", "threshold_map_sha256", "detectors_sha256", "preregistration_sha256")
THRESHOLD_KEYS = frozenset({*THRESHOLD_FIXED, "calibration_run_at_utc", *THRESHOLD_DIGEST_KEYS})
SNAPSHOT_KEYS = frozenset({"bound", "latest_retrieved_at", "projection_sha256"})

# Exact Turkish sentences fixed by PROTOCOL.md "Records, comments and order" and
# "Selectable dates". Only these are exempt from the denylist.
GUARD_TR = ("Her tarih ayrı bir arşiv kesitidir. Bu görünüm, o tarihte bir uyarı verildiğini ya da "
            "sonucun önceden bilinebileceğini göstermez.")
NO_CROSSING_NOTE_TR = "Eşiğin aşılmaması bir güvenlik değerlendirmesi değildir."
SURVIVORSHIP_TR = ("Fon listesi Ekim 2026 yatırımcı sayılarına göre seçildi. Daha önceki tarihlerde henüz "
                   "fiyatı olmayan ya da sonradan kapanan fonlar bu görünümde doğru temsil edilmeyebilir.")
WHY_DATES_TITLE_TR = "Neden yalnızca bu tarihler?"
WHY_DATES_TR = ("Tarihler önceden belirlenmiş bir kurala göre seçildi: Ekim 2025–Ağustos 2026 arasında her "
                "ayın son TEFAS fiyat tarihi ve ön kayıtlı inceleme penceresinin son günü. Eşikler 6 Ekim 2025 "
                "öncesi verilerle hesaplandığı için daha önceki tarihler gösterilmez.")
WINDOW_END_LABEL_TR = "Ön kayıtlı inceleme penceresinin son günü; sabit görünümle aynı tarih."
NOT_COMPUTED_TR = "Bu tarih görünümünde hesaplanmadı."
FIXED_VIEW_LINK_TR = "Sabit 16 Eylül 2026 görünümüne geç (farklı tarih)"
SNAPSHOT_LABEL_TEMPLATE_TR = "Ad ve kategoriler: {date} anlık görüntüsü."
EXACT_SENTENCES_TR = (GUARD_TR, NO_CROSSING_NOTE_TR, SURVIVORSHIP_TR, WHY_DATES_TITLE_TR, WHY_DATES_TR,
                      WINDOW_END_LABEL_TR, NOT_COMPUTED_TR, FIXED_VIEW_LINK_TR)
DENYLIST_TR = ("erken uyarı", "ilk eşik aşımı", "gün önce", "ay önce", "önceden", "tahmin", "öngör",
               "risk yok", "güvenli", "tasfiye", "SPK", "dolandırıcılık")
MONTH_NAMES_TR = ("Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül",
                  "Ekim", "Kasım", "Aralık")

_DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")
_HEX64 = re.compile(r"[0-9a-f]{64}")


def validate_cutoff(value: object) -> str:
    """Format, calendar validity and range only; grid membership is checked elsewhere."""
    if not isinstance(value, str) or _DATE_PATTERN.fullmatch(value) is None:
        raise ValueError("cutoff date must be a canonical YYYY-MM-DD string")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("cutoff date is not a calendar date") from exc
    if parsed.isoformat() != value:
        raise ValueError("cutoff date must be a canonical YYYY-MM-DD string")
    if not date.fromisoformat(WINDOW_START) <= parsed <= date.fromisoformat(WINDOW_END):
        raise ValueError("cutoff date is outside the registered range")
    return value


def cutoff_at_for(value: str) -> str:
    return f"{validate_cutoff(value)}T23:59:59+03:00"


def validate_grid(dates: Sequence[str]) -> list[str]:
    """Structural check of a sealed grid: one date per month plus the window end."""
    selected = list(dates) if isinstance(dates, (list, tuple)) else None
    if selected is None or len(selected) != GRID_SIZE:
        raise ValueError("date grid must contain exactly 12 dates")
    for value in selected:
        validate_cutoff(value)
    if any(later <= earlier for earlier, later in zip(selected, selected[1:])):
        raise ValueError("date grid must be strictly ascending")
    if selected[-1] != WINDOW_END:
        raise ValueError("date grid must end at the registered window end")
    if [value[:7] for value in selected[:-1]] != list(GRID_MONTHS):
        raise ValueError("date grid must hold one date for each month from 2025-10 to 2026-08")
    return selected


def grid_dates(calendar: Iterable[str]) -> list[str]:
    """Latest calendar date per month 2025-10..2026-08, plus the window end."""
    days = set()
    for value in calendar:
        if not isinstance(value, str) or _DATE_PATTERN.fullmatch(value) is None:
            raise ValueError("calendar contains a non-canonical date")
        try:
            if date.fromisoformat(value).isoformat() != value:
                raise ValueError
        except ValueError as exc:
            raise ValueError("calendar contains a non-canonical date") from exc
        if WINDOW_START <= value <= WINDOW_END:
            days.add(value)
    grid = []
    for month in GRID_MONTHS:
        in_month = [value for value in days if value[:7] == month]
        if in_month:
            grid.append(max(in_month))
    if WINDOW_END in days:
        grid.append(WINDOW_END)
    if len(grid) != GRID_SIZE or grid[-1] != WINDOW_END:
        raise ValueError(f"derived date grid has {len(grid)} dates; exactly 12 ending at {WINDOW_END} are required")
    return validate_grid(grid)


def metadata_for(value: str) -> dict:
    cutoff = validate_cutoff(value)
    return {**METADATA, "cutoff_at": cutoff_at_for(cutoff), "cutoff_date": cutoff,
            "knowledge_basis": KNOWLEDGE_BASIS, "findings_scope": FINDINGS_SCOPE, "date_rule": DATE_RULE}


def d1_state(d1: dict) -> str:
    if d1.get("arithmetic_status") != "AVAILABLE":
        return "UNAVAILABLE"
    if d1.get("freshness") == "STALE":
        return "STALE"
    if d1.get("freshness") != "FRESH":
        raise ValueError("available D1 finding has no known freshness")
    if d1.get("research_screen") == "CROSSING":
        return "ELIGIBLE_CROSSING"
    if d1.get("research_screen") == "NO_CROSSING":
        return "ELIGIBLE_NO_CROSSING"
    raise ValueError("available D1 finding has no research screen")


def parse_instant(value: object) -> datetime:
    """Offset-aware ISO instant; offset-free or unparseable values refuse."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("timestamp is missing")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("timestamp is not ISO 8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp has no UTC offset")
    return parsed


def is_hex64(value: object) -> bool:
    return isinstance(value, str) and _HEX64.fullmatch(value) is not None


def denylist_hits(text: str) -> list[str]:
    """Denylisted terms in text after removing the exempt exact sentences."""
    remaining = text
    for sentence in EXACT_SENTENCES_TR:
        remaining = remaining.replace(sentence, " ")
    folded = turkish_lower(remaining)
    return [term for term in DENYLIST_TR if turkish_lower(term) in folded]


def turkish_lower(text: str) -> str:
    """Lower case with Turkish dotted/dotless I, so capitalised terms are still caught."""
    return text.replace("I", "ı").replace("İ", "i").lower()


def date_or_month_mentions(text: str) -> list[str]:
    """Fixed dates or Turkish month names in a template (exact sentences excluded)."""
    remaining = text
    for sentence in EXACT_SENTENCES_TR:
        remaining = remaining.replace(sentence, " ")
    found = _DATE_PATTERN.findall(remaining)
    found.extend(name for name in MONTH_NAMES_TR if re.search(rf"(?<!\w){name}", remaining))
    return found
