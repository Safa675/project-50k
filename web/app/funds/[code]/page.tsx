import Link from 'next/link';
import {notFound} from 'next/navigation';
import {requireUser, serverApi} from '@/lib/auth';
import {dateTr, decimal, reasonTr, stateTr} from '@/lib/client';
import {FundPoint, FundSignal, sourceTime} from '@/lib/fund-display';
import NavChart, {FundMarker} from '@/components/NavChart';
import FundTooltip from '@/components/FundTooltip';
import FundEvidence from '@/components/FundEvidence';
import FundSections from '@/components/FundSections';
import FundShare from '@/components/FundShare';
import FundDecision from '@/components/FundDecision';
import ChatPanel from '@/components/ChatPanel';
import WatchlistButton from '@/components/WatchlistButton';
import styles from '@/components/Funds.module.css';

type RegulatoryEvent = {event_id: string; effective_date: string | null; status: string; availability_unknown: boolean; source_url: string | null; source_sha256: string; available_at: string | null};
type Document = {document_key: string; report_period: string | null; published_at: string | null; available_at: string | null; source_sha256: string; source_url: string | null; has_local_document: boolean};

function EvidenceSources({signals, events, documents}: {signals: FundSignal[]; events: RegulatoryEvent[]; documents: Document[]}) {
  return <div>
    <div className={styles.sectionTitle}><h2>Detektör kanıtları</h2></div>
    <div className="table-scroll"><table><thead><tr><th>Gösterge</th><th>Durum</th><th>Değer</th><th>Eşik</th><th>Kanıt tarihi</th></tr></thead><tbody>{signals.map(signal => <tr key={signal.evidence_id}>
      <td>{signal.detector_id}{signal.is_attribute ? ' · Tarihçe özelliği' : ''}</td><td>{signal.is_attribute && signal.value !== null ? 'Gözlenen tarihçe' : stateTr[signal.state]}</td><td>{decimal(signal.value)}</td><td>{decimal(signal.threshold)}</td><td>{dateTr(signal.effective_date)}</td>
    </tr>)}</tbody></table></div>
    {signals.length === 0 && <p className={styles.empty}>Bu fon için tamamlanmış detektör kanıtı bulunmuyor.</p>}
    {signals.map(signal => <details key={signal.evidence_id}><summary>{signal.detector_id} · Kaynak ve sınırlamalar</summary><p>{reasonTr(signal.reason)}</p><p className="evidence-id">{signal.evidence_id}</p>{signal.source_references.length ? signal.source_references.map((ref, index) => <p key={index}>{ref.source_id} · {sourceTime(ref.available_at)}<br/><code>{ref.source_sha256}</code></p>) : <p>Bu gösterge için uygun zamanlı kaynak kanıtı bulunmuyor.</p>}</details>)}
    <div className={styles.sectionTitle}><h2>Düzenleyici kayıtlar</h2></div>
    {events.length ? events.map(event => <div className="event" key={event.event_id}><strong>{dateTr(event.effective_date)}</strong><p>{event.status === 'CONFIRMED' && !event.availability_unknown ? 'İnsan tarafından doğrulandı' : 'İnceleme bekliyor'}</p>{event.availability_unknown && <p>Kesin yayım zamanı bilinmiyor; tetikleyici olarak kullanılamaz.</p>}{event.source_url && <a href={event.source_url} rel="noreferrer" target="_blank">Resmî kaynak</a>}<details><summary>Kaynak izi</summary><p>{sourceTime(event.available_at)}</p><code>{event.source_sha256}</code></details></div>) : <p className={styles.empty}>İncelenen kaynak kümesinde bu fon için kayıt bulunamadı. Kaynak kapsamı SPK 2026/61 ile sınırlıdır.</p>}
    {documents.length > 0 && <div className={styles.sectionTitle}><h2>KAP kaynak izi</h2></div>}
    {documents.map(document => <details key={document.document_key}><summary>{document.report_period ?? 'Dönemi belirtilmemiş'} · Portföy raporu</summary><p>Yayım: {sourceTime(document.published_at)} · Erişim: {sourceTime(document.available_at)}</p><p>{document.has_local_document ? 'Yerel kaynak dosyası mevcut.' : 'Belge listesi kaydı; yerel kaynak dosyası yok.'}</p><code>{document.source_sha256}</code>{document.source_url && <p><a href={document.source_url} target="_blank" rel="noreferrer">KAP kaynağını aç</a></p>}</details>)}
  </div>;
}

