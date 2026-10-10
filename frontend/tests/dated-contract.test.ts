import {describe, it, expect} from 'vitest';
import {DateIndexSchema, datedSchemas, cutoffAtFor, isCalendarDate, isInDatedRange, DatedSummarySchema, SnapshotSchema} from '../src/lib/dated-contract';
import {syntheticBundle, syntheticIndex, SYNTHETIC_DATES} from '../src/lib/dated-synthetic';
import {FIXTURE_DATES, datedFixture, fixtureCode, indexFixture} from './fixtures/dated-research';

const clone = <T>(value: T): T => structuredClone(value);
const EARLY = FIXTURE_DATES[0];
const LATE = FIXTURE_DATES[11];

describe('date index', () => {
  it('accepts the 12-entry ordered index ending at the window end', () => {
    expect(DateIndexSchema.safeParse(indexFixture()).success).toBe(true);
    expect(DateIndexSchema.safeParse(syntheticIndex).success).toBe(true);
  });
  it('rejects wrong counts, order, ending, months, cutoffs and duplicate bundles', () => {
    const cases: ((index: ReturnType<typeof indexFixture>) => void)[] = [
      index => { index.entries.pop(); },
      index => { index.entries.push({...index.entries[11], date: '2026-09-17'}); },
      index => { [index.entries[0], index.entries[1]] = [index.entries[1], index.entries[0]]; },
      index => { index.entries[11] = {...index.entries[11], date: '2026-09-15', cutoff_at: cutoffAtFor('2026-09-15')}; },
      index => { index.entries[0] = {...index.entries[0], date: '2025-10-05', cutoff_at: cutoffAtFor('2025-10-05')}; },
      index => { index.entries[3] = {...index.entries[3], date: '2026-02-02', cutoff_at: cutoffAtFor('2026-02-02')}; },
      index => { index.entries[2] = {...index.entries[2], cutoff_at: '2025-12-31T23:59:59+00:00'}; },
      index => { index.entries[2] = {...index.entries[2], cutoff_at: '2025-12-31T20:59:59Z'}; },
      index => { index.entries[4] = {...index.entries[4], bundle_id: index.entries[5].bundle_id}; },
      index => { (index as Record<string, unknown>).default_date = '2026-08-31'; },
      index => { (index as Record<string, unknown>).summary = {}; },
      index => { (index.entries[0] as Record<string, unknown>).d1_eligible_crossing = 1; },
    ];
    for (const mutate of cases) { const index = clone(indexFixture()); mutate(index); expect(DateIndexSchema.safeParse(index).success).toBe(false); }
  });
});

