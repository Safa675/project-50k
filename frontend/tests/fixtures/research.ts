// Authored synthetic browser fixtures only. No private archive is imported.
import {createHash} from 'node:crypto';
import type {Fund, Source, ResearchSummary, Concentration} from '../../src/lib/research-contract';

export const BUNDLE_ID = 'a'.repeat(64);
export const CUTOFF_AT = '2026-09-16T23:59:59+03:00';
export const METADATA = {
  origin: 'HISTORICAL_REPLAY', analysis_mode: 'EXPLORATORY_ARCHIVE', cutoff_at: CUTOFF_AT,
  cutoff_semantics: 'RECORDED_SOURCE_DATE_FILTER', point_in_time_verified: false,
  historical_availability: 'UNKNOWN', rights_status: 'UNKNOWN',
  universe_basis: 'OCTOBER_2026_INVESTOR_SNAPSHOT', category_basis: 'CURRENT_SNAPSHOT',
  immutable_bundle_id: BUNDLE_ID,
} as const;

function identifier(index: number, kind: string): string {
  return kind + index.toString(16).padStart(63, '0');
}

function authoredPdf(): Buffer {
  const content = 'BT /F1 12 Tf 40 100 Td (Authored synthetic browser fixture) Tj ET\n';
  const second = 'BT /F1 12 Tf 40 100 Td (Authored synthetic second page) Tj ET\n';
  const objects = [
    '<< /Type /Catalog /Pages 2 0 R >>',
    '<< /Type /Pages /Kids [3 0 R 6 0 R] /Count 2 >>',
    '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
    '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
    `<< /Length ${Buffer.byteLength(content)} >>\nstream\n${content}endstream`,
    '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] /Resources << /Font << /F1 4 0 R >> >> /Contents 7 0 R >>',
    `<< /Length ${Buffer.byteLength(second)} >>\nstream\n${second}endstream`,
  ];
  let result = '%PDF-1.4\n';
  const offsets = [0];
  objects.forEach((object, index) => {
    offsets.push(Buffer.byteLength(result));
    result += `${index + 1} 0 obj\n${object}\nendobj\n`;
  });
  const xref = Buffer.byteLength(result);
  result += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  offsets.slice(1).forEach(offset => { result += `${String(offset).padStart(10, '0')} 00000 n \n`; });
  result += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
  return Buffer.from(result);
}

export const SYNTHETIC_PDF = authoredPdf();
const PDF_SHA = createHash('sha256').update(SYNTHETIC_PDF).digest('hex');

function source(index: number, code: string, kind: 'PRICE'|'KAP_SERIES'|'KAP_PDF'): Source {
  const pdf = kind === 'KAP_PDF';
  const id = pdf ? '900000001' : null;
  return {
    source_id: identifier(index, kind === 'PRICE' ? '1' : kind === 'KAP_SERIES' ? '2' : '3'),
    kind, label: `Authored synthetic ${kind}`, fund_code: code,
    sha256: pdf ? PDF_SHA : identifier(index, '9'),
    file_name: pdf ? 'authored-synthetic-report.pdf' : 'authored-synthetic-input.json',
    media_type: pdf ? 'application/pdf' : 'application/json', pdf_available: pdf,
    published_at: pdf ? '2026-09-02T11:00:00+03:00' : null,
    retrieved_at: null, historical_availability: 'UNKNOWN', rights_status: 'UNKNOWN',
    origin: 'HISTORICAL_REPLAY', disclosure_id: id,
    disclosure_url: id ? `https://www.kap.org.tr/tr/Bildirim/${id}` : null,
  };
}

function d1(index: number, priceId: string): Fund['d1'] {
  const missing = index === 4;
  const stale = index === 3;
  const crossing = index === 0 || index === 2 || stale;
  return {
    arithmetic_status: missing ? 'UNAVAILABLE' : 'AVAILABLE',
    research_screen: missing ? 'UNKNOWN' : crossing ? 'CROSSING' : 'NO_CROSSING',
    freshness: missing ? 'UNKNOWN' : stale ? 'STALE' : 'FRESH', production_status: 'ABSTAINED',
    missing_reasons: missing ? ['price_source_missing'] : stale ? ['final_contributing_observation_before_cutoff'] : [],
    qualifications: ['historical_availability_unknown', 'peer_category_membership_from_current_snapshot'],
    metric_period: {start: missing ? null : '2026-06-23', end: missing ? null : '2026-09-16'},
    units: {statistic: 'DAILY_LOG_RETURN', threshold: 'DAILY_LOG_RETURN'}, input_refs: [priceId],
    statistic: missing ? null : crossing ? '0.0020' : '0.0002', threshold: missing ? null : '0.0010',
    usable_observations: missing ? 0 : stale ? 59 : 60, window_positions: missing ? 0 : 60,
    eligible_peers: missing ? 0 : 20, latest_contributing_at: missing ? null : stale ? '2026-09-15' : '2026-09-16',
  };
}

