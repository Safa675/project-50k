import {afterEach, describe, it, expect, vi} from 'vitest';
import {DatedApiError, DatedRequestError, datedErrorKind, loadDateIndex, loadDatedDetail, loadDatedList, resolveDateEntry} from '../src/lib/dated-api';
import {DateIndexSchema} from '../src/lib/dated-contract';
import {ResearchApiError} from '../src/lib/research-api';
import {FIXTURE_DATES, INDEX_ID, bundleIdFor, datedFixture, errorFixture, fixtureCode, indexFixture} from './fixtures/dated-research';

afterEach(() => vi.unstubAllGlobals());
const index = () => DateIndexSchema.parse(indexFixture());
const EARLY = FIXTURE_DATES[0];
const LATE = FIXTURE_DATES[11];
/** The rejection of a load that must fail. */
async function failure(promise: Promise<unknown>): Promise<Error> {
  try { await promise; } catch (error) { if (error instanceof Error) return error; throw error; }
  throw new Error('expected a rejection');
}

/** Route mock keyed by the full path including date and bundle; anything else fails the test. */
function routes(handler: (path: string, bundle: string | null) => unknown) {
  const calls: string[] = [];
  const mock = vi.fn(async (input: string, init?: RequestInit) => {
    const url = new URL(input, 'http://127.0.0.1:3060');
    calls.push(url.pathname + url.search);
    expect(init).toMatchObject({cache: 'no-store', credentials: 'omit'});
    const value = handler(url.pathname, url.searchParams.get('bundle'));
    if (value instanceof Response) return value;
    if (value === undefined) throw new Error(`unexpected request ${url.pathname}${url.search}`);
    return new Response(JSON.stringify(value), {status: 200, headers: {'content-type': 'application/json'}});
  });
  vi.stubGlobal('fetch', mock);
  return calls;
}
function serve(date: string, mutate?: (kind: 'funds' | 'summary' | 'detail', payload: Record<string, unknown>) => unknown) {
  const fixture = datedFixture(date);
  return routes((path, bundle) => {
    if (bundle !== bundleIdFor(date)) return undefined;
    const base = `/api/research-dated/v1/dates/${date}/`;
    if (path === base + 'funds') return mutate ? mutate('funds', structuredClone(fixture.list)) : fixture.list;
    if (path === base + 'summary') return mutate ? mutate('summary', structuredClone(fixture.summary)) : fixture.summary;
    if (path.startsWith(base + 'funds/')) { const detail = fixture.detail(path.slice((base + 'funds/').length)); return detail && (mutate ? mutate('detail', structuredClone(detail)) : detail); }
    return undefined;
  });
}

describe('index and date resolution', () => {
  it('loads the validated index without a bundle parameter', async () => {
    const calls = routes(path => path === '/api/research-dated/v1/dates' ? indexFixture() : undefined);
    expect((await loadDateIndex()).entries).toHaveLength(12);
    expect(calls).toEqual(['/api/research-dated/v1/dates']);
  });
  it('rejects an index carrying findings or a wrong entry count', async () => {
    routes(() => ({...indexFixture(), entries: indexFixture().entries.slice(1)}));
    await expect(loadDateIndex()).rejects.toMatchObject({code: 'INVALID_DATA'});
  });
  it('checks format and range before index membership, never a nearest date', () => {
    for (const value of ['2026-9-16', '2026-02-30', '2025-10-05', '2026-09-17', 'x', '']) {
      expect(() => resolveDateEntry(index(), value)).toThrow(expect.objectContaining({code: 'DATE_INVALID'}));
    }
    for (const value of ['2025-10-30', '2026-09-15', '2025-10-06']) expect(() => resolveDateEntry(index(), value)).toThrow(expect.objectContaining({code: 'DATE_NOT_REGISTERED'}));
    expect(resolveDateEntry(index(), EARLY).bundle_id).toBe(bundleIdFor(EARLY));
  });
  it('makes no request for an invalid, unregistered or mismatched date', async () => {
    const calls = routes(() => undefined);
    await expect(loadDatedList(index(), '2026-02-30')).rejects.toBeInstanceOf(DatedRequestError);
    await expect(loadDatedList(index(), '2026-09-15')).rejects.toBeInstanceOf(DatedRequestError);
    await expect(loadDatedList(index(), EARLY, undefined, bundleIdFor(LATE))).rejects.toMatchObject({code: 'BUNDLE_CHANGED'});
    await expect(loadDatedList(index(), EARLY, undefined, 'not-a-bundle')).rejects.toMatchObject({code: 'BUNDLE_CHANGED'});
    await expect(loadDatedDetail(index(), EARLY, '../x')).rejects.toMatchObject({status: 404});
    expect(calls).toEqual([]);
  });
});

