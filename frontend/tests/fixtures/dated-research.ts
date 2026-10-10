// Authored synthetic per-date fixtures only. Invented codes X00..X99 and invented
// values; no private archive, real fund or real TEFAS number is used.
import {createHash} from 'node:crypto';

export const FIXTURE_DATES = ['2025-10-31', '2025-11-28', '2025-12-31', '2026-01-30', '2026-02-27', '2026-03-31',
  '2026-04-30', '2026-05-29', '2026-06-30', '2026-07-31', '2026-08-31', '2026-09-16'] as const;
export type FixtureDate = typeof FIXTURE_DATES[number];
const sha = (text: string) => createHash('sha256').update(text).digest('hex');
export const INDEX_ID = sha('fixture-index');
export const bundleIdFor = (date: string) => sha(`fixture-bundle:${date}`);
export const cutoffAt = (date: string) => `${date}T23:59:59+03:00`;
export const NO_CROSSING_NOTE = 'Eşiğin aşılmaması bir güvenlik değerlendirmesi değildir.';
export const LABELS = {
  origin: 'HISTORICAL_REPLAY', analysis_mode: 'EXPLORATORY_ARCHIVE', cutoff_semantics: 'RECORDED_SOURCE_DATE_FILTER',
  point_in_time_verified: false, historical_availability: 'UNKNOWN', rights_status: 'UNKNOWN',
  universe_basis: 'OCTOBER_2026_INVESTOR_SNAPSHOT', category_basis: 'CURRENT_SNAPSHOT',
  knowledge_basis: 'RECORDED_SOURCE_DATE_RECONSTRUCTION', findings_scope: 'D1_ONLY', date_rule: 'MONTH_END_PLUS_WINDOW_END_V1',
} as const;
export const SNAPSHOT_BOUND = '2026-10-07T08:52:12.470547+00:00';

export function indexFixture() {
  return {...LABELS, index_id: INDEX_ID, default_date: '2026-09-16',
    entries: FIXTURE_DATES.map((date): {date: string; cutoff_at: string; bundle_id: string} => ({date, cutoff_at: cutoffAt(date), bundle_id: bundleIdFor(date)}))};
}
export function errorFixture(status: number, code: string, message_tr: string, date: string | null = null) {
  return {status, body: {...LABELS, cutoff_at: date ? cutoffAt(date) : null, cutoff_date: date, index_id: INDEX_ID,
    immutable_bundle_id: null, error: {code, message_tr}}};
}

function addDays(date: string, days: number): string {
  const value = new Date(`${date}T00:00:00Z`);
  value.setUTCDate(value.getUTCDate() + days);
  return value.toISOString().slice(0, 10);
}
export const fixtureCode = (n: number) => `X${String(n).padStart(2, '0')}`;
const priceId = (n: number) => sha(`fixture-price:${n}`);
const GLOBALS = (['UNIVERSE', 'PROTOCOL', 'CALIBRATION', 'CODE', 'SNAPSHOT'] as const).map(kind => ({kind, id: sha(`fixture-global:${kind}`)}));
const TEMPLATES = {
  UNAVAILABLE: 'Seçilen tarihte benzer fonlarla getiri karşılaştırması için yeterli veri yok.',
  STALE: 'Benzer fonlarla getiri hesabının son gözlemi seçilen tarihe ait değil; bu tarihin uygun bulguları arasında sayılmadı.',
  ELIGIBLE_CROSSING: 'Seçilen tarihe kadarki son 60 veri konumunda ortanca günlük fazla getiri, sabit araştırma eşiğinin üzerinde.',
  ELIGIBLE_NO_CROSSING: `Seçilen tarihe kadarki son 60 veri konumunda benzer fonlarla getiri farkı sabit araştırma eşiğini aşmadı. ${NO_CROSSING_NOTE}`,
} as const;
type State = keyof typeof TEMPLATES;
const RANK: Record<State, number> = {ELIGIBLE_CROSSING: 0, STALE: 1, UNAVAILABLE: 1, ELIGIBLE_NO_CROSSING: 2};

/** States at step i: crossings X{i}, X{i+12}; stale X{50+i}; unavailable X40; unpriced X99.. while i < 3. */
export function stateFor(n: number, step: number): {state: State; unpriced: boolean} {
  const unpriced = step < 3 && n >= 97 + step;
  if (unpriced || n === 40) return {state: 'UNAVAILABLE', unpriced};
  if (n === 50 + step) return {state: 'STALE', unpriced};
  if (n === step || n === step + 12) return {state: 'ELIGIBLE_CROSSING', unpriced};
  return {state: 'ELIGIBLE_NO_CROSSING', unpriced};
}

