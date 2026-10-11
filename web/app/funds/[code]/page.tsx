import Link from 'next/link';
import AssetLogo from '@/components/AssetLogo';
import {explainResult,resultStatus} from '@/lib/method-explanations';
import {notFound} from 'next/navigation';
import {requireUser, serverApi} from '@/lib/auth';
import {dateTr, decimal, reasonTr, stateTr} from '@/lib/client';
import {FundPoint, FundSignal, sourceTime, sourceName, signalName, latestKnownNav} from '@/lib/fund-display';
import NavChart, {FundMarker} from '@/components/NavChart';
import FundReportSeries,{FundReportPoint} from '@/components/FundReportSeries';
import FundTooltip from '@/components/FundTooltip';
import FundEvidence from '@/components/FundEvidence';
import FundSections from '@/components/FundSections';
import FundShare from '@/components/FundShare';
import FundDecision from '@/components/FundDecision';
import FundAlert from '@/components/FundAlert';
import AgentPage from '@/components/agents/AgentPage';
import WatchlistButton from '@/components/WatchlistButton';
import styles from '@/components/Funds.module.css';

type RegulatoryEvent = {event_id: string; effective_date: string | null; status: string; availability_unknown: boolean; source_url: string | null; source_sha256: string; available_at: string | null};
type Document = {document_key: string; report_period: string | null; published_at: string | null; available_at: string | null; source_sha256: string; source_url: string | null; has_local_document: boolean};

function EvidenceSources({signals,events,documents}:{signals:FundSignal[];events:RegulatoryEvent[];documents:Document[]}){
  return <div><div className={styles.sectionTitle}><h2>İncelemenin dayanakları</h2></div>
    {signals.map(signal=><details key={signal.evidence_id}><summary>{signalName(signal.detector_id)} · {resultStatus(signal)}</summary><p>{explainResult(signal)}</p>{signal.effective_date&&<p>İncelenen tarih: {dateTr(signal.effective_date)}</p>}{signal.source_references.length>0&&<p>Kaynak: {[...new Set(signal.source_references.map(ref=>sourceName(ref.source_id)))].join(', ')}</p>}</details>)}
    {signals.length===0&&<p className={styles.empty}>Bu fon için tamamlanmış inceleme bulunmuyor.</p>}
    <div className={styles.sectionTitle}><h2>Resmî duyurular</h2></div>
    {events.length?events.map(event=><div className="event" key={event.event_id}>{event.effective_date&&<strong>{dateTr(event.effective_date)}</strong>}<p>{event.status==='CONFIRMED'?'Bu kayıt fonla eşleştirildi.':'Kayıt ile fonun eşleşmesi inceleniyor.'}</p>{event.availability_unknown&&<p>Yayım saati bilinmediği için olayın o tarihte bilindiği varsayılmıyor.</p>}{event.source_url&&<a href={event.source_url} rel="noreferrer" target="_blank">Resmî duyuruyu aç</a>}</div>):<p className={styles.empty}>İncelenen SPK bülteninde bu fon için bir duyuru bulunamadı.</p>}
    {documents.length>0&&<div className={styles.sectionTitle}><h2>KAP raporları</h2></div>}
    {documents.map(document=><details key={document.document_key}><summary>{document.report_period??'Dönemi belirtilmemiş'} · Portföy raporu</summary><p>{document.published_at?`Yayım: ${sourceTime(document.published_at)}`:'Yayım tarihi kaynakta belirtilmemiş.'}</p>{document.source_url?<a href={document.source_url} target="_blank" rel="noreferrer">KAP’ta raporu aç</a>:<p>Bu kayıtta rapor bağlantısı bulunmuyor.</p>}</details>)}
  </div>;
}

