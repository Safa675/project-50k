"""After-the-fact comparison of the 12 September scan with SPK's 17 September liquidation orders.

Read-only and deterministic. Nothing here feeds detectors, agents or any analysis
view: the official list, published after the scan's cutoff, is set beside stored
detector output only to report how that earlier scan lines up with it. The
regulatory-record detector (AN-FND-005) is left out, so the official list can
never count as its own detection. A fund without enough data for a behaviour
check is "not assessable", never "quiet".
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Iterable

from p50k.product.archive import ISTANBUL
from p50k.product.chat_language import DEFINITIONS

SCAN_DAY = date(2026, 9, 12)
EVENT_DATE = date(2026, 9, 17)
EVENT_TYPE = 'SPK_LIQUIDATION_ORDER'
DECISION_REFERENCES = ('57/1707', '57/1708')
REGULATORY = 'AN-FND-005'
PRICE_DETECTORS = frozenset({'D1', 'D2', 'D3', 'D4'})
DATA_QUALITY_PREFIX = 'AN-DQ-'
VIEWS = ('all', 'price', 'data_quality')
OUTCOMES = ('caught', 'missed', 'listed_not_assessable', 'flagged_outside', 'quiet', 'other_not_assessable')
ONE_DECIMAL = Decimal('0.1')


@dataclass(frozen=True)
class FundSignals:
    """One fund's admissible scan output; regulatory and attribute rows are already removed."""
    fund_code: str
    name: str
    triggered: frozenset[str]
    assessed: frozenset[str]


def family(detector_id: str) -> str | None:
    if detector_id in PRICE_DETECTORS:
        return 'price'
    if detector_id.startswith(DATA_QUALITY_PREFIX):
        return 'data_quality'
    return None


def counts_in(detector_id: str, view: str) -> bool:
    if view not in VIEWS:
        raise ValueError('VIEW_INVALID')
    return detector_id != REGULATORY and (view == 'all' or family(detector_id) == view)


def checked(fund: FundSignals, view: str) -> bool:
    """A fund was looked at only when a behaviour check (data checks in that view) returned a result."""
    wanted = 'data_quality' if view == 'data_quality' else 'price'
    return any(family(detector) == wanted for detector in fund.assessed)


def outcome(fund: FundSignals, listed: bool, view: str) -> str:
    if any(counts_in(detector, view) for detector in fund.triggered):
        return 'caught' if listed else 'flagged_outside'
    if not checked(fund, view):
        return 'listed_not_assessable' if listed else 'other_not_assessable'
    return 'missed' if listed else 'quiet'


def percent(numerator: int, denominator: int) -> str | None:
    if denominator <= 0:
        return None
    return str((Decimal(100 * numerator) / Decimal(denominator)).quantize(ONE_DECIMAL, ROUND_HALF_UP))


def rate(numerator: int, denominator: int) -> dict[str, Any]:
    return {'numerator': numerator, 'denominator': denominator, 'percent': percent(numerator, denominator)}


def times(first: dict[str, Any], second: dict[str, Any]) -> str | None:
    """How many times the first rate is the second; None when either rate is undefined or the second is zero."""
    if first['denominator'] <= 0 or second['denominator'] <= 0 or second['numerator'] <= 0:
        return None
    value = Decimal(first['numerator'] * second['denominator']) / Decimal(first['denominator'] * second['numerator'])
    return str(value.quantize(ONE_DECIMAL, ROUND_HALF_UP))


def summarize(funds: Iterable[FundSignals], listed: set[str], view: str) -> dict[str, Any]:
    tally = dict.fromkeys(OUTCOMES, 0)
    for fund in funds:
        tally[outcome(fund, fund.fund_code in listed, view)] += 1
    listed_total = tally['caught'] + tally['missed'] + tally['listed_not_assessable']
    other_total = tally['flagged_outside'] + tally['quiet'] + tally['other_not_assessable']
    flagged = tally['caught'] + tally['flagged_outside']
    listed_rate = rate(tally['caught'], listed_total)
    other_rate = rate(tally['flagged_outside'], other_total)
    return {'view': view, 'counts': {**tally, 'listed_funds': listed_total, 'other_funds': other_total, 'flagged': flagged,
                                     'scanned': listed_total + other_total},
            'detection_rate': listed_rate, 'on_list_share': rate(tally['caught'], flagged),
            'other_flag_rate': other_rate, 'times_more_often': times(listed_rate, other_rate),
            'assessed_detection_rate': rate(tally['caught'], tally['caught'] + tally['missed'])}


