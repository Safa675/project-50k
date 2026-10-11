"""Admit official Borsa Istanbul daily equity bulletins as dated BIST 30 closes (DEC-036).

Each bulletin's rows flagged BIST 30 become that trade date's dated membership and
closes. Availability is the publisher's HTTP Last-Modified captured at download,
checked against the archive's inner CSV timestamp; the capture time is the
conservative fallback. Bulletin files are untrusted data: they are parsed, never
executed, and their bytes must match the capture record.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from email.utils import parsedate_to_datetime
import hashlib
import io
import json
from pathlib import Path
import re
import sys
from typing import Any, Literal
from uuid import uuid4
import zipfile

import psycopg
from psycopg.types.json import Jsonb

from p50k.product.archive import ISTANBUL, canonical_json, timestamp

SOURCE_ID = "borsaistanbul-thb"
SOURCE_VERSION = "thb-v1"
SOURCE_LABEL = "Borsa İstanbul günlük bülteni"
RULE = "thb_http_last_modified_at_capture"
FALLBACK_RULE = "thb_capture_time_fallback"
LOCK = 50_000_038  # Shared with stock_import so stock writes never interleave.
MEMBERS = 30
MAX_ZIP_BYTES = 8*1024*1024
MAX_CSV_BYTES = 32*1024*1024
MAX_JSON_BYTES = 2*1024*1024
MAX_FILES = 400
INNER_TOLERANCE = timedelta(minutes=10)
ZIP_NAME = re.compile(r"^thb([0-9]{8})1\.zip$")
OFFICIAL_URL = re.compile(r"^https://(?:www\.)?borsaistanbul\.com/data/thb/([0-9]{4})/([0-9]{2})/(thb[0-9]{8}1\.zip)$")
SERIES = re.compile(r"^([A-Z][A-Z0-9]{1,11})\.E$")
DECIMAL = re.compile(r"^-?[0-9]{1,15}(?:\.[0-9]{1,8})?$")
COLUMNS = {"trade_date": "TRADE DATE", "series": "INSTRUMENT SERIES CODE", "name": "INSTRUMENT NAME",
           "group": "INSTRUMENT GROUP", "bist30": "BIST 30 INDEX", "suspended": "SUSPENDED",
           "corporate_action": "CORPORATE ACTION", "previous_close": "PREVIOUS LAST PRICE",
           "close": "CLOSING PRICE", "change_pct": "CHANGE TO PREVIOUS CLOSING (%)", "vwap": "VWAP",
           "traded_value": "TOTAL TRADED VALUE", "volume": "TOTAL TRADED VOLUME"}
OPTIONAL_NUMBERS = {"previous_close": False, "change_pct": True, "vwap": False, "traded_value": False, "volume": False}


@dataclass(frozen=True)
class Capture:
    url: str
    status: int
    last_modified: str | None
    captured_at: datetime
    sha256: str
    etag: str | None = None


@dataclass(frozen=True)
class Member:
    symbol: str
    series: str
    name: str
    close: Decimal | None
    fields: dict[str, Any]


@dataclass(frozen=True)
class Bulletin:
    file_name: str
    trade_date: date
    zip_sha256: str
    csv_sha256: str
    available_at: datetime
    availability_rule: str
    inner_timestamp: datetime | None
    inner_consistent: bool
    capture: Capture
    members: tuple[Member, ...]


def number_text(value: str, *, signed: bool=False) -> str | None:
    """Return trimmed decimal text, None when empty or malformed (never a guessed number)."""
    text = value.strip()
    if not text or not DECIMAL.fullmatch(text) or (text.startswith("-") and not signed):
        return None
    return text


def http_time(value: str | None) -> datetime | None:
    if not isinstance(value,str) or not value.strip():
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo is not None else None


def load_capture(entry: Any) -> Capture:
    if not isinstance(entry,dict):
        raise ValueError("Bulletin capture record is not an object")
    url,status,sha = entry.get("url"),entry.get("status"),entry.get("sha256")
    captured = timestamp(entry.get("captured_at") or entry.get("retrieved_at"))
    if not isinstance(url,str) or not isinstance(status,int) or not isinstance(sha,str) or not re.fullmatch(r"[a-f0-9]{64}",sha):
        raise ValueError("Bulletin capture record lacks URL, status or SHA-256")
    if captured is None or captured>datetime.now(timezone.utc):
        raise ValueError("Bulletin capture time is absent or in the future")
    last_modified,etag = entry.get("last_modified"),entry.get("etag")
    return Capture(url=url,status=status,last_modified=last_modified if isinstance(last_modified,str) else None,
                   captured_at=captured.astimezone(timezone.utc),sha256=sha,etag=etag if isinstance(etag,str) else None)


def availability(trade_date: date, capture: Capture, inner: datetime | None) -> tuple[datetime,str,bool]:
    """Last-Modified when consistent with the trade date, inner timestamp and capture; else capture time."""
    published = http_time(capture.last_modified)
    consistent = (published is not None and inner is not None and inner.astimezone(ISTANBUL).date()==trade_date
                  and inner<=published+INNER_TOLERANCE)
    if (not consistent or published.astimezone(ISTANBUL).date()<trade_date or published>capture.captured_at):
        return capture.captured_at,FALLBACK_RULE,consistent
    return published,RULE,True


def read_bulletin(path: Path, capture: Capture) -> Bulletin:
    name = ZIP_NAME.fullmatch(path.name)
    if not name:
        raise ValueError("File is not a session-1 daily bulletin")
    trade_date = datetime.strptime(name[1],"%Y%m%d").date()
    if capture.captured_at.astimezone(ISTANBUL).date()<trade_date:
        raise ValueError("Bulletin capture predates the trade date")
    official = OFFICIAL_URL.fullmatch(capture.url)
    if not official or official[3]!=path.name or (official[1],official[2])!=(f"{trade_date:%Y}",f"{trade_date:%m}"):
        raise ValueError("Bulletin URL does not follow the official path pattern")
    if capture.status!=200:
        raise ValueError("Bulletin capture did not succeed")
    if path.is_symlink() or not path.is_file() or path.stat().st_size>MAX_ZIP_BYTES:
        raise ValueError("Bulletin file is missing or exceeds the size bound")
    data = path.read_bytes()
    zip_sha = hashlib.sha256(data).hexdigest()
    if zip_sha!=capture.sha256:
        raise ValueError("Bulletin bytes differ from the capture record")
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        infos = archive.infolist()
        if len(infos)!=1 or infos[0].filename!=path.name[:-4]+".csv" or infos[0].file_size>MAX_CSV_BYTES:
            raise ValueError("Bulletin archive must hold exactly its own CSV")
        info = infos[0]
        with archive.open(info) as stream:
            raw = stream.read(MAX_CSV_BYTES+1)
    if len(raw)>MAX_CSV_BYTES:
        raise ValueError("Bulletin CSV exceeds the size bound")
    try:
        inner = datetime(*info.date_time,tzinfo=ISTANBUL)
    except ValueError:
        inner = None
    rows = list(csv.reader(io.StringIO(raw.decode("utf-8-sig"),newline=""),delimiter=";"))
    if len(rows)<3:
        raise ValueError("Bulletin CSV has no data rows")
    header = [cell.strip() for cell in rows[1]]
    index = {}
    for key,column in COLUMNS.items():
        if header.count(column)!=1:
            raise ValueError("Bulletin header lacks required column "+column)
        index[key] = header.index(column)
    members: list[Member] = []
    for row in rows[2:]:
        if not any(cell.strip() for cell in row):
            continue
        if len(row)!=len(header):
            raise ValueError("Bulletin row width differs from its header")
        if row[index["trade_date"]].strip()!=trade_date.isoformat():
            raise ValueError("Bulletin row trade date differs from the file date")
        if row[index["bist30"]].strip()!="1":
            continue
        series = SERIES.fullmatch(row[index["series"]].strip())
        if not series or row[index["group"]].strip()!="EQT":
            raise ValueError("BIST 30 row is not an equity series")
        close = number_text(row[index["close"]])
        if close is None:
            raise ValueError("BIST 30 row has no decimal closing price")
        title = " ".join(row[index["name"]].split())
        if not 1<=len(title)<=240:
            raise ValueError("BIST 30 row has no instrument name")
        fields: dict[str,Any] = {key:number_text(row[index[key]],signed=signed) for key,signed in OPTIONAL_NUMBERS.items()}
        suspended = row[index["suspended"]].strip()
        fields["suspended"] = {"0":False,"1":True}.get(suspended)
        fields["corporate_action"] = row[index["corporate_action"]].strip()[:40] or None
        members.append(Member(symbol=series[1],series=series[0],name=title,
                              close=None if Decimal(close)==0 else Decimal(close),fields=fields))
    if len(members)!=MEMBERS or len({member.symbol for member in members})!=MEMBERS:
        raise ValueError("Bulletin must flag exactly 30 distinct BIST 30 equities")
    available,rule,consistent = availability(trade_date,capture,inner)
    return Bulletin(file_name=path.name,trade_date=trade_date,zip_sha256=zip_sha,csv_sha256=hashlib.sha256(raw).hexdigest(),
                    available_at=available,availability_rule=rule,inner_timestamp=inner,inner_consistent=consistent,
                    capture=capture,members=tuple(sorted(members,key=lambda member:member.symbol)))


def read_json(path: Path) -> Any:
    if path.is_symlink() or not path.is_file() or path.stat().st_size>MAX_JSON_BYTES:
        raise ValueError("Capture record is missing or exceeds the size bound")
    return json.loads(path.read_text(encoding="utf-8"))


def read_manifest(path: Path) -> tuple[list[Bulletin],list[dict[str,Any]]]:
    """Validate the whole manifest before admitting any file, keeping documented gaps."""
    manifest = read_json(path)
    entries = manifest.get("entries") if isinstance(manifest,dict) else None
    if not isinstance(entries,list) or len(entries)>MAX_FILES*2:
        raise ValueError("Bulletin manifest has no bounded entry list")
    if manifest.get("source") not in (None,SOURCE_ID):
        raise ValueError("Bulletin manifest names a different source")
    bulletins,gaps = [],[]
    dates: set[date] = set()
    for entry in entries:
        if not isinstance(entry,dict):
            raise ValueError("Bulletin manifest entry is not an object")
        trade_date = date.fromisoformat(entry.get("trade_date", ""))
        if entry.get("trade_date")!=trade_date.isoformat() or trade_date in dates:
            raise ValueError("Bulletin manifest has an invalid or duplicate trade date")
        dates.add(trade_date)
        file_name = entry.get("file")
        if not file_name:
            if entry.get("status")==200:
                raise ValueError("Successful bulletin capture has no file")
            gaps.append({"trade_date":trade_date.isoformat(),"reason":entry.get("skipped") or entry.get("error") or "no file"})
            continue
        if not isinstance(file_name,str) or Path(file_name).name!=file_name or not ZIP_NAME.fullmatch(file_name):
            raise ValueError("Bulletin manifest names an unsafe file")
        bulletin = read_bulletin(path.parent/file_name,load_capture(entry))
        if trade_date!=bulletin.trade_date:
            raise ValueError("Bulletin manifest trade date differs from its file")
        bulletins.append(bulletin)
    if len(bulletins)>MAX_FILES or len({item.file_name for item in bulletins})!=len(bulletins):
        raise ValueError("Bulletin manifest lists too many or duplicate files")
    return sorted(bulletins,key=lambda item:item.trade_date),gaps


def read_folder(folder: Path) -> tuple[list[Bulletin],list[dict[str,Any]]]:
    """Read every captured bulletin listed in folder/manifest.json."""
    return read_manifest(folder/"manifest.json")


def summary(bulletins: list[Bulletin]) -> dict[str,Any]:
    return {"source_id":SOURCE_ID,"source_version":SOURCE_VERSION,"bulletins":len(bulletins),
            "trade_dates":[min(item.trade_date for item in bulletins).isoformat(),max(item.trade_date for item in bulletins).isoformat()] if bulletins else [],
            "rows":sum(len(item.members) for item in bulletins),
            "capture_time_fallbacks":sorted(item.trade_date.isoformat() for item in bulletins if item.availability_rule==FALLBACK_RULE),
            "missing_closes":sum(member.close is None for item in bulletins for member in item.members)}


def import_bulletins(connection: psycopg.Connection, bulletins: list[Bulletin], *,
                     origin: Literal["DELAYED","SYNTHETIC"]="DELAYED") -> dict[str,Any]:
    if origin not in {"DELAYED","SYNTHETIC"}:
        raise ValueError("Bulletin import origin is invalid")
    if not bulletins:
        raise ValueError("No bulletins to import")
    result = summary(bulletins)
    batch = hashlib.sha256(canonical_json(sorted(item.zip_sha256 for item in bulletins)).encode()).hexdigest()
    connection.autocommit = True
    run_id = uuid4()
    connection.execute("INSERT INTO obs.ingest_runs(run_id,archive_sha256,status) VALUES(%s,%s,'RUNNING')",(run_id,batch))
    try:
        with connection.transaction():
            connection.execute("SET LOCAL statement_timeout='60s'")
            connection.execute("SET LOCAL lock_timeout='5s'")
            connection.execute("SELECT pg_advisory_xact_lock(%s)",(LOCK,))
            connection.execute("INSERT INTO ref.sources(source_id,label,metadata) VALUES(%s,%s,%s) ON CONFLICT(source_id) DO NOTHING",
                               (SOURCE_ID,SOURCE_LABEL,Jsonb({"source_version":SOURCE_VERSION,"decision":"DEC-036","rights_status":"UNREVIEWED",
                                                             "path_pattern":"/data/thb/YYYY/MM/thbYYYYMMDD1.zip"})))
            instruments = prices = 0
            with connection.cursor() as cursor:
                for item in sorted(bulletins,key=lambda bulletin:(bulletin.trade_date,bulletin.available_at)):
                    for member in item.members:
                        cursor.execute("""INSERT INTO ref.stock_instruments(symbol,name,exchange,currency,source_id,source_sha256,observed_at,metadata)
                            VALUES(%s,%s,'BIST','TRY',%s,%s,%s,%s) ON CONFLICT(symbol) DO NOTHING""",
                            (member.symbol,member.name,SOURCE_ID,item.zip_sha256,item.available_at,
                             Jsonb({"dated_bulletin_member":True,"current_catalog_only":False,"first_trade_date":item.trade_date.isoformat(),
                                    "series_code":member.series,"source_version":SOURCE_VERSION})))
                        instruments += cursor.rowcount
                        cursor.execute("""INSERT INTO obs.stock_prices(symbol,effective_date,close,source_id,source_sha256,raw_source_sha256,origin,
                                available_at,observed_at,availability_rule,price_adjustment,metadata)
                            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'UNADJUSTED',%s) ON CONFLICT DO NOTHING""",
                            (member.symbol,item.trade_date,member.close,SOURCE_ID,item.zip_sha256,item.csv_sha256,origin,
                             item.available_at,item.available_at,item.availability_rule,
                             Jsonb({**member.fields,"bist30_member":True,"series_code":member.series,"bulletin_name":member.name,
                                    "source_version":SOURCE_VERSION,"decision":"DEC-036","file":item.file_name,"url":item.capture.url,
                                    "http_last_modified":item.capture.last_modified,"etag":item.capture.etag,
                                    "captured_at":item.capture.captured_at.isoformat(),
                                    "inner_csv_timestamp":item.inner_timestamp.isoformat() if item.inner_timestamp else None,
                                    "inner_timestamp_consistent":item.inner_consistent,"close_missing":member.close is None})))
                        prices += cursor.rowcount
            result.update({"inserted_prices":prices,"inserted_instruments":instruments})
            connection.execute("UPDATE obs.ingest_runs SET finished_at=clock_timestamp(),status='SUCCEEDED',counts=%s WHERE run_id=%s",(Jsonb(result),run_id))
    except Exception as error:
        connection.execute("UPDATE obs.ingest_runs SET finished_at=clock_timestamp(),status='FAILED',error_class=%s WHERE run_id=%s",(type(error).__name__,run_id))
        raise
    return {**result,"run_id":str(run_id)}


def main(argv: list[str] | None=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command",required=True)
    command = commands.add_parser("import",help="Validate and admit captured bulletins")
    inputs = command.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--zip",type=Path,help="One bulletin ZIP; requires --capture-json")
    inputs.add_argument("--folder",type=Path,help="Folder holding bulletin ZIPs and manifest.json")
    inputs.add_argument("--manifest",type=Path,help="Manifest whose bulletin ZIPs are in the same folder")
    command.add_argument("--capture-json",type=Path)
    command.add_argument("--dry-run",action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.zip is not None:
            if args.capture_json is None:
                raise ValueError("--zip requires --capture-json")
            bulletins,gaps = [read_bulletin(args.zip,load_capture(read_json(args.capture_json)))],[]
        else:
            if args.capture_json is not None:
                raise ValueError("--capture-json is only valid with --zip")
            bulletins,gaps = read_manifest(args.manifest) if args.manifest is not None else read_folder(args.folder)
        if args.dry_run:
            print(json.dumps({**summary(bulletins),"gaps":gaps,"dry_run":True}))
            return 0
        from p50k.product.db import connect
        from p50k.product.settings import Settings
        with connect(Settings.from_env()) as connection:
            print(json.dumps({**import_bulletins(connection,bulletins),"gaps":gaps}))
        return 0
    except Exception as error:
        print(json.dumps({"error_class":type(error).__name__,"error":str(error)[:200]}),file=sys.stderr)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
