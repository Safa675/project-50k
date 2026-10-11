import Link from 'next/link';
import {redirect} from 'next/navigation';
import AssetLogo from '@/components/AssetLogo';
import {requireUser, serverApi} from '@/lib/auth';
import {FundSignal} from '@/lib/fund-display';
import FundEvidence from '@/components/FundEvidence';
import styles from '@/components/Funds.module.css';

type Fund = {fund_code: string; name: string; category: string | null};

function FundList({funds, offset = 0, full = false}: {funds: Fund[]; offset?: number; full?: boolean}) {
  return <ol className={`${styles.catalog} ${full ? styles.catalogFull : ''}`}>
    {funds.map((fund, index) => <li key={fund.fund_code}>
      <span className={styles.catalogNumber}>{offset + index + 1}</span><AssetLogo kind="fund" code={fund.fund_code} name={fund.name} decorative/>
      <span className={styles.catalogText}><Link href={`/funds/${fund.fund_code}`}>{fund.fund_code}</Link>
        <Link href={`/funds/${fund.fund_code}`} title={fund.name}>{fund.name}</Link><span className={styles.caption}>{fund.category ?? 'Kategori bilinmiyor'}</span></span>
    </li>)}
  </ol>;
}

export default async function Funds({searchParams}:{searchParams:Promise<{q?:string;offset?:string;category?:string;view?:string}>}){
  const params=await searchParams;
  const view=params.view==='developments'?'developments':'catalog';
  const q=(params.q??'').slice(0,80),category=(params.category??'').slice(0,200);
  const limit=view==='catalog'?50:25;
  const offset=Math.max(0,Math.min(view==='catalog'?10000:50000,Math.floor(Number(params.offset)||0)));
  const query=new URLSearchParams({q,limit:String(limit),offset:String(offset)});
  if(category)query.set('category',category);
  if(view==='developments')query.set('state','TRIGGERED');
  const [response,categoriesResponse]=await Promise.all([serverApi(`${view==='catalog'?'/funds':'/signals'}?${query}`),serverApi('/fund-categories'),requireUser()]);
  if(!response.ok)throw new Error(view==='catalog'?'Fon kataloğu şu anda yüklenemiyor.':'Gelişmeler şu anda yüklenemiyor.');
  const data=await response.json();
  if(!Array.isArray(data.items)||!Number.isInteger(data.total))throw new Error('Liste şu anda okunamıyor.');
  const categories:string[]=categoriesResponse.ok?(await categoriesResponse.json()).items:[];
  function href(nextView:string,nextOffset=0,nextCategory=category,nextQ=q){const search=new URLSearchParams({view:nextView});if(nextQ)search.set('q',nextQ);if(nextCategory)search.set('category',nextCategory);if(nextOffset)search.set('offset',String(nextOffset));return `/funds?${search}`;}
  if(offset>0&&offset>=data.total)redirect(href(view,data.total?Math.floor((data.total-1)/limit)*limit:0));
  const filtered=!!q||!!category;
  return <section className={styles.page} data-figma-node="27:508">
    <h1>Keşfet</h1>
    <nav className={styles.viewTabs} aria-label="Keşfet görünümleri"><Link href={href('catalog')} className={view==='catalog'?styles.viewActive:undefined} aria-current={view==='catalog'?'page':undefined}>Tüm fonlar</Link><Link href={href('developments')} className={view==='developments'?styles.viewActive:undefined} aria-current={view==='developments'?'page':undefined}>Gelişmeler</Link></nav>
    <form className={styles.search} action="/funds"><input type="hidden" name="view" value={view}/><label><span className={styles.srOnly}>Fon kodu veya adı</span><img src="/design/search-large.svg" alt=""/><input name="q" defaultValue={q} maxLength={80} placeholder="Fon adı ya da kodu ara"/></label>{category&&<input type="hidden" name="category" value={category}/>}<button type="submit">Ara</button></form>
    <div className={styles.catalogFilters}><form action="/funds"><input type="hidden" name="view" value={view}/>{q&&<input type="hidden" name="q" value={q}/>}<label>Fon türü<select name="category" defaultValue={category}><option value="">Tüm türler</option>{categories.map(item=><option key={item} value={item}>{item}</option>)}</select></label><button type="submit">Uygula</button></form>{filtered&&<Link href={href(view,0,'','')}>Filtreleri temizle</Link>}</div>
    <div id={view==='catalog'?'fund-catalog':'fund-developments'}><div className={styles.sectionTitle}><h2>{view==='catalog'?(filtered?'Arama sonuçları':'Fon kataloğu'):'İnceleme gerektiren gelişmeler'}</h2><span className={styles.muted} role="status">{data.total.toLocaleString('tr-TR')} {view==='catalog'?'fon':'gelişme'}</span></div>
      {view==='catalog'?<><p className={styles.caption}>Fon koduna göre alfabetik sıralama. Fon adını seçerek fiyatını ve incelemelerini açabilirsiniz.</p>{data.items.length?<FundList funds={data.items} offset={offset} full/>:<div className={styles.empty}><p>Bu arama ve fon türüyle eşleşen fon bulunamadı.</p>{filtered&&<Link href={href('catalog',0,'','')}>Tüm fonları göster</Link>}</div>}</>:<><p className={styles.caption}>Yalnızca inceleme işareti üreten kayıtlar gösterilir. Her kaydın tarihi yanında yer alır; aynı fon için birden fazla gelişme bulunabilir.</p>{data.items.length?<FundEvidence signals={data.items as FundSignal[]} showFund/>:<div className={styles.empty}><p>Bu görünümde kayıtlı bir gelişme bulunamadı.</p><p>Bu sonuç, tüm fonların incelendiği veya bilgi eksikliği olmadığı anlamına gelmez. Fon sayfasında hangi karşılaştırmaların tamamlandığını görebilirsiniz.</p><Link href={href('catalog',0)}>Fonları incele</Link></div>}</>}
      {data.total>0&&<nav className={styles.pagination} aria-label={view==='catalog'?'Fon sayfaları':'Gelişme sayfaları'}>{offset>0?<Link href={href(view,Math.max(0,offset-limit))}>Önceki</Link>:<span/>}<span>{Math.min(offset+1,data.total)}–{Math.min(offset+limit,data.total)} / {data.total.toLocaleString('tr-TR')}</span>{offset+limit<data.total?<Link href={href(view,offset+limit)}>Sonraki</Link>:<span/>}</nav>}
    </div>
  </section>;
}
