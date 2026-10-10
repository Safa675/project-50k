import {describe, it, expect} from 'vitest';
import {DATED_COPY, DATED_DENYLIST, DATED_EXACT, EXACT_SENTENCES, LATER_DATE_EXEMPT, PREVIEW_STATES, dateMentions, deniedTerms, snapshotSentence,
  stripLaterDateExempt} from '../src/lib/dated-presentation';
import {syntheticBundle, SYNTHETIC_DATES} from '../src/lib/dated-synthetic';

function strings(value: unknown): string[] {
  if (typeof value === 'string') return [value];
  if (Array.isArray(value)) return value.flatMap(strings);
  if (value && typeof value === 'object') return Object.values(value).flatMap(strings);
  return [];
}
const PROTOCOL_SENTENCES = [
  'Her tarih ayrı bir arşiv kesitidir. Bu görünüm, o tarihte bir uyarı verildiğini ya da sonucun önceden bilinebileceğini göstermez.',
  'Eşiğin aşılmaması bir güvenlik değerlendirmesi değildir.',
  'Fon listesi Ekim 2026 yatırımcı sayılarına göre seçildi. Daha önceki tarihlerde henüz fiyatı olmayan ya da sonradan kapanan fonlar bu görünümde doğru temsil edilmeyebilir.',
  'Neden yalnızca bu tarihler?',
  'Tarihler önceden belirlenmiş bir kurala göre seçildi: Ekim 2025–Ağustos 2026 arasında her ayın son TEFAS fiyat tarihi ve ön kayıtlı inceleme penceresinin son günü. Eşikler 6 Ekim 2025 öncesi verilerle hesaplandığı için daha önceki tarihler gösterilmez.',
  'Ön kayıtlı inceleme penceresinin son günü; sabit görünümle aynı tarih.',
  'Bu tarih görünümünde hesaplanmadı.',
  'Sabit 16 Eylül 2026 görünümüne geç (farklı tarih)',
];

describe('exact protocol sentences', () => {
  it('match PROTOCOL.md verbatim and are the only exemptions', () => {
    expect([...EXACT_SENTENCES].sort()).toEqual([...PROTOCOL_SENTENCES].sort());
    expect(DATED_DENYLIST).toEqual(expect.arrayContaining(['erken uyarı', 'ilk eşik aşımı', 'gün önce', 'ay önce', 'önceden', 'tahmin', 'öngör', 'risk yok', 'güvenli', 'tasfiye', 'SPK', 'dolandırıcılık']));
  });
  it('are exempt only as whole sentences', () => {
    expect(deniedTerms(DATED_EXACT.guard)).toEqual([]);
    expect(deniedTerms(DATED_EXACT.noCrossing)).toEqual([]);
    expect(deniedTerms('Sonuç önceden bilinebilirdi.')).toEqual(['önceden']);
    expect(deniedTerms(DATED_EXACT.noCrossing.replace('değildir', 'sayılır'))).toEqual(['güvenli']);
    expect(dateMentions(DATED_EXACT.fixedViewLink)).toEqual([]);
    expect(dateMentions('Sabit 16 Eylül 2026 görünümü')).toEqual(expect.arrayContaining(['2026', 'Eylül']));
  });
});

describe('later-date exemptions (fund-review-dated-design.md, protocol clarification 1)', () => {
  it('name exactly the survivorship, why-dates and fixed-view link sentences', () => {
    expect([...LATER_DATE_EXEMPT].sort()).toEqual([DATED_EXACT.survivorship, DATED_EXACT.whyDates, DATED_EXACT.fixedViewLink].sort());
    for (const sentence of LATER_DATE_EXEMPT) expect(dateMentions(sentence)).toEqual([]);
    expect(dateMentions(snapshotSentence('2026-10-07T06:30:00+00:00'))).toEqual([]);
  });
  it('still check the guard, no-crossing and other exact sentences for dates', () => {
    for (const key of ['guard', 'noCrossing', 'whyDatesTitle', 'windowEnd', 'notComputed'] as const) {
      expect(LATER_DATE_EXEMPT).not.toContain(DATED_EXACT[key]);
      expect(stripLaterDateExempt(DATED_EXACT[key]).trim()).toBe(DATED_EXACT[key]);
    }
    expect(dateMentions(`${DATED_EXACT.guard} 16 Eylül 2026`)).toEqual(expect.arrayContaining(['2026', 'Eylül']));
  });
  it('exempt the snapshot label only with a single formatted day', () => {
    expect(dateMentions('Ad ve kategoriler: 16 Eylül 2026 sonucu ve 2026-09-17 anlık görüntüsü.')).toEqual(expect.arrayContaining(['2026-09-17', 'Eylül']));
    expect(dateMentions('Fon listesi Ekim 2026 yatırımcı sayılarına göre seçildi.')).toEqual(expect.arrayContaining(['2026', 'Ekim']));
  });
});

describe('dated copy table', () => {
  const copy = [...strings(DATED_COPY), ...strings(PREVIEW_STATES)];
  it('contains no denylisted wording, including güvenli and dolandırıcılık outside the exact sentences', () => {
    for (const text of copy) expect([text, deniedTerms(text)]).toEqual([text, []]);
  });
  it('contains no fixed date, year or month name', () => {
    for (const text of copy) expect([text, dateMentions(text)]).toEqual([text, []]);
  });
  it('carries no lead-time or cross-date wording', () => {
    for (const text of copy) expect(text).not.toMatch(/son kesit|ilk aşım|kaç gün|zaman çizelgesi|isabet|yanlış alarm|otomatik oynat/i);
  });
  it('snapshot sentence contains only its own date', () => {
    expect(deniedTerms(snapshotSentence('2026-10-07T06:30:00+00:00'))).toEqual([]);
  });
});

describe('synthetic preview strings', () => {
  it('are labelled examples, free of denylisted wording and fixed dates', () => {
    for (const date of SYNTHETIC_DATES) {
      const bundle = syntheticBundle(date);
      for (const fund of bundle.list.funds) {
        expect(fund.name.startsWith('Örnek')).toBe(true);
        expect(fund.category?.startsWith('Örnek')).toBe(true);
        expect(fund.code).toMatch(/^Z\d{2}$/);
        for (const text of [fund.name, fund.category ?? '', fund.comment_tr]) {
          expect([text, deniedTerms(text), dateMentions(text)]).toEqual([text, [], []]);
        }
      }
      for (const source of bundle.detail(bundle.list.funds[0].code)!.sources) expect(deniedTerms(source.label + source.file_name)).toEqual([]);
    }
  });
});
