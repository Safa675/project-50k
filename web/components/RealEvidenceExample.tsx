import Link from 'next/link';
import {serverApi} from '@/lib/auth';
import {dateTr,decimal,reasonTr,stateTr} from '@/lib/client';

export default async function RealEvidenceExample(){
  const auth=await serverApi('/auth/me');
  if(!auth.ok)return <div className="real-evidence-example"><p className="bs-label">Geçmiş fon incelemesi</p><h3>THF kaynak ve kanıt incelemesi</h3><p>Resmî kayıtlar, tarihli gözlemler ve incelemenin sınırları birlikte gösterilir.</p><Link href="/login">Giriş yap ve kaynakları incele →</Link></div>;
  const response=await serverApi('/funds/THF');
  if(!response.ok)return <div className="real-evidence-example"><h3>Kaynaklara şu anda erişilemiyor</h3><Link href="/funds/THF">Fon incelemesini aç →</Link></div>;
  const data=await response.json();
  const item=data.signals?.find((signal:{state:string;is_attribute:boolean})=>signal.state==='TRIGGERED'&&!signal.is_attribute)??data.signals?.[0];
  if(!item)return <div className="real-evidence-example"><h3>THF kaynak incelemesi</h3><p>Bu fon için tamamlanmış gösterge kaydı bulunmuyor.</p><Link href="/funds/THF">Kaynakları incele →</Link></div>;
  return <div className="real-evidence-example"><p className="bs-label">{dateTr(item.as_of)} · Geliştirme sonucu</p><h3>THF · {stateTr[item.state]}</h3><p>{reasonTr(item.reason)}</p><p>{item.detector_id} · Değer: {decimal(item.value)} · Eşik: {decimal(item.threshold)}</p><Link href={`/developments/${encodeURIComponent(item.evidence_id)}?fund=THF`}>Gelişmeyi incele →</Link></div>;
}