describe('per-cutoff factory', () => {
  it('refuses non-canonical or out-of-range dates before building', () => {
    for (const date of ['2025-10-05', '2026-09-17', '2026-02-30', '2026-1-31', '20260131', '']) expect(() => datedSchemas(date)).toThrow(RangeError);
    expect(isCalendarDate('2026-02-29')).toBe(false);
    expect(isInDatedRange('2025-10-06') && isInDatedRange('2026-09-16')).toBe(true);
  });
  it('accepts every fixture and synthetic date payload', () => {
    for (const date of FIXTURE_DATES) {
      const fixture = datedFixture(date); const schemas = datedSchemas(date);
      expect(schemas.List.safeParse(fixture.list).success).toBe(true);
      expect(schemas.Summary.safeParse(fixture.summary).success).toBe(true);
      expect(schemas.Detail.safeParse(fixture.detail(fixtureCode(0))).success).toBe(true);
    }
    for (const date of SYNTHETIC_DATES) expect(syntheticBundle(date).list.funds).toHaveLength(100);
  });
  it('binds metadata to its own cutoff and rejects another date', () => {
    const fixture = datedFixture(EARLY);
    expect(datedSchemas(LATE).List.safeParse(fixture.list).success).toBe(false);
    for (const change of [{cutoff_at: cutoffAtFor(LATE)}, {cutoff_date: LATE}, {cutoff_at: `${EARLY}T23:59:59Z`}, {findings_scope: 'ALL'}, {knowledge_basis: 'POINT_IN_TIME'}, {point_in_time_verified: true}, {origin: 'LIVE'}]) {
      expect(datedSchemas(EARLY).List.safeParse({...fixture.list, ...change}).success).toBe(false);
    }
  });
  it('rejects nested dates after the payload cutoff', () => {
    const fixture = datedFixture(EARLY); const schemas = datedSchemas(EARLY);
    const fresh = fixture.list.funds.find(fund => fund.d1_state === 'ELIGIBLE_NO_CROSSING')!;
    const after = '2025-11-01';
    for (const change of [{latest_contributing_at: after}, {metric_period: {start: fresh.d1.metric_period.start, end: after}}]) {
      expect(schemas.Record.safeParse({...fresh, d1: {...fresh.d1, ...change}}).success).toBe(false);
    }
    const chart = clone(fresh.chart) as {points: unknown[]}; chart.points.push({date: after, fund: '104', peers: '102'});
    expect(schemas.Record.safeParse({...fresh, chart}).success).toBe(false);
    const detail = fixture.detail(fresh.code)!;
    detail.sources[0] = {...detail.sources[0], published_at: '2025-11-01T00:00:00+03:00'} as never;
    expect(schemas.Detail.safeParse(detail).success).toBe(false);
    const later = datedFixture(LATE).detail(fresh.code)!;
    expect(datedSchemas(LATE).Detail.safeParse(later).success).toBe(true);
  });
  it('measures freshness against the selected date and keeps stale out of eligibility', () => {
    const schemas = datedSchemas(EARLY);
    const fixture = datedFixture(EARLY);
    const fresh = fixture.list.funds.find(fund => fund.d1_state === 'ELIGIBLE_NO_CROSSING')!;
    const stale = fixture.list.funds.find(fund => fund.d1_state === 'STALE')!;
    expect(schemas.Record.safeParse({...fresh, d1: {...fresh.d1, latest_contributing_at: '2025-10-30'}}).success).toBe(false);
    expect(schemas.Record.safeParse({...fresh, d1: {...fresh.d1, latest_contributing_at: '2025-10-30', freshness: 'STALE'}}).success).toBe(false);
    expect(schemas.Record.safeParse({...fresh, d1_state: 'STALE', d1: {...fresh.d1, latest_contributing_at: '2025-10-30', freshness: 'STALE'}}).success).toBe(true);
    expect(schemas.Record.safeParse({...stale, d1_state: 'ELIGIBLE_CROSSING'}).success).toBe(false);
    expect(schemas.Record.safeParse({...stale, d1: {...stale.d1, freshness: 'FRESH'}}).success).toBe(false);
  });
  it('enforces the strict crossing, unavailable unknowns and the unpriced rule', () => {
    const schemas = datedSchemas(EARLY);
    const funds = datedFixture(EARLY).list.funds;
    const crossing = funds.find(fund => fund.d1_state === 'ELIGIBLE_CROSSING')!;
    expect(schemas.Record.safeParse({...crossing, d1: {...crossing.d1, statistic: crossing.d1.threshold}}).success).toBe(false);
    expect(schemas.Record.safeParse({...crossing, d1_state: 'ELIGIBLE_NO_CROSSING', d1: {...crossing.d1, statistic: crossing.d1.threshold, research_screen: 'NO_CROSSING'}}).success).toBe(true);
    const unpriced = funds.find(fund => !fund.date_context.has_positive_price_on_or_before_cutoff)!;
    expect(unpriced.d1_state).toBe('UNAVAILABLE');
    expect(schemas.Record.safeParse({...unpriced, d1: {...unpriced.d1, statistic: '0.001'}}).success).toBe(false);
    expect(schemas.Record.safeParse({...unpriced, d1: {...unpriced.d1, freshness: 'STALE'}}).success).toBe(false);
    expect(schemas.Record.safeParse({...crossing, date_context: {has_positive_price_on_or_before_cutoff: false}}).success).toBe(false);
  });
  it('rejects flow, concentration and assessment keys and KAP sources', () => {
    const fixture = datedFixture(LATE); const schemas = datedSchemas(LATE); const fund = fixture.list.funds[0];
    for (const extra of [{flow: {}}, {concentration: null}, {assessment: 'FULL'}, {eligible_crossings: 1}]) expect(schemas.Record.safeParse({...fund, ...extra}).success).toBe(false);
    const detail = fixture.detail(fund.code)!;
    for (const change of [{kind: 'KAP_PDF'}, {kind: 'KAP_SERIES'}, {pdf_available: true}, {disclosure_id: '1'}, {disclosure_url: 'https://www.kap.org.tr/tr/Bildirim/1'}, {media_type: 'application/pdf'}]) {
      expect(schemas.Detail.safeParse({...detail, sources: [{...detail.sources[0], ...change}, ...detail.sources.slice(1)]}).success).toBe(false);
    }
    expect(schemas.Summary.safeParse({...fixture.summary, summary: {...fixture.summary.summary, flow_crossing: 0}}).success).toBe(false);
  });
  it('rejects comments with fixed dates or denylisted wording but keeps the exact note', () => {
    const schemas = datedSchemas(LATE); const fund = datedFixture(LATE).list.funds.find(item => item.d1_state === 'ELIGIBLE_NO_CROSSING')!;
    expect(schemas.Record.safeParse(fund).success).toBe(true);
    for (const comment_tr of ['16 Eylül tarihinde eşik aşıldı.', 'Ağustos sonunda eşik aşıldı.', '2026-09-16 kesitinde aşım.', 'Bu bir erken uyarı.', 'Fon güvenli görünüyor.', 'Tasfiye listesinde.', 'SPK kararı.', 'Getiri tahmini.']) {
      expect(schemas.Record.safeParse({...fund, comment_tr}).success).toBe(false);
    }
  });
  it('enforces 100 unique records in the registered order', () => {
    const fixture = datedFixture(LATE); const schemas = datedSchemas(LATE);
    const funds = clone(fixture.list.funds);
    expect(schemas.List.safeParse({...fixture.list, funds: funds.slice(1)}).success).toBe(false);
    expect(schemas.List.safeParse({...fixture.list, funds: [...funds.slice(0, 99), funds[0]]}).success).toBe(false);
    expect(schemas.List.safeParse({...fixture.list, funds: [...funds].reverse()}).success).toBe(false);
    const swapped = [...funds]; [swapped[0], swapped[1]] = [swapped[1], swapped[0]];
    expect(schemas.List.safeParse({...fixture.list, funds: swapped}).success).toBe(false);
  });
  it('checks summary arithmetic and the snapshot bound', () => {
    const summary = datedFixture(EARLY).summary.summary;
    expect(DatedSummarySchema.safeParse(summary).success).toBe(true);
    expect(DatedSummarySchema.safeParse({...summary, d1_stale: summary.d1_stale + 1}).success).toBe(false);
    expect(DatedSummarySchema.safeParse({...summary, no_price_at_cutoff: summary.d1_unavailable + 1}).success).toBe(false);
    const snapshot = datedFixture(EARLY).summary.snapshot;
    expect(SnapshotSchema.safeParse(snapshot).success).toBe(true);
    expect(SnapshotSchema.safeParse({...snapshot, latest_retrieved_at: '2026-10-07T08:52:13+00:00'}).success).toBe(false);
    expect(SnapshotSchema.safeParse({...snapshot, bound: '2026-10-08T00:00:00+00:00'}).success).toBe(false);
  });
});
