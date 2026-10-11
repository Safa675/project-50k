'use client';

import {FormEvent, useEffect, useId, useImperativeHandle, useRef, useState, type Ref} from 'react';
import {csrfCookie} from '@/lib/client';
import {AGENTS_REFRESH, clockTime} from '@/lib/agents';
import {ChatAnswer, ChatError, readChatAnswer} from '@/lib/chat-stream';
import {ChatThread, StoredChatMessage, chatAssetQuery, parseChatHistory, parseChatThreads, shouldSendOnEnter} from '@/lib/chat-history';
import Mascot from './Mascot';

const toolLabels: Record<string, string> = {
  search_funds: 'Raportör fon kataloğuna bakıyor…',
  get_fund_profile: 'Raportör fon bilgilerini okuyor…',
  get_signals: 'Raportör hesaplanmış kanıtları okuyor…',
  get_decision: 'Raportör kayıtlı kararı okuyor…',
  get_case_status: 'Raportör ekibin vaka kaydına bakıyor…',
  request_investigation: 'Raportör isteğinizi ekibin sırasına ekliyor…',
};
const errorLabels: Record<string, string> = {
  AI_OFF: 'Raportör şu anda yanıt veremiyor: yapay zekâ kapalı. Bir model yanıtı üretilmedi.',
  KEY_UNAVAILABLE: 'Raportör hizmeti şu anda kullanılamıyor. Bir model yanıtı üretilmedi.',
  OPENAI_KEY_UNAVAILABLE: 'Raportör hizmeti şu anda kullanılamıyor. Bir model yanıtı üretilmedi.',
  QUESTION_REJECTED: 'Soru kabul edilmedi. Kişisel bilgileri, hesap bilgilerini ve rakamları çıkarıp yeniden sorun.',
  CHAT_DAILY_LIMIT: 'Günlük soru sınırına ulaştınız. Yeni bir soru için yarını bekleyin.',
  DAILY_LIMIT: 'Günlük soru sınırına ulaştınız. Yeni bir soru için yarını bekleyin.',
  BUDGET_EXHAUSTED: 'Raportörün kullanım bütçesi doldu. Bir model yanıtı üretilmedi.',
  BUDGET_LIMIT: 'Raportörün kullanım bütçesi doldu. Bir model yanıtı üretilmedi.',
  BUDGET_UNAVAILABLE: 'Raportörün kullanım bütçesi doldu. Bir model yanıtı üretilmedi.',
  AUTHENTICATION_REQUIRED: 'Oturumunuz sona erdi. Yeniden giriş yapın.',
  CSRF_REJECTED: 'Oturum doğrulanamadı. Sayfayı yenileyip yeniden deneyin.',
  ANSWER_INVALID: 'Yanıt kanıt denetiminden geçemedi ve gösterilmedi.',
  VALIDATION_FAILED: 'Yanıt kanıt denetiminden geçemedi ve gösterilmedi.',
  STREAM_INVALID: 'Yanıt doğrulanamadı ve gösterilmedi.',
  STREAM_INTERRUPTED: 'Bağlantı yanıt tamamlanmadan kesildi. Yeni bir soru gönderebilirsiniz.',
  MODEL_CALL_FAILED: 'Raportöre şu anda ulaşılamıyor. Bir model yanıtı gösterilmedi.',
  CHAT_VALIDATION_OR_CALL_LIMIT: 'Doğrulanmış bir yanıt üretilemedi. Daha dar bir soru gönderebilirsiniz.',
  CHAT_TIMEOUT: 'Yanıt süresi aşıldı. Yeni bir soru gönderebilirsiniz.',
  CHAT_TOOL_LIMIT: 'Soru, izin verilen kanıt sorgusu sınırını aştı. Daha dar bir soru sorun.',
  THREAD_BUSY: 'Önceki sorunuz işleniyor. Yanıtı bekleyip yeniden deneyin.',
  THREAD_NOT_FOUND: 'Bu sohbet bu sayfa ve tarih için bulunamadı.',
  FUND_NOT_FOUND: 'Bu fon için sohbet açılamadı.',
  HISTORY_UNAVAILABLE: 'Kayıtlı sohbetler alınamadı. Yeniden yükleyin.',
  HISTORY_INVALID: 'Kayıtlı sohbet yanıtı doğrulanamadı. Yeniden yükleyin.',
  HISTORY_SCOPE_CHANGED: 'İnceleme tarihi değişti. Sohbet geçmişini yeniden yükleyin.',
};
const PAGE = 60, THREADS = 20;

export type ConversationHandle = {ask: (text: string) => void; focus: () => void};

