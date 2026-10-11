'use client';

import {useState, type RefObject} from 'react';
import {post} from '@/lib/client';
import {AGENTS_REFRESH, caseStatusLabel, parseInvestigation, requestError} from '@/lib/agents';
import type {PageNoteState} from './hooks';
import ReporterConversation, {type ConversationHandle} from './ReporterConversation';

type RequestState = {status: 'idle' | 'busy' | 'done' | 'error'; message?: string; caseId?: string};

export default function ReporterTab({fundCode, evidenceId, path, scopeKey, note, active, conversation, onOpenCase}: {
  fundCode: string | null; evidenceId?: string; path: string; scopeKey?: string; note: PageNoteState; active: boolean;
  conversation: RefObject<ConversationHandle | null>; onOpenCase: (caseId: string) => void;
}) {
  const [request, setRequest] = useState<RequestState>({status: 'idle'});
  const data = note.data;
  const openCase = data?.case && data.case.status !== 'closed' ? data.case : null;
  async function investigate() {
    if (!fundCode || request.status === 'busy') return;
    setRequest({status: 'busy'});
    try {
      const response = await post('/agents/requests', {fund_code: fundCode, kind: 'investigate'});
      if (!response.ok) {
        let code: string | null = null;
        try {const body = await response.json(); code = typeof body?.error === 'string' ? body.error : typeof body?.detail === 'string' ? body.detail : null;} catch {/* An empty error body keeps the status message. */}
        setRequest({status: 'error', message: requestError(response.status, code)});
        return;
      }
      const result = parseInvestigation(await response.json());
      setRequest({status: 'done', caseId: result.case_id});
      window.dispatchEvent(new Event(AGENTS_REFRESH));
    } catch {
      setRequest({status: 'error', message: requestError(0)});
    }
  }
  return <div className="ag-reporter">
    <aside className="ag-brief" aria-label="Bu sayfa için Raportör notu">
      <p className="ag-eyebrow">{fundCode ? `${fundCode} · bu sayfa` : 'Bu sayfa'}</p>
      {note.status === 'loading' && !data && <p className="ag-muted" role="status">Raportör sayfadaki kayıtlara bakıyor…</p>}
      {note.status === 'error' && <p className="ag-muted">Bu sayfa için not şu anda hazırlanamadı. Sohbet kullanılabilir.</p>}
      {data?.note_tr && <p className="ag-brief-note">{data.note_tr}</p>}
      {data?.warning_tr && <p className="ag-brief-warning" role="note"><svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 9v4"/><path d="M12 17h.01"/><path d="M10.3 3.9 2.6 17.2a2 2 0 0 0 1.7 3h15.4a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z"/></svg><span>{data.warning_tr}</span></p>}
      {note.status === 'ready' && !data?.note_tr && !data?.warning_tr && <p className="ag-muted">Bu sayfa için ayrıca not edilecek bir kayıt yok.</p>}
      {data && data.suggestions.length > 0 && <div className="ag-suggestions" role="group" aria-label="Önerilen sorular">
        {data.suggestions.map(item => <button key={item.prompt_tr} type="button" className="ag-chip" onClick={() => conversation.current?.ask(item.prompt_tr)}>
          <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/></svg>{item.label_tr}</button>)}
      </div>}
      {openCase && <div className="ag-brief-case"><span>Ekibin bu fondaki vakası: <strong>{caseStatusLabel(openCase.status)}</strong></span>
        <button type="button" className="ag-link" onClick={() => onOpenCase(openCase.case_id)}>Vakanın akışını izle</button></div>}
      {fundCode && <div className="ag-request">
        <button type="button" className="ag-primary" disabled={request.status === 'busy'} onClick={() => void investigate()}>
          {request.status === 'busy' ? 'İstek gönderiliyor…' : openCase ? 'İncelemeyi öne al' : 'Ekipten inceleme iste'}</button>
        <p className="ag-muted">{openCase ? 'Vaka kullanıcı isteği önceliğine alınır ve sıradaki işlerin önüne geçer.' :
          'Raportör isteğinizi ekibin sırasına ekler. Nöbetçi, Hipotezci, Şüpheci ve Doğrulayıcı sırayla çalışır; sonuç insan incelemesine sunulur.'}</p>
        <p className="ag-request-state" role="status">{request.status === 'done' ? 'İsteğiniz ekibin sırasına alındı.' : ''}</p>
        {request.status === 'done' && request.caseId && <button type="button" className="ag-link" onClick={() => onOpenCase(request.caseId!)}>Vakanın akışını izle</button>}
        {request.status === 'error' && <p className="ag-alert" role="alert">{request.message}</p>}
      </div>}
    </aside>
    <ReporterConversation key={`${fundCode ?? 'general'}:${scopeKey ?? ''}`} fundCode={fundCode} evidenceId={evidenceId} path={path}
      scopeKey={scopeKey} active={active} handle={conversation}/>
  </div>;
}
