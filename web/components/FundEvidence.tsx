import Link from 'next/link';
import {dateTr,decimal,reasonTr,stateTr} from '@/lib/client';
import {signalName,sourceName,FundSignal} from '@/lib/fund-display';
import FundTooltip from './FundTooltip';
import MethodExplanation from './MethodExplanation';
import {explainResult,resultStatus} from '@/lib/method-explanations';
import styles from './Funds.module.css';

export default function FundEvidence({signals,showFund=false}:{signals:FundSignal[];showFund?:boolean}){
  return <div>{signals.length?signals.map(signal=><div key={signal.evidence_id} className={styles.signalRow}>
    <div className={styles.signalDate}>{signal.effective_date?dateTr(signal.effective_date):'Tarih belirlenemedi'}</div>
    <div className={styles.signalBody}><div className={styles.signalTags}><FundTooltip title={resultStatus(signal)} text={explainResult(signal)}><span className={`${styles.badge} ${signal.state==='TRIGGERED'?styles.triggered:''}`}>{signal.state==='TRIGGERED'&&<img src="/design/important-dot.svg" alt=""/>}{signal.is_attribute?'Fiyat geçmişi':resultStatus(signal)}</span></FundTooltip></div>
      <h3>{showFund&&`${signal.fund_code}: `}{signalName(signal.detector_id)}</h3><p>{explainResult(signal)}</p>
      <MethodExplanation code={signal.detector_id} effectiveDate={signal.effective_date}/>
      <div className={styles.signalSources}>{signal.source_references.length>0&&<span>Kaynak: {[...new Set(signal.source_references.map(ref=>sourceName(ref.source_id)))].join(', ')}</span>}<Link className={styles.textButton} href={`/developments/${encodeURIComponent(signal.evidence_id)}?fund=${signal.fund_code}`}>Gelişmeyi incele<img src="/design/arrow.svg" alt=""/></Link></div>
    </div></div>):<p className={styles.empty}>Bu görünümde gösterilecek bir inceleme sonucu bulunmuyor.</p>}</div>;
}
