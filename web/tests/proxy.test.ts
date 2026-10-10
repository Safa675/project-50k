import {describe, expect, it, vi} from 'vitest';
import {allowedHost, proxyRequest} from '../lib/proxy';

describe('same-origin API proxy', () => {
  it('rejects foreign and malformed hosts before any fetch', async () => {
    const send = vi.fn();
    expect(allowedHost('localhost:3070')).toBe(true);
    expect(allowedHost('127.0.0.1:3071')).toBe(true);
    const response = await proxyRequest(new Request('http://evil.invalid/api/p/health/live', {headers: {host: 'evil.invalid'}}), ['health', 'live'], send);
    expect(response.status).toBe(400);
    expect(send).not.toHaveBeenCalled();
  });

  it('forwards cookie, origin and CSRF for each loopback origin and preserves separate cookies', async () => {
    for (const origin of ['http://127.0.0.1:3070', 'http://localhost:3070']) {
      const send = vi.fn(async () => new Response('accepted', {headers: [
        ['set-cookie', 'probe=synthetic; HttpOnly; Path=/'],
        ['set-cookie', 'marker=synthetic; Path=/'],
      ]}));
      const response = await proxyRequest(new Request(`${origin}/api/p/__test__/csrf`, {method: 'POST', headers: {
        host: new URL(origin).host, cookie: 'probe=synthetic', origin, 'x-csrf-token': 'synthetic',
      }, body: '{}'}), ['__test__', 'csrf'], send);
      const [, options] = send.mock.calls[0] as unknown as [URL, RequestInit];
      const headers = options.headers as Headers;
      expect(headers.get('cookie')).toBe('probe=synthetic');
      expect(headers.get('origin')).toBe(origin);
      expect(headers.get('x-csrf-token')).toBe('synthetic');
      expect(response.headers.getSetCookie()).toHaveLength(2);
      expect(await response.text()).toBe('accepted');
    }
  });

  it('returns the first SSE event before the upstream stream closes', async () => {
    let source: ReadableStreamDefaultController<Uint8Array>;
    const stream = new ReadableStream<Uint8Array>({start(controller) {source = controller; controller.enqueue(new TextEncoder().encode('data: first\n\n'));}});
    const send = vi.fn(async () => new Response(stream, {headers: {'content-type': 'text/event-stream'}}));
    const response = await proxyRequest(new Request('http://localhost:3070/api/p/__test__/sse', {headers: {host: 'localhost:3070'}}), ['__test__', 'sse'], send);
    const reader = response.body!.getReader();
    expect(new TextDecoder().decode((await reader.read()).value)).toBe('data: first\n\n');
    source!.enqueue(new TextEncoder().encode('data: second\n\n'));
    source!.close();
    expect(new TextDecoder().decode((await reader.read()).value)).toBe('data: second\n\n');
    expect(response.headers.get('x-accel-buffering')).toBe('no');
  });

  it('rejects path traversal and oversized bodies', async () => {
    const send = vi.fn();
    const request = () => new Request('http://localhost:3070/api/p/x', {method: 'POST', headers: {host: 'localhost:3070'}, body: 'x'.repeat(65537)});
    expect((await proxyRequest(request(), ['..', 'funds'], send)).status).toBe(400);
    expect((await proxyRequest(request(), ['funds'], send)).status).toBe(413);
    expect(send).not.toHaveBeenCalled();
  });
});
