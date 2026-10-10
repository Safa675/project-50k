import {decimal,dateTr} from '@/lib/client';
type Point={effective_date:string;nav:string|null;ambiguous_revision:boolean};
export default function NavChart({points}:{points:Point[]}) {
  const valid=points.flatMap((point,index)=>point.nav===null?[]:[{index,value:Number(point.nav)}]).filter(p=>Number.isFinite(p.value));
  if(!valid.length)return <p>Bu dönem için yayımlanmış birim fiyat bulunmuyor.</p>;
  const low=Math.min(...valid.map(p=>p.value)),high=Math.max(...valid.map(p=>p.value));
  const segments:string[]=[];let segment:string[]=[];
  points.forEach((point,index)=>{if(point.nav===null||point.ambiguous_revision){if(segment.length)segments.push(segment.join(' '));segment=[];return;}const x=30+index*740/Math.max(1,points.length-1);const y=200-(Number(point.nav)-low)*170/Math.max(high-low,Number.EPSILON);segment.push(`${x},${y}`);});if(segment.length)segments.push(segment.join(' '));
  return <><svg viewBox="0 0 800 230" role="img" aria-label="Yayımlanmış günlük fon birim fiyatı; eksik değerler boşluk olarak gösterilir"><line x1="30" y1="210" x2="770" y2="210" stroke="currentColor" opacity=".25"/>{segments.map((line,index)=><polyline key={index} points={line} fill="none" stroke="#1b6559" strokeWidth="2"/>)}</svg><p className="muted">Günlük yayımlanmış birim fiyat. Eksik veya çelişkili değerler doldurulmaz.</p><details><summary>Grafik verilerini tablo olarak göster</summary><div className="table-scroll"><table><thead><tr><th>Tarih</th><th>Birim fiyat</th></tr></thead><tbody>{points.map(p=><tr key={p.effective_date}><td>{dateTr(p.effective_date)}</td><td>{p.ambiguous_revision?'Çelişkili kaynak sürümü':decimal(p.nav)}</td></tr>)}</tbody></table></div></details></>;
}
