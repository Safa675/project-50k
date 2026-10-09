import {createHash} from 'node:crypto';
import {describe, expect, it} from 'vitest';
import {opaquePdfPath, verifyPdfResponse} from '../src/components/SourcePdfDialog';
import type {Source} from '../src/lib/research-contract';

const bytes = new TextEncoder().encode('%PDF-1.4\nSynthetic authored test only\n%%EOF\n');
const bundleId = 'a'.repeat(64);
const cutoffAt = '2026-09-16T23:59:59+03:00';
const source: Source = {source_id: 'b'.repeat(64), kind: 'KAP_PDF', label: 'Synthetic PDF', fund_code: 'AAA',
  sha256: createHash('sha256').update(bytes).digest('hex'), file_name: 'synthetic.pdf', media_type: 'application/pdf',
  pdf_available: true, published_at: '2026-09-02T11:00:00+03:00', retrieved_at: null,
  historical_availability: 'UNKNOWN', rights_status: 'UNKNOWN', origin: 'HISTORICAL_REPLAY',
  disclosure_id: '1', disclosure_url: 'https://www.kap.org.tr/tr/Bildirim/1'};
function response(changes: Record<string, string> = {}, body = bytes): Response {
  return new Response(body, {headers: {'Content-Type': 'application/pdf', 'Cache-Control': 'no-store',
    'X-Research-Bundle-Id': bundleId, 'X-Research-Cutoff-At': cutoffAt,
    'X-Research-Origin': 'HISTORICAL_REPLAY', 'X-Research-Analysis-Mode': 'EXPLORATORY_ARCHIVE',
    'X-Research-Point-In-Time-Verified': 'false', 'X-Research-Rights-Status': 'UNKNOWN', ...changes}});
}
describe('manifest-bound private PDF viewer', () => {
  it('constructs only a local opaque source route', () => {
    expect(opaquePdfPath(source, bundleId)).toBe(`/api/research/v1/sources/${source.source_id}`);
    for (const id of ['../raw/private.pdf', 'https://example.com', 'bad']) {
      expect(() => opaquePdfPath({...source, source_id: id}, bundleId)).toThrow();
    }
    expect(() => opaquePdfPath({...source, pdf_available: false}, bundleId)).toThrow();
    expect(() => opaquePdfPath(source, 'synthetic')).toThrow();
  });
  it('rejects unknown or future publication for the fixed cutoff', () => {
    for (const published_at of [null, '2026-09-17T00:00:00+03:00']) {
      expect(() => opaquePdfPath({...source, published_at}, bundleId)).toThrow();
    }
  });
  it('verifies exact response bytes, bundle, cutoff, provenance and no-store', async () => {
    expect(new Uint8Array(await verifyPdfResponse(response(), source, bundleId))).toEqual(bytes);
    const invalidHeaders: Record<string, string>[] = [
      {'X-Research-Bundle-Id': 'c'.repeat(64)}, {'X-Research-Cutoff-At': 'future'},
      {'X-Research-Point-In-Time-Verified': 'true'}, {'Content-Type': 'text/html'}, {'Cache-Control': 'public'},
    ];
    for (const headers of invalidHeaders) {
      await expect(verifyPdfResponse(response(headers), source, bundleId)).rejects.toThrow();
    }
  });
  it('rejects corrupted PDF content and missing signatures', async () => {
    await expect(verifyPdfResponse(response({}, new TextEncoder().encode('%PDF-1.4\nchanged')), source, bundleId)).rejects.toThrow();
    await expect(verifyPdfResponse(response({}, new TextEncoder().encode('not a PDF')), source, bundleId)).rejects.toThrow();
  });
  it('rejects missing and unavailable sources before rendering', async () => {
    await expect(verifyPdfResponse(new Response(null, {status: 404}), source, bundleId)).rejects.toThrow('bulunamadı');
    await expect(verifyPdfResponse(new Response(null, {status: 503}), source, bundleId)).rejects.toThrow('doğrulanamıyor');
  });
});