export default async function Detail({params}: {params: Promise<{code: string}>}) {
  const {code} = await params;
  if (!/^[A-Z0-9]{2,12}$/.test(code)) notFound();
  const [response, documentResponse, seriesResponse, summaryResponse, user] = await Promise.all([serverApi(`/funds/${code}?days=731`), serverApi(`/funds/${code}/documents?limit=20`), serverApi(`/funds/${code}/series?limit=60`), serverApi(`/agents/funds/${code}/summary`).catch(()=>null), requireUser()]);
  if (response.status === 404) notFound();
  if (!response.ok) throw new Error('Fon verilerine şu anda erişilemiyor.');
  const data = await response.json();
  if (!data.fund || !Array.isArray(data.signals) || !Array.isArray(data.chart?.points)) throw new Error('Fon yanıtı doğrulanamadı.');
  const documents: Document[] = documentResponse.ok ? (await documentResponse.json()).items : [];
  const reportData=seriesResponse.ok?await seriesResponse.json():null;
  const reportPoints:FundReportPoint[]=Array.isArray(reportData?.items)?reportData.items:[];
  const points: FundPoint[] = data.chart.points;
  const signals: FundSignal[] = data.signals;
  const summary = summaryResponse?.ok ? await summaryResponse.json().catch(()=>null) : null;
  const newest = data.price_summary?.latest_observation ?? points.at(-1);
  const latest:FundPoint|undefined = data.price_summary?.last_available ?? latestKnownNav(points);
  const document = documents[0];
  const findings = [...signals].filter(signal => !signal.is_attribute).sort((a, b) => Number(b.state === 'TRIGGERED') - Number(a.state === 'TRIGGERED'));
  const markers: FundMarker[] = documents.filter(item => item.published_at !== null).slice(0, 12).map(item => ({
    date: new Intl.DateTimeFormat('en-CA', {timeZone: 'Europe/Istanbul', year: 'numeric', month: '2-digit', day: '2-digit'}).format(new Date(item.published_at!)),
    label: `KAP · ${item.report_period ?? 'Portföy raporu'}`, href: item.source_url ?? '#kap-reports',
  }));
  const sourceCount = new Set(signals.flatMap(signal => signal.source_references.map(ref => ref.source_sha256))).size;
  const overview = <>
    <h2 className={styles.srOnly}>Yayımlanmış günlük birim fiyat</h2><NavChart points={points} markers={markers}/>
    <FundReportSeries items={reportPoints}/>
    <div className={styles.sectionTitle}><h2>Gelişmeler</h2><Link className={styles.textButton} href={user.role === 'viewer' ? '/method' : '/review'}>{user.role === 'viewer' ? 'Yöntemde oku' : 'İnceleme kuyruğu'}<img src="/design/arrow.svg" alt=""/></Link></div>
    <FundEvidence signals={findings.slice(0, 3)}/>
    <div className={styles.sectionTitle}><h2>Fon bilgileri</h2></div>
    <dl className={styles.facts}>
      <div><dt>Fon kodu</dt><dd>{code}</dd></div><div><dt>Fon türü · güncel katalog</dt><dd>{data.fund.category ?? 'Kategori bilinmiyor'}</dd></div>
    </dl><details className="method-explanation"><summary>Bu sayfada hangi bilgiler var?</summary><p>Günlük fiyatlar ve tamamlanan fiyat karşılaştırmaları gösterilir. Pay sayısı, yatırımcı sayısı ve varlık dağılımı için tarihli kaynak kayıtları gerekir; güncel bir sayı geçmişe taşınmaz. Alınmış portföy raporları Kaynaklar bölümünden açılabilir.</p></details><div className={styles.reviewBlock} id="karar"><FundDecision code={code}/></div>
  </>;
  return <section className={styles.page} data-figma-node="21:206">
    <AgentPage fundCode={code}/>
    <header className={styles.identity}>
      <div className={styles.identityText}><AssetLogo kind="fund" code={code} name={data.fund.name} size={48} decorative/><div><div className={styles.identityMeta}><span className={styles.code}>{code}</span><span>{data.fund.category ?? 'Kategori bilinmiyor'}</span></div><h1>{data.fund.name}</h1></div></div>
      <div className={styles.actions}><FundShare/><Link className={styles.iconButton} href="/notifications" aria-label="Bildirimler"><img src="/design/bell.svg" alt=""/></Link><WatchlistButton code={code}/></div>
    </header>
    <div className={styles.priceSummary}><p className={styles.muted}><FundTooltip title="Fon pay fiyatı" text="Fonun yayımlanmış günlük birim pay değeri. Gün içi işlem fiyatı değildir. Kaynakta sıfır veya eksik gelen değerler kullanılmaz.">Günlük fon pay fiyatı</FundTooltip></p><div className={styles.priceLine}><span className={styles.priceValue}>{latest ? decimal(latest.nav) : 'Bu dönemde fiyat kaydı yok'}</span><span className={styles.muted}>{latest ? `${dateTr(latest.effective_date)} · TEFAS` : 'Bu dönemde yayımlanmış fiyat yok'}</span></div>{latest&&newest&&(newest.nav===null||newest.ambiguous_revision)&&<p className={styles.caption}>Son kayıtta ({dateTr(newest.effective_date)}) kullanılabilir fiyat yok. Gösterilen son fiyatın tarihi {dateTr(latest.effective_date)}.</p>}</div>
    <div className={styles.columns}>
      <div className={styles.mainColumn}><FundAlert summary={summary} signals={signals} canReview={user.role!=='viewer'}/><FundSections overview={overview} evidence={<><div className={styles.sectionTitle}><h2>Gelişmeler</h2></div><FundEvidence signals={findings}/></>} sources={<EvidenceSources signals={signals} events={data.events} documents={documents}/>}/></div>
      <aside className={styles.sidebar}>
        <div className={styles.card}><h2>Veri durumu</h2><dl>
          <div className={styles.dataRow}><dt>Fon pay fiyatı</dt><dd><FundTooltip align="end" title="Fiyatın kaynak tarihi" text={latest ? `Fiyatın tarihi: ${dateTr(latest.effective_date)}. İncelemede kullanılabildiği tarih: ${sourceTime(latest.available_at)}. Yayım zamanı: ${sourceTime(latest.published_at)}. Kaynak bilgileri grafik tablosunda bulunur.` : 'Sorgulanan dönemde kullanılabilir fiyat kaydı yok.'}>{latest ? `TEFAS, ${dateTr(latest.effective_date)}` : 'Veri yok'}</FundTooltip></dd></div>
          <div className={styles.dataRow}><dt>Aylık portföy raporu</dt><dd>{document ? `KAP, ${dateTr(document.published_at)}` : documentResponse.ok ? 'Kayıt bulunamadı' : 'Kaynağa erişilemiyor'}</dd></div>
          <div className={styles.dataRow}><dt>Kaynak dayanağı</dt><dd><FundTooltip align="end" title="Kaynak dayanağı" text="İncelemede kullanılan kaynak kayıtları burada listelenir. Aynı kaynağın birden fazla kaydı bulunabilir; kayıt sayısı güven puanı değildir.">{sourceCount} kaynak kaydı</FundTooltip></dd></div>
        </dl></div>
        <div className={styles.card} id="kap-reports"><h2>KAP raporları</h2>{documents.length ? <ul className={styles.sourceList}>{documents.slice(0, 3).map(item => <li key={item.document_key}><img src="/figma/funds/document.svg" alt=""/><div>{item.report_period ?? 'Dönemi belirtilmemiş'} portföy raporu<p className={styles.caption}>KAP · {dateTr(item.published_at)}</p></div>{item.source_url && <a href={item.source_url} target="_blank" rel="noreferrer">Aç</a>}</li>)}</ul> : <p className={styles.muted}>{documentResponse.ok ? 'Bu fon için alınmış KAP rapor kaydı bulunmuyor.' : 'KAP kaynak kayıtlarına şu anda erişilemiyor.'}</p>}{documents.length>0&&<p className={styles.caption}>Raporların tarihleri ve bağlantıları Kaynaklar bölümünde.</p>}</div>
      </aside>
    </div>

    <Link className={styles.textButton} href="/funds">Fon kataloğuna dön</Link>
  </section>;
}
