import {describe, expect, it} from 'vitest';
import {StockPoint, stockSeries} from '../lib/stock-chart';

function point(close: string|null, ambiguous_revision = false): StockPoint {
  return {effective_date: '2000-01-03', close, ambiguous_revision, available_at: '2000-01-03T18:10:00+03:00', source_sha256: 'a'.repeat(64)};
}

describe('daily stock chart evidence', () => {
  it('keeps gaps and conflicting revisions disconnected rather than filling them', () => {
    const segments = stockSeries([point('10'), point('12'), point(null), point('14'), point('15', true), point('16')]);
    expect(segments.map(segment => segment.length)).toEqual([2, 1, 1]);
    expect(segments[1][0].x).toBeGreaterThan(segments[0][1].x);
    expect(segments.flat().every(value => Number.isFinite(value.x) && Number.isFinite(value.y))).toBe(true);
  });
  it('renders a constant single observation without dividing by zero', () => {
    expect(stockSeries([point('8.125')])).toEqual([[{x: 30, y: 115}]]);
    expect(stockSeries([point('8.125'), point('8.125')])[0].map(value => value.y)).toEqual([115, 115]);
  });
  it('does not draw missing, invalid or ambiguous prices as zero values', () => {
    expect(stockSeries([point(null), point('100', true), point('NaN'), point('0'), point('-2')])).toEqual([]);
  });
});
