"""TEFAS / borsapy provider spike (2026-10-06).

Fetches a small sample for two funds from TEFAS's public JSON endpoints with
certificate verification on, runs borsapy 0.10.1's parsing on the same raw
responses, and records which fields carry their own source date.

Deliberately not run:
- borsapy's allocation path. It drives a stealth browser built to get past
  Akamai bot detection, which is not an admissible data path.
- borsapy's KAP holdings path. It downloads disclosure PDFs and parses them
  with a paid LLM. Only the KAP disclosure list (dates) is fetched here.

Run from the repo root:
    python research/spikes/2026-10-06-tefas/spike.py

Raw responses go to the repo's raw/tefas/responses/ and raw/kap/reports/, which
are gitignored because TEFAS and KAP data rights have not been reviewed.
results.json holds structure, dates, counts, consistency checks and hashes only.
"""
from __future__ import annotations

import hashlib
import json
import math
import platform
import re
import socket
import ssl
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import certifi
import httpx

# TTE: an equity fund. AAL: the first TEFAS-traded money-market fund by code in
# the 2026-10-06 fund list. Two different fund types, chosen without looking at
# their data.
FUNDS = ("TTE", "AAL")
# AAK is borsapy's documentation example and is no longer in TEFAS's fund list;
# ZZZZZ never existed. Both test how an unknown code is reported.
NOT_FOUND_CODES = ("AAK", "ZZZZZ")
TEFAS_HOST = "www.tefas.gov.tr"
TEFAS_API = f"https://{TEFAS_HOST}/api/funds"
KAP_HOST = "kap.org.tr"
# Disclosure type id for "Portföy Dağılım Raporu", as used by borsapy's kap_holdings.py.
KAP_PORTFOLIO_REPORT_TYPE = "8aca490d502e34b801502e380044002b"
HISTORY_PERIYOD = 60  # TEFAS's largest history bucket (5 years)
PAUSE_SECONDS = 1.5
ISTANBUL = ZoneInfo("Europe/Istanbul")

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
RAW = REPO / "raw"
TEFAS_RESPONSES = RAW / "tefas" / "responses"
KAP_DIR = RAW / "kap" / "reports"
RESULTS = HERE / "results.json"

DATE_KEY = re.compile(r"tarih|date|zaman|saat|donem|time", re.IGNORECASE)
DATE_VALUE = re.compile(r"^\d{4}-\d{2}-\d{2}")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def environment() -> dict[str, Any]:
    import borsapy
    import borsapy._providers.tefas as tefas_module
    import borsapy.fund as fund_module

    return {
        "python": platform.python_version(),
        "borsapy": borsapy.__version__,
        "borsapy_tefas_py_sha256": sha256_file(Path(tefas_module.__file__)),
        "borsapy_fund_py_sha256": sha256_file(Path(fund_module.__file__)),
        "httpx": httpx.__version__,
        "certifi": certifi.__version__,
        "openssl": ssl.OPENSSL_VERSION,
    }


def _rdn(name: tuple) -> dict[str, str]:
    return {key: value for rdn in name for key, value in rdn}


def tls_handshake(host: str, context: ssl.SSLContext) -> dict[str, Any]:
    try:
        with socket.create_connection((host, 443), timeout=15) as sock:
            with context.wrap_socket(sock, server_hostname=host) as tls:
                cert = tls.getpeercert()
                return {
                    "ok": True,
                    "tls_version": tls.version(),
                    "subject_cn": _rdn(cert["subject"]).get("commonName"),
                    "issuer": _rdn(cert["issuer"]),
                    "not_after": cert["notAfter"],
                }
    except ssl.SSLCertVerificationError as exc:
        return {"ok": False, "error": type(exc).__name__, "verify_message": exc.verify_message}
    except (OSError, ssl.SSLError) as exc:
        return {"ok": False, "error": type(exc).__name__, "message": str(exc)}


def tls_checks() -> dict[str, Any]:
    out = {}
    for host in (TEFAS_HOST, KAP_HOST):
        verified = ssl.create_default_context(cafile=certifi.where())  # what httpx verify=True uses
        no_trust = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)  # verifies, but trusts no CA
        out[host] = {
            "verified_handshake": tls_handshake(host, verified),
            "negative_control_no_trusted_ca": tls_handshake(host, no_trust),
        }
    return out


