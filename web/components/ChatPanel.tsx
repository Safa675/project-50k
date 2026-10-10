'use client';

import {FormEvent, useEffect, useId, useRef, useState} from 'react';
import {createPortal} from 'react-dom';
import {csrfCookie,dateTr} from '@/lib/client';
import {ChatAnswer, ChatError, readChatAnswer} from '@/lib/chat-stream';
import {ChatThread,StoredChatMessage,parseChatHistory,parseChatThreads,shouldSendOnEnter} from '@/lib/chat-history';
import {sourceTime} from '@/lib/fund-display';
import {useReady} from '@/lib/use-ready';
import './ChatPanel.css';

type Message = StoredChatMessage;
const toolLabels: Record<string, string> = {
  search_funds: 'Fon kataloğu inceleniyor…',
  get_fund_profile: 'Fon bilgileri inceleniyor…',
  get_signals: 'Kaynak bilgileri inceleniyor…',
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
  THREAD_NOT_FOUND:'Bu sohbet bu varlık ve tarih için bulunamadı.',
  HISTORY_UNAVAILABLE:'Kayıtlı sohbetler alınamadı. Yeniden yükleyin.',
  HISTORY_INVALID:'Kayıtlı sohbet yanıtı doğrulanamadı. Yeniden yükleyin.',
  HISTORY_SCOPE_CHANGED:'Analiz tarihi değişti. Sohbet geçmişini yeniden yükleyin.',
};

