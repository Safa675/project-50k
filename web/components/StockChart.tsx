import {dateTr, decimal} from '@/lib/client';
import {StockPoint, stockAvailableTime, stockSeries, stockSourceLabel} from '@/lib/stock-chart';

export default function StockChart({points}: {points: StockPoint[]}) {
  const segments = stockSeries(points);
  const prices=points.filter(point=>point.close!==null&&!point.ambiguous_revision&&Number.isFinite(Number(point.close))&&Number(point.close)>0).map(point=>Number(point.close));
  const low=prices.length?Math.min(...prices):0,high=prices.length?Math.max(...prices):0;
  return <>
    {segments.length ? <svg style={{display:'block',width:'100%',height:'auto',minHeight:180}} viewBox="0 0 800 230" role="img" aria-label="Yayımlanmış günlük hisse kapanış fiyatı, TRY; eksik veya çelişkili değerler boşluk olarak gösterilir">
      <line x1="30" y1="210" x2="770" y2="210" stroke="currentColor" opacity=".25"/>
      {(high===low?[115]:[30,115,200]).map((y,index)=><g key={y}><line x1="30" x2="770" y1={y} y2={y} stroke="currentColor" opacity=".12" strokeDasharray="3 5"/><text x="32" y={y-7} fill="var(--bs-muted)" fontSize="10">{new Intl.NumberFormat('tr-TR',{maximumFractionDigits:4}).format(high-index*(high-low)/2)} TL</text></g>)}
      {segments.map((segment, index) => segment.length === 1
        ? <circle key={index} cx={segment[0].x} cy={segment[0].y} r="3" fill="var(--bs-accent-text,#8b95ff)"/>
        : <polyline key={index} points={segment.map(point => `${point.x},${point.y}`).join(' ')} fill="none" stroke="var(--bs-accent-text,#8b95ff)" strokeWidth="2"/>)}
      {points.length>0&&<><text x="30" y="226" fill="var(--bs-muted)" fontSize="10">{dateTr(points[0].effective_date)}</text><text x="770" y="226" textAnchor="end" fill="var(--bs-muted)" fontSize="10">{dateTr(points[points.length-1].effective_date)}</text></>}
    </svg> : <p>Bu dönem için kullanılabilir günlük kapanış fiyatı bulunmuyor.</p>}
    <p className="muted">Günlük kapanış fiyatı · Türk lirası. Fiyat alınamayan günler boş bırakılır.</p>
    {points.length > 0 && <details><summary>Kapanış fiyatlarını ve kaynaklarını tablo olarak göster</summary>
      <div className="table-scroll"><table><thead><tr><th>Tarih</th><th>Kapanış · TL</th><th>Kaynak erişim zamanı</th><th>Kaynak</th></tr></thead>
        <tbody>{points.map(point => <tr key={point.effective_date}>
          <td><time dateTime={point.effective_date}>{dateTr(point.effective_date)}</time></td>
          <td>{point.ambiguous_revision ? 'Kaynaklarda farklı fiyatlar var' : decimal(point.close)}</td>
          <td><time dateTime={point.available_at ?? undefined}>{stockAvailableTime(point.available_at)}</time></td>
          <td>{stockSourceLabel(point.source_id)}</td>
        </tr>)}</tbody></table></div>
    </details>}
  </>;
}