class Fetcher:
    """Records every request; raw bodies are written under the repo's raw/."""

    def __init__(self, client: httpx.Client) -> None:
        self.client = client
        self.requests: list[dict[str, Any]] = []

    def _record(self, label: str, method: str, url: str, payload: Any,
                started: datetime, response: httpx.Response | None,
                error: Exception | None) -> tuple[dict[str, Any], bytes | None]:
        record: dict[str, Any] = {
            "label": label,
            "method": method,
            "url": url,
            "payload": payload,
            "requested_at_utc": started.isoformat(),
        }
        body = None
        if error is not None:
            record["error"] = f"{type(error).__name__}: {error}"
        else:
            body = response.content
            directory = KAP_DIR if label.startswith("kap_") else TEFAS_RESPONSES
            path = directory / f"{label}.body"
            path.write_bytes(body)
            record.update({
                "status": response.status_code,
                "content_type": response.headers.get("content-type"),
                "server_date_header": response.headers.get("date"),
                "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "raw_file": path.relative_to(REPO).as_posix(),
            })
        self.requests.append(record)
        time.sleep(PAUSE_SECONDS)
        return record, body

    def post_tefas(self, endpoint: str, payload: dict[str, Any], label: str):
        url = f"{TEFAS_API}/{endpoint}"
        started = datetime.now(timezone.utc)
        try:
            response = self.client.post(url, json=payload)
        except httpx.HTTPError as exc:
            return self._record(label, "POST", url, payload, started, None, exc)
        return self._record(label, "POST", url, payload, started, response, None)

    def get(self, url: str, label: str):
        started = datetime.now(timezone.utc)
        try:
            response = self.client.get(url)
        except httpx.HTTPError as exc:
            return self._record(label, "GET", url, None, started, None, exc)
        return self._record(label, "GET", url, None, started, response, None)


def tefas_envelope(record: dict[str, Any], body: bytes | None) -> dict[str, Any] | None:
    """Return the decoded TEFAS envelope, or None if the body is not JSON."""
    if body is None or "json" not in (record.get("content_type") or "").lower():
        return None
    try:
        decoded = json.loads(body)
    except json.JSONDecodeError:
        return None
    return decoded if isinstance(decoded, dict) else None


