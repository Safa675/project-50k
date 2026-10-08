// Authored synthetic browser fixtures only. No private archive is imported.
import {createHash} from 'node:crypto';
import type {Fund, Source, ResearchSummary} from '../../src/lib/research-contract';

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
      }, evidence: sources.map(item => item.source_id),
    };
  });
  const group = (fund: Fund) => fund.eligible_crossings === 2 ? 0 : fund.eligible_crossings === 1 ? 1 : fund.assessment === 'FULL' ? 3 : 2;
  funds.sort((left, right) => group(left) - group(right) || left.code.localeCompare(right.code));
  const summary: ResearchSummary = {total: 100, denominator: 100, fully_assessable: 97,
    partially_assessable: 2, unavailable: 1, two_findings: 1, one_finding: 2,
    unassessable_no_findings: 2, no_findings: 95, d1_assessable: 98, flow_assessable: 98, d1_stale: 1};
  return {list: {...METADATA, funds}, summary: {...METADATA, summary},
    detail: (code: string) => ({...METADATA, fund: funds.find(fund => fund.code === code), sources: sourcesByCode[code] ?? []})};
}
