import Link from 'next/link';
import {serverApi} from '@/lib/auth';
import AssetLogo from './AssetLogo';
import styles from './KapExperiment.module.css';

type Counts={cohort:number;assessed:number;abstained:number;flagged:number;listed_total:number;caught:number;baseline_caught:number;added_to_price:number;union_price_caught:number;outside_list:number};
type Case={fund_code:string;name:string;state:'FLAGGED'|'NOT_FLAGGED'|'ABSTAINED';added_to_price:boolean};
export type KapExperimentReport={counts:Counts;cases:Case[];development_result:true;baseline_unchanged:true;cutoff:string};
const countKeys=['cohort','assessed','abstained','flagged','listed_total','caught','baseline_caught','added_to_price','union_price_caught','outside_list'] as const;
const number=(value:number)=>new Intl.NumberFormat('tr-TR').format(value);
const stateLabels={FLAGGED:'İşaretlendi',NOT_FLAGGED:'Sınır aşılmadı',ABSTAINED:'Yeterli rapor yok'};

function record(value:unknown):value is Record<string,unknown>{return typeof value==='object'&&value!==null&&!Array.isArray(value);}

/** Only complete, consistent server counts are shown; unavailable values are never replaced. */
export function parseKapExperimentReport(value:unknown):KapExperimentReport|null{
  if(!record(value)||value.development_result!==true||value.baseline_unchanged!==true||
    typeof value.cutoff!=='string'||!/^\d{4}-\d{2}-\d{2}T/.test(value.cutoff)||!Number.isFinite(Date.parse(value.cutoff))||
    !record(value.counts)||!Array.isArray(value.cases)||value.cases.length>8)return null;
  const counts=value.counts;
  if(!countKeys.every(key=>typeof counts[key]==='number'&&Number.isSafeInteger(counts[key])&&(counts[key] as number)>=0))return null;
  const c=counts as Counts;
  if(c.cohort===0||c.listed_total===0||c.assessed+c.abstained!==c.cohort||c.flagged>c.assessed||
    c.caught>c.flagged||c.caught>c.listed_total||c.outside_list!==c.flagged-c.caught||
    c.union_price_caught<c.baseline_caught||c.union_price_caught>c.listed_total||
    c.added_to_price!==c.union_price_caught-c.baseline_caught||c.added_to_price>c.caught)return null;
  const cases:Case[]=[];
  for(const item of value.cases){
    if(!record(item)||typeof item.fund_code!=='string'||!/^[A-Z0-9]{2,12}$/.test(item.fund_code)||
      typeof item.name!=='string'||!item.name.trim()||item.name.length>500||
      !['FLAGGED','NOT_FLAGGED','ABSTAINED'].includes(String(item.state))||typeof item.added_to_price!=='boolean'||
      (item.added_to_price&&item.state!=='FLAGGED')||cases.some(row=>row.fund_code===item.fund_code))return null;
    cases.push({fund_code:item.fund_code,name:item.name,state:item.state as Case['state'],added_to_price:item.added_to_price});
  }
  return{counts:c,cases,development_result:true,baseline_unchanged:true,cutoff:value.cutoff};
}

