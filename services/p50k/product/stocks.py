"""Bounded current BIST30 catalog and point-in-time daily close reads."""
from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Any, Literal

from psycopg import Connection
from psycopg.rows import dict_row
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, JsonValue

from p50k.product.queries import decimal_text

Symbol = Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9]{1,11}$")]
DecimalText = Annotated[str, Field(pattern=r"^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")]
Checksum = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class StockContract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class StockProvenance(StockContract):
    data_mode: Literal["DELAYED"] = "DELAYED"
    rights_status: Literal["UNREVIEWED"] = "UNREVIEWED"
    universe: Literal["BIST30_CURRENT_CATALOG"] = "BIST30_CURRENT_CATALOG"
    metadata_current_only: Literal[True] = True
    development_result: Literal[True] = True


class StockInstrument(StockContract):
    symbol: Symbol
    name: str
    exchange: Literal["BIST"] = "BIST"
    currency: Literal["TRY"] = "TRY"


class StockListing(StockInstrument):
    last_date: date | None
    last_close: DecimalText | None


class StocksPage(StockProvenance):
    items: list[StockListing] = Field(max_length=30)
    total: int = Field(ge=0, le=30)
    limit: int = Field(ge=1, le=30)
    offset: int = Field(ge=0, le=30)
    catalog_captured_at: AwareDatetime | None


class StockPricePoint(StockContract):
    effective_date: date
    close: DecimalText | None
    available_at: AwareDatetime
    source_sha256: Checksum
    ambiguous_revision: bool


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
            dense_rank() OVER(PARTITION BY effective_date
                ORDER BY available_at DESC,observed_at DESC) priority
        FROM obs.stock_prices WHERE symbol=%s AND effective_date BETWEEN %s AND %s
            AND available_at<=%s
    ), latest AS (SELECT * FROM eligible WHERE priority=1), conflicts AS (
        SELECT effective_date,(count(DISTINCT close)>1 OR
            (count(close)>0 AND count(close)<count(*))) ambiguous_revision
        FROM latest GROUP BY effective_date
    ) SELECT DISTINCT ON(latest.effective_date) latest.effective_date,
        CASE WHEN conflicts.ambiguous_revision THEN NULL::numeric ELSE latest.close END AS close,
        latest.available_at,latest.source_sha256,conflicts.ambiguous_revision,latest.price_adjustment
      FROM latest JOIN conflicts USING(effective_date)
      ORDER BY latest.effective_date,latest.source_sha256 DESC
"""
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

    def stocks(self, query: str, limit: int, offset: int, cutoff: datetime) -> StocksPage:
        term = "%" + query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        where = " WHERE symbol ILIKE %s OR name ILIKE %s"
        total = self._rows(CATALOG_CTE + "SELECT count(*) total FROM members" + where, (term, term))[0]["total"]
        members = self._rows(CATALOG_CTE + "SELECT * FROM members" + where + " ORDER BY symbol LIMIT %s OFFSET %s", (term, term, limit, offset))
        captured = self._rows(CATALOG_CTE + "SELECT captured_at FROM catalog", ())
        items = []
        for member in members:
            statement = PRICE_SQL.replace("latest.effective_date,latest.source_sha256 DESC", "latest.effective_date DESC,latest.source_sha256 DESC") + " LIMIT 1"
            from p50k.product.archive import ISTANBUL
            rows = self._rows(statement, (member["symbol"], date.min, cutoff.astimezone(ISTANBUL).date(), cutoff))
            latest = rows[0] if rows else None
            items.append(StockListing(**member, last_date=latest["effective_date"] if latest else None,
                                      last_close=decimal_text(latest["close"]) if latest else None))
        return StocksPage(items=items, total=total, limit=limit, offset=offset,
                          catalog_captured_at=captured[0]["captured_at"] if captured else None)

    def stock(self, symbol: str) -> StockInstrument | None:
        rows = self._rows(CATALOG_CTE + "SELECT * FROM members WHERE symbol=%s", (symbol,))
        return StockInstrument(**rows[0]) if rows else None

    def detail(self, stock: StockInstrument, start: date, end: date, cutoff: datetime) -> StockDetail:
        rows = self._rows(PRICE_SQL, (stock.symbol, start, end, cutoff))
        adjustments = {row.pop("price_adjustment") for row in rows}
        points = [StockPricePoint(**{**row, "close": decimal_text(row["close"])}) for row in rows]
        adjustment = next(iter(adjustments)) if len(adjustments)==1 else "MIXED" if adjustments else "UNVERIFIED"
        args=(stock.symbol,start,end,cutoff)
        total=self._rows(ACTION_CTE+"SELECT count(*) total FROM eligible",args)[0]["total"]
        action_rows=self._rows(ACTION_CTE+"SELECT * FROM eligible ORDER BY effective_date DESC,event_id LIMIT 100",args)
        actions=[StockAction(event_id=row["event_id"],effective_date=row["effective_date"],
                             available_at=row["available_at"],source_sha256=row["source_sha256"],
                             payload=row["metadata"].get("provider_payload",{})) for row in action_rows]
        return StockDetail(stock=stock,
                           chart=StockChart(start_date=start,end_date=end,cutoff=cutoff,points=points),
                           signals=[], price_adjustment=adjustment, cutoff=cutoff,
                           corporate_actions=actions,corporate_actions_total=total)
