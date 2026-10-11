"""Isolated, preregistered monthly scale-change development experiment.

The rule sees eligible reports only. Later SPK labels enter the comparison after
classification, never the rule, existing evidence packets or agent input.
"""
from __future__ import annotations
from calendar import monthrange
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from p50k.product import evaluation
from p50k.product.archive import ISTANBUL

VERSION = 'kap-monthly-scale-v1'
UPPER = Decimal('2')
LOWER = Decimal('0.5')
CASE_CODES = frozenset({'THF','TP2','PRY','PNU','DFI','DOH','KHA','TLY'})


@dataclass(frozen=True)
class Monthly:
    period: str
    value: Decimal | None
    units: Decimal | None
    published_at: datetime | None
    available_at: datetime | None
    ambiguous: bool = False


def month_end(period: str) -> date:
    year, month = map(int, period.split('-'))
    return date(year, month, monthrange(year, month)[1])


def classify(reports: list[Monthly], cutoff: datetime) -> dict[str, Any]:
    """Fixed two-period rule; no fund identity, price result or event label input."""
    day = cutoff.astimezone(ISTANBUL).date()
    eligible = [r for r in reports if r.published_at is not None and r.available_at is not None
                and r.published_at <= cutoff and r.available_at <= cutoff and month_end(r.period) <= day]
    eligible.sort(key=lambda r:r.period)
    if len(eligible) < 2:
        return {'state':'ABSTAINED','reason':'INSUFFICIENT_PERIODS'}
    previous, current = eligible[-2:]
    py, pm = map(int, previous.period.split('-'));cy, cm = map(int, current.period.split('-'))
    if cy*12+cm != py*12+pm+1:
        return {'state':'ABSTAINED','reason':'NONCONSECUTIVE_PERIODS'}
    values = (previous.value, previous.units, current.value, current.units)
    if previous.ambiguous or current.ambiguous:
        return {'state':'ABSTAINED','reason':'AMBIGUOUS_REVISION'}
    if any(v is None or not v.is_finite() or v <= 0 for v in values):
        return {'state':'ABSTAINED','reason':'MISSING_OR_NONPOSITIVE'}
    value_ratio = current.value / previous.value
    unit_ratio = current.units / previous.units
    flagged = (value_ratio >= UPPER and unit_ratio >= UPPER) or (value_ratio <= LOWER and unit_ratio <= LOWER)
    return {'state':'FLAGGED' if flagged else 'NOT_FLAGGED','reason':'SCALE_CHANGE' if flagged else 'BELOW_RULE',
            'previous_period':previous.period,'current_period':current.period,
            'value_ratio':str(value_ratio),'unit_ratio':str(unit_ratio),
            'available_at':max(previous.available_at,current.available_at).isoformat()}


REPORT_SQL = r"""WITH eligible AS (
    SELECT fund_code,report_period,published_at,available_at,observed_at,source_sha256,
      CASE WHEN jsonb_typeof(metadata->'report'->'total_value')='string'
        AND metadata->'report'->>'total_value' ~ '^-?(0|[1-9][0-9]*)(\.[0-9]+)?$'
        THEN (metadata->'report'->>'total_value')::numeric ELSE NULL END value,
      CASE WHEN jsonb_typeof(metadata->'report'->'units_outstanding')='string'
        AND metadata->'report'->>'units_outstanding' ~ '^-?(0|[1-9][0-9]*)(\.[0-9]+)?$'
        THEN (metadata->'report'->>'units_outstanding')::numeric ELSE NULL END units,
      dense_rank() OVER(PARTITION BY fund_code,report_period ORDER BY available_at DESC,published_at DESC,observed_at DESC NULLS LAST) priority
    FROM obs.kap_series WHERE fund_code=ANY(%s) AND cadence='monthly'
      AND published_at IS NOT NULL AND published_at<=%s AND available_at IS NOT NULL AND available_at<=%s
      AND (to_date(report_period||'-01','YYYY-MM-DD')+interval '1 month'-interval '1 day')::date<=%s
      AND (origin<>'SYNTHETIC' OR %s)
), canonical AS (
    SELECT fund_code,report_period,min(value) value,min(units) units,max(published_at) published_at,max(available_at) available_at,
      (count(DISTINCT value)>1 OR (count(value)>0 AND count(value)<count(*))
       OR count(DISTINCT units)>1 OR (count(units)>0 AND count(units)<count(*))) ambiguous
    FROM eligible WHERE priority=1 GROUP BY fund_code,report_period
) SELECT * FROM canonical ORDER BY fund_code,report_period"""


def report(connection, *, version_id: str, include_synthetic: bool) -> dict[str, Any] | None:
    run = evaluation.find_run(connection,version_id,include_synthetic)
    if run is None:
        return None
    cutoff = evaluation.scan_cutoff()
    funds = evaluation.read_funds(connection,run['run_id'],run['as_of'],run['cutoff'])
    grouped: dict[str,list[Monthly]] = defaultdict(list)
    rows = connection.execute(REPORT_SQL,([f.fund_code for f in funds],cutoff,cutoff,cutoff.astimezone(ISTANBUL).date(),include_synthetic)).fetchall()
    for code,period,value,units,published,available,ambiguous in rows:
        grouped[code].append(Monthly(period,value,units,published,available,ambiguous))
    outcomes = {f.fund_code:classify(grouped[f.fund_code],cutoff) for f in funds}
    # Labels are deliberately read only after every independent report classification.
    events, _ = evaluation.read_events(connection,include_synthetic)
    cohort = set(outcomes);listed = set(events)&cohort
    flagged = {code for code,item in outcomes.items() if item['state']=='FLAGGED'}
    price = {f.fund_code for f in funds if f.triggered&evaluation.PRICE_DETECTORS}
    assessed = {code for code,item in outcomes.items() if item['state']!='ABSTAINED'}
    counts = {'cohort':len(cohort),'assessed':len(assessed),'abstained':len(cohort-assessed),'flagged':len(flagged),
              'listed_total':len(listed),'caught':len(flagged&listed),'baseline_caught':len(price&listed),
              'added_to_price':len((flagged-price)&listed),'union_price_caught':len((price|flagged)&listed),
              'outside_list':len(flagged-listed),'listed_assessed':len(listed&assessed)}
    cases = [{'fund_code':f.fund_code,'name':f.name,**outcomes[f.fund_code],
              'added_to_price':f.fund_code in ((flagged-price)&listed)} for f in funds if f.fund_code in CASE_CODES]
    return {'protocol_version':VERSION,'cutoff':cutoff.isoformat(),'counts':counts,'cases':cases,
            'development_result':True,'baseline_unchanged':True,'feeds_agents':False}
