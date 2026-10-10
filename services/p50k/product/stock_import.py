"""Verify an external BIST30 manifest and append close/action observations.

All dates use capture-time availability until provider publication times are
independently verified. The importer never recalibrates fund detectors.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Annotated, Any, Literal
from uuid import uuid4

import psycopg
from psycopg.types.json import Jsonb
from pydantic import BaseModel, ConfigDict, Field, JsonValue

from p50k.product.archive import ISTANBUL, canonical_json, sha256_file, timestamp

MAX_MANIFEST_BYTES = 8*1024*1024
RULE = "stock_observed_at_provider_capture_no_historical_publication_inference"
LOCK = 50_000_038
Symbol = Annotated[str,Field(pattern=r"^[A-Z][A-Z0-9]{1,11}$")]
Checksum = Annotated[str,Field(pattern=r"^[a-f0-9]{64}$")]


class InputContract(BaseModel):
    model_config = ConfigDict(extra="forbid",strict=True)


class InstrumentInput(InputContract):
    symbol: Symbol
    name: str = Field(min_length=1,max_length=240)
    exchange: Literal["BIST"]
    currency: Literal["TRY"]


class RawSourceInput(InputContract):
    path: str = Field(min_length=1,max_length=240)
    sha256: Checksum


class PriceInput(InputContract):
    symbol: Symbol
    date: str
    close: str | None
    raw_source_sha256: Checksum | None = None


class ActionInput(InputContract):
    symbol: Symbol
    date: str
    kind: Literal["PROVIDER_CORPORATE_ACTION"]
    payload: dict[str,JsonValue]
    raw_source_sha256: Checksum | None = None


class StockManifest(InputContract):
    version: Literal["bist-daily-v1"]
    captured_at: str
    universe: Literal["XU030"]
    source: Literal["forinvest"]
    capture_kind: Literal["MCP_STRUCTURED_RESPONSE","SYNTHETIC_TEST"]
    normalization_version: str = Field(min_length=1,max_length=160)
    instruments: list[InstrumentInput] = Field(min_length=1,max_length=30)
    prices: list[PriceInput] = Field(max_length=21930)
    corporate_actions: list[ActionInput] = Field(max_length=3000)
    raw_sources: list[RawSourceInput] = Field(min_length=1,max_length=100)
    provider_adjustment: Literal["UNVERIFIED","UNADJUSTED","ADJUSTED"] = "UNVERIFIED"


def stock_decimal(value: str | None, *, zero_missing: bool=True) -> Decimal | None:
    if value is None:
        return None
    if not isinstance(value,str) or not re.fullmatch(r"[+-]?(?:[0-9]+)(?:\.[0-9]+)?",value):
        raise ValueError("Stock decimal must be explicit decimal text")
    try:
        result = Decimal(value)
    except InvalidOperation:
        raise ValueError("Stock decimal is invalid") from None
    if not result.is_finite() or result<0:
        raise ValueError("Stock value must be finite and nonnegative")
    return None if zero_missing and result==0 else result


def verify_manifest(path: Path, *, now: datetime | None=None) -> tuple[StockManifest,str,datetime]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size>MAX_MANIFEST_BYTES:
        raise ValueError("Stock manifest is missing or exceeds size bound")
    sidecar = Path(str(path)+".sha256")
    if sidecar.is_symlink() or not sidecar.is_file():
        raise ValueError("Stock manifest hash sidecar is missing")
    checksum = sidecar.read_text(encoding="ascii").strip()
    if not re.fullmatch(r"[a-f0-9]{64}",checksum):
        raise ValueError("Stock manifest hash sidecar is invalid")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest()!=checksum:
        raise ValueError("Stock manifest checksum differs")
    manifest = StockManifest.model_validate_json(data)
    captured = timestamp(manifest.captured_at)
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None or captured is None or captured>now:
        raise ValueError("Stock capture time is absent or in the future")
    codes = {row.symbol for row in manifest.instruments}
    if len(codes)!=len(manifest.instruments) or any(not row.name.strip() for row in manifest.instruments):
        raise ValueError("Stock catalog has duplicate identities or blank names")
    raw_hashes = set()
    for raw in manifest.raw_sources:
        candidate = path.parent / raw.path
        if candidate.is_symlink() or Path(raw.path).is_absolute() or ".." in Path(raw.path).parts:
            raise ValueError("Raw stock source path is unsafe")
        candidate.resolve().relative_to(path.parent.resolve())
        if not candidate.is_file() or sha256_file(candidate)!=raw.sha256:
            raise ValueError("Captured provider response bytes do not match stock provenance")
        raw_hashes.add(raw.sha256)
    price_keys = set()
    for price in manifest.prices:
        day = date.fromisoformat(price.date)
        if price.symbol not in codes or day>captured.astimezone(ISTANBUL).date():
            raise ValueError("Stock price identity/date exceeds capture boundary")
        key = price.symbol,day
        if key in price_keys:
            raise ValueError("Stock manifest contains duplicate daily closes")
        price_keys.add(key)
        stock_decimal(price.close)
        if price.raw_source_sha256 is not None and price.raw_source_sha256 not in raw_hashes:
            raise ValueError("Stock price refers to unverified provider bytes")
    action_keys = set()
    for action in manifest.corporate_actions:
        day = date.fromisoformat(action.date)
        identity = hashlib.sha256(canonical_json(action.payload).encode()).hexdigest()
        if action.symbol not in codes or (action.symbol,day,identity) in action_keys:
            raise ValueError("Stock action identity is absent or duplicated")
        action_keys.add((action.symbol,day,identity))
        if len(canonical_json(action.payload).encode())>16384:
            raise ValueError("Raw stock action payload exceeds size bound")
        if action.raw_source_sha256 is not None and action.raw_source_sha256 not in raw_hashes:
            raise ValueError("Stock action refers to unverified provider bytes")
    if len(raw_hashes)>1 and any(row.raw_source_sha256 is None for row in [*manifest.prices,*manifest.corporate_actions]):
        raise ValueError("Each observation must select its verified raw source")
    return manifest,checksum,captured


def import_stocks(connection: psycopg.Connection, path: Path, *, now: datetime | None=None,
                  dry_run: bool=False, origin: Literal["DELAYED","SYNTHETIC"]="DELAYED") -> dict[str,Any]:
    manifest,checksum,captured = verify_manifest(path,now=now)
    if origin not in {"DELAYED","SYNTHETIC"}:
        raise ValueError("Stock import origin is invalid")
    if manifest.capture_kind=="SYNTHETIC_TEST" and origin!="SYNTHETIC":
        raise ValueError("Synthetic stock captures require synthetic origin")
    raw_default = manifest.raw_sources[0].sha256
    summary: dict[str,Any] = {"manifest_sha256":checksum,"instruments":len(manifest.instruments),
                            "prices":len(manifest.prices),"corporate_actions":len(manifest.corporate_actions),
                            "raw_sources":len(manifest.raw_sources),"captured_at":captured.isoformat(),
                            "universe":"BIST30_CURRENT_CATALOG","provider_adjustment":manifest.provider_adjustment,
                            "capture_kind":manifest.capture_kind,"normalization_version":manifest.normalization_version}
    if dry_run:
        return {**summary,"dry_run":True}
    connection.autocommit = True
    run_id = uuid4()
    connection.execute("INSERT INTO obs.ingest_runs(run_id,archive_sha256,status) VALUES(%s,%s,'RUNNING')",(run_id,checksum))
    try:
        with connection.transaction():
            connection.execute("SET LOCAL statement_timeout='30s'")
            connection.execute("SET LOCAL lock_timeout='5s'")
            connection.execute("SELECT pg_advisory_xact_lock(%s)",(LOCK,))
            latest = connection.execute("SELECT captured_at,catalog_sha256 FROM ref.stock_catalogs ORDER BY captured_at DESC,catalog_sha256 DESC LIMIT 1").fetchone()
            if latest and latest[0]>captured:
                raise ValueError("Older stock capture cannot replace the current catalog")
            if latest and latest[0]==captured and latest[1]!=checksum:
                raise ValueError("Conflicting stock catalog captures share the same acquisition time")
            for instrument in manifest.instruments:
                connection.execute("""INSERT INTO ref.stock_instruments
                    (symbol,name,exchange,currency,source_id,source_sha256,observed_at,metadata)
                    VALUES(%s,%s,'BIST','TRY','forinvest',%s,%s,%s)
                    ON CONFLICT(symbol) DO UPDATE SET name=EXCLUDED.name,
                        source_sha256=EXCLUDED.source_sha256,observed_at=EXCLUDED.observed_at,
                        metadata=EXCLUDED.metadata WHERE ref.stock_instruments.observed_at<=EXCLUDED.observed_at""",
                    (instrument.symbol,instrument.name.strip(),checksum,captured,
                     Jsonb({"current_catalog_only":True,"universe":"XU030","capture_kind":manifest.capture_kind})))
            connection.execute("INSERT INTO ref.stock_catalogs(catalog_sha256,universe,captured_at,symbols,source_id,metadata) VALUES(%s,'XU030',%s,%s,'forinvest',%s) ON CONFLICT DO NOTHING",
                (checksum,captured,[item.symbol for item in manifest.instruments],
                 Jsonb({"rights_status":"UNREVIEWED","membership_rule":"CURRENT_CATALOG_NO_HISTORICAL_MEMBERSHIP","capture_kind":manifest.capture_kind,"normalization_version":manifest.normalization_version})))
            price_count=action_count=missing=0
            with connection.cursor() as cursor:
                cursor.execute("CREATE TEMP TABLE stock_price_stage(LIKE obs.stock_prices INCLUDING DEFAULTS) ON COMMIT DROP")
                fields = "symbol,effective_date,close,source_id,source_sha256,raw_source_sha256,origin,available_at,observed_at,availability_rule,price_adjustment,metadata"
                with cursor.copy("COPY stock_price_stage("+fields+") FROM STDIN") as copy:
                    for price in manifest.prices:
                        close=stock_decimal(price.close)
                        missing+=close is None
                        copy.write_row((price.symbol,date.fromisoformat(price.date),close,"forinvest",checksum,
                                        price.raw_source_sha256 or raw_default,origin,captured,captured,RULE,
                                        manifest.provider_adjustment,Jsonb({"manifest_version":"bist-daily-v1","historical_publication_unverified":True,"capture_kind":manifest.capture_kind,"normalization_version":manifest.normalization_version})))
                cursor.execute("INSERT INTO obs.stock_prices("+fields+") SELECT "+fields+" FROM stock_price_stage ON CONFLICT DO NOTHING")
                price_count=cursor.rowcount
                for action in manifest.corporate_actions:
                    event_id=hashlib.sha256(canonical_json({"symbol":action.symbol,"date":action.date,"payload":action.payload}).encode()).hexdigest()
                    cursor.execute("""INSERT INTO obs.stock_actions(symbol,event_id,action_type,effective_date,factor,cash_amount,source_id,source_sha256,raw_source_sha256,origin,available_at,observed_at,metadata)
                        VALUES(%s,%s,%s,%s,%s,%s,'forinvest',%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                        (action.symbol,event_id,"OTHER",date.fromisoformat(action.date),
                         None,None,checksum,
                         action.raw_source_sha256 or raw_default,origin,captured,captured,
                         Jsonb({"kind":action.kind,"provider_payload":action.payload,"coverage":"UNREVIEWED","interpretation":"NOT_INTERPRETED","capture_kind":manifest.capture_kind})))
                    action_count+=cursor.rowcount
            # Recheck immutable selected source bytes before committing the batch.
            verified,after,_ = verify_manifest(path,now=now)
            if after!=checksum or verified!=manifest:
                raise ValueError("Stock manifest changed during import")
            summary.update({"inserted_prices":price_count,"inserted_actions":action_count,"missing_prices":missing})
            connection.execute("UPDATE obs.ingest_runs SET finished_at=clock_timestamp(),status='SUCCEEDED',counts=%s WHERE run_id=%s",(Jsonb(summary),run_id))
    except Exception as error:
        connection.execute("UPDATE obs.ingest_runs SET finished_at=clock_timestamp(),status='FAILED',error_class=%s WHERE run_id=%s",(type(error).__name__,run_id))
        raise
    return {**summary,"run_id":str(run_id)}


