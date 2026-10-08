import {z} from 'zod';
import {absoluteDecimal, compareDecimal} from './decimal-compare';

const CUTOFF_DAY = '2026-09-16';
const CUTOFF_AT = '2026-09-16T23:59:59+03:00';
const Decimal = z.string().regex(/^[+-]?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?$/)
  .refine(value => Number.isFinite(Number(value)), 'A decimal must be finite');
const validDay = (value: string) => !Number.isNaN(Date.parse(value)) && new Date(value).toISOString().slice(0, 10) === value;
const Day = z.string().regex(/^\d{4}-\d{2}-\d{2}$/).refine(validDay, 'Invalid date');
const Period = z.string().regex(/^\d{4}-\d{2}(?:-\d{2})?$/)
  .refine(value => validDay(value.length === 7 ? value + '-01' : value), 'Invalid period');
const Timestamp = z.string().regex(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/)
  .refine(value => !Number.isNaN(Date.parse(value)) && validDay(value.slice(0, 10)) && Number(value.slice(11, 13)) < 24 && Number(value.slice(14, 16)) < 60 && Number(value.slice(17, 19)) < 60, 'Invalid timestamp');
const Hash = z.string().regex(/^[a-f0-9]{64}$/);
const Code = z.string().regex(/^[A-Z0-9]{3}$/);
const Count = z.number().int().nonnegative();
const Finding = z.strictObject({
  arithmetic_status: z.enum(['AVAILABLE', 'UNAVAILABLE']),
  research_screen: z.enum(['CROSSING', 'NO_CROSSING', 'UNKNOWN']),
  freshness: z.enum(['FRESH', 'STALE', 'UNKNOWN']),
  production_status: z.literal('ABSTAINED'),
  missing_reasons: z.array(z.string()), qualifications: z.array(z.string()),
  metric_period: z.strictObject({start: Period.nullable(), end: Period.nullable()}),
  units: z.strictObject({statistic: z.enum(['DAILY_LOG_RETURN', 'RATIO']), threshold: z.enum(['DAILY_LOG_RETURN', 'RATIO'])}),
  input_refs: z.array(Hash), statistic: Decimal.nullable(), threshold: Decimal.nullable(),
});
function issue(ctx: z.RefinementCtx, message: string) { ctx.addIssue({code: 'custom', message}); }
function validateFinding(finding: z.infer<typeof Finding>, ctx: z.RefinementCtx) {
  if (finding.arithmetic_status === 'UNAVAILABLE') {
    if (finding.statistic !== null || finding.research_screen !== 'UNKNOWN') issue(ctx, 'Unavailable arithmetic must remain unknown');
  } else if (finding.statistic === null || finding.threshold === null || finding.research_screen === 'UNKNOWN') {
    issue(ctx, 'Available arithmetic requires statistic, threshold and screen');
  }
  const {start, end} = finding.metric_period;
  if ([start, end].some(period => period !== null && period > CUTOFF_DAY) || (start && end && start > end)) issue(ctx, 'Invalid finding period or future period');
}
export const D1Schema = Finding.extend({
  usable_observations: Count, window_positions: Count, eligible_peers: Count,
  latest_contributing_at: Day.nullable(),
}).superRefine((finding, ctx) => {
  validateFinding(finding, ctx);
  if (finding.units.statistic !== 'DAILY_LOG_RETURN' || finding.units.threshold !== 'DAILY_LOG_RETURN') issue(ctx, 'D1 uses daily log return units');
  if (finding.window_positions > 60 || finding.usable_observations > finding.window_positions) issue(ctx, 'Invalid D1 observation coverage');
  if (finding.latest_contributing_at && finding.latest_contributing_at > CUTOFF_DAY) issue(ctx, 'Future D1 observation');
  if (finding.arithmetic_status === 'AVAILABLE') {
    const {start, end} = finding.metric_period;
    if (finding.usable_observations < 50 || finding.eligible_peers < 10 || !finding.latest_contributing_at || !start || !end) issue(ctx, 'Available D1 requires its window, latest observation and coverage');
    if (finding.latest_contributing_at && start && end && (finding.latest_contributing_at < start || finding.latest_contributing_at > end)) issue(ctx, 'D1 latest observation must be in its window');
    if (finding.freshness !== (finding.latest_contributing_at === CUTOFF_DAY ? 'FRESH' : 'STALE')) issue(ctx, 'D1 freshness mismatch');
    if (finding.statistic !== null && finding.threshold !== null) {
      const expected = compareDecimal(finding.statistic, finding.threshold) > 0 ? 'CROSSING' : 'NO_CROSSING';
      if (finding.research_screen !== expected) issue(ctx, 'D1 uses a strict greater-than crossing');
    }
  }
});
const Endpoint = z.strictObject({
  period: Period, source_id: Hash, record_sha256: Hash,
  record_hash_basis: z.literal('CONSUMED_ENDPOINT_FIELDS'),
  published_at: Timestamp.nullable(), published_at_raw: z.string().nullable(),
  historical_availability: z.literal('UNKNOWN'),
});
export const FlowSchema = Finding.extend({
  direction: z.enum(['INFLOW_ESTIMATE', 'OUTFLOW_ESTIMATE', 'NONE', 'UNKNOWN']),
  previous_assets: Decimal.nullable(), current_assets: Decimal.nullable(),
  previous_nav: Decimal.nullable(), current_nav: Decimal.nullable(), residual: Decimal.nullable(),
  endpoint_refs: z.array(Endpoint),
  input_units: z.strictObject({assets: z.literal('REPORT_CURRENCY'), nav: z.literal('REPORT_CURRENCY_PER_UNIT')}),
}).superRefine((finding, ctx) => {
  validateFinding(finding, ctx);
  if (finding.units.statistic !== 'RATIO' || finding.units.threshold !== 'RATIO') issue(ctx, 'Flow uses ratio units');
  if (finding.metric_period.start !== '2026-07' || finding.metric_period.end !== '2026-08') issue(ctx, 'Fixed monthly period required');
  if (finding.arithmetic_status === 'UNAVAILABLE') {
    if (finding.direction !== 'UNKNOWN') issue(ctx, 'Unavailable flow direction must remain unknown');
    return;
  }
  if ([finding.previous_assets, finding.current_assets, finding.previous_nav, finding.current_nav, finding.residual].some(value => value === null)) issue(ctx, 'Available flow must retain every input');
  if ([finding.previous_assets, finding.previous_nav, finding.current_nav].some(value => value !== null && compareDecimal(value, '0') <= 0) || (finding.current_assets !== null && compareDecimal(finding.current_assets, '0') < 0)) issue(ctx, 'Invalid flow input sign');
  if (finding.freshness !== 'FRESH' || finding.endpoint_refs.length !== 2 || finding.endpoint_refs[0]?.period !== '2026-07' || finding.endpoint_refs[1]?.period !== '2026-08') issue(ctx, 'Available flow must retain the two monthly endpoints');
  if (finding.endpoint_refs.some(endpoint => endpoint.published_at === null || Date.parse(endpoint.published_at) > Date.parse(CUTOFF_AT))) issue(ctx, 'Available flow requires known publication before cutoff');
  if (finding.threshold === null || compareDecimal(finding.threshold, '0.10') !== 0) issue(ctx, 'Fixed flow threshold must be 0.10');
  if (finding.statistic !== null) {
    const sign = compareDecimal(finding.statistic, '0');
    const expectedDirection = sign > 0 ? 'INFLOW_ESTIMATE' : sign < 0 ? 'OUTFLOW_ESTIMATE' : 'NONE';
    const expectedScreen = compareDecimal(absoluteDecimal(finding.statistic), '0.10') >= 0 ? 'CROSSING' : 'NO_CROSSING';
    if (finding.direction !== expectedDirection || finding.research_screen !== expectedScreen) issue(ctx, 'Flow direction and screen must match the signed estimate');
    if (finding.residual !== null && Math.sign(compareDecimal(finding.residual, '0')) !== Math.sign(sign)) issue(ctx, 'Flow residual and rate signs must agree');
  }
});
export const ChartSchema = z.strictObject({
  status: z.enum(['AVAILABLE', 'UNAVAILABLE']), reason: z.string().nullable(),
  baseline_date: Day.nullable(), unit: z.literal('INDEX_100'),
  points: z.array(z.strictObject({date: Day, fund: Decimal.nullable(), peers: Decimal.nullable()})),
  peer_count: Count,
}).superRefine((chart, ctx) => {
  const dates = chart.points.map(point => point.date);
  if (dates.some((date, index) => date > CUTOFF_DAY || (index > 0 && date <= dates[index - 1]))) issue(ctx, 'Chart must use unique ordered cutoff dates');
  if (chart.status === 'AVAILABLE' && (chart.peer_count < 10 || !dates.length || chart.baseline_date !== dates[0])) issue(ctx, 'Chart needs a common baseline and 10 peers');
});
export const FundSchema = z.strictObject({
  code: Code, name: z.string(), category: z.string().nullable(), comment_tr: z.string(),
  assessment: z.enum(['FULL', 'PARTIAL', 'UNAVAILABLE']), eligible_crossings: Count.max(2),
  d1: D1Schema, flow: FlowSchema, chart: ChartSchema, evidence: z.array(Hash),
}).superRefine((fund, ctx) => {
  const findings = [fund.d1, fund.flow];
  const eligible = findings.map(finding => finding.arithmetic_status === 'AVAILABLE' && finding.freshness === 'FRESH');
  const count = findings.filter((finding, index) => eligible[index] && finding.research_screen === 'CROSSING').length;
  const assessment = eligible.every(Boolean) ? 'FULL' : eligible.some(Boolean) ? 'PARTIAL' : 'UNAVAILABLE';
  if (count !== fund.eligible_crossings || assessment !== fund.assessment) issue(ctx, 'Finding count and assessment must match eligible inputs');
});
export const SourceSchema = z.strictObject({
  source_id: Hash, kind: z.enum(['PRICE', 'KAP_SERIES', 'KAP_PDF', 'SNAPSHOT', 'CALIBRATION', 'UNIVERSE', 'PROTOCOL', 'CODE']),
  label: z.string(), fund_code: Code.nullable(), sha256: Hash, file_name: z.string(),
  media_type: z.enum(['application/json', 'application/pdf', 'text/plain', 'application/octet-stream']),
  pdf_available: z.boolean(), published_at: Timestamp.nullable(), retrieved_at: Timestamp.nullable(),
  historical_availability: z.literal('UNKNOWN'), rights_status: z.literal('UNKNOWN'), origin: z.literal('HISTORICAL_REPLAY'),
  disclosure_id: z.string().regex(/^[0-9]+$/).nullable(), disclosure_url: z.string().nullable(),
}).superRefine((source, ctx) => {
  const expected = source.disclosure_id === null ? null : `https://www.kap.org.tr/tr/Bildirim/${source.disclosure_id}`;
  if (source.disclosure_url !== expected) issue(ctx, 'KAP disclosure URL must use the official domain');
  if (source.pdf_available !== (source.kind === 'KAP_PDF' && source.media_type === 'application/pdf')) issue(ctx, 'PDF availability must match source type');
  if (['PRICE', 'KAP_SERIES', 'KAP_PDF'].includes(source.kind) && source.fund_code === null) issue(ctx, 'Fund-specific sources require a valid code');
});
const Metadata = z.strictObject({
  origin: z.literal('HISTORICAL_REPLAY'), analysis_mode: z.literal('EXPLORATORY_ARCHIVE'),
  cutoff_at: z.literal(CUTOFF_AT), cutoff_semantics: z.literal('RECORDED_SOURCE_DATE_FILTER'),
  point_in_time_verified: z.literal(false), historical_availability: z.literal('UNKNOWN'),
  rights_status: z.literal('UNKNOWN'), universe_basis: z.literal('OCTOBER_2026_INVESTOR_SNAPSHOT'),
  category_basis: z.literal('CURRENT_SNAPSHOT'), immutable_bundle_id: Hash,
});
export const SummarySchema = z.strictObject({
  total: Count, fully_assessable: Count, partially_assessable: Count, unavailable: Count,
  two_findings: Count, one_finding: Count, no_findings: Count, unassessable_no_findings: Count,
  d1_assessable: Count, flow_assessable: Count, d1_stale: Count, denominator: z.literal(100),
}).superRefine((summary, ctx) => {
  if (summary.total !== 100 || summary.fully_assessable + summary.partially_assessable + summary.unavailable !== summary.total || summary.two_findings + summary.one_finding + summary.no_findings + summary.unassessable_no_findings !== summary.total) issue(ctx, 'Summary counts must match the fixed universe');
});
export const ListResponseSchema = Metadata.extend({funds: z.array(FundSchema).length(100)})
  .refine(payload => new Set(payload.funds.map(fund => fund.code)).size === 100, 'Fund codes must be unique');
export const DetailResponseSchema = Metadata.extend({fund: FundSchema, sources: z.array(SourceSchema)});
export const SummaryResponseSchema = Metadata.extend({summary: SummarySchema});
export type Fund = z.infer<typeof FundSchema>;
export type Source = z.infer<typeof SourceSchema>;
export type ResearchSummary = z.infer<typeof SummarySchema>;
export type DetailResponse = z.infer<typeof DetailResponseSchema>;
export type ListResponse = z.infer<typeof ListResponseSchema>;
