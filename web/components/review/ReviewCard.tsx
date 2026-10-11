'use client';
import Link from 'next/link';
import {useEffect,useId,useRef,useState} from 'react';
import AssetLogo from '@/components/AssetLogo';
import {friendlyEvidenceText} from '@/lib/fund-display';
import ReviewActions from './ReviewActions';
import {decisionLabel,decisionTone,proposalOriginLabel,proposalSource,reviewStateLabel,reviewedAtTr,type Decision} from './review-logic';
import styles from './review.module.css';

export const toneClass={important:'bs-tag bs-tag-important',attention:'bs-tag bs-tag-attention',neutral:'bs-tag'};

/** Two-line rationale with an expand control that appears only when the text is clamped. */
export function Rationale({text}:{text:string}){
  const ref=useRef<HTMLParagraphElement>(null),id=useId();
  const [open,setOpen]=useState(false),[clamped,setClamped]=useState(false);
  useEffect(()=>{const node=ref.current;if(!node)return;
    const measure=()=>setClamped(open||node.scrollHeight>node.clientHeight+1);
    measure();const observer=new ResizeObserver(measure);observer.observe(node);return ()=>observer.disconnect();},[open,text]);
  return <div className={styles.rationale}>
    <p ref={ref} id={id} className={open?undefined:styles.clamp}>{text}</p>
    {clamped&&<button type="button" className={styles.more} aria-expanded={open} aria-controls={id} onClick={()=>setOpen(value=>!value)}>{open?'Daha az göster':'Gerekçenin tamamı'}</button>}
  </div>;
}

/** Links to the developments a proposal cites, folded so the card stays short. */
export function EvidenceLinks({decision}:{decision:Pick<Decision,'evidence_ids'|'fund_code'>}){
  const evidence=decision.evidence_ids;
  if(!evidence.length)return null;
  return <details className={styles.evidence}>
    <summary>Dayandığı gelişmeler ({evidence.length})</summary>
    <ul>{evidence.map((id,index)=><li key={id}><Link href={`/developments/${encodeURIComponent(id)}?fund=${decision.fund_code}`}>Gelişme {index+1}</Link></li>)}</ul>
  </details>;
}

export default function ReviewCard({decision,onSaved}:{decision:Decision;onSaved:(message:string)=>void}){
  const code=decision.fund_code,headingId=`review-${code}`,reviewed=decision.has_current_review;
  return <article className={`${styles.card}${proposalSource(decision)==='team'?` ${styles.teamCard}`:''}`} aria-labelledby={headingId}>
    <div className={styles.main}>
      <div className={styles.proposalLine}><p className={styles.source}>{proposalOriginLabel(decision)}</p><span className={styles.reviewState}>{reviewStateLabel(decision)}</span></div>
      <div className={styles.head}>
        <div className={styles.identity}>
          <AssetLogo kind="fund" code={code} name={decision.fund_name??undefined} size={44} decorative/>
          <div className={styles.identityText}>{decision.fund_name&&<span className={styles.code}>{code}</span>}
          <h3 id={headingId} className={styles.name}><Link href={`/funds/${code}`}>{decision.fund_name||code}</Link></h3></div>
        </div>
        <span className={toneClass[decisionTone(decision.effective_value)]}>{decisionLabel(decision.effective_value)}</span>
      </div>
      {reviewed&&<p className={styles.meta}>İnsan incelemesi · {reviewedAtTr(decision.reviewed_at)}</p>}
      <Rationale text={friendlyEvidenceText(decision.rationale_tr)}/>
      {decision.stale_review_exists&&!reviewed&&<p className={styles.stale}>Önceki insan kararı farklı kanıta aitti. Bu kanıt için yeni inceleme gerekiyor.</p>}
      <div className={styles.links}>
        <Link href={`/funds/${code}`}>Fon sayfası</Link>
        <Link href={`/funds/${code}#karar`}>Karar bölümü</Link>
      </div>
      <EvidenceLinks decision={decision}/>
    </div>
    <div className={styles.side}>
      {reviewed?<>
        <dl className={styles.record}>
          <div><dt>İlk öneri (korunur)</dt><dd>{decisionLabel(decision.original_value)}</dd></div>
          <div><dt>İnceleyen</dt><dd>{decision.reviewer_email??'Kayıtlı değil'}</dd></div>
          <div><dt>Gerekçe</dt><dd>{decision.review_reason??'Öneri gerekçe yazılmadan kabul edildi.'}</dd></div>
        </dl>
        <details className={styles.again}><summary>Yeni inceleme ekle</summary><ReviewActions decision={decision} onSaved={onSaved}/></details>
      </>:<ReviewActions decision={decision} onSaved={onSaved}/>}
    </div>
  </article>;
}
