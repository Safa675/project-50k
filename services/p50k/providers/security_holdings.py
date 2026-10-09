"""Read source rows from one explicitly supported KAP month-end table.

The reader preserves every signed position and its source coordinates. It does
not calculate concentration, merge issuers, interpret negative quantities or
turn a repo's collateral security into an owned security. PDF decoding and
report/publication identity admission belong to the caller.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Context, Decimal, localcontext
from math import isfinite
from typing import Sequence

from .kap_report import normalize, parse_number
from .thf_holdings import HoldingsReadError, PositionedWord, PrintedNumber

SECURITY_TYPES = frozenset({"EQUITY", "BOND", "FUND", "OTHER_SECURITY"})
PROFILE = "KAP_950_1200_III_IV_V1"
_ISIN = re.compile(r"[A-Z]{2}[A-Z0-9]{9}\d")
_TURKISH_NUMBER = re.compile(r"[-+]?(?:\d{1,3}(?:\.\d{3})+|\d+),\d{1,16}")
_MAX_WORDS = 250_000


@dataclass(frozen=True)
class SecurityHoldingRow:
    isin: str | None
    native_name: str
    instrument_type: str
    instrument_label: str
    currency_label: str | None
    position_value: PrintedNumber
    source_page: int
    source_row: int
    source_bbox: tuple[float, float, float, float]

    @property
    def is_identified_security(self) -> bool:
        return self.isin is not None and self.instrument_type in SECURITY_TYPES


@dataclass(frozen=True)
class SecurityHoldingsSnapshot:
    report_period: str
    published_at: datetime
    source_path: str
    source_sha256: str
    rows: tuple[SecurityHoldingRow, ...]
    portfolio_total: PrintedNumber | None
    fund_net_assets: PrintedNumber | None
    problems: tuple[str, ...]
    qualifications: tuple[str, ...]
    supported_profile: bool
    profile: str | None

    @property
    def excluded_rows(self) -> tuple[SecurityHoldingRow, ...]:
        return tuple(row for row in self.rows if row.instrument_type not in SECURITY_TYPES)

    @property
    def unidentified_rows(self) -> tuple[SecurityHoldingRow, ...]:
        return tuple(row for row in self.rows if row.isin is None)

    @property
    def reconciled(self) -> bool:
        return self.supported_profile and not self.problems


@dataclass(frozen=True)
class _Line:
    page: int
    y: float
    words: tuple[PositionedWord, ...]

    @property
    def position(self) -> tuple[int, float]:
        return self.page, self.y

    def label(self, right: float = 310.0) -> str:
        return " ".join(word.text for word in self.words if word.x0 < right
                        and not re.fullmatch(r"[-+]?\d[\d.,]*", word.text))


def _lines(words: Sequence[PositionedWord]) -> list[_Line]:
    result: list[_Line] = []
    bucket: list[PositionedWord] = []
    for word in sorted(words, key=lambda value: (value.page, value.y0, value.x0)):
        if bucket and (word.page != bucket[0].page or abs(word.y0 - bucket[0].y0) >= 1.0):
            result.append(_Line(bucket[0].page, bucket[0].y0,
                                tuple(sorted(bucket, key=lambda value: value.x0))))
            bucket = []
        bucket.append(word)
    if bucket:
        result.append(_Line(bucket[0].page, bucket[0].y0,
                            tuple(sorted(bucket, key=lambda value: value.x0))))
    return result


def _printed(word: PositionedWord) -> PrintedNumber:
    if len(word.text) > 128 or _TURKISH_NUMBER.fullmatch(word.text) is None:
        raise HoldingsReadError("unsupported or ambiguous Turkish numeric cell")
    try:
        number = parse_number(word.text)
    except ValueError as exc:
        raise HoldingsReadError("invalid numeric cell") from exc
    return PrintedNumber(number, word.text, word.page, word.bbox)


def _one_number(line: _Line, edge: float) -> PrintedNumber:
    candidates = [word for word in line.words if abs(word.x1 - edge) < 0.2
                  and word.x0 > edge - 170]
    if len(candidates) != 1:
        raise HoldingsReadError("missing or ambiguous aligned numeric cell")
    return _printed(candidates[0])


def _type(label: str) -> str | None:
    value = normalize(label)
    if "NAKIT TEMINAT" in value or value in {"TEMINAT", "VOB TEMINATI"}:
        return "COLLATERAL"
    if "REPO" in value:
        return "REPO"
    if "MEVDUAT" in value or "KATILIM HESABI" in value:
        return "DEPOSIT"
    if "PARA PIYASASI" in value or value in {"TPP", "BPP", "TPP-TPP BORCLANMA", "BPP-BPP BORCLANMA"}:
        return "MONEY_MARKET"
    if any(marker in value for marker in ("VADELI ISLEM", "VADELI KONTRAT", "OPSİYON", "OPSIYON", "VOB SOZLESM", "VIOP", "FUTURE")):
        return "DERIVATIVE"
    if "HISSE" in value and "SENET" in value or value.startswith("HISSE TURK") or value.startswith("HISSE YABANCI"):
        return "EQUITY"
    if any(marker in value for marker in ("BORCLANMA SENET", "TAHVIL", "FINANSMAN BONO", "HAZINE BONO", "EUROBOND", "KIRA SERTIFIKA", "VARLIGA DAYALI", "VARLIK TEMINATLI")):
        return "BOND"
    if "YATIRIM FON" in value or value in {"FON", "FON KATILMA PAYLARI", "KATILMA PAYLARI"}:
        return "FUND"
    if value in {"KIYMETLI MADENLER", "ALTIN", "GUMUS"}:
        return "OTHER_SECURITY"
    return None


def _rounding_bound(numbers: Sequence[PrintedNumber]) -> Decimal:
    return sum((Decimal(5).scaleb(number.value.as_tuple().exponent - 1)
                for number in numbers), Decimal(0))


def read_security_holdings(
    words: Sequence[PositionedWord], *, page_sizes: Sequence[tuple[float, float]],
    report_period: str, published_at: datetime, source_path: str, source_sha256: str,
) -> SecurityHoldingsSnapshot:
    """Return printed III-section rows and reconciliation failures, never metrics.

    Only the observed 950 by 1200 point profile is supported. Unsupported layouts
    stay explicit; there is no text-only fallback, OCR or inferred column shift.
    Signed values, duplicate ISIN lots and nonsecurity rows are retained. Totals
    are checked using their printed half-unit rounding bounds, not a tuned error
    tolerance. Later sales tables are excluded by the first section-IV boundary.
    """
    if not re.fullmatch(r"\d{4}-(?:0[1-9]|1[0-2])", report_period):
        raise HoldingsReadError("invalid report period")
    if not isinstance(published_at, datetime) or published_at.tzinfo is None or published_at.utcoffset() is None:
        raise HoldingsReadError("publication time must be timezone-aware")
    if not source_path or not re.fullmatch(r"[0-9a-f]{64}", source_sha256):
        raise HoldingsReadError("source path and SHA-256 are required")
    problems: list[str] = []
    qualifications: list[str] = ["monthly_reported_positions_not_current_holdings", "issuer_equivalence_not_inferred", "fund_of_fund_lookthrough_unavailable"]
    rows: list[SecurityHoldingRow] = []
    portfolio_total = fund_net_assets = None
    supported = bool(page_sizes) and all(size == (950.0, 1200.0) for size in page_sizes)

    def result() -> SecurityHoldingsSnapshot:
        return SecurityHoldingsSnapshot(report_period, published_at, source_path,
                                        source_sha256, tuple(rows), portfolio_total,
                                        fund_net_assets, tuple(sorted(set(problems))),
                                        tuple(sorted(set(qualifications))), supported,
                                        PROFILE if supported else None)

    if not supported:
        problems.append("unsupported_page_geometry")
        return result()
    if len(words) > _MAX_WORDS:
        problems.append("word_limit_exceeded")
        return result()
    if any(isinstance(word.page, bool) or not isinstance(word.page, int)
           or word.page < 1 or word.page > len(page_sizes)
           or not isinstance(word.text, str) or len(word.text) > 4096
           or not all(isinstance(value, (int, float)) and not isinstance(value, bool)
                      and isfinite(value) for value in word.bbox)
           or not (0 <= word.x0 < word.x1 <= 950 and 0 <= word.y0 < word.y1 <= 1200)
           for word in words):
        problems.append("invalid_source_word")
        return result()
    lines = _lines([word for word in words if word.text.strip()])
    starts = [line for line in lines if normalize(line.label()).startswith("III-FON PORTFOY DEGERI TABLOSU")]
    if len(starts) != 1:
        problems.append("missing_or_ambiguous_section_iii")
        return result()
    start = starts[0]
    iv = [line for line in lines if line.position > start.position
          and normalize(line.label()).startswith("IV-FON TOPLAM DEGERI TABLOSU")]
    if not iv:
        problems.append("section_iv_boundary_missing")
        return result()
    end = iv[0]
    table = [line for line in lines if start.position < line.position < end.position]
    footers = [line for line in table if normalize(line.label()) == "FON PORTFOY DEGERI"]
    if len(footers) != 1:
        problems.append("missing_or_ambiguous_portfolio_footer")
        return result()
    footer = footers[0]
    if any(line.position > footer.position and any(abs(word.x1 - 817) < 0.2
           for word in line.words) for line in table):
        problems.append("numeric_rows_after_portfolio_footer")
    table = [line for line in table if line.position < footer.position]
    header_words = [word for line in table for word in line.words]
    if not (any(normalize(word.text) == "ISIN" and 220 < word.x0 < 250 for word in header_words)
            and any(normalize(word.text) == "DEGER" and 785 < word.x0 < 800 for word in header_words)):
        problems.append("unsupported_value_or_identity_columns")
        return result()
    try:
        portfolio_total = _one_number(footer, 817)
    except HoldingsReadError:
        problems.append("portfolio_footer_value_unreadable")
    anchors = [line for line in table if any(abs(word.x1 - 817) < 0.2 for word in line.words)]
    instrument_type, instrument_label = "UNKNOWN", ""
    subtotal: list[PrintedNumber] = []
    class_total: list[PrintedNumber] = []
    group_count = 0
    with localcontext(Context(prec=300)):
        for line_index, line in enumerate(table):
            label = line.label(90)
            normalized = normalize(label)
            numeric = any(abs(word.x1 - 817) < 0.2 for word in line.words)
            if not numeric:
                heading_words = [word for word in line.words if word.x0 < 90]
                # In this profile subsection headings use a larger font than
                # wrapped position names. Body text cannot change asset type.
                kind = _type(label) if heading_words and max(word.y1 - word.y0 for word in heading_words) >= 8.5 else None
                if kind:
                    instrument_type, instrument_label = kind, label
                elif heading_words and line.y >= 75 and max(word.y1 - word.y0 for word in heading_words) >= 9.5:
                    # An unsupported asset section must not inherit the last
                    # recognized section's type. Repeated page mastheads sit
                    # above the table and do not reset a continued section.
                    instrument_type, instrument_label = "UNKNOWN", label
                continue
            try:
                number = _one_number(line, 817)
            except HoldingsReadError:
                problems.append("position_or_group_value_unreadable")
                continue
            if normalized == "GRUP TOPLAMI":
                group_count += 1
                markers = [word for word in line.words if normalize(word.text) == "GRUP" and word.x0 < 35]
                if len(markers) != 1:
                    problems.append("group_total_level_ambiguous")
                    continue
                major = markers[0].y1 - markers[0].y0 >= 8.5
                values = class_total if major else subtotal
                if abs(sum((value.value for value in values), Decimal(0)) - number.value) > _rounding_bound([*values, number]):
                    problems.append("class_total_reconciliation_failed" if major else "subgroup_total_reconciliation_failed")
                if major:
                    class_total = []
                subtotal = []
                continue
            next_anchors = [anchor for anchor in anchors if anchor.position > line.position]
            next_position = next_anchors[0].position if next_anchors else footer.position
            band = [word for item in table if line.position <= item.position < next_position
                    for word in item.words]
            # Only the designated ISIN column binds identity. Repo collateral
            # ISINs remain on excluded repo rows; left-hand identifiers do not
            # bypass the security-type guard.
            identities = [word for word in band if 200 < word.x0 < 280 and _ISIN.fullmatch(word.text)]
            isin = identities[0].text if len(identities) == 1 else None
            if len(identities) > 1:
                problems.append("row_identity_ambiguous")
            names = [word for word in band if word.x0 < 90 and normalize(word.text) not in {"MENKUL", "KIYMET"}]
            native_name = " ".join(word.text for word in sorted(names, key=lambda word: (word.y0, word.x0)))
            if not native_name:
                problems.append("row_name_missing")
            currency_words = [word for word in line.words if 90 < word.x0 < 112]
            currency = currency_words[0].text if len(currency_words) == 1 else None
            kind = "DERIVATIVE" if native_name.startswith(("F_", "O_")) else instrument_type
            bbox_words = [word for word in line.words if word.x0 < 90] + [word for word in line.words if abs(word.x1 - 817) < 0.2]
            row = SecurityHoldingRow(isin, native_name, kind, instrument_label, currency, number,
                                     line.page, len(rows) + 1,
                                     (min(word.x0 for word in bbox_words), min(word.y0 for word in bbox_words),
                                      max(word.x1 for word in bbox_words), max(word.y1 for word in bbox_words)))
            rows.append(row)
            subtotal.append(number)
            class_total.append(number)
        if not group_count:
            problems.append("instrument_group_totals_missing")
        if subtotal or class_total:
            problems.append("unterminated_instrument_group")
        if portfolio_total:
            if portfolio_total.value <= 0:
                problems.append("portfolio_total_nonpositive")
            # The supported form prints derivative notional in this column,
            # alongside owned-asset valuations. It is not a portfolio asset.
            # Apply this rule to every report; never try per-fund exclusions
            # until some sum happens to match the printed footer.
            all_values = [row.position_value for row in rows
                          if row.instrument_type != "DERIVATIVE"]
            if abs(sum((number.value for number in all_values), Decimal(0)) - portfolio_total.value) > _rounding_bound([*all_values, portfolio_total]):
                problems.append("portfolio_rows_reconciliation_failed")
        next_sections = [line for line in lines if line.position > end.position
                         and normalize(line.label()).startswith("V-AY")]
        section_v = next_sections[0].position if next_sections else None
        if section_v is None:
            problems.append("section_v_boundary_missing")
        following = [line for line in lines if line.position >= end.position
                     and (section_v is None or line.position < section_v)]
        iv_portfolio = [line for line in following if normalize(line.label()).startswith("A-)FON PORTFOY DEGERI")]
        if len(iv_portfolio) != 1:
            problems.append("section_iv_portfolio_total_ambiguous")
        else:
            try:
                iv_total = _one_number(iv_portfolio[0], 329)
                if portfolio_total and abs(iv_total.value - portfolio_total.value) > _rounding_bound([iv_total, portfolio_total]):
                    problems.append("section_iv_portfolio_reconciliation_failed")
            except HoldingsReadError:
                problems.append("section_iv_portfolio_total_unreadable")
        nav_lines = [line for line in following if normalize(line.label()).startswith("FON TOPLAM DEGERI")]
        if len(nav_lines) == 1:
            try:
                fund_net_assets = _one_number(nav_lines[0], 331)
            except HoldingsReadError:
                qualifications.append("fund_net_assets_unreadable")
        else:
            qualifications.append("fund_net_assets_unavailable")
    if any(row.position_value.value < 0 for row in rows):
        qualifications.append("signed_negative_positions_interpretation_unknown")
    if any(row.instrument_type == "DERIVATIVE" for row in rows):
        qualifications.append("derivatives_excluded_notional_not_owned_security_value")
    if any(not row.is_identified_security and row.position_value.value != 0 for row in rows):
        qualifications.append("positive_identified_security_subset_is_partial")
    if any(row.instrument_type == "FUND" for row in rows):
        qualifications.append("reported_fund_units_not_underlying_holdings")
    return result()