describe('dated list', () => {
  it('requests the indexed bundle for the selected date and recounts the summary', async () => {
    const calls = serve(EARLY);
    const data = await loadDatedList(index(), EARLY, undefined, bundleIdFor(EARLY));
    expect(data.list.funds).toHaveLength(100);
    expect(data.summary.summary.no_price_at_cutoff).toBe(3);
    expect(calls.sort()).toEqual([`/api/research-dated/v1/dates/${EARLY}/funds?bundle=${bundleIdFor(EARLY)}`, `/api/research-dated/v1/dates/${EARLY}/summary?bundle=${bundleIdFor(EARLY)}`]);
  });
  it('rejects a response for another date or bundle, another index and wrong counts', async () => {
    const other = datedFixture(LATE);
    const cases: [(kind: string, payload: Record<string, unknown>) => unknown, string][] = [
      [(kind, payload) => kind === 'funds' ? {...payload, immutable_bundle_id: bundleIdFor(LATE)} : payload, 'BUNDLE_CHANGED'],
      [(kind, payload) => kind === 'summary' ? {...payload, index_id: 'f'.repeat(64)} : payload, 'BUNDLE_CHANGED'],
      [(kind, payload) => kind === 'funds' ? other.list : payload, 'INVALID_DATA'],
      [(kind, payload) => kind === 'summary' ? {...payload, summary: {...(payload.summary as object), d1_stale: 0, d1_eligible_no_crossing: (payload.summary as {d1_eligible_no_crossing: number}).d1_eligible_no_crossing + 1}} : payload, 'INVALID_DATA'],
      [(kind, payload) => kind === 'summary' ? {...payload, summary: {...(payload.summary as object), no_price_at_cutoff: 0}} : payload, 'INVALID_DATA'],
    ];
    for (const [mutate, code] of cases) {
      serve(EARLY, mutate);
      await expect(loadDatedList(index(), EARLY)).rejects.toMatchObject({code});
    }
  });
  it('carries API errors and 409 context mismatches as bounded Turkish errors', async () => {
    routes(() => new Response(JSON.stringify(errorFixture(409, 'CONTEXT_MISMATCH', 'Paket uyuşmuyor.', EARLY).body), {status: 409}));
    await expect(loadDatedList(index(), EARLY)).rejects.toMatchObject({status: 409, message: 'Paket uyuşmuyor.'});
    routes(() => new Response('<html>raw</html>', {status: 503}));
    await expect(loadDatedList(index(), EARLY)).rejects.toBeInstanceOf(ResearchApiError);
  });
});

describe('dated detail', () => {
  it('accepts the selected fund with exactly its referenced sources', async () => {
    serve(LATE);
    const {detail} = await loadDatedDetail(index(), LATE, fixtureCode(5), undefined, bundleIdFor(LATE));
    expect(detail.fund.code).toBe('X05');
    expect(detail.index_id).toBe(INDEX_ID);
  });
  it('rejects another fund, unreferenced or missing sources and a foreign bundle, each by its own guard', async () => {
    const extra = datedFixture(LATE).detail('X09')!.sources.at(-1)!;
    // X06's complete, self-consistent payload: only the fund-code guard can reject it.
    const otherFund = datedFixture(LATE).detail('X06')!;
    const path = `/api/research-dated/v1/dates/${LATE}/funds/X05?bundle=${bundleIdFor(LATE)}`;
    const cases: [(payload: Record<string, unknown>) => unknown, string, string][] = [
      [() => structuredClone(otherFund), 'INVALID_DATA', 'API yanıtı seçilen fonla uyuşmuyor.'],
      [payload => ({...payload, sources: [...(payload.sources as unknown[]), extra]}), 'INVALID_DATA', 'Fonun kaynak kayıtları araştırma paketiyle uyuşmuyor.'],
      [payload => ({...payload, sources: (payload.sources as unknown[]).slice(1)}), 'INVALID_DATA', 'Fonun kaynak kayıtları araştırma paketiyle uyuşmuyor.'],
      [payload => ({...payload, immutable_bundle_id: bundleIdFor(EARLY)}), 'BUNDLE_CHANGED', 'Tarih, paket ve dizin yanıtları birbiriyle uyuşmuyor. Sonuçlar birleştirilemez.'],
      [payload => ({...payload, index_id: 'f'.repeat(64)}), 'BUNDLE_CHANGED', 'Tarih, paket ve dizin yanıtları birbiriyle uyuşmuyor. Sonuçlar birleştirilemez.'],
      [payload => ({...payload, cutoff_date: EARLY}), 'INVALID_DATA', 'Araştırma yanıtı beklenen veri sözleşmesine uymuyor.'],
    ];
    for (const [mutate, code, message] of cases) {
      const calls = serve(LATE, (_kind, payload) => mutate(payload));
      const error = await failure(loadDatedDetail(index(), LATE, 'X05'));
      expect(error).toBeInstanceOf(ResearchApiError);
      expect(error).toMatchObject({code, message});
      expect(calls).toEqual([path]);
    }
  });
  it('accepts an unchanged detail through the same mock, so each rejection above is the mutation', async () => {
    const calls = serve(LATE, (_kind, payload) => payload);
    expect((await loadDatedDetail(index(), LATE, 'X05')).detail.fund.code).toBe('X05');
    expect(calls).toEqual([`/api/research-dated/v1/dates/${LATE}/funds/X05?bundle=${bundleIdFor(LATE)}`]);
  });
});

