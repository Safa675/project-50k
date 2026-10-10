import Link from 'next/link';
import AssetLogo from '@/components/AssetLogo';
import {requireUser, serverApi} from '@/lib/auth';
import {FundSignal} from '@/lib/fund-display';
import FundEvidence from '@/components/FundEvidence';
import FundTooltip from '@/components/FundTooltip';
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

export default async function Funds({searchParams}: {searchParams: Promise<{q?: string; offset?: string; category?: string; view?: string}>}) {
  const params = await searchParams;
  const q = (params.q ?? '').slice(0, 80), category = (params.category ?? '').slice(0, 200);
  const offset = Math.max(0, Math.min(10000, Math.floor(Number(params.offset) || 0)));
  const featured = !q && !category && offset === 0 && params.view !== 'catalog';
  const query = new URLSearchParams({q, limit: '50', offset: String(offset)});
  if (category) query.set('category', category);
  const [response, categoriesResponse, signalsResponse, user] = await Promise.all([
    serverApi(`/funds?${query}`), serverApi('/fund-categories'),
    featured ? serverApi('/signals?state=TRIGGERED&limit=3') : Promise.resolve(null), requireUser(),
  ]);
  if (!response.ok) throw new Error('Fon kataloğu şu anda yüklenemiyor.');
  const data = await response.json();
  if (!Array.isArray(data.items) || !Number.isInteger(data.total)) throw new Error('Fon yanıtı doğrulanamadı.');
  const categories: string[] = categoriesResponse.ok ? (await categoriesResponse.json()).items : [];
  const signals: FundSignal[] = signalsResponse?.ok ? (await signalsResponse.json()).items : [];
  function href(nextOffset: number, nextCategory = category) {
    const search = new URLSearchParams({q, offset: String(nextOffset)});
    if (nextCategory) search.set('category', nextCategory);
    if (params.view === 'catalog' || nextOffset > 0) search.set('view', 'catalog');
    return `/funds?${search}`;
  }
  return <section className={styles.page} data-figma-node="27:508">
    <div><FundTooltip pill title="Yayımlanmış arşiv verileri" text="Katalog güncel fon kimliklerini gösterir. Fiyatlar ve kanıtlar kendi kaynak tarihlerine göre sunulur. Kategori ve üyelik bilgisi geçmiş üyeliği göstermez.">
      <img src="/figma/funds/info.svg" alt=""/>{user.data_mode === 'SYNTHETIC' ? 'Örnek test verileri' : 'Yayımlanmış veriler'}
    </FundTooltip></div>
    <h1>Keşfet</h1>
    <form className={styles.search} action="/funds"><label><span className={styles.srOnly}>Fon kodu veya adı</span><img src="/design/search-large.svg" alt=""/><input name="q" defaultValue={q} maxLength={80} placeholder="Fon adı ya da kodu ara"/></label>{category && <input type="hidden" name="category" value={category}/>}<button type="submit">Ara</button></form>
    <nav className={styles.segments} aria-label="Fon kategorileri"><Link className={!category ? styles.selected : ''} href={href(0, '')}>Tüm fonlar</Link>
      {categories.slice(0, 5).map(item => <Link className={category === item ? styles.selected : ''} key={item} href={href(0, item)}>{item}</Link>)}
      {categories.length > 5 && <Link href="/funds?view=catalog#fund-catalog">Tüm kategoriler</Link>}
    </nav>
    {featured && <div className={styles.columns}>
      <div><div className={styles.sectionTitle}><h2>Gelişmeler</h2><Link className={styles.textButton} href={user.role === 'viewer' ? '/method' : '/review'}>{user.role === 'viewer' ? 'Yöntemde oku' : 'İnceleme kuyruğu'}<img src="/design/arrow.svg" alt=""/></Link></div>
        <p className={styles.caption}>Son tamamlanan incelemeler. Fon koduna göre sıralıdır.</p><FundEvidence signals={signals} showFund/>
      </div>
      <aside><div className={styles.sectionTitle}><h2>Fon kataloğu</h2></div><p className={styles.caption}>Fon koduna göre alfabetik sıralama · {data.total.toLocaleString('tr-TR')} fon</p><FundList funds={data.items.slice(0, 5)}/><Link className={styles.textButton} href="/funds?view=catalog">Daha fazla göster<img src="/design/arrow.svg" alt=""/></Link></aside>
    </div>}
    {!featured && <div id="fund-catalog"><div className={styles.sectionTitle}><h2>{q ? 'Arama sonuçları' : category || 'Türkiye yatırım fonları'}</h2><span className={styles.muted} role="status">{data.total.toLocaleString('tr-TR')} fon</span></div>
      {categories.length > 5 && <form action="/funds" className="toolbar"><input type="hidden" name="q" value={q}/><label>Kategori<select name="category" defaultValue={category}><option value="">Tüm fonlar</option>{categories.map(item => <option key={item} value={item}>{item}</option>)}</select></label><button type="submit">Filtrele</button></form>}
      {data.items.length ? <FundList funds={data.items} offset={offset} full/> : <p className={styles.empty}>Aramanızla eşleşen fon bulunamadı.</p>}
      <nav className={styles.pagination} aria-label="Sayfalar">{offset > 0 && <Link href={href(Math.max(0, offset - 50))}>Önceki</Link>}{offset + 50 < data.total && <Link href={href(offset + 50)}>Sonraki</Link>}</nav>
    </div>}

  </section>;
}
