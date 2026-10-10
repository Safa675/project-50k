// Browser loaders for the dated D1 view. Every per-date request is checked by
// date format and sealed-index membership first, and carries the indexed bundle ID.
import type {z} from 'zod';
import {ResearchApiError} from './research-api';
import {BUNDLE_PATTERN, CODE_PATTERN, DateIndexSchema, datedSchemas, isCalendarDate, isInDatedRange,
  type DateEntry, type DateIndex, type DatedDetailResponse, type DatedListResponse, type DatedSummaryResponse} from './dated-contract';

export const DATED_API_BASE = '/api/research-dated/v1';

export class DatedRequestError extends Error {
  constructor(message: string, public readonly code: 'DATE_INVALID' | 'DATE_NOT_REGISTERED') {
    super(message);
    this.name = 'DatedRequestError';
  }
}

/** Format, calendar and range first, then sealed-index membership. Never a nearest date. */
export function resolveDateEntry(index: DateIndex, date: string): DateEntry {
  if (!isCalendarDate(date) || !isInDatedRange(date)) throw new DatedRequestError('Tarih geçersiz.', 'DATE_INVALID');
  const entry = index.entries.find(item => item.date === date);
  if (!entry) throw new DatedRequestError('Bu tarih kayıtlı değil.', 'DATE_NOT_REGISTERED');
  return entry;
}
/** A link's bundle must be well formed and equal to the indexed bundle for its date. */
export function requireIndexedBundle(entry: DateEntry, expectedBundle?: string) {
  if (expectedBundle === undefined || expectedBundle === '') return;
  if (!BUNDLE_PATTERN.test(expectedBundle)) throw new ResearchApiError('Araştırma paketi bağlantısı geçersiz.', 'BUNDLE_CHANGED');
  if (expectedBundle !== entry.bundle_id) throw new ResearchApiError('Bu bağlantının araştırma paketi, seçilen tarih için kayıtlı paketle aynı değil.', 'BUNDLE_CHANGED');
}
function requireContext(index: DateIndex, entry: DateEntry, payload: {cutoff_date: string; cutoff_at: string; immutable_bundle_id: string; index_id: string}) {
  if (payload.cutoff_date !== entry.date || payload.cutoff_at !== entry.cutoff_at || payload.immutable_bundle_id !== entry.bundle_id || payload.index_id !== index.index_id) {
    throw new ResearchApiError('Tarih, paket ve dizin yanıtları birbiriyle uyuşmuyor. Sonuçlar birleştirilemez.', 'BUNDLE_CHANGED');
  }
}
const datedPath = (entry: DateEntry, suffix: string) => `${DATED_API_BASE}/dates/${entry.date}/${suffix}?bundle=${entry.bundle_id}`;

/** An HTTP error that keeps the dated API's error code; research-api fetchValidated keeps only status and message. */
export class DatedApiError extends ResearchApiError {
  constructor(message: string, status: number, public readonly apiCode: string | null) {
    super(message, 'HTTP', status);
    this.name = 'DatedApiError';
  }
}
const API_CODE = /^[A-Z][A-Z0-9_]{0,63}$/;
/** research-api fetchValidated with the same options and Turkish messages, plus the error body's code. */
async function fetchDated<T>(path: string, schema: z.ZodType<T>, signal?: AbortSignal): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {cache: 'no-store', credentials: 'omit', signal, headers: {Accept: 'application/json'}});
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
    throw new ResearchApiError('Yerel araştırma API’sine ulaşılamıyor.', 'NETWORK');
  }
  if (!response.ok) {
    let message = 'Araştırma verisi şu anda alınamıyor.';
    let apiCode: string | null = null;
    try {
      const payload: unknown = await response.json();
      if (payload && typeof payload === 'object' && 'error' in payload) {
        const value = payload.error;
        if (value && typeof value === 'object' && 'message_tr' in value && typeof value.message_tr === 'string') message = value.message_tr;
        if (value && typeof value === 'object' && 'code' in value && typeof value.code === 'string' && API_CODE.test(value.code)) apiCode = value.code;
      }
    } catch { /* Keep a Turkish error instead of raw HTML or paths. */ }
    throw new DatedApiError(message, response.status, apiCode);
  }
  let payload: unknown;
  try { payload = await response.json(); } catch {
    throw new ResearchApiError('API yanıtı geçerli araştırma verisi içermiyor.', 'INVALID_DATA');
  }
  const result = schema.safeParse(payload);
  if (!result.success) throw new ResearchApiError('Araştırma yanıtı beklenen veri sözleşmesine uymuyor.', 'INVALID_DATA');
  return result.data;
}

