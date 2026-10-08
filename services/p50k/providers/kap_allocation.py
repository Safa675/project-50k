"""Read a bounded monthly-average allocation table from positioned PDF text.

This module does not read PDFs or infer economic equivalence between labels.
The caller supplies text cells and separately verifies fund/period identity and
publication provenance. Missing rows never become zero; invalid tables retain
their readable source rows but cannot supply detector weights.
"""
from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from decimal import Context, Decimal, DecimalException, DivisionByZero, Inexact, InvalidOperation, Overflow, Rounded, localcontext
from typing import Sequence

from .kap_report import normalize, parse_number

MONTHLY_AVERAGE = "MONTHLY_AVERAGE"
_MAX_CELLS = 100_000
_MAX_TEXT_LENGTH = 4096
_MAX_CATEGORIES = 1000
_MAX_FRACTION_PLACES = 4096
_HEADER = re.compile(
    r"AYLIK\s+ORTALAMA\s+PORTFOYDEKI\s*:?\s*"
    r"MENKUL\s+KIYMETLER\s+YUZDESI"
)
_LIST_MARKER = re.compile(r"^[A-Z](?:\d+)?\s*[-.)]+\s*")
_NEXT_SECTION = re.compile(
    r"^(?:[A-Z](?:\d+)?\s*[-.)]+\s*)?"
    r"(?:AYLIK ORTALAMA (?:PORTFOY )?(?:DEVIR HIZI|TEDAVUL ORANI)"
    r"|PORTFOYUN ORTALAMA VADESI|PORTFOY ORTALAMA VADESI"
    r"|KATILMA PAYI (?:IHRAC|IADE)|III\s*[-.)]?\s*FON PORTFOY DEGERI TABLOSU"
    r"|3\s*[-.)]?\s*FON PORTFOY DEGERI TABLOSU)"
)
_NUMBER_AT_END = re.compile(r"(?P<number>[-+]?\d[\d.,]*\s*%?)\s*$")
_WHOLE_NUMBER = re.compile(r"[-+]?\s*\d[\d.,]*\s*%?")


@dataclass(frozen=True)
class TextCell:
    page: int
    x0: float
    y0: float
    x1: float
    y1: float
    text: str


@dataclass(frozen=True)
class AllocationRow:
    category: str
    label: str
    weight_percent: Decimal
    page: int
    rect: tuple[float, float, float, float]


@dataclass(frozen=True)
class AllocationTable:
    weights: dict[str, Decimal] | None
    category_schema: str | None
    basis: str | None
    problems: tuple[str, ...]
    source_rows: tuple[AllocationRow, ...]


@dataclass(frozen=True)
class _Line:
    page: int
    cells: tuple[TextCell, ...]

    @property
    def text(self) -> str:
        return " ".join(cell.text.strip() for cell in self.cells)

    @property
    def x0(self) -> float:
        return min(cell.x0 for cell in self.cells)

    @property
    def y0(self) -> float:
        return min(cell.y0 for cell in self.cells)


def _lines(cells: Sequence[TextCell]) -> list[_Line]:
    """Cluster neighboring baselines relative to glyph height, then sort by x.

    Fixed pixel tolerances would merge the tightly spaced small-print profile.
    A tolerance based on the smallest glyph also accommodates label/value
    baselines differing slightly within one row.
    """
    result: list[_Line] = []
    current: list[TextCell] = []
    smallest_height = math.inf
    for cell in sorted(cells, key=lambda value: (value.page, value.y0, value.x0)):
        if current:
            tolerance = 0.45 * min(smallest_height, cell.y1 - cell.y0)
            same_line = (
                cell.page == current[0].page
                and abs(cell.y0 - current[0].y0) <= tolerance
            )
            if not same_line:
                result.append(_Line(current[0].page, tuple(sorted(current, key=lambda item: item.x0))))
                current = []
                smallest_height = math.inf
        current.append(cell)
        smallest_height = min(smallest_height, cell.y1 - cell.y0)
    if current:
        result.append(_Line(current[0].page, tuple(sorted(current, key=lambda item: item.x0))))
    return result


