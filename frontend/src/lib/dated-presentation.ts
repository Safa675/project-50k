// Copy and formatting for the dated D1 view (fund_review_dated/PROTOCOL.md).
// Only `import type` from dated-contract: the contract imports this module's denylist.
import type {DatedRecord} from './dated-contract';
import {reason} from './presentation';

/** Exact sentences fixed by the protocol. Only these are exempt from the denylist. */
export const DATED_EXACT = {
  guard: 'Her tarih ayrı bir arşiv kesitidir. Bu görünüm, o tarihte bir uyarı verildiğini ya da sonucun önceden bilinebileceğini göstermez.',
  noCrossing: 'Eşiğin aşılmaması bir güvenlik değerlendirmesi değildir.',
  survivorship: 'Fon listesi Ekim 2026 yatırımcı sayılarına göre seçildi. Daha önceki tarihlerde henüz fiyatı olmayan ya da sonradan kapanan fonlar bu görünümde doğru temsil edilmeyebilir.',
  whyDatesTitle: 'Neden yalnızca bu tarihler?',
  whyDates: 'Tarihler önceden belirlenmiş bir kurala göre seçildi: Ekim 2025–Ağustos 2026 arasında her ayın son TEFAS fiyat tarihi ve ön kayıtlı inceleme penceresinin son günü. Eşikler 6 Ekim 2025 öncesi verilerle hesaplandığı için daha önceki tarihler gösterilmez.',
  windowEnd: 'Ön kayıtlı inceleme penceresinin son günü; sabit görünümle aynı tarih.',
  notComputed: 'Bu tarih görünümünde hesaplanmadı.',
  fixedViewLink: 'Sabit 16 Eylül 2026 görünümüne geç (farklı tarih)',
} as const;
export const EXACT_SENTENCES: readonly string[] = Object.values(DATED_EXACT);
const SNAPSHOT_PREFIX = 'Ad ve kategoriler: ';
const SNAPSHOT_SUFFIX = ' anlık görüntüsü.';

export const DATED_DENYLIST = ['erken uyarı', 'ilk eşik aşımı', 'gün önce', 'ay önce', 'önceden', 'tahmin', 'öngör',
  'risk yok', 'güvenli', 'tasfiye', 'SPK', 'dolandırıcılık', 'son kesit'] as const;
export const MONTH_NAMES_TR = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık'] as const;

