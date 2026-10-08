'use client';
import Link from 'next/link';
import {useState} from 'react';
import type {Fund, Source} from '@/lib/research-contract';
import {amount, percent, date, screenLabel, flowLabel, reason, sourceTitle, reportedPdfPeriod} from '@/lib/presentation';
import Shell from './Shell';
import Chip from './primitives/Chip';
import EmptyState from './primitives/EmptyState';
import FundChart from './FundChart';
import SourcePdfDialog from './SourcePdfDialog';

interface Props {
  fund: Fund;
  sources: Source[];
  synthetic?: boolean;
  bundleId?: string;
  backQuery?: string;
}
function SourceEntry({source, openPdf, technical = false}: {source: Source; openPdf: (source: Source) => void; technical?: boolean}) {
  return <div className="evidence-source">
    <strong>{sourceTitle(source)}</strong>
    {technical && <p className="detail-note source-hash">{source.file_name}</p>}
    <dl>
      <div><dt>Kayıtlı yayın zamanı</dt><dd>{date(source.published_at)}</dd></div>
      <div><dt>Arşive alınma zamanı</dt><dd>{date(source.retrieved_at)}</dd></div>
      <div><dt>Geçmiş erişilebilirlik</dt><dd>Doğrulanmadı</dd></div>
    </dl>
    <details className="detail-note source-version">
      <summary>Kaynak sürümü ve zaman kaydı</summary>
      <p>Kaynak dosyasının özeti:</p><code className="source-hash">{source.sha256}</code>
      <p>Kayıtlı yayın: {source.published_at ?? 'Bilinmiyor'}<br/>Arşive alınma: {source.retrieved_at ?? 'Bilinmiyor'}</p>
    </details>
    {source.disclosure_url && <a className="source-link" href={source.disclosure_url} target="_blank" rel="noreferrer">KAP bildirimini aç ↗</a>}
    {source.pdf_available && <button className="button" onClick={() => openPdf(source)}>Orijinal PDF’yi aç</button>}
  </div>;
}
function Qualifications({values}: {values: string[]}) {
  if (!values.length) return null;
  return <details className="qualification-panel">
    <summary>Varsayımlar ve hesap sınırları ({values.length})</summary>
    <ul>{values.map(value => <li key={value}>{reason(value)}</li>)}</ul>
  </details>;
}
export default function FundDetail({fund, sources, synthetic = false, bundleId = 'synthetic', backQuery = ''}: Props) {
  const [pdf, setPdf] = useState<Source | null>(null);
  const primary = sources.filter(source => source.fund_code === fund.code && ['PRICE', 'KAP_SERIES', 'KAP_PDF'].includes(source.kind));
  const peers = sources.filter(source => source.kind === 'PRICE' && source.fund_code !== fund.code);
  const groupedIds = new Set([...primary, ...peers].map(source => source.source_id));
  const versions = sources.filter(source => !groupedIds.has(source.source_id));
  const hasPdf = primary.some(source => source.pdf_available);
  const missingMonthlyPdfs = ['2026-07', '2026-08'].filter(period =>
    fund.flow.endpoint_refs.some(endpoint => endpoint.period === period) &&
    !primary.some(source => source.kind === 'KAP_PDF' && source.pdf_available && reportedPdfPeriod(source.file_name) === period));
  return <Shell synthetic={synthetic}>
    <Link href={`${synthetic ? '/preview' : '/'}${backQuery ? '?' + backQuery : ''}`} className="back-link">← Fon listesine dön</Link>
    <section className="page-intro">
      <div><p className="eyebrow">{fund.category ?? 'Kategori bilgisi yok'}</p><h1>{fund.code} <span className="text-xl font-normal text-[var(--text-secondary)]">{fund.name}</span></h1></div>
      <div className="cutoff"><span>İnceleme zamanı</span>16 Eylül 2026 · 23:59 İstanbul</div>
    </section>
    <div className="detail-summary">{fund.comment_tr}</div>
    <div className="detail-layout">
      <div>
        <section className="detail-section">
          <h2>Fon ve benzerlerinin getirisi</h2>
          <FundChart chart={fund.chart} synthetic={synthetic}/>
          {fund.chart.status === 'AVAILABLE' && <p className="detail-note">Fon kendi benzerler grubuna katılmaz.</p>}
        </section>
        <section className="detail-section">
          <h2>İki ayrı araştırma hesabı</h2>
          <div className="metrics">
            <div className="metric-panel">
              <h3>Benzer fonlara göre getiri farkı</h3>
              <p className="detail-note">Son 60 ortak fiyat tarihindeki günlük getiri farklarının medyanı. Geçerli gözlem ve uygun benzer fon sayısı yeterli olmalıdır.</p>
              <Chip variant={fund.d1.research_screen === 'CROSSING' ? 'warning' : 'outline'}>{screenLabel(fund.d1)}</Chip>
              <span className="metric-value" title={fund.d1.statistic ?? undefined}>{percent(fund.d1.statistic, 4)}</span>
              <dl>
                <div><dt>Sabit kategori eşiği</dt><dd title={fund.d1.threshold ?? undefined}>{percent(fund.d1.threshold, 4)}</dd></div>
                <div><dt>Gözlem dönemi</dt><dd>{date(fund.d1.metric_period.start)} – {date(fund.d1.metric_period.end)}</dd></div>
                <div><dt>Geçerli gözlem</dt><dd>{fund.d1.usable_observations} / {fund.d1.window_positions}</dd></div>
                <div><dt>Uygun benzer fon</dt><dd>En az {fund.d1.eligible_peers} fon</dd></div>
                <div><dt>Son katkı veren gözlem</dt><dd>{date(fund.d1.latest_contributing_at)}</dd></div>
              </dl>
              {fund.d1.missing_reasons.map(value => <p className="detail-note" key={value}>{reason(value)}</p>)}
              <Qualifications values={fund.d1.qualifications}/>
              <details className="detail-note"><summary>Tam hesap değerleri</summary><p>Günlük log getiri farkı: <code>{fund.d1.statistic ?? 'Bilinmiyor'}</code><br/>Sabit eşik: <code>{fund.d1.threshold ?? 'Bilinmiyor'}</code></p></details>
            </div>
            <div className="metric-panel">
              <h3>Tahmini para hareketi</h3>
              <Chip variant={fund.flow.research_screen === 'CROSSING' ? 'warning' : 'outline'}>{flowLabel(fund)}</Chip>
              <span className="metric-value" title={fund.flow.statistic ?? undefined}>{percent(fund.flow.statistic)}</span>
              <dl>
                <div><dt>Sabit sınır · mutlak oran</dt><dd>{percent(fund.flow.threshold, 0)}</dd></div>
                <div><dt>Rapor dönemleri</dt><dd>{date(fund.flow.metric_period.start)} → {date(fund.flow.metric_period.end)}</dd></div>
                <div><dt>Temmuz toplam değer</dt><dd>{amount(fund.flow.previous_assets)}<small>rapor para birimi</small></dd></div>
                <div><dt>Ağustos toplam değer</dt><dd>{amount(fund.flow.current_assets)}<small>rapor para birimi</small></dd></div>
                <div><dt>Temmuz pay fiyatı</dt><dd>{amount(fund.flow.previous_nav, 6)}<small>rapor para birimi / pay</small></dd></div>
                <div><dt>Ağustos pay fiyatı</dt><dd>{amount(fund.flow.current_nav, 6)}<small>rapor para birimi / pay</small></dd></div>
                <div><dt>Hesaplanan fark</dt><dd>{amount(fund.flow.residual)}<small>rapor para birimi</small></dd></div>
              </dl>
              <p className="detail-note">Fiyat etkisi çıkarıldıktan sonra kalan farktır. Gerçekte bildirilen yatırımcı nakit akışı değildir. Para birimi, kapsam ve fon işlemleri doğrulanmadığında hesap koşulludur.</p>
              {fund.flow.missing_reasons.map(value => <p className="detail-note" key={value}>{reason(value)}</p>)}
              <div className="endpoint-publications">
                <h3>Aylık raporların yayın kaydı</h3>
                {(['2026-07', '2026-08'] as const).map(period => {
                  const endpoint = fund.flow.endpoint_refs.find(reference => reference.period === period);
                  return <div key={period} className="endpoint-record"><p><strong>{date(period)}</strong><br/>Kayıtlı yayın: {date(endpoint?.published_at ?? null)}</p>{endpoint && <details className="detail-note"><summary>Kaydedilmiş zaman ve uç değer sürümü</summary><p>Yayın kaydı: {endpoint.published_at ?? 'Bilinmiyor'}<br/>Arşivdeki zaman: {endpoint.published_at_raw ?? 'Bilinmiyor'}</p><p>Özet, hesapta kullanılan uç değer alanlarına aittir:</p><code className="source-hash">{endpoint.record_sha256}</code><p>Geçmiş erişilebilirlik: doğrulanmadı</p></details>}</div>;
                })}
              </div>
              <Qualifications values={fund.flow.qualifications}/>
              <details className="detail-note"><summary>Tam hesap girdileri</summary><dl><div><dt>Temmuz toplam değer</dt><dd>{fund.flow.previous_assets ?? 'Bilinmiyor'}</dd></div><div><dt>Ağustos toplam değer</dt><dd>{fund.flow.current_assets ?? 'Bilinmiyor'}</dd></div><div><dt>Temmuz pay fiyatı</dt><dd>{fund.flow.previous_nav ?? 'Bilinmiyor'}</dd></div><div><dt>Ağustos pay fiyatı</dt><dd>{fund.flow.current_nav ?? 'Bilinmiyor'}</dd></div><div><dt>Fark / oran</dt><dd>{fund.flow.residual ?? 'Bilinmiyor'} / {fund.flow.statistic ?? 'Bilinmiyor'}</dd></div></dl></details>
            </div>
          </div>
        </section>
      </div>
      <aside>
        <section className="detail-section">
          <h2>Hesabın kaynakları</h2>
          <p className="detail-note">Rapor dönemi, kayıtlı yayın zamanı ve arşive alınma zamanı ayrı bilgilerdir. Yayın zamanı, bu arşiv sürümünün o tarihte erişilebilir olduğunu kanıtlamaz.</p>
          {primary.length === 0 ? <EmptyState title={synthetic ? 'Kaynak görünümü örneği' : 'Fona ait kaynak bilgisi bulunamadı'} description={synthetic ? 'Aylık rapor ve fiyat kaydı burada listelenir.' : 'Eksik kaynak yerine bir değer üretilmedi.'}/> : primary.map(source => <SourceEntry source={source} openPdf={setPdf} key={source.source_id}/>)}
          {!hasPdf && <p className="detail-note missing-pdf">Bu pakette açılabilir orijinal PDF bulunmuyor.</p>}
          {missingMonthlyPdfs.map(period => <p className="detail-note missing-pdf" key={period}>{date(period)} hesabının uç değer kaydı mevcut; bu döneme ait açılabilir orijinal PDF pakette eşleştirilemedi.</p>)}
          {peers.length > 0 && <details className="evidence-group"><summary>Benzer fonların fiyat kaynakları ({peers.length})</summary>{peers.map(source => <SourceEntry source={source} openPdf={setPdf} key={source.source_id}/>)}</details>}
          {versions.length > 0 && <details className="evidence-group"><summary>Hesap sürümleri ve diğer kaynaklar ({versions.length})</summary>{versions.map(source => <SourceEntry source={source} openPdf={setPdf} technical key={source.source_id}/>)}</details>}
        </section>
        <div className="notice"><strong>Yorumun sınırı</strong><br/>Eşik aşımı dolandırıcılık kanıtı değildir. Eşik aşımı olmaması da güvenli olduğu anlamına gelmez. Tarihsel sürüm ve erişim zamanı doğrulanmadı.</div>
        <p className="detail-note">Üretim kararı: değerlendirme dışı</p>
        <details className="detail-note"><summary>Araştırma paketinin sürümü</summary><code className="source-hash">{synthetic ? 'Örnek veri' : bundleId}</code></details>
      </aside>
    </div>
    <SourcePdfDialog source={pdf} bundleId={bundleId} onClose={() => setPdf(null)}/>
  </Shell>;
}
