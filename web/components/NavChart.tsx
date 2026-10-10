'use client';

import {useId, useMemo, useState} from 'react';
import {decimal, dateTr} from '@/lib/client';
import {FundPoint, fundSeries, fundWindow, sourceTime,sourceName} from '@/lib/fund-display';
import {useReady} from '@/lib/use-ready';
import styles from './Funds.module.css';

export type FundMarker = {date: string; label: string; href: string};

export default function NavChart({points, markers = []}: {points: FundPoint[]; markers?: FundMarker[]}) {
  const ready = useReady();
  const [days, setDays] = useState<number | null>(365);
  const [active, setActive] = useState<number | null>(null);
  const [marker, setMarker] = useState<FundMarker | null>(null);
  const [table, setTable] = useState(false);
  const gradient = useId().replaceAll(':', '');
  const visible = useMemo(() => fundWindow(points, days), [points, days]);
  const series = useMemo(() => fundSeries(visible), [visible]);
  const point = active === null ? null : visible[active];
  const coordinate = active === null ? null : series.coordinates[active];
  const start = visible.length ? Date.parse(visible[0].effective_date) : 0;
  const end = visible.length ? Date.parse(visible[visible.length - 1].effective_date) : 0;
  const markerPoints = markers.filter(item => Date.parse(item.date) >= start && Date.parse(item.date) <= end);

  function atPosition(value: number) {
    let closest = 0;
    for (let index = 1; index < series.coordinates.length; index++) {
      if (Math.abs(series.coordinates[index].x - value) < Math.abs(series.coordinates[closest].x - value)) closest = index;
    }
    setActive(closest); setMarker(null);
  }

  return <div className={styles.chart}>
    {series.segments.length ? <div className={styles.plot} onMouseLeave={() => {setActive(null); setMarker(null);}}>
      <svg className={styles.chartSvg} viewBox="0 0 896 320" role="img" tabIndex={ready ? 0 : -1}
        aria-label="Yayımlanmış günlük fon birim fiyatı; ok tuşlarıyla tarihleri inceleyin, eksik değerler boşluk olarak gösterilir"
        onPointerMove={event => {const bounds = event.currentTarget.getBoundingClientRect(); atPosition((event.clientX - bounds.left) * 896 / bounds.width);}}
        onFocus={() => setActive(visible.length - 1)} onBlur={() => setActive(null)}
        onKeyDown={event => {
          if (['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) {
            event.preventDefault(); setMarker(null);
            setActive(current => event.key === 'Home' ? 0 : event.key === 'End' ? visible.length - 1 : Math.max(0, Math.min(visible.length - 1, (current ?? visible.length - 1) + (event.key === 'ArrowLeft' ? -1 : 1))));
          } else if (event.key === 'Escape') {setActive(null); setMarker(null);}
        }}>
        <defs><linearGradient id={gradient} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="currentColor" stopOpacity=".14"/><stop offset="100%" stopColor="currentColor" stopOpacity="0"/></linearGradient></defs>
        {[26, 148, 270].map((y, index) => <g key={y}><line x1="12" x2="792" y1={y} y2={y} stroke="currentColor" strokeDasharray="2 4" opacity=".16"/>
          <text x="815" y={y + 4} className={styles.axis}>{new Intl.NumberFormat('tr-TR', {maximumSignificantDigits: 5}).format(series.high! - index * (series.high! - series.low!) / 2)}</text></g>)}
        {series.segments.map((segment, index) => <g key={index}>
          <polygon points={`${segment[0].x},280 ${segment.map(item => `${item.x},${item.y}`).join(' ')} ${segment[segment.length - 1].x},280`} fill={`url(#${gradient})`}/>
          <polyline points={segment.map(item => `${item.x},${item.y}`).join(' ')} fill="none" stroke="currentColor" strokeWidth="1.7"/>
          {segment.length === 1 && <circle cx={segment[0].x} cy={segment[0].y} r="2" fill="currentColor"/>}
        </g>)}
        {[0, .25, .5, .75, 1].map(fraction => {const item = visible[Math.round(fraction * (visible.length - 1))]; return <text key={fraction} x={12 + fraction * 780} y="312" textAnchor={fraction === 0 ? 'start' : fraction === 1 ? 'end' : 'middle'} className={styles.axis}>{dateTr(item.effective_date)}</text>;})}
        {markerPoints.map(item => <line key={`${item.date}-${item.label}`} x1={12 + (Date.parse(item.date) - start) * 780 / Math.max(1, end - start)} x2={12 + (Date.parse(item.date) - start) * 780 / Math.max(1, end - start)} y1="16" y2="280" stroke="#ff9f1a" strokeDasharray="3 4" opacity=".6"/>)}
        {coordinate && <line x1={coordinate.x} x2={coordinate.x} y1="16" y2="280" stroke="currentColor" opacity=".45"/>}
      </svg>
      {coordinate?.y !== null && coordinate?.y !== undefined && <img className={styles.chartPoint} src="/figma/funds/chart-point.svg" alt="" style={{left: `${coordinate.x / 896 * 100}%`, top: `${coordinate.y / 320 * 100}%`}}/>}
      {markerPoints.map(item => <button disabled={!ready} type="button" className={styles.marker} key={`${item.date}-${item.label}`}
        style={{left: `${(12 + (Date.parse(item.date) - start) * 780 / Math.max(1, end - start)) / 896 * 100}%`, top: `${(series.coordinates[visible.findIndex(point => point.effective_date === item.date)]?.y ?? 280) / 320 * 100}%`}}
        aria-label={`${dateTr(item.date)} ${item.label}`} onMouseEnter={() => {setMarker(item); setActive(null);}} onClick={() => {setMarker(item); setActive(null);}} onFocus={() => {setMarker(item); setActive(null);}}
        onKeyDown={event => {if (event.key === 'Escape') setMarker(null);}}><img src="/design/important-dot.svg" alt=""/></button>)}
      {(point || marker) && <div className={styles.chartTooltip} role="status" style={{left: `${Math.max(17, Math.min(78, coordinate ? coordinate.x / 896 * 100 : (12 + (Date.parse(marker!.date) - start) * 780 / Math.max(1, end - start)) / 896 * 100))}%`}}>
        <span>{dateTr(marker?.date ?? point!.effective_date)}</span>
        {marker ? <><strong>{marker.label}</strong><a href={marker.href} target={marker.href.startsWith('https://') ? '_blank' : undefined} rel="noreferrer">Kaynağı incele<img src="/design/arrow.svg" alt=""/></a></> : <><strong>{point!.ambiguous_revision ? 'Kaynaklarda farklı fiyatlar var' : point!.nav === null ? 'Veri yok' : decimal(point!.nav)}</strong><span>TEFAS · günlük birim fiyat</span></>}
        <img className={styles.chartTooltipArrow} src="/figma/funds/tooltip-down.svg" alt=""/>
      </div>}
    </div> : <p className={styles.empty}>Bu dönem için yayımlanmış birim fiyat bulunmuyor.</p>}
    <div className={styles.chartControls}><div className={styles.segments} aria-label="Grafik dönemi">
      {([[31, '1A'], [93, '3A'], [365, '1Y'], [null, '2Y']] as const).map(([value, label]) => <button disabled={!ready} key={label} type="button" className={days === value ? styles.selected : ''}
        aria-pressed={days === value} onClick={() => {setDays(value); setActive(null); setMarker(null);}}>{label}</button>)}
    </div><button disabled={!ready} type="button" className={styles.textButton} aria-expanded={table} onClick={() => setTable(value => !value)}>{table ? 'Tabloyu gizle' : 'Tablo olarak gör'}<img src="/design/arrow.svg" alt=""/></button></div>
    <p className={styles.caption}>Son iki yıl içinde yayımlanmış günlük fiyatlar. Fiyat alınamayan günler grafikte boş bırakılır.</p>
    {table && <div className="table-scroll"><table><caption>Yayımlanmış günlük birim fiyat verileri</caption><thead><tr><th>Tarih</th><th>Birim fiyat</th><th>İncelemede kullanılabildiği tarih</th><th>Kaynak</th></tr></thead><tbody>{visible.map(item => <tr key={item.effective_date}><td>{dateTr(item.effective_date)}</td><td>{item.ambiguous_revision ? 'Kaynaklarda farklı fiyatlar var' : decimal(item.nav)}</td><td>{sourceTime(item.available_at)}</td><td>{sourceName(item.source_id)}</td></tr>)}</tbody></table></div>}
  </div>;
}
