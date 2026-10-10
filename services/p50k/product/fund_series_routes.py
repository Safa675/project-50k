"""Published KAP period values for private display, outside model egress.

Monthly and weekly reports remain distinct observations. Nothing in this module
reads daily snapshots or fills dates between reports.
"""
from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import AwareDatetime, Field

from p50k.product.analysis_context import historical_mode
from p50k.product.archive import ISTANBUL
from p50k.product.auth import require_session
from p50k.product.models import Contract, DecimalText, FundCode
from p50k.product.queries import FundQueries, decimal_text
from p50k.product.routes import Code, Cutoff, Reader, resolve_cutoff


class PeriodValue(Contract):
    report_period: str
    cadence: Literal['monthly', 'weekly']
    period_end: date | None
    total_value: DecimalText | None
    units_outstanding: DecimalText | None
    total_value_currency: None = None
    published_at: AwareDatetime
    available_at: AwareDatetime
    source_url: str | None
    source_label: Literal['KAP'] = 'KAP'
    source_sha256: str
    status: Literal['AVAILABLE', 'PARSER_MISSING', 'AMBIGUOUS_REVISION']
    missing_fields: list[Literal['total_value', 'units_outstanding']]
    source_revision_count: int = Field(ge=1)


class SeriesCoverage(Contract):
    published_documents: int = Field(ge=0)
    local_documents: int = Field(ge=0)
    parsed_periods: int = Field(ge=0)
    parser_missing_periods: int = Field(ge=0)
    ambiguous_periods: int = Field(ge=0)
    known_unpublished_documents: int = Field(ge=0)
    unknown_publication_documents: int = Field(ge=0)


class FundSeriesPage(Contract):
    fund_code: FundCode
    items: list[PeriodValue] = Field(max_length=60)
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=60)
    offset: int = Field(ge=0, le=500)
    cutoff: AwareDatetime
    mode: Literal['HISTORICAL_REPLAY', 'DELAYED']
    status: Literal['AVAILABLE', 'PARTIAL', 'PARSER_MISSING', 'SOURCE_MISSING',
                    'REPORT_NOT_YET_PUBLISHED', 'PUBLICATION_TIME_UNKNOWN']
    coverage: SeriesCoverage
    rights_status: Literal['UNREVIEWED'] = 'UNREVIEWED'
    investor_counts_available: Literal[False] = False
    interpolated: Literal[False] = False


# Values must be exact parser-produced decimal strings. JSON numbers, unusual
# formatting and missing parser fields do not become invented numeric values.
SERIES_CTE = r"""WITH eligible AS (
    SELECT report_period,cadence,published_at,available_at,observed_at,source_sha256,
      CASE WHEN jsonb_typeof(metadata->'report'->'total_value')='string'
        AND metadata->'report'->>'total_value' ~ '^-?(0|[1-9][0-9]*)(\.[0-9]+)?$'
        THEN (metadata->'report'->>'total_value')::numeric ELSE NULL END total_value,
      CASE WHEN jsonb_typeof(metadata->'report'->'units_outstanding')='string'
        AND metadata->'report'->>'units_outstanding' ~ '^-?(0|[1-9][0-9]*)(\.[0-9]+)?$'
        THEN (metadata->'report'->>'units_outstanding')::numeric ELSE NULL END units_outstanding,
      metadata->'report'->>'disclosure_index' disclosure_index,
      dense_rank() OVER(PARTITION BY cadence,report_period
        ORDER BY available_at DESC,published_at DESC,observed_at DESC NULLS LAST) priority
    FROM obs.kap_series
    WHERE fund_code=%s AND published_at IS NOT NULL AND published_at<=%s
      AND available_at IS NOT NULL AND available_at<=%s
      AND (cadence<>'monthly' OR
        (to_date(report_period||'-01','YYYY-MM-DD')+interval '1 month'-interval '1 day')::date<=%s)
), selected AS (
    SELECT report_period,cadence,max(published_at) published_at,max(available_at) available_at,
      min(source_sha256) source_sha256,
      (array_agg(disclosure_index ORDER BY source_sha256))[1] disclosure_index,
      min(total_value) total_value,min(units_outstanding) units_outstanding,count(*) revision_count,
      (count(DISTINCT total_value)>1 OR (count(total_value)>0 AND count(total_value)<count(*))
       OR count(DISTINCT units_outstanding)>1
       OR (count(units_outstanding)>0 AND count(units_outstanding)<count(*))) ambiguous_revision
    FROM eligible WHERE priority=1 GROUP BY report_period,cadence
) """


def period_end(period: str, cadence: str) -> date | None:
    if cadence != 'monthly':
        # The archive's weekly code does not independently establish a valuation
        # weekday. Preserve that code and publication date without inventing one.
        return None
    year, month = (int(part) for part in period.split('-'))
    return date(year, month, monthrange(year, month)[1])