def _read_row(line: _Line) -> AllocationRow:
    text = line.text.strip()
    if text.count(":") > 1:
        raise ValueError("multiple label/value separators")
    if ":" in text:
        label, number = (piece.strip() for piece in text.split(":", 1))
        if not label:
            raise ValueError("value without a category")
    else:
        match = _NUMBER_AT_END.search(text)
        if match is None:
            raise ValueError("missing or invalid weight")
        label, number = text[:match.start()].strip(), match.group("number")
        if not label:
            raise ValueError("value without a category")
    category = _LIST_MARKER.sub("", normalize(label)).strip()
    if not category or not re.search(r"[A-Z]", category):
        raise ValueError("missing category label")
    if re.search(r"\d|[%:]", category):
        raise ValueError("multiple values or unsupported category label")
    if category in ("TOPLAM", "TOTAL"):
        raise ValueError("a total is not an allocation category")
    if _WHOLE_NUMBER.fullmatch(number.strip()) is None:
        raise ValueError("invalid weight: expected exactly one numeric cell")
    try:
        weight = parse_number(number)
    except ValueError as exc:
        raise ValueError(f"invalid weight: {exc}") from exc
    if not weight.is_finite() or weight < 0 or weight > 100:
        raise ValueError("weight is not a nonnegative percentage at most 100")
    if max(0, -weight.as_tuple().exponent) > _MAX_FRACTION_PLACES:
        raise ValueError("weight exceeds supported fractional precision")
    return AllocationRow(
        category=category,
        label=label,
        weight_percent=weight,
        page=line.page,
        rect=(
            min(cell.x0 for cell in line.cells), min(cell.y0 for cell in line.cells),
            max(cell.x1 for cell in line.cells), max(cell.y1 for cell in line.cells),
        ),
    )


def _heading_text(line: _Line) -> str:
    parts = []
    for item in line.cells:
        if item.text.strip() == ":" or _WHOLE_NUMBER.fullmatch(item.text.strip()):
            continue
        # Wrapped heading values and colons can precede the last label line.
        parts.append(re.sub(r"\s*:\s*[-+]?\d[\d.,]*\s*%?\s*$", "", item.text))
    return normalize(" ".join(parts))


