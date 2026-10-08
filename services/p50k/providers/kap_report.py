"""Read the headline fields of a KAP monthly portfolio report from its text lines.

Management companies lay the same SPK form out differently: list letters, label
wording, wrapped labels, values on the next line, and number formats
(1.234,56 or 1,234.56). Fields are therefore found by keywords, not by list
letter, in the report's first section. Anything that cannot be read exactly is
left as None and named in `problems`; nothing is guessed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence

_TURKISH = str.maketrans("İıŞşĞğÜüÖöÇç", "IISSGGUUOOCC")
_NUMBER = re.compile(r"[-+]?\d[\d.,]*%?")
_PLAIN_NUMBER = re.compile(r"[-+]?\d[\d.,]*%?\s*")
_SECTION_END = re.compile(r"PORTFOY DEGERI TABLOSU")
_MAX_HEADER_LINES = 150

# Label patterns apply to the label part of the line (before the colon), upper-cased and
# ASCII-folded. Reports are monthly ("AY SONU"), weekly ("HAFTALIK") or period-end
# ("DONEM SONU"), and some layouts wrap a label so that "ARTIS ORANI" sits on the next line.
FIELDS = {
    "total_value": re.compile(r"TOPLAM DEGER"),
    "units_outstanding": re.compile(
        r"KATILMA PAYI SAYISI|TEDAVULDEKI (?:KATILMA )?PAY SAYISI|DOLASIMDAKI PAY SAYISI"),
    "period_end_price": re.compile(
        r"(?:AY|DONEM|HAFTA) SONU (?:KATILMA|PAY)|HAFTALIK (?:KATILMA )?PAY(?:I)? FIYATI(?!.*ARTIS)"),
    "previous_period_price": re.compile(r"ONCEKI (?:AY|DONEM|HAFTA)\b"),
    "period_change_pct": re.compile(
        r"(?:AYLIK|HAFTALIK|DONEMSEL) (?:KATILMA|PAY)(?=.*ARTIS)|(?:AYLIK|DONEMSEL) KATILMA(?: PAYI)?$"),
    "cash_in": re.compile(r"NAKIT GIRIS"),
    "cash_out": re.compile(r"NAKIT CIKIS"),
}


@dataclass(frozen=True)
class Headline:
    total_value: Decimal | None
    units_outstanding: Decimal | None
    period_end_price: Decimal | None
    previous_period_price: Decimal | None
    period_change_pct: Decimal | None
    cash_in: Decimal | None
    cash_out: Decimal | None
    problems: tuple[str, ...]


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.translate(_TURKISH).upper()).strip()


def parse_number(text: str) -> Decimal:
    """Parse 1.234,56 or 1,234.56. A lone separator followed by three digits is ambiguous and rejected."""
    s = text.strip().replace(" ", "").rstrip("%")
    sign = ""
    if s[:1] in ("+", "-"):
        sign, s = s[0], s[1:]
    if not re.fullmatch(r"\d[\d.,]*", s):
        raise ValueError(f"not a number: {text!r}")
    commas, dots = s.count(","), s.count(".")
    if commas and dots:
        decimal, grouping = ("," if s.rfind(",") > s.rfind(".") else "."), None
        grouping = "." if decimal == "," else ","
        head, _, tail = s.rpartition(decimal)
        groups = head.split(grouping)
        if decimal in head or not tail or not _groups_of_three(groups):
            raise ValueError(f"inconsistent separators: {text!r}")
        return Decimal(f"{sign}{''.join(groups)}.{tail}")
    if not commas and not dots:
        return Decimal(sign + s)
    separator = "," if commas else "."
    groups = s.split(separator)
    if len(groups) > 2:  # repeated separator: only thousands groups
        if not _groups_of_three(groups):
            raise ValueError(f"inconsistent separators: {text!r}")
        return Decimal(sign + "".join(groups))
    head, tail = groups
    if len(tail) == 3 and head not in ("0", ""):
        raise ValueError(f"ambiguous number: {text!r}")
    return Decimal(f"{sign}{head}.{tail}")


def _groups_of_three(groups: list[str]) -> bool:
    return 1 <= len(groups[0]) <= 3 and all(len(g) == 3 for g in groups[1:])


def _value(lines: Sequence[str], at: int) -> Decimal:
    """The number after the label's colon, or a number alone on the next line."""
    _, colon, after = lines[at].partition(":")
    found = _NUMBER.search(after) if colon else None
    if found:
        return parse_number(found.group())
    following = lines[at + 1].strip() if at + 1 < len(lines) else ""
    if _PLAIN_NUMBER.fullmatch(following):
        return parse_number(following)
    raise LookupError("no value after the label")


def read_headline(lines: Sequence[str]) -> Headline:
    header = []
    for line in lines[:_MAX_HEADER_LINES]:
        if _SECTION_END.search(normalize(line)):
            break
        header.append(line)
    folded = [normalize(line) for line in header]
    values: dict[str, Decimal | None] = {}
    problems: list[str] = []
    for name, label in FIELDS.items():
        values[name] = None
        reason = "not found"
        for at, text in enumerate(folded):
            if not label.search(text.partition(":")[0].strip()):
                continue
            try:
                values[name] = _value(header, at)
                break
            except LookupError:
                continue
            except ValueError as exc:
                reason = str(exc)
        if values[name] is None:
            problems.append(f"{name}: {reason}")
    return Headline(problems=tuple(problems), **values)
