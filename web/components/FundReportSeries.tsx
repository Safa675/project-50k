'use client';
import {useId,useMemo,useState} from 'react';
import {dateTr,decimal} from '../lib/client';
import {useReady} from '../lib/use-ready';
import styles from './Funds.module.css';

export type FundReportPoint={report_period:string;cadence:string;period_end:string|null;total_value:string|null;units_outstanding:string|null;published_at:string|null;available_at:string|null;source_url:string|null;source_sha256:string;status:string;missing_fields:string[]};
type Metric='total_value'|'units_outstanding';
const metricLabels:Record<Metric,string>={total_value:'Raporlanan toplam değer',units_outstanding:'Pay sayısı'};
function usable(row:FundReportPoint,metric:Metric):number|null{const value=row[metric]===null?null:Number(row[metric]);return row.status!=='AMBIGUOUS_REVISION'&&value!==null&&Number.isFinite(value)?value:null;}
function cadenceLabel(value:string){return value==='weekly'?'Haftalık raporlar':value==='monthly'?'Aylık raporlar':'Dönemsel raporlar';}

export default function FundReportSeries({items}:{items:FundReportPoint[]}){
  const ready=useReady(),id=useId().replaceAll(':','');
  const cadences=[...new Set(items.map(item=>item.cadence.toLowerCase()))];
  const [chosenCadence,setCadence]=useState(cadences.includes('monthly')?'monthly':cadences[0]);
  const cadence=cadences.includes(chosenCadence)?chosenCadence:cadences.includes('monthly')?'monthly':cadences[0];
  const [metric,setMetric]=useState<Metric>('total_value');
  const rows=useMemo(()=>items.filter(item=>item.cadence.toLowerCase()===cadence).sort((a,b)=>(a.period_end??a.report_period).localeCompare(b.period_end??b.report_period)),[items,cadence]);
  const metrics=(['total_value','units_outstanding'] as const).filter(key=>rows.some(row=>usable(row,key)!==null));
  const active=metrics.includes(metric)?metric:metrics[0];
  if(!items.length||!active)return null;
  const dated=rows.filter(row=>row.period_end),values=dated.map(row=>usable(row,active)),known=values.filter((value):value is number=>value!==null);
  const low=known.length?Math.min(...known):0,high=known.length?Math.max(...known):0;
  const first=dated.length?Date.parse(dated[0].period_end!):0,last=dated.length?Date.parse(dated[dated.length-1].period_end!):0;
  const segments:{x:number;y:number}[][]=[];let segment:{x:number;y:number}[]=[];
  dated.forEach((row,index)=>{const value=values[index],previous=dated[index-1];const elapsed=previous?(Date.parse(row.period_end!)-Date.parse(previous.period_end!))/86400000:0;const gap=previous&&(cadence==='weekly'?elapsed>8:cadence==='monthly'?elapsed>35:false);if(value===null||gap){if(segment.length)segments.push(segment);segment=[];}if(value!==null)segment.push({x:24+(Date.parse(row.period_end!)-first)*800/Math.max(1,last-first),y:high===low?130:220-(value-low)*180/(high-low)});});if(segment.length)segments.push(segment);
  return <section className={styles.reportSeries}><div className={styles.sectionTitle}><h2>Raporlarda fonun görünümü</h2><span className={styles.caption}>KAP · {cadenceLabel(cadence)}</span></div><p className={styles.muted}>{cadence==='weekly'?'Haftalık rapor değerleri kaynak tablosunda gösterilir. Dönemin tam değerleme günü doğrulanmadığı için tarihli bir çizgi üretilmez.':'Her nokta bir rapor dönemidir. Günlük değerler üretilmez; eksik dönemlerde çizgi kesilir.'}</p><div className={styles.chartControls}><div className={styles.segments} aria-label="Rapor ölçümü">{metrics.map(key=><button type="button" disabled={!ready} key={key} aria-pressed={active===key} className={active===key?styles.selected:undefined} onClick={()=>setMetric(key)}>{metricLabels[key]}</button>)}</div>{cadences.length>1&&<label>Rapor sıklığı<select value={cadence} onChange={event=>setCadence(event.target.value)}>{cadences.map(value=><option key={value} value={value}>{cadenceLabel(value)}</option>)}</select></label>}</div><h3>{metricLabels[active]}</h3>
    {segments.length>0&&<svg className={styles.chartSvg} viewBox="0 0 896 260" role="img" aria-label={`${cadenceLabel(cadence)}: ${metricLabels[active]}; eksik dönemler boş bırakılır`}><title>{`${metricLabels[active]} · KAP rapor dönemleri`}</title><defs><linearGradient id={id} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="var(--bs-accent-text)" stopOpacity=".15"/><stop offset="100%" stopColor="var(--bs-accent-text)" stopOpacity="0"/></linearGradient></defs>{(high===low?[130]:[40,130,220]).map((y,index)=><g key={y}><line x1="24" x2="824" y1={y} y2={y} stroke="currentColor" opacity=".12" strokeDasharray="3 5"/><text x="834" y={y+4} className={styles.axis}>{new Intl.NumberFormat('tr-TR',{notation:'compact',maximumFractionDigits:1}).format(high-index*(high-low)/2)}</text></g>)}{segments.map((points,index)=><g key={index}><polyline points={points.map(point=>`${point.x},${point.y}`).join(' ')} fill="none" stroke="var(--bs-accent-text)" strokeWidth="2"/>{points.map((point,i)=><circle key={i} cx={point.x} cy={point.y} r="3" fill="var(--bs-accent-text)"/>)}</g>)}{dated.length>0&&<><text x="24" y="252" className={styles.axis}>{dateTr(dated[0].period_end)}</text><text x="824" y="252" textAnchor="end" className={styles.axis}>{dateTr(dated[dated.length-1].period_end)}</text></>}</svg>}
    <details><summary>Rapor değerlerini ve kaynaklarını gör</summary><div className="table-scroll"><table><thead><tr><th>Rapor dönemi</th><th>{metricLabels[active]}</th><th>Yayım tarihi</th><th>Kaynak</th></tr></thead><tbody>{rows.map(row=><tr key={`${row.report_period}:${row.source_sha256}`}><td>{row.report_period}</td><td>{row.status==='AMBIGUOUS_REVISION'?'Kaynaklar çelişiyor':row[active]===null?'Raporda okunamadı':decimal(row[active])}</td><td>{row.published_at?dateTr(row.published_at):'Belirtilmemiş'}</td><td>{row.source_url?<a href={row.source_url} target="_blank" rel="noreferrer">KAP raporunu aç</a>:'KAP'}</td></tr>)}</tbody></table></div></details>
  </section>;
}
