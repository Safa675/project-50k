import Link from 'next/link';
import {notFound} from 'next/navigation';
import {serverApi} from '@/lib/auth';
import {dateTr} from '@/lib/client';
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
  return <section><Link href="/stocks">← Hisse kataloğu</Link>
    <p className="eyebrow">{symbol} · BIST · {data.data_mode}</p><h1>{data.stock.name}</h1>
    <p>Güncel BIST 30 kataloğu · TRY. Güncel endeks üyeliği tarihsel üyelik bilgisi değildir.</p>
    <p className="notice">Geliştirme sonucu · Veri hakları incelenmedi · Yatırım tavsiyesi değildir.</p>
    <article><h2>Yayımlanmış günlük kapanış fiyatı</h2>
      <p>Bölünme ve temettü düzeltmesinin yapıldığı doğrulanmadı; bu durum fiyat karşılaştırmalarını sınırlayabilir.</p>
      <StockChart points={data.chart.points}/>
    </article>
    {Array.isArray(data.corporate_actions) && data.corporate_actions.length > 0 && <article><h2>Kaynakta gözlenen şirket işlem kayıtları</h2>
      <p>Kayıtların sınıflandırması ve kapanış fiyatlarına etkileri doğrulanmadı. Kaynağın özgün kayıtları gösterilir.</p>
      {data.corporate_actions_total > data.corporate_actions.length && <p>{data.corporate_actions_total.toLocaleString('tr-TR')} kaydın ilk {data.corporate_actions.length.toLocaleString('tr-TR')} tanesi gösteriliyor.</p>}
      {data.corporate_actions.map((action: CorporateAction) => <details key={action.event_id}>
        <summary>{dateTr(action.effective_date)} · Kaynak kaydı</summary>
        <p>Kaynak erişim zamanı: {new Intl.DateTimeFormat('tr-TR', {dateStyle: 'medium', timeStyle: 'short', timeZone: 'Europe/Istanbul'}).format(new Date(action.available_at))}</p>
        <p><code>{action.source_sha256}</code></p>
        <pre style={{whiteSpace: 'pre-wrap', overflowWrap: 'anywhere'}}><code>{JSON.stringify(action.payload, null, 2)}</code></pre>
      </details>)}
    </article>}
  </section>;
}
