'use client';
import {FormEvent,useId,useRef,useState} from 'react';
import {useRouter} from 'next/navigation';
import {post} from '@/lib/client';
import {canAccept,decisionLabel,defaultOverride,submitReview,type Decision,type ReviewAction} from './review-logic';
import styles from './review.module.css';

/** Accept in one step; change or reject with a required reason. Saves through the CSRF-protected client helper. */
export default function ReviewActions({decision,onSaved}:{decision:Decision;onSaved?:(message:string)=>void}){
  const router=useRouter(),id=useId();
  const [mode,setMode]=useState<ReviewAction|null>(null),[override,setOverride]=useState(()=>defaultOverride(decision));
  const [reason,setReason]=useState(''),[busy,setBusy]=useState<ReviewAction|null>(null);
  const [error,setError]=useState(''),[saved,setSaved]=useState('');
  const changeRef=useRef<HTMLButtonElement>(null),rejectRef=useRef<HTMLButtonElement>(null);
  if(decision.decision_id===null)return <p className={styles.actionNote}>Bu kanıt için henüz incelenecek bir öneri yok.</p>;
  const acceptable=canAccept(decision);
  function open(next:ReviewAction){setMode(next);setError('');setSaved('');}
  function close(){const trigger=mode==='OVERRIDE'?changeRef:rejectRef;setMode(null);setError('');setReason('');trigger.current?.focus();}
  async function send(action:ReviewAction){
    setBusy(action);setError('');setSaved('');
    const result=await submitReview(post,decision,action,action==='OVERRIDE'?override:null,action==='ACCEPT'?'':reason);
    setBusy(null);
    if(!result.ok){setError(result.message);return;}
    setSaved(result.message);setMode(null);setReason('');
    onSaved?.(result.message);
    router.refresh();
  }
  function submit(event:FormEvent<HTMLFormElement>){event.preventDefault();if(mode)void send(mode);}
  const reasonId=`${id}-reason`,errorId=`${id}-error`;
  return <div className={styles.actions}>
    <div className={styles.buttons} role="group" aria-label="İnceleme işlemi">
      {acceptable&&<button type="button" className={styles.accept} onClick={()=>void send('ACCEPT')} disabled={busy!==null} aria-busy={busy==='ACCEPT'}>{busy==='ACCEPT'?'Kaydediliyor…':'Kabul et'}</button>}
      <button type="button" ref={changeRef} className={styles.secondary} aria-expanded={mode==='OVERRIDE'} aria-controls={mode==='OVERRIDE'?`${id}-form`:undefined} onClick={()=>mode==='OVERRIDE'?close():open('OVERRIDE')} disabled={busy!==null||decision.allowed_options.length===0}>Değiştir</button>
      <button type="button" ref={rejectRef} className={styles.secondary} aria-expanded={mode==='REJECT'} aria-controls={mode==='REJECT'?`${id}-form`:undefined} onClick={()=>mode==='REJECT'?close():open('REJECT')} disabled={busy!==null}>Reddet</button>
    </div>
    {!mode&&<p className={styles.actionNote}>{acceptable?'Kabul için gerekçe gerekmez. Değiştirme ve ret gerekçeyle kaydedilir.':'Geçerli bir öneri olmadığı için yalnızca değiştirilebilir veya reddedilebilir.'}</p>}
    {mode&&<form id={`${id}-form`} className={styles.form} onSubmit={submit} noValidate>
      {mode==='OVERRIDE'?<label className={styles.field}>Yeni karar<select value={override} onChange={event=>setOverride(event.target.value)} autoFocus>{decision.allowed_options.map(option=><option key={option} value={option}>{decisionLabel(option)}</option>)}</select></label>
        :<p className={styles.actionNote}>Reddedilen öneri etkin karar olmaz; karar “Karar verilmedi” olarak görünür.</p>}
      <label className={styles.field} htmlFor={reasonId}>Gerekçe <span className={styles.required}>(zorunlu)</span></label>
      <textarea id={reasonId} className={styles.textarea} value={reason} onChange={event=>setReason(event.target.value)} maxLength={1000} rows={3} required aria-invalid={Boolean(error)&&!reason.trim()} aria-describedby={error?errorId:undefined} autoFocus={mode==='REJECT'}/>
      <div className={styles.formButtons}>
        <button type="submit" className={styles.accept} disabled={busy!==null} aria-busy={busy===mode}>{busy===mode?'Kaydediliyor…':mode==='OVERRIDE'?'Değişikliği kaydet':'Reddi kaydet'}</button>
        <button type="button" className={styles.ghost} onClick={close} disabled={busy!==null}>Vazgeç</button>
      </div>
    </form>}
    {error&&<p id={errorId} className={styles.error} role="alert">{error}</p>}
    <p className={styles.saved} role="status">{saved}</p>
  </div>;
}
