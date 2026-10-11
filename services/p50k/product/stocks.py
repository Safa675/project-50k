"""Bounded BIST30 catalog and point-in-time daily close reads.

A retrospective view lists the dated BIST 30 membership of the latest official
Borsa Istanbul daily bulletin available at its cutoff (DEC-036); the live view
keeps the current ForInvest catalog. Where both sources hold a close for the same
day, the official bulletin is preferred and every value names its source.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any, Literal

from psycopg import Connection
from psycopg.rows import dict_row
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, JsonValue

from p50k.product.archive import ISTANBUL
from p50k.product.queries import decimal_text

Symbol = Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9]{1,11}$")]
DecimalText = Annotated[str, Field(pattern=r"^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")]
SignedDecimalText = Annotated[str, Field(pattern=r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")]
Checksum = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
SourceId = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9-]{0,39}$")]
BULLETIN_SOURCE = "borsaistanbul-thb"


class StockContract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class StockProvenance(StockContract):
    data_mode: Literal["DELAYED"] = "DELAYED"
    rights_status: Literal["UNREVIEWED"] = "UNREVIEWED"
    universe: Literal["BIST30_CURRENT_CATALOG", "BIST30_DATED_BULLETIN"] = "BIST30_CURRENT_CATALOG"
    metadata_current_only: bool = True
    development_result: Literal[True] = True


class StockInstrument(StockContract):
    symbol: Symbol
    name: str
    exchange: Literal["BIST"] = "BIST"
    currency: Literal["TRY"] = "TRY"


class BulletinFields(StockContract):
    """Values only the official bulletin reports; None when absent or from another source."""
    previous_close: DecimalText | None = None
    change_pct: SignedDecimalText | None = None
    volume: DecimalText | None = None
    traded_value: DecimalText | None = None


class StockListing(StockInstrument, BulletinFields):
    last_date: date | None
    last_close: DecimalText | None
    source_id: SourceId | None = None
    available_at: AwareDatetime | None = None


class StocksPage(StockProvenance):
    items: list[StockListing] = Field(max_length=30)
    total: int = Field(ge=0, le=30)
    limit: int = Field(ge=1, le=30)
    offset: int = Field(ge=0, le=30)
    catalog_captured_at: AwareDatetime | None
    membership_date: date | None = None
    membership_available_at: AwareDatetime | None = None
    membership_source_sha256: Checksum | None = None


class StockPricePoint(BulletinFields):
    effective_date: date
    close: DecimalText | None
    available_at: AwareDatetime
    source_sha256: Checksum
    ambiguous_revision: bool
    source_id: SourceId | None = None


class StockChart(StockContract):
    cadence: Literal["DAILY_CLOSE"] = "DAILY_CLOSE"
    start_date: date
    end_date: date
    cutoff: AwareDatetime
    points: list[StockPricePoint] = Field(max_length=731)
    missing_dates: Literal["ABSENT_OBSERVATIONS"] = "ABSENT_OBSERVATIONS"


class StockAction(StockContract):
    event_id: str
    effective_date: date
    kind: Literal["PROVIDER_CORPORATE_ACTION"] = "PROVIDER_CORPORATE_ACTION"
    payload: dict[str,JsonValue]
    available_at: AwareDatetime
    source_sha256: Checksum


class StockDetail(StockProvenance):
    stock: StockInstrument
    chart: StockChart
    signals: list[dict[str, Any]] = Field(default_factory=list)
    price_adjustment: Literal["UNVERIFIED", "UNADJUSTED", "ADJUSTED", "MIXED"]
    corporate_actions_status: Literal["UNREVIEWED"] = "UNREVIEWED"
    corporate_actions: list[StockAction] = Field(default_factory=list,max_length=100)
    corporate_actions_total: int = Field(default=0,ge=0)
    cutoff: AwareDatetime
    dated_member_on: date | None = None


CATALOG_CTE = """WITH catalog AS (
    SELECT symbols,captured_at FROM ref.stock_catalogs
    ORDER BY captured_at DESC,catalog_sha256 DESC LIMIT 1
), members AS (
    SELECT instrument.symbol,instrument.name,instrument.exchange,instrument.currency
    FROM ref.stock_instruments instrument JOIN catalog ON instrument.symbol=ANY(catalog.symbols)
)"""
PRICE_SQL = """
    WITH eligible AS (
        SELECT effective_date,close,available_at,observed_at,source_sha256,price_adjustment,
source_id,metadata,
            dense_rank() OVER(PARTITION BY effective_date
                ORDER BY (source_id='borsaistanbul-thb') DESC,available_at DESC,observed_at DESC) priority
        FROM obs.stock_prices WHERE symbol=%s AND effective_date BETWEEN %s AND %s
            AND available_at<=%s
    ), latest AS (SELECT * FROM eligible WHERE priority=1), conflicts AS (
        SELECT effective_date,(count(DISTINCT close)>1 OR
            (count(close)>0 AND count(close)<count(*))) ambiguous_revision
        FROM latest GROUP BY effective_date
    ) SELECT DISTINCT ON(latest.effective_date) latest.effective_date,
        CASE WHEN conflicts.ambiguous_revision THEN NULL::numeric ELSE latest.close END AS close,
        latest.available_at,latest.source_sha256,conflicts.ambiguous_revision,latest.price_adjustment,
        latest.source_id,latest.metadata
      FROM latest JOIN conflicts USING(effective_date)
      ORDER BY latest.effective_date,latest.source_sha256 DESC
