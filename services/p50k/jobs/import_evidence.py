"""Import explicitly selected local fund evidence into an immutable replay bundle.

This job never downloads or discovers files. JSON inputs must use CODE.json names,
and --funds must select a subset of the committed development universe. The target
database must live outside this repository. Real inputs remain rights UNKNOWN.
Synthetic mode additionally requires an explicit SYNTHETIC marker in every input;
SQLite fixtures use evidence_import_metadata(key, value) with origin=SYNTHETIC.
"""
from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Sequence
from zoneinfo import ZoneInfo

from p50k.evidence_store import EvidenceStore, Observation, normalize_timestamp

REPO_ROOT = Path(__file__).resolve().parents[3]
DEVELOPMENT_FUNDS = REPO_ROOT / "research/events/2026-09-17-spk-liquidations/top100_funds.txt"
SOURCE_DATE_ZONE = ZoneInfo("Europe/Istanbul")
KAP_FIELDS = {
    "period_end_price": ("nav", "currency/unit"),
    "previous_period_price": ("previous_period_price", "currency/unit"),
    "total_value": ("total_value", "currency"),
    "units_outstanding": ("units_outstanding", "unit"),
    "period_change_pct": ("period_change_pct", "percent"),
    "cash_in": ("cash_in", "currency"),
    "cash_out": ("cash_out", "currency"),
}
SNAPSHOT_FIELDS = {
    "price": ("nav", "currency/unit"),
    "total_value": ("total_value", "currency"),
    "units_outstanding": ("units_outstanding", "unit"),
    "investors": ("investors", "count"),
    "daily_return_pct": ("daily_return_pct", "percent"),
    "category_rank": ("category_rank", "rank"),
    "category_size": ("category_size", "count"),
    "market_share_pct": ("market_share_pct", "percent"),
}


@dataclass(frozen=True)
class LoadedSource:
    locator: str
    sha256: str
    observations: tuple[Observation, ...]


def select_funds(funds: Sequence[str], *, allowlist_path: Path = DEVELOPMENT_FUNDS) -> frozenset[str]:
    """Validate the requested universe before any source evidence is opened."""
    selected = frozenset(code.upper() for code in funds)
    if not selected or any(not re.fullmatch(r"[A-Z0-9]{3}", code) for code in selected):
        raise ValueError("select at least one valid three-character fund code")
    allowed = frozenset(allowlist_path.read_text(encoding="utf-8").split())
    if not selected <= allowed:
        raise ValueError("requested funds are outside the committed development allowlist")
    return selected


def _input_fund(path: Path, funds: frozenset[str]) -> str:
    code = path.stem.upper()
    if path.suffix.lower() != ".json" or code not in funds:
        raise ValueError("JSON input must be named CODE.json for a selected fund")
    return code


def _json_document(path: Path, funds: frozenset[str], synthetic: bool, source: str) -> tuple[dict, str, str]:
    expected = _input_fund(path, funds)
    raw = path.read_bytes()
    payload = json.loads(raw, parse_float=Decimal)
    if not isinstance(payload, dict) or payload.get("fund") != expected:
        raise ValueError("input fund must match its selected filename")
    if payload.get("source") != source:
        raise ValueError("input source marker does not match the selected loader")
    _origin(payload.get("origin"), synthetic)
    return payload, hashlib.sha256(raw).hexdigest(), expected


def _origin(marker: Any, synthetic: bool) -> str:
    if synthetic:
        if marker != "SYNTHETIC":
            raise ValueError("synthetic mode requires an explicit SYNTHETIC input marker")
        return "SYNTHETIC"
    if marker not in (None, "HISTORICAL_REPLAY"):
        raise ValueError("source origin conflicts with historical replay mode")
    return "HISTORICAL_REPLAY"


def _number(value: Any, *, nav: bool = False) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        raise ValueError("numeric evidence must be decimal text or an exact JSON number")
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("invalid decimal evidence") from exc
    if not number.is_finite():
        raise ValueError("non-finite numeric evidence")
    if nav and number < 0:
        raise ValueError("NAV cannot be negative")
    return None if nav and number == 0 else number


