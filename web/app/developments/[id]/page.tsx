import Link from 'next/link';
import {notFound} from 'next/navigation';
import {serverApi,requireUser} from '@/lib/auth';
import {dateTr,decimal,reasonTr,stateTr} from '@/lib/client';
import {signalName,sourceName} from '@/lib/fund-display';
import AgentPage from '@/components/agents/AgentPage';
import EvidenceFeedback from '@/components/EvidenceFeedback';
import EvidenceTooltip from '@/components/EvidenceTooltip';
import MethodExplanation from '@/components/MethodExplanation';
import {explainResult,resultStatus} from '@/lib/method-explanations';
import './evidence.css';

type Source={source_id:string;source_sha256:string;source_url:string|null;available_at:string|null;effective_date:string|null};
function Hover({children,text,direction='bottom'}:{children:React.ReactNode;text:string;direction?:'bottom'|'right'}){return <EvidenceTooltip text={text} direction={direction}>{children}</EvidenceTooltip>;}
export default async function Development({params}:{params:Promise<{id:string}>}){
  const route=await params;let id:string;try{id=decodeURIComponent(route.id);}catch{notFound();}if(!id||id.length>100)notFound();
  const [response]=await Promise.all([serverApi(`/evidence?evidence_id=${encodeURIComponent(id)}`),requireUser()]);
  if(response.status===404)notFound();if(!response.ok)throw new Error('Kanıt kaydına erişilemiyor.');
  const data=await response.json(),signal=data.signal,sources:Source[]=signal.source_references??[];
  const title=signalName(signal.detector_id);
  return <section className="evidence-detail" data-design-node="22:382">
    <AgentPage fundCode={data.fund.fund_code} evidenceId={signal.evidence_id} title={title}/>
    <Link className="evidence-back" href={`/funds/${data.fund.fund_code}`}><img src="/design/evidence/back.svg" alt=""/>{data.fund.name}</Link>
    {!data.is_current&&<p className="notice">Bu kayıt önceki bir değerlendirme çalışmasına aittir. Güncel sonuçlara fon sayfasından ulaşabilirsiniz.</p>}
    <div className="evidence-columns"><div className="evidence-main">
      <header className="evidence-heading"><div className="evidence-tags"><span className={signal.state==='TRIGGERED'?'evidence-tag attention':'evidence-tag'}><Hover text="Etiket yalnızca bu göstergenin durumunu açıklar. Bir yatırım kararı, fiyat yönü veya doğrulanmış tahmin anlamına gelmez.">{resultStatus(signal)}</Hover></span><span className="evidence-tag">{signal.detector_id.startsWith('AN-DQ')?'Veri durumu':'Fiyat incelemesi'}</span><span className="evidence-tag">{data.fund.fund_code}</span></div><h1>{title}</h1><p>{dateTr(signal.effective_date)} · <Hover text="Bu incelemenin dayandığı kaynaklar sağ tarafta gösterilir. Kaynak bulunması sonucun kesin olduğu anlamına gelmez.">{sources.length?'Kaynağı mevcut':'Kaynak bilgisi eksik'}</Hover></p></header>
      <article className="evidence-card"><h2>Ne gözlendi</h2>
        <p>{explainResult(signal)}</p>{signal.is_attribute&&signal.value!==null&&<p>Eldeki fiyat geçmişi: {decimal(signal.value)} takvim günü.</p>}<dl className="evidence-measures">{signal.effective_date&&<div><dt>İncelenen tarih</dt><dd>{dateTr(signal.effective_date)}</dd></div>}<div><dt>Son veri tarihi</dt><dd>{dateTr(signal.as_of)}</dd></div></dl>
        <MethodExplanation code={signal.detector_id} effectiveDate={signal.effective_date} asOf={signal.as_of}/>

      </article>
      <section><h2>Nasıl yorumlanır</h2><p>{explainResult(signal)}</p><p>Bu gösterge değişimin nedenini tek başına açıklamaz. Sonuç, kaynağı ve sınırlarıyla birlikte insan tarafından incelenmelidir.</p></section>
      <div className="evidence-notes"><article className="evidence-card"><h2>Bu bilgi ne anlatıyor?</h2><p>{signal.state==='ABSTAINED'?'Bu konu için yeterli bilgi bulunamadı. Bilgi eksikliği normal bir sonuç olarak değerlendirilmez.':signal.is_attribute?'Bu bilgi arşivdeki geçmişin uzunluğunu anlatır.':signal.state==='TRIGGERED'?'Bu inceleme bir değişime veya eksik fiyat bilgisine dikkat çeker. Nedenini anlamak için kaynaklar birlikte incelenir.':`${explainResult(signal)} Bu sonuç yalnızca burada açıklanan karşılaştırmaya aittir.`}</p></article><article className="evidence-card"><h2>Henüz bilinmeyenler</h2><p>{signal.state==='ABSTAINED'?'Bu gösterge için karar vermeye yetecek uygun zamanlı kanıt bulunmuyor.':'Değişimin nedeni ve başka kaynaklarla doğrulanıp doğrulanmadığı bu göstergeden çıkarılamaz.'}</p></article></div>
      <EvidenceFeedback key={signal.evidence_id} evidenceId={signal.evidence_id} initial={data.helpful}/>
    </div><aside className="evidence-aside">
      <article className="evidence-card"><h2>Kaynak</h2><p>{data.fund.name}</p>{sources.length?sources.map((source,index)=><div className="evidence-source" key={`${source.source_sha256}-${index}`}><strong>{sourceName(source.source_id)}</strong><dl className="evidence-measures"><div><dt>Gözlem</dt><dd>{dateTr(source.effective_date)}</dd></div><div><dt>İncelemede kullanılabildiği tarih</dt><dd>{source.available_at?new Date(source.available_at).toLocaleString('tr-TR',{timeZone:'Europe/Istanbul'}):'Zaman bilinmiyor'}</dd></div></dl>{source.source_url&&<a className="evidence-source-link" target="_blank" rel="noreferrer" href={source.source_url}><img src="/design/evidence/external.svg" alt=""/>Resmî kaynakta gör</a>}</div>):<p>Bu gösterge için uygun zamanlı kaynak referansı bulunmuyor.</p>}</article>
      <article className="evidence-card"><h2>Kanıt nasıl izlenir</h2><p>Her değerlendirme dayandığı kaynaklarla saklanır. İnsan incelemesi, yapay zekânın ilk önerisinin yanında korunur.</p><Link href={`/funds/${data.fund.fund_code}`}>Fonun diğer gelişmelerini incele</Link><p className="evidence-small">Kaynak izlenebilirliği bir olasılık veya yatırım değerlendirmesi değildir.</p></article>
    </aside></div>
  </section>;
}
