'use client';
import type {Fund, Source} from '@/lib/research-contract';
import {amount, concentrationLabel, date, percent, percentagePoints} from '@/lib/presentation';
import EmptyState from './primitives/EmptyState';
import {DataTable, DataTableHeader, DataTableHeaderCell, DataTableBody, DataTableRow, DataTableCell} from './primitives/DataTable';

const LIMITS: Record<string, string> = {
  historical_availability_unknown: 'Bu arşiv sürümünün rapor tarihinde erişilebilirliği doğrulanmadı.',
  security_concentration_not_issuer_concentration: 'Aynı şirketin farklı kıymetleri ayrı sayılır; şirket bazında yoğunlaşma hesaplanmadı.',
  normalized_identified_subset_not_whole_fund: 'Kıymet payları, kimliği belirlenebilen pozitif menkul kıymet değerlerinin toplamına göre hesaplanır.',
  no_anomaly_threshold_registered: 'Bu ölçü için bir alarm eşiği belirlenmedi.',
  positive_security_without_identified_isin: 'ISIN kimliği belirlenemeyen kıymetler hesaba katılmadı.',
  nonsecurity_or_derivative_positions_excluded: 'Nakit ve diğer kıymet dışı kalemler ile türev pozisyonlar bu ölçüye katılmadı.',
  fund_holdings_without_lookthrough: 'Tutulan yatırım fonlarının kendi içindeki yatırımları ayrıştırılmadı.',
  coverage_exceeds_one_within_printed_rounding: 'Kıymet toplamı rapor toplamını, basılı sayıların doğrulanmış yuvarlama sınırı içinde az miktarda aşıyor. Kapsam oranı 100’e kırpılmadı.',
  selected_monthly_holdings_missing: 'İnceleme tarihinden önce yayımlanmış uygun aylık portföy raporu bulunamadı.',
  selected_holdings_not_reconciled: 'Okunan pozisyonlar raporun portföy toplamıyla doğrulanamadı.',
  negative_or_invalid_position_value: 'Negatif veya geçersiz pozisyon değeri nedeniyle hesap yapılmadı.',
  no_positive_identified_security_values: 'Pozitif değeri ve ISIN kimliği birlikte doğrulanmış kıymet bulunamadı.',
  positive_reported_portfolio_value_missing: 'Geçerli bir portföy toplamı bulunamadı.',
  identified_subset_exceeds_reported_portfolio: 'Okunan kıymetlerin toplamı raporun portföy toplamını aşıyor.',
  publication_missing_or_invalid: 'Raporun yayın zamanı bilinmiyor veya geçersiz.',
  verified_pdf_source_reference_missing: 'Doğrulanmış orijinal PDF kaydı bulunamadı.',
  previous_report_unavailable: 'Önceki uygun aylık rapor mevcut değil.',
  both_reports_require_complete_comparable_security_coverage: 'İki rapor da tam ve karşılaştırılabilir kıymet kapsamı sağlamadığı için değişim hesaplanmadı.',
  report_value_basis_not_verified_comparable: 'Raporların değerleme ve para birimi temellerinin karşılaştırılabilirliği doğrulanmadı.',
  previous_period_not_earlier: 'Karşılaştırma raporu daha önceki bir döneme ait değil.',
};
function limitation(value: string) {return LIMITS[value] ?? 'Raporun bu hesap için uygunluğu doğrulanamadı.';}