/** Static Turkish UI strings for the dated view. No fixed date, month name or denylisted wording. */
export const DATED_COPY = {
  brand: 'Fon araştırması', brandSmall: 'Project 50K',
  archiveLabel: 'Tarihsel arşiv araştırması · Tarih görünümü',
  syntheticLabel: 'Örnek verilerle tasarım önizlemesi · Tarih görünümü',
  footerSources: 'Kaynak sürümlerinin geçmişte erişilebilir olduğu doğrulanmadı.',
  footerUniverse: 'Fon evreni ve kategoriler, incelenen tarihlerden sonraki bir anlık görüntüden alındı.',
  footerRights: 'Veri hakları incelenmedi · Üretim kararları değerlendirme dışı',
  eyebrow: 'Tarih görünümü · Yalnızca D1 hesabı', syntheticEyebrow: 'Tarih görünümü · Tasarım önizlemesi',
  headingPrefix: 'Fonlar · ',
  cutoffCaption: 'İnceleme zamanı', cutoffSuffix: ' · 23:59 İstanbul',
  intro: 'Benzer fonlara göre getiri farkı (D1), seçilen tarihe kadar kayıtlı fiyatlarla gösterilir. Her fonun hesap kapsamı ve kaynakları fon detayında.',
  syntheticNotice: 'Bu ekrandaki tarih dizini, fonlar ve sayılar tamamen örnektir.',
  syntheticNoticeDetail: 'Gerçek fon bulgusu veya ölçülmüş başarı göstermez.',
  archiveNotice: 'Bu ekran geçmiş arşiv verilerini seçilen tarihe göre süzer.',
  archiveNoticeDetail: 'Kayıtlı kaynak tarihlerine göre yeniden oluşturulmuştur; o tarihte gerçekten erişilebilir olduğu doğrulanmadı.',
  selectorForm: 'Tarih seçimi', selectorLabel: 'İnceleme tarihi', selectorSubmit: 'Tarihi göster',
  selectorHint: 'Seçim, “Tarihi göster” düğmesine basıldığında uygulanır.',
  statCrossing: 'Eşik aşımı', statNoCrossing: 'Eşik aşımı yok', statStale: 'Güncel gözlem eksik', statUnavailable: 'Veri yetersiz',
  stateNoPrice: 'Bu tarihte fiyat kaydı yok',
  ofFunds: ' fon',
  noPricePrefix: 'Seçilen tarihte veya öncesinde fiyat kaydı olmayan fon: ',
  noPriceSuffix: ' · veri yetersiz sayısına dahildir.',
  searchLabel: 'Fon ara', searchPlaceholder: 'Kod veya fon adı ara', clearSearch: 'Aramayı temizle',
  shownSuffix: ' fon gösteriliyor',
  order: 'Sıra: eşik aşımı → değerlendirilemeyen (eski gözlem veya veri yetersiz) → eşik aşımı yok',
  noMatchTitle: 'Aramanızla eşleşen fon yok', noMatchDescription: 'Fon kodunu veya adını değiştirin.',
  columnFund: 'Fon', columnD1: 'Getiri farkı · D1', columnThreshold: 'Kategori eşiği', columnState: 'D1 durumu', columnComment: 'Veriye dayalı yorum',
  unknownCategory: 'Kategori bilinmiyor',
  notComputedHeading: 'Aylık rapora dayalı para hareketi ve portföy yoğunlaşması',
  thresholdHeading: 'Eşiklerin kapsamı',
  thresholdText: 'Kategori eşikleri, inceleme penceresinin başından önceki verilerin 99. yüzdeliğidir. Yalnızca eşiğin kesin olarak üzerindeki değerler aşım sayılır.',
  thresholdUniverse: 'Eşikler, değerlendirilen fonları da içeren sonraki bir fon evreni ve kategori kaydı üzerinden hesaplandı.',
  bundleVersion: 'Araştırma paketinin sürümü', indexVersion: 'Tarih dizininin sürümü', sampleVersion: 'Örnek veri',
  indexLoading: 'Tarih dizini yükleniyor…', indexLoadingDescription: 'Kayıtlı tarihler doğrulandıktan sonra gösterilecek.',
  indexError: 'Tarih dizini alınamadı',
  invalidDate: 'Tarih geçersiz',
  invalidDateDescription: 'Bağlantıdaki tarih YYYY-AA-GG biçiminde ve kayıtlı aralıkta olmalı. Kayıtlı bir tarih seçin.',
  unregisteredDate: 'Bu tarih kayıtlı değil',
  unregisteredDateDescription: 'Yalnızca kayıtlı tarihler gösterilir; yerine yakın bir tarih seçilmez. Kayıtlı bir tarih seçin.',
  bundleLoading: 'Araştırma paketi yükleniyor…', bundleLoadingDescription: 'Sonuçlar doğrulandıktan sonra gösterilecek.',
  bundleError: 'Araştırma verisi alınamadı',
  noResults: 'Bu durumda fon sonucu gösterilmiyor.',
  mismatch: 'Bağlantı kayıtlı paketle uyuşmuyor',
  mismatchDescription: 'Bu bağlantıdaki araştırma paketi, seçilen tarih için kayıtlı paketle aynı değil. Sonuçlar birleştirilmez.',
  openRegistered: 'Kayıtlı paketle aç',
  retry: 'Tekrar dene', fundNotFound: 'Fon bulunamadı', backToList: '← Fon listesine dön', backToDates: '← Tarih görünümüne dön',
  chartHeading: 'Fon ve benzerlerinin getirisi', chartNote: 'Fon kendi benzerler grubuna katılmaz.',
  d1Heading: 'Benzer fonlara göre getiri farkı · D1',
  d1Description: 'Seçilen tarihe kadarki son 60 ortak fiyat tarihindeki günlük getiri farklarının medyanı. Geçerli gözlem ve uygun benzer fon sayısı yeterli olmalıdır.',
  labelThreshold: 'Sabit kategori eşiği', labelPeriod: 'Gözlem dönemi', labelUsable: 'Geçerli gözlem', labelPeers: 'Uygun benzer fon',
  labelLatest: 'Son katkı veren gözlem', labelExact: 'Tam hesap değerleri', labelStatistic: 'Günlük log getiri farkı', labelExactThreshold: 'Sabit eşik',
  unknown: 'Bilinmiyor', peersPrefix: 'En az ', qualificationsPrefix: 'Varsayımlar ve hesap sınırları ',
  noPriceDetail: 'Seçilen tarihte veya öncesinde bu fonun pozitif fiyat kaydı yok.',
  sourcesHeading: 'Hesabın kaynakları',
  sourcesNote: 'Bu görünüm yalnızca fiyat, fon listesi, kategori kaydı, eşik ve kod sürümlerini kullanır. Aylık rapor ve PDF bu görünümde yer almaz.',
  sourceVersion: 'Kaynak sürümü', sourceDigest: 'Kaynak dosyasının özeti:',
  peerSources: 'Benzer fonların fiyat kaynakları', otherSources: 'Hesap sürümleri ve diğer kaynaklar',
  noSources: 'Fona ait kaynak bilgisi bulunamadı', noSourcesDescription: 'Eksik kaynak yerine bir değer üretilmedi.',
  limitHeading: 'Yorumun sınırı', limitText: 'Eşik aşımı bir hüküm değildir; yalnızca kayıtlı eşikle bir karşılaştırmadır. Tarihsel sürüm ve erişim zamanı doğrulanmadı.',
  production: 'Üretim kararı: değerlendirme dışı',
  dateReadOnly: 'Bu sayfada tarih değiştirilemez; tarih seçimi fon listesindedir.',
  previewStates: 'Önizleme durumları',
  liveSuffix: ' tarihli görünüm yüklendi.', titleSuffix: ' · Tarih görünümü · Fon araştırması',
} as const;