def series_page(reader: FundQueries, code: str, cutoff: datetime,
                limit: int = 60, offset: int = 0, *, historical: bool = True) -> FundSeriesPage:
    args = (code, cutoff, cutoff, cutoff.astimezone(ISTANBUL).date())
    counts = reader._rows(SERIES_CTE + '''SELECT count(*) total,
        count(*) FILTER(WHERE NOT ambiguous_revision AND (total_value IS NOT NULL OR units_outstanding IS NOT NULL)) usable,
        count(*) FILTER(WHERE total_value IS NULL OR units_outstanding IS NULL) parser_missing,
        count(*) FILTER(WHERE ambiguous_revision) ambiguous FROM selected''', args)[0]
    rows = reader._rows(SERIES_CTE + '''SELECT * FROM selected
        ORDER BY published_at DESC,report_period DESC,cadence LIMIT %s OFFSET %s''', args + (limit, offset))
    items = []
    for row in rows:
        ambiguous = row['ambiguous_revision']
        total_value = None if ambiguous else decimal_text(row['total_value'])
        units = None if ambiguous else decimal_text(row['units_outstanding'])
        disclosure = row['disclosure_index']
        source_url = (f'https://www.kap.org.tr/tr/Bildirim/{disclosure}'
                      if isinstance(disclosure, str) and disclosure.isascii() and disclosure.isdigit()
                      and 0 < len(disclosure) <= 20 and int(disclosure) > 0 else None)
        missing = [name for name, value in (('total_value', total_value), ('units_outstanding', units))
                   if value is None]
        items.append(PeriodValue(report_period=row['report_period'], cadence=row['cadence'],
            period_end=period_end(row['report_period'], row['cadence']),
            total_value=total_value, units_outstanding=units, published_at=row['published_at'],
            available_at=row['available_at'], source_url=source_url, source_sha256=row['source_sha256'],
            status='AMBIGUOUS_REVISION' if ambiguous else 'PARSER_MISSING' if missing else 'AVAILABLE',
            missing_fields=missing, source_revision_count=row['revision_count']))

    # A later report's mere existence must not alter historical coverage. Only
    # headers already observed by the cutoff may describe a scheduled future
    # publication; no future identity, publication date or values are returned.
    documents = reader._rows('''WITH visible AS (
        SELECT DISTINCT ON(document_key) document_key,published_at,available_at,
            relative_path,observed_at,ingested_at
        FROM obs.kap_documents WHERE fund_code=%s
          AND ((published_at<=%s AND available_at<=%s)
            OR COALESCE(observed_at,ingested_at)<=%s)
        ORDER BY document_key,available_at DESC NULLS LAST,observed_at DESC NULLS LAST,source_sha256
    ) SELECT
        count(*) FILTER(WHERE published_at<=%s AND available_at<=%s) published,
        count(*) FILTER(WHERE published_at<=%s AND available_at<=%s AND relative_path IS NOT NULL) local,
        count(*) FILTER(WHERE published_at>%s AND COALESCE(observed_at,ingested_at)<=%s) unpublished,
        count(*) FILTER(WHERE published_at IS NULL AND COALESCE(observed_at,ingested_at)<=%s) unknown
        FROM visible''', (code, cutoff, cutoff, cutoff, cutoff, cutoff, cutoff, cutoff, cutoff, cutoff, cutoff))[0]
    unknown_series = reader._count('''SELECT count(*) total FROM obs.kap_series
        WHERE fund_code=%s AND published_at IS NULL
        AND COALESCE(available_at,observed_at,ingested_at)<=%s''', (code, cutoff))
    coverage = SeriesCoverage(published_documents=documents['published'], local_documents=documents['local'],
        parsed_periods=counts['total'], parser_missing_periods=counts['parser_missing'],
        ambiguous_periods=counts['ambiguous'], known_unpublished_documents=documents['unpublished'],
        unknown_publication_documents=documents['unknown'] + unknown_series)
    if counts['total']:
        status = ('PARTIAL' if counts['usable'] and (counts['parser_missing'] or counts['ambiguous'])
                  else 'PARSER_MISSING' if not counts['usable'] or counts['ambiguous'] else 'AVAILABLE')
    elif documents['local']:
        status = 'PARSER_MISSING'
    elif documents['unpublished']:
        status = 'REPORT_NOT_YET_PUBLISHED'
    elif coverage.unknown_publication_documents:
        status = 'PUBLICATION_TIME_UNKNOWN'
    else:
        status = 'SOURCE_MISSING'
    return FundSeriesPage(fund_code=code, items=items, total=counts['total'], limit=limit,
        offset=offset, cutoff=cutoff, mode='HISTORICAL_REPLAY' if historical else 'DELAYED',
        status=status, coverage=coverage)


router = APIRouter(dependencies=[Depends(require_session)], tags=['Published fund reports'])


@router.get('/funds/{fund_code}/series', response_model=FundSeriesPage)
def fund_series(fund_code: Code, reader: Reader, cutoff: Cutoff = None,
                limit: Annotated[int, Query(ge=1, le=60)] = 60,
                offset: Annotated[int, Query(ge=0, le=500)] = 0) -> FundSeriesPage:
    if reader.fund(fund_code) is None:
        raise HTTPException(404, 'FUND_NOT_FOUND')
    return series_page(reader, fund_code, resolve_cutoff(cutoff), limit, offset,
                       historical=cutoff is not None or historical_mode())