export default function ReporterConversation({fundCode, evidenceId, path, scopeKey, active, handle}: {
  fundCode: string | null; evidenceId?: string; path: string; scopeKey?: string; active: boolean; handle?: Ref<ConversationHandle>;
}) {
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState<StoredChatMessage[]>([]);
  const [draft, setDraft] = useState('');
  const [threadId, setThreadId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState('');
  const [error, setError] = useState('');
  const [threads, setThreads] = useState<ChatThread[]>([]);
  const [scope, setScope] = useState<string | undefined>(scopeKey);
  const [historyLoading, setHistoryLoading] = useState(false), [historyLoaded, setHistoryLoaded] = useState(false);
  const [historyPending, setHistoryPending] = useState(false), [newConversation, setNewConversation] = useState(false);
  const [hasOlder, setHasOlder] = useState(false), [olderLoading, setOlderLoading] = useState(false);
  const [moreThreads, setMoreThreads] = useState(false), [threadOffset, setThreadOffset] = useState(0), [threadsLoading, setThreadsLoading] = useState(false);
  const [started, setStarted] = useState(false);
  const request = useRef<AbortController | null>(null);
  const historyRequest = useRef<AbortController | null>(null), version = useRef(0), composing = useRef(false);
  const input = useRef<HTMLTextAreaElement | null>(null), transcript = useRef<HTMLDivElement | null>(null);
  const pendingAsk = useRef<string | null>(null);
  const noticeId = useId(), hintId = useId(), selectId = useId();
  const asset = chatAssetQuery(fundCode);
  const join = (base: string, extra: string) => `${base}${base.includes('?') ? '&' : '?'}${extra}`;
  const withAsset = (base: string) => asset ? join(base, asset) : base;

  async function restore(selected?: string) {
    historyRequest.current?.abort();
    const controller = new AbortController(), current = version.current;
    historyRequest.current = controller;
    let loaded = false;
    const timeout = window.setTimeout(() => controller.abort(), 15000);
    setHistoryLoading(true); setHistoryLoaded(false); setError('');
    try {
      const response = await fetch(withAsset('/api/p/chat/threads'), {cache: 'no-store', signal: controller.signal});
      if (!response.ok) throw new ChatError(response.status === 401 ? 'AUTHENTICATION_REQUIRED' : 'HISTORY_UNAVAILABLE');
      const saved = parseChatThreads(await response.json(), fundCode, scopeKey);
      if (controller.signal.aborted || current !== version.current) return;
      const chosen = selected ?? saved.items[0]?.thread_id;
      let items: StoredChatMessage[] = [];
      if (chosen) {
        const detail = await fetch(withAsset(`/api/p/chat/${chosen}`), {cache: 'no-store', signal: controller.signal});
        if (!detail.ok) throw new ChatError(detail.status === 404 ? 'THREAD_NOT_FOUND' : detail.status === 401 ? 'AUTHENTICATION_REQUIRED' : 'HISTORY_UNAVAILABLE');
        items = parseChatHistory(await detail.json(), fundCode, chosen, saved.analysis_scope_key);
      }
      if (controller.signal.aborted || current !== version.current) return;
      setThreads(saved.items); setScope(saved.analysis_scope_key); setThreadId(chosen ?? null); setMessages(items);
      setMoreThreads(saved.items.length === THREADS); setThreadOffset(saved.items.length); setHasOlder(items.length === PAGE);
      setHistoryPending(items.some(item => item.role === 'user' && item.status === 'PENDING')); setNewConversation(false);
      loaded = true;
    } catch (failure) {
      if (current !== version.current) return;
      const name = failure instanceof ChatError ? failure.code : 'HISTORY_UNAVAILABLE';
      setMessages([]); setThreadId(null); setHistoryPending(false);
      setError(errorLabels[name] ?? errorLabels.HISTORY_UNAVAILABLE);
    } finally {
      window.clearTimeout(timeout);
      if (current === version.current) {setHistoryLoading(false); setHistoryLoaded(loaded);}
      if (historyRequest.current === controller) historyRequest.current = null;
    }
  }
  async function loadOlderThreads() {
    if (!scope || threadsLoading) return;
    const controller = new AbortController(), current = version.current;
    historyRequest.current?.abort(); historyRequest.current = controller; setThreadsLoading(true);
    const timeout = window.setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(withAsset(`/api/p/chat/threads?offset=${threadOffset}`), {cache: 'no-store', signal: controller.signal});
      if (!response.ok) throw new ChatError('HISTORY_UNAVAILABLE');
      const saved = parseChatThreads(await response.json(), fundCode, scope);
      if (controller.signal.aborted || current !== version.current) return;
      setThreads(previous => [...previous, ...saved.items.filter(item => !previous.some(old => old.thread_id === item.thread_id))]);
      setThreadOffset(value => value + saved.items.length); setMoreThreads(saved.items.length === THREADS);
    } catch {if (current === version.current) setError(errorLabels.HISTORY_UNAVAILABLE);}
    finally {window.clearTimeout(timeout); if (current === version.current) setThreadsLoading(false); if (historyRequest.current === controller) historyRequest.current = null;}
  }
  async function loadOlder() {
    const oldest = messages.find(item => item.message_id)?.message_id;
    if (!threadId || !scope || !oldest || olderLoading) return;
    const controller = new AbortController(), current = version.current;
    historyRequest.current = controller; setOlderLoading(true);
    const timeout = window.setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(withAsset(`/api/p/chat/${threadId}?before_message_id=${oldest}`), {cache: 'no-store', signal: controller.signal});
      if (!response.ok) throw new ChatError('HISTORY_UNAVAILABLE');
      const items = parseChatHistory(await response.json(), fundCode, threadId, scope);
      if (controller.signal.aborted || current !== version.current) return;
      setMessages(previous => [...items, ...previous.filter(item => !item.message_id || !items.some(older => older.message_id === item.message_id))]);
      setHasOlder(items.length === PAGE);
    } catch {if (!controller.signal.aborted && current === version.current) setError(errorLabels.HISTORY_UNAVAILABLE);}
    finally {window.clearTimeout(timeout); if (current === version.current) setOlderLoading(false); if (historyRequest.current === controller) historyRequest.current = null;}
  }

  // History loads the first time the Raportör tab is shown, then stays in memory while the panel lives.
  useEffect(() => {if (active && !started) {setStarted(true); void restore();}}, [active, started]);
  useEffect(() => () => {request.current?.abort(); historyRequest.current?.abort(); version.current++;}, []);
  useEffect(() => {
    function changed() {
      version.current++; request.current?.abort(); request.current = null; historyRequest.current?.abort();
      setMessages([]); setDraft(''); setThreadId(null); setThreads([]); setBusy(false); setProgress(''); setHistoryLoaded(false); setStarted(false);
    }
    window.addEventListener('blackswan-analysis-change', changed);
    return () => window.removeEventListener('blackswan-analysis-change', changed);
  }, []);
  useEffect(() => {
    if (!historyPending || busy || historyLoading || !threadId) return;
    const timer = window.setTimeout(() => void restore(threadId), 2000);
    return () => window.clearTimeout(timer);
  }, [historyPending, busy, historyLoading, threadId]);
  useEffect(() => {
    // The transcript scrolls itself on wide panels; on narrow sheets the whole Raportör view scrolls instead.
    const node = transcript.current;
    if (!node) return;
    const scroller = node.scrollHeight > node.clientHeight + 1 ? node : node.closest<HTMLElement>('.ag-view');
    if (scroller && (messages.length || draft)) scroller.scrollTop = scroller.scrollHeight;
  }, [messages.length, draft, progress]);
  useEffect(() => {
    if (pendingAsk.current && historyLoaded && !busy && !historyPending) {
      const text = pendingAsk.current;
      pendingAsk.current = null;
      void send(text);
    }
  }, [historyLoaded, busy, historyPending]);
  useImperativeHandle(handle, () => ({
    ask(text: string) {
      if (busy || historyPending) {setQuestion(text); input.current?.focus(); return;}
      if (!historyLoaded) {pendingAsk.current = text; setQuestion(text); return;}
      void send(text);
    },
    focus() {input.current?.focus();},
  }));

  function startNew() {
    if (busy) return;
    historyRequest.current?.abort();
    setMessages([]); setDraft(''); setThreadId(null); setHistoryPending(false); setHasOlder(false); setOlderLoading(false);
    setNewConversation(true); setError(''); input.current?.focus();
  }

  async function send(raw: string) {
    const text = raw.trim();
    if (!text || busy || historyPending || !historyLoaded || request.current) return;
    setBusy(true); setDraft(''); setError(''); setProgress('Raportör sorunuz için kaynakları inceliyor…');
    const controller = new AbortController(), current = version.current, key = crypto.randomUUID();
    const live = () => current === version.current && !controller.signal.aborted;
    request.current = controller;
    const timeout = window.setTimeout(() => controller.abort(), 60000);
    let submitted = false, queued = false;
    try {
      const response = await fetch('/api/p/chat', {
        method: 'POST', cache: 'no-store', signal: controller.signal,
        headers: {'Content-Type': 'application/json', 'Accept': 'text/event-stream', 'X-CSRF-Token': csrfCookie()},
        body: JSON.stringify({fund_code: fundCode, question: text, thread_id: threadId, page_context: {path, fund_code: fundCode},
          ...(evidenceId ? {evidence_id: evidenceId} : {}), ...(newConversation ? {new_thread: true} : {})}),
      });
      if (!live()) return;
      if (response.ok) {
        setMessages(previous => [...previous, {role: 'user', content: text, evidence_ids: [], clientKey: key, status: 'PENDING'}]);
        setQuestion(''); submitted = true;
      }
      const result: ChatAnswer = await readChatAnswer(response,
        name => {if (live()) {setProgress(toolLabels[name] ?? 'Raportör kaynakları inceliyor…'); if (name === 'request_investigation') queued = true;}},
        paragraph => {if (live()) {setDraft(previous => previous ? `${previous}\n\n${paragraph.content}` : paragraph.content); setProgress('Raportör yazıyor…');}},
        () => {if (live()) {setDraft(''); setProgress('Raportör yanıtı yeniden denetliyor…');}},
        thread => {if (live()) {if (scope && scope !== thread.analysis_scope_key) throw new ChatError('HISTORY_SCOPE_CHANGED'); setThreadId(thread.thread_id); setNewConversation(false);}});
      if (!live()) return;
      setThreadId(result.thread_id); setNewConversation(false); setDraft('');
      setMessages(previous => [...previous.map(item => item.clientKey === key ? {...item, status: 'VALID' as const} : item),
        {role: 'assistant', content: result.content, evidence_ids: result.evidence_ids, evidence_labels: result.evidence_labels, status: 'VALID', created_at: new Date().toISOString()}]);
      const now = new Date().toISOString();
      setThreads(previous => {
        const existing = previous.find(item => item.thread_id === result.thread_id);
        return [{thread_id: result.thread_id, created_at: existing?.created_at ?? now, last_message_at: now, message_count: (existing?.message_count ?? 0) + 2,
          title: existing?.title || text.slice(0, 120)}, ...previous.filter(item => item.thread_id !== result.thread_id)].slice(0, THREADS);
      });
    } catch (failure) {
      if (current !== version.current) return;
      const code = failure instanceof ChatError ? failure.code : failure instanceof DOMException && failure.name === 'AbortError' ? 'STREAM_INTERRUPTED' : 'CHAT_UNAVAILABLE';
      setError(errorLabels[code] ?? 'Raportör şu anda yanıt veremiyor. Bir model yanıtı gösterilmedi.');
      if (submitted) {setQuestion(text); setMessages(previous => previous.map(item => item.clientKey === key ? {...item, status: 'FAILED'} : item));}
    } finally {
      window.clearTimeout(timeout);
      if (request.current === controller) request.current = null;
      if (current === version.current) {setBusy(false); setDraft(''); setProgress(''); input.current?.focus();}
      if (queued) window.dispatchEvent(new Event(AGENTS_REFRESH));
    }
  }
  function submit(event: FormEvent<HTMLFormElement>) {event.preventDefault(); void send(question);}

  const locked = busy || historyPending || !historyLoaded;
  const sourceHref = (id: string) => `/developments/${encodeURIComponent(id)}${fundCode ? `?fund=${fundCode}` : ''}`;
  return <div className="ag-chat">
    <div className="ag-chat-bar">
      <label className="ag-chat-threads" htmlFor={selectId}><span className="sr-only">Kayıtlı sohbet</span>
        <select id={selectId} value={threadId ?? ''} disabled={busy || historyLoading || threadsLoading || olderLoading || !historyLoaded}
          onChange={event => {if (event.target.value === '__older__') void loadOlderThreads(); else if (event.target.value) void restore(event.target.value); else startNew();}}>
          <option value="">{threads.length ? 'Yeni sohbet' : 'İlk sohbet'}</option>
          {threadId && !threads.some(thread => thread.thread_id === threadId) && <option value={threadId}>Geçerli sohbet</option>}
          {threads.map(thread => <option key={thread.thread_id} value={thread.thread_id}>{thread.title || `Sohbet · ${clockTime(thread.created_at)}`}</option>)}
          {moreThreads && <option value="__older__">Daha eski sohbetleri yükle</option>}
        </select>
      </label>
      <button type="button" className="ag-ghost" disabled={busy || historyLoading || threadsLoading || !historyLoaded} onClick={startNew}>Yeni sohbet</button>
    </div>
    <div className="ag-transcript" ref={transcript} role="log" aria-label="Raportör ile sohbet" aria-live="polite" aria-relevant="additions" aria-busy={busy}>
      {hasOlder && <button type="button" className="ag-ghost ag-older" disabled={olderLoading || busy || historyLoading} onClick={() => void loadOlder()}>{olderLoading ? 'Önceki mesajlar yükleniyor…' : 'Önceki mesajları göster'}</button>}
      {messages.length === 0 && !draft ? <div className="ag-chat-empty">
        <Mascot size={44}/>
        <p>{historyLoading ? 'Kayıtlı sohbet yükleniyor…' : historyLoaded ?
          (fundCode ? 'Bu fonla ilgili gelişmeleri, ekibin incelemesini veya fiyat bilgisinin ne anlattığını sorabilirsiniz. Yanıtlar kaynaklarıyla gelir.' :
            'Ekibin çalışmasını, açık vakaları veya yöntemin nasıl işlediğini sorabilirsiniz. Bir fon sayfasındayken o fona özel sohbet açılır.') :
          'Kayıtlı sohbet henüz alınamadı.'}</p>
      </div> : messages.map((message, index) => <div key={message.message_id ?? message.clientKey ?? index} className={`ag-msg ag-msg-${message.role}`}>
        {message.role === 'assistant' && <span className="ag-msg-avatar" aria-hidden="true"><Mascot size={24}/></span>}
        <div className="ag-msg-body">
          <strong className="ag-msg-author">{message.role === 'user' ? 'Siz' : 'Raportör'}</strong>
          <p>{message.content}</p>
          {message.role === 'user' && ['FAILED', 'INTERRUPTED'].includes(message.status ?? '') && <small className="ag-msg-state">Bu soru için tamamlanmış bir yanıt yok.</small>}
          {message.evidence_ids.length > 0 && <details className="ag-sources"><summary>Yanıtın kaynakları</summary><ul>{message.evidence_ids.map((id, position) =>
            <li key={id}><a href={sourceHref(id)}>{message.evidence_labels?.[id] ?? `Kaynak bilgisi ${position + 1}`}</a></li>)}</ul></details>}
          {message.created_at && <time className="ag-msg-time" dateTime={message.created_at}>{clockTime(message.created_at)}</time>}
        </div>
      </div>)}
      {draft && <div className="ag-msg ag-msg-assistant is-streaming"><span className="ag-msg-avatar" aria-hidden="true"><Mascot size={24}/></span>
        <div className="ag-msg-body"><strong className="ag-msg-author">Raportör</strong><p>{draft}</p></div></div>}
    </div>
    <p role="status" className="ag-chat-progress">{progress || (historyPending ? 'Önceki sorunuzun yanıtı bekleniyor…' : '')}</p>
    {error && <p role="alert" className="ag-alert">{error}</p>}
    {!historyLoading && !historyLoaded && started && <button type="button" className="ag-ghost" onClick={() => void restore()}>Sohbet geçmişini yeniden yükle</button>}
    <form className="ag-composer" onSubmit={submit}>
      <label className="sr-only" htmlFor={`${selectId}-input`}>Raportöre sorunuz</label>
      <textarea id={`${selectId}-input`} ref={input} value={question} rows={1} maxLength={1200} required disabled={locked}
        placeholder={fundCode ? 'Bu fon hakkında Raportöre sorun' : 'Raportöre sorun'} aria-describedby={`${noticeId} ${hintId}`}
        onChange={event => setQuestion(event.target.value)}
        onCompositionStart={() => {composing.current = true;}} onCompositionEnd={() => {composing.current = false;}}
        onKeyDown={event => {
          if (shouldSendOnEnter({key: event.key, shiftKey: event.shiftKey, isComposing: composing.current || event.nativeEvent.isComposing, keyCode: event.nativeEvent.keyCode})) {
            event.preventDefault();
            if (!locked && question.trim()) event.currentTarget.form?.requestSubmit();
          }
        }}/>
      <button type="submit" className="ag-send" disabled={locked || !question.trim()} aria-label="Soruyu gönder">
        <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 19V5"/><path d="m5.5 11.5 6.5-6.5 6.5 6.5"/></svg>
      </button>
    </form>
    <p className="ag-chat-foot"><span id={hintId}>Enter gönderir, Shift+Enter yeni satır ekler{question.length > 900 ? ` · ${question.length.toLocaleString('tr-TR')}/1.200` : ''}.</span>{' '}
      <span id={noticeId}>Sorularınız OpenAI&apos;a iletilir; kişisel veya hesap bilgisi paylaşmayın. Yanıtlar yatırım tavsiyesi değildir.</span></p>
  </div>;
}
