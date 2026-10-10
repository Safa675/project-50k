// Runtime contract of the dated D1 view (fund_review_dated/PROTOCOL.md).
// Every per-date schema is built for one cutoff: nested observation dates may not
// pass that payload's own cutoff_date. No flow, concentration or KAP source exists here.
import {z} from 'zod';
import {compareDecimal} from './decimal-compare';
import {dateMentions, deniedTerms} from './dated-presentation';

export const WINDOW_START = '2025-10-06';
export const WINDOW_END = '2026-09-16';
export const DEFAULT_DATE = WINDOW_END;
export const CALIBRATION_END_EXCLUSIVE = '2025-10-06';
export const DATE_RULE = 'MONTH_END_PLUS_WINDOW_END_V1';
export const SNAPSHOT_BOUND = '2026-10-07T08:52:12.470547+00:00';
export const GRID_MONTHS = ['2025-10', '2025-11', '2025-12', '2026-01', '2026-02', '2026-03',
  '2026-04', '2026-05', '2026-06', '2026-07', '2026-08'] as const;
export const GRID_SIZE = 12;
export const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;
export const BUNDLE_PATTERN = /^[a-f0-9]{64}$/;
export const CODE_PATTERN = /^[A-Z0-9]{3}$/;
export const D1_STATES = ['ELIGIBLE_CROSSING', 'ELIGIBLE_NO_CROSSING', 'STALE', 'UNAVAILABLE'] as const;
export const DATED_SOURCE_KINDS = ['PRICE', 'SNAPSHOT', 'CALIBRATION', 'UNIVERSE', 'PROTOCOL', 'CODE'] as const;

