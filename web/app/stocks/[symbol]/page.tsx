import Link from 'next/link';
import AssetLogo from '@/components/AssetLogo';
import {notFound} from 'next/navigation';
import {serverApi} from '@/lib/auth';
import {dateTr,decimal} from '@/lib/client';
import StockChart from '@/components/StockChart';
import {StockPoint, stockAvailableTime, stockSourceLabel} from '@/lib/stock-chart';

type CorporateAction = {event_id: string; effective_date: string|null; payload: Record<string, unknown>; available_at: string; source_sha256: string};

export default async function Detail({params}: {params: Promise<{symbol: string}>}) {
  const {symbol} = await params;
  if (!/^[A-Z][A-Z0-9]{1,11}$/.test(symbol)) notFound();
  const response = await serverApi(`/stocks/${symbol}?days=365`);
  if (response.status === 404) notFound();
  if (!response.ok) throw new Error('Hisse verilerine şu anda erişilemiyor.');
  const data = await response.json();
  if (!data.stock || data.stock.symbol !== symbol || !Array.isArray(data.chart?.points) || data.chart.cadence !== 'DAILY_CLOSE' || !['BIST30_CURRENT_CATALOG','BIST30_DATED_BULLETIN'].includes(data.universe)) {
    throw new Error('Hisse yanıtı doğrulanamadı.');
  }
  const latest: StockPoint|undefined=data.chart.points.slice().reverse().find((point:StockPoint)=>point.close!==null&&!point.ambiguous_revision&&Number(point.close)>0);
  const dated=data.universe==='BIST30_DATED_BULLETIN';
  return <section><Link href="/stocks">← Hisse kataloğu</Link>
    <p className="eyebrow">{symbol} · BIST</p><div className="stock-heading"><AssetLogo kind="stock" code={symbol} name={data.stock.name} size={48} decorative/><h1>{data.stock.name}</h1></div>
    <p>{dated ? `${dateTr(data.dated_member_on)} tarihli bültenin BIST 30 üyeliği` : 'Güncel BIST 30 kataloğu'} · Türk lirası.</p>
    {!latest&&<p className="notice">Seçilen inceleme tarihinde kullanılabilir bir fiyat kaydı yok. Kaynaktan daha sonra alınan fiyatlar bu tarihe taşınmaz. Üstteki inceleme tarihinden güncel görünüme geçebilirsiniz.</p>}{latest&&<div className="stock-latest"><p>Son yayımlanmış kapanış</p><strong>{decimal(latest.close)} TL</strong><p>{dateTr(latest.effective_date)} · {stockSourceLabel(latest.source_id)}</p><p className="muted">Kaynakta erişilebilir olduğu zaman: <time dateTime={latest.available_at??undefined}>{stockAvailableTime(latest.available_at)}</time>.</p></div>}
    <article><h2>Yayımlanmış günlük kapanış fiyatı</h2>
      <p>{data.price_adjustment==='UNADJUSTED' ? 'Borsa İstanbul bültenindeki kapanışlar bölünme ve temettü için düzeltilmemiştir; bu işlemler fiyat karşılaştırmalarını etkileyebilir.' : data.price_adjustment==='MIXED' ? 'Borsa İstanbul bültenindeki kapanışlar bölünme ve temettü için düzeltilmemiştir. ForInvest fiyatlarının düzeltme durumu doğrulanmadı; bu durum fiyat karşılaştırmalarını sınırlayabilir.' : 'Bölünme ve temettü düzeltmesinin yapıldığı doğrulanmadı; bu durum fiyat karşılaştırmalarını sınırlayabilir.'}</p>
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
