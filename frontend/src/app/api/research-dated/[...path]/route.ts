// GET-only same-origin proxy to the separate loopback dated API. Only four route
// shapes and a well-formed ?bundle= pass; no cookie, header or other query is forwarded.
// An invalid origin disables only these dated routes; next.config.ts is untouched.
export const dynamic = 'force-dynamic';

const DEFAULT_ORIGIN = 'http://127.0.0.1:8768';
const LOOPBACK = new Set(['127.0.0.1', 'localhost', '[::1]']);
const DATE = /^\d{4}-\d{2}-\d{2}$/;
const CODE = /^[A-Z0-9]{3}$/;
const BUNDLE = /^[a-f0-9]{64}$/;
const PASSED_STATUSES = new Set([200, 400, 404, 409, 503]);
const TIMEOUT_MS = 20_000;

function respond(status: number, body: string): Response {
  return new Response(body, {status, headers: {
    'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store',
    'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer',
  }});
}
function failure(status: number, code: string, message_tr: string): Response {
  return respond(status, JSON.stringify({error: {code, message_tr}}));
}
function datedOrigin(): string | null {
  let url: URL;
  try { url = new URL(process.env.P50K_DATED_API_ORIGIN || DEFAULT_ORIGIN); } catch { return null; }
  if (url.protocol !== 'http:' || !LOOPBACK.has(url.hostname) || url.username || url.password || url.pathname !== '/' || url.search || url.hash) return null;
  return url.origin;
}
/** Maps the allowlisted segments to the upstream path, or null. */
function upstreamPath(segments: string[]): {path: string; perDate: boolean} | null {
  if (segments.length < 2 || segments[0] !== 'v1' || segments[1] !== 'dates') return null;
  if (segments.length === 2) return {path: '/research-dated/v1/dates', perDate: false};
  const date = segments[2];
  if (!DATE.test(date)) return null;
  if (segments.length === 4 && (segments[3] === 'summary' || segments[3] === 'funds')) return {path: `/research-dated/v1/dates/${date}/${segments[3]}`, perDate: true};
  if (segments.length === 5 && segments[3] === 'funds' && CODE.test(segments[4])) return {path: `/research-dated/v1/dates/${date}/funds/${segments[4]}`, perDate: true};
  return null;
}

export async function GET(request: Request, {params}: {params: Promise<{path: string[]}>}): Promise<Response> {
  const {path: segments} = await params;
  const origin = datedOrigin();
  if (!origin) return failure(503, 'DATED_API_ORIGIN_INVALID', 'Tarih görünümü için yerel API adresi geçersiz.');
  const target = upstreamPath(Array.isArray(segments) ? segments : []);
  if (!target) return failure(404, 'NOT_FOUND', 'Bu tarih görünümü adresi bulunmuyor.');
  const bundles = new URL(request.url).searchParams.getAll('bundle');
  if (bundles.length > 1 || (bundles.length === 1 && !BUNDLE.test(bundles[0]))) return failure(400, 'BUNDLE_INVALID', 'Araştırma paketi bağlantısı geçersiz.');
  const url = new URL(target.path, origin);
  if (target.perDate && bundles.length === 1) url.searchParams.set('bundle', bundles[0]);
  let upstream: Response;
  try {
    upstream = await fetch(url, {method: 'GET', redirect: 'error', cache: 'no-store', credentials: 'omit',
      headers: {Accept: 'application/json'}, signal: AbortSignal.timeout(TIMEOUT_MS)});
  } catch {
    return failure(502, 'DATED_API_UNREACHABLE', 'Tarih görünümü API’sine ulaşılamıyor.');
  }
  const type = upstream.headers.get('content-type') ?? '';
  if (!PASSED_STATUSES.has(upstream.status) || !/^application\/json(?:;|$)/i.test(type)) {
    return failure(502, 'DATED_API_INVALID_RESPONSE', 'Tarih görünümü API’sinden geçerli bir yanıt alınamadı.');
  }
  let body: string;
  try {
    body = await upstream.text();
    JSON.parse(body);
  } catch {
    return failure(502, 'DATED_API_INVALID_RESPONSE', 'Tarih görünümü API’sinden geçerli bir yanıt alınamadı.');
  }
  return respond(upstream.status, body);
}
