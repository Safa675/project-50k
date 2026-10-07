"""TEFAS JSON API client: fund snapshot, recent prices and the fund list.

Built from the 2026-10-06 spike (research/spikes/2026-10-06-tefas/REPORT.md):
- certificate verification stays on;
- an empty result list for one fund raises FundNotFound, so a retired or
  unknown code is never read as "nothing changed";
- missing values stay None, never 0 or NaN;
- units outstanding (payAdet) are kept;
- category rank and size inside history rows are dropped, because they repeat
  today's value on every row.
Numbers are parsed as Decimal to keep TEFAS's exact digits. Standard library only.
"""
from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Callable

BASE_URL = "https://www.tefas.gov.tr/api/funds"
# Same browser User-Agent borsapy sends; the spike's requests used it.
USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
PERIOD_WEEK = 13  # TEFAS's smallest history bucket, about five business days
_RETURNS_PAYLOAD = {
    "dil": "TR", "calismaTipi": 2, "donemGetiri1a": "1", "donemGetiri3a": "1", "donemGetiri6a": "1",
    "donemGetiriyb": "1", "donemGetiri1y": "1", "donemGetiri3y": "1", "donemGetiri5y": "1",
}

# (url, json body, headers) -> (HTTP status, content type, body)
Transport = Callable[[str, bytes, dict[str, str]], tuple[int, str, bytes]]


class TefasError(RuntimeError):
    """Base class for TEFAS client errors."""


class TefasUnavailable(TefasError):
    """Transport failure, HTTP error, non-JSON body or an error message from TEFAS. Worth retrying."""


class FundNotFound(TefasError):
    """TEFAS returned an empty list for this fund code. Not worth retrying."""


@dataclass(frozen=True)
class FundSnapshot:
    """TEFAS's latest values for one fund. TEFAS states no as-of date for them."""

    code: str
    name: str | None
    price: Decimal | None
    daily_return_pct: Decimal | None
    units_outstanding: Decimal | None
    total_value: Decimal | None
    investors: int | None
    category: str | None
    category_rank: int | None
    category_size: int | None
    market_share_pct: Decimal | None
    raw: dict[str, Any]


@dataclass(frozen=True)
class PricePoint:
    date: date
    price: Decimal


def urllib_transport(timeout: float = 30.0) -> Transport:
    context = ssl.create_default_context()  # verifies certificates and host names

    def send(url: str, body: bytes, headers: dict[str, str]) -> tuple[int, str, bytes]:
        request = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
                return response.status, response.headers.get("Content-Type", ""), response.read()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.headers.get("Content-Type", "") if exc.headers else "", exc.read()
        except (urllib.error.URLError, OSError) as exc:
            raise TefasUnavailable(f"transport failed: {type(exc).__name__}") from exc

    return send


class TefasClient:
    def __init__(self, transport: Transport | None = None, base_url: str = BASE_URL) -> None:
        self._transport = transport or urllib_transport()
        self._base_url = base_url

    def snapshot(self, code: str) -> FundSnapshot:
        row = self._one(self._post("fonBilgiGetir", {"fonKodu": code.upper()}), code)
        return FundSnapshot(
            code=str(row.get("fonKodu") or code.upper()),
            name=_text(row.get("fonUnvan")),
            price=_decimal(row.get("sonFiyat")),
            daily_return_pct=_decimal(row.get("gunlukGetiri")),
            units_outstanding=_decimal(row.get("payAdet")),
            total_value=_decimal(row.get("portBuyukluk")),
            investors=_integer(row.get("yatirimciSayi")),
            category=_text(row.get("fonKategori")),
            category_rank=_integer(row.get("kategoriDerece")),
            category_size=_integer(row.get("kategoriFonSay")),
            market_share_pct=_decimal(row.get("pazarPayi")),
            raw=row,
        )

    def price_history(self, code: str, periyod: int = PERIOD_WEEK) -> list[PricePoint]:
        """Dated unit prices, oldest first. Rows without a valid date or price are skipped."""
        rows = self._post("fonFiyatBilgiGetir", {"fonKodu": code.upper(), "dil": "TR", "periyod": periyod})
        if not rows:
            raise FundNotFound(code)
        points = {}
        for row in rows:
            price = _decimal(row.get("fiyat"))
            try:
                day = date.fromisoformat(str(row.get("tarih"))[:10])
            except ValueError:
                continue
            if price is not None:
                points[day] = price
        return [PricePoint(day, points[day]) for day in sorted(points)]

    def fund_list(self, fund_type: str = "YAT") -> list[dict[str, Any]]:
        """Every fund of the given type (YAT investment, EMK pension), one row each."""
        return self._post("fonGetiriBazliBilgiGetir", {"fonTipi": fund_type, **_RETURNS_PAYLOAD})

    def _post(self, endpoint: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
        headers = {"Content-Type": "application/json", "Accept": "application/json", "User-Agent": USER_AGENT}
        status, content_type, body = self._transport(
            f"{self._base_url}/{endpoint}", json.dumps(payload).encode("utf-8"), headers)
        if status != 200:
            raise TefasUnavailable(f"{endpoint}: HTTP {status}")
        if "json" not in content_type.lower() or not body.strip():
            # TEFAS's firewall can answer 200 with an empty body or an HTML page.
            raise TefasUnavailable(f"{endpoint}: not a JSON response ({content_type or 'no content type'})")
        try:
            envelope = json.loads(body, parse_float=Decimal)
        except ValueError as exc:
            raise TefasUnavailable(f"{endpoint}: malformed JSON") from exc
        if not isinstance(envelope, dict):
            raise TefasUnavailable(f"{endpoint}: unexpected response shape")
        if envelope.get("errorMessage"):
            raise TefasUnavailable(f"{endpoint}: TEFAS error {envelope.get('errorCode')}")
        rows = envelope.get("resultList") or []
        if not isinstance(rows, list):
            raise TefasUnavailable(f"{endpoint}: resultList is not a list")
        return [row for row in rows if isinstance(row, dict)]

    @staticmethod
    def _one(rows: list[dict[str, Any]], code: str) -> dict[str, Any]:
        if not rows:
            raise FundNotFound(code)
        return rows[0]


def _decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool) or not isinstance(value, (int, Decimal)):
        return None
    out = Decimal(value)
    return out if out.is_finite() else None


def _integer(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, Decimal) and value.is_finite() and value == value.to_integral_value():
        return int(value)
    return None


def _text(value: Any) -> str | None:
    return value.strip() or None if isinstance(value, str) else None