function record(n: number, date: string, step: number) {
  const {state, unpriced} = stateFor(n, step);
  const unavailable = state === 'UNAVAILABLE';
  const start = addDays(date, -85);
  const crossing = state === 'ELIGIBLE_CROSSING' || state === 'STALE';
  return {
    code: fixtureCode(n), name: `Örnek Test Fonu ${fixtureCode(n)}`, category: n % 2 ? 'Örnek Değişken' : 'Örnek Hisse',
    comment_tr: TEMPLATES[state], d1_state: state,
    d1: {
      arithmetic_status: unavailable ? 'UNAVAILABLE' : 'AVAILABLE', research_screen: unavailable ? 'UNKNOWN' : crossing ? 'CROSSING' : 'NO_CROSSING',
      freshness: unavailable ? 'UNKNOWN' : state === 'STALE' ? 'STALE' : 'FRESH', production_status: 'ABSTAINED',
      missing_reasons: unavailable ? ['fewer_than_50_usable_excess_observations'] : state === 'STALE' ? ['final_contributing_observation_before_cutoff'] : [],
      qualifications: ['historical_availability_unknown', 'peer_category_membership_from_current_snapshot'],
      metric_period: {start, end: date}, units: {statistic: 'DAILY_LOG_RETURN', threshold: 'DAILY_LOG_RETURN'},
      input_refs: [priceId(n), priceId((n + 2) % 100)].sort(),
      statistic: unavailable ? null : crossing ? `0.00${50 + step}` : `0.000${n % 7}`, threshold: '0.0020',
      usable_observations: unavailable ? (unpriced ? 0 : 20) : 60, window_positions: 60, eligible_peers: unavailable ? 0 : 20,
      latest_contributing_at: unavailable ? null : state === 'STALE' ? addDays(date, -3) : date,
    },
    chart: unavailable ? {status: 'UNAVAILABLE', reason: 'no_common_valid_baseline_with_10_peers', baseline_date: null, unit: 'INDEX_100', points: [], peer_count: 20}
      : {status: 'AVAILABLE', reason: null, baseline_date: start, unit: 'INDEX_100', peer_count: 20, points: [
        {date: start, fund: '100', peers: '100'}, {date: addDays(start, 40), fund: n === 1 ? null : '101.5', peers: '100.7'},
        {date, fund: String(102 + step), peers: '101.2'}]},
    date_context: {has_positive_price_on_or_before_cutoff: !unpriced},
    evidence: [...GLOBALS.map(item => item.id), priceId(n)].sort(),
  };
}
function source(id: string, kind: string, fundCode: string | null) {
  return {source_id: id, kind, label: `Authored synthetic ${kind}`, fund_code: fundCode, sha256: sha(`fixture-bytes:${id}`),
    file_name: kind === 'PRICE' ? `${fundCode}.json` : `authored-${kind.toLowerCase()}.txt`,
    media_type: kind === 'PRICE' || kind === 'SNAPSHOT' || kind === 'CALIBRATION' ? 'application/json' : 'text/plain',
    pdf_available: false, published_at: null, retrieved_at: kind === 'PRICE' || kind === 'SNAPSHOT' ? '2026-10-07T07:00:00+00:00' : null,
    historical_availability: 'UNKNOWN', rights_status: 'UNKNOWN', origin: 'HISTORICAL_REPLAY', disclosure_id: null, disclosure_url: null};
}

/** One sealed date's synthetic API payloads. */
export function datedFixture(date: string) {
  const step = FIXTURE_DATES.indexOf(date as FixtureDate);
  if (step < 0) throw new Error(`not a fixture date: ${date}`);
  const metadata = {...LABELS, cutoff_at: cutoffAt(date), cutoff_date: date, index_id: INDEX_ID, immutable_bundle_id: bundleIdFor(date)};
  const funds = Array.from({length: 100}, (_, n) => record(n, date, step))
    .sort((a, b) => RANK[a.d1_state] - RANK[b.d1_state] || a.code.localeCompare(b.code));
  const count = (state: State) => funds.filter(fund => fund.d1_state === state).length;
  const summary = {denominator: 100, record_count: 100, d1_eligible_crossing: count('ELIGIBLE_CROSSING'), d1_eligible_no_crossing: count('ELIGIBLE_NO_CROSSING'),
    d1_stale: count('STALE'), d1_unavailable: count('UNAVAILABLE'), no_price_at_cutoff: funds.filter(fund => !fund.date_context.has_positive_price_on_or_before_cutoff).length};
  return {
    entry: {date, cutoff_at: cutoffAt(date), bundle_id: bundleIdFor(date)},
    list: {...metadata, funds},
    summary: {...metadata, summary,
      threshold_provenance: {calibration_end_exclusive: '2025-10-06', percentile: 99, crossing: 'STRICTLY_ABOVE', calibration_run_at_utc: SNAPSHOT_BOUND,
        results_sha256: sha('fixture-results'), threshold_map_sha256: sha('fixture-map'), detectors_sha256: sha('fixture-detectors'), preregistration_sha256: sha('fixture-prereg'),
        calibration_universe_basis: 'OCTOBER_2026_INVESTOR_SNAPSHOT', calibration_category_basis: '2026-10-06 snapshot',
        note: 'Thresholds were computed over a post-event universe that includes the evaluated funds.'},
      snapshot: {bound: SNAPSHOT_BOUND, latest_retrieved_at: '2026-10-07T07:00:00+00:00', projection_sha256: sha('fixture-projection')}},
    detail(code: string) {
      const fund = funds.find(item => item.code === code);
      if (!fund) return null;
      const n = Number(code.slice(1));
      const sources = [...GLOBALS.map(item => source(item.id, item.kind, null)), source(priceId(n), 'PRICE', code), source(priceId((n + 2) % 100), 'PRICE', fixtureCode((n + 2) % 100))];
      return {...metadata, fund, sources};
    },
  };
}
