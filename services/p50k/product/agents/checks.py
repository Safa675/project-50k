"""Doğrulayıcı's deterministic tests. Code computes every number from data the run admits.

Fixed descriptive parameters (2026-10-10, DEC-035). They describe a case for the
review; they never trigger, recalibrate or alter a detector result:

- peer_window: the last 20 daily returns (21 dated prices) found within 60 calendar
  days before the run's as-of date; at least 10 same-category peers; "below" at or
  under the 10th percentile, "above" at or over the 90th.
- category_move: the share of other same-category funds with a TRIGGERED D1-D4 in
  the same run; at least 5 peers; widespread at 25 % or more, isolated under 10 %.
- data_quality: the fund's last 20 dated price rows; stale at 2 or more weekdays,
  the existing AN-DQ-001 rule.
- kap_monthly_change: the two latest monthly KAP reports published by the cutoff;
  a notable change is 20 % or more in total value or units outstanding.
- regulatory_event: admitted official records and the stored regulatory evidence.

Only categorical outcomes and fixed sentences without numbers are model input
(DEC-031); numbers stay in stored payloads and server-rendered text.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
import math
from statistics import median
from typing import Any

import numpy as np

from p50k.product.agents.store import Run
from p50k.product.archive import ISTANBUL
from p50k.product.egress import Evidence

WINDOW = 20
LOOKBACK_DAYS = 60
MIN_PEERS = 10
PEER_LOW, PEER_HIGH = 0.10, 0.90
CATEGORY_MIN = 5
CATEGORY_WIDESPREAD, CATEGORY_ISOLATED = 0.25, 0.10
KAP_NOTABLE = Decimal('0.20')
STALE_WEEKDAYS = 2

TESTS = {
    'peer_window': ('Benzer fonlarla dönem karşılaştırması',
                    'Son dönemdeki işlem günlerinde fonun getirisini aynı kategorideki fonlarla karşılaştırır.'),
    'category_move': ('Kategori genelinde hareket',
                      'Aynı hesaplamada aynı kategorideki diğer fonların fiyat davranışı ölçümlerinde inceleme sınırını aşıp aşmadığını sayar.'),
    'data_quality': ('Veri kalitesi kontrolü',
                     'Fonun son fiyat kayıtlarında eksik, gecikmiş veya çelişkili kayıt olup olmadığını kontrol eder.'),
    'kap_monthly_change': ('Aylık rapor değişimi',
                           'Seçili tarihe kadar yayımlanmış son aylık raporlarda toplam değer ve pay sayısındaki değişimi hesaplar.'),
    'regulatory_event': ('Resmî kayıt kontrolü',
                         'Seçili tarihe kadar kullanılabilir resmî kayıtlarda bu fonla eşleşen bir olay olup olmadığını kontrol eder.'),
}
DEFAULT_TESTS = tuple(TESTS)
FINDINGS = {
    'peer_window': {
        'below_peers': 'Seçili dönemde fonun getirisi aynı kategorideki fonların çoğunun altında kalmış.',
        'above_peers': 'Seçili dönemde fonun getirisi aynı kategorideki fonların çoğunun üzerinde kalmış.',
        'within_peers': 'Seçili dönemde fonun getirisi aynı kategorideki fonların orta kesiminde kalmış.',
        'unavailable': 'Bu dönem için karşılaştırma yapacak kadar uygun fiyat kaydı yok.'},
    'category_move': {
        'widespread': 'Aynı hesaplamada bu kategorideki fonların önemli bir kısmı da inceleme sınırını aşmış.',
        'mixed': 'Aynı hesaplamada bu kategorideki fonların bir kısmı da inceleme sınırını aşmış.',
        'isolated': 'Aynı hesaplamada bu kategorideki fonların çok azı inceleme sınırını aşmış.',
        'unavailable': 'Kategori bilgisi veya yeterli sayıda benzer fon olmadığından bu test yapılamadı.'},
    'data_quality': {
        'issues_found': 'Fonun son fiyat kayıtlarında eksik, gecikmiş veya çelişkili kayıt var.',
        'clean': 'Fonun son fiyat kayıtlarında eksik, gecikmiş veya çelişkili kayıt görülmedi.',
        'unavailable': 'Fonun seçili tarihe kadar kullanılabilir fiyat kaydı yok.'},
    'kap_monthly_change': {
        'notable_change': 'Seçili tarihe kadar yayımlanmış son aylık raporlar arasında toplam değer veya pay sayısında belirgin bir değişim var.',
        'no_notable_change': 'Seçili tarihe kadar yayımlanmış son aylık raporlar arasında toplam değer ve pay sayısında belirgin bir değişim görülmedi.',
        'unavailable': 'Karşılaştırma için seçili tarihe kadar yayımlanmış yeterli aylık rapor yok.'},
    'regulatory_event': {
        'confirmed_event': 'Seçili tarihe kadar kullanılabilir resmî kayıtlarda bu fonla eşleşen ve zamanı belli bir olay var.',
        'candidate_only': 'Eşleşen bir resmî kayıt var; ancak zamanı veya eşleşmesi yeterince doğrulanmamış.',
        'none_found': 'İncelenen resmî kayıt arşivinde bu fonla eşleşen uygun bir olay bulunmadı; arşiv sınırlı olduğundan bu, olay olmadığı anlamına gelmez.'},
}
MONTHS = ('Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık')


@dataclass(frozen=True)
class CheckContext:
    fund_code: str
    category: str | None
    run: Run
    evidence: tuple[Evidence, ...]

    @property
    def cutoff_date(self) -> date:
        return self.run.cutoff.astimezone(ISTANBUL).date()


def resolve_prices(rows) -> dict[tuple[str, date], tuple[str, Decimal | None]]:
    """Latest admitted row per fund and date; conflicting top rows stay ambiguous, never chosen."""
    groups: dict[tuple[str, date], list] = {}
    for code, day, nav, available, observed in rows:
        groups.setdefault((code, day), []).append((nav, available, observed))
    resolved = {}
    for key, items in groups.items():
        rank = lambda item: (item[1], item[2] is not None, item[2] or datetime.min.replace(tzinfo=item[1].tzinfo))
        top = max(rank(item) for item in items)
        values = {item[0] for item in items if rank(item) == top}
        if len(values) > 1:
            resolved[key] = ('ambiguous', None)
        else:
            value = next(iter(values))
            resolved[key] = ('ok', Decimal(value)) if value is not None and Decimal(value) > 0 else ('missing', None)
    return resolved


def percent(value: Decimal | float) -> str:
    return str(Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def log_return_percent(value: float) -> str:
    return percent(Decimal(str(math.expm1(value))) * 100)


def result(test: str, outcome: str, values: dict[str, Any] | None = None, reason: str | None = None) -> dict[str, Any]:
    return {'test': test, 'outcome': outcome, 'values': values or {}, 'reason': reason}


def peer_window(connection, context: CheckContext) -> dict[str, Any]:
    if not context.category:
        return result('peer_window', 'unavailable', reason='CATEGORY_MISSING')
    rows = connection.execute("""SELECT price.fund_code,price.effective_date,price.nav,price.available_at,price.observed_at
        FROM obs.fund_prices price JOIN ref.funds fund USING(fund_code)
        WHERE fund.category=%s AND price.effective_date BETWEEN %s AND %s
          AND price.available_at IS NOT NULL AND price.available_at<=%s
          AND (price.published_at IS NULL OR price.published_at<=%s)""",
        (context.category, context.run.as_of - timedelta(days=LOOKBACK_DAYS), context.run.as_of,
         context.run.cutoff, context.run.cutoff)).fetchall()
    prices = resolve_prices(rows)
    days = sorted({day for _, day in prices})
    if len(days) < WINDOW + 1:
        return result('peer_window', 'unavailable', reason='SHORT_WINDOW')
    start, end = days[-(WINDOW + 1)], days[-1]
    returns = {}
    for code in {code for code, _ in prices}:
        first, last = prices.get((code, start)), prices.get((code, end))
        if first and last and first[0] == 'ok' and last[0] == 'ok':
            returns[code] = math.log(float(last[1]) / float(first[1]))
    own = returns.get(context.fund_code)
    peers = [value for code, value in returns.items() if code != context.fund_code]
    if own is None:
        return result('peer_window', 'unavailable', {'window_start': start.isoformat(), 'window_end': end.isoformat()},
                      'FUND_PRICE_MISSING')
    if len(peers) < MIN_PEERS:
        return result('peer_window', 'unavailable', {'peers': len(peers)}, 'TOO_FEW_PEERS')
    lower = sum(value < own for value in peers) + 0.5 * sum(value == own for value in peers)
    share = lower / len(peers)
    outcome = 'below_peers' if share <= PEER_LOW else 'above_peers' if share >= PEER_HIGH else 'within_peers'
    return result('peer_window', outcome, {
        'fund_return_pct': log_return_percent(own), 'peer_median_return_pct': log_return_percent(median(peers)),
        'lower_peer_share_pct': percent(share * 100), 'peers': len(peers), 'trading_days': WINDOW,
        'window_start': start.isoformat(), 'window_end': end.isoformat()})


def category_move(connection, context: CheckContext) -> dict[str, Any]:
    if not context.category:
        return result('category_move', 'unavailable', reason='CATEGORY_MISSING')
    rows = connection.execute("""SELECT signal.fund_code,
            bool_or(signal.state='TRIGGERED' AND signal.detector_id IN ('D1','D2','D3','D4'))
        FROM det.signals signal JOIN ref.funds fund USING(fund_code)
        WHERE signal.run_id=%s AND fund.category=%s AND signal.as_of<=%s
        GROUP BY signal.fund_code""", (context.run.run_id, context.category, context.run.as_of)).fetchall()
    others = [bool(flag) for code, flag in rows if code != context.fund_code]
    if len(others) < CATEGORY_MIN:
        return result('category_move', 'unavailable', {'category_funds': len(others)}, 'TOO_FEW_PEERS')
    flagged = sum(others)
    share = flagged / len(others)
    outcome = 'widespread' if share >= CATEGORY_WIDESPREAD else 'isolated' if share < CATEGORY_ISOLATED else 'mixed'
    return result('category_move', outcome, {'category_funds': len(others), 'flagged_funds': flagged,
                                             'flagged_share_pct': percent(share * 100)})


def data_quality(connection, context: CheckContext) -> dict[str, Any]:
    rows = connection.execute("""SELECT fund_code,effective_date,nav,available_at,observed_at FROM obs.fund_prices
        WHERE fund_code=%s AND effective_date BETWEEN %s AND %s
          AND available_at IS NOT NULL AND available_at<=%s AND (published_at IS NULL OR published_at<=%s)""",
        (context.fund_code, context.run.as_of - timedelta(days=LOOKBACK_DAYS), context.run.as_of,
         context.run.cutoff, context.run.cutoff)).fetchall()
    last_priced = connection.execute("""SELECT max(effective_date) FROM obs.fund_prices
        WHERE fund_code=%s AND nav IS NOT NULL AND effective_date<=%s
          AND available_at IS NOT NULL AND available_at<=%s AND (published_at IS NULL OR published_at<=%s)""",
        (context.fund_code, context.run.as_of, context.run.cutoff, context.run.cutoff)).fetchone()[0]
    prices = resolve_prices(rows)
    window = sorted(day for _, day in prices)[-WINDOW:]
    if not window and last_priced is None:
        return result('data_quality', 'unavailable', reason='NO_PRICE_ROWS')
    states = [prices[(context.fund_code, day)][0] for day in window]
    gap = (max(0, int(np.busday_count(last_priced + timedelta(days=1), context.cutoff_date)))
           if last_priced is not None else None)
    missing, ambiguous = states.count('missing'), states.count('ambiguous')
    issues = (not window or missing or ambiguous or states[-1] != 'ok' or gap is None or gap >= STALE_WEEKDAYS)
    return result('data_quality', 'issues_found' if issues else 'clean', {
        'rows': len(window), 'missing_rows': missing, 'ambiguous_rows': ambiguous,
        'window_start': window[0].isoformat() if window else None, 'window_end': window[-1].isoformat() if window else None,
        'last_priced_date': last_priced.isoformat() if last_priced else None, 'weekdays_since_last_price': gap})


KAP_SQL = r"""SELECT report_period,published_at,available_at,observed_at,
      CASE WHEN jsonb_typeof(metadata->'report'->'total_value')='string'
        AND metadata->'report'->>'total_value' ~ '^-?(0|[1-9][0-9]*)(\.[0-9]+)?$'
        THEN (metadata->'report'->>'total_value')::numeric ELSE NULL END,
      CASE WHEN jsonb_typeof(metadata->'report'->'units_outstanding')='string'
        AND metadata->'report'->>'units_outstanding' ~ '^-?(0|[1-9][0-9]*)(\.[0-9]+)?$'
        THEN (metadata->'report'->>'units_outstanding')::numeric ELSE NULL END
    FROM obs.kap_series
    WHERE fund_code=%s AND cadence='monthly' AND published_at IS NOT NULL AND published_at<=%s
      AND available_at IS NOT NULL AND available_at<=%s
      AND (to_date(report_period||'-01','YYYY-MM-DD')+interval '1 month'-interval '1 day')::date<=%s"""


def kap_monthly_change(connection, context: CheckContext) -> dict[str, Any]:
    rows = connection.execute(KAP_SQL, (context.fund_code, context.run.cutoff, context.run.cutoff,
                                        context.cutoff_date)).fetchall()
    periods: dict[str, list] = {}
    for period, published, available, observed, total, units in rows:
        periods.setdefault(period, []).append(((available, published, observed is not None, observed or published), total, units, published))
    usable = []
    for period, items in periods.items():
        top = max(item[0] for item in items)
        chosen = [item for item in items if item[0] == top]
        totals, unit_values = {item[1] for item in chosen}, {item[2] for item in chosen}
        if len(totals) > 1 or len(unit_values) > 1:
            continue
        total, units = next(iter(totals)), next(iter(unit_values))
        if total is not None or units is not None:
            usable.append((period, total, units, chosen[0][3]))
    usable.sort(key=lambda item: item[0])
    if len(usable) < 2:
        return result('kap_monthly_change', 'unavailable', {'usable_reports': len(usable)}, 'TOO_FEW_REPORTS')
    previous, latest = usable[-2], usable[-1]
    changes = {}
    for name, index in (('total_value_change_pct', 1), ('units_change_pct', 2)):
        if previous[index] is not None and latest[index] is not None and previous[index] > 0:
            changes[name] = (latest[index] - previous[index]) / previous[index]
    if not changes:
        return result('kap_monthly_change', 'unavailable', {'usable_reports': len(usable)}, 'NO_COMPARABLE_VALUES')
    notable = any(abs(value) >= KAP_NOTABLE for value in changes.values())
    return result('kap_monthly_change', 'notable_change' if notable else 'no_notable_change', {
        'previous_period': previous[0], 'latest_period': latest[0],
        'previous_published_at': previous[3].isoformat(), 'latest_published_at': latest[3].isoformat(),
        **{name: percent(value * 100) for name, value in changes.items()}})


def regulatory_event(connection, context: CheckContext) -> dict[str, Any]:
    rows = connection.execute("""SELECT DISTINCT ON (event_id) event_id,status,available_at FROM obs.regulatory_events
        WHERE fund_code=%s AND (available_at<=%s OR (available_at IS NULL AND ingested_at<=%s))
          AND (published_at IS NULL OR published_at<=%s) AND (effective_date IS NULL OR effective_date<=%s)
          AND (status='CANDIDATE' OR confirmed_at<=%s)
        ORDER BY event_id,(status='CONFIRMED') DESC,available_at DESC NULLS LAST,source_sha256 DESC""",
        (context.fund_code, context.run.cutoff, context.run.cutoff, context.run.cutoff, context.cutoff_date,
         context.run.cutoff)).fetchall()
    triggered = any(item.detector_id == 'AN-FND-005' and item.state == 'TRIGGERED' for item in context.evidence)
    outcome = 'confirmed_event' if triggered else 'candidate_only' if rows else 'none_found'
    return result('regulatory_event', outcome, {'records': len(rows),
        'confirmed_records': sum(row[1] == 'CONFIRMED' for row in rows),
        'unknown_time_records': sum(row[2] is None for row in rows)})


RUNNERS = {'peer_window': peer_window, 'category_move': category_move, 'data_quality': data_quality,
           'kap_monthly_change': kap_monthly_change, 'regulatory_event': regulatory_event}


def run_check(connection, test: str, context: CheckContext) -> dict[str, Any]:
    if test not in RUNNERS:
        raise ValueError('TEST_UNKNOWN')
    return RUNNERS[test](connection, context)


def tr_date(value: str | None) -> str:
    if not value:
        return 'bilinmeyen bir tarih'
    day = date.fromisoformat(value[:10])
    return f'{day.day} {MONTHS[day.month - 1]} {day.year}'


def tr_period(value: str) -> str:
    year, month = value.split('-')
    return f'{MONTHS[int(month) - 1]} {year}'


def tr_percent(value: str | None) -> str:
    if value is None:
        return 'hesaplanamadı'
    number = Decimal(value)
    text = format(abs(number), 'f').replace('.', ',')
    return ('-%' if number < 0 else '%') + text


def describe(item: dict[str, Any]) -> str:
    """Server-written result sentence; numbers come only from the computed payload."""
    name = TESTS[item['test']][0]
    finding = FINDINGS[item['test']][item['outcome']]
    values = item['values']
    if item['outcome'] == 'unavailable':
        return f'{name}: {finding}'
    if item['test'] == 'peer_window':
        return (f"{name}: {tr_date(values['window_start'])} ile {tr_date(values['window_end'])} arasındaki "
                f"{values['trading_days']} işlem gününde fonun getirisi {tr_percent(values['fund_return_pct'])}, "
                f"aynı kategorideki {values['peers']} fonun ortanca getirisi {tr_percent(values['peer_median_return_pct'])}. "
                f"Getirisi bu fondan düşük olan benzer fonların oranı: {tr_percent(values['lower_peer_share_pct'])}. {finding}")
    if item['test'] == 'category_move':
        return (f"{name}: aynı hesaplamada bu kategorideki diğer {values['category_funds']} fondan "
                f"{values['flagged_funds']} tanesi fiyat davranışı ölçümlerinde inceleme sınırını aşmış "
                f"(oran: {tr_percent(values['flagged_share_pct'])}). {finding}")
    if item['test'] == 'data_quality':
        last = (f"Son kullanılabilir fiyat {tr_date(values['last_priced_date'])} tarihli; değerlendirme tarihine kadar "
                f"{values['weekdays_since_last_price']} hafta içi gün geçmiş." if values['last_priced_date']
                else 'Kullanılabilir pozitif fiyat kaydı yok.')
        if not values['rows']:
            return f'{name}: son dönemde fiyat kaydı yok. {last} {finding}'
        return (f"{name}: son {values['rows']} fiyat kaydından {values['missing_rows']} tanesinde fiyat yok, "
                f"{values['ambiguous_rows']} tanesinde çelişkili kayıt var. {last} {finding}")
    if item['test'] == 'kap_monthly_change':
        parts = []
        if 'total_value_change_pct' in values:
            parts.append(f"toplam değer {tr_percent(values['total_value_change_pct'])}")
        if 'units_change_pct' in values:
            parts.append(f"pay sayısı {tr_percent(values['units_change_pct'])}")
        return (f"{name}: {tr_period(values['previous_period'])} ve {tr_period(values['latest_period'])} aylık raporları "
                f"arasında {' ve '.join(parts)} değişmiş. Raporlar {tr_date(values['previous_published_at'])} ve "
                f"{tr_date(values['latest_published_at'])} tarihlerinde yayımlanmış. {finding}")
    return (f"{name}: seçili tarihe kadar kullanılabilir {values['records']} resmî kayıt bulundu; "
            f"{values['confirmed_records']} tanesi doğrulanmış. {finding}")


def model_view(reference: str, item: dict[str, Any]) -> dict[str, str]:
    """Categorical, number-free projection for model input (DEC-031)."""
    return {'ref': reference, 'test': item['test'], 'name_tr': TESTS[item['test']][0],
            'outcome': item['outcome'], 'finding_tr': FINDINGS[item['test']][item['outcome']]}