def read_allocation(cells: Sequence[TextCell]) -> AllocationTable:
    """Return native-category weights only for one complete valid table.

    Supported sections fit on one page and end at a recognizable same-column
    heading. Orthographic normalization removes only list markers, whitespace,
    case and Turkish diacritics. There are no category aliases or zero filling.
    Printed percentages must sum to exactly 100; there is no renormalization.
    """
    problems: list[str] = []
    clean: list[TextCell] = []
    if len(cells) > _MAX_CELLS:
        return AllocationTable(None, None, None, ("text cell limit exceeded",), ())
    for cell in cells:
        coordinates = (cell.x0, cell.y0, cell.x1, cell.y1)
        if (
            isinstance(cell.page, bool) or not isinstance(cell.page, int) or cell.page < 1
            or not all(isinstance(value, (int, float)) and not isinstance(value, bool)
                       and math.isfinite(value) for value in coordinates)
            or cell.x1 <= cell.x0 or cell.y1 <= cell.y0
            or not isinstance(cell.text, str)
            or len(cell.text) > _MAX_TEXT_LENGTH
        ):
            return AllocationTable(None, None, None, ("invalid text cell",), ())
        if cell.text.strip():
            clean.append(cell)
    lines = _lines(clean)
    headers: list[tuple[int, int]] = []
    for start, line in enumerate(lines):
        folded = normalize(line.text)
        if "AYLIK" not in folded or "ORTALAMA" not in folded:
            continue
        pieces: list[str] = []
        for end in range(start, min(start + 5, len(lines))):
            if lines[end].page != line.page:
                break
            pieces.append(_heading_text(lines[end]))
            match = _HEADER.search(" ".join(pieces))
            if match:
                headers.append((start, end))
                break
    if not headers:
        return AllocationTable(None, None, None, ("monthly-average allocation section not found",), ())
    if len(headers) != 1:
        return AllocationTable(None, None, None, ("ambiguous allocation sections",), ())
    start, header_end = headers[0]
    anchor = lines[start].x0
    page = lines[start].page
    alignment = max(8.0, max(cell.y1 - cell.y0 for cell in lines[start].cells))
    end: int | None = None
    for index in range(header_end + 1, len(lines)):
        line = lines[index]
        if line.page != page:
            break
        if abs(line.x0 - anchor) <= alignment:
            pieces = []
            for continuation in lines[index:min(index + 5, len(lines))]:
                if continuation.page != page:
                    break
                label_text = _heading_text(continuation)
                if not label_text:
                    continue
                if abs(continuation.x0 - anchor) > alignment:
                    break
                pieces.append(label_text)
                if _NEXT_SECTION.match(" ".join(pieces)):
                    end = index
                    break
            if end is not None:
                break
    if end is None:
        return AllocationTable(
            None, None, MONTHLY_AVERAGE,
            ("allocation section has no same-page, same-column boundary",), (),
        )

    # A recognized parallel section starts a separate column. Its heading must
    # not end this table, and its rows must not be mistaken for allocation rows.
    right = math.inf
    for line in lines[start:end]:
        for offset, cell in enumerate(line.cells):
            if cell.x0 <= anchor + max(80.0, alignment * 4):
                continue
            following = normalize(" ".join(item.text for item in line.cells[offset:]))
            if _NEXT_SECTION.match(following):
                right = min(right, cell.x0)
    source_rows: list[AllocationRow] = []
    percentages: dict[str, Decimal] = {}
    for line in lines[header_end + 1:end]:
        if any(cell.x0 < anchor - alignment for cell in line.cells):
            problems.append(f"allocation row at page {page}, y={line.y0:g}: unsupported left-column data")
        selected = tuple(cell for cell in line.cells if anchor - alignment <= cell.x0 < right)
        if not selected:
            continue
        bounded = _Line(page, selected)
        try:
            row = _read_row(bounded)
        except ValueError as exc:
            problems.append(f"allocation row at page {page}, y={line.y0:g}: {exc}")
            continue
        source_rows.append(row)
        if row.category in percentages:
            problems.append(f"duplicate allocation category: {row.category}")
        else:
            percentages[row.category] = row.weight_percent
    if not source_rows:
        problems.append("allocation section contains no valid rows")
    if len(percentages) > _MAX_CATEGORIES:
        problems.append("allocation category limit exceeded")
        return AllocationTable(None, None, MONTHLY_AVERAGE, tuple(problems), tuple(source_rows))
    fractional_places = max(
        (max(0, -value.as_tuple().exponent) for value in percentages.values()), default=0
    )
    context = Context(
        prec=max(28, fractional_places + 3 + len(str(len(percentages))) + 2),
        Emin=-999999, Emax=999999,
        traps=[InvalidOperation, DivisionByZero, Overflow, Inexact, Rounded],
    )
    try:
        with localcontext(context):
            total = sum(percentages.values(), Decimal(0))
            if total != Decimal(100):
                problems.append(f"allocation percentages do not sum to 100: {total}")
            weights = {category: value / Decimal(100) for category, value in percentages.items()}
    except DecimalException:
        problems.append("allocation arithmetic could not be performed exactly")
        return AllocationTable(None, None, MONTHLY_AVERAGE, tuple(problems), tuple(source_rows))
    if problems:
        return AllocationTable(None, None, MONTHLY_AVERAGE, tuple(problems), tuple(source_rows))
    schema = hashlib.sha256("\n".join(sorted(weights)).encode("utf-8")).hexdigest()
    return AllocationTable(weights, schema, MONTHLY_AVERAGE, (), tuple(source_rows))