export default function ChatPanel({code,drawer=false,evidenceId,contextTitle,initialQuestion='',analysisScopeKey}: {code: string;drawer?:boolean;evidenceId?:string;contextTitle?:string;initialQuestion?:string;analysisScopeKey?:string}) {
  const [question, setQuestion] = useState(initialQuestion);
  const [open,setOpen]=useState(false);
  const ready=useReady();
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft,setDraft]=useState('');
  const [threadId, setThreadId] = useState<string|null>(null);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState('');
  const [error, setError] = useState('');
  const [threads,setThreads]=useState<ChatThread[]>([]);
  const [scope,setScope]=useState<string|undefined>(analysisScopeKey);
  const [historyLoading,setHistoryLoading]=useState(true),[historyLoaded,setHistoryLoaded]=useState(false);
  const [historyPending,setHistoryPending]=useState(false),[newConversation,setNewConversation]=useState(false);
  const [hasOlder,setHasOlder]=useState(false),[olderLoading,setOlderLoading]=useState(false);
  const [moreThreads,setMoreThreads]=useState(false),[threadOffset,setThreadOffset]=useState(0),[threadsLoading,setThreadsLoading]=useState(false);
  const [historyVersion,setHistoryVersion]=useState(0);
  const request = useRef<AbortController|null>(null);
  const historyRequest=useRef<AbortController|null>(null),contextVersion=useRef(0),composing=useRef(false);
  const input = useRef<HTMLTextAreaElement|null>(null);
  const dialog=useRef<HTMLElement|null>(null), trigger=useRef<HTMLButtonElement|null>(null);
  const noticeId = useId(), limitId = useId();
  async function restore(selected?:string){
    historyRequest.current?.abort();const controller=new AbortController();historyRequest.current=controller;
    const version=contextVersion.current;let loaded=false;
    const timeout=window.setTimeout(()=>{if(version===contextVersion.current&&historyRequest.current===controller){setError(errorLabels.HISTORY_UNAVAILABLE);setHistoryLoading(false);setHistoryLoaded(false);}controller.abort();},15000);
    setHistoryLoading(true);setHistoryLoaded(false);setError('');
    try{
      const response=await fetch(`/api/p/chat/threads?fund_code=${encodeURIComponent(code)}`,{cache:'no-store',signal:controller.signal});
      if(!response.ok)throw new ChatError(response.status===401?'AUTHENTICATION_REQUIRED':'HISTORY_UNAVAILABLE');
      const saved=parseChatThreads(await response.json(),code,analysisScopeKey);
      if(controller.signal.aborted||version!==contextVersion.current)return;
      const chosen=selected??saved.items[0]?.thread_id;
      let items:Message[]=[];
      if(chosen){
        const detail=await fetch(`/api/p/chat/${chosen}?fund_code=${encodeURIComponent(code)}`,{cache:'no-store',signal:controller.signal});
        if(!detail.ok)throw new ChatError(detail.status===404?'THREAD_NOT_FOUND':detail.status===401?'AUTHENTICATION_REQUIRED':'HISTORY_UNAVAILABLE');
        items=parseChatHistory(await detail.json(),code,chosen,saved.analysis_scope_key);
      }
      if(controller.signal.aborted||version!==contextVersion.current)return;
      setThreads(saved.items);setScope(saved.analysis_scope_key);setThreadId(chosen??null);setMessages(items);
      setMoreThreads(saved.items.length===20);setThreadOffset(saved.items.length);
      setHasOlder(items.length===60);
      setHistoryPending(items.some(item=>item.role==='user'&&item.status==='PENDING'));setNewConversation(false);loaded=true;
    }catch(failure){
      if(controller.signal.aborted||version!==contextVersion.current)return;
      const name=failure instanceof ChatError?failure.code:'HISTORY_UNAVAILABLE';
      setMessages([]);setThreadId(null);setHistoryPending(false);setError(errorLabels[name]??errorLabels.HISTORY_UNAVAILABLE);
    }finally{
      window.clearTimeout(timeout);
      if(!controller.signal.aborted&&version===contextVersion.current){setHistoryLoading(false);setHistoryLoaded(loaded);}
      if(historyRequest.current===controller)historyRequest.current=null;
    }
  }
  async function loadOlderThreads(){
    if(!scope||threadsLoading)return;
    historyRequest.current?.abort();const controller=new AbortController(),version=contextVersion.current;
    historyRequest.current=controller;setThreadsLoading(true);
    const timeout=window.setTimeout(()=>controller.abort(),15000);
    try{
      const response=await fetch(`/api/p/chat/threads?fund_code=${encodeURIComponent(code)}&offset=${threadOffset}`,{cache:'no-store',signal:controller.signal});
      if(!response.ok)throw new ChatError('HISTORY_UNAVAILABLE');
      const saved=parseChatThreads(await response.json(),code,scope);
      if(controller.signal.aborted||version!==contextVersion.current)return;
      setThreads(previous=>[...previous,...saved.items.filter(item=>!previous.some(old=>old.thread_id===item.thread_id))]);
      setThreadOffset(value=>value+saved.items.length);setMoreThreads(saved.items.length===20);
    }catch{if(version===contextVersion.current)setError(errorLabels.HISTORY_UNAVAILABLE);}
    finally{window.clearTimeout(timeout);if(version===contextVersion.current)setThreadsLoading(false);if(historyRequest.current===controller)historyRequest.current=null;}
  }
  async function loadOlder(){
    const oldest=messages.find(item=>item.message_id)?.message_id;
    if(!threadId||!scope||!oldest||olderLoading)return;
    const controller=new AbortController(),version=contextVersion.current;historyRequest.current=controller;setOlderLoading(true);
    const timeout=window.setTimeout(()=>{if(version===contextVersion.current&&historyRequest.current===controller){setError(errorLabels.HISTORY_UNAVAILABLE);setOlderLoading(false);}controller.abort();},15000);
    try{
      const response=await fetch(`/api/p/chat/${threadId}?fund_code=${encodeURIComponent(code)}&before_message_id=${oldest}`,{cache:'no-store',signal:controller.signal});
      if(!response.ok)throw new ChatError('HISTORY_UNAVAILABLE');
      const items=parseChatHistory(await response.json(),code,threadId,scope);
      if(controller.signal.aborted||version!==contextVersion.current)return;
      setMessages(previous=>[...items,...previous.filter(item=>!item.message_id||!items.some(older=>older.message_id===item.message_id))]);setHasOlder(items.length===60);
    }catch(failure){if(!controller.signal.aborted&&version===contextVersion.current)setError(errorLabels.HISTORY_UNAVAILABLE);}
    finally{window.clearTimeout(timeout);if(version===contextVersion.current)setOlderLoading(false);if(historyRequest.current===controller)historyRequest.current=null;}
  }
  useEffect(()=>()=>{request.current?.abort();historyRequest.current?.abort();contextVersion.current++;},[]);
  useEffect(()=>{
    contextVersion.current++;request.current?.abort();request.current=null;historyRequest.current?.abort();
    setMessages([]);setDraft('');setThreadId(null);setThreads([]);setQuestion(initialQuestion);setError('');setOpen(false);
    setBusy(false);setProgress('');setHistoryPending(false);setHistoryLoaded(false);setScope(analysisScopeKey);
    setHasOlder(false);setOlderLoading(false);
    setMoreThreads(false);setThreadOffset(0);setThreadsLoading(false);
    void restore();
  },[code,analysisScopeKey,historyVersion]);
  useEffect(()=>{if(initialQuestion)setQuestion(initialQuestion);},[initialQuestion]);
  useEffect(()=>{const changed=()=>setHistoryVersion(value=>value+1);window.addEventListener('blackswan-analysis-change',changed);return()=>window.removeEventListener('blackswan-analysis-change',changed);},[]);
  useEffect(()=>{
    if(!historyPending||busy||historyLoading||!threadId)return;
    const timer=window.setTimeout(()=>void restore(threadId),2000);return()=>window.clearTimeout(timer);
  },[historyPending,busy,historyLoading,threadId]);
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
  },[drawer,open,busy,historyPending,historyLoading]);

  function startNew(){if(busy)return;historyRequest.current?.abort();setMessages([]);setDraft('');setThreadId(null);setHistoryPending(false);setHasOlder(false);setOlderLoading(false);setNewConversation(true);setError('');input.current?.focus();}

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = question.trim();
    if (!text || busy || historyPending || !historyLoaded || request.current) return;
    setBusy(true); setDraft(''); setError(''); setProgress('Sorunuz için kaynaklar inceleniyor…');
    const controller = new AbortController();
    const version=contextVersion.current,userKey=crypto.randomUUID();
    const current=()=>version===contextVersion.current&&!controller.signal.aborted;
    request.current = controller;
    const timeout = window.setTimeout(() => controller.abort(), 60000);
    let submitted = false;
    try {
      const response = await fetch('/api/p/chat', {
        method: 'POST', headers: {'Content-Type': 'application/json', 'Accept': 'text/event-stream', 'X-CSRF-Token': csrfCookie()},
        body: JSON.stringify({fund_code: code, question: text, thread_id: threadId,...(evidenceId?{evidence_id:evidenceId}:{}),...(newConversation?{new_thread:true}:{})}),
        cache: 'no-store', signal: controller.signal,
      });
      if(!current())return;
      if (response.ok) {
        setMessages(previous => [...previous, {role: 'user', content: text, evidence_ids: [],clientKey:userKey,status:'PENDING'}]);
        setQuestion(''); submitted = true;
      }
      const result: ChatAnswer = await readChatAnswer(response, name => {if(current())setProgress(toolLabels[name]);},
        paragraph=>{if(current()){setDraft(previous=>previous?previous+'\n\n'+paragraph.content:paragraph.content);setProgress('Yanıt yazılıyor…');}},
        ()=>{if(current()){setDraft('');setProgress('Yanıt kontrol ediliyor…');}},
        started=>{if(current()){if(scope&&scope!==started.analysis_scope_key)throw new ChatError('HISTORY_SCOPE_CHANGED');setThreadId(started.thread_id);setNewConversation(false);}});
      if(!current())return;
      setThreadId(result.thread_id);
      setNewConversation(false);
      setDraft('');
      setMessages(previous => [...previous.map(item=>item.clientKey===userKey?{...item,status:'VALID' as const}:item), {role: 'assistant', content: result.content, evidence_ids: result.evidence_ids,evidence_labels:result.evidence_labels,status:'VALID'}]);
      const now=new Date().toISOString();
      setThreads(previous=>{const existing=previous.find(item=>item.thread_id===result.thread_id);return [{thread_id:result.thread_id,created_at:existing?.created_at??now,last_message_at:now,message_count:(existing?.message_count??0)+2,title:existing?.title||text.slice(0,120)},...previous.filter(item=>item.thread_id!==result.thread_id)].slice(0,20);});
    } catch (failure) {
      if(version!==contextVersion.current)return;
      const code = failure instanceof ChatError ? failure.code : failure instanceof DOMException && failure.name === 'AbortError' ? 'STREAM_INTERRUPTED' : 'CHAT_UNAVAILABLE';
      setError(errorLabels[code] ?? 'Sohbet şu anda kullanılamıyor. Bir model yanıtı gösterilmedi.');
      if (submitted){setQuestion(text);setMessages(previous=>previous.map(item=>item.clientKey===userKey?{...item,status:'FAILED'}:item));}
    } finally {
      window.clearTimeout(timeout);if(request.current===controller)request.current=null;
      if(version===contextVersion.current){setBusy(false);setDraft('');setProgress('');input.current?.focus();}
    }
  }

  const content=<article ref={dialog} className={`chat-panel${drawer?' chat-drawer':''}`} role={drawer?'dialog':undefined} aria-modal={drawer?true:undefined} aria-labelledby={`chat-title-${code}`}>
    <div className="chat-heading"><h2 id={`chat-title-${code}`}>{drawer?(evidenceId?'Bu gelişmeyle ilgili sorular':'Fon kanıtlarıyla sohbet'):'Kanıtlarla sohbet'}</h2>{drawer&&<button type="button" className="chat-close" aria-label="Sohbeti kapat" onClick={()=>setOpen(false)}><img src="/design/evidence/close.svg" width={20} height={20} alt=""/></button>}</div>
    {drawer&&<div className="chat-context"><span>{code}</span><p>{contextTitle??'Fonla ilgili gelişmeler ve kaynaklar'}</p></div>}
    <div className="chat-history-controls"><label>Kayıtlı sohbet<select aria-label="Kayıtlı sohbet" value={threadId??''} disabled={busy||historyLoading||threadsLoading||olderLoading||!historyLoaded} onChange={event=>{if(event.target.value==='__older_threads__')void loadOlderThreads();else if(event.target.value)void restore(event.target.value);else startNew();}}><option value="">Yeni sohbet</option>{threadId&&!threads.some(thread=>thread.thread_id===threadId)&&<option value={threadId}>Geçerli sohbet</option>}{threads.map(thread=><option key={thread.thread_id} value={thread.thread_id}>{thread.title||`Sohbet · ${sourceTime(thread.created_at)}`}</option>)}{moreThreads&&<option value="__older_threads__">Daha eski sohbetleri yükle</option>}</select></label><button type="button" disabled={busy||historyLoading||threadsLoading||!historyLoaded} onClick={startNew}>Yeni sohbet</button></div>
    {scope&&<p className="chat-scope-label">{scope==='live'?'Güncel görünümdeki sohbet':`Seçili tarih: ${dateTr(scope.slice(5))}`}</p>}
    <p className="chat-privacy" id={noticeId}>Yazdığınız sorular OpenAI&apos;a iletilir. Kişisel veya hesap bilgilerinizi paylaşmayın. Yanıtlar yatırım tavsiyesi değildir.</p>
    <div className="chat-transcript" role="log" aria-label="Sohbet mesajları" aria-live="polite" aria-relevant="additions" aria-busy={busy}>
      {hasOlder&&<button type="button" className="chat-history-older" disabled={olderLoading||busy||historyLoading} onClick={()=>void loadOlder()}>{olderLoading?'Önceki mesajlar yükleniyor…':'Önceki mesajları göster'}</button>}
      {messages.length === 0 ? <p className="muted">{historyLoading?'Kayıtlı sohbetler yükleniyor…':historyLoaded?'Bu fonda nelerin değiştiğini, fiyat bilgilerinin ne anlattığını ve kaynaklarda nelerin eksik olduğunu sorabilirsiniz.':'Kayıtlı sohbetler henüz alınamadı.'}</p> : messages.map((message, index) => <div className={`chat-message chat-${message.role}`} key={message.message_id??message.clientKey??index}>
        <strong>{message.role === 'user' ? 'Siz' : 'BlackSwan'}</strong>
        <p>{message.content}</p>
        {message.created_at&&<time className="chat-message-time" dateTime={message.created_at}>{sourceTime(message.created_at)}</time>}
        {message.role==='user'&&['FAILED','INTERRUPTED'].includes(message.status??'')&&<small className="chat-message-state">Bu soru için tamamlanmış bir yanıt yok.</small>}
        {message.evidence_ids.length > 0 && <details><summary>Yanıtın kaynakları</summary>{message.evidence_ids.map((id,index) => <p key={id}><a href={`/developments/${encodeURIComponent(id)}?fund=${code}`}>{message.evidence_labels?.[id]??`Kaynak bilgisi ${index+1}`}</a></p>)}</details>}
      </div>)}
      {draft&&<div className="chat-message chat-assistant chat-streaming"><strong>BlackSwan</strong><p>{draft}</p></div>}
    </div>
    <p role="status" className="chat-progress">{progress||(historyPending?'Önceki sorunuzun yanıtı bekleniyor…':'')}</p>
    {error && <p role="alert" className="notice">{error}</p>}
    {!historyLoading&&!historyLoaded&&<button type="button" className="chat-history-retry" onClick={()=>void restore()}>Sohbet geçmişini yeniden yükle</button>}
    {drawer&&<div className="chat-suggestions">{['Bu fonla ilgili ne değişti?','Fiyat bilgisi neden eksik?'].map(value=><button type="button" key={value} disabled={busy} onClick={()=>{setQuestion(value);input.current?.focus();}}><img src="/design/evidence/question.svg" width={16} height={16} alt=""/>{value}</button>)}</div>}
    <form onSubmit={submit} className="chat-form">
      <label>Fon kanıtları hakkında sorunuz<textarea ref={input} value={question} onChange={event => setQuestion(event.target.value)} onCompositionStart={()=>{composing.current=true;}} onCompositionEnd={()=>{composing.current=false;}} onKeyDown={event=>{if(shouldSendOnEnter({key:event.key,shiftKey:event.shiftKey,isComposing:composing.current||event.nativeEvent.isComposing,keyCode:event.nativeEvent.keyCode})){event.preventDefault();if(!busy&&!historyPending&&historyLoaded&&question.trim())event.currentTarget.form?.requestSubmit();}}} maxLength={1200} rows={drawer?1:3} required disabled={busy||historyPending||!historyLoaded} aria-describedby={`${noticeId} ${limitId}`}/></label>
      <div className="chat-controls"><p className="muted" id={limitId}>{question.length}/1200 karakter · Enter gönderir, Shift+Enter yeni satır</p><button disabled={busy||historyPending||!historyLoaded||!question.trim()} aria-label="Soruyu gönder">{drawer?<img src="/design/evidence/send.svg" width={16} height={16} alt=""/>:busy ? 'Yanıt bekleniyor…' : 'Soruyu gönder'}</button></div>
    </form>
  </article>;
  if(!drawer)return content;
  return <><article className="chat-launcher"><h2>Fon hakkında sorularınız</h2><p>Gelişmeleri ve fiyat bilgilerinin ne anlama geldiğini kaynaklarıyla birlikte sorun.</p><button ref={trigger} type="button" disabled={!ready} className="chat-open" onClick={()=>setOpen(true)}>Kanıtlarla sohbet</button><div className="chat-suggestions">{['Bu fonla ilgili ne değişti?','Fiyat bilgisi neden eksik?'].map(value=><button disabled={!ready} type="button" key={value} onClick={()=>{setQuestion(value);setOpen(true);}}><img src="/design/evidence/question.svg" width={16} height={16} alt=""/>{value}</button>)}</div></article>{open&&createPortal(<div className="chat-layer" data-design-node="29:904"><div className="chat-backdrop" onClick={()=>setOpen(false)}/>{content}</div>,document.body)}</>;
}
