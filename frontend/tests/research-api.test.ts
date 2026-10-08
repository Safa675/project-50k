import {afterEach, describe, it, expect, vi} from 'vitest';
import {z} from 'zod';
import {fetchValidated, loadDetail, loadList, ResearchApiError} from '../src/lib/research-api';
import {BUNDLE_ID, researchFixture} from './fixtures/research';

afterEach(() => vi.unstubAllGlobals());

function respond(value: unknown) {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify(value))));
}

describe('validated JSON transport', () => {
  it('marks runtime requests no-store', async () => {
    const mock = vi.fn().mockResolvedValue(new Response('{"value":"ok"}', {status: 200}));
    vi.stubGlobal('fetch', mock);
    expect(await fetchValidated('/test', z.object({value: z.string()}))).toEqual({value: 'ok'});
    expect(mock.mock.calls[0][1]).toMatchObject({cache: 'no-store', credentials: 'omit'});
  });

  it('rejects malformed runtime payloads', async () => {
    respond({value: 1});
    await expect(fetchValidated('/test', z.object({value: z.string()}))).rejects.toMatchObject({code: 'INVALID_DATA'});
  });

  it('reports API network errors', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')));
    await expect(fetchValidated('/test', z.string())).rejects.toBeInstanceOf(ResearchApiError);
  });

  it('preserves abort semantics', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new DOMException('Cancelled', 'AbortError')));
    await expect(fetchValidated('/test', z.string())).rejects.toMatchObject({name: 'AbortError'});
  });
});

describe('fund detail identity and source isolation', () => {
  it('accepts the selected fund with exactly its referenced sources', async () => {
    const detail = researchFixture().detail('S00');
    respond(detail);
    await expect(loadDetail('S00', undefined, BUNDLE_ID)).resolves.toEqual(detail);
  });

  it('rejects an unreferenced source from another fund', async () => {
    const fixture = researchFixture();
    const detail = fixture.detail('S00');
    detail.sources.push(fixture.detail('S01').sources[0]);
    respond(detail);
    await expect(loadDetail('S00', undefined, BUNDLE_ID)).rejects.toMatchObject({code: 'INVALID_DATA'});
  });

  it('rejects a missing referenced source', async () => {
    const detail = researchFixture().detail('S00');
    detail.sources.pop();
    respond(detail);
    await expect(loadDetail('S00', undefined, BUNDLE_ID)).rejects.toMatchObject({code: 'INVALID_DATA'});
  });

  it('rejects a referenced monthly report attributed to another fund', async () => {
    const detail = researchFixture().detail('S00');
    detail.sources.find(source => source.kind === 'KAP_PDF')!.fund_code = 'S01';
    respond(detail);
    await expect(loadDetail('S00', undefined, BUNDLE_ID)).rejects.toMatchObject({code: 'INVALID_DATA'});
  });

  it('rejects a response for a different selected fund', async () => {
    respond(researchFixture().detail('S01'));
    await expect(loadDetail('S00')).rejects.toMatchObject({code: 'INVALID_DATA'});
  });

  it('rejects a changed bundle even when the fund is valid', async () => {
    respond(researchFixture().detail('S00'));
    await expect(loadDetail('S00', undefined, 'b'.repeat(64))).rejects.toMatchObject({code: 'BUNDLE_CHANGED'});
  });

  it('rejects malformed code and bundle before making a request', async () => {
    const mock = vi.fn();
    vi.stubGlobal('fetch', mock);
    await expect(loadDetail('../S00')).rejects.toMatchObject({status: 404});
    await expect(loadDetail('S00', undefined, 'malformed')).rejects.toMatchObject({code: 'INVALID_DATA'});
    expect(mock).not.toHaveBeenCalled();
  });
});

describe('list and summary agreement', () => {
  it('accepts one coherent synthetic 100-record bundle', async () => {
    const fixture = researchFixture();
    vi.stubGlobal('fetch', vi.fn().mockImplementation((path: string) =>
      Promise.resolve(new Response(JSON.stringify(path.endsWith('/summary') ? fixture.summary : fixture.list)))));
    await expect(loadList(undefined, BUNDLE_ID)).resolves.toEqual({list: fixture.list, summary: fixture.summary});
  });

  it('rejects summary counts that are internally valid but disagree with records', async () => {
    const fixture = researchFixture();
    fixture.summary.summary.d1_assessable = 97;
    vi.stubGlobal('fetch', vi.fn().mockImplementation((path: string) =>
      Promise.resolve(new Response(JSON.stringify(path.endsWith('/summary') ? fixture.summary : fixture.list)))));
    await expect(loadList()).rejects.toMatchObject({code: 'INVALID_DATA'});
  });
});
