// Authored illustrative data for /preview/dates only. Invented codes and values,
// labelled "Örnek". Never import private archives into frontend code.
import {cutoffAtFor, DATE_RULE, DEFAULT_DATE, SNAPSHOT_BOUND, datedSchemas, DateIndexSchema,
  type DateIndex, type DatedDetailResponse, type DatedListResponse, type DatedRecord, type DatedSource, type DatedSummaryResponse} from './dated-contract';

export const SYNTHETIC_DATES = ['2025-10-31', '2025-11-28', '2025-12-31', '2026-01-30', '2026-02-27', '2026-03-31',
  '2026-04-30', '2026-05-29', '2026-06-30', '2026-07-31', '2026-08-31', '2026-09-16'] as const;
const hex = (prefix: string, value: number) => prefix + value.toString(16).padStart(64 - prefix.length, '0');
const LABELS = {
  origin: 'HISTORICAL_REPLAY', analysis_mode: 'EXPLORATORY_ARCHIVE', cutoff_semantics: 'RECORDED_SOURCE_DATE_FILTER',
  point_in_time_verified: false, historical_availability: 'UNKNOWN', rights_status: 'UNKNOWN',
  universe_basis: 'OCTOBER_2026_INVESTOR_SNAPSHOT', category_basis: 'CURRENT_SNAPSHOT',
  knowledge_basis: 'RECORDED_SOURCE_DATE_RECONSTRUCTION', findings_scope: 'D1_ONLY', date_rule: DATE_RULE,
} as const;
const INDEX_ID = 'e'.repeat(64);
export const syntheticIndex: DateIndex = DateIndexSchema.parse({
  ...LABELS, index_id: INDEX_ID, default_date: DEFAULT_DATE,
  entries: SYNTHETIC_DATES.map((date, i) => ({date, cutoff_at: cutoffAtFor(date), bundle_id: hex('5', i + 1)})),
});

function addDays(date: string, days: number): string {
  const value = new Date(`${date}T00:00:00Z`);
  value.setUTCDate(value.getUTCDate() + days);
  return value.toISOString().slice(0, 10);
}
const CATEGORIES = ['Örnek Hisse', 'Örnek Borçlanma', 'Örnek Değişken', 'Örnek Katılım'];
const THRESHOLDS = ['0.0030', '0.0012', '0.0021', '0.0018'];
const GLOBAL_SOURCES: [string, DatedSource['kind'], DatedSource['media_type'], string][] = [
  [hex('a', 1), 'UNIVERSE', 'text/plain', 'ornek-fon-listesi.txt'], [hex('a', 2), 'PROTOCOL', 'text/plain', 'ornek-protokol.md'],
  [hex('a', 3), 'CALIBRATION', 'application/json', 'ornek-esikler.json'], [hex('a', 4), 'CODE', 'text/plain', 'ornek-hesap.py'],
  [hex('a', 5), 'SNAPSHOT', 'application/json', 'ornek-kategori-kaydi.json'],
];
const code = (n: number) => `Z${String(n).padStart(2, '0')}`;
const priceId = (n: number) => hex('b', n + 1);
const COMMENTS = {
  ELIGIBLE_CROSSING: 'Örnek yorum: seçilen tarihe kadarki son 60 veri konumunda getiri farkı, sabit araştırma eşiğinin üzerinde.',
  ELIGIBLE_NO_CROSSING: 'Örnek yorum: seçilen tarihe kadarki son 60 veri konumunda getiri farkı sabit araştırma eşiğini aşmadı.',
  STALE: 'Örnek yorum: hesabın son gözlemi seçilen tarihe ait değil; bu tarihin uygun bulguları arasında sayılmadı.',
  UNAVAILABLE: 'Örnek yorum: seçilen tarihte getiri karşılaştırması için yeterli veri yok.',
} as const;

function record(n: number, date: string, step: number): DatedRecord {
  const unpriced = n >= 100 - Math.max(0, 4 - step);
  const unavailable = unpriced || n === 90 || (n === 91 && step < 2);
  const stale = !unavailable && n === 80 + (step % 5);
  const crossing = !unavailable && (stale || n === step || n === step + 12);
  const category = CATEGORIES[n % 4];
  const threshold = THRESHOLDS[n % 4];
  const start = addDays(date, -86);
  const latest = unavailable ? null : stale ? addDays(date, -2) : date;
  const d1: DatedRecord['d1'] = {
    arithmetic_status: unavailable ? 'UNAVAILABLE' : 'AVAILABLE', research_screen: unavailable ? 'UNKNOWN' : crossing ? 'CROSSING' : 'NO_CROSSING',
    freshness: unavailable ? 'UNKNOWN' : stale ? 'STALE' : 'FRESH', production_status: 'ABSTAINED',
    missing_reasons: unpriced || n === 91 ? ['fewer_than_50_usable_excess_observations'] : n === 90 ? ['fewer_than_10_category_peers'] : stale ? ['final_contributing_observation_before_cutoff'] : [],
    qualifications: ['historical_availability_unknown', 'peer_category_membership_from_current_snapshot'],
    metric_period: {start, end: date}, units: {statistic: 'DAILY_LOG_RETURN', threshold: 'DAILY_LOG_RETURN'},
    input_refs: [priceId(n), priceId((n + 4) % 100)].sort(), statistic: unavailable ? null : crossing ? `0.00${45 + step}` : `0.000${n % 9}`,
    threshold, usable_observations: unavailable ? (unpriced ? 0 : 31) : 58 + (n % 3), window_positions: 60,
    eligible_peers: unavailable ? (n === 90 ? 6 : 0) : 21, latest_contributing_at: latest,
  };
  const gap = n % 7 === 0;
  const chart: DatedRecord['chart'] = unavailable
    ? {status: 'UNAVAILABLE', reason: 'no_common_valid_baseline_with_10_peers', baseline_date: null, unit: 'INDEX_100', points: [], peer_count: n === 90 ? 6 : 21}
    : {status: 'AVAILABLE', reason: null, baseline_date: start, unit: 'INDEX_100', peer_count: 21, points: [
      {date: start, fund: '100', peers: '100'}, {date: addDays(start, 28), fund: String(101 + (n % 3)), peers: '100.8'},
      {date: addDays(start, 56), fund: gap ? null : String(102 + (n % 4)), peers: '101.5'}, {date, fund: String(103 + (crossing ? 4 : n % 2)), peers: '102.2'}]};
  const d1_state = unavailable ? 'UNAVAILABLE' : stale ? 'STALE' : crossing ? 'ELIGIBLE_CROSSING' : 'ELIGIBLE_NO_CROSSING';
  return {code: code(n), name: `Örnek Fon ${code(n)}`, category: n === 90 ? 'Örnek Az Üyeli' : category, comment_tr: COMMENTS[d1_state], d1_state, d1, chart,
    date_context: {has_positive_price_on_or_before_cutoff: !unpriced}, evidence: [...GLOBAL_SOURCES.map(([id]) => id), priceId(n)].sort()};
}
const RANK = {ELIGIBLE_CROSSING: 0, STALE: 1, UNAVAILABLE: 1, ELIGIBLE_NO_CROSSING: 2} as const;

