import {describe, it, expect} from 'vitest';
import {ConcentrationSchema, FundSchema} from '../src/lib/research-contract';
import {concentrationLabel, percentagePoints} from '../src/lib/presentation';
import {authoredConcentration, researchFixture} from './fixtures/research';
import {syntheticFunds} from '../src/lib/synthetic';

describe('bounded securities concentration', () => {
  const holding = () => authoredConcentration('c'.repeat(64));
  it('retains the subset denominator and partial portfolio coverage together', () => {
    const value = ConcentrationSchema.parse(holding());
    expect(value.top5_ratio).toBe('1'); expect(value.portfolio_coverage_ratio).toBe('0.75');
    expect(value.scope).toBe('POSITIVE_IDENTIFIED_ISIN_SECURITIES'); expect(value.status).toBe('PARTIAL');
  });
  it('does not add a third threshold crossing or alter the two existing assessments', () => {
    const fund = researchFixture().detail('S00').fund!;
    expect(FundSchema.parse(fund).eligible_crossings).toBe(2);
    expect(FundSchema.parse({...fund, concentration: {...fund.concentration!, status: 'AVAILABLE', qualifications: fund.concentration!.qualifications.filter(value => value !== 'nonsecurity_or_derivative_positions_excluded')}}).assessment).toBe(fund.assessment);
    expect(ConcentrationSchema.safeParse({...holding(), research_screen: 'CROSSING'}).success).toBe(false);
  });
  it('supports immutable older bundles with absent or null concentration', () => {
    expect(FundSchema.safeParse(syntheticFunds[0]).success).toBe(true);
    expect(FundSchema.safeParse({...syntheticFunds[0], concentration: null}).success).toBe(true);
    expect(concentrationLabel(null)).toBe('Bu pakette hesaplanmadı');
  });
  it('keeps missing concentration unknown rather than zero', () => {
    const missing = authoredConcentration();
    expect(ConcentrationSchema.safeParse(missing).success).toBe(true);
    expect(ConcentrationSchema.safeParse({...missing, top5_ratio: '0'}).success).toBe(false);
    expect(concentrationLabel(missing)).toBe('Hesaplanamadı');
  });
  it('rejects future publication and false reporting dates or ages', () => {
    for (const change of [{published_at: '2026-09-17T00:00:00+03:00'}, {effective_date: '2026-09-17'}, {age_days: 17}, {report_period: '2026-08-31'}, {report_period: '2026-13'}, {effective_date: '2026-08-30', age_days: 17}]) {
      expect(ConcentrationSchema.safeParse({...holding(), ...change}).success).toBe(false);
    }
  });
  it('rejects incomparable ratio bases, invalid weights and forged source rows', () => {
    for (const change of [{weight_basis: 'WHOLE_FUND'}, {portfolio_coverage_ratio: '1.01'}, {top1_ratio: '-0.1'}, {hhi: 'NaN'}, {position_count: 1}]) expect(ConcentrationSchema.safeParse({...holding(), ...change}).success).toBe(false);
    const value = holding(); value.positions[0].source_rows[0].source_id = 'd'.repeat(64);
    expect(ConcentrationSchema.safeParse(value).success).toBe(false);
  });
  it('rejects an available trend based on partial coverage or missing prior evidence', () => {
    const value = holding();
    value.comparison = {...value.comparison, status: 'AVAILABLE', reason: null, previous_period: '2026-07', previous_effective_date: '2026-07-31', previous_published_at: '2026-08-03T11:00:00+03:00', input_refs: [...value.input_refs], previous_top1_ratio: '0.5', previous_top5_ratio: '1', previous_top10_ratio: '1', previous_hhi: '0.5', top1_ratio_delta: '0.3', top5_ratio_delta: '0', top10_ratio_delta: '0', hhi_delta: '0.18'};
    expect(ConcentrationSchema.safeParse(value).success).toBe(false);
    expect(ConcentrationSchema.safeParse({...value, status: 'AVAILABLE', qualifications: value.qualifications.filter(item => item !== 'nonsecurity_or_derivative_positions_excluded')}).success).toBe(true);
    expect(ConcentrationSchema.safeParse({...value, status: 'AVAILABLE', comparison: {...value.comparison, previous_published_at: null}}).success).toBe(false);
  });
  it('formats concentration changes as signed percentage points', () => {
    expect(percentagePoints('0.2')).toBe('+20,00 yüzde puan');
    expect(percentagePoints('-0.05')).toBe('-5,00 yüzde puan');
    expect(percentagePoints(null)).toBe('—');
  });
});