export type DatedErrorKind = 'invalid-date' | 'unregistered-date' | 'mismatch' | 'not-found' | 'bundle-error';
/** Screen for a failed dated load. Only a FUND_NOT_FOUND 404 is "not found"; a DATE_NOT_REGISTERED 404 is an unregistered date. */
export function datedErrorKind(error: Error): DatedErrorKind {
  if (error instanceof DatedRequestError) return error.code === 'DATE_INVALID' ? 'invalid-date' : 'unregistered-date';
  if (!(error instanceof ResearchApiError)) return 'bundle-error';
  if (error.code === 'BUNDLE_CHANGED' || error.status === 409) return 'mismatch';
  if (error instanceof DatedApiError) {
    if (error.status === 404 && error.apiCode === 'DATE_NOT_REGISTERED') return 'unregistered-date';
    if (error.status === 404 && error.apiCode === 'FUND_NOT_FOUND') return 'not-found';
    if (error.status === 400 && error.apiCode === 'DATE_INVALID') return 'invalid-date';
  }
  return 'bundle-error';
}

export function loadDateIndex(signal?: AbortSignal): Promise<DateIndex> {
  return fetchDated(`${DATED_API_BASE}/dates`, DateIndexSchema, signal);
}

export type DatedListData = {entry: DateEntry; list: DatedListResponse; summary: DatedSummaryResponse};
export async function loadDatedList(index: DateIndex, date: string, signal?: AbortSignal, expectedBundle?: string): Promise<DatedListData> {
  const entry = resolveDateEntry(index, date);
  requireIndexedBundle(entry, expectedBundle);
  const schemas = datedSchemas(entry.date);
  const [list, summary] = await Promise.all([
    fetchDated(datedPath(entry, 'funds'), schemas.List, signal),
    fetchDated(datedPath(entry, 'summary'), schemas.Summary, signal),
  ]);
  requireContext(index, entry, list);
  requireContext(index, entry, summary);
  const counts = {d1_eligible_crossing: 0, d1_eligible_no_crossing: 0, d1_stale: 0, d1_unavailable: 0, no_price_at_cutoff: 0};
  for (const fund of list.funds) {
    counts[fund.d1_state === 'ELIGIBLE_CROSSING' ? 'd1_eligible_crossing' : fund.d1_state === 'ELIGIBLE_NO_CROSSING' ? 'd1_eligible_no_crossing' : fund.d1_state === 'STALE' ? 'd1_stale' : 'd1_unavailable']++;
    if (!fund.date_context.has_positive_price_on_or_before_cutoff) counts.no_price_at_cutoff++;
  }
  if (summary.summary.record_count !== list.funds.length || Object.entries(counts).some(([key, value]) => summary.summary[key as keyof typeof counts] !== value)) {
    throw new ResearchApiError('Özet sayıları fon listesiyle uyuşmuyor.', 'INVALID_DATA');
  }
  return {entry, list, summary};
}

export type DatedDetailData = {entry: DateEntry; detail: DatedDetailResponse};
export async function loadDatedDetail(index: DateIndex, date: string, code: string, signal?: AbortSignal, expectedBundle?: string): Promise<DatedDetailData> {
  const entry = resolveDateEntry(index, date);
  requireIndexedBundle(entry, expectedBundle);
  if (!CODE_PATTERN.test(code)) throw new DatedApiError('Bu fon seçili 100 fon içinde bulunmuyor.', 404, 'FUND_NOT_FOUND');
  const detail = await fetchDated(datedPath(entry, `funds/${code}`), datedSchemas(entry.date).Detail, signal);
  requireContext(index, entry, detail);
  if (detail.fund.code !== code) throw new ResearchApiError('API yanıtı seçilen fonla uyuşmuyor.', 'INVALID_DATA');
  const sourceIds = new Set(detail.sources.map(source => source.source_id));
  const references = new Set([...detail.fund.evidence, ...detail.fund.d1.input_refs]);
  if (sourceIds.size !== detail.sources.length || sourceIds.size !== references.size || [...references].some(reference => !sourceIds.has(reference))) {
    throw new ResearchApiError('Fonun kaynak kayıtları araştırma paketiyle uyuşmuyor.', 'INVALID_DATA');
  }
  return {entry, detail};
}
