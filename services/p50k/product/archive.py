"""Read the private archive without changing its files or dated observations."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterator

ISTANBUL = timezone(timedelta(hours=3))
PRICE_AVAILABILITY_RULE = "tefas_row_date_1105_istanbul_assumption"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), parse_float=Decimal)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def timestamp(value: str | None) -> datetime | None:
    if value is None:
        return None
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Archive timestamp has no timezone")
    return result


def decimal_value(value: Any, *, positive: bool = False) -> Decimal | None:
    if value is None or value == "":
        return None
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError("Non-finite archive value")
    if positive and result <= 0:
        return None
    return result


def kap_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.strptime(value, "%d.%m.%Y %H:%M:%S").replace(tzinfo=ISTANBUL)


def price_available_at(day: date, price: Decimal | None, retrieved_at: datetime) -> datetime:
    # Missing values cannot be assigned a fabricated historical publication time.
    return (datetime.combine(day, time(11, 5), ISTANBUL) if price is not None else retrieved_at)


@dataclass
class Archive:
    raw_dir: Path
    snapshot_dbs: tuple[Path, ...] = ()
    event_map: Path | None = None
    _hashes: dict[Path, str] = field(default_factory=dict, init=False)
    _manifest: tuple[tuple[str, Path, str], ...] | None = field(default=None, init=False)

    def read(self, path: Path) -> Any:
        payload = path.read_bytes()
        actual = hashlib.sha256(payload).hexdigest()
        if path in self._hashes and self._hashes[path] != actual:
            raise ValueError("Archive input changed after fingerprinting")
        self._hashes[path] = actual
        return json.loads(payload.decode("utf-8"), parse_float=Decimal)

    def digest(self, path: Path) -> str:
        if path not in self._hashes:
            self._hashes[path] = sha256_file(path)
        return self._hashes[path]

    def relative(self, path: Path) -> str:
        return path.relative_to(self.raw_dir).as_posix()

    def input_files(self) -> Iterator[tuple[str, Path]]:
        for pattern in (
            "tefas/responses/fonGetiriBazliBilgiGetir_YAT.body", "tefas/responses/requests.json",
            "tefas/prices/*.json", "kap/series/*.json", "kap/reports/*/kap_report_list.json",
            "kap/reports/kap_portfolio_reports_*.body", "kap/reports/*/*.pdf",
            "spk/*.pdf",
        ):
            for path in sorted(self.raw_dir.glob(pattern)):
                yield self.relative(path), path
        for index, path in enumerate(self.snapshot_dbs):
            yield f"snapshot-input-{index}", path
        if self.event_map:
            yield "spk-event-map", self.event_map

    def fingerprint(self) -> str:
        if self._manifest is not None:
            self.verify_unchanged()
        else:
            self._manifest = tuple((name, path, self.digest(path)) for name, path in self.input_files())
        if not self._manifest:
            raise ValueError("Archive has no inputs")
        pairs = [(name, checksum) for name, _, checksum in self._manifest]
        return hashlib.sha256(canonical_json(pairs).encode("utf-8")).hexdigest()

    def verify_unchanged(self) -> None:
        if self._manifest is None:
            raise ValueError("Archive inventory was not fingerprinted")
        inventory = tuple((name, path) for name, path in self.input_files())
        if inventory != tuple((name, path) for name, path, _ in self._manifest):
            raise ValueError("Archive input inventory changed")
        for _, path, expected in self._manifest:
            if sha256_file(path) != expected:
                raise ValueError("Archive source bytes changed during import")
        for path in self.snapshot_dbs:
            self.check_sqlite_stable(path)

    @staticmethod
    def check_sqlite_stable(path: Path) -> None:
        for suffix in ("-wal", "-journal"):
            sidecar = Path(str(path) + suffix)
            if sidecar.exists() and sidecar.stat().st_size:
                raise ValueError("SQLite input has an active or unreconciled journal")

    def listing(self) -> tuple[list[dict[str, Any]], Path, datetime]:
        path = self.raw_dir / "tefas/responses/fonGetiriBazliBilgiGetir_YAT.body"
        response = self.read(path)
        if response.get("errorCode") is not None:
            raise ValueError("Saved fund listing returned an error")
        rows = response["resultList"]
        requests = self.read(self.raw_dir / "tefas/responses/requests.json")
        # requests.json is either an envelope or the original list of requests.
        entries = requests.get("requests", []) if isinstance(requests, dict) else requests
        matching = [entry for entry in entries if Path(entry.get("raw_file", "")).name == path.name
                    or entry.get("label") == path.stem]
        if len(matching) != 1:
            raise ValueError("Fund listing acquisition metadata is ambiguous")
        acquired = timestamp(matching[0]["requested_at_utc"])
        if acquired is None:
            raise ValueError("Fund listing acquisition time is unknown")
        recorded_hash = matching[0].get("sha256")
        if recorded_hash and recorded_hash != self.digest(path):
            raise ValueError("Fund listing source hash differs")
        codes = [row["fonKodu"] for row in rows]
        if not rows or len(codes) != len(set(codes)):
            raise ValueError("Fund listing is empty or has duplicate codes")
        return rows, path, acquired

    def funds(self) -> Iterator[dict[str, Any]]:
        rows, path, acquired = self.listing()
        for row in rows:
            yield {
                "fund_code": row["fonKodu"], "name": row["fonUnvan"],
                "category": row.get("fonTurAciklama"), "tefas_status": row.get("tefasDurum"),
                "listing_as_of": acquired.date(), "source_id": "tefas-fund-list",
                "source_sha256": self.digest(path),
                "observed_at": acquired,
                "metadata": {"observed_at": acquired.isoformat(), "source_path": self.relative(path),
                             "category_rule": "current_fonTurAciklama_not_dated_membership"},
            }

    def prices(self) -> Iterator[dict[str, Any]]:
        for path in sorted((self.raw_dir / "tefas/prices").glob("*.json")):
            payload = self.read(path)
            acquired = timestamp(payload["retrieved_at"])
            if acquired is None:
                raise ValueError("Price archive acquisition time is unknown")
            seen: set[date] = set()
            for day_text, value in payload["rows"]:
                day = date.fromisoformat(day_text)
                if day > acquired.astimezone(ISTANBUL).date():
                    raise ValueError("Price row date is after archive acquisition")
                if day in seen:
                    raise ValueError("Price archive contains duplicate dates")
                seen.add(day)
                price = decimal_value(value, positive=True)
                available = price_available_at(day, price, acquired)
                if available > acquired:
                    raise ValueError("Price row is dated after archive acquisition")
                yield {
                    "fund_code": payload["fund"], "effective_date": day, "nav": price,
                    "source_id": "tefas-prices", "source_sha256": self.digest(path),
                    "origin": "DELAYED", "available_at": available, "observed_at": acquired,
                    "availability_rule": PRICE_AVAILABILITY_RULE if price is not None
                    else "missing_row_observed_at_archive_acquisition",
                    "metadata": {"source_path": self.relative(path), "periyod": payload["periyod"],
                                 "limitation": "Publication time inferred; historical revisions unverified"},
                }

    def snapshots(self) -> Iterator[dict[str, Any]]:
        for index, path in enumerate(self.snapshot_dbs):
            self.check_sqlite_stable(path)
            uri = path.resolve().as_uri() + "?mode=ro&immutable=1"
            connection = sqlite3.connect(uri, uri=True)
            connection.row_factory = sqlite3.Row
            try:
                for row in connection.execute("SELECT * FROM fund_snapshots ORDER BY fund, retrieved_at"):
                    acquired = timestamp(row["retrieved_at"])
                    if acquired is None:
                        raise ValueError("Snapshot acquisition time is unknown")
                    as_of = date.fromisoformat(row["as_of"]) if row["as_of"] else None
                    if as_of is not None and as_of > acquired.astimezone(ISTANBUL).date():
                        raise ValueError("Snapshot as-of date is after acquisition")
                    price = decimal_value(row["price"], positive=True)
                    if price is None:
                        as_of = None
                    yield {
                        "fund_code": row["fund"], "snapshot_key": row["retrieved_at"],
                        "effective_date": as_of, "nav": price,
                        "total_value": decimal_value(row["total_value"], positive=True),
                        "units_outstanding": decimal_value(row["units_outstanding"], positive=True),
                        "investors": row["investors"],
                        "daily_return_pct": decimal_value(row["daily_return_pct"]),
                        "source_id": "tefas-snapshots", "source_sha256": self.digest(path),
                        "origin": "DELAYED", "available_at": acquired, "observed_at": acquired,
                        "availability_rule": row["as_of_rule"] if as_of else "unknown:undated_snapshot",
                        "metadata": {"source_path": f"snapshot-input-{index}",
                                     "as_of_rule": row["as_of_rule"], "category": row["category"],
                                     "limitation": "Latest-value snapshot; no backfilled history"},
                    }
            finally:
                connection.close()

    def kap_documents(self) -> Iterator[dict[str, Any]]:
        paths = list(sorted((self.raw_dir / "kap/reports").glob("*/kap_report_list.json")))
        paths += list(sorted((self.raw_dir / "kap/reports").glob("kap_portfolio_reports_*.body")))
        seen: set[str] = set()
        for path in paths:
            code = path.parent.name if path.name == "kap_report_list.json" else path.stem.removeprefix("kap_portfolio_reports_")
            for item in self.read(path):
                basic = item["disclosureBasic"]
                disclosure = basic["disclosureIndex"]
                key = f"{code}:{disclosure}"
                if key in seen:
                    continue
                seen.add(key)
                published = kap_timestamp(basic.get("publishDate"))
                period = None
                cadence = "weekly" if basic.get("period") == "HB" else "monthly"
                if basic.get("year") and basic.get("donem"):
                    period = f"{basic['year']}-{'W' if cadence == 'weekly' else ''}{int(basic['donem']):02d}"
                pdfs = sorted((self.raw_dir / "kap/reports" / code).glob(f"*_{disclosure}*.pdf"))
                # An attachment index must end at '_' or '.', never prefix-match another disclosure.
                pdfs = [pdf for pdf in pdfs if pdf.stem.split("_")[1:2] == [str(disclosure)]]
                attachments = [{"path": self.relative(pdf), "sha256": self.digest(pdf)} for pdf in pdfs]
                yield {
                    "document_key": key, "fund_code": code, "report_period": period,
                    "relative_path": attachments[0]["path"] if attachments else None,
                    "source_id": "kap-reports", "source_sha256": self.digest(path),
                    "origin": "DELAYED", "published_at": published, "available_at": published,
                    "availability_rule": "kap_publishDate_istanbul_assumption" if published else "unknown:publication_time",
                    "metadata": {"disclosure_index": disclosure, "cadence": cadence,
                                 "list_path": self.relative(path), "attachments": attachments},
                }

    def kap_series(self) -> Iterator[dict[str, Any]]:
        for path in sorted((self.raw_dir / "kap/series").glob("*.json")):
            payload = self.read(path)
            for report in payload["reports"]:
                code = payload["fund"]
                disclosure = report.get("disclosure_index")
                published = timestamp(report.get("published_at"))
                yield {
                    "fund_code": code, "series_key": str(disclosure) if disclosure is not None else report["period"],
                    "report_period": report["period"], "cadence": report.get("cadence", "monthly"),
                    "document_key": f"{code}:{disclosure}" if disclosure is not None else None,
                    "source_id": "kap-series", "source_sha256": self.digest(path),
                    "origin": "DELAYED", "published_at": published, "available_at": published,
                    "availability_rule": "kap_report_publication" if published else "unknown:publication_time",
                    "metadata": {"source_path": self.relative(path), "report": report},
                }

    def events(self) -> Iterator[dict[str, Any]]:
        if self.event_map is None:
            return
        payload = self.read(self.event_map)
        source_hash = payload["source_sha256"]
        # Confirm the official source PDF is present; the legacy mapping is read-only.
        source_pdfs = list((self.raw_dir / "spk").glob("*.pdf"))
        if not any(self.digest(pdf) == source_hash for pdf in source_pdfs):
            raise ValueError("SPK source PDF does not match mapping provenance")
        bulletin = Path(payload["source"]).stem
        if bulletin != "2026-61":
            raise ValueError("Only the reviewed SPK 2026/61 mapping is supported")
        for fund in payload["funds"]:
            yield {
                "event_id": f"spk:{bulletin}:{fund['code']}", "fund_code": fund["code"],
                "event_type": "SPK_LIQUIDATION_ORDER", "effective_date": date(2026, 9, 17),
                "status": "CANDIDATE", "source_id": "spk-bulletins", "source_sha256": source_hash,
                "origin": "DELAYED", "availability_rule": "unknown:bulletin_publication_time",
                "metadata": {"bulletin_id": bulletin, "source_url": payload["source"],
                             "mapping_method": fund["match"], "mapping_sha256": self.digest(self.event_map),
                             "source_entry": fund["n"], "publication_date": "2026-09-17",
                             "limitation": "Human spot checks pending; publication time unknown"},
            }
