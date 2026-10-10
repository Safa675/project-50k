import Link from 'next/link';
import {requireUser, serverApi} from '@/lib/auth';
import {dateTr} from '@/lib/client';
import styles from './workflow.module.css';

type Provenance = {run_id:string;version_id:string;protocol_version:string;protocol_sha256:string;code_sha256:string;input_sha256:string;as_of:string;cutoff:string;created_at:string;calibration_cutoff:string;origin:string};
type Model = {model_id:string;prompt_version:string;schema_version:string;ai_mode:string;latest_at:string};
type Overview = {
  observed_at:string;data_mode:string;fund_catalog_count:number;run:Provenance|null;
  evidence:{total:number;funds:number;triggered:number;not_triggered:number;abstained:number;attributes:number};
  decisions:{packets:number;valid_live:number;valid_synthetic:number;valid_deterministic:number;invalid:number;awaiting_proposal:number;reviewed:number;accepted:number;overridden:number;rejected:number;models:Model[]};
  latest_ingest:{run_id:string;status:string;started_at:string;finished_at:string|null;counts:Record<string,Record<string,number>>}|null;
  jobs:{ready:number;running:number;succeeded:number;failed:number};
  stocks:{state:string;catalog_members:number;symbols_with_prices:number;price_observations:number;catalog_captured_at:string|null};
};
const number = (value:number) => value.toLocaleString('tr-TR');
const time = (value:string) => new Intl.DateTimeFormat('tr-TR',{dateStyle:'medium',timeStyle:'short',timeZone:'Europe/Istanbul'}).format(new Date(value));
const ingestStatus:Record<string,string> = {RUNNING:'İçe aktarım sürüyor',SUCCEEDED:'İçe aktarım tamamlandı',FAILED:'İçe aktarım başarısız'};
const ingestTable:Record<string,string> = {'ref.funds':'Fon kataloğu','obs.fund_prices':'Günlük fon fiyatı','obs.fund_snapshots':'Fon anlık kaydı','obs.kap_documents':'KAP belgesi','obs.kap_series':'KAP rapor serisi','obs.regulatory_events':'Düzenleyici olay','ref.stock_instruments':'Hisse kataloğu','obs.stock_prices':'Günlük hisse fiyatı',stocks:'Hisse verileri'};
const countLabel:Record<string,string> = {input:'Okunan',inserted:'Eklenen',missing:'Eksik',non_null:'Mevcut',instruments:'Hisseler',prices:'Fiyat kayıtları',actions:'Kurumsal olaylar',inserted_prices:'Eklenen fiyatlar',missing_prices:'Eksik fiyatlar',inserted_actions:'Eklenen olaylar'};