/** Labels for the synthetic preview state links. */
export const PREVIEW_STATES = [
  ['ready', 'Hazır'], ['early-date', 'İlk tarih'], ['detail', 'Fon detayı'], ['index-loading', 'Dizin yükleniyor'],
  ['index-error', 'Dizin hatası'], ['invalid-date', 'Geçersiz tarih'], ['unregistered-date', 'Kayıtsız tarih'],
  ['bundle-loading', 'Paket yükleniyor'], ['bundle-error', 'Paket hatası'], ['mismatch', 'Paket uyuşmazlığı'],
] as const;
export type PreviewState = typeof PREVIEW_STATES[number][0];

/**
 * The only text exempt from the no-later-date rule (docs/notes/fund-review-dated-design.md,
 * "Protocol clarification 1"): the survivorship sentence, the snapshot label, the
 * "Neden yalnızca bu tarihler?" text, and the fixed-view link sentence. The selector's
 * options are exempt too and are removed by the browser check itself. Every other exact
 * sentence (guard, no-crossing, window end, ...) is still checked for dates.
 */
export const LATER_DATE_EXEMPT: readonly string[] = [DATED_EXACT.survivorship, DATED_EXACT.whyDates, DATED_EXACT.fixedViewLink];
/** The snapshot label with exactly one formatted day ("7 Ekim 2026"), nothing else. */
const SNAPSHOT_LABEL_PATTERN = new RegExp(`${SNAPSHOT_PREFIX}\\d{1,2} (?:${MONTH_NAMES_TR.join('|')}) \\d{4}${SNAPSHOT_SUFFIX.replace('.', '\\.')}`, 'g');

function strip(text: string, sentences: readonly string[]): string {
  let remaining = text.replace(/\s+/g, ' ');
  for (const sentence of sentences) remaining = remaining.split(sentence).join(' ');
  return remaining.replace(SNAPSHOT_LABEL_PATTERN, ' ');
}
/** Text left after removing the later-date exemptions only; dates in it are checked. */
export const stripLaterDateExempt = (text: string) => strip(text, LATER_DATE_EXEMPT);
/** Denylisted terms remaining after the exempt exact sentences are removed. */
export function deniedTerms(text: string): string[] {
  const folded = strip(text, EXACT_SENTENCES).toLocaleLowerCase('tr-TR');
  return DATED_DENYLIST.filter(term => folded.includes(term.toLocaleLowerCase('tr-TR')));
}
/** Fixed ISO dates, four-digit years or Turkish month names outside the later-date exemptions. */
export function dateMentions(text: string): string[] {
  const remaining = stripLaterDateExempt(text);
  const found = remaining.match(/\b\d{4}(?:-\d{2}(?:-\d{2})?)?\b/g) ?? [];
  return [...found, ...MONTH_NAMES_TR.filter(name => new RegExp(`(?<![\\p{L}\\p{N}_])${name}`, 'u').test(remaining))];
}