def detector_labels(rows: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    used = sorted({detector for row in rows for detector in row['detectors']})
    return {detector: {'label': DEFINITIONS.get(detector, ('Kaynak incelemesi', '', ''))[0], 'family': family(detector)}
            for detector in used}


def fund_rows(funds: Iterable[FundSignals], listed: set[str]) -> list[dict[str, Any]]:
    """Funds that are listed or flagged in some view; every other fund is quiet or not assessable everywhere."""
    rows = []
    for fund in funds:
        is_listed = fund.fund_code in listed
        fired = sorted(detector for detector in fund.triggered if counts_in(detector, 'all'))
        if not is_listed and not fired:
            continue
        rows.append({'fund_code': fund.fund_code, 'name': fund.name, 'listed': is_listed,
                     'detectors': fired,
                     'outcomes': {view: outcome(fund, is_listed, view) for view in VIEWS},
                     'href': '/funds/' + fund.fund_code})
    return sorted(rows, key=lambda row: row['fund_code'])


def build_report(run: dict[str, Any], funds: list[FundSignals], events: dict[str, str],
                 ground_truth: dict[str, Any]) -> dict[str, Any]:
    """Pure assembly of the report from already-read rows; `events` maps listed fund codes to names."""
    scanned = {fund.fund_code for fund in funds}
    listed = set(events) & scanned
    outside = [{'fund_code': code, 'name': events[code]} for code in sorted(set(events) - scanned)]
    rows = fund_rows(funds, listed)
    return {'run': run, 'ground_truth': {**ground_truth, 'listed_total': len(events), 'outside_scan': outside},
            'summaries': {view: summarize(funds, listed, view) for view in VIEWS},
            'funds': rows, 'detectors': detector_labels(rows),
            'method': {'excluded_detectors': [REGULATORY], 'price_detectors': sorted(PRICE_DETECTORS),
                       'data_quality_prefix': DATA_QUALITY_PREFIX, 'after_the_fact': True,
                       'development_result': True, 'feeds_detectors_or_agents': False}}


def scan_cutoff() -> datetime:
    return datetime.combine(SCAN_DAY, time.max, ISTANBUL)


def find_run(connection, version_id: str, include_synthetic: bool) -> dict[str, Any] | None:
    """The 12 September run, chosen with the same rule as the retrospective analysis view."""
    row = connection.execute("""SELECT run.run_id,input.as_of,run.origin,run.cutoff,input.version_id,run.protocol_version
        FROM det.detector_runs run JOIN det.run_inputs input USING(run_id)
        WHERE input.complete AND run.cutoff IS NOT NULL AND run.cutoff<=%s
          AND (run.cutoff AT TIME ZONE 'Europe/Istanbul')::date=%s
          AND ((run.origin='HISTORICAL_REPLAY' AND input.version_id=%s) OR (%s AND run.origin='SYNTHETIC'))
        ORDER BY run.cutoff DESC,run.created_at DESC,run.run_id DESC LIMIT 1""",
        (scan_cutoff(), SCAN_DAY, version_id, include_synthetic)).fetchone()
    if not row:
        return None
    return {'run_id': str(row[0]), 'as_of': row[1].isoformat(), 'origin': row[2], 'cutoff': row[3].isoformat(),
            'version_id': row[4], 'protocol_version': row[5], 'scan_day': SCAN_DAY.isoformat(), 'development_result': True}


def read_funds(connection, run_id: str, as_of: str, cutoff: str) -> list[FundSignals]:
    """Every fund in the run; only admissible, non-attribute, non-regulatory results count (as the agent sentinel reads them)."""
    rows = connection.execute("""SELECT signal.fund_code,fund.name,
            COALESCE(array_agg(signal.detector_id ORDER BY signal.detector_id)
              FILTER (WHERE signal.state='TRIGGERED' AND admissible.ok),'{}'),
            COALESCE(array_agg(signal.detector_id ORDER BY signal.detector_id)
              FILTER (WHERE signal.state IN ('TRIGGERED','NOT_TRIGGERED') AND admissible.ok),'{}')
        FROM det.signals signal JOIN det.evidence_items item USING(evidence_id)
        JOIN ref.funds fund ON fund.fund_code=signal.fund_code
        CROSS JOIN LATERAL (SELECT signal.detector_id<>%s AND signal.as_of<=%s::date
            AND NOT COALESCE((item.metadata->>'is_attribute')::boolean,false)
            AND item.available_at IS NOT NULL AND item.available_at<=%s::timestamptz AS ok) admissible
        WHERE signal.run_id=%s
        GROUP BY signal.fund_code,fund.name ORDER BY signal.fund_code""",
        (REGULATORY, as_of, cutoff, run_id)).fetchall()
    return [FundSignals(row[0], row[1], frozenset(row[2]), frozenset(row[3])) for row in rows]


def read_events(connection) -> tuple[dict[str, str], dict[str, Any]]:
    """Confirmed liquidation orders of 17 September, one per fund; candidate copies never count."""
    rows = connection.execute("""SELECT event.fund_code,fund.name,event.metadata->>'bulletin_id',
            event.metadata->>'publication_date',event.metadata->>'source_url',event.published_at
        FROM obs.regulatory_events event JOIN ref.funds fund USING(fund_code)
        WHERE event.event_type=%s AND event.status='CONFIRMED' AND event.effective_date=%s
        ORDER BY event.fund_code,event.event_id""", (EVENT_TYPE, EVENT_DATE)).fetchall()
    events = {row[0]: row[1] for row in rows}
    ground_truth = {'source': 'SPK', 'event_type': EVENT_TYPE, 'status': 'CONFIRMED', 'decision_date': EVENT_DATE.isoformat(),
                    'decision_references': list(DECISION_REFERENCES),
                    'bulletins': sorted({row[2] for row in rows if row[2]}),
                    'publication_dates': sorted({row[3] for row in rows if row[3]}),
                    'source_urls': sorted({row[4] for row in rows if row[4] and row[4].startswith('https://')}),
                    'publication_time_known': bool(rows) and all(row[5] is not None for row in rows),
                    'published_after_scan': EVENT_DATE > SCAN_DAY}
    return events, ground_truth


def retrospective(connection, *, version_id: str, include_synthetic: bool) -> dict[str, Any] | None:
    """Read-only report; None when the 12 September run is not stored."""
    run = find_run(connection, version_id, include_synthetic)
    if run is None:
        return None
    funds = read_funds(connection, run['run_id'], run['as_of'], run['cutoff'])
    events, ground_truth = read_events(connection)
    return build_report(run, funds, events, ground_truth)
