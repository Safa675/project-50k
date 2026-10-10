// Golden bodies produced by the Python dated API (tests/unit/test_dated_api_golden.py).
// The Python test proves the API still serves exactly these bodies; this test proves the
// browser contract and loaders accept them, so neither side can drift silently.
// Synthetic data only; path-derived IDs are 64-hex placeholders (see the fixture header).
import {readFileSync} from 'node:fs';
import {afterEach, describe, expect, it, vi} from 'vitest';
import {z} from 'zod';
import {DATED_API_BASE, loadDateIndex, loadDatedDetail, loadDatedList} from '../src/lib/dated-api';
import {BUNDLE_PATTERN, DateIndexSchema, cutoffAtFor, datedSchemas} from '../src/lib/dated-contract';
import {ResearchApiError, fetchValidated} from '../src/lib/research-api';

const API_PREFIX = '/research-dated/v1';
const ResponseSchema = z.strictObject({
  name: z.string(), kind: z.enum(['dates', 'summary', 'funds', 'detail', 'error']),
  date: z.string().nullable(), code: z.string().nullable(), path: z.string().startsWith(API_PREFIX),
  status: z.number().int(), body: z.record(z.string(), z.unknown()),
});
const GoldenSchema = z.object({schema: z.literal('p50k.dated-api-golden.v1'), responses: z.array(ResponseSchema).min(1)});
const golden = GoldenSchema.parse(JSON.parse(readFileSync(new URL('./fixtures/dated-api-golden.json', import.meta.url), 'utf8')));
type GoldenResponse = z.infer<typeof ResponseSchema>;

const successes = golden.responses.filter(item => item.kind !== 'error');
const errors = golden.responses.filter(item => item.kind === 'error');
const datesBody = successes.find(item => item.kind === 'dates')!.body;
const DATES = [...new Set(successes.flatMap(item => item.date === null ? [] : [item.date]))];

// The served error envelope (dated_models.DatedErrorResponse); the browser reads only error.message_tr.
const LABEL_KEYS = ['origin', 'analysis_mode', 'cutoff_semantics', 'point_in_time_verified', 'historical_availability', 'rights_status',
  'universe_basis', 'category_basis', 'knowledge_basis', 'findings_scope', 'date_rule'] as const;
const ErrorSchema = z.strictObject({
  ...Object.fromEntries(LABEL_KEYS.map(key => [key, z.literal(datesBody[key] as string | boolean)])),
  cutoff_at: z.string().nullable(), cutoff_date: z.string().nullable(), index_id: z.string().regex(BUNDLE_PATTERN).nullable(),
  immutable_bundle_id: z.null(), error: z.strictObject({code: z.string().regex(/^[A-Z_]+$/), message_tr: z.string().min(1)}),
}).refine(body => body.cutoff_date === null ? body.cutoff_at === null : body.cutoff_at === cutoffAtFor(body.cutoff_date), 'Error cutoff must match its date');

function schemaFor(item: GoldenResponse): z.ZodType {
  if (item.kind === 'dates') return DateIndexSchema;
  const schemas = datedSchemas(item.date!);
  return item.kind === 'summary' ? schemas.Summary : item.kind === 'funds' ? schemas.List : schemas.Detail;
}

/** Serves the golden bodies by path through the same-origin proxy prefix; anything else fails. */
function serveGolden() {
  const byPath = new Map(golden.responses.filter(item => item.kind !== 'error').map(item => [item.path.split('?')[0], item]));
  const index = DateIndexSchema.parse(datesBody);
  const calls: string[] = [];
  vi.stubGlobal('fetch', vi.fn(async (input: string) => {
    const url = new URL(input, 'http://127.0.0.1:3060');
    calls.push(url.pathname + url.search);
    expect(url.pathname.startsWith(DATED_API_BASE)).toBe(true);
    const item = byPath.get(url.pathname.replace('/api', ''));
    if (!item) throw new Error(`unexpected request ${url.pathname}`);
    if (item.date !== null) expect(url.searchParams.get('bundle')).toBe(index.entries.find(entry => entry.date === item.date)!.bundle_id);
    return new Response(JSON.stringify(item.body), {status: item.status, headers: {'content-type': 'application/json'}});
  }));
  return calls;
}

afterEach(() => vi.unstubAllGlobals());

describe('dated API golden fixture', () => {
  it('covers the index, two dates, every D1 state and two error statuses', () => {
    expect(DATES).toHaveLength(2);
    const states = successes.filter(item => item.kind === 'detail').map(item => (item.body.fund as {d1_state: string}).d1_state);
    expect(new Set(states)).toEqual(new Set(['ELIGIBLE_CROSSING', 'ELIGIBLE_NO_CROSSING', 'STALE', 'UNAVAILABLE']));
    expect(errors.map(item => item.status).sort()).toEqual([404, 409]);
    for (const item of successes) expect(item.status).toBe(200);
  });

  it('validates every 200 body with the browser schema for its own date', () => {
    for (const item of successes) {
      const result = schemaFor(item).safeParse(item.body);
      expect(result.success, `${item.name}: ${result.success ? '' : JSON.stringify(result.error.issues.slice(0, 3))}`).toBe(true);
      if (result.success) expect(result.data).toEqual(item.body);
    }
  });

  it('feeds the real loaders, including summary counts and source cross-checks', async () => {
    const calls = serveGolden();
    const index = await loadDateIndex();
    expect(index).toEqual(datesBody);
    for (const date of DATES) {
      const {list, summary} = await loadDatedList(index, date);
      expect(list.funds).toHaveLength(100);
      expect(summary.cutoff_date).toBe(date);
      for (const item of successes.filter(entry => entry.kind === 'detail' && entry.date === date)) {
        const {detail} = await loadDatedDetail(index, date, item.code!);
        expect(detail).toEqual(item.body);
        expect(list.funds.find(fund => fund.code === item.code)).toEqual(detail.fund);
      }
    }
    expect(calls.every(call => call.startsWith(DATED_API_BASE))).toBe(true);
  });

  it('parses error bodies as errors and surfaces their Turkish message', async () => {
    for (const item of errors) {
      expect(ErrorSchema.safeParse(item.body).success, item.name).toBe(true);
      expect(DateIndexSchema.safeParse(item.body).success).toBe(false);
      const schemas = datedSchemas(item.date!);
      for (const schema of [schemas.Summary, schemas.List, schemas.Detail]) expect(schema.safeParse(item.body).success).toBe(false);
      vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(item.body), {status: item.status, headers: {'content-type': 'application/json'}})));
      const failure = await fetchValidated(`/api${item.path}`, schemas.Summary).then(() => null, (error: unknown) => error);
      expect(failure).toBeInstanceOf(ResearchApiError);
      expect(failure).toMatchObject({code: 'HTTP', status: item.status, message: (item.body.error as {message_tr: string}).message_tr});
    }
  });
});
