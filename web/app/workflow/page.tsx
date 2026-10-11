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

type TeamCounts = {open_cases:number;queued:number;running:number;done_today:number};
async function teamCounts():Promise<TeamCounts|null>{
  try{const response=await serverApi('/agents/team');if(!response.ok)return null;const counts=(await response.json())?.counts;
    return counts&&['open_cases','queued','done_today'].every(key=>Number.isInteger(counts[key]))?counts as TeamCounts:null;}
  catch{return null;}
}

export default async function Workflow(){
  const [user,response,team]=await Promise.all([requireUser(),serverApi('/workflow'),teamCounts()]);
  if(!response.ok)throw new Error('İş akışı bilgisi alınamadı.');
  const data=await response.json() as Overview;
  if(!data.evidence||!data.decisions||!data.jobs||!data.stocks||!Number.isInteger(data.fund_catalog_count))throw new Error('İş akışı bilgisi okunamadı.');
  const valid=data.decisions.valid_live+data.decisions.valid_synthetic+data.decisions.valid_deterministic;
  return <section><p className="eyebrow">KURUMSAL ÇALIŞMA ALANI</p><h1>Bilgiden incelemeye</h1>
    <p>Bankalar ve finansal kurumlar için fon ve hisse verilerini kaynaklarıyla bir araya getirir. Yapay zekâ değerlendirmeleri insan incelemesiyle tamamlanır.</p><p className="muted">Son kontrol: {time(data.observed_at)}</p>
    <ol className={styles.stages} aria-label="Kanıt iş akışı">
      <li><span className="eyebrow">01 · VERİ</span><h2>Fonlar incelenir</h2><strong className={styles.number}>{number(data.evidence.funds)}</strong><p>Fonun fiyat hareketleri ve kaynak kayıtları incelendi.</p><Link href="/funds">Gelişmeleri aç</Link></li>
      <li><span className="eyebrow">02 · DEĞERLENDİRME</span><h2>Bilgi yorumlanır</h2><strong className={styles.number}>{number(valid)}</strong><p>Kayıtlı değerlendirme. {number(data.decisions.awaiting_proposal)} inceleme değerlendirme bekliyor.</p></li>
      <li><span className="eyebrow">03 · İNSAN</span><h2>İnsan incelemesi</h2><strong className={styles.number}>{number(data.decisions.reviewed)}</strong><p>{number(data.decisions.accepted)} kabul · {number(data.decisions.overridden)} gerekçeli değişiklik · {number(data.decisions.rejected)} ret. İlk değerlendirme korunur.</p>{user.role!=='viewer'&&<Link href="/review">İnceleme kuyruğunu aç</Link>}</li>
      <li><span className="eyebrow">04 · ERİŞİM</span><h2>Kurumunuzla bağlantı</h2><p>Fonlar, fiyatlar ve gelişmeler API üzerinden de okunabilir. Erişim için oturum açılması gerekir.</p><a href="http://127.0.0.1:8770/docs" target="_blank" rel="noreferrer">API belgelerini aç</a></li>
    </ol>
    <article><h2>Fonlarda son durum</h2><p>Katalogda {number(data.fund_catalog_count)} fon bulunuyor. Son incelemelerde:</p><dl className={styles.metrics}><div><dt>İnceleme gereken değişim</dt><dd>{number(data.evidence.triggered)}</dd></div><div><dt>İnceleme sınırı aşılmadı</dt><dd>{number(data.evidence.not_triggered)}</dd></div><div><dt>Bilgi yetersiz</dt><dd>{number(data.evidence.abstained)}</dd></div></dl>{data.run?<p className="muted">İncelenen son veri tarihi: {dateTr(data.run.as_of)} · İnceleme zamanı: {time(data.run.created_at)}</p>:<p>Henüz tamamlanmış bir fon incelemesi yok.</p>}<p className="muted">Sayılar ayrı inceleme sonuçlarını gösterir; aynı fon birden fazla incelemede yer alabilir.</p></article>
    <article><div className={styles.row}><h2>BIST 30 hisseleri</h2><Link href="/stocks">Hisseleri aç</Link></div>{data.stocks.state==='DAILY_PRICES_AVAILABLE'?<p>{number(data.stocks.symbols_with_prices)} hisse için {number(data.stocks.price_observations)} günlük fiyat kaydı mevcut.</p>:<p>Seçili tarih için kullanılabilir hisse fiyatı yok.</p>}{data.stocks.catalog_captured_at&&<p className="muted">Katalog tarihi: {time(data.stocks.catalog_captured_at)}. Hisselerin günlük fiyatları ve kaynakları incelenebilir.</p>}</article>
    <article><div className={styles.row}><h2>İncelemelerin ilerleyişi</h2>{team&&<Link href="/ekip">Ajan ekibini aç</Link>}</div>{team?<dl className={styles.metrics}><div><dt>Açık vaka</dt><dd>{number(team.open_cases)}</dd></div><div><dt>Sıradaki ajan görevi</dt><dd>{number(team.queued)}</dd></div><div><dt>Bugün tamamlanan görev</dt><dd>{number(team.done_today)}</dd></div></dl>:<dl className={styles.metrics}><div><dt>Sırada</dt><dd>{number(data.jobs.ready)}</dd></div><div><dt>İnceleniyor</dt><dd>{number(data.jobs.running)}</dd></div><div><dt>Tamamlandı</dt><dd>{number(data.jobs.succeeded)}</dd></div>{data.jobs.failed>0&&<div><dt>Tamamlanamadı</dt><dd>{number(data.jobs.failed)}</dd></div>}</dl>}{data.latest_ingest&&<p className="muted">{ingestStatus[data.latest_ingest.status]??'Veri alımı kontrol ediliyor'}{data.latest_ingest.finished_at&&` · ${time(data.latest_ingest.finished_at)}`}</p>}</article>
  </section>;
}
