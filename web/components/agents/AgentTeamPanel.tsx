'use client';

import Link from 'next/link';
import {useEffect, useId, useRef, useState, type KeyboardEvent as ReactKeyboardEvent, type RefObject} from 'react';
import type {User} from '@/lib/auth';
import {type AgentRole, ROLE_META, type TeamSnapshot, budgetView, relativeTime, scopeLabel, usd} from '@/lib/agents';
import AgentQueue from './AgentQueue';
import {CaseTimeline, RoleWorkspace} from './AgentWorkspace';
import type {AgentFeed, PageNoteState} from './hooks';
import Mascot from './Mascot';
import ReporterTab from './ReporterTab';
import type {ConversationHandle} from './ReporterConversation';
import TeamStage, {StageTicker as Ticker} from './TeamStage';

export type PanelTab = 'team' | 'reporter' | 'queue' | 'detail';
export type PanelDetail = {kind: 'agent'; role: AgentRole} | {kind: 'case'; caseId: string};

export function BudgetMeter({team}: {team: TeamSnapshot | null}) {
  const view = budgetView(team?.budget ?? null);
  if (!view) return <div className="ag-budget is-unknown"><span className="ag-label">Günlük bütçe</span><strong>{team ? 'Bilgi yok' : '—'}</strong></div>;
  return <div className={`ag-budget${view.exhausted ? ' is-exhausted' : ''}`}>
    <span className="ag-label">Günlük bütçe</span>
    <span className="ag-meter" role="meter" aria-label="Günlük yapay zekâ bütçesi" aria-valuemin={0} aria-valuemax={view.cap} aria-valuenow={Math.min(view.spent, view.cap)}
      aria-valuetext={`${usd(view.spent)} harcandı, ${usd(view.reserved)} ayrıldı, günlük sınır ${usd(view.cap)}`}>
      <span className="ag-meter-spent" style={{width: `${(view.spentRatio * 100).toFixed(1)}%`}}/>
      <span className="ag-meter-reserved" style={{width: `${(view.reservedRatio * 100).toFixed(1)}%`}}/>
    </span>
    <strong>{view.label}</strong>
  </div>;
}