function flow(index: number, seriesId: string): Fund['flow'] {
  const missing = index === 2 || index === 4;
  const rate = index === 0 ? '0.20' : index === 1 ? '-0.20' : index === 3 ? '0.03' : '0';
  return {
    arithmetic_status: missing ? 'UNAVAILABLE' : 'AVAILABLE',
    research_screen: missing ? 'UNKNOWN' : index < 2 ? 'CROSSING' : 'NO_CROSSING',
    freshness: missing ? 'UNKNOWN' : 'FRESH', production_status: 'ABSTAINED',
    missing_reasons: missing ? ['kap_series_missing'] : [],
    qualifications: ['currency_unknown_common_report_field_assumption', 'distribution_status_unknown',
      'baseline_unverified', 'endpoint_estimate_not_reported_cash'],
    metric_period: {start: '2026-07', end: '2026-08'}, units: {statistic: 'RATIO', threshold: 'RATIO'},
    input_refs: [seriesId], statistic: missing ? null : rate, threshold: '0.10',
    direction: missing ? 'UNKNOWN' : index === 1 ? 'OUTFLOW_ESTIMATE' : index === 0 || index === 3 ? 'INFLOW_ESTIMATE' : 'NONE',
    previous_assets: missing ? null : '1000', current_assets: missing ? null : index === 0 ? '1220' : index === 1 ? '800' : index === 3 ? '1030' : '1000',
    previous_nav: missing ? null : '1', current_nav: missing ? null : index === 0 ? '1.02' : '1',
    residual: missing ? null : index === 0 ? '200' : index === 1 ? '-200' : index === 3 ? '30' : '0',
    endpoint_refs: missing ? [] : ['2026-07', '2026-08'].map((period, endpoint) => ({
      period, source_id: seriesId, record_sha256: identifier(index, endpoint === 0 ? '4' : '5'),
      record_hash_basis: 'CONSUMED_ENDPOINT_FIELDS', published_at: endpoint === 0 ? '2026-08-03T11:00:00+03:00' : '2026-09-02T11:00:00+03:00',
      published_at_raw: endpoint === 0 ? '03.08.2026 11:00:00' : '02.09.2026 11:00:00', historical_availability: 'UNKNOWN',
    })),
    input_units: {assets: 'REPORT_CURRENCY', nav: 'REPORT_CURRENCY_PER_UNIT'},
  };
}

export function authoredConcentration(pdfId?: string): Concentration {
  const available = !!pdfId;
  return {
    schema: 'p50k.holding-concentration.v1', status: available ? 'PARTIAL' : 'UNAVAILABLE',
    research_screen: 'NOT_SCREENED', production_status: 'ABSTAINED', scope: 'POSITIVE_IDENTIFIED_ISIN_SECURITIES',
    weight_basis: 'NORMALIZED_IDENTIFIED_SECURITIES_VALUE', coverage_basis: 'REPORTED_PORTFOLIO_VALUE',
    issuer_aggregation: 'NOT_AVAILABLE', fund_lookthrough: 'NOT_PERFORMED', cadence: 'MONTHLY',
    report_period: available ? '2026-08' : null, effective_date: available ? '2026-08-31' : null,
    published_at: available ? '2026-09-02T11:00:00+03:00' : null, age_days: available ? 16 : null,
    current_source_id: pdfId ?? null, input_refs: pdfId ? [pdfId] : [], missing_reasons: available ? [] : ['selected_monthly_holdings_missing'],
    qualifications: ['historical_availability_unknown', 'security_concentration_not_issuer_concentration',
      'normalized_identified_subset_not_whole_fund', 'no_anomaly_threshold_registered', ...(available ? ['nonsecurity_or_derivative_positions_excluded'] : [])],
    subset_value: available ? '750' : null, reported_portfolio_value: available ? '1000' : null, portfolio_rounding_bound: available ? '0' : null,
    portfolio_coverage_ratio: available ? '0.75' : null, position_count: available ? 2 : 0,
    top1_ratio: available ? '0.8' : null, top5_ratio: available ? '1' : null,
    top10_ratio: available ? '1' : null, hhi: available ? '0.68' : null,
    positions: pdfId ? [
      {isin: 'TRSYNA000001', native_name: 'Örnek Kıymet Alfa', value: '600', weight: '0.8', source_rows: [{source_id: pdfId, page: 1, bbox: [40, 80, 240, 100], reported_value: '600'}]},
      {isin: 'TRSYNA000002', native_name: 'Örnek Kıymet Beta', value: '150', weight: '0.2', source_rows: [{source_id: pdfId, page: 2, bbox: [40, 80, 240, 100], reported_value: '150'}]},
    ] : [],
    comparison: {status: 'UNAVAILABLE', reason: 'both_reports_require_complete_comparable_security_coverage',
      previous_period: null, previous_effective_date: null, previous_published_at: null, input_refs: [],
      previous_top1_ratio: null, previous_top5_ratio: null, previous_top10_ratio: null, previous_hhi: null,
      top1_ratio_delta: null, top5_ratio_delta: null, top10_ratio_delta: null, hhi_delta: null},
  };
}

