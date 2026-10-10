import Link from 'next/link';
import {serverApi} from '@/lib/auth';
import {dateTr, decimal} from '@/lib/client';

type Stock = {symbol: string; name: string; exchange: string; currency: string; last_date: string|null; last_close: string|null};
export default async function Stocks({searchParams}: {searchParams: Promise<{q?: string; offset?: string}>}) {
  const params = await searchParams;
  const q = (params.q ?? '').slice(0, 80), offset = Math.max(0, Math.min(30, Math.floor(Number(params.offset) || 0)));
  const response = await serverApi(`/stocks?q=${encodeURIComponent(q)}&limit=30&offset=${offset}`);
  if (!response.ok) throw new Error('Hisse kataloğu şu anda yüklenemiyor.');
  const data = await response.json();
  if (!Array.isArray(data.items) || !Number.isInteger(data.total) || data.universe !== 'BIST30_CURRENT_CATALOG') {
    throw new Error('Hisse yanıtı doğrulanamadı.');
  }
  return <section><p className="eyebrow">BIST 30 · {data.data_mode}</p><h1>Türkiye hisseleri</h1>
    <p>Katalog güncel BIST 30 üyeliğini gösterir. Bu üyelik geçmiş tarihli endeks kapsamı olarak kullanılamaz.</p>
    <p className="notice">Yayımlanmış günlük kapanış verileri · TRY. Veri hakları incelenmedi; yalnızca yerel inceleme.</p>
    <form className="toolbar" action="/stocks"><label>Hisse kodu veya adı<input name="q" defaultValue={q} maxLength={80}/></label><button>Ara</button></form>
    <p role="status">{data.total.toLocaleString('tr-TR')} hisse</p>
    {data.items.length ? <div className="table-scroll"><table><thead><tr><th>Hisse</th><th>Adı</th><th>Son kapanış · TRY</th><th>Veri tarihi</th></tr></thead>
      <tbody>{data.items.map((stock: Stock) => <tr key={stock.symbol}>
        <td><Link href={`/stocks/${encodeURIComponent(stock.symbol)}`}>{stock.symbol}</Link></td>
        <td><Link href={`/stocks/${encodeURIComponent(stock.symbol)}`}>{stock.name}</Link></td>
        <td>{decimal(stock.last_close)}</td><td>{dateTr(stock.last_date)}</td>
      </tr>)}</tbody></table></div> : <p>{q ? 'Aramanızla eşleşen hisse bulunamadı.' : 'Kaynaklı BIST 30 hisse kaydı bulunmuyor.'}</p>}
    <nav className="pagination" aria-label="Hisse sayfaları">
      {offset > 0 && <Link href={`/stocks?q=${encodeURIComponent(q)}&offset=${Math.max(0, offset - 30)}`}>Önceki</Link>}
      {offset + 30 < data.total && <Link href={`/stocks?q=${encodeURIComponent(q)}&offset=${offset + 30}`}>Sonraki</Link>}
    </nav>
  </section>;
}