export default function AgentTeamPanel({state, onClose, onClosed, user, feed, note, path, fundCode, evidenceId, compact, reducedMotion,
  tab, setTab, detail, openDetail, conversation, returnFocus}: {
  state: 'open' | 'closing' | 'closed'; onClose: () => void; onClosed: () => void; user: User; feed: AgentFeed; note: PageNoteState;
  path: string; fundCode: string | null; evidenceId?: string; compact: boolean; reducedMotion: boolean; tab: PanelTab;
  setTab: (tab: PanelTab) => void; detail: PanelDetail | null; openDetail: (detail: PanelDetail | null) => void;
  conversation: RefObject<ConversationHandle | null>; returnFocus: RefObject<HTMLElement | null>;
}) {
  const panel = useRef<HTMLDivElement | null>(null);
  const titleId = useId(), baseId = useId();
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {setNow(Date.now());}, [feed.team, feed.updatedAt]);
  const open = state === 'open';
  const team = feed.team;
  const scope = scopeLabel(team?.scope ?? user.analysis_context?.scope_key ?? null);
  const tabs: {id: PanelTab; label: string}[] = [
    ...(compact ? [{id: 'team' as const, label: 'Ekip'}] : []),
    {id: 'reporter', label: 'Raportör'},
    {id: 'queue', label: 'Sıra'},
    ...(detail ? [{id: 'detail' as const, label: detail.kind === 'agent' ? ROLE_META[detail.role].name : 'Vaka akışı'}] : []),
  ];
  const active = tabs.some(item => item.id === tab) ? tab : 'reporter';

  // Focus trap, Esc to close and body scroll lock while the dialog is open.
  useEffect(() => {
    if (!open) return;
    const original = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const focusables = () => Array.from(panel.current?.querySelectorAll<HTMLElement>('button:not(:disabled),a[href],textarea:not(:disabled),select:not(:disabled),input:not(:disabled),summary,[tabindex="0"]') ?? [])
      .filter(node => node.getClientRects().length > 0 && !node.closest('[hidden]'));
    const frame = requestAnimationFrame(() => {
      if (panel.current?.contains(document.activeElement)) return;
      // On touch-sized layouts the composer is not focused automatically, so the keyboard does not cover the sheet.
      const composer = compact ? null : panel.current?.querySelector<HTMLTextAreaElement>('.ag-composer textarea:not(:disabled)');
      (active === 'reporter' && composer ? composer : panel.current?.querySelector<HTMLElement>('[role="tab"][aria-selected="true"]') ?? focusables()[0])?.focus();
    });
    function keys(event: KeyboardEvent) {
      if (event.key === 'Escape') {event.preventDefault(); onClose(); return;}
      if (event.key !== 'Tab') return;
      const nodes = focusables();
      if (!nodes.length) return;
      const first = nodes[0], last = nodes[nodes.length - 1];
      if (!panel.current?.contains(document.activeElement)) {event.preventDefault(); (event.shiftKey ? last : first).focus();}
      else if (event.shiftKey && document.activeElement === first) {event.preventDefault(); last.focus();}
      else if (!event.shiftKey && document.activeElement === last) {event.preventDefault(); first.focus();}
    }
    document.addEventListener('keydown', keys);
    return () => {cancelAnimationFrame(frame); document.body.style.overflow = original; document.removeEventListener('keydown', keys);};
  }, [open]);
  useEffect(() => {
    if (state !== 'closing') return;
    const timer = window.setTimeout(() => {onClosed(); returnFocus.current?.focus();}, reducedMotion ? 0 : 200);
    return () => window.clearTimeout(timer);
  }, [state, reducedMotion]);

  function tabKeys(event: ReactKeyboardEvent<HTMLButtonElement>) {
    const index = tabs.findIndex(item => item.id === active);
    const next = event.key === 'ArrowRight' ? (index + 1) % tabs.length : event.key === 'ArrowLeft' ? (index - 1 + tabs.length) % tabs.length :
      event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : -1;
    if (next < 0) return;
    event.preventDefault();
    setTab(tabs[next].id);
    requestAnimationFrame(() => panel.current?.querySelector<HTMLElement>(`#${CSS.escape(`${baseId}-tab-${tabs[next].id}`)}`)?.focus());
  }
  const select = (role: AgentRole) => {openDetail({kind: 'agent', role}); setTab('detail');};
  const openCase = (caseId: string) => {openDetail({kind: 'case', caseId}); setTab('detail');};
  const reviewHref = user.role === 'viewer' ? '/method#evidence' : '/review';
  const stage = <TeamStage team={team} status={feed.teamStatus} reducedMotion={reducedMotion} onSelect={select}
    selected={detail?.kind === 'agent' ? detail.role : null} onTalk={() => setTab('reporter')} reviewHref={reviewHref}/>;
  const liveText = feed.teamStatus === 'loading' && !team ? 'Bağlanıyor…' : !team ? 'Ekibin durumu alınamıyor' :
    feed.stale ? 'Bağlantı yeniden deneniyor' : `Canlı · ${feed.updatedAt ? relativeTime(new Date(feed.updatedAt).toISOString(), now) : 'az önce'} güncellendi`;

  return <div className="ag-layer" data-state={state} hidden={state === 'closed'}>
    <div className="ag-backdrop" onClick={onClose} aria-hidden="true"/>
    <div ref={panel} className="ag-panel" role="dialog" aria-modal="true" aria-labelledby={titleId} id="ag-team-panel">
      <div className="ag-handle" aria-hidden="true"/>
      <div className="ag-head">
        <div className="ag-head-title">
          <span className="ag-head-mascot" aria-hidden="true"><Mascot size={30}/></span>
          <div><h2 id={titleId}>Ajan ekibi · 7/24</h2>
            <p className="ag-head-sub"><span className={`ag-live${team && !feed.stale ? ' is-live' : ''}`} aria-hidden="true"/>{liveText}</p></div>
        </div>
        <div className="ag-head-meta">
          <div className="ag-head-date"><span className="ag-label">İnceleme tarihi</span><strong>{scope.date ?? scope.mode}</strong>{scope.date && <span className="ag-muted">{scope.mode}</span>}</div>
          <BudgetMeter team={team}/>
        </div>
        <button type="button" className="ag-close" aria-label="Ajan ekibi panelini kapat" onClick={onClose}>
          <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
        </button>
      </div>
      {!compact && <div className="ag-stage-wrap">{stage}<Ticker team={team} now={now}/>
        {!team && feed.teamStatus !== 'loading' && <div className="ag-stage-error" role="status"><span>Ekibin canlı durumu şu anda alınamıyor. Bağlantı kendiliğinden yeniden denenecek.</span>
          <button type="button" className="ag-ghost" onClick={feed.refresh}>Şimdi dene</button></div>}</div>}
      {!team && compact && feed.teamStatus !== 'loading' && active !== 'team' && <div className="ag-stage-error is-inline" role="status"><span>Ekibin canlı durumu şu anda alınamıyor.</span>
        <button type="button" className="ag-ghost" onClick={feed.refresh}>Şimdi dene</button></div>}
      <div className="ag-tabs" role="tablist" aria-label="Panel bölümleri">
        {tabs.map(item => <button key={item.id} id={`${baseId}-tab-${item.id}`} type="button" role="tab" aria-selected={active === item.id}
          aria-controls={`${baseId}-panel`} tabIndex={active === item.id ? 0 : -1} className={`ag-tab${active === item.id ? ' is-active' : ''}`}
          onClick={() => setTab(item.id)} onKeyDown={tabKeys}>
          {item.id === 'reporter' && <Mascot size={18}/>}{item.label}
          {item.id === 'queue' && team && team.counts.queued + team.counts.running > 0 && <span className="ag-count">{(team.counts.queued + team.counts.running).toLocaleString('tr-TR')}</span>}
        </button>)}
        {active === 'detail' && <button type="button" className="ag-tab-close" aria-label="Çalışma alanını kapat" onClick={() => {openDetail(null); setTab('reporter');}}>
          <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg></button>}
      </div>
      <div className="ag-body" role="tabpanel" id={`${baseId}-panel`} aria-labelledby={`${baseId}-tab-${active}`}>
        {active === 'team' && compact && <div className="ag-view ag-view-team"><div className="ag-stage-wrap is-compact">{stage}<Ticker team={team} now={now}/>
          {!team && feed.teamStatus !== 'loading' && <div className="ag-stage-error" role="status"><span>Ekibin canlı durumu şu anda alınamıyor.</span><button type="button" className="ag-ghost" onClick={feed.refresh}>Şimdi dene</button></div>}</div></div>}
        <div hidden={active !== 'reporter'} className="ag-view">
          <ReporterTab fundCode={fundCode} evidenceId={evidenceId} path={path} scopeKey={user.analysis_context?.scope_key} note={note}
            active={active === 'reporter' && state !== 'closed'} conversation={conversation} onOpenCase={openCase}/>
        </div>
        {active === 'queue' && <div className="ag-view"><AgentQueue queue={feed.queue} status={feed.queueStatus} team={team} onOpenCase={openCase}/></div>}
        {active === 'detail' && detail && <div className="ag-view">
          {detail.kind === 'agent' ? <><RoleWorkspace role={detail.role} onOpenCase={openCase}/>
            <p className="ag-detail-foot"><Link href={`/ekip/${ROLE_META[detail.role].slug}`}>Çalışma alanını tam sayfada aç</Link></p></> :
            <CaseTimeline caseId={detail.caseId}/>}
        </div>}
      </div>
    </div>
  </div>;
}