export default async function Workflow() {
  const [user,response] = await Promise.all([requireUser(),serverApi('/workflow')]);
  if (!response.ok) throw new Error('İş akışı bilgisi alınamadı.');
  const data = await response.json() as Overview;
  if (!data.evidence || !data.decisions || !data.jobs || !data.stocks || !Number.isInteger(data.fund_catalog_count)) throw new Error('İş akışı yanıtı doğrulanamadı.');
  const valid = data.decisions.valid_live + data.decisions.valid_synthetic + data.decisions.valid_deterministic;
  return <section>
    <p className="eyebrow">KURUMSAL KANIT VE API</p>
    <h1>Kanıttan incelemeye</h1>
    <p>Bankalar ve finansal kurumlar için kaynakları izlenebilir fon ve hisse verisi. Sayısal kanıt detektörlerden gelir; yapay zekâ önerisi insan incelemesiyle birlikte saklanır.</p>
    <p className="muted">Gözlem: {time(data.observed_at)} · {data.data_mode} · Geliştirme sonucu</p>
    <ol className={styles.stages} aria-label="Kanıt iş akışı">
      <li><span className="eyebrow">01 · HESAPLAMA</span><h2>Deterministik kanıt</h2><strong className={styles.number}>{number(data.evidence.total)}</strong><p>{number(data.evidence.funds)} fon için mevcut çalışma kayıtları. Eşikler model tarafından değiştirilmez.</p><Link href="/funds">Fon kanıtlarını aç</Link></li>
      <li><span className="eyebrow">02 · ÖNERİ</span><h2>Yapay zekâ değerlendirmesi</h2><strong className={styles.number}>{number(valid)}</strong><p>Doğrulayıcıdan geçen öneri. {number(data.decisions.invalid)} geçersiz çıktı; {number(data.decisions.awaiting_proposal)} kanıt paketi değerlendirme bekliyor.</p><p className="muted">Canlı model: {number(data.decisions.valid_live)} · Deterministik yetersiz kanıt: {number(data.decisions.valid_deterministic)}{data.decisions.valid_synthetic>0&&` · Sentetik: ${number(data.decisions.valid_synthetic)}`}</p></li>
      <li><span className="eyebrow">03 · İNSAN</span><h2>İnceleme kaydı</h2><strong className={styles.number}>{number(data.decisions.reviewed)}</strong><p>{number(data.decisions.accepted)} kabul · {number(data.decisions.overridden)} gerekçeli değişiklik · {number(data.decisions.rejected)} ret. İlk öneri korunur.</p>{user.role!=='viewer'&&<Link href="/review">İnceleme kuyruğunu aç</Link>}</li>
      <li><span className="eyebrow">04 · API</span><h2>Kimliği doğrulanmış erişim</h2><p>Fon kataloğu, günlük veriler, kanıtlar ve olaylar oturumla okunur. API sözleşmesi OpenAPI üzerinden incelenebilir.</p><a href="http://127.0.0.1:8770/docs" target="_blank" rel="noreferrer">API belgelerini aç</a></li>
    </ol>
    <p className="notice">Bu görünüm tek model önerisi ve insan incelemesini gösterir. Kanıtlar geliştirme sonuçlarıdır; tarihsel olay hakkında doğrulanmış tahmin veya yatırım tavsiyesi değildir. Veriler localhost üzerinde kullanılır; yeniden dağıtım hakları incelenmedi.</p>
    <article><h2>Güncel fon kanıtı</h2>
      <p>{number(data.fund_catalog_count)} fon katalogda. Aşağıdaki sayılar yalnızca son tamamlanan çalışmaya aittir; nitelik kayıtları eşik bulgusu sayılmaz.</p>
      <dl className={styles.metrics}><div><dt>Eşik aşımı</dt><dd>{number(data.evidence.triggered)}</dd></div><div><dt>Eşik aşılmadı</dt><dd>{number(data.evidence.not_triggered)}</dd></div><div><dt>Yeterli kanıt yok</dt><dd>{number(data.evidence.abstained)}</dd></div><div><dt>Nitelik kayıtları</dt><dd>{number(data.evidence.attributes)}</dd></div></dl>
      {data.run?<details><summary>Çalışma ve protokol kaydı</summary><dl className={styles.metadata}><dt>Çalışma</dt><dd><code>{data.run.run_id}</code></dd><dt>Son veri tarihi</dt><dd>{dateTr(data.run.as_of)}</dd><dt>Bilgi kesim zamanı</dt><dd>{time(data.run.cutoff)}</dd><dt>Protokol</dt><dd>{data.run.protocol_version}</dd><dt>Kalibrasyon sürümü</dt><dd><code>{data.run.version_id}</code></dd><dt>Kalibrasyon kesimi</dt><dd>{time(data.run.calibration_cutoff)}</dd><dt>Protokol SHA-256</dt><dd><code>{data.run.protocol_sha256}</code></dd><dt>Kod SHA-256</dt><dd><code>{data.run.code_sha256}</code></dd><dt>Girdi SHA-256</dt><dd><code>{data.run.input_sha256}</code></dd></dl></details>:<p>Tamamlanmış, kullanılabilir fon detektör çalışması bulunmuyor.</p>}
      <p className="muted">Öneri ve insan incelemesi sayıları bu çalışma ile eşleşen güncel kanıt paketlerine aittir. Önceki çalışma kararları bu toplamlara katılmaz.</p>
    </article>
    <article><h2>Model ve istem kaydı</h2>{data.decisions.models.length?<div className="table-scroll"><table><caption className="muted">Güncel çalışmaya bağlı önerilerin model sürümleri</caption><thead><tr><th>Model</th><th>İstem</th><th>Şema</th><th>Kip</th><th>Son kayıt</th></tr></thead><tbody>{data.decisions.models.map(model=><tr key={`${model.model_id}:${model.prompt_version}:${model.schema_version}:${model.ai_mode}`}><td>{model.model_id}</td><td>{model.prompt_version}</td><td>{model.schema_version}</td><td>{model.ai_mode}</td><td>{time(model.latest_at)}</td></tr>)}</tbody></table></div>:<p>Güncel çalışmaya bağlı model önerisi bulunmuyor.</p>}</article>
    <article><div className={styles.row}><h2>BIST 30 veri kapsamı</h2><Link href="/stocks">Hisseleri aç</Link></div>
      {data.stocks.state==='DAILY_PRICES_AVAILABLE'?<p>{number(data.stocks.catalog_members)} güncel katalog üyesi; {number(data.stocks.symbols_with_prices)} hissede {number(data.stocks.price_observations)} günlük fiyat kaydı.</p>:data.stocks.state==='CATALOG_ONLY'?<p>{number(data.stocks.catalog_members)} güncel katalog üyesi mevcut; kullanılabilir günlük fiyat kaydı bulunmuyor.</p>:<p>İçe aktarılmış güncel hisse kataloğu bulunmuyor.</p>}
      {data.stocks.catalog_captured_at&&<p className="muted">Katalog alım zamanı: {time(data.stocks.catalog_captured_at)}. Güncel üyelik, geçmiş endeks üyeliği olarak kullanılamaz.</p>}
    </article>
    <article><h2>Veri alımı ve değerlendirme işleri</h2>
      {data.latest_ingest?<><p>{ingestStatus[data.latest_ingest.status]} · Başlangıç {time(data.latest_ingest.started_at)}{data.latest_ingest.finished_at&&` · Bitiş ${time(data.latest_ingest.finished_at)}`}</p><p className="muted">Alım kaydı: <code>{data.latest_ingest.run_id}</code></p>{Object.entries(data.latest_ingest.counts).map(([table,counts])=><p key={table}><strong>{ingestTable[table]??table}</strong>: {Object.entries(counts).map(([key,value])=>`${countLabel[key]??key} ${number(value)}`).join(' · ')}</p>)}</>:<p>Veritabanında alım çalışması kaydı bulunmuyor.</p>}
      <dl className={styles.metrics}><div><dt>Bekleyen değerlendirme</dt><dd>{number(data.jobs.ready)}</dd></div><div><dt>Çalışan</dt><dd>{number(data.jobs.running)}</dd></div><div><dt>Tamamlanan</dt><dd>{number(data.jobs.succeeded)}</dd></div><div><dt>Başarısız</dt><dd>{number(data.jobs.failed)}</dd></div></dl><p className="muted">İş sayıları kaydedilmiş tüm değerlendirme işlerini kapsar; yalnızca güncel çalışma ile sınırlı değildir.</p>
    </article>
  </section>;
}
