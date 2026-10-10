import Link from 'next/link';
import AssetLogo from '@/components/AssetLogo';
import {notFound} from 'next/navigation';
import {serverApi} from '@/lib/auth';
import {dateTr,decimal} from '@/lib/client';
import StockChart from '@/components/StockChart';

type CorporateAction = {event_id: string; effective_date: string|null; payload: Record<string, unknown>; available_at: string; source_sha256: string};

export default async function Detail({params}: {params: Promise<{symbol: string}>}) {
  const {symbol} = await params;
  if (!/^[A-Z][A-Z0-9]{1,11}$/.test(symbol)) notFound();
  const response = await serverApi(`/stocks/${symbol}?days=365`);
  if (response.status === 404) notFound();
  if (!response.ok) throw new Error('Hisse verilerine şu anda erişilemiyor.');
  const data = await response.json();
  if (!data.stock || data.stock.symbol !== symbol || !Array.isArray(data.chart?.points) || data.chart.cadence !== 'DAILY_CLOSE') {
    throw new Error('Hisse yanıtı doğrulanamadı.');
  }
  const latest=data.chart.points.slice().reverse().find((point:{close:string|null;ambiguous_revision:boolean})=>point.close!==null&&!point.ambiguous_revision&&Number(point.close)>0);
  return <section><Link href="/stocks">← Hisse kataloğu</Link>
    <p className="eyebrow">{symbol} · BIST</p><div className="stock-heading"><AssetLogo kind="stock" code={symbol} name={data.stock.name} size={48} decorative/><h1>{data.stock.name}</h1></div>
    <p>Güncel BIST 30 kataloğu · Türk lirası.</p>
    {latest&&<div className="stock-latest"><p>Son yayımlanmış kapanış</p><strong>{decimal(latest.close)} TL</strong><p>{dateTr(latest.effective_date)} · ForInvest</p></div>}
    <article><h2>Yayımlanmış günlük kapanış fiyatı</h2>
      <p>Bölünme ve temettü düzeltmesinin yapıldığı doğrulanmadı; bu durum fiyat karşılaştırmalarını sınırlayabilir.</p>
      <StockChart points={data.chart.points}/>
    </article>
    {Array.isArray(data.corporate_actions) && data.corporate_actions.length > 0 && <article><h2>Kaynakta gözlenen şirket işlem kayıtları</h2>
      <p>Kayıtların sınıflandırması ve kapanış fiyatlarına etkileri doğrulanmadı. İşlemin türü doğrulanana kadar fiyat üzerindeki etkisi hesaplanmaz.</p>
      {data.corporate_actions_total > data.corporate_actions.length && <p>{data.corporate_actions_total.toLocaleString('tr-TR')} kaydın ilk {data.corporate_actions.length.toLocaleString('tr-TR')} tanesi gösteriliyor.</p>}
      {data.corporate_actions.map((action: CorporateAction) => <details key={action.event_id}>
        <summary>{dateTr(action.effective_date)} · Kaynak kaydı</summary>
        <p>Kaynak erişim zamanı: {new Intl.DateTimeFormat('tr-TR', {dateStyle: 'medium', timeStyle: 'short', timeZone: 'Europe/Istanbul'}).format(new Date(action.available_at))}</p>

        <p>ForInvest kaynağında bu tarih için bir şirket işlemi kaydı bulunuyor. İşlem türü henüz doğrulanmadı.</p>
      </details>)}
    </article>}
  </section>;
}