def seed_browser_stock(settings) -> dict[str,Any]:
    """Seed only the isolated synthetic browser database; never the real catalog."""
    if settings.db_name!="p50k_dev" or settings.db_user!="p50k_owner":
        raise ValueError("Synthetic stock browser seed requires isolated p50k_dev owner")
    from datetime import timedelta
    from p50k.product.db import connect
    captured=datetime.now(timezone.utc)
    day=captured.astimezone(ISTANBUL).date()
    with TemporaryDirectory() as folder:
        root=Path(folder)
        raw=root/"synthetic-response.json"
        raw.write_text('{"synthetic":true}',encoding="utf-8",newline="\n")
        raw_hash=sha256_file(raw)
        payload={"version":"bist-daily-v1","captured_at":captured.isoformat(),"universe":"XU030","source":"forinvest",
                 "capture_kind":"SYNTHETIC_TEST","normalization_version":"synthetic-browser-v1","provider_adjustment":"UNVERIFIED",
                 "instruments":[{"symbol":"TESTA","name":"Synthetic browser stock","exchange":"BIST","currency":"TRY"}],
                 "prices":[{"symbol":"TESTA","date":(day-timedelta(days=3-i)).isoformat(),"close":value,"raw_source_sha256":raw_hash}
                           for i,value in enumerate(("100",None,"102"))],
                 "corporate_actions":[],"raw_sources":[{"path":raw.name,"sha256":raw_hash}]}
        path=root/"manifest.json"
        path.write_text(json.dumps(payload),encoding="utf-8",newline="\n")
        Path(str(path)+".sha256").write_text(sha256_file(path),encoding="ascii",newline="\n")
        with connect(settings) as connection:
            return import_stocks(connection,path,origin="SYNTHETIC")


def main(argv: list[str] | None=None) -> int:
    parser=argparse.ArgumentParser(description=__doc__.splitlines()[0])
    inputs=parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--manifest",type=Path)
    inputs.add_argument("--seed-synthetic-browser",action="store_true")
    parser.add_argument("--dry-run",action="store_true")
    args=parser.parse_args(argv)
    try:
        if args.seed_synthetic_browser:
            from p50k.product.settings import Settings
            print(json.dumps(seed_browser_stock(Settings.from_env())))
        elif args.dry_run:
            manifest,checksum,captured=verify_manifest(args.manifest)
            print(json.dumps({"manifest_sha256":checksum,"instruments":len(manifest.instruments),"prices":len(manifest.prices),"corporate_actions":len(manifest.corporate_actions),"captured_at":captured.isoformat(),"dry_run":True}))
        else:
            from p50k.product.db import connect
            from p50k.product.settings import Settings
            with connect(Settings.from_env()) as connection:
                print(json.dumps(import_stocks(connection,args.manifest)))
        return 0
    except Exception as error:
        print(json.dumps({"error_class":type(error).__name__}),file=sys.stderr)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
