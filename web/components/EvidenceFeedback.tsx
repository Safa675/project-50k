'use client';
import {useState} from 'react';
import {post} from '@/lib/client';
import {useReady} from '@/lib/use-ready';
export default function EvidenceFeedback({evidenceId,initial}:{evidenceId:string;initial:boolean|null}){
  const [choice,setChoice]=useState(initial),[busy,setBusy]=useState(false),[message,setMessage]=useState('');
  const ready=useReady();
  async function vote(helpful:boolean){setBusy(true);setMessage('');try{const response=await post('/evidence-feedback',{evidence_id:evidenceId,helpful});if(!response.ok)throw new Error();setChoice(helpful);setMessage('Geri bildiriminiz kaydedildi.');}catch{setMessage('Geri bildirim kaydedilemedi. Yeniden deneyin.');}finally{setBusy(false);}}
  return <div className="evidence-feedback"><span>Bu açıklama faydalı oldu mu?</span><div><button type="button" aria-pressed={choice===true} disabled={!ready||busy} onClick={()=>vote(true)}>Evet</button><button type="button" aria-pressed={choice===false} disabled={!ready||busy} onClick={()=>vote(false)}>Hayır</button></div>{message&&<p role="status">{message}</p>}</div>;
}
