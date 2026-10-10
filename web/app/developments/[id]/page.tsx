import Link from 'next/link';
import {notFound} from 'next/navigation';
import {serverApi} from '@/lib/auth';
import {dateTr,decimal,reasonTr,stateTr} from '@/lib/client';
import {detectorNames} from '@/lib/fund-display';
import ChatPanel from '@/components/ChatPanel';
import EvidenceFeedback from '@/components/EvidenceFeedback';
import EvidenceTooltip from '@/components/EvidenceTooltip';
import './evidence.css';

type Source={source_id:string;source_sha256:string;source_url:string|null;available_at:string|null;effective_date:string|null};
const unitLabels:Record<string,string>={days:'Takvim günü',weekdays:'Hafta içi gün (resmî tatiller doğrulanmadı)',indicator:'İkili gösterge (0 / 1)',log_return:'Logaritmik getiri',correlation:'Korelasyon katsayısı'};
function Hover({children,text,direction='bottom'}:{children:React.ReactNode;text:string;direction?:'bottom'|'right'}){return <EvidenceTooltip text={text} direction={direction}>{children}</EvidenceTooltip>;}
export default async function Development({params}:{params:Promise<{id:string}>}){
  const route=await params;let id:string;try{id=decodeURIComponent(route.id);}catch{notFound();}if(!id||id.length>100)notFound();
  const response=await serverApi(`/evidence?evidence_id=${encodeURIComponent(id)}`);
  if(response.status===404)notFound();if(!response.ok)throw new Error('Kanıt kaydına erişilemiyor.');
  const data=await response.json(),signal=data.signal,sources:Source[]=signal.source_references??[];
  const title=detectorNames[signal.detector_id]??signal.detector_id;
  const numberValue=Number(signal.value),numberThreshold=Number(signal.threshold);
  const comparable=signal.value!==null&&signal.threshold!==null&&Number.isFinite(numberValue)&&Number.isFinite(numberThreshold)&&numberValue>=0&&numberThreshold>0;
  const scale=comparable?Math.max(numberValue,numberThreshold):1;
  return <section className="evidence-detail" data-design-node="22:382">
    <div><span className="evidence-mode"><img src="/figma/funds/clock.svg" alt=""/><Hover text="Bu ekran tarihli kaynaklardan üretilen bir geliştirme sonucudur. Gözlem tarihi ile elde edilme zamanı farklı olabilir.">{dateTr(signal.as_of)} · {signal.origin}</Hover></span></div>
    <Link className="evidence-back" href={`/funds/${data.fund.fund_code}`}><img src="/design/evidence/back.svg" alt=""/>{data.fund.name}</Link>
    {!data.is_current&&<p className="notice">Bu kayıt önceki bir değerlendirme çalışmasına aittir. Güncel sonuçlara fon sayfasından ulaşabilirsiniz.</p>}
    <div className="evidence-columns"><div className="evidence-main">
      <header className="evidence-heading"><div className="evidence-tags"><span className={signal.state==='TRIGGERED'?'evidence-tag attention':'evidence-tag'}><Hover text="Etiket yalnızca bu göstergenin durumunu açıklar. Bir yatırım kararı, fiyat yönü veya doğrulanmış tahmin anlamına gelmez.">{signal.is_attribute?'Tarihçe özelliği':stateTr[signal.state]}</Hover></span><span className="evidence-tag">{signal.detector_id.startsWith('AN-DQ')?'Veri kalitesi':'Detektör kanıtı'}</span><span className="evidence-tag">{data.fund.fund_code}</span></div><h1>{title}</h1><p>{dateTr(signal.effective_date)} · Geliştirme sonucu · <Hover text="Kaynak referansları kayıtların izlenebilirliğini sağlar. Bağımsız doğrulama veya bir olasılık puanı değildir.">{sources.length?'Kaynak referansı kayıtlı':'Kaynak kanıtı yetersiz'}</Hover></p></header>
      <article className="evidence-card"><h2>Ne gözlendi</h2>
        {comparable&&<div className="evidence-comparison" aria-label="Hesaplanan değer ve sabit eşik karşılaştırması"><div><span style={{width:`${Math.max(0,numberThreshold/scale*100)}%`}}/><p>Sabit eşik<br/><strong>{decimal(signal.threshold)}</strong></p></div><div><span style={{width:`${Math.max(0,numberValue/scale*100)}%`}}/><p>Hesaplanan değer<br/><strong>{decimal(signal.value)}</strong></p></div></div>}
        <dl className="evidence-measures"><div><dt><Hover text="Sayısal değer model tarafından yazılmaz; sabit detektör uygulaması tarafından hesaplanır.">Hesaplanan değer</Hover></dt><dd>{decimal(signal.value)}</dd></div><div><dt><Hover text="Eşik bu çalışma için önceden kaydedilmiş sürüme bağlıdır. Model bu değeri değiştiremez.">Sabit eşik</Hover></dt><dd>{decimal(signal.threshold)}</dd></div><div><dt>Birim</dt><dd>{unitLabels[signal.unit]??signal.unit}</dd></div><div><dt>Gözlem tarihi</dt><dd>{dateTr(signal.effective_date)}</dd></div><div><dt>Değerlendirme tarihi</dt><dd>{dateTr(signal.as_of)}</dd></div></dl>
      </article>
      <section><h2>Nasıl yorumlanır</h2><p>{reasonTr(signal.reason)}</p><p>Bu gösterge değişimin nedenini tek başına açıklamaz. Sonuç, kaynağı ve sınırlarıyla birlikte insan tarafından incelenmelidir.</p></section>
      <div className="evidence-notes"><article className="evidence-card"><h2>İnceleme sınırları</h2><p>Eşikler olaydan sonra belirlendi. Bu kayıt doğrulanmış başarı, erken uyarı veya geleceğe ilişkin bir sonuç göstermez.</p></article><article className="evidence-card"><h2>Henüz bilinmeyenler</h2><p>{signal.state==='ABSTAINED'?'Bu gösterge için karar vermeye yetecek uygun zamanlı kanıt bulunmuyor.':'Değişimin nedeni ve başka kaynaklarla doğrulanıp doğrulanmadığı bu göstergeden çıkarılamaz.'}</p></article></div>
      <EvidenceFeedback key={signal.evidence_id} evidenceId={signal.evidence_id} initial={data.helpful}/>
    </div><aside className="evidence-aside">
      <article className="evidence-card"><h2>Kaynak</h2><p>{data.fund.name}</p>{sources.length?sources.map((source,index)=><div className="evidence-source" key={`${source.source_sha256}-${index}`}><strong>{source.source_id}</strong><dl className="evidence-measures"><div><dt>Gözlem</dt><dd>{dateTr(source.effective_date)}</dd></div><div><dt>Kullanılabilirlik</dt><dd>{source.available_at?new Date(source.available_at).toLocaleString('tr-TR',{timeZone:'Europe/Istanbul'}):'Zaman bilinmiyor'}</dd></div></dl><details><summary>Kaynak özeti</summary><code>{source.source_sha256}</code></details>{source.source_url&&<a className="evidence-source-link" target="_blank" rel="noreferrer" href={source.source_url}><img src="/design/evidence/external.svg" alt=""/>Resmî kaynakta gör</a>}</div>):<p>Bu gösterge için uygun zamanlı kaynak referansı bulunmuyor.</p>}</article>
      <article className="evidence-card"><h2>Kanıt nasıl izlenir</h2><p>Her sonuç bir çalışma ve kaynak özetiyle saklanır. İnsan incelemesi özgün model kararının yanında korunur.</p><details><summary>Çalışma ve kanıt kimlikleri</summary><code>{signal.run_id}</code><code>{signal.evidence_id}</code><code>{signal.version_id}</code></details><p className="evidence-small">Kaynak izlenebilirliği bir olasılık veya yatırım değerlendirmesi değildir.</p></article>
      <ChatPanel key={signal.evidence_id} code={data.fund.fund_code} drawer evidenceId={signal.evidence_id} contextTitle={title}/>
    </aside></div>
  </section>;
}
