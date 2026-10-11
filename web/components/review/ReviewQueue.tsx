'use client';
import Link from 'next/link';
import {useRef,useState} from 'react';
import ReviewCard from './ReviewCard';
import {decisionLabel,decisionOrder,proposalSource,proposalSourceDescriptions,proposalSourceOrder,proposalSourceTitles,type Decision} from './review-logic';
import styles from './review.module.css';

/** One tab of the review queue, with a decision-value filter and a confirmation that survives the refresh. */
export default function ReviewQueue({items,reviewedTab}:{items:Decision[];reviewedTab:boolean}){
  const [filter,setFilter]=useState<string|null>(null),[notice,setNotice]=useState('');
  const noticeRef=useRef<HTMLParagraphElement>(null);
  const counts=decisionOrder.map(value=>[value,items.filter(item=>item.effective_value===value).length] as const).filter(([,count])=>count>0);
  const active=filter&&counts.some(([value])=>value===filter)?filter:null;
  const shown=active?items.filter(item=>item.effective_value===active):items;
  function saved(message:string){setNotice(message);requestAnimationFrame(()=>noticeRef.current?.focus());}
  return <div className={styles.queue}>
    <p ref={noticeRef} tabIndex={-1} className={notice?styles.notice:'sr-only'} role="status">{notice&&<>{notice} {reviewedTab?'Kayıt güncellendi.':<>Karar <Link href="/review?durum=incelenen">İncelenen</Link> sekmesine taşındı.</>}</>}</p>
    {items.length===100&&<p className={styles.queueCount}>Bu görünümde 100 kayıt gösteriliyor. Ajan ekibinin önerileri önce yer alır.</p>}
    {counts.length>1&&<div className={styles.filters} role="group" aria-label="Karara göre süz">
      <button type="button" className={styles.chip} aria-pressed={!active} onClick={()=>setFilter(null)}>Tümü <span>{items.length}</span></button>
      {counts.map(([value,count])=><button type="button" key={value} className={styles.chip} aria-pressed={active===value} onClick={()=>setFilter(value)}>{decisionLabel(value)} <span>{count}</span></button>)}
    </div>}
    {!reviewedTab&&items.length>0&&!items.some(item=>proposalSource(item)==='team')&&<p className={styles.sourceNote}>Bu kuyrukta henüz Raportör önerisi yok. <Link href="/ekip">Ekibin çalışmasını görün</Link>.</p>}
    {shown.length?<div className={styles.list}>{proposalSourceOrder.map(source=>{
      const group=shown.filter(decision=>proposalSource(decision)===source);
      return group.length>0&&<section key={source} className={styles.sourceGroup} aria-label={proposalSourceTitles[source]}>
        <div className={styles.sourceHeading}><h2>{proposalSourceTitles[source]} <span className={styles.count}>{group.length}</span></h2><p>{proposalSourceDescriptions[source]}</p></div>
        {group.map(decision=><ReviewCard key={decision.packet_sha256??decision.fund_code} decision={decision} onSaved={saved}/>)}</section>;
    })}</div>
      :reviewedTab?<div className={styles.empty}><p>Bu analiz için henüz insan incelemesi kaydedilmedi.</p><Link href="/review">Bekleyen önerilere dönün</Link></div>
      :<div className={styles.empty}><p>İnceleme bekleyen öneri yok.</p><Link href="/ekip">Ajan ekibinin çalışmasını görün</Link></div>}
  </div>;
}
