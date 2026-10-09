import {describe,it,expect} from 'vitest';
import {chartSegments} from '../src/lib/chart-data';
import {syntheticFunds} from '../src/lib/synthetic';
describe('missing chart segments',()=>{
 it('breaks a fund line at null instead of joining across the gap',()=>{const segments=chartSegments(syntheticFunds[0].chart.points,'fund');expect(segments).toHaveLength(2);expect(segments[0].at(-1)?.time).toBe('2026-07-15');expect(segments[1][0].time).toBe('2026-08-15');expect(segments.flat().some(point=>point.value===0)).toBe(false);});
 it('keeps fully observed peer context separate',()=>expect(chartSegments(syntheticFunds[0].chart.points,'peers')).toHaveLength(1));
 it('returns no synthetic baseline for missing charts',()=>expect(chartSegments(syntheticFunds[3].chart.points,'fund')).toEqual([]));
});
