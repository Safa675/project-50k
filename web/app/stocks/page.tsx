import Link from 'next/link';
import AssetLogo from '@/components/AssetLogo';
import {serverApi} from '@/lib/auth';
import {dateTr, decimal} from '@/lib/client';
import {stockAvailableTime, stockSourceLabel} from '@/lib/stock-chart';

type Stock = {symbol: string; name: string; exchange: string; currency: string; last_date: string|null; last_close: string|null;
  source_id: string|null; change_pct: string|null; volume: string|null};
export default async function Stocks({searchParams}: {searchParams: Promise<{q?: string; offset?: string}>}) {
  const params = await searchParams;
  const q = (params.q ?? '').slice(0, 80), offset = Math.max(0, Math.min(30, Math.floor(Number(params.offset) || 0)));
  const response = await serverApi(`/stocks?q=${encodeURIComponent(q)}&limit=30&offset=${offset}`);
  if (!response.ok) throw new Error('Hisse kataloğu şu anda yüklenemiyor.');
  const data = await response.json();
  if (!Array.isArray(data.items) || !Number.isInteger(data.total) || !['BIST30_CURRENT_CATALOG','BIST30_DATED_BULLETIN'].includes(data.universe)) {
    throw new Error('Hisse yanıtı doğrulanamadı.');
  }
  const dated = data.universe === 'BIST30_DATED_BULLETIN';
  return <section><p className="eyebrow">BIST 30</p><h1>Türkiye hisseleri</h1>
    {dated ? data.membership_date ? <>
      <p>Bu sayfadaki BIST 30 üyeliği, {dateTr(data.membership_date)} tarihli Borsa İstanbul günlük bültenine aittir.</p>
      <p className="muted">Bültenin kaynakta erişilebilir olduğu zaman: <time dateTime={data.membership_available_at}>{stockAvailableTime(data.membership_available_at)}</time>. Yalnızca inceleme tarihine kadar erişilebilir olan kayıtlar gösterilir.</p>
    </> : <p className="notice">Seçilen inceleme tarihine kadar erişilebilir bir BIST 30 bülteni bulunmuyor. Daha sonra alınan fiyatlar ve güncel üyelik geçmişe taşınmaz.</p>
      : <p>Katalog güncel BIST 30 üyeliğini gösterir. Bu üyelik geçmiş tarihli endeks kapsamı olarak kullanılamaz.</p>}
    <p className="muted">Yayımlanmış günlük kapanış fiyatları · Türk lirası.</p>{data.items.length>0&&data.items.every((stock:Stock)=>stock.last_close===null)&&<p className="notice">Seçilen inceleme tarihinde kullanılabilir bir hisse fiyat kaydı bulunmuyor. Daha sonra alınan fiyatlar geçmişte biliniyormuş gibi gösterilmez. İnceleme tarihinden güncel görünüme geçebilirsiniz.</p>}
    <form className="toolbar" action="/stocks"><label>Hisse kodu veya adı<input name="q" defaultValue={q} maxLength={80}/></label><button>Ara</button></form>
    <p role="status">{data.total.toLocaleString('tr-TR')} hisse</p>
    {data.items.length ? <div className="table-scroll"><table><thead><tr><th>Hisse</th><th>Adı</th><th>Son kapanış · TL</th><th>Veri tarihi</th>{dated&&<><th>Önceki kapanışa göre · %</th><th>İşlem hacmi · adet</th></>}<th>Fiyat kaynağı</th></tr></thead>
      <tbody>{data.items.map((stock: Stock) => <tr key={stock.symbol}>
        <td><Link className="stock-symbol" href={`/stocks/${encodeURIComponent(stock.symbol)}`}><AssetLogo kind="stock" code={stock.symbol} name={stock.name} decorative/>{stock.symbol}</Link></td>
        <td><Link href={`/stocks/${encodeURIComponent(stock.symbol)}`}>{stock.name}</Link></td>
        <td>{decimal(stock.last_close)}</td><td>{dateTr(stock.last_date)}</td>
        {dated&&<><td>{decimal(stock.change_pct)}</td><td>{decimal(stock.volume)}</td></>}
        <td>{stockSourceLabel(stock.source_id)}</td>
      </tr>)}</tbody></table></div> : <p>{q ? 'Aramanızla eşleşen hisse bulunamadı.' : 'Kaynaklı BIST 30 hisse kaydı bulunmuyor.'}</p>}
    <nav className="pagination" aria-label="Hisse sayfaları">
      {offset > 0 && <Link href={`/stocks?q=${encodeURIComponent(q)}&offset=${Math.max(0, offset - 30)}`}>Önceki</Link>}
      {offset + 30 < data.total && <Link href={`/stocks?q=${encodeURIComponent(q)}&offset=${offset + 30}`}>Sonraki</Link>}
    </nav>
  </section>;
}
