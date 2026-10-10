'use client';

import {FormEvent, useEffect, useId, useRef, useState} from 'react';
import {createPortal} from 'react-dom';
import {csrfCookie} from '@/lib/client';
import {ChatAnswer, ChatError, readChatAnswer} from '@/lib/chat-stream';
import {useReady} from '@/lib/use-ready';
import './ChatPanel.css';

type Message = {role: 'user'|'assistant'; content: string; evidence_ids: string[]};
const toolLabels: Record<string, string> = {
  search_funds: 'Fon kataloğu inceleniyor…',
  get_fund_profile: 'Fon bilgileri inceleniyor…',
  get_signals: 'Detektör kanıtları inceleniyor…',
  get_decision: 'Kayıtlı karar inceleniyor…',
};
const errorLabels: Record<string, string> = {
  AI_OFF: 'Sohbet şu anda kapalı. Bir model yanıtı üretilmedi.',
  KEY_UNAVAILABLE: 'Sohbet hizmeti şu anda kullanılamıyor. Bir model yanıtı üretilmedi.',
  OPENAI_KEY_UNAVAILABLE: 'Sohbet hizmeti şu anda kullanılamıyor. Bir model yanıtı üretilmedi.',
  QUESTION_REJECTED: 'Soru kabul edilmedi. Kişisel bilgileri ve hesap bilgilerini çıkarıp yalnızca fon kanıtlarını sorun.',
  CHAT_DAILY_LIMIT: 'Günlük soru sınırına ulaştınız. Yeni bir soru için yarını bekleyin.',
  DAILY_LIMIT: 'Günlük soru sınırına ulaştınız. Yeni bir soru için yarını bekleyin.',
  BUDGET_EXHAUSTED: 'Sohbet kullanım sınırına ulaştı. Bir model yanıtı üretilmedi.',
  BUDGET_LIMIT: 'Sohbet kullanım sınırına ulaştı. Bir model yanıtı üretilmedi.',
  BUDGET_UNAVAILABLE: 'Sohbet kullanım sınırına ulaştı. Bir model yanıtı üretilmedi.',
  AUTHENTICATION_REQUIRED: 'Oturumunuz sona erdi. Yeniden giriş yapın.',
  CSRF_REJECTED: 'Oturum doğrulanamadı. Sayfayı yenileyip yeniden deneyin.',
  ANSWER_INVALID: 'Model yanıtı kanıt denetiminden geçemedi ve gösterilmedi.',
  VALIDATION_FAILED: 'Model yanıtı kanıt denetiminden geçemedi ve gösterilmedi.',
  STREAM_INVALID: 'Sohbet yanıtı doğrulanamadı ve gösterilmedi.',
  STREAM_INTERRUPTED: 'Bağlantı yanıt tamamlanmadan kesildi. Yeni bir soru gönderebilirsiniz.',
  MODEL_CALL_FAILED: 'Sohbet hizmetine şu anda erişilemiyor. Bir model yanıtı gösterilmedi.',
  CHAT_VALIDATION_OR_CALL_LIMIT: 'Doğrulanmış bir yanıt üretilemedi. Daha dar bir soru gönderebilirsiniz.',
  CHAT_TIMEOUT: 'Sohbet yanıt süresini aştı. Yeni bir soru gönderebilirsiniz.',
  CHAT_TOOL_LIMIT: 'Soru, izin verilen kanıt sorgusu sınırını aştı. Daha dar bir soru sorun.',
  THREAD_BUSY: 'Önceki sorunuz işleniyor. Yanıtı bekleyip yeniden deneyin.',
};