"""
BULLETIN_CTE = """WITH bulletin AS (
    SELECT effective_date,source_sha256,available_at FROM obs.stock_prices
    WHERE source_id='borsaistanbul-thb' AND available_at<=%s
    ORDER BY effective_date DESC,available_at DESC,source_sha256 DESC LIMIT 1
), members AS (
    SELECT price.symbol,COALESCE(NULLIF(price.metadata->>'bulletin_name',''),instrument.name) AS name,
        instrument.exchange,instrument.currency,price.effective_date,price.close,price.available_at,
        price.source_id,price.metadata,price.source_sha256
    FROM obs.stock_prices price JOIN bulletin USING(effective_date,source_sha256,available_at)
    JOIN ref.stock_instruments instrument USING(symbol)
    WHERE price.source_id='borsaistanbul-thb'
)"""
ACTION_CTE = """WITH eligible AS (
    SELECT DISTINCT ON(event_id) event_id,effective_date,available_at,source_sha256,metadata
    FROM obs.stock_actions WHERE symbol=%s AND effective_date BETWEEN %s AND %s AND available_at<=%s
    ORDER BY event_id,available_at DESC,observed_at DESC,source_sha256 DESC
)"""


class StockQueries:
    def __init__(self, connection: Connection):
        self.connection = connection

    def _rows(self, statement: str, parameters: tuple[Any, ...]) -> list[dict[str, Any]]:
        with self.connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(statement, parameters)
            return cursor.fetchall()

    def stocks(self, query: str, limit: int, offset: int, cutoff: datetime, *, dated: bool=False) -> StocksPage:
        """Current catalog, or in a retrospective view the dated bulletin membership at the cutoff."""
        term = "%" + query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        where = " WHERE symbol ILIKE %s OR name ILIKE %s"
        captured = self._rows(CATALOG_CTE + "SELECT captured_at FROM catalog", ()) if not dated else []
        catalog_captured_at = captured[0]["captured_at"] if captured else None
        bulletin = self._rows(BULLETIN_CTE + "SELECT * FROM bulletin", (cutoff,)) if dated else []
        if bulletin:
            total = self._rows(BULLETIN_CTE + "SELECT count(*) total FROM members" + where, (cutoff, term, term))[0]["total"]
            rows = self._rows(BULLETIN_CTE + "SELECT * FROM members" + where + " ORDER BY symbol LIMIT %s OFFSET %s",
                              (cutoff, term, term, limit, offset))
            items = [StockListing(symbol=row["symbol"], name=row["name"], last_date=row["effective_date"],
                                  last_close=decimal_text(row["close"]), source_id=row["source_id"],
                                  available_at=row["available_at"], **bulletin_fields(row["metadata"], row["source_id"]))
                     for row in rows]
            return StocksPage(items=items, total=total, limit=limit, offset=offset, universe="BIST30_DATED_BULLETIN",
                              metadata_current_only=False, catalog_captured_at=catalog_captured_at,
                              membership_date=bulletin[0]["effective_date"], membership_available_at=bulletin[0]["available_at"],
                              membership_source_sha256=bulletin[0]["source_sha256"])
        if dated:
            return StocksPage(items=[], total=0, limit=limit, offset=offset, universe="BIST30_DATED_BULLETIN",
                              metadata_current_only=False, catalog_captured_at=None)
        total = self._rows(CATALOG_CTE + "SELECT count(*) total FROM members" + where, (term, term))[0]["total"]
        members = self._rows(CATALOG_CTE + "SELECT * FROM members" + where + " ORDER BY symbol LIMIT %s OFFSET %s", (term, term, limit, offset))
        statement = PRICE_SQL.replace("latest.effective_date,latest.source_sha256 DESC", "latest.effective_date DESC,latest.source_sha256 DESC") + " LIMIT 1"
        items = []
        for member in members:
            rows = self._rows(statement, (member["symbol"], date.min, cutoff.astimezone(ISTANBUL).date(), cutoff))
            latest = rows[0] if rows else None
            extra = {"source_id": latest["source_id"], "available_at": latest["available_at"],
                     **bulletin_fields(latest["metadata"], latest["source_id"])} if latest and not latest["ambiguous_revision"] else {}
            items.append(StockListing(**member, last_date=latest["effective_date"] if latest else None,
                                      last_close=decimal_text(latest["close"]) if latest else None, **extra))
        return StocksPage(items=items, total=total, limit=limit, offset=offset, catalog_captured_at=catalog_captured_at)

    def stock(self, symbol: str, cutoff: datetime | None=None, *, dated: bool=False) -> StockInstrument | None:
        """A member of the current catalog or the latest eligible dated bulletin."""
        if dated:
            if cutoff is None:
                raise ValueError("Dated membership requires an availability cutoff")
            rows = self._rows(BULLETIN_CTE + "SELECT symbol,name,exchange,currency FROM members WHERE symbol=%s", (cutoff, symbol))
            return StockInstrument(**rows[0]) if rows else None
        rows = self._rows(CATALOG_CTE + "SELECT * FROM members WHERE symbol=%s", (symbol,))
        return StockInstrument(**rows[0]) if rows else None

    def detail(self, stock: StockInstrument, start: date, end: date, cutoff: datetime, *, dated: bool=False) -> StockDetail:
        rows = self._rows(PRICE_SQL, (stock.symbol, start, end, cutoff))
        adjustments = {row.pop("price_adjustment") for row in rows}
        points = []
        for row in rows:
            metadata = row.pop("metadata")
            fields = bulletin_fields(metadata, row["source_id"]) if not row["ambiguous_revision"] else {}
            points.append(StockPricePoint(**{**row, "close": decimal_text(row["close"]), **fields}))
        adjustment = next(iter(adjustments)) if len(adjustments)==1 else "MIXED" if adjustments else "UNVERIFIED"
        member = self._rows(BULLETIN_CTE + "SELECT effective_date FROM members WHERE symbol=%s", (cutoff, stock.symbol))
        args=(stock.symbol,start,end,cutoff)
        total=self._rows(ACTION_CTE+"SELECT count(*) total FROM eligible",args)[0]["total"]
        action_rows=self._rows(ACTION_CTE+"SELECT * FROM eligible ORDER BY effective_date DESC,event_id LIMIT 100",args)
        actions=[StockAction(event_id=row["event_id"],effective_date=row["effective_date"],
                             available_at=row["available_at"],source_sha256=row["source_sha256"],
                             payload=row["metadata"].get("provider_payload",{})) for row in action_rows]
        return StockDetail(stock=stock, universe="BIST30_DATED_BULLETIN" if dated else "BIST30_CURRENT_CATALOG",
                           metadata_current_only=not dated,
                           chart=StockChart(start_date=start,end_date=end,cutoff=cutoff,points=points),
                           signals=[], price_adjustment=adjustment, cutoff=cutoff,
                           corporate_actions=actions,corporate_actions_total=total,
                           dated_member_on=member[0]["effective_date"] if member else None)


def bulletin_fields(metadata: Any, source_id: str | None) -> dict[str, str | None]:
    """Bulletin-only numbers as canonical decimal text; anything else stays missing."""
    if source_id != BULLETIN_SOURCE or not isinstance(metadata, dict):
        return {}
    result: dict[str, str | None] = {}
    for key in ("previous_close", "change_pct", "volume", "traded_value"):
        value = metadata.get(key)
        try:
            result[key] = decimal_text(value) if isinstance(value, str) and value else None
        except (ArithmeticError, ValueError):
            result[key] = None
    if result["previous_close"] is not None and Decimal(result["previous_close"]) == 0:
        result["previous_close"] = None
    return result
