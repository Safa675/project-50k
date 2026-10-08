// Narrow JSON transport/error pattern adapted from Bilun cafa27bc.
// Copyright (c) 2026 Safa Öksüz. All rights reserved.
import type {z} from 'zod';
import {ListResponseSchema, DetailResponseSchema, SummaryResponseSchema} from './research-contract';

export class ResearchApiError extends Error {
  constructor(message: string, public readonly code: 'NETWORK' | 'HTTP' | 'INVALID_DATA' | 'BUNDLE_CHANGED', public readonly status?: number) {
    super(message);
    this.name = 'ResearchApiError';
  }
}
export async function fetchValidated<T>(path: string, schema: z.ZodType<T>, signal?: AbortSignal): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {cache: 'no-store', credentials: 'omit', signal, headers: {Accept: 'application/json'}});
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
    throw new ResearchApiError('Yerel araştırma API’sine ulaşılamıyor.', 'NETWORK');
  }
  if (!response.ok) {
    let message = 'Araştırma verisi şu anda alınamıyor.';
    try {
      const payload: unknown = await response.json();
      if (payload && typeof payload === 'object' && 'error' in payload) {
        const value = payload.error;
        if (value && typeof value === 'object' && 'message_tr' in value && typeof value.message_tr === 'string') message = value.message_tr;
      }
    } catch { /* Keep a Turkish error instead of raw HTML or paths. */ }
    throw new ResearchApiError(message, 'HTTP', response.status);
  }
  let payload: unknown;
  try { payload = await response.json(); } catch {
    throw new ResearchApiError('API yanıtı geçerli araştırma verisi içermiyor.', 'INVALID_DATA');
  }
  const result = schema.safeParse(payload);
  if (!result.success) throw new ResearchApiError('Araştırma yanıtı beklenen veri sözleşmesine uymuyor.', 'INVALID_DATA');
  return result.data;
}
function validateExpectedBundle(expected?: string) {
  if (expected && !/^[a-f0-9]{64}$/.test(expected)) throw new ResearchApiError('Araştırma paketi bağlantısı geçersiz.', 'INVALID_DATA');
}
function requireBundle(actual: string, expected?: string) {
  if (expected && actual !== expected) throw new ResearchApiError('Bu bağlantının araştırma paketi ile API’deki paket farklı. Sonuçlar birleştirilemez.', 'BUNDLE_CHANGED');
}
export async function loadList(signal?: AbortSignal, expectedBundle?: string) {
  validateExpectedBundle(expectedBundle);
  const [list, summary] = await Promise.all([
    fetchValidated('/api/research/v1/funds', ListResponseSchema, signal),
    fetchValidated('/api/research/v1/summary', SummaryResponseSchema, signal),
  ]);
  if (list.immutable_bundle_id !== summary.immutable_bundle_id || list.cutoff_at !== summary.cutoff_at) {
    throw new ResearchApiError('Araştırma paketi yükleme sırasında değişti. Yeniden deneyin.', 'BUNDLE_CHANGED');
  }
  requireBundle(list.immutable_bundle_id, expectedBundle);
  const counts = {fully_assessable: 0, partially_assessable: 0, unavailable: 0, two_findings: 0, one_finding: 0, no_findings: 0, unassessable_no_findings: 0, d1_assessable: 0, flow_assessable: 0, d1_stale: 0};
  for (const fund of list.funds) {
    counts[fund.assessment === 'FULL' ? 'fully_assessable' : fund.assessment === 'PARTIAL' ? 'partially_assessable' : 'unavailable']++;
    counts[fund.eligible_crossings === 2 ? 'two_findings' : fund.eligible_crossings === 1 ? 'one_finding' : fund.assessment === 'FULL' ? 'no_findings' : 'unassessable_no_findings']++;
    if (fund.d1.arithmetic_status === 'AVAILABLE' && fund.d1.freshness === 'FRESH') counts.d1_assessable++;
    if (fund.flow.arithmetic_status === 'AVAILABLE' && fund.flow.freshness === 'FRESH') counts.flow_assessable++;
    if (fund.d1.freshness === 'STALE') counts.d1_stale++;
  }
  if (summary.summary.total !== list.funds.length || Object.entries(counts).some(([key, value]) => summary.summary[key as keyof typeof counts] !== value)) {
    throw new ResearchApiError('Özet sayıları fon listesiyle uyuşmuyor.', 'INVALID_DATA');
  }
  return {list, summary};
}
export async function loadDetail(code: string, signal?: AbortSignal, expectedBundle?: string) {
  validateExpectedBundle(expectedBundle);
  if (!/^[A-Z0-9]{3}$/.test(code)) throw new ResearchApiError('Bu fon seçili 100 fon içinde bulunmuyor.', 'HTTP', 404);
  const detail = await fetchValidated(`/api/research/v1/funds/${code}`, DetailResponseSchema, signal);
  if (detail.fund.code !== code) throw new ResearchApiError('API yanıtı seçilen fonla uyuşmuyor.', 'INVALID_DATA');
  requireBundle(detail.immutable_bundle_id, expectedBundle);
  if (detail.sources.some(source => ['KAP_SERIES', 'KAP_PDF'].includes(source.kind) && source.fund_code !== code)) {
    throw new ResearchApiError('Aylık rapor kaynağı seçilen fona ait değil.', 'INVALID_DATA');
  }
  const sourceIds = new Set(detail.sources.map(source => source.source_id));
  const references = new Set([...detail.fund.evidence, ...detail.fund.d1.input_refs, ...detail.fund.flow.input_refs, ...detail.fund.flow.endpoint_refs.map(endpoint => endpoint.source_id)]);
  if (sourceIds.size !== detail.sources.length || sourceIds.size !== references.size || [...references].some(reference => !sourceIds.has(reference))) {
    throw new ResearchApiError('Fonun kaynak kayıtları araştırma paketiyle uyuşmuyor.', 'INVALID_DATA');
  }
  return detail;
}