def field_inventory(row: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out = {}
    for key, value in row.items():
        out[key] = {
            "type": type(value).__name__,
            "null": value is None,
            "date_like": bool(DATE_KEY.search(key))
            or (isinstance(value, str) and bool(DATE_VALUE.match(value))),
        }
    return out


def decimals(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    text = repr(float(value))
    if "e" in text or "E" in text:
        return None
    return len(text.split(".")[1].rstrip("0")) if "." in text else 0


def history_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    keys = sorted({key for row in rows for key in row})
    raw_dates = [row.get("tarih") for row in rows]
    shapes = sorted({re.sub(r"\d", "9", str(d)) for d in raw_dates})
    parsed: list[date] = []
    unparsed = 0
    for value in raw_dates:
        try:
            parsed.append(date.fromisoformat(str(value)[:10]))
        except ValueError:
            unparsed += 1
    unique = sorted(set(parsed))
    if parsed == sorted(parsed):
        order = "ascending"
    elif parsed == sorted(parsed, reverse=True):
        order = "descending"
    else:
        order = "unsorted"
    gaps = sorted(
        ((later - earlier).days, earlier.isoformat(), later.isoformat())
        for earlier, later in zip(unique, unique[1:])
    )
    prices = [row.get("fiyat") for row in rows]
    finite_prices = [p for p in prices if isinstance(p, (int, float)) and not isinstance(p, bool) and math.isfinite(p)]
    price_decimals = [d for d in (decimals(p) for p in finite_prices) if d is not None]
    return {
        "row_count": len(rows),
        "row_keys": keys,
        "row_field_inventory": field_inventory(rows[0]) if rows else {},
        "date_string_shapes": shapes,
        "unparsed_dates": unparsed,
        "first_date": unique[0].isoformat() if unique else None,
        "last_date": unique[-1].isoformat() if unique else None,
        "order": order,
        "duplicate_dates": len(parsed) - len(unique),
        "weekend_dates": [d.isoformat() for d in unique if d.weekday() >= 5],
        "gaps_over_4_days": [
            {"days": days, "from": start, "to": end} for days, start, end in gaps if days > 4
        ],
        "price_types": sorted({type(p).__name__ for p in prices}),
        "missing_prices": sum(1 for p in prices if p is None),
        "nonpositive_prices": sum(1 for p in finite_prices if p <= 0),
        "max_price_decimals": max(price_decimals) if price_decimals else None,
    }


def latest_two(rows: list[dict[str, Any]]) -> list[tuple[date, float]]:
    points = []
    for row in rows:
        try:
            points.append((date.fromisoformat(str(row["tarih"])[:10]), float(row["fiyat"])))
        except (KeyError, TypeError, ValueError):
            continue
    points.sort()
    return points[-2:]


class _NoNetwork(httpx.BaseTransport):
    def handle_request(self, request: httpx.Request) -> httpx.Response:
        raise AssertionError(f"borsapy attempted a network call: {request.url}")


def borsapy_view(raw_results: dict[tuple, list[dict[str, Any]]]) -> dict[str, Any]:
    """Run borsapy's TEFAS parsing on the already-fetched raw result lists."""
    from borsapy._providers.tefas import TEFASProvider

    provider = TEFASProvider()  # builds an httpx client with verify=False ...
    provider._client.close()
    provider._client = httpx.Client(transport=_NoNetwork())  # ... which is replaced, unused
    calls: list[list[Any]] = []

    def replay(endpoint_path, payload, endpoint_label, max_retries=3):
        key = (endpoint_path, payload.get("fonKodu") or payload.get("fonTipi"), payload.get("periyod"))
        calls.append(list(key))
        if key == ("fonGetiriBazliBilgiGetir", "EMK", None):
            return []  # pension-fund fallback; not fetched in this spike
        if key not in raw_results:
            raise AssertionError(f"unexpected borsapy call: {key}")
        return raw_results[key]

    provider._post_json_v2 = replay
    out: dict[str, Any] = {"calls": calls, "funds": {}}
    for code in FUNDS:
        fund: dict[str, Any] = {}
        try:
            detail = provider.get_fund_detail(code)
            fund["detail_keys"] = sorted(detail)
            fund["detail_empty_or_zero"] = sorted(
                key for key, value in detail.items() if value in ("", 0, None)
            )
            fund["detail_date_value"] = detail.get("date")
            fund["detail"] = detail
        except Exception as exc:  # noqa: BLE001 - recorded, not hidden
            fund["detail_error"] = f"{type(exc).__name__}: {exc}"
        try:
            history = provider.get_history(code, period="5y")
            fund["history_columns"] = list(history.columns)
            fund["history_rows"] = len(history)
            fund["history_index_tz"] = str(getattr(history.index, "tz", None))
            fund["history_fundsize_all_nan"] = bool(history["FundSize"].isna().all())
            fund["history_investors_all_zero"] = bool((history["Investors"] == 0).all())
            fund["history_last_date"] = history.index.max().date().isoformat()
        except Exception as exc:  # noqa: BLE001
            fund["history_error"] = f"{type(exc).__name__}: {exc}"
        out["funds"][code] = fund
    return out


def kap_probe(fetcher: Fetcher, code: str, kap_link: Any) -> dict[str, Any]:
    out: dict[str, Any] = {"kap_link_present": bool(kap_link)}
    if not isinstance(kap_link, str) or not kap_link:
        return out
    url = httpx.URL(kap_link)
    if url.scheme != "https" or not (url.host == KAP_HOST or url.host.endswith("." + KAP_HOST)):
        out["skipped"] = f"kapLink host not on {KAP_HOST}: {url.host}"
        return out
    record, body = fetcher.get(kap_link, f"kap_page_{code}")
    out["page_status"] = record.get("status")
    if body is None or record.get("status") != 200:
        out["stopped"] = "KAP fund page not retrieved; no further KAP requests"
        return out
    match = re.search(r'objId[\\"\':]+([A-Fa-f0-9]{32})', body.decode("utf-8", errors="replace"))
    if not match:
        out["stopped"] = "objId not found in KAP page (possible challenge page); not bypassed"
        return out
    fund_id = match.group(1)
    list_url = (f"https://{KAP_HOST}/tr/api/disclosure/filter/FILTERYFBF/"
                f"{fund_id}/{KAP_PORTFOLIO_REPORT_TYPE}/365")
    record, body = fetcher.get(list_url, f"kap_portfolio_reports_{code}")
    out["list_status"] = record.get("status")
    try:
        items = json.loads(body) if body else None
    except json.JSONDecodeError:
        items = None
    if not isinstance(items, list):
        out["stopped"] = "disclosure list was not a JSON list"
        return out
    basics = [item.get("disclosureBasic", {}) for item in items if isinstance(item, dict)]
    out["report_count"] = len(basics)
    out["disclosure_basic_keys"] = sorted({key for basic in basics for key in basic})
    out["publish_date_shapes"] = sorted({re.sub(r"\d", "9", str(b.get("publishDate"))) for b in basics})
    out["flags_set"] = {
        flag: sum(1 for b in basics if b.get(flag)) for flag in ("isLate", "isChanged", "isBlocked")
    }
    out["reports"] = [
        {
            "publish_date": basic.get("publishDate"),
            "year": basic.get("year"),
            "period_month": basic.get("donem"),
            "attachment_count": basic.get("attachmentCount"),
        }
        for basic in basics
    ]
    return out


def main() -> None:
    TEFAS_RESPONSES.mkdir(parents=True, exist_ok=True)
    KAP_DIR.mkdir(parents=True, exist_ok=True)
    run_utc = datetime.now(timezone.utc)
    results: dict[str, Any] = {
        "run_at_utc": run_utc.isoformat(),
        "run_at_istanbul": run_utc.astimezone(ISTANBUL).isoformat(),
        "funds": list(FUNDS),
        "environment": environment(),
        "tls": tls_checks(),
    }
    if not results["tls"][TEFAS_HOST]["verified_handshake"]["ok"]:
        results["stopped"] = "TEFAS certificate did not verify; no TEFAS requests made"
        RESULTS.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(results["stopped"])
        return

    from borsapy._providers.base import BaseProvider

    user_agent = BaseProvider.DEFAULT_HEADERS["User-Agent"]
    results["request_headers"] = {"User-Agent": user_agent, "Content-Type": "application/json",
                                  "Accept": "application/json"}
    client = httpx.Client(verify=True, timeout=30.0, headers=results["request_headers"])
    fetcher = Fetcher(client)
    raw_results: dict[tuple, list[dict[str, Any]]] = {}
    tefas: dict[str, Any] = {}

    for code in FUNDS:
        fund: dict[str, Any] = {}
        calls = (
            ("fonBilgiGetir", {"fonKodu": code}, None),
            ("fonProfilBilgiGetir", {"fonKodu": code, "dil": "TR"}, None),
            ("fonFiyatBilgiGetir", {"fonKodu": code, "dil": "TR", "periyod": HISTORY_PERIYOD}, HISTORY_PERIYOD),
        )
        for endpoint, payload, periyod in calls:
            record, body = fetcher.post_tefas(endpoint, payload, f"{endpoint}_{code}")
            envelope = tefas_envelope(record, body)
            entry: dict[str, Any] = {"status": record.get("status"), "error": record.get("error")}
            if envelope is None:
                entry["parsed"] = False
            else:
                result_list = envelope.get("resultList") or []
                entry.update({
                    "parsed": True,
                    "envelope_keys": sorted(envelope),
                    "error_code": envelope.get("errorCode"),
                    "error_message": envelope.get("errorMessage"),
                    "result_count": len(result_list),
                })
                raw_results[(endpoint, code, periyod)] = result_list
                if endpoint == "fonFiyatBilgiGetir":
                    entry["history"] = history_summary(result_list)
                elif result_list:
                    entry["field_inventory"] = field_inventory(result_list[0])
            fund[endpoint] = entry
        tefas[code] = fund

    returns_payload = {
        "fonTipi": "YAT", "dil": "TR", "calismaTipi": 2,
        "donemGetiri1a": "1", "donemGetiri3a": "1", "donemGetiri6a": "1",
        "donemGetiriyb": "1", "donemGetiri1y": "1", "donemGetiri3y": "1", "donemGetiri5y": "1",
    }
    record, body = fetcher.post_tefas("fonGetiriBazliBilgiGetir", returns_payload, "fonGetiriBazliBilgiGetir_YAT")
    envelope = tefas_envelope(record, body)
    all_returns = (envelope or {}).get("resultList") or []
    raw_results[("fonGetiriBazliBilgiGetir", "YAT", None)] = all_returns
    tefas["fonGetiriBazliBilgiGetir_YAT"] = {
        "status": record.get("status"),
        "result_count": len(all_returns),
        "field_inventory_per_fund": {
            row.get("fonKodu"): field_inventory(row) for row in all_returns if row.get("fonKodu") in FUNDS
        },
    }

    listed = {row.get("fonKodu") for row in all_returns}
    tefas["not_found_codes"] = {}
    for code in NOT_FOUND_CODES:
        record, body = fetcher.post_tefas("fonBilgiGetir", {"fonKodu": code}, f"fonBilgiGetir_{code}")
        tefas["not_found_codes"][code] = {
            "in_yat_fund_list": code in listed,
            "status": record.get("status"),
            "content_type": record.get("content_type"),
            "envelope": tefas_envelope(record, body),
        }
    results["tefas"] = tefas

    # Cross-checks: does the undated snapshot line up with the newest dated history row?
    checks: dict[str, Any] = {}
    for code in FUNDS:
        info_rows = raw_results.get(("fonBilgiGetir", code, None)) or [{}]
        info = info_rows[0]
        last_two = latest_two(raw_results.get(("fonFiyatBilgiGetir", code, HISTORY_PERIYOD)) or [])
        check: dict[str, Any] = {"latest_history_date": last_two[-1][0].isoformat() if last_two else None}
        price = info.get("sonFiyat")
        if last_two and isinstance(price, (int, float)):
            check["sonFiyat_equals_latest_history_price"] = math.isclose(price, last_two[-1][1], rel_tol=0, abs_tol=1e-9)
        units, size = info.get("payAdet"), info.get("portBuyukluk")
        if all(isinstance(v, (int, float)) and v > 0 for v in (units, size, price)):
            # Fund size should equal units outstanding x unit price at the same as-of date.
            check["units_x_price_vs_size_rel_diff"] = abs(units * price - size) / size
        daily = info.get("gunlukGetiri")
        if len(last_two) == 2 and isinstance(daily, (int, float)):
            computed = last_two[1][1] / last_two[0][1] - 1
            check["gunlukGetiri_abs_diff_if_percent"] = abs(daily - computed * 100)
            check["gunlukGetiri_abs_diff_if_fraction"] = abs(daily - computed)
            check["latest_two_history_dates"] = [d.isoformat() for d, _ in last_two]
        checks[code] = check
    results["snapshot_vs_history"] = checks

    view = borsapy_view(raw_results)
    for code in FUNDS:
        detail = view["funds"][code].pop("detail", None)
        if detail is None:
            continue
        info = (raw_results.get(("fonBilgiGetir", code, None)) or [{}])[0]
        # Fields where borsapy reports 0/""/None although the raw snapshot carried a value.
        view["funds"][code]["coerced_vs_raw"] = {
            out_key: {"raw_present": info.get(raw_key) is not None, "borsapy_value_is_placeholder": detail.get(out_key) in ("", 0, None)}
            for out_key, raw_key in (("price", "sonFiyat"), ("fund_size", "portBuyukluk"),
                                     ("investor_count", "yatirimciSayi"), ("category", "fonKategori"))
        }
    results["borsapy"] = view

    kap: dict[str, Any] = {}
    for code in FUNDS:
        profile = (raw_results.get(("fonProfilBilgiGetir", code, None)) or [{}])[0]
        kap[code] = kap_probe(fetcher, code, profile.get("kapLink"))
    results["kap"] = kap

    results["requests"] = fetcher.requests
    client.close()
    RESULTS.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (TEFAS_RESPONSES / "requests.json").write_text(json.dumps(fetcher.requests, indent=2, ensure_ascii=False) + "\n",
                                       encoding="utf-8")
    print(f"{len(fetcher.requests)} requests; results written to {RESULTS.relative_to(HERE.parents[2])}")


if __name__ == "__main__":
    main()
