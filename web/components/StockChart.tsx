import {dateTr, decimal} from '@/lib/client';
import {StockPoint, stockSeries} from '@/lib/stock-chart';

function availableTime(value: string|null): string {
  return value ? new Intl.DateTimeFormat('tr-TR', {dateStyle: 'medium', timeStyle: 'short', timeZone: 'Europe/Istanbul'}).format(new Date(value)) : 'Zaman bilinmiyor';
}

export default function StockChart({points}: {points: StockPoint[]}) {
  const segments = stockSeries(points);
  return <>
    {segments.length ? <svg viewBox="0 0 800 230" role="img" aria-label="Yayımlanmış günlük hisse kapanış fiyatı, TRY; eksik veya çelişkili değerler boşluk olarak gösterilir">
      <line x1="30" y1="210" x2="770" y2="210" stroke="currentColor" opacity=".25"/>
      {segments.map((segment, index) => segment.length === 1
        ? <circle key={index} cx={segment[0].x} cy={segment[0].y} r="3" fill="#1b6559"/>
        : <polyline key={index} points={segment.map(point => `${point.x},${point.y}`).join(' ')} fill="none" stroke="#1b6559" strokeWidth="2"/>)}
    </svg> : <p>Bu dönem için kullanılabilir günlük kapanış fiyatı bulunmuyor.</p>}
    <p className="muted">Günlük kapanış fiyatı · TRY. Eksik veya çelişkili gözlemler doldurulmaz.</p>
    {points.length > 0 && <details><summary>Kapanış fiyatlarını ve kaynaklarını tablo olarak göster</summary>
      <div className="table-scroll"><table><thead><tr><th>Tarih</th><th>Kapanış · TRY</th><th>Kaynak erişim zamanı</th><th>Kaynak özeti</th></tr></thead>
        <tbody>{points.map(point => <tr key={point.effective_date}>
          <td><time dateTime={point.effective_date}>{dateTr(point.effective_date)}</time></td>
          <td>{point.ambiguous_revision ? 'Çelişkili kaynak sürümü' : decimal(point.close)}</td>
          <td><time dateTime={point.available_at ?? undefined}>{availableTime(point.available_at)}</time></td>
          <td><code>{point.source_sha256}</code></td>
        </tr>)}</tbody></table></div>
    </details>}
  </>;
}
