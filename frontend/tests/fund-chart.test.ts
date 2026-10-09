import {describe, expect, it} from 'vitest';
import {prepareChart} from '../src/components/FundChart';
import {syntheticFunds} from '../src/lib/synthetic';

describe('rendering the authored chart', () => {
  it('uses the actual supplied values and distinct segments across gaps', () => {
    const chart = prepareChart(syntheticFunds[0].chart)!;
    expect(chart.fundSegments).toHaveLength(2);
    expect(chart.fundSegments[0].at(-1)?.time).toBe('2026-07-15');
    expect(chart.fundSegments[1][0]).toEqual({time: '2026-08-15', value: 106});
    expect(chart.peerSegments).toHaveLength(1);
    const changed = structuredClone(syntheticFunds[0].chart);
    changed.points.at(-1)!.fund = '111';
    expect(prepareChart(changed)!.fundSegments.at(-1)!.at(-1)!.value).toBe(111);
  });
  it('does not create a chart for unavailable inputs', () => {
    expect(prepareChart(syntheticFunds[3].chart)).toBeNull();
  });
  it('rejects future points, non-common baselines, and too few peers', () => {
    const future = structuredClone(syntheticFunds[0].chart);
    future.points.push({date: '2026-09-17', fund: '999', peers: '999'});
    expect(prepareChart(future)).toBeNull();
    const baseline = structuredClone(syntheticFunds[0].chart);
    baseline.points[0].peers = '101';
    expect(prepareChart(baseline)).toBeNull();
    const peers = structuredClone(syntheticFunds[0].chart);
    peers.peer_count = 9;
    expect(prepareChart(peers)).toBeNull();
    const overflow = structuredClone(syntheticFunds[0].chart);
    overflow.points.at(-1)!.fund = '1e999';
    expect(prepareChart(overflow)).toBeNull();
  });
});