const DAY_FORMAT = new Intl.DateTimeFormat('tr-TR', {timeZone: 'Europe/Istanbul', day: 'numeric', month: 'long', year: 'numeric'});
/** "31 Ekim 2025" for a canonical YYYY-MM-DD calendar date. */
export function formatDay(date: string): string {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return DATED_COPY.unknown;
  const value = new Date(`${date}T12:00:00+03:00`);
  return Number.isNaN(value.getTime()) ? DATED_COPY.unknown : DAY_FORMAT.format(value);
}
/** "31 Ekim 2025 · 23:59 İstanbul" from the response's own cutoff_at. */
export function formatCutoff(cutoffAt: string): string {
  const match = /^(\d{4}-\d{2}-\d{2})T23:59:59\+03:00$/.exec(cutoffAt);
  return match ? formatDay(match[1]) + DATED_COPY.cutoffSuffix : DATED_COPY.unknown;
}
/** Date part of an offset-aware instant, in Europe/Istanbul. */
export function formatInstantDay(instant: string): string {
  const value = new Date(instant);
  return Number.isNaN(value.getTime()) ? DATED_COPY.unknown : DAY_FORMAT.format(value);
}
export function snapshotSentence(latestRetrievedAt: string): string {
  return `${SNAPSHOT_PREFIX}${formatInstantDay(latestRetrievedAt)}${SNAPSHOT_SUFFIX}`;
}
export function dateOptionLabel(date: string, windowEnd: string): string {
  return date === windowEnd ? `${formatDay(date)} · ${DATED_EXACT.windowEnd}` : formatDay(date);
}
export const listHeading = (date: string) => DATED_COPY.headingPrefix + formatDay(date);
export const liveAnnouncement = (date: string) => formatDay(date) + DATED_COPY.liveSuffix;
export const documentTitle = (date: string, code?: string) => (code ? `${code} · ` : '') + formatDay(date) + DATED_COPY.titleSuffix;
export const ofHundred = (value: number, total = 100) => `${value} / ${total}${DATED_COPY.ofFunds}`;

export function d1StateLabel(record: Pick<DatedRecord, 'd1_state' | 'date_context'>): string {
  if (record.d1_state === 'ELIGIBLE_CROSSING') return DATED_COPY.statCrossing;
  if (record.d1_state === 'ELIGIBLE_NO_CROSSING') return DATED_COPY.statNoCrossing;
  if (record.d1_state === 'STALE') return DATED_COPY.statStale;
  return record.date_context.has_positive_price_on_or_before_cutoff ? DATED_COPY.statUnavailable : DATED_COPY.stateNoPrice;
}
/** The no-crossing sentence accompanies every no-crossing comment exactly once. */
export function commentWithNote(record: Pick<DatedRecord, 'd1_state' | 'comment_tr'>): string[] {
  if (record.d1_state !== 'ELIGIBLE_NO_CROSSING' || record.comment_tr.includes(DATED_EXACT.noCrossing)) return [record.comment_tr];
  return [record.comment_tr, DATED_EXACT.noCrossing];
}
export function matchesDatedRecord(record: Pick<DatedRecord, 'code' | 'name'>, query: string): boolean {
  const needle = query.trim();
  if (!needle) return true;
  return record.code.toUpperCase().includes(needle.toUpperCase()) || record.name.toLocaleLowerCase('tr-TR').includes(needle.toLocaleLowerCase('tr-TR'));
}

const DATED_REASONS: Record<string, string> = {
  STALE_D1: 'Son geçerli gözlem seçilen tarihe ait değil.',
  final_contributing_observation_before_cutoff: 'Son geçerli gözlem seçilen tarihe ait değil.',
  no_positive_price_on_or_before_cutoff: 'Seçilen tarihte veya öncesinde pozitif fiyat kaydı yok.',
};
const GENERIC_REASON = 'Bu verinin uygunluğu doğrulanamadı; hesap sınırlı olabilir.';
/** presentation.reason() with date-bearing labels replaced by "seçilen tarih" wording. */
export function datedReason(value: string): string {
  if (DATED_REASONS[value]) return DATED_REASONS[value];
  const label = reason(value);
  return dateMentions(label).length || deniedTerms(label).length ? GENERIC_REASON : label;
}

function query(values: Record<string, string>): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(values)) if (value) params.set(key, value);
  return params.toString();
}
export function datedListHref(date: string, bundle: string, synthetic = false): string {
  return synthetic ? `/preview/dates?${query({date})}` : `/dates?${query({date, bundle})}`;
}
export function datedDetailHref(code: string, date: string, bundle: string, synthetic = false): string {
  return synthetic ? `/preview/dates?${query({state: 'detail', date, detail: code})}` : `/dates/funds/${code}?${query({date, bundle})}`;
}
export const fixedViewHref = (synthetic = false) => synthetic ? '/preview' : '/';
