"""Paced, restartable public-source downloads to the external overnight archive.

These runners never write to the research raw archive. TEFAS profiles and prices
share one coordinator; KAP report lists and SPK PDFs run independently. All
requests verify TLS, and a runner stops after three consecutive failed requests.
No secrets or response bodies are logged.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import re
import sqlite3
import ssl
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable, Iterator, Sequence

from p50k.providers.tefas import FundNotFound, TefasClient, TefasUnavailable, USER_AGENT

TEFAS = "https://www.tefas.gov.tr/api/funds"
KAP = "https://kap.org.tr"
SPK = "https://spk.gov.tr"
REPORT_TYPE = "8aca490d502e34b801502e380044002b"
CODE = re.compile(r"^[A-Z0-9]{2,10}$")
FUND_ID = re.compile(r"objId[\\\"':\s]+([A-Fa-f0-9]{32})")
MAX_BODY_BYTES = 64 * 1024 * 1024
MAX_CONSECUTIVE_FAILURES = 3
MAX_REDIRECTS = 3
REDIRECT_STATUSES = {301, 302, 303, 307, 308}
SMOKE_CODES = ("THF", "TP2")


class ResponseError(ValueError):
    """Unexpected public-source response, without including its body."""


class DownloadStopped(RuntimeError):
    """Three consecutive request failures: no further source requests."""


@dataclass(frozen=True)
class Response:
    status: int
    content_type: str
    body: bytes
    server_date: str | None = None
    location: str | None = None


@dataclass
class Counts:
    saved: int = 0
    reused: int = 0
    missing: int = 0
    failed: int = 0


Transport = Callable[[str, str, bytes | None, dict[str, str]], Response]
Validator = Callable[[Response], Any]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def allowed_url(url: str, host: str) -> bool:
    try:
        parts = urllib.parse.urlsplit(url)
        return (parts.scheme == "https" and parts.hostname in {host, "www." + host}
                and parts.port in {None, 443} and not parts.username and not parts.password)
    except ValueError:
        return False


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # PacedSession handles each redirect as a separate logged, paced request.
        return None


def urllib_transport(method: str, url: str, body: bytes | None,
                     headers: dict[str, str]) -> Response:
    opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=ssl.create_default_context()), _NoRedirect())
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with opener.open(request, timeout=90) as result:
            content = result.read(MAX_BODY_BYTES + 1)
            if len(content) > MAX_BODY_BYTES:
                raise ResponseError("response exceeds size limit")
            return Response(result.status, result.headers.get("Content-Type", ""), content,
                            result.headers.get("Date"))
    except urllib.error.HTTPError as exc:
        try:
            return Response(exc.code, exc.headers.get("Content-Type", "") if exc.headers else "", b"",
                            exc.headers.get("Date") if exc.headers else None,
                            exc.headers.get("Location") if exc.headers else None)
        finally:
            exc.close()


def atomic_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(dir=path.parent, prefix="." + path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except BaseException:
        Path(temp_name).unlink(missing_ok=True)
        raise


def atomic_json(path: Path, value: Any) -> None:
    atomic_bytes(path, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def payload_sha256(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


class PacedSession:
    def __init__(self, host: str, pause: float, log: Path | None = None, *,
                 transport: Transport = urllib_transport,
                 sleep: Callable[[float], None] = time.sleep) -> None:
        minimum = 1.5 if host == "tefas.gov.tr" else 6.0
        if host not in {"tefas.gov.tr", "kap.org.tr", "spk.gov.tr"} or pause < minimum:
            raise ValueError("unknown source or unsafe request pace")
        self.host, self.pause, self.log = host, pause, log
        self.transport, self.sleep = transport, sleep
        self.failures = 0
        self.requests = 0
        self.last_metadata: dict[str, Any] = {}

    def request(self, method: str, url: str, *, payload: dict[str, Any] | None = None,
                validate: Validator | None = None) -> Response | None:
        if self.failures >= MAX_CONSECUTIVE_FAILURES:
            raise DownloadStopped("consecutive request failures")
        if not allowed_url(url, self.host):
            raise ValueError("source URL is not allowed")
        headers = {"User-Agent": USER_AGENT, "Accept": "application/json, text/html, application/pdf"}
        body = None
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        current_url = url
        chain: list[dict[str, Any]] = []
        for hop in range(MAX_REDIRECTS + 1):
            entry: dict[str, Any] = {"requested_at_utc": utc_now(), "method": method,
                                     "url": current_url, "original_url": url, "redirect_hop": hop}
            if payload is not None:
                entry["payload_sha256"] = payload_sha256(payload)
            response = None
            next_url = None
            try:
                response = self.transport(method, current_url, body, headers)
                entry.update(status=response.status, bytes=len(response.body),
                             content_type=response.content_type,
                             sha256=hashlib.sha256(response.body).hexdigest(),
                             server_date_header=response.server_date)
                if response.status in REDIRECT_STATUSES:
                    if (not response.location or hop == MAX_REDIRECTS
                            or (method != "GET" and response.status not in {307, 308})):
                        raise ResponseError("redirect is missing, unbounded or changes request method")
                    next_url = urllib.parse.urljoin(current_url, response.location)
                    if not allowed_url(next_url, self.host):
                        raise ResponseError("redirect outside source host")
                    entry["redirect_to"] = next_url
                elif response.status != 200 or not response.body.strip():
                    raise ResponseError("HTTP status or empty body")
                elif validate is not None:
                    validate(response)
            except (OSError, ValueError, urllib.error.URLError) as exc:
                entry["error_class"] = type(exc).__name__
                response, next_url = None, None
            finally:
                self.requests += 1
                self.last_metadata = {**entry, "redirect_chain": list(chain)}
                if self.log is not None:
                    self.log.parent.mkdir(parents=True, exist_ok=True)
                    with self.log.open("a", encoding="utf-8", newline="\n") as handle:
                        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
                self.sleep(self.pause)
            if next_url is None:
                break
            chain.append({"url": current_url, "method": method, "status": response.status,
                          "redirect_to": next_url})
            current_url = next_url
        self.failures = 0 if response is not None else self.failures + 1
        if self.failures >= MAX_CONSECUTIVE_FAILURES:
            raise DownloadStopped("consecutive request failures")
        return response

    def tefas_transport(self, url: str, body: bytes, headers: dict[str, str]) -> tuple[int, str, bytes]:
        del headers
        response = self.request("POST", url, payload=json.loads(body), validate=tefas_envelope)
        if response is None:
            raise TefasUnavailable("source request failed")
        return response.status, response.content_type, response.body


def tefas_envelope(response: Response) -> dict[str, Any]:
    if "json" not in response.content_type.lower():
        raise ResponseError("TEFAS response is not JSON")
    parsed = json.loads(response.body)
    if (not isinstance(parsed, dict) or parsed.get("errorMessage")
            or not isinstance(parsed.get("resultList"), list)
            or any(not isinstance(row, dict) for row in parsed["resultList"])):
        raise ResponseError("TEFAS response shape")
    return parsed


def kap_listing(response: Response) -> list[dict[str, Any]]:
    if "json" not in response.content_type.lower():
        raise ResponseError("KAP response is not JSON")
    parsed = json.loads(response.body)
    if not isinstance(parsed, list) or any(
            not isinstance(item, dict) or not isinstance(item.get("disclosureBasic"), dict)
            for item in parsed):
        raise ResponseError("KAP report-list shape")
    return parsed


def pdf_response(response: Response) -> None:
    if not response.body.startswith(b"%PDF-"):
        raise ResponseError("SPK response is not a PDF")


def kap_page(response: Response) -> str:
    match = FUND_ID.search(response.body.decode("utf-8", errors="replace"))
    if not match:
        raise ResponseError("KAP fund identifier missing")
    return match.group(1)


def store_response(path: Path, response: Response, session: PacedSession) -> None:
    atomic_bytes(path, response.body)
    atomic_json(path.with_suffix(path.suffix + ".meta.json"), session.last_metadata)


def cached(path: Path, validator: Validator, *, expected_url: str,
           expected_method: str = "GET", expected_payload: dict[str, Any] | None = None) -> bool:
    if not path.is_file():
        return False
    try:
        body = path.read_bytes()
        meta_path = path.with_suffix(path.suffix + ".meta.json")
        if not meta_path.exists():
            return False
        metadata = read_json(meta_path)
        if not isinstance(metadata, dict) or metadata.get("sha256") != hashlib.sha256(body).hexdigest():
            return False
        host = (urllib.parse.urlsplit(expected_url).hostname or "").removeprefix("www.")
        if host not in {"tefas.gov.tr", "kap.org.tr", "spk.gov.tr"} or not allowed_url(expected_url, host):
            return False
        if (metadata.get("original_url", metadata.get("url")) != expected_url
                or metadata.get("method") != expected_method
                or type(metadata.get("status")) is not int or metadata["status"] != 200
                or not isinstance(metadata.get("url"), str) or not allowed_url(metadata["url"], host)):
            return False
        chain = metadata.get("redirect_chain", [])
        if not isinstance(chain, list) or len(chain) > MAX_REDIRECTS:
            return False
        current_url = expected_url
        for hop in chain:
            if (not isinstance(hop, dict) or hop.get("url") != current_url
                    or hop.get("method") != expected_method or hop.get("status") not in REDIRECT_STATUSES
                    or not isinstance(hop.get("redirect_to"), str)
                    or not allowed_url(hop["redirect_to"], host)
                    or (expected_method != "GET" and hop["status"] not in {307, 308})):
                return False
            current_url = hop["redirect_to"]
        if metadata["url"] != current_url:
            return False
        if expected_payload is not None and metadata.get("payload_sha256") != payload_sha256(expected_payload):
            return False
        validator(Response(200, str(metadata.get("content_type") or ""), body))
        return True
    except (OSError, ValueError, TypeError, KeyError):
        return False


def valid_code(value: Any) -> str | None:
    code = value.upper() if isinstance(value, str) else ""
    return code if CODE.fullmatch(code) else None


def archive_codes(archive_root: Path, snapshot_db: Path | None = None, *,
                  tefas_only: bool = False) -> list[str]:
    rows = read_json(archive_root / "tefas/responses/fonGetiriBazliBilgiGetir_YAT.body")["resultList"]
    codes = {code for row in rows if (code := valid_code(row.get("fonKodu")))
             and (not tefas_only or row.get("tefasDurum") is True)}
    if not tefas_only and snapshot_db is not None and snapshot_db.is_file():
        with sqlite3.connect(snapshot_db.resolve().as_uri() + "?mode=ro&immutable=1", uri=True) as db:
            codes.update(code for row in db.execute("SELECT DISTINCT fund FROM fund_snapshots")
                         if (code := valid_code(row[0])))
    return sorted(codes)


def profile_links(archive_root: Path, out_root: Path,
                  snapshot_db: Path | None = None) -> dict[str, str]:
    links: dict[str, str] = {}
    paths = [*sorted((archive_root / "tefas/responses").glob("fonProfilBilgiGetir_*.body")),
             *sorted((archive_root / "kap/reports").glob("*/tefas_profile.json")),
             *sorted((out_root / "tefas/profiles").glob("*.json"))]
    for path in paths:
        if path.name.endswith(".meta.json"):
            continue
        if path.name == "tefas_profile.json":
            inferred = path.parent.name
        else:
            inferred = path.stem.removeprefix("fonProfilBilgiGetir_")
        try:
            rows = read_json(path).get("resultList") or []
        except (OSError, ValueError, AttributeError):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            code = valid_code(row.get("fonKodu") or inferred)
            link = row.get("kapLink")
            if code and isinstance(link, str) and allowed_url(link, "kap.org.tr"):
                links[code] = link
    if snapshot_db is not None and snapshot_db.is_file():
        with sqlite3.connect(snapshot_db.resolve().as_uri() + "?mode=ro&immutable=1", uri=True) as db:
            for fund, raw in db.execute("SELECT fund, raw_snapshot FROM fund_snapshots"):
                try:
                    row = json.loads(raw)
                    code, link = valid_code(fund), row.get("kapLink")
                    if code and isinstance(link, str) and allowed_url(link, "kap.org.tr"):
                        links.setdefault(code, link)
                except (ValueError, AttributeError):
                    continue
    return links


def download_profiles(session: PacedSession, codes: Sequence[str], out_root: Path,
                      *, force: bool = False) -> Counts:
    counts = Counts()
    for code in codes:
        if not valid_code(code):
            raise ValueError("invalid fund code")
        path = out_root / "tefas/profiles" / (code + ".json")
        payload = {"fonKodu": code, "dil": "TR"}
        if not force and cached(path, tefas_envelope, expected_url=TEFAS + "/fonProfilBilgiGetir",
                                expected_method="POST", expected_payload=payload):
            counts.reused += 1
            continue
        response = session.request("POST", TEFAS + "/fonProfilBilgiGetir",
                                   payload=payload, validate=tefas_envelope)
        if response is None:
            counts.failed += 1
            continue
        store_response(path, response, session)
        counts.saved += 1
        if not tefas_envelope(response)["resultList"]:
            counts.missing += 1
        status(out_root, "tefas-profiles", "running", counts, session.requests)
    return counts


def _price_payload(response: Response) -> None:
    parsed = json.loads(response.body)
    if not isinstance(parsed, dict) or parsed.get("periyod") != 12 or not isinstance(parsed.get("rows"), list):
        raise ResponseError("price archive shape")
    if any(not isinstance(row, list) or len(row) != 2 for row in parsed["rows"]):
        raise ResponseError("price archive rows")


def download_prices(session: PacedSession, codes: Sequence[str], out_root: Path) -> Counts:
    """Use the existing Decimal/zero-normalizing provider without changing it."""
    counts = Counts()
    client = TefasClient(transport=session.tefas_transport)
    for code in codes:
        path = out_root / "tefas/prices" / (code + ".json")
        if cached(path, _price_payload, expected_url=TEFAS + "/fonFiyatBilgiGetir", expected_method="POST",
                  expected_payload={"fonKodu": code, "dil": "TR", "periyod": 12}):
            counts.reused += 1
            continue
        try:
            points = client.price_history(code, periyod=12)
        except FundNotFound:
            counts.missing += 1
            continue
        except TefasUnavailable:
            counts.failed += 1
            continue
        payload = {"fund": code, "source": "TEFAS fonFiyatBilgiGetir", "periyod": 12,
                   "retrieved_at": utc_now(),
                   "rows": [[point.date.isoformat(), None if point.price is None else str(point.price)]
                            for point in points]}
        atomic_json(path, payload)
        metadata = dict(session.last_metadata)
        metadata["raw_response_sha256"] = metadata.pop("sha256")
        metadata["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        atomic_json(path.with_suffix(".json.meta.json"), metadata)
        counts.saved += 1
        status(out_root, "tefas-prices", "running", counts, session.requests)
    return counts


class _Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self.links.extend(value for key, value in attrs if key == "href" and value is not None)


def spk_index_url(year: int) -> str:
    if year not in {2024, 2025, 2026}:
        raise ValueError("only approved SPK years may be downloaded")
    section = "/spk-bultenleri/"
    if year == 2024:
        section += "gecmis-yillara-ait-bultenler/"
    return SPK + section + str(year) + "-yili-spk-bultenleri"


def parse_spk_index(body: bytes, page_url: str, year: int) -> tuple[list[str], list[str]]:
    parser = _Links()
    parser.feed(body.decode("utf-8", errors="replace"))
    pdfs, pages = set(), set()
    base_path = urllib.parse.urlsplit(spk_index_url(year)).path
    for href in parser.links:
        url = urllib.parse.urljoin(page_url, href)
        if not allowed_url(url, "spk.gov.tr"):
            continue
        parsed = urllib.parse.urlsplit(url)
        if parsed.path.startswith("/data/") and re.fullmatch(
                str(year) + r"[-_]\d+\.pdf", Path(parsed.path).name, flags=re.IGNORECASE):
            pdfs.add(url)
        elif parsed.path.rstrip("/") == base_path:
            query = urllib.parse.parse_qs(parsed.query)
            page = query.get("s", ["1"])[0]
            if page.isdigit() and 1 <= int(page) <= 20:
                pages.add(spk_index_url(year) + ("?s=" + page if int(page) != 1 else ""))
    return sorted(pdfs), sorted(pages)


def download_spk(session: PacedSession, out_root: Path,
                 years: Sequence[int] = (2026, 2025, 2024)) -> Counts:
    counts = Counts()
    manifest: dict[str, dict[str, Any]] = {}
    manifest_path = out_root / "spk/manifest.json"
    if manifest_path.exists():
        manifest = read_json(manifest_path)
    for year in years:
        pending, seen, pdfs = [spk_index_url(year)], set(), set()
        while pending:
            url = pending.pop(0)
            if url in seen:
                continue
            seen.add(url)

            def validate_index(response: Response) -> None:
                if not parse_spk_index(response.body, url, year)[0]:
                    raise ResponseError("SPK index contains no bulletin links")

            response = session.request("GET", url, validate=validate_index)
            if response is None:
                counts.failed += 1
                continue
            page = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query).get("s", ["1"])[0]
            store_response(out_root / "spk/indexes" / f"{year}-{page}.html", response, session)
            found, pagination = parse_spk_index(response.body, url, year)
            pdfs.update(found)
            pending.extend(page_url for page_url in pagination if page_url not in seen)
        for url in sorted(pdfs, reverse=True):
            filename = Path(urllib.parse.urlsplit(url).path).name
            path = out_root / "spk/pdfs" / str(year) / filename
            if cached(path, pdf_response, expected_url=url):
                counts.reused += 1
                continue
            response = session.request("GET", url, validate=pdf_response)
            if response is None:
                counts.failed += 1
                continue
            store_response(path, response, session)
            manifest[str(year) + "/" + filename] = dict(session.last_metadata)
            atomic_json(manifest_path, manifest)
            counts.saved += 1
            status(out_root, "spk", "running", counts, session.requests)
    return counts


def _has_archive_list(archive_root: Path, code: str) -> bool:
    for path in (
        archive_root / "kap/reports" / code / "kap_report_list.json",
        archive_root / "kap/reports" / ("kap_portfolio_reports_" + code + ".body")):
        if path.is_file():
            try:
                kap_listing(Response(200, "application/json", path.read_bytes()))
                return True
            except (OSError, ValueError):
                pass
    return False


def download_kap_list(session: PacedSession, code: str, link: str, out_root: Path) -> bool:
    folder = out_root / "kap/reports" / code
    response = session.request("GET", link, validate=kap_page)
    if response is None:
        return False
    fund_id = kap_page(response)
    store_response(folder / "kap_fund_page.html", response, session)
    return download_kap_id(session, code, fund_id, out_root)


def download_kap_id(session: PacedSession, code: str, fund_id: str, out_root: Path) -> bool:
    if not valid_code(code) or not re.fullmatch(r"[a-fA-F0-9]{32}", fund_id):
        raise ValueError("invalid public KAP fund identity")
    folder = out_root / "kap/reports" / code
    url = kap_list_url(fund_id)
    response = session.request("GET", url, validate=kap_listing)
    if response is None:
        return False
    store_response(folder / "kap_report_list.json", response, session)
    return True


def kap_list_url(fund_id: str) -> str:
    return KAP + "/tr/api/disclosure/filter/FILTERYFBF/" + fund_id + "/" + REPORT_TYPE + "/365"


def cached_kap_list(out_root: Path, code: str, fund_id: str | None, link: str | None) -> bool:
    folder = out_root / "kap/reports" / code
    if fund_id is None:
        page = folder / "kap_fund_page.html"
        if link is None or not cached(page, kap_page, expected_url=link):
            return False
        fund_id = kap_page(Response(200, "text/html", page.read_bytes()))
    return cached(folder / "kap_report_list.json", kap_listing, expected_url=kap_list_url(fund_id))


def parse_kap_directory(body: bytes) -> dict[str, str]:
    """Read JSON embedded by KAP's public Next.js page without executing scripts.

    The public directory also carries other fund classes in its navigation data.
    Only unambiguous code/identifier pairs are returned; callers select the
    authorized TEFAS investment-fund cohort before making report-list requests.
    """
    text = body.decode("utf-8", errors="replace")
    chunks: list[str] = []
    for match in re.finditer(r"self\.__next_f\.push\((\[.*?\])\)\s*;?", text, flags=re.DOTALL):
        try:
            frame = json.loads(match.group(1))
        except ValueError:
            continue
        if isinstance(frame, list):
            chunks.extend(item for item in frame if isinstance(item, str))
    combined = "".join(chunks)
    decoder = json.JSONDecoder()
    candidates: dict[str, set[str]] = {}
    for match in re.finditer(r'"fundCode"', combined):
        start = combined.rfind("{", 0, match.start())
        if start < 0:
            continue
        try:
            row, _ = decoder.raw_decode(combined, start)
        except ValueError:
            continue
        if not isinstance(row, dict):
            continue
        code, fund_id = valid_code(row.get("fundCode")), row.get("fundOid")
        if code and isinstance(fund_id, str) and re.fullmatch(r"[a-fA-F0-9]{32}", fund_id):
            candidates.setdefault(code, set()).add(fund_id.lower())
    return {code: next(iter(ids)) for code, ids in candidates.items() if len(ids) == 1}


def download_kap_directory(session: PacedSession, out_root: Path) -> dict[str, str]:
    path = out_root / "kap/directory/TEYF.html"

    def validate_directory(response: Response) -> None:
        if not parse_kap_directory(response.body):
            raise ResponseError("public KAP directory has no unambiguous fund identities")

    if cached(path, validate_directory, expected_url=KAP + "/tr/YatirimFonlari/TEYF"):
        body = path.read_bytes()
    else:
        response = session.request("GET", KAP + "/tr/YatirimFonlari/TEYF", validate=validate_directory)
        if response is None:
            return {}
        store_response(path, response, session)
        body = response.body
    mapping = parse_kap_directory(body)
    atomic_json(path.with_name("fund_ids.json"), {
        "source": KAP + "/tr/YatirimFonlari/TEYF",
        "source_sha256": hashlib.sha256(body).hexdigest(),
        "acquisition": read_json(path.with_suffix(".html.meta.json")),
        "fund_ids": mapping,
    })
    return mapping


def download_kap(session: PacedSession, archive_root: Path, out_root: Path, *,
                 snapshot_db: Path | None = None, watch: bool = False,
                 sleep: Callable[[float], None] = time.sleep,
                 smoke: bool = True, deadline_hours: float = 20,
                 use_directory: bool = True) -> Counts:
    counts = Counts()
    directory = download_kap_directory(session, out_root) if use_directory else {}
    universe_path = archive_root / "tefas/responses/fonGetiriBazliBilgiGetir_YAT.body"
    universe = set(archive_codes(archive_root, tefas_only=True)) if universe_path.is_file() else None
    attempted: set[str] = set()
    smoke_done = not smoke
    deadline = time.monotonic() + deadline_hours * 3600
    while True:
        links = profile_links(archive_root, out_root, snapshot_db)
        identities = set(directory) | set(links)
        if not smoke_done and all(code in identities for code in SMOKE_CODES):
            for code in SMOKE_CODES:
                ok = (download_kap_id(session, code, directory[code], out_root) if code in directory
                      else download_kap_list(session, code, links[code], out_root))
                if not ok:
                    raise ResponseError("two-fund KAP smoke failed")
            smoke_done = True
            status(out_root, "kap-smoke", "complete", Counts(saved=len(SMOKE_CODES)), session.requests)
        for code in sorted(identities):
            if universe is not None and code not in universe:
                continue
            if code in attempted:
                continue
            if _has_archive_list(archive_root, code) or cached_kap_list(
                    out_root, code, directory.get(code), links.get(code)):
                attempted.add(code)
                counts.reused += 1
                continue
            if not smoke_done:
                continue
            attempted.add(code)
            ok = (download_kap_id(session, code, directory[code], out_root) if code in directory
                  else download_kap_list(session, code, links[code], out_root))
            if ok:
                counts.saved += 1
            else:
                counts.failed += 1
            status(out_root, "kap", "running", counts, session.requests)
        profile_status = out_root / "status/tefas-profiles.json"
        profiles_finished = False
        if profile_status.exists():
            profiles_finished = read_json(profile_status).get("state") in {"complete", "failed", "stopped"}
        status(out_root, "kap", "waiting_for_profiles" if watch and not profiles_finished else "running",
               counts, session.requests)
        if (not watch or profiles_finished or time.monotonic() >= deadline
                or (universe is not None and universe <= attempted)):
            break
        sleep(30)
    return counts


def status(out_root: Path, stage: str, state: str, counts: Counts | None = None,
           requests: int = 0, error_class: str | None = None) -> None:
    record: dict[str, Any] = {"stage": stage, "state": state, "at_utc": utc_now(),
                              "pid": os.getpid(), "requests": requests}
    if counts is not None:
        record.update(asdict(counts))
    if error_class is not None:
        record["error_class"] = error_class
    atomic_json(out_root / "status" / (stage + ".json"), record)


def process_running(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
        kernel.OpenProcess.restype = ctypes.c_void_p
        kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        kernel.WaitForSingleObject.restype = ctypes.c_ulong
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = kernel.OpenProcess(0x00100000, False, pid)
        if not handle:
            if ctypes.get_last_error() == 5:
                raise PermissionError("cannot inspect snapshot process")
            return False
        try:
            return kernel.WaitForSingleObject(handle, 0) == 0x00000102
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


def wait_for_processes(pids: Sequence[int], out_root: Path, *,
                       running: Callable[[int], bool] = process_running,
                       sleep: Callable[[float], None] = time.sleep) -> None:
    while any(running(pid) for pid in pids):
        status(out_root, "tefas", "waiting_for_snapshot")
        sleep(30)


@contextmanager
def host_lock(out_root: Path, host: str) -> Iterator[None]:
    """One stream per public host, including across accidental duplicate launches."""
    path = out_root / "locks" / (host + ".lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def default_out_root() -> Path:
    return Path.home() / ".local/share/project-50k/overnight/2026-10-10"


def validate_out_root(path: Path) -> Path:
    resolved = path.resolve()
    if resolved != default_out_root().resolve():
        raise ValueError("output must be the approved external overnight directory")
    return resolved


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("tefas", "spk", "kap"))
    parser.add_argument("--archive-root", type=Path, required=True)
    parser.add_argument("--out-root", type=Path, default=default_out_root())
    parser.add_argument("--snapshot-db", type=Path)
    parser.add_argument("--wait-pid", nargs="*", type=int, default=[])
    parser.add_argument("--no-existing-collector", action="store_true",
                        help="explicitly assert no legacy TEFAS snapshot collector is running")
    parser.add_argument("--watch-profiles", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "tefas" and not args.wait_pid and not args.no_existing_collector:
        parser.error("TEFAS requires --wait-pid or an explicit --no-existing-collector assertion")
    if any(pid <= 0 for pid in args.wait_pid):
        parser.error("snapshot process IDs must be positive")
    out_root = validate_out_root(args.out_root)
    host = {"tefas": "tefas.gov.tr", "spk": "spk.gov.tr", "kap": "kap.org.tr"}[args.command]
    session = PacedSession(host, 1.5 if args.command == "tefas" else 6,
                           out_root / "logs" / (args.command + "-requests.jsonl"))
    stage = args.command
    try:
        with host_lock(out_root, host):
            status(out_root, stage, "starting")
            if args.command == "tefas":
                wait_for_processes(args.wait_pid, out_root)
                smoke_profiles = download_profiles(session, SMOKE_CODES, out_root)
                if smoke_profiles.failed:
                    raise ResponseError("two-fund profile smoke failed")
                smoke_prices = download_prices(session, SMOKE_CODES, out_root)
                if smoke_prices.failed or smoke_prices.missing:
                    raise ResponseError("two-fund price smoke failed")
                status(out_root, "tefas-smoke", "complete", Counts(saved=4), session.requests)
                codes = archive_codes(args.archive_root, args.snapshot_db)
                stage = "tefas-profiles"
                counts = download_profiles(session, codes, out_root)
                status(out_root, stage, "complete", counts, session.requests)
                stage = "tefas-prices"
                counts = download_prices(session, codes, out_root)
                status(out_root, stage, "complete", counts, session.requests)
                stage = "tefas"
            elif args.command == "spk":
                counts = download_spk(session, out_root)
            else:
                counts = download_kap(session, args.archive_root, out_root,
                                      snapshot_db=args.snapshot_db, watch=args.watch_profiles)
            status(out_root, stage, "complete", counts, session.requests)
            print(json.dumps({"runner": args.command, "state": "complete", **asdict(counts)}), flush=True)
            return 0 if counts.failed == 0 else 1
    except (DownloadStopped, ResponseError, OSError, ValueError, sqlite3.Error) as exc:
        state = "stopped" if isinstance(exc, DownloadStopped) else "failed"
        status(out_root, stage, state, requests=session.requests, error_class=type(exc).__name__)
        if args.command == "tefas" and stage != "tefas-profiles":
            profile_status = out_root / "status/tefas-profiles.json"
            if not profile_status.exists() or read_json(profile_status).get("state") != "complete":
                status(out_root, "tefas-profiles", state, error_class=type(exc).__name__)
        print(json.dumps({"runner": args.command, "state": state, "error_class": type(exc).__name__}), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
