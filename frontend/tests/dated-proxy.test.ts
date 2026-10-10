import {afterEach, beforeEach, describe, it, expect, vi} from 'vitest';
import * as route from '../src/app/api/research-dated/[...path]/route';

const BUNDLE = 'a'.repeat(64);
const call = (url: string, init?: RequestInit) => {
  const path = new URL(url, 'http://127.0.0.1:3060').pathname.replace(/^\/api\/research-dated\//, '').split('/').map(decodeURIComponent);
  return route.GET(new Request(new URL(url, 'http://127.0.0.1:3060'), init), {params: Promise.resolve({path})});
};
let upstream: ReturnType<typeof vi.fn>;
beforeEach(() => {
  delete process.env.P50K_DATED_API_ORIGIN;
  upstream = vi.fn(async () => new Response('{"ok":true}', {status: 200, headers: {'content-type': 'application/json'}}));
  vi.stubGlobal('fetch', upstream);
});
afterEach(() => { vi.unstubAllGlobals(); delete process.env.P50K_DATED_API_ORIGIN; });

describe('dated proxy route', () => {
  it('exports GET only', () => {
    expect(Object.keys(route).filter(key => /^[A-Z]+$/.test(key))).toEqual(['GET']);
  });
  it('forwards the four allowlisted shapes to the default loopback origin', async () => {
    const cases: [string, string][] = [
      ['/api/research-dated/v1/dates', 'http://127.0.0.1:8768/research-dated/v1/dates'],
      [`/api/research-dated/v1/dates/2025-10-31/summary?bundle=${BUNDLE}`, `http://127.0.0.1:8768/research-dated/v1/dates/2025-10-31/summary?bundle=${BUNDLE}`],
      [`/api/research-dated/v1/dates/2025-10-31/funds?bundle=${BUNDLE}`, `http://127.0.0.1:8768/research-dated/v1/dates/2025-10-31/funds?bundle=${BUNDLE}`],
      ['/api/research-dated/v1/dates/2025-10-31/funds/X05', 'http://127.0.0.1:8768/research-dated/v1/dates/2025-10-31/funds/X05'],
    ];
    for (const [input, expected] of cases) {
      const response = await call(input);
      expect(response.status).toBe(200);
      expect(String(upstream.mock.lastCall![0])).toBe(expected);
    }
  });
  it('rejects every other path without contacting the API', async () => {
    for (const input of ['/api/research-dated/v1', '/api/research-dated/v2/dates', '/api/research-dated/v1/dates/2025-10-31',
      '/api/research-dated/v1/dates/2025-10-31/sources/abc', '/api/research-dated/v1/dates/latest/funds', '/api/research-dated/v1/dates/2025-10-31/funds/x05',
      '/api/research-dated/v1/dates/2025-10-31/funds/X05/pdf', '/api/research-dated/v1/dates/%2E%2E%2F%2E%2E/funds', '/api/research-dated/v1/dates/2025-10-31/funds/..%2FX05',
      '/api/research-dated/v1/funds', '/api/research-dated/research/v1/funds']) {
      expect((await call(input)).status).toBe(404);
    }
    expect(upstream).not.toHaveBeenCalled();
  });
  it('forwards only a single well-formed bundle on per-date routes and nothing else', async () => {
    await call(`/api/research-dated/v1/dates/2025-10-31/funds?bundle=${BUNDLE}&q=x&cutoff=2026-09-16`);
    expect(String(upstream.mock.lastCall![0])).toBe(`http://127.0.0.1:8768/research-dated/v1/dates/2025-10-31/funds?bundle=${BUNDLE}`);
    await call(`/api/research-dated/v1/dates?bundle=${BUNDLE}`);
    expect(String(upstream.mock.lastCall![0])).toBe('http://127.0.0.1:8768/research-dated/v1/dates');
    upstream.mockClear();
    for (const query of ['bundle=ABC', `bundle=${BUNDLE}&bundle=${BUNDLE}`, `bundle=${BUNDLE.toUpperCase()}`, 'bundle=']) {
      expect((await call(`/api/research-dated/v1/dates/2025-10-31/funds?${query}`)).status).toBe(400);
    }
    expect(upstream).not.toHaveBeenCalled();
  });
  it('sends no cookie or client header and refuses redirects', async () => {
    await call('/api/research-dated/v1/dates', {headers: {cookie: 'session=secret', authorization: 'Bearer secret', 'x-forwarded-for': '10.0.0.1'}});
    const init = upstream.mock.lastCall![1] as RequestInit;
    expect(init).toMatchObject({method: 'GET', redirect: 'error', cache: 'no-store', credentials: 'omit'});
    expect(new Headers(init.headers).get('cookie')).toBeNull();
    expect([...new Headers(init.headers).keys()]).toEqual(['accept']);
  });
  it('returns no-store, nosniff JSON and passes known statuses', async () => {
    upstream.mockResolvedValueOnce(new Response('{"error":{"code":"CONTEXT_MISMATCH","message_tr":"x"}}', {status: 409, headers: {'content-type': 'application/json', 'set-cookie': 'a=b'}}));
    const response = await call(`/api/research-dated/v1/dates/2025-10-31/funds?bundle=${BUNDLE}`);
    expect(response.status).toBe(409);
    expect(response.headers.get('cache-control')).toBe('no-store');
    expect(response.headers.get('x-content-type-options')).toBe('nosniff');
    expect(response.headers.get('content-type')).toMatch(/^application\/json/);
    expect(response.headers.get('set-cookie')).toBeNull();
  });
  it('maps unreachable, redirected, non-JSON and unexpected upstream replies to bounded errors', async () => {
    const replies = [() => Promise.reject(new TypeError('fetch failed')), () => Promise.resolve(new Response('<html/>', {status: 200, headers: {'content-type': 'text/html'}})),
      () => Promise.resolve(new Response('{"x":', {status: 200, headers: {'content-type': 'application/json'}})),
      () => Promise.resolve(new Response('{}', {status: 302, headers: {'content-type': 'application/json'}})),
      () => Promise.resolve(new Response('{}', {status: 500, headers: {'content-type': 'application/json'}}))];
    for (const reply of replies) {
      upstream.mockImplementationOnce(reply);
      const response = await call('/api/research-dated/v1/dates');
      expect(response.status).toBe(502);
      expect((await response.json()).error.message_tr).toMatch(/Tarih görünümü API/);
    }
  });
  it('uses P50K_DATED_API_ORIGIN when it is loopback http', async () => {
    for (const [origin, expected] of [['http://localhost:9001', 'http://localhost:9001'], ['http://[::1]:8768/', 'http://[::1]:8768']]) {
      process.env.P50K_DATED_API_ORIGIN = origin;
      await call('/api/research-dated/v1/dates');
      expect(String(upstream.mock.lastCall![0])).toBe(`${expected}/research-dated/v1/dates`);
    }
  });
  it('disables only the dated routes for a non-loopback, https or non-root origin', async () => {
    for (const origin of ['https://127.0.0.1:8768', 'http://10.0.0.5:8768', 'http://example.com', 'http://user:pw@127.0.0.1:8768', 'http://127.0.0.1:8768/x', 'not a url', 'http://127.0.0.1.example.com:8768']) {
      process.env.P50K_DATED_API_ORIGIN = origin;
      const response = await call('/api/research-dated/v1/dates');
      expect(response.status).toBe(503);
      expect((await response.json()).error.code).toBe('DATED_API_ORIGIN_INVALID');
    }
    expect(upstream).not.toHaveBeenCalled();
  });
});