describe('dated error codes', () => {
  const reply = (status: number, code: string, message: string) => routes(() => new Response(JSON.stringify(errorFixture(status, code, message, EARLY).body), {status}));
  it('keeps the API error code that fetchValidated drops', async () => {
    reply(404, 'DATE_NOT_REGISTERED', 'Bu tarih için kayıtlı bir arşiv kesiti yok.');
    const error = await failure(loadDatedList(index(), EARLY));
    expect(error).toBeInstanceOf(DatedApiError);
    expect(error).toBeInstanceOf(ResearchApiError);
    expect(error).toMatchObject({code: 'HTTP', status: 404, apiCode: 'DATE_NOT_REGISTERED', message: 'Bu tarih için kayıtlı bir arşiv kesiti yok.'});
  });
  it('maps only FUND_NOT_FOUND to not-found and DATE_NOT_REGISTERED to an unregistered date', async () => {
    const cases: [number, string, string][] = [
      [404, 'DATE_NOT_REGISTERED', 'unregistered-date'], [404, 'FUND_NOT_FOUND', 'not-found'], [404, 'NOT_FOUND', 'bundle-error'],
      [400, 'DATE_INVALID', 'invalid-date'], [409, 'CONTEXT_MISMATCH', 'mismatch'], [503, 'INDEX_UNAVAILABLE', 'bundle-error'],
    ];
    for (const [status, code, kind] of cases) {
      const calls = reply(status, code, 'Örnek hata.');
      const error = await failure(loadDatedDetail(index(), EARLY, 'X05'));
      expect([status, code, datedErrorKind(error)]).toEqual([status, code, kind]);
      expect(calls).toEqual([`/api/research-dated/v1/dates/${EARLY}/funds/X05?bundle=${bundleIdFor(EARLY)}`]);
    }
    routes(() => new Response('<html>404</html>', {status: 404}));
    expect(datedErrorKind(await failure(loadDatedDetail(index(), EARLY, 'X05')))).toBe('bundle-error');
    routes(() => new Response(JSON.stringify({error: {code: 'fund not found <b>', message_tr: 'x'}}), {status: 404}));
    expect(await failure(loadDatedDetail(index(), EARLY, 'X05'))).toMatchObject({apiCode: null});
  });
  it('treats a malformed code as a client-side FUND_NOT_FOUND and local date errors as their own states', async () => {
    routes(() => undefined);
    expect(datedErrorKind(await failure(loadDatedDetail(index(), EARLY, '../x')))).toBe('not-found');
    expect(datedErrorKind(await failure(loadDatedList(index(), '2026-02-30')))).toBe('invalid-date');
    expect(datedErrorKind(await failure(loadDatedList(index(), '2026-09-15')))).toBe('unregistered-date');
    expect(datedErrorKind(await failure(loadDatedList(index(), EARLY, undefined, bundleIdFor(LATE))))).toBe('mismatch');
    expect(datedErrorKind(new Error('x'))).toBe('bundle-error');
  });
});