/** Canonical YYYY-MM-DD that names a real calendar day. */
export function isCalendarDate(value: string): boolean {
  if (!DATE_PATTERN.test(value)) return false;
  const parsed = new Date(`${value}T00:00:00Z`);
  return !Number.isNaN(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value;
}
export function isInDatedRange(value: string): boolean { return value >= WINDOW_START && value <= WINDOW_END; }
/** Fixed +03:00 offset; no time-zone database. */
export function cutoffAtFor(date: string): string { return `${date}T23:59:59+03:00`; }

const Decimal = z.string().regex(/^[+-]?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?$/)
  .refine(value => Number.isFinite(Number(value)), 'A decimal must be finite');
const Day = z.string().refine(isCalendarDate, 'Invalid date');
const Timestamp = z.string().regex(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/)
  .refine(value => !Number.isNaN(Date.parse(value)) && isCalendarDate(value.slice(0, 10)) && Number(value.slice(11, 13)) < 24 && Number(value.slice(14, 16)) < 60 && Number(value.slice(17, 19)) < 60, 'Invalid timestamp');
const Hash = z.string().regex(BUNDLE_PATTERN);
const Code = z.string().regex(CODE_PATTERN);
const Count = z.number().int().nonnegative();
function issue(ctx: z.RefinementCtx, message: string) { ctx.addIssue({code: 'custom', message}); }

const FIXED_LABELS = {
  origin: z.literal('HISTORICAL_REPLAY'), analysis_mode: z.literal('EXPLORATORY_ARCHIVE'),
  cutoff_semantics: z.literal('RECORDED_SOURCE_DATE_FILTER'), point_in_time_verified: z.literal(false),
  historical_availability: z.literal('UNKNOWN'), rights_status: z.literal('UNKNOWN'),
  universe_basis: z.literal('OCTOBER_2026_INVESTOR_SNAPSHOT'), category_basis: z.literal('CURRENT_SNAPSHOT'),
  knowledge_basis: z.literal('RECORDED_SOURCE_DATE_RECONSTRUCTION'), findings_scope: z.literal('D1_ONLY'),
  date_rule: z.literal(DATE_RULE),
};

const DateEntrySchema = z.strictObject({date: Day, cutoff_at: z.string(), bundle_id: Hash});
/** `GET /research-dated/v1/dates`: labels, the index ID and the 12 sealed entries only. */
export const DateIndexSchema = z.strictObject({
  ...FIXED_LABELS, index_id: Hash, default_date: z.literal(DEFAULT_DATE),
  entries: z.array(DateEntrySchema).length(GRID_SIZE),
}).superRefine((index, ctx) => {
  const dates = index.entries.map(entry => entry.date);
  if (index.entries.some(entry => entry.cutoff_at !== cutoffAtFor(entry.date))) issue(ctx, 'Every entry needs its canonical cutoff');
  if (dates.some(date => !isInDatedRange(date))) issue(ctx, 'Entry outside the registered range');
  if (dates.some((date, i) => i > 0 && date <= dates[i - 1])) issue(ctx, 'Entries must be in strict calendar order');
  if (dates[GRID_SIZE - 1] !== WINDOW_END) issue(ctx, 'The index must end at the window end');
  if (GRID_MONTHS.some((month, i) => dates[i]?.slice(0, 7) !== month)) issue(ctx, 'One entry per grid month is required');
  if (new Set(index.entries.map(entry => entry.bundle_id)).size !== GRID_SIZE) issue(ctx, 'Bundle IDs must be distinct');
});

export const ThresholdProvenanceSchema = z.strictObject({
  calibration_end_exclusive: z.literal(CALIBRATION_END_EXCLUSIVE), percentile: z.literal(99), crossing: z.literal('STRICTLY_ABOVE'),
  calibration_run_at_utc: Timestamp, results_sha256: Hash, threshold_map_sha256: Hash, detectors_sha256: Hash, preregistration_sha256: Hash,
  calibration_universe_basis: z.literal('OCTOBER_2026_INVESTOR_SNAPSHOT'), calibration_category_basis: z.literal('2026-10-06 snapshot'),
  note: z.literal('Thresholds were computed over a post-event universe that includes the evaluated funds.'),
});
export const SnapshotSchema = z.strictObject({bound: z.literal(SNAPSHOT_BOUND), latest_retrieved_at: Timestamp, projection_sha256: Hash})
  .refine(snapshot => Date.parse(snapshot.latest_retrieved_at) <= Date.parse(SNAPSHOT_BOUND), 'Snapshot rows must not pass the bound');
export const DatedSummarySchema = z.strictObject({
  denominator: z.literal(100), record_count: z.literal(100), d1_eligible_crossing: Count, d1_eligible_no_crossing: Count,
  d1_stale: Count, d1_unavailable: Count, no_price_at_cutoff: Count,
}).superRefine((summary, ctx) => {
  if (summary.d1_eligible_crossing + summary.d1_eligible_no_crossing + summary.d1_stale + summary.d1_unavailable !== 100) issue(ctx, 'D1 states must cover the 100 funds');
  if (summary.no_price_at_cutoff > summary.d1_unavailable) issue(ctx, 'Unpriced funds are a subset of unavailable funds');
});

const STATE_ORDER: Record<typeof D1_STATES[number], number> = {ELIGIBLE_CROSSING: 0, STALE: 1, UNAVAILABLE: 1, ELIGIBLE_NO_CROSSING: 2};
export function expectedState(d1: {arithmetic_status: string; freshness: string; research_screen: string}): typeof D1_STATES[number] | null {
  if (d1.arithmetic_status !== 'AVAILABLE') return 'UNAVAILABLE';
  if (d1.freshness === 'STALE') return 'STALE';
  if (d1.freshness !== 'FRESH') return null;
  return d1.research_screen === 'CROSSING' ? 'ELIGIBLE_CROSSING' : d1.research_screen === 'NO_CROSSING' ? 'ELIGIBLE_NO_CROSSING' : null;
}

function build(date: string) {
  const cutoffAt = cutoffAtFor(date);
  const metadata = {...FIXED_LABELS, cutoff_at: z.literal(cutoffAt), cutoff_date: z.literal(date)};
  const D1 = z.strictObject({
    arithmetic_status: z.enum(['AVAILABLE', 'UNAVAILABLE']), research_screen: z.enum(['CROSSING', 'NO_CROSSING', 'UNKNOWN']),
    freshness: z.enum(['FRESH', 'STALE', 'UNKNOWN']), production_status: z.literal('ABSTAINED'),
    missing_reasons: z.array(z.string()), qualifications: z.array(z.string()),
    metric_period: z.strictObject({start: Day.nullable(), end: Day.nullable()}),
    units: z.strictObject({statistic: z.literal('DAILY_LOG_RETURN'), threshold: z.literal('DAILY_LOG_RETURN')}),
    input_refs: z.array(Hash), statistic: Decimal.nullable(), threshold: Decimal.nullable(),
    usable_observations: Count, window_positions: Count, eligible_peers: Count, latest_contributing_at: Day.nullable(),
  }).superRefine((d1, ctx) => {
    const {start, end} = d1.metric_period;
    if ([start, end, d1.latest_contributing_at].some(value => value !== null && value > date)) issue(ctx, 'D1 dates must not pass the cutoff');
    if (start && end && start > end) issue(ctx, 'Invalid D1 window');
    if (d1.window_positions > 60 || d1.usable_observations > d1.window_positions) issue(ctx, 'Invalid D1 observation coverage');
    if (new Set(d1.input_refs).size !== d1.input_refs.length) issue(ctx, 'Duplicate D1 input');
    if (d1.arithmetic_status === 'UNAVAILABLE') {
      if (d1.statistic !== null || d1.research_screen !== 'UNKNOWN' || d1.freshness !== 'UNKNOWN') issue(ctx, 'Unavailable arithmetic must remain unknown');
      return;
    }
    if (d1.statistic === null || d1.threshold === null || d1.research_screen === 'UNKNOWN') issue(ctx, 'Available arithmetic requires statistic, threshold and screen');
    if (d1.usable_observations < 50 || d1.eligible_peers < 10 || !d1.latest_contributing_at || !start || end !== date) issue(ctx, 'Available D1 requires its window up to the cutoff and coverage');
    if (d1.latest_contributing_at && start && (d1.latest_contributing_at < start || d1.latest_contributing_at > date)) issue(ctx, 'D1 latest observation must be in its window');
    if (d1.freshness !== (d1.latest_contributing_at === date ? 'FRESH' : 'STALE')) issue(ctx, 'D1 freshness must be measured against the selected date');
    if (d1.statistic !== null && d1.threshold !== null && d1.research_screen !== (compareDecimal(d1.statistic, d1.threshold) > 0 ? 'CROSSING' : 'NO_CROSSING')) issue(ctx, 'D1 uses a strict greater-than crossing');
  });
  const Chart = z.strictObject({
    status: z.enum(['AVAILABLE', 'UNAVAILABLE']), reason: z.string().nullable(), baseline_date: Day.nullable(), unit: z.literal('INDEX_100'),
    points: z.array(z.strictObject({date: Day, fund: Decimal.nullable(), peers: Decimal.nullable()})), peer_count: Count,
  }).superRefine((chart, ctx) => {
    const dates = chart.points.map(point => point.date);
    if (dates.some((value, i) => value > date || (i > 0 && value <= dates[i - 1]))) issue(ctx, 'Chart must use unique ordered dates up to the cutoff');
    if (chart.baseline_date !== null && chart.baseline_date > date) issue(ctx, 'Chart baseline after the cutoff');
    if (chart.status === 'AVAILABLE' && (chart.peer_count < 10 || !dates.length || chart.baseline_date !== dates[0])) issue(ctx, 'Chart needs a common baseline and 10 peers');
    if (chart.status === 'UNAVAILABLE' && chart.points.length) issue(ctx, 'Unavailable chart has no points');
  });
  const Record = z.strictObject({
    code: Code, name: z.string(), category: z.string().nullable(), comment_tr: z.string().min(1),
    d1_state: z.enum(D1_STATES), d1: D1, chart: Chart,
    date_context: z.strictObject({has_positive_price_on_or_before_cutoff: z.boolean()}), evidence: z.array(Hash),
  }).superRefine((record, ctx) => {
    if (expectedState(record.d1) !== record.d1_state) issue(ctx, 'd1_state must follow the D1 finding');
    if (!record.date_context.has_positive_price_on_or_before_cutoff && (record.d1_state !== 'UNAVAILABLE' || record.chart.status !== 'UNAVAILABLE')) issue(ctx, 'A fund without a price at the cutoff has no D1 or chart');
    if (record.evidence.some((value, i) => i > 0 && value <= record.evidence[i - 1])) issue(ctx, 'Evidence must be sorted and unique');
    if (deniedTerms(record.comment_tr).length || dateMentions(record.comment_tr).length) issue(ctx, 'Dated comments carry no fixed date or denylisted wording');
  });
  const Source = z.strictObject({
    source_id: Hash, kind: z.enum(DATED_SOURCE_KINDS), label: z.string(), fund_code: Code.nullable(), sha256: Hash, file_name: z.string(),
    media_type: z.enum(['application/json', 'text/plain', 'application/octet-stream']), pdf_available: z.literal(false),
    published_at: Timestamp.nullable(), retrieved_at: Timestamp.nullable(),
    historical_availability: z.literal('UNKNOWN'), rights_status: z.literal('UNKNOWN'), origin: z.literal('HISTORICAL_REPLAY'),
    disclosure_id: z.null(), disclosure_url: z.null(),
  }).superRefine((source, ctx) => {
    // retrieved_at is the archive retrieval instant, never an observation date; it is not displayed.
    if (source.published_at !== null && Date.parse(source.published_at) > Date.parse(cutoffAt)) issue(ctx, 'Source published after the cutoff');
    if (source.kind === 'PRICE' && source.fund_code === null) issue(ctx, 'Price sources require a fund code');
  });
  const ids = {index_id: Hash, immutable_bundle_id: Hash};
  const List = z.strictObject({...metadata, ...ids, funds: z.array(Record).length(100)}).superRefine((payload, ctx) => {
    if (new Set(payload.funds.map(fund => fund.code)).size !== 100) issue(ctx, 'Fund codes must be unique');
    const rank = (fund: typeof payload.funds[number]) => STATE_ORDER[fund.d1_state];
    if (payload.funds.some((fund, i) => i > 0 && (rank(payload.funds[i - 1]) > rank(fund) || (rank(payload.funds[i - 1]) === rank(fund) && payload.funds[i - 1].code >= fund.code)))) issue(ctx, 'Funds must follow the registered order');
  });
  const Summary = z.strictObject({...metadata, ...ids, summary: DatedSummarySchema, threshold_provenance: ThresholdProvenanceSchema, snapshot: SnapshotSchema});
  const Detail = z.strictObject({...metadata, ...ids, fund: Record, sources: z.array(Source)});
  return {D1, Chart, Record, Source, List, Summary, Detail};
}

const cache = new Map<string, ReturnType<typeof build>>();
/** Schemas for one registered-range cutoff; anything else is refused before use. */
export function datedSchemas(date: string): ReturnType<typeof build> {
  if (!isCalendarDate(date) || !isInDatedRange(date)) throw new RangeError('Dated schemas need a canonical date inside the registered range');
  let schemas = cache.get(date);
  if (!schemas) { schemas = build(date); cache.set(date, schemas); }
  return schemas;
}

type Schemas = ReturnType<typeof build>;
export type DateIndex = z.infer<typeof DateIndexSchema>;
export type DateEntry = DateIndex['entries'][number];
export type DatedRecord = z.infer<Schemas['Record']>;
export type DatedSource = z.infer<Schemas['Source']>;
export type DatedSummary = z.infer<typeof DatedSummarySchema>;
export type DatedListResponse = z.infer<Schemas['List']>;
export type DatedSummaryResponse = z.infer<Schemas['Summary']>;
export type DatedDetailResponse = z.infer<Schemas['Detail']>;
export type ThresholdProvenance = z.infer<typeof ThresholdProvenanceSchema>;
