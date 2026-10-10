const MAX_BODY_BYTES = 64 * 1024;
const REQUEST_HEADERS = ['cookie', 'origin', 'x-csrf-token', 'content-type', 'accept', 'last-event-id'];
const RESPONSE_HEADERS = ['content-type', 'retry-after', 'www-authenticate'];

export function allowedHost(host: string | null): boolean {
  return host !== null && /^(127\.0\.0\.1|localhost):(3070|3071|3000)$/.test(host);
}

export function apiOrigin(): string {
  const value = process.env.P50K_API_ORIGIN ?? 'http://127.0.0.1:8770';
  const parsed = new URL(value);
  if (parsed.protocol !== 'http:' || !['api', 'localhost', '127.0.0.1'].includes(parsed.hostname) ||
      parsed.username || parsed.password || parsed.pathname !== '/' || parsed.search || parsed.hash) {
    throw new Error('The API origin must be a fixed internal HTTP origin');
  }
  return parsed.origin;
}

async function boundedBody(request: Request): Promise<Uint8Array | undefined> {
  if (!request.body) return undefined;
  const reader = request.body.getReader();
  const chunks: Uint8Array[] = [];
  let length = 0;
  try {
    while (true) {
      const {value, done} = await reader.read();
      if (done) break;
      length += value.length;
      if (length > MAX_BODY_BYTES) {
        await reader.cancel();
        throw new RangeError('Request body exceeds the permitted size');
      }
      chunks.push(value);
    }
  } finally {
    reader.releaseLock();
  }
  const result = new Uint8Array(length);
  let offset = 0;
  for (const chunk of chunks) {result.set(chunk, offset); offset += chunk.length;}
  return result;
}

export async function proxyRequest(request: Request, path: string[], send: typeof fetch = fetch): Promise<Response> {
  if (!allowedHost(request.headers.get('host'))) return Response.json({error: 'HOST_REJECTED'}, {status: 400});
  if (path.some(part => !/^[A-Za-z0-9_.-]+$/.test(part) || part === '.' || part === '..')) {
    return Response.json({error: 'PATH_REJECTED'}, {status: 400});
  }
  const target = new URL(`/${path.map(encodeURIComponent).join('/')}`, apiOrigin());
  target.search = new URL(request.url).search;
  const headers = new Headers();
  for (const name of REQUEST_HEADERS) {
    const value = request.headers.get(name);
    if (value !== null) headers.set(name, value);
  }
  // This loopback-only installation has one verified local browser source.
  // Overwrite the value rather than trusting a caller's forwarded header.
  headers.set('x-p50k-client-ip', '127.0.0.1');
  let body: Uint8Array | undefined;
  try {
    body = ['GET', 'HEAD'].includes(request.method) ? undefined : await boundedBody(request);
  } catch {
    return Response.json({error: 'BODY_TOO_LARGE'}, {status: 413});
  }
  try {
    const upstream = await send(target, {
      method: request.method, headers, body: body as BodyInit | undefined,
      cache: 'no-store', redirect: 'manual', signal: request.signal,
    });
    const responseHeaders = new Headers({'Cache-Control': 'no-store', 'X-Accel-Buffering': 'no'});
    for (const name of RESPONSE_HEADERS) {
      const value = upstream.headers.get(name);
      if (value !== null) responseHeaders.set(name, value);
    }
    for (const cookie of upstream.headers.getSetCookie()) responseHeaders.append('set-cookie', cookie);
    return new Response(upstream.body, {status: upstream.status, headers: responseHeaders});
  } catch {
    return Response.json({error: 'API_UNAVAILABLE'}, {status: 502, headers: {'Cache-Control': 'no-store'}});
  }
}
