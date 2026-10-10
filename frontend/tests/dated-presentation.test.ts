import {describe, it, expect} from 'vitest';
import {commentWithNote, d1StateLabel, dateOptionLabel, datedDetailHref, datedListHref, datedReason, DATED_EXACT, formatCutoff,
  formatDay, listHeading, matchesDatedRecord, snapshotSentence} from '../src/lib/dated-presentation';
import {reason} from '../src/lib/presentation';

describe('tr-TR Europe/Istanbul cutoff formatting', () => {
  it('formats the response cutoff without a time-zone shift', () => {
    expect(formatCutoff('2025-10-31T23:59:59+03:00')).toBe('31 Ekim 2025 · 23:59 İstanbul');
    expect(formatCutoff('2026-09-16T23:59:59+03:00')).toBe('16 Eylül 2026 · 23:59 İstanbul');
    expect(formatDay('2026-01-30')).toBe('30 Ocak 2026');
    expect(listHeading('2026-05-29')).toBe('Fonlar · 29 Mayıs 2026');
  });
  it('refuses non-canonical cutoffs instead of guessing', () => {
    for (const value of ['2025-10-31T23:59:59Z', '2025-10-31', '2025-10-31T20:59:59+00:00']) expect(formatCutoff(value)).toBe('Bilinmiyor');
    expect(formatDay('2025-10')).toBe('Bilinmiyor');
  });
  it('labels the window end per protocol and never as a month end', () => {
    expect(dateOptionLabel('2026-09-16', '2026-09-16')).toBe(`16 Eylül 2026 · ${DATED_EXACT.windowEnd}`);
    expect(dateOptionLabel('2026-08-31', '2026-09-16')).toBe('31 Ağustos 2026');
  });
  it('states the snapshot date from the bundle', () => {
    expect(snapshotSentence('2026-10-07T06:30:00+00:00')).toBe('Ad ve kategoriler: 7 Ekim 2026 anlık görüntüsü.');
  });
});

describe('dated reasons', () => {
  it('replaces date-bearing v1 reasons with selected-date wording', () => {
    expect(reason('final_contributing_observation_before_cutoff')).toContain('16 Eylül');
    expect(datedReason('final_contributing_observation_before_cutoff')).toBe('Son geçerli gözlem seçilen tarihe ait değil.');
    expect(datedReason('STALE_D1')).not.toMatch(/Eylül|\d{4}/);
    expect(datedReason('MISSING_MONTHLY_PAIR')).not.toMatch(/Temmuz|ağustos/i);
    expect(datedReason('2026-08_publication_missing_or_invalid')).not.toMatch(/Ağustos/);
  });
  it('keeps date-free v1 reasons unchanged', () => {
    for (const value of ['fewer_than_10_category_peers', 'historical_availability_unknown', 'peer_category_membership_from_current_snapshot']) expect(datedReason(value)).toBe(reason(value));
  });
});

describe('record presentation', () => {
  const base = {d1_state: 'ELIGIBLE_NO_CROSSING' as const, comment_tr: 'Seçilen tarihte eşik aşılmadı.', date_context: {has_positive_price_on_or_before_cutoff: true}};
  it('adds the no-crossing sentence exactly once', () => {
    expect(commentWithNote(base)).toEqual([base.comment_tr, DATED_EXACT.noCrossing]);
    expect(commentWithNote({...base, comment_tr: `${base.comment_tr} ${DATED_EXACT.noCrossing}`})).toHaveLength(1);
    expect(commentWithNote({...base, d1_state: 'ELIGIBLE_CROSSING'})).toHaveLength(1);
  });
  it('distinguishes unpriced from other unavailable records', () => {
    expect(d1StateLabel({...base, d1_state: 'UNAVAILABLE'})).toBe('Veri yetersiz');
    expect(d1StateLabel({d1_state: 'UNAVAILABLE', date_context: {has_positive_price_on_or_before_cutoff: false}})).toBe('Bu tarihte fiyat kaydı yok');
    expect(d1StateLabel({...base, d1_state: 'STALE'})).toBe('Güncel gözlem eksik');
  });
  it('searches codes and Turkish names locally', () => {
    expect(matchesDatedRecord({code: 'X05', name: 'Örnek Çığ Fonu'}, 'çığ')).toBe(true);
    expect(matchesDatedRecord({code: 'X05', name: 'Örnek'}, 'x05')).toBe(true);
    expect(matchesDatedRecord({code: 'X05', name: 'Örnek'}, 'X06')).toBe(false);
  });
  it('keeps date and bundle in every link', () => {
    expect(datedListHref('2025-10-31', 'a'.repeat(64))).toBe(`/dates?date=2025-10-31&bundle=${'a'.repeat(64)}`);
    expect(datedDetailHref('X05', '2025-10-31', 'a'.repeat(64))).toBe(`/dates/funds/X05?date=2025-10-31&bundle=${'a'.repeat(64)}`);
    expect(datedDetailHref('Z05', '2025-10-31', 'x', true)).toBe('/preview/dates?state=detail&date=2025-10-31&detail=Z05');
  });
});
