"""Read signed spot holdings in the observed THF monthly-report geometry.

This is a deliberately narrow reader, not a generic KAP adapter. PDF libraries
stay in the research runner; this module consumes positioned words and Decimal
values only. Negative rows and duplicate ISINs are preserved as printed. Their
economic meaning is unknown, and this reader never calls them short positions.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from decimal import (
    Context, Decimal, DivisionByZero, InvalidOperation, Overflow,
    ROUND_HALF_EVEN, localcontext,
)
from math import isfinite
from typing import Sequence

from p50k.providers.kap_report import parse_number


class HoldingsReadError(ValueError):
    """The observed geometry or a required source field is ambiguous."""


@dataclass(frozen=True)
class PositionedWord:
    page: int  # One-based, as in the PDF.
    x0: float
    y0: float
    x1: float
    y1: float
    text: str

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        return self.x0, self.y0, self.x1, self.y1


@dataclass(frozen=True)
class PrintedNumber:
    value: Decimal
    raw: str
    source_page: int
    source_bbox: tuple[float, float, float, float]


@dataclass(frozen=True)
class HoldingRow:
    symbol: str
    isin: str
    currency_label: str
    nominal_quantity: PrintedNumber
    valuation_price: PrintedNumber
    position_value: PrintedNumber
    group_pct: PrintedNumber
    portfolio_pct: PrintedNumber  # FPD, not fund net assets.
    fund_pct: PrintedNumber  # FTD, not portfolio value.
    source_page: int
    source_row: int
    source_symbol_bbox: tuple[float, float, float, float]
    source_isin_page: int
    source_isin_bbox: tuple[float, float, float, float]
    negative_quantity_interpretation: str = "UNKNOWN"


@dataclass(frozen=True)
class HoldingsSnapshot:
    report_period: str
    published_at: datetime
    source_path: str
    source_sha256: str
    rows: tuple[HoldingRow, ...]
    equity_group_total: PrintedNumber
    equity_group_nominal_total: PrintedNumber
    equity_group_portfolio_pct: PrintedNumber
    equity_group_fund_pct: PrintedNumber
    headline_total_value: PrintedNumber
    section_iv_total_value: PrintedNumber
    portfolio_total_value: PrintedNumber
    problems: tuple[str, ...]
    percentage_warnings: tuple[str, ...]
    futures_present: bool

    @property
    def reconciled(self) -> bool:
        return not self.problems


def _single(items: Sequence[PositionedWord], name: str) -> PositionedWord:
    if len(items) != 1:
        raise HoldingsReadError(f"{name}: expected exactly one source token; got {len(items)}")
    return items[0]


def _numeric(word: PositionedWord, name: str) -> PrintedNumber:
    # Explicit Turkish decimal convention of this observed THF template.
    if not re.fullmatch(r"[-+]?(?:\d{1,3}(?:\.\d{3})+|\d+),\d+", word.text):
        raise HoldingsReadError(f"{name}: invalid Turkish numeric token")
    try:
        value = parse_number(word.text)
    except ValueError as exc:
        raise HoldingsReadError(f"{name}: ambiguous numeric token") from exc
    return PrintedNumber(value, word.text, word.page, word.bbox)


def _column(words: Sequence[PositionedWord], row: PositionedWord,
            left: float, right: float, name: str, tolerance: float = 1.0,
            align_edge: float | None = None) -> PrintedNumber:
    aligned = [w for w in words if w.page == row.page and
               abs(w.y0 - row.y0) < tolerance and left < w.x0 and w.x1 < right and
               (align_edge is None or abs(w.x1 - align_edge) < 0.1)]
    return _numeric(_single(aligned, name), name)


def _position(word: PositionedWord) -> float:
    return (word.page - 1) * 1200.0 + word.y0


def read_thf_holdings(
    words: Sequence[PositionedWord], *, page_sizes: Sequence[tuple[float, float]],
    report_period: str, published_at: datetime, source_path: str, source_sha256: str,
) -> HoldingsSnapshot:
    """Return source fields and arithmetic checks, without return calculations.

    Invalid/ambiguous required fields raise HoldingsReadError. Readable arithmetic
    contradictions are retained in ``problems``; they must gate any later model.
    Printed cents and percentages are checked with their half-unit rounding
    bounds, not with an empirically chosen discrepancy threshold.
    """
    if not re.fullmatch(r"\d{4}-(?:0[1-9]|1[0-2])", report_period):
        raise HoldingsReadError("invalid report period")
    if published_at.tzinfo is None or published_at.utcoffset() is None:
        raise HoldingsReadError("publication time must be timezone-aware")
    if not source_path or not re.fullmatch(r"[0-9a-f]{64}", source_sha256):
        raise HoldingsReadError("source path and SHA-256 are required")
    if not page_sizes or any(size != (950.0, 1200.0) for size in page_sizes):
        raise HoldingsReadError("unsupported THF page geometry")
    if any(w.page < 1 or w.page > len(page_sizes) or
           not all(isfinite(v) for v in w.bbox) or
           not (0 <= w.x0 < w.x1 <= 950 and 0 <= w.y0 < w.y1 <= 1200)
           for w in words):
        raise HoldingsReadError("invalid word coordinates")
    start = _single([w for w in words if w.text == "HİSSE" and w.x0 < 25],
                    "spot section start")
    totals = sorted([w for w in words if w.text == "GRUP" and w.x0 < 35 and
                     _position(w) > _position(start)], key=_position)
    if not totals:
        raise HoldingsReadError("spot section group total not found")
    end = totals[0]
    candidates = sorted([w for w in words if abs(w.x0 - 20.0) < 1 and
                         _position(start) < _position(w) < _position(end) and
                         re.fullmatch(r"[A-Z0-9]{2,6}", w.text)], key=_position)
    isins = [w for w in words if 200 < w.x0 < 280 and
             _position(start) < _position(w) < _position(end) and
             re.fullmatch(r"TR[A-Z0-9]{10}", w.text)]
    if not candidates:
        raise HoldingsReadError("spot section has no readable rows")
    rows: list[HoldingRow] = []
    used_isins: list[PositionedWord] = []
    for ordinal, symbol in enumerate(candidates, 1):
        next_position = _position(candidates[ordinal]) if ordinal < len(candidates) else _position(end)
        isin = _single([w for w in isins if _position(symbol) - 3 < _position(w) < next_position],
                       f"row {ordinal} ISIN")
        used_isins.append(isin)
        currency = _single([w for w in words if w.page == symbol.page and
                           90 < w.x0 < 110 and abs(w.y0 - symbol.y0) < 1],
                          f"row {ordinal} currency")
        if currency.text != "TL":
            raise HoldingsReadError(f"row {ordinal}: unsupported currency")
        fields = {
            "nominal_quantity": _column(words, symbol, 300, 420, "nominal quantity"),
            "valuation_price": _column(words, symbol, 650, 755, "valuation price", align_edge=752),
            "position_value": _column(words, symbol, 650, 820, "position value", align_edge=817),
            "group_pct": _column(words, symbol, 820, 855, "group percentage"),
            "portfolio_pct": _column(words, symbol, 850, 885, "FPD percentage"),
            "fund_pct": _column(words, symbol, 880, 915, "FTD percentage"),
        }
        rows.append(HoldingRow(symbol.text, isin.text, currency.text,
                               source_page=symbol.page, source_row=ordinal,
                               source_symbol_bbox=symbol.bbox,
                               source_isin_page=isin.page, source_isin_bbox=isin.bbox,
                               **fields))
    if sorted(used_isins, key=lambda w: (w.page, w.bbox)) != sorted(isins, key=lambda w: (w.page, w.bbox)):
        raise HoldingsReadError("spot ISIN coverage is not one-to-one")
    # The template prints both subgroup and overall equity total. They must
    # agree; do not add the repeated total to the positions a second time.
    total_lines = [t for t in totals if _position(t) - _position(end) < 25]
    equity_values = []
    for line in total_lines:
        equity_values.append((
            _column(words, line, 300, 420, "group nominal total"),
            _column(words, line, 650, 820, "group position total", align_edge=817),
            _column(words, line, 850, 885, "group FPD percentage"),
            _column(words, line, 880, 915, "group FTD percentage"),
        ))
    if any(tuple(n.value for n in line) != tuple(n.value for n in equity_values[0])
           for line in equity_values[1:]):
        raise HoldingsReadError("contradictory repeated equity group totals")
    group_nominal, group_total, group_fpd, group_ftd = equity_values[0]

    header = _single([w for w in words if w.page == 1 and w.x0 < 25 and
                      w.text == "D-)Toplam"], "headline total label")
    headline_total = _column(words, header, 330, 420, "headline total value", tolerance=7)
    section_iv_markers = sorted([w for w in words if w.x0 < 25 and w.text == "IV-FON"], key=_position)
    if not section_iv_markers:
        raise HoldingsReadError("section IV marker not found")
    section_iv = section_iv_markers[0]  # Repeated heading at a page boundary is allowed.
    section_v = _single([w for w in words if w.x0 < 25 and w.text == "V-AY"],
                        "section V marker")
    section_words = [w for w in words if _position(section_iv) < _position(w) < _position(section_v)]
    portfolio_label = _single([w for w in section_words if w.x0 < 25 and w.text == "A-)FON"],
                             "section IV portfolio label")
    fund_label = _single([w for w in section_words if w.x0 < 25 and w.text == "FON"],
                        "section IV fund total label")
    portfolio_total = _column(words, portfolio_label, 215, 335, "portfolio total value")
    iv_total = _column(words, fund_label, 215, 335, "section IV total value")

    problems: list[str] = []
    percentage_warnings: list[str] = []
    with localcontext(Context(prec=80, rounding=ROUND_HALF_EVEN,
                              Emin=-999999, Emax=999999,
                              traps=[InvalidOperation, DivisionByZero, Overflow])):
        for name, number in (("headline_total_value", headline_total),
                             ("section_iv_total_value", iv_total),
                             ("portfolio_total_value", portfolio_total)):
            if number.value <= 0:
                problems.append(f"{name}: non-positive")
        if headline_total.value != iv_total.value:
            problems.append("headline and section IV fund totals disagree")
        if sum((r.nominal_quantity.value for r in rows), Decimal(0)) != group_nominal.value:
            problems.append("signed nominal sum disagrees with printed equity group total")
        cent_half = Decimal("0.005")
        if abs(sum((r.position_value.value for r in rows), Decimal(0)) - group_total.value) > cent_half * (len(rows) + 1):
            problems.append("signed position value sum disagrees with printed equity group total")
        for row in rows:
            prefix = f"row {row.source_row}"
            if row.valuation_price.value <= 0:
                problems.append(f"{prefix}: non-positive valuation price")
            if abs(row.nominal_quantity.value * row.valuation_price.value - row.position_value.value) > cent_half:
                problems.append(f"{prefix}: quantity times valuation price disagrees with position value")
            for denominator, printed, label in (
                (headline_total.value, row.fund_pct.value, "FTD"),
                (portfolio_total.value, row.portfolio_pct.value, "FPD"),
                (group_total.value, row.group_pct.value, "GROUP"),
            ):
                if denominator > 0 and abs(row.position_value.value / denominator * 100 - printed) > cent_half:
                    percentage_warnings.append(f"{prefix}: printed {label} percentage differs from exact value ratio")
        for denominator, printed, label in (
            (headline_total.value, group_ftd.value, "FTD"),
            (portfolio_total.value, group_fpd.value, "FPD"),
        ):
            if denominator > 0 and abs(group_total.value / denominator * 100 - printed) > cent_half:
                percentage_warnings.append(f"equity group: printed {label} percentage differs from exact value ratio")
    return HoldingsSnapshot(
        report_period, published_at, source_path, source_sha256, tuple(rows),
        group_total, group_nominal, group_fpd, group_ftd, headline_total, iv_total,
        portfolio_total, tuple(problems), tuple(percentage_warnings),
        futures_present=any(re.fullmatch(r"F_[A-Z0-9]+", w.text) and w.x0 < 25 for w in words),
    )
