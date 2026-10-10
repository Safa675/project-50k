import {describe, expect, it} from 'vitest';
import {FundPoint, fundSeries, fundWindow,latestKnownNav,sourceName,friendlyEvidenceText} from '../lib/fund-display';

function point(day: number, nav: string | null, ambiguous_revision = false): FundPoint {
  return {effective_date: `2000-01-${String(day).padStart(2, '0')}`, nav, ambiguous_revision};
}

describe('fund chart evidence integrity', () => {
  it('shows the dated last known price without moving it to a missing or conflicting day',()=>{
    const points=[point(1,'10'),point(2,'12'),point(3,null),point(4,'15',true),point(5,'0')];
    expect(latestKnownNav(points)).toBe(points[1]);
    expect(points[2].nav).toBeNull();
    expect(fundSeries(points).coordinates[2].y).toBeNull();
    expect(latestKnownNav([point(1,null)])).toBeUndefined();
  });
  it('presents provider names without exposing internal source identifiers',()=>{
    expect(sourceName('tefas-prices')).toBe('TEFAS');
    expect(sourceName('kap_report_index')).toBe('KAP');
    expect(sourceName('internal-unknown-source')).toBe('Yayımlanmış kaynak');
  });
  it('explains saved assessments without showing internal codes or comparison numbers',()=>{
    expect(friendlyEvidenceText('D1 [değer: 0.012; eşik: 0.01; eşik aşıldı]')).toBe('Benzer fonlara göre fiyat farkı (inceleme gerekiyor)');
    const text=friendlyEvidenceText('D2 [değer: bilinmiyor; eşik: bilinmiyor; kanıt yetersiz]');
    expect(text).toBe('Benzer fonlarla farkın değişimi (bilgi yetersiz)');
  });
  it('breaks the line at missing, ambiguous, zero and nonfinite observations', () => {
    const result = fundSeries([point(1, '10'), point(2, '12'), point(3, null), point(4, '14'), point(5, '16', true), point(6, '0'), point(7, 'NaN'), point(8, '18')]);
    expect(result.segments.map(segment => segment.length)).toEqual([2, 1, 1]);
    expect(result.coordinates.filter(item => item.y === null).map(item => item.index)).toEqual([2, 4, 5, 6]);
    expect(result.low).toBe(10); expect(result.high).toBe(18);
  });
  it('uses actual calendar spacing and keeps a constant series finite', () => {
    const result = fundSeries([point(1, '8.125'), point(2, '8.125'), point(11, '8.125')]);
    expect(result.coordinates.map(item => item.x)).toEqual([12, 90, 792]);
    expect(result.coordinates.map(item => item.y)).toEqual([148, 148, 148]);
    expect(fundSeries([point(1, '8.125')]).coordinates).toEqual([{index: 0, x: 12, y: 148}]);
  });
  it('does not invent a series when every observation is unavailable', () => {
    expect(fundSeries([point(1, null), point(2, '12', true), point(3, '-3')]).segments).toEqual([]);
    expect(fundSeries([]).segments).toEqual([]);
  });
  it('anchors the selected calendar window to the last actual observation without filling gaps', () => {
    const points = [point(1, '10'), point(2, null), point(10, '20'), point(11, '21')];
    expect(fundWindow(points, 3)).toEqual(points.slice(2));
    expect(fundWindow(points, 10)).toEqual(points.slice(1));
    expect(fundWindow(points, null)).toBe(points);
    expect(fundWindow([], 31)).toEqual([]);
  });
});