export default async function Detail({params}: {params: Promise<{code: string}>}) {
  const {code} = await params;
  if (!/^[A-Z0-9]{2,12}$/.test(code)) notFound();
  const [response, documentResponse, user] = await Promise.all([serverApi(`/funds/${code}?days=731`), serverApi(`/funds/${code}/documents?limit=20`), requireUser()]);
  if (response.status === 404) notFound();
  if (!response.ok) throw new Error('Fon verilerine şu anda erişilemiyor.');
  const data = await response.json();
  if (!data.fund || !Array.isArray(data.signals) || !Array.isArray(data.chart?.points)) throw new Error('Fon yanıtı doğrulanamadı.');
  const documents: Document[] = documentResponse.ok ? (await documentResponse.json()).items : [];
  const points: FundPoint[] = data.chart.points;
  const signals: FundSignal[] = data.signals;
  const latest = points.at(-1);
  const document = documents[0];
  const findings = [...signals].filter(signal => !signal.is_attribute).sort((a, b) => Number(b.state === 'TRIGGERED') - Number(a.state === 'TRIGGERED'));
  const markers: FundMarker[] = documents.filter(item => item.published_at !== null).slice(0, 12).map(item => ({
    date: new Intl.DateTimeFormat('en-CA', {timeZone: 'Europe/Istanbul', year: 'numeric', month: '2-digit', day: '2-digit'}).format(new Date(item.published_at!)),
    label: `KAP · ${item.report_period ?? 'Portföy raporu'}`, href: item.source_url ?? '#kap-reports',
  }));
  const sourceCount = new Set(signals.flatMap(signal => signal.source_references.map(ref => ref.source_sha256))).size;
  const overview = <>
    <h2 className={styles.srOnly}>Yayımlanmış günlük birim fiyat</h2><NavChart points={points} markers={markers}/>
    <div className={styles.sectionTitle}><h2>Gelişmeler</h2><Link className={styles.textButton} href={user.role === 'viewer' ? '/method' : '/review'}>{user.role === 'viewer' ? 'Yöntemde oku' : 'İnceleme kuyruğu'}<img src="/design/arrow.svg" alt=""/></Link></div>
    <FundEvidence signals={findings.slice(0, 3)}/>
    <div className={styles.sectionTitle}><h2>Fon bilgileri</h2></div>
    <dl className={styles.facts}>
      <div><dt>Fon kodu</dt><dd>{code}</dd></div><div><dt>Fon türü</dt><dd>{data.fund.category ?? 'Kategori bilinmiyor'}</dd></div><div><dt>Para birimi</dt><dd>Kaynakta belirtilmemiş</dd></div>
      <div><dt><FundTooltip title="Tedavüldeki pay" text="Yatırımcıların elindeki toplam fon payı sayısı. Güncel bir sayı geçmişe taşınmaz; bu ekranda dönemsel pay sayısı serisi sunulmuyor.">Tedavüldeki pay</FundTooltip></dt><dd>Dönemsel seri yok</dd></div>
      <div><dt>Katalog tarihi</dt><dd>{dateTr(data.fund.listing_as_of)}</dd></div>
      <div><dt><FundTooltip title="Yatırımcı sayısı neden yok?" text="TEFAS güncel yatırımcı sayısını verir. İstenen geçmiş güne ait sayı bu veriden türetilemez; yalnızca o gün gerçekten kaydedilmiş bir gözlem kullanılabilir.">Yatırımcı sayısı</FundTooltip></dt><dd>Geçmiş seri yok</dd></div>
    </dl><div className={styles.reviewBlock}><FundDecision code={code}/></div>
  </>;
  return <section className={styles.page} data-figma-node="21:206">
    <div><FundTooltip pill title="Yayımlanmış arşiv verileri" text={`Bu görünüm ${sourceTime(data.cutoff)} erişim sınırına göre sorgulandı. Kaynakların gerçek tarihleri farklı olabilir. Bu görünüm tarihsel yeniden oynatma değildir; kategori bilgisi güncel katalogdan gelir.`}>
      <img src="/figma/funds/clock.svg" alt=""/>{user.data_mode === 'SYNTHETIC' ? 'SYNTHETIC · Sentetik test verileri' : 'DELAYED · Yayımlanmış veriler'}
    </FundTooltip></div>
    <header className={styles.identity}>
      <div className={styles.identityText}><span className={styles.avatar} aria-hidden="true">{code.slice(0, 2)}</span><div><div className={styles.identityMeta}><span className={styles.code}>{code}</span><span>{data.fund.category ?? 'Kategori bilinmiyor'}</span></div><h1>{data.fund.name}</h1></div></div>
      <div className={styles.actions}><FundShare/><Link className={styles.iconButton} href="/notifications" aria-label="Bildirimler"><img src="/design/bell.svg" alt=""/></Link><WatchlistButton code={code}/></div>
    </header>
    <div className={styles.priceSummary}><p className={styles.muted}><FundTooltip title="Fon pay fiyatı" text="Fonun yayımlanmış günlük birim pay değeri. Gün içi işlem fiyatı değildir. Kaynakta sıfır veya eksik gelen değerler kullanılmaz.">Günlük fon pay fiyatı</FundTooltip></p><div className={styles.priceLine}><span className={styles.priceValue}>{latest && !latest.ambiguous_revision && latest.nav !== null ? decimal(latest.nav) : 'Veri yok'}</span><span className={styles.muted}>{latest ? `${dateTr(latest.effective_date)} · TEFAS` : 'Bu dönemde yayımlanmış fiyat yok'}</span></div></div>
    <div className={styles.columns}>
      <div className={styles.mainColumn}><FundSections overview={overview} evidence={<><div className={styles.sectionTitle}><h2>Gelişmeler</h2></div><FundEvidence signals={findings}/></>} sources={<EvidenceSources signals={signals} events={data.events} documents={documents}/>}/></div>
      <aside className={styles.sidebar}>
        <div className={styles.card}><h2>Veri durumu</h2><dl>
          <div className={styles.dataRow}><dt>Fon pay fiyatı</dt><dd><FundTooltip align="end" title="Fiyatın kaynak tarihi" text={latest ? `TEFAS satır tarihi: ${dateTr(latest.effective_date)}. Erişim zamanı: ${sourceTime(latest.available_at)}. Yayım zamanı: ${sourceTime(latest.published_at)}. Fiyat gününe ait tam kaynak izi grafik tablosunda bulunur.` : 'Sorgulanan dönemde kullanılabilir fiyat kaydı yok.'}>{latest ? `TEFAS, ${dateTr(latest.effective_date)}` : 'Veri yok'}</FundTooltip></dd></div>
          <div className={styles.dataRow}><dt>Aylık portföy raporu</dt><dd>{document ? `KAP, ${dateTr(document.published_at)}` : documentResponse.ok ? 'Kayıt bulunamadı' : 'Kaynağa erişilemiyor'}</dd></div>
          <div className={styles.dataRow}><dt>Kaynak dayanağı</dt><dd><FundTooltip align="end" title="Kaynak dayanağı" text="Kanıtlar bu dosya özetlerine bağlıdır. Referans sayısı, bağımsız doğrulama sayısı veya güven puanı değildir.">{sourceCount} kaynak dosyası</FundTooltip></dd></div>
          <div className={styles.dataRow}><dt>Yatırımcı sayısı</dt><dd><FundTooltip align="end" title="Yatırımcı sayısı neden yok?" text="Güncel TEFAS yatırımcı sayısı geçmiş tarihlere uygulanamaz. Bu sayfada tarihsel yatırımcı sayısı serisi bulunmuyor."><img src="/figma/funds/info.svg" alt=""/>Geçmiş seri yok</FundTooltip></dd></div>
        </dl></div>
        <div className={styles.card} id="kap-reports"><h2>KAP raporları</h2>{documents.length ? <ul className={styles.sourceList}>{documents.slice(0, 3).map(item => <li key={item.document_key}><img src="/figma/funds/document.svg" alt=""/><div>{item.report_period ?? 'Dönemi belirtilmemiş'} portföy raporu<p className={styles.caption}>KAP · {dateTr(item.published_at)}</p></div>{item.source_url && <a href={item.source_url} target="_blank" rel="noreferrer">Aç</a>}</li>)}</ul> : <p className={styles.muted}>{documentResponse.ok ? 'Bu fon için alınmış KAP rapor kaydı bulunmuyor.' : 'KAP kaynak kayıtlarına şu anda erişilemiyor.'}</p>}<p className={styles.caption}>Belge zamanları ve dosya özetleri Kaynaklar bölümünde.</p></div>
        <ChatPanel key={code} code={code} drawer/>
      </aside>
    </div>
    <p className={styles.integrity}>Geliştirme sonucu; eşikler olaydan sonra belirlendi. Bir bulgu, usulsüzlük veya yatırım kararı anlamına gelmez. Kategori bilgisi güncel katalogdan gelir.</p>
    <Link className={styles.textButton} href="/funds">Fon kataloğuna dön</Link>
  </section>;
}