export function researchFixture() {
  const sourcesByCode: Record<string, Source[]> = {};
  const funds: Fund[] = Array.from({length: 100}, (_, index) => {
    const code = index === 99 ? 'IAA' : `S${String(index).padStart(2, '0')}`;
    const sources = [source(index, code, 'PRICE'), source(index, code, 'KAP_SERIES')];
    if (index === 0) sources.push(source(index, code, 'KAP_PDF'));
    sourcesByCode[code] = sources;
    return {
      code, name: index === 0 ? 'Örnek Çığ Fonu' : `Örnek Sentetik Fon ${index}`,
      category: index % 2 === 0 ? 'Örnek Hisse' : 'Örnek Değişken',
      comment_tr: index === 0 ? 'İki ayrı araştırma eşiği aşıldı; bu sentetik bir test yorumudur.' : index === 1 ? 'Tahmini çıkış eşiği aşıldı; bu sentetik bir test yorumudur.' : index === 2 ? 'Tek bulgu mevcut; aylık veri eksik. Sentetik test yorumu.' : index === 3 ? 'Son geçerli gözlem eski; birlikte sayılmadı. Sentetik test yorumu.' : index === 4 ? 'İki hesap için veri yetersiz. Sentetik test yorumu.' : 'Bu kesitte eşik aşımı yok; bu bir güvenlik sonucu değildir. Sentetik test yorumu.',
      assessment: index === 4 ? 'UNAVAILABLE' : index === 2 || index === 3 ? 'PARTIAL' : 'FULL',
      eligible_crossings: index === 0 ? 2 : index === 1 || index === 2 ? 1 : 0,
      d1: d1(index, sources[0].source_id), flow: flow(index, sources[1].source_id),
      chart: index === 4 ? {status: 'UNAVAILABLE', reason: 'no_common_valid_baseline_with_10_peers', baseline_date: null, unit: 'INDEX_100', points: [], peer_count: 0} : {
        status: 'AVAILABLE', reason: null, baseline_date: '2026-07-01', unit: 'INDEX_100', peer_count: 20,
        points: [{date: '2026-07-01', fund: '100', peers: '100'}, {date: '2026-07-15', fund: '102', peers: '101'},
          {date: '2026-08-03', fund: null, peers: '102'}, {date: '2026-08-17', fund: '106', peers: '102.5'},
          {date: '2026-09-01', fund: '105.5', peers: '103'}, {date: '2026-09-16', fund: '108', peers: '104'}],
      }, concentration: authoredConcentration(sources.find(item => item.kind === 'KAP_PDF')?.source_id), evidence: sources.map(item => item.source_id),
    };
  });
  const group = (fund: Fund) => fund.eligible_crossings === 2 ? 0 : fund.eligible_crossings === 1 ? 1 : fund.assessment === 'FULL' ? 3 : 2;
  funds.sort((left, right) => group(left) - group(right) || left.code.localeCompare(right.code));
  const summary: ResearchSummary = {total: 100, denominator: 100, fully_assessable: 97,
    partially_assessable: 2, unavailable: 1, two_findings: 1, one_finding: 2,
    unassessable_no_findings: 2, no_findings: 95, d1_assessable: 98, flow_assessable: 98, d1_stale: 1,
    concentration_available: 0, concentration_partial: 1, concentration_unavailable: 99};
  return {list: {...METADATA, funds}, summary: {...METADATA, summary},
    detail: (code: string) => ({...METADATA, fund: funds.find(fund => fund.code === code), sources: sourcesByCode[code] ?? []})};
}