function bundle(date: string) {
  const step = SYNTHETIC_DATES.indexOf(date as typeof SYNTHETIC_DATES[number]);
  const entry = syntheticIndex.entries[step];
  if (!entry) throw new RangeError('Not a synthetic index date');
  const funds = Array.from({length: 100}, (_, n) => record(n, date, step))
    .sort((a, b) => RANK[a.d1_state] - RANK[b.d1_state] || a.code.localeCompare(b.code));
  const metadata = {...LABELS, cutoff_at: entry.cutoff_at, cutoff_date: date, index_id: INDEX_ID, immutable_bundle_id: entry.bundle_id};
  const count = (state: DatedRecord['d1_state']) => funds.filter(fund => fund.d1_state === state).length;
  const schemas = datedSchemas(date);
  const list: DatedListResponse = schemas.List.parse({...metadata, funds});
  const summary: DatedSummaryResponse = schemas.Summary.parse({...metadata,
    summary: {denominator: 100, record_count: 100, d1_eligible_crossing: count('ELIGIBLE_CROSSING'), d1_eligible_no_crossing: count('ELIGIBLE_NO_CROSSING'),
      d1_stale: count('STALE'), d1_unavailable: count('UNAVAILABLE'), no_price_at_cutoff: funds.filter(fund => !fund.date_context.has_positive_price_on_or_before_cutoff).length},
    threshold_provenance: {calibration_end_exclusive: '2025-10-06', percentile: 99, crossing: 'STRICTLY_ABOVE', calibration_run_at_utc: SNAPSHOT_BOUND,
      results_sha256: hex('c', 1), threshold_map_sha256: hex('c', 2), detectors_sha256: hex('c', 3), preregistration_sha256: hex('c', 4),
      calibration_universe_basis: 'OCTOBER_2026_INVESTOR_SNAPSHOT', calibration_category_basis: '2026-10-06 snapshot',
      note: 'Thresholds were computed over a post-event universe that includes the evaluated funds.'},
    snapshot: {bound: SNAPSHOT_BOUND, latest_retrieved_at: '2026-10-07T06:30:00+00:00', projection_sha256: hex('d', 1)}});
  const detail = (selected: string): DatedDetailResponse | null => {
    const fund = funds.find(item => item.code === selected);
    if (!fund) return null;
    const n = Number(selected.slice(1));
    const sources: DatedSource[] = [...GLOBAL_SOURCES.map(([source_id, kind, media_type, file_name]) => ({source_id, kind, label: `Örnek ${kind}`, fund_code: null, sha256: hex('f', parseInt(source_id.slice(-2), 16)),
      file_name, media_type, pdf_available: false as const, published_at: null, retrieved_at: kind === 'SNAPSHOT' ? '2026-10-07T06:30:00+00:00' : null,
      historical_availability: 'UNKNOWN' as const, rights_status: 'UNKNOWN' as const, origin: 'HISTORICAL_REPLAY' as const, disclosure_id: null, disclosure_url: null})),
    ...[n, (n + 4) % 100].map(item => ({source_id: priceId(item), kind: 'PRICE' as const, label: `Örnek ${code(item)} PRICE`, fund_code: code(item), sha256: hex('9', item + 1),
      file_name: `${code(item)}.json`, media_type: 'application/json' as const, pdf_available: false as const, published_at: null, retrieved_at: '2026-10-07T06:00:00+00:00',
      historical_availability: 'UNKNOWN' as const, rights_status: 'UNKNOWN' as const, origin: 'HISTORICAL_REPLAY' as const, disclosure_id: null, disclosure_url: null}))];
    return schemas.Detail.parse({...metadata, fund, sources});
  };
  return {entry, list, summary, detail};
}

const bundles = new Map<string, ReturnType<typeof bundle>>();
/** Validated synthetic bundle for one of the synthetic index dates. */
export function syntheticBundle(date: string): ReturnType<typeof bundle> {
  let value = bundles.get(date);
  if (!value) { value = bundle(date); bundles.set(date, value); }
  return value;
}