export function KapExperimentPanel({report}:{report:KapExperimentReport}){
  const c=report.counts;
  const cutoff=new Intl.DateTimeFormat('tr-TR',{dateStyle:'long',timeStyle:'short',timeZone:'Europe/Istanbul'}).format(new Date(report.cutoff));
  return <section className={styles.experiment} aria-labelledby="kap-experiment-title">
    <header className={styles.heading}><span className={styles.caption}>Aylık rapor karşılaştırması · Geliştirme deneyi</span><h2 id="kap-experiment-title">Aylık raporlar fiyat taramasına ne ekliyor?</h2><p>Bu ayrı deney, kayıtlı fiyat sonuçlarını değiştirmeden KAP raporlarındaki toplam değer ve pay sayısı değişimini karşılaştırır.</p></header>
    <div className={styles.rule}><strong>Önceden sabitlenen kural</strong><p>Karşılaştırılan son iki rapor ardışık aylara ait olmalıdır. Raporlanan toplam değer ve pay sayısı birlikte en az iki katına çıkmışsa veya ikisi de önceki ayın yarısına ya da altına inmişse fon işaretlenir. İki ayda da pozitif değer gerekir; eksik ya da çelişen kayıtla sonuç üretilmez.</p><p>Yalnızca <strong>{cutoff} (İstanbul)</strong> anına kadar yayımlanmış ve kullanılabilir olmuş raporlar alınır. Sonraki raporlar geçmişteki eksikleri tamamlamaz.</p></div>
    <div className={styles.metrics}>
      <article className={styles.metric}><span>Değerlendirilen fon</span><strong>{number(c.assessed)} <small>/ {number(c.cohort)}</small></strong><p>{number(c.abstained)} fon yeterli iki aylık rapor olmadığı için değerlendirilemedi.</p></article>
      <article className={styles.metric}><span>Aylık kuralın işaretlediği</span><strong>{number(c.flagged)}</strong><p>{number(c.caught)} fon sonradan SPK listesinde yer aldı; {number(c.outside_list)} fon bu listede yer almadı.</p></article>
      <article className={styles.metric}><span>Fiyat taramasına eklenen</span><strong>{number(c.added_to_price)}</strong><p>Sonradan SPK listesinde yer alan, fiyat taramasında işaretlenmeyip bu aylık kuralda işaretlenen fonlar.</p></article>
      <article className={styles.metric}><span>Fiyat ve aylık kural birlikte</span><strong>{number(c.union_price_caught)} <small>/ {number(c.listed_total)}</small></strong><p>Sonradan yayımlanan SPK listesindeki fonlarla olaydan sonra yapılan karşılaştırma.</p></article>
    </div>
    <p className={styles.comparison}>Sabit fiyat taramasında listedeki {number(c.listed_total)} fondan {number(c.baseline_caught)} tanesi işaretlenmişti. Yeni kural eklenince karşılaştırmadaki sayı {number(c.union_price_caught)} oluyor; yukarıdaki kayıtlı fiyat sonuçları aynı kalır.</p>
    {report.cases.length>0&&<div className={styles.cases}><h3>Vaka fonlarında aylık kural</h3><ul>{report.cases.map(item=><li key={item.fund_code}><Link href={`/funds/${item.fund_code}`} title={item.name}><AssetLogo kind="fund" code={item.fund_code} name={item.name} size={36} decorative/><span className={styles.fund}><strong>{item.fund_code}</strong><span>{item.name}</span><small className={item.state==='FLAGGED'?styles.flagged:undefined}>{stateLabels[item.state]}{item.added_to_price?' · Fiyat taramasına eklenen':''}</small></span><span className={styles.arrow} aria-hidden="true">↗</span></Link></li>)}</ul></div>}
    <div className={styles.limits}><p><strong>İki ölçü bağımsız kanıt değildir.</strong> Toplam değer ve pay sayısı birbiriyle ilişkilidir. Fon giriş ve çıkışları, yapı veya pay birimi değişiklikleri ve kaynak hataları bu farkı açıklayabilir.</p><p>Bilinen olaylar bu kuralın geliştirilmesini etkiledi; ayrı bir doğrulama grubu yoktur. Bunlar doğrulanmış başarı, tahmin veya erken uyarı sonuçları değildir. Listede olmayan bir işaret yanlışlık kanıtı değildir; işaretlenmemek de güvence değildir. Sonradan yayımlanan SPK listesi yalnızca karşılaştırmada kullanılır, bu kuralın girdisi değildir.</p><Link href="/method#sources">Kaynakları ve tarih kurallarını inceleyin →</Link></div>
  </section>;
}

/** Optional server-rendered result: an unfinished or unavailable experiment adds no template content. */
export default async function KapExperiment(){
  try{
    const response=await serverApi('/evaluation/kap-scale-experiment');
    if(!response.ok)return null;
    const report=parseKapExperimentReport(await response.json());
    return report?<KapExperimentPanel report={report}/>:null;
  }catch{return null;}
}