export default function ChatPanel({code,drawer=false,evidenceId,contextTitle,initialQuestion=''}: {code: string;drawer?:boolean;evidenceId?:string;contextTitle?:string;initialQuestion?:string}) {
  const [question, setQuestion] = useState(initialQuestion);
  const [open,setOpen]=useState(false);
  const ready=useReady();
  const [messages, setMessages] = useState<Message[]>([]);
  const [threadId, setThreadId] = useState<string|null>(null);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState('');
  const [error, setError] = useState('');
  const request = useRef<AbortController|null>(null);
  const input = useRef<HTMLTextAreaElement|null>(null);
  const dialog=useRef<HTMLElement|null>(null), trigger=useRef<HTMLButtonElement|null>(null);
  const noticeId = useId(), limitId = useId();
  useEffect(() => () => request.current?.abort(), []);
  useEffect(()=>{request.current?.abort();setMessages([]);setThreadId(null);setQuestion(initialQuestion);setError('');setOpen(false);},[code,evidenceId,initialQuestion]);
  useEffect(()=>{
    if(!drawer||!open)return;
    const original=document.body.style.overflow;
    document.body.style.overflow='hidden';
    const previous=document.activeElement as HTMLElement|null;
    function controls(){return Array.from(dialog.current?.querySelectorAll<HTMLElement>('button:not(:disabled),a[href],textarea:not(:disabled),[tabindex="0"]')??[]).filter(node=>node.getClientRects().length>0);}
    if(input.current&&!input.current.disabled)input.current.focus();
    else controls()[0]?.focus();
    function keys(event:KeyboardEvent){
      if(event.key==='Escape'){event.preventDefault();setOpen(false);return;}
      if(event.key!=='Tab')return;
      const available=controls();if(!available.length)return;
      const first=available[0],last=available[available.length-1];
      if(!dialog.current?.contains(document.activeElement)){event.preventDefault();(event.shiftKey?last:first).focus();}
      else if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}
      else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}
    }
    document.addEventListener('keydown',keys);
    return()=>{document.body.style.overflow=original;document.removeEventListener('keydown',keys);previous?.focus();};
  },[drawer,open,busy]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = question.trim();
    if (!text || busy || request.current) return;
    setBusy(true); setError(''); setProgress('Kanıtlar hazırlanıyor…');
    const controller = new AbortController();
    request.current = controller;
    const timeout = window.setTimeout(() => controller.abort(), 60000);
    let submitted = false;
    try {
      const response = await fetch('/api/p/chat', {
        method: 'POST', headers: {'Content-Type': 'application/json', 'Accept': 'text/event-stream', 'X-CSRF-Token': csrfCookie()},
        body: JSON.stringify({fund_code: code, question: text, thread_id: threadId,...(evidenceId?{evidence_id:evidenceId}:{})}),
        cache: 'no-store', signal: controller.signal,
      });
      if (response.ok) {
        setMessages(previous => [...previous, {role: 'user', content: text, evidence_ids: []}]);
        setQuestion(''); submitted = true;
      }
      const result: ChatAnswer = await readChatAnswer(response, name => setProgress(toolLabels[name]));
      setThreadId(result.thread_id);
      setMessages(previous => [...previous, {role: 'assistant', content: result.content, evidence_ids: result.evidence_ids}]);
    } catch (failure) {
      const code = failure instanceof ChatError ? failure.code : failure instanceof DOMException && failure.name === 'AbortError' ? 'STREAM_INTERRUPTED' : 'CHAT_UNAVAILABLE';
      setError(errorLabels[code] ?? 'Sohbet şu anda kullanılamıyor. Bir model yanıtı gösterilmedi.');
      if (submitted) setQuestion(text);
    } finally {
      window.clearTimeout(timeout); request.current = null;
      setBusy(false); setProgress(''); input.current?.focus();
    }
  }

  const content=<article ref={dialog} className={`chat-panel${drawer?' chat-drawer':''}`} role={drawer?'dialog':undefined} aria-modal={drawer?true:undefined} aria-labelledby={`chat-title-${code}`}>
    <div className="chat-heading"><h2 id={`chat-title-${code}`}>{drawer?(evidenceId?'Bu gelişmeyle ilgili sorular':'Fon kanıtlarıyla sohbet'):'Kanıtlarla sohbet'}</h2>{drawer&&<button type="button" className="chat-close" aria-label="Sohbeti kapat" onClick={()=>setOpen(false)}><img src="/design/evidence/close.svg" width={20} height={20} alt=""/></button>}</div>
    {drawer&&<div className="chat-context"><span>{code}</span><p>{contextTitle??'Detektör kanıtları ve kaynak sınırları'}</p></div>}
    <p className="notice" id={noticeId}>Yazdığınız sorular OpenAI&apos;a iletilir. Yalnızca türetilmiş fon kanıtları kullanılır. Kişisel bilgileri, hesap bilgilerini veya anahtarları paylaşmayın. Yanıtlar yatırım tavsiyesi değildir.</p>
    <div className="chat-transcript" role="log" aria-label="Sohbet mesajları" aria-live="polite" aria-relevant="additions" aria-busy={busy}>
      {messages.length === 0 ? <p className="muted">Bu fonun detektör bulgularını ve kanıt sınırlarını sorabilirsiniz.</p> : messages.map((message, index) => <div className={`chat-message chat-${message.role}`} key={index}>
        <strong>{message.role === 'user' ? 'Siz' : 'BlackSwan'}</strong>
        <p>{message.content}</p>
        {message.evidence_ids.length > 0 && <details><summary>Yanıtın kanıt bağlantıları</summary>{message.evidence_ids.map((id,index) => <p className="evidence-id" key={id}><a href={`/developments/${encodeURIComponent(id)}?fund=${code}`}>Kaynak kanıtı {index+1}</a></p>)}</details>}
      </div>)}
    </div>
    <p role="status" className="chat-progress">{progress}</p>
    {error && <p role="alert" className="notice">{error}</p>}
    {drawer&&<div className="chat-suggestions">{['Bu kanıt neyi gösteriyor?','Hangi bilgiler eksik?'].map(value=><button type="button" key={value} disabled={busy} onClick={()=>{setQuestion(value);input.current?.focus();}}><img src="/design/evidence/question.svg" width={16} height={16} alt=""/>{value}</button>)}</div>}
    <form onSubmit={submit} className="chat-form">
      <label>Fon kanıtları hakkında sorunuz<textarea ref={input} value={question} onChange={event => setQuestion(event.target.value)} maxLength={1200} rows={drawer?1:3} required disabled={busy} aria-describedby={`${noticeId} ${limitId}`}/></label>
      <div className="chat-controls"><p className="muted" id={limitId}>{question.length}/1200 karakter</p><button disabled={busy || !question.trim()} aria-label="Soruyu gönder">{drawer?<img src="/design/evidence/send.svg" width={16} height={16} alt=""/>:busy ? 'Yanıt bekleniyor…' : 'Soruyu gönder'}</button></div>
    </form>
  </article>;
  if(!drawer)return content;
  return <><article className="chat-launcher"><h2>Bu kanıtla ilgili sorular</h2><p>Yanıtlar fonun türetilmiş kanıtlarına dayanır. Yeterli veri yoksa bu durum belirtilir.</p><button ref={trigger} type="button" disabled={!ready} className="chat-open" onClick={()=>setOpen(true)}>Kanıtlarla sohbet</button><div className="chat-suggestions">{['Bu kanıt neyi gösteriyor?','Hangi bilgiler eksik?'].map(value=><button disabled={!ready} type="button" key={value} onClick={()=>{setQuestion(value);setOpen(true);}}><img src="/design/evidence/question.svg" width={16} height={16} alt=""/>{value}</button>)}</div></article>{open&&createPortal(<div className="chat-layer" data-design-node="29:904"><div className="chat-backdrop" onClick={()=>setOpen(false)}/>{content}</div>,document.body)}</>;
}