export default function ConcentrationPanel({holding, sources, openPdf}: {holding: Fund['concentration']; sources: Source[]; openPdf: (source: Source) => void}) {
  const currentPdf = holding ? sources.find(source => source.kind === 'KAP_PDF' && source.pdf_available && source.source_id === holding.current_source_id) : undefined;
  const available = holding && holding.status !== 'UNAVAILABLE';
  return <section className="detail-section concentration-section" aria-labelledby="concentration-title">
    <h2 id="concentration-title">Son açıklanan portföyde yoğunlaşma</h2>
    <p className="detail-note">Fonun yatırımları kaç farklı menkul kıymete dağılmış? Buradaki paylar, okunabilen kıymetler içindeki dağılımı gösterir. Portföyün okunabilen payı ayrıca belirtilir.</p>
    {!holding ? <EmptyState title="Bu pakette portföy yoğunlaşması hesaplanmadı" description="Bu sürüm yalnızca iki önceki araştırma hesabını içeriyor."/> : <>
      <p className="concentration-status">{concentrationLabel(holding)}</p>
      <dl className="holding-dates">
        <div><dt>Aylık rapor dönemi</dt><dd>{date(holding.report_period)}</dd></div>
        <div><dt>Portföyün rapor tarihi</dt><dd>{date(holding.effective_date)}</dd></div>
        <div><dt>Kayıtlı yayın zamanı</dt><dd>{date(holding.published_at)}</dd></div>
        <div><dt>İnceleme gününde raporun yaşı</dt><dd>{holding.age_days === null ? 'Bilinmiyor' : `${holding.age_days} gün`}</dd></div>
      </dl>
      {available ? <>
        <div className="holding-coverage"><strong>Portföyün okunabilen payı: {percent(holding.portfolio_coverage_ratio)}</strong><p className="detail-note">Kimliği belirlenebilen pozitif menkul kıymetler / raporun portföy toplamı. {holding.status === 'PARTIAL' ? 'Portföyün tamamını temsil etmez.' : 'Pozisyonlar rapor toplamıyla kontrol edildi.'}</p></div>
        <h3>Okunabilen menkul kıymetler içinde</h3>
        <dl className="holding-metrics">
          <div><dt>En büyük kıymetin payı</dt><dd title={holding.top1_ratio ?? undefined}>{percent(holding.top1_ratio)}</dd></div>
          <div><dt>En büyük 5 kıymetin payı</dt><dd title={holding.top5_ratio ?? undefined}>{percent(holding.top5_ratio)}</dd></div>
          <div><dt>En büyük 10 kıymetin payı</dt><dd title={holding.top10_ratio ?? undefined}>{percent(holding.top10_ratio)}</dd></div>
          <div><dt>Yoğunlaşma ölçüsü · HHI</dt><dd title={holding.hhi ?? undefined}>{amount(holding.hhi, 4)}</dd></div>
          <div><dt>Farklı ISIN sayısı</dt><dd>{holding.position_count}</dd></div>
        </dl>
        <p className="detail-note">HHI, her kıymetin payının karesinin toplamıdır. Örneğin tek kıymet varsa 1; eşit paylı 10 kıymet varsa 0,1 olur. Bu sayı dolandırıcılık olasılığı değildir.</p>
        <DataTable minWidth={480} className="holding-table" aria-label="Okunan en büyük menkul kıymetler">
          <DataTableHeader><tr><DataTableHeaderCell>Kıymet ve ISIN</DataTableHeaderCell><DataTableHeaderCell>Okunan kıymetler içindeki pay</DataTableHeaderCell><DataTableHeaderCell>PDF satırı</DataTableHeaderCell></tr></DataTableHeader>
          <DataTableBody>{holding.positions.map(position => <DataTableRow key={position.isin}>
            <DataTableCell><strong className="holding-name">{position.native_name}</strong><span className="metric-hint">{position.isin}</span></DataTableCell>
            <DataTableCell><span className="metric-value" title={position.weight}>{percent(position.weight)}</span></DataTableCell>
            <DataTableCell><details className="detail-note"><summary>Sayfa {Array.from(new Set(position.source_rows.map(row => row.page))).join(', ')}</summary>{position.source_rows.map((row, index) => <p key={index}>Sayfa {row.page} · satır alanı: {row.bbox.map(value => amount(String(value))).join(', ')}<br/>Rapor değeri: {amount(row.reported_value)}<br/><code className="source-hash">{row.source_id}</code></p>)}</details></DataTableCell>
          </DataTableRow>)}</DataTableBody>
        </DataTable>
        <p className="detail-note">{holding.positions.length} / {holding.position_count} kıymet gösteriliyor. Aynı ISIN’in birden fazla satırı birleştirilmiştir. Kıymet değerleri raporun para birimindedir.</p>
      </> : <EmptyState title="Portföy yoğunlaşması hesaplanamadı" description="Eksik veya doğrulanamayan pozisyonlar yerine sıfır üretilmedi."/>}
      {holding.missing_reasons.length > 0 && <ul className="holding-limitations">{[...new Set(holding.missing_reasons.map(limitation))].map(value => <li key={value}>{value}</li>)}</ul>}
      <div className="holding-comparison"><h3>Önceki aylık rapora göre değişim</h3>
        {holding.comparison.status === 'AVAILABLE' ? <><p className="detail-note">{date(holding.comparison.previous_period)} → {date(holding.report_period)} · Önceki kayıtlı yayın: {date(holding.comparison.previous_published_at)}</p><dl><div><dt>En büyük 5 kıymetin payındaki değişim</dt><dd>{percentagePoints(holding.comparison.top5_ratio_delta)}</dd></div><div><dt>HHI değişimi</dt><dd>{amount(holding.comparison.hhi_delta, 4)}</dd></div></dl></> : <p className="detail-note">{limitation(holding.comparison.reason ?? 'previous_report_unavailable')}</p>}
      </div>
      {currentPdf ? <button className="button" onClick={() => openPdf(currentPdf)}>Yoğunlaşma raporunun PDF’sini aç</button> : <p className="detail-note">Bu hesap için açılabilir orijinal PDF eşleştirilemedi.</p>}
      <details className="qualification-panel"><summary>Kapsam ve hesap sınırları</summary><ul>{[...new Set(holding.qualifications.map(limitation))].map(value => <li key={value}>{value}</li>)}<li>Yalnızca aylık raporlar kullanılır; haftalık raporlar bu ölçüye katılmadı. Son açıklanan portföy, inceleme günündeki pozisyonları kanıtlamaz.</li></ul></details>
      <p className="detail-note">Bu bölüm bir alarm üretmez. Listedeki “iki bulgu / tek bulgu” sayıları getiri farkı ve tahmini para hareketi hesaplarına aittir.</p>
    </>}
  </section>;
}