def _timestamp(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("timestamp must be text or unknown")
    return normalize_timestamp(value)


def _currency(metadata: dict) -> str:
    currency = metadata.get("currency")
    if currency is None:
        return "UNKNOWN_CURRENCY"
    if not isinstance(currency, str) or not re.fullmatch(r"[A-Z]{3}", currency):
        raise ValueError("explicit source currency must use a three-letter uppercase code")
    return currency


def _units(fields: dict, currency: str) -> dict[str, str]:
    return {target: unit.replace("currency", currency) for target, unit in fields.values()}


def _currency_limitations(currency: str) -> tuple[str, ...]:
    return ("Source does not establish currency; monetary units remain UNKNOWN_CURRENCY.",) if currency == "UNKNOWN_CURRENCY" else ()


def _day(value: Any) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("source row date must use YYYY-MM-DD")
    return date.fromisoformat(value).isoformat()


def _plain(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_plain(item) for item in value]
    return value


def _version(record: dict) -> str:
    encoded = json.dumps(_plain(record), ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                         allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_price_file(path: Path, *, funds: frozenset[str], imported_at: str,
                    synthetic: bool = False) -> LoadedSource:
    """Preserve source dates; retrieval proves availability only at retrieval."""
    funds = select_funds(tuple(funds))
    path = path.resolve()
    payload, digest, fund = _json_document(path, funds, synthetic, "TEFAS fonFiyatBilgiGetir")
    retrieved = _timestamp(payload.get("retrieved_at"))
    retrieval_day = datetime.fromisoformat(retrieved.replace("Z", "+00:00")).astimezone(SOURCE_DATE_ZONE).date() if retrieved else None
    currency = _currency(payload)
    metadata = _plain({key: value for key, value in payload.items() if key != "rows"})
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise ValueError("price input must contain rows")
    observations = []
    seen = set()
    for row in rows:
        if not isinstance(row, list) or len(row) != 2:
            raise ValueError("price row must contain date and NAV")
        day = _day(row[0])
        if retrieval_day and date.fromisoformat(day) > retrieval_day:
            raise ValueError("source price row is dated after its retrieval")
        if day in seen:
            raise ValueError("duplicate source price date")
        seen.add(day)
        nav = _number(row[1], nav=True)
        observations.append(Observation(
            observation_key=f"tefas:price:{fund}:{day}", fund=fund,
            source_id="TEFAS:fonFiyatBilgiGetir", source_version=_version({"metadata": metadata, "row": row}),
            locator=str(path), origin=_origin(payload.get("origin"), synthetic),
            values={"nav": nav}, units={"nav": f"{currency}/unit"}, effective_at=None, published_at=None,
            available_at=retrieved, observed_at=retrieved, ingested_at=imported_at,
            availability_provenance="OBSERVED" if retrieved else "UNKNOWN",
            rights_status="SYNTHETIC" if synthetic else "UNKNOWN",
            source_timestamps={"row_date": day, "retrieved_at": payload.get("retrieved_at")},
            attributes={"source_metadata": metadata, "source_row_date": day},
            limitations=("Historical publication and valuation instants are unverified; source date is retained without backdating.",
                         "Source row date is interpreted in Europe/Istanbul only for rejecting dates after retrieval.",
                         "Retrieved history can contain revisions; each selected value is known only from retrieval.",
                         *_currency_limitations(currency))
        ))
    return LoadedSource(str(path), digest, tuple(observations))


def load_kap_file(path: Path, *, funds: frozenset[str], imported_at: str,
                  synthetic: bool = False) -> LoadedSource:
    """Current parsed series lacks archived revision evidence; availability is unknown."""
    funds = select_funds(tuple(funds))
    path = path.resolve()
    payload, digest, fund = _json_document(path, funds, synthetic, "KAP Portföy Dağılım Raporu")
    reports = payload.get("reports")
    if not isinstance(reports, list):
        raise ValueError("KAP input must contain reports")
    metadata = _plain({key: value for key, value in payload.items() if key != "reports"})
    observations = []
    seen = set()
    for report in reports:
        if not isinstance(report, dict):
            raise ValueError("KAP report must be an object")
        period, cadence = report.get("period"), report.get("cadence")
        index = report.get("disclosure_index")
        if not isinstance(index, int) or isinstance(index, bool) or index <= 0:
            raise ValueError("KAP report requires a positive disclosure index")
        period_end = None
        if cadence == "monthly" and isinstance(period, str) and re.fullmatch(r"\d{4}-\d{2}", period):
            year, month = map(int, period.split("-"))
            period_end = date(year, month, calendar.monthrange(year, month)[1]).isoformat()
        elif cadence != "weekly" or not isinstance(period, str) or not re.fullmatch(r"\d{4}-W\d{2}", period):
            raise ValueError("KAP period must match its monthly or weekly cadence")
        key = f"kap:report:{fund}:{index}:{period}"
        if key in seen:
            raise ValueError("duplicate KAP disclosure and period")
        seen.add(key)
        values = {target: _number(report.get(field), nav=target in ("nav", "previous_period_price"))
                  for field, (target, _) in KAP_FIELDS.items()}
        currency = _currency({**payload, **report})
        observations.append(Observation(
            observation_key=key, fund=fund, source_id="KAP:portfolio_report",
            source_version=_version({"metadata": metadata, "report": report}), locator=str(path),
            origin=_origin(payload.get("origin"), synthetic), values=values,
            units=_units(KAP_FIELDS, currency),
            effective_at=None, published_at=_timestamp(report.get("published_at")),
            available_at=None, observed_at=None, ingested_at=imported_at,
            availability_provenance="UNKNOWN", rights_status="SYNTHETIC" if synthetic else "UNKNOWN",
            source_timestamps={"period": period, "period_end_date": period_end,
                               "published_at": report.get("published_at")},
            attributes={"source_metadata": metadata, "source_report": _plain(report),
                        "period_end_date": period_end, "source_nav_field": "period_end_price"},
            limitations=("Parsed series selects reports per period and may omit original revisions.",
                         "No archived original revision receipt and hash prove historical availability.",
                         "Source publication timezone was assumed by the earlier KAP parser and is unverified.",
                         "Weekly effective period is ambiguous; no precise effective instant is inferred.",
                         *_currency_limitations(currency))
        ))
    return LoadedSource(str(path), digest, tuple(observations))


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_snapshot_db(path: Path, *, funds: frozenset[str], imported_at: str,
                     synthetic: bool = False) -> LoadedSource:
    """Select only approved funds from a read-only, unchanged SQLite source."""
    funds = select_funds(tuple(funds))
    path = path.resolve()
    wal = Path(f"{path}-wal")
    if wal.exists() and wal.stat().st_size:
        raise ValueError("snapshot source has an uncheckpointed WAL; use a separate consistent backup")
    digest = _file_digest(path)
    db = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        db.execute("PRAGMA query_only = ON")
        db.execute("BEGIN")
        marker = None
        has_metadata = db.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'evidence_import_metadata'").fetchone()
        if has_metadata:
            row = db.execute("SELECT value FROM evidence_import_metadata WHERE key = 'origin'").fetchone()
            marker = row[0] if row else None
        origin = _origin(marker, synthetic)
        placeholders = ",".join("?" for _ in funds)
        rows = db.execute(f"SELECT * FROM fund_snapshots WHERE fund IN ({placeholders}) ORDER BY fund, retrieved_at",
                          tuple(sorted(funds))).fetchall()
        observations = []
        for row in rows:
            record = dict(row)
            fund, retrieved_source = record["fund"], record["retrieved_at"]
            retrieved = _timestamp(retrieved_source)
            as_of = None if record.get("as_of") is None else _day(record["as_of"])
            values = {target: _number(record.get(field), nav=target == "nav")
                      for field, (target, _) in SNAPSHOT_FIELDS.items()}
            currency = _currency(record)
            # SQLite REAL is diagnostic metadata, not a recovered exact-decimal observation.
            if isinstance(record.get("units_x_price_vs_total_rel_diff"), float):
                record["units_x_price_vs_total_rel_diff"] = str(record["units_x_price_vs_total_rel_diff"])
            observations.append(Observation(
                observation_key=f"tefas:snapshot:{fund}:{retrieved_source}", fund=fund,
                source_id="TEFAS:fonBilgiGetir", source_version=_version(record), locator=str(path), origin=origin,
                values=values, units=_units(SNAPSHOT_FIELDS, currency),
                effective_at=None, published_at=None, available_at=retrieved, observed_at=retrieved,
                ingested_at=imported_at, availability_provenance="OBSERVED" if retrieved else "UNKNOWN",
                rights_status="SYNTHETIC" if synthetic else "UNKNOWN",
                source_timestamps={"retrieved_at": retrieved_source, "as_of": as_of},
                attributes={"source_row": record, "inferred_price_as_of": as_of,
                            "as_of_rule": record.get("as_of_rule")},
                limitations=("Snapshot fields are latest-only; inferred price as-of does not backdate category, investors or other fields.",
                             "Exact source publication and economic effective instants are unknown.",
                             *_currency_limitations(currency))
            ))
    finally:
        db.close()
    if digest != _file_digest(path) or (wal.exists() and wal.stat().st_size):
        raise ValueError("snapshot source changed while being read")
    return LoadedSource(str(path), digest, tuple(observations))


def _validate_output(out: Path, inputs: Sequence[Path], *, repo_root: Path = REPO_ROOT) -> Path:
    target = out.resolve()
    if target.is_relative_to(repo_root.resolve()):
        raise ValueError("evidence database must live outside the repository")
    for source in inputs:
        if target == source.resolve() or (target.exists() and source.exists() and target.samefile(source)):
            raise ValueError("evidence database must not overwrite a source input")
    return target


def import_files(*, price_files: Sequence[Path] = (), kap_files: Sequence[Path] = (),
                 snapshot_db: Path | None = None, out: Path, funds: Sequence[str],
                 imported_at: str, synthetic: bool = False) -> str:
    """Load all selected inputs before one all-or-none bundle transaction."""
    selected = select_funds(funds)
    imported_at = normalize_timestamp(imported_at)
    inputs = [*price_files, *kap_files, *([snapshot_db] if snapshot_db else [])]
    if not inputs:
        raise ValueError("select at least one explicit source input")
    target = _validate_output(out, inputs)
    for path in (*price_files, *kap_files):
        _input_fund(path, selected)
    resolved = [path.resolve() for path in inputs]
    if len(set(resolved)) != len(resolved):
        raise ValueError("each source input must be supplied only once")
    loaded = [load_price_file(path, funds=selected, imported_at=imported_at, synthetic=synthetic)
              for path in price_files]
    loaded.extend(load_kap_file(path, funds=selected, imported_at=imported_at, synthetic=synthetic)
                  for path in kap_files)
    if snapshot_db:
        loaded.append(load_snapshot_db(snapshot_db, funds=selected, imported_at=imported_at, synthetic=synthetic))
    store = EvidenceStore(target)
    try:
        return store.import_bundle(
            [observation for source in loaded for observation in source.observations],
            sources={source.locator: source.sha256 for source in loaded}, imported_at=imported_at,
            config={"importer": "fund-local-v1", "funds": sorted(selected),
                    "origin": "SYNTHETIC" if synthetic else "HISTORICAL_REPLAY"})
    finally:
        store.close()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--price-file", type=Path, action="append", default=[])
    parser.add_argument("--kap-file", type=Path, action="append", default=[])
    parser.add_argument("--snapshot-db", type=Path)
    parser.add_argument("--out", type=Path, required=True, help="target SQLite database outside the repository")
    parser.add_argument("--funds", nargs="+", required=True, help="explicit committed development-universe subset")
    parser.add_argument("--synthetic", action="store_true", help="requires explicit SYNTHETIC source markers")
    args = parser.parse_args(argv)
    try:
        bundle = import_files(price_files=args.price_file, kap_files=args.kap_file, snapshot_db=args.snapshot_db,
                              out=args.out, funds=args.funds, synthetic=args.synthetic,
                              imported_at=datetime.now(timezone.utc).isoformat())
    except (ValueError, OSError, sqlite3.Error) as exc:
        parser.error(str(exc))
    print(bundle)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
