'use client';

import Link from 'next/link';
import {usePathname} from 'next/navigation';
import {useEffect, useId, useRef, useState} from 'react';
import {createPortal} from 'react-dom';
import type {User} from '@/lib/auth';
import {AGENTS_CLOSE, AGENTS_OPEN, dockBadge, dockLabel, dockRing, fundFromPath} from '@/lib/agents';
import AgentTeamPanel, {type PanelDetail, type PanelTab} from './AgentTeamPanel';
import {useAgentFeed, useAgentPage, useCompactPanel, usePageVisit, useReducedMotion} from './hooks';
import Mascot from './Mascot';
import type {ConversationHandle} from './ReporterConversation';
import useDockPosition from './useDockPosition';
import {dockSize} from './dock-position';
import './agents.css';

function SignedOutDock() {
  const [open, setOpen] = useState(false);
  const dock = useDockPosition('signed-out'), moveId = useId();
  const popupWidth = Math.min(320, (dock.viewport?.width ?? 352) - 32);
  const popupLeft = dock.position && dock.viewport ? Math.max(16, Math.min(dock.position.x + dockSize(dock.viewport.width) - popupWidth,
    dock.viewport.width - popupWidth - 16)) : 16;
  const above = dock.position && dock.viewport ? dock.position.y > dock.viewport.height / 2 : true;
  const popup = dock.position && dock.viewport ? {position: 'fixed' as const, left: popupLeft, right: 'auto', width: popupWidth,
    ...(above ? {top: 'auto', bottom: dock.viewport.height - dock.position.y + 12, maxHeight: Math.max(120, dock.position.y - 28)} :
      {bottom: 'auto', top: dock.position.y + dockSize(dock.viewport.width) + 12,
        maxHeight: Math.max(120, dock.viewport.height - dock.position.y - dockSize(dock.viewport.width) - 28)})} : undefined;
  const button = useRef<HTMLButtonElement | null>(null), card = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    if (!open) return;
    card.current?.querySelector<HTMLElement>('a')?.focus();
    function keys(event: KeyboardEvent) {if (event.key === 'Escape') {setOpen(false); button.current?.focus();}}
    function outside(event: PointerEvent) {if (!card.current?.contains(event.target as Node) && !button.current?.contains(event.target as Node)) setOpen(false);}
    document.addEventListener('keydown', keys);
    document.addEventListener('pointerdown', outside);
    return () => {document.removeEventListener('keydown', keys); document.removeEventListener('pointerdown', outside);};
  }, [open]);
  return <div className="ag-dock" style={dock.style} data-dragging={dock.dragging}>
    {open && <div ref={card} className="ag-signin" style={popup} role="dialog" aria-label="Ajan ekibi">
      <div className="ag-signin-head"><span className="ag-head-mascot" aria-hidden="true"><Mascot size={28}/></span><strong>Ajan ekibi · 7/24</strong></div>
      <p>Nöbetçi, Hipotezci, Şüpheci, Doğrulayıcı ve Raportör fonları sürekli inceler. Ekibin çalışmasını izlemek ve Raportörle konuşmak için giriş yapın.</p>
      <Link className="ag-primary" href="/login">Giriş yap</Link>
    </div>}
    <button ref={button} type="button" className="ag-fab is-signed-out" aria-expanded={open} aria-haspopup="dialog"
      aria-label="Ajan ekibi ve Raportör. Kullanmak için giriş gerekir." aria-describedby={moveId}
      aria-keyshortcuts="ArrowUp ArrowDown ArrowLeft ArrowRight Home" {...dock.handlers}
      onClick={() => {if (!dock.consumeDrag()) setOpen(value => !value);}}>
      <span className="ag-fab-face"><Mascot size={40}/></span>
    </button>
    <span id={moveId} className="sr-only">Düğmeyi sürükleyerek veya ok tuşlarıyla taşıyın. Home tuşu başlangıç konumuna döndürür.</span>
  </div>;
}

export default function AgentDock({user}: {user?: User}) {
  if (!user) return <SignedOutDock/>;
  return <SignedInDock user={user}/>;
}

function SignedInDock({user}: {user: User}) {
  const dock = useDockPosition(user.user_id), moveId = useId();
  const pathname = usePathname() ?? '/';
  const {page} = useAgentPage();
  const [state, setState] = useState<'open' | 'closing' | 'closed'>('closed');
  const [everOpened, setEverOpened] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [tab, setTab] = useState<PanelTab>('reporter');
  const [detail, setDetail] = useState<PanelDetail | null>(null);
  const [seenPath, setSeenPath] = useState<string | null>(null);
  const fab = useRef<HTMLButtonElement | null>(null);
  const conversation = useRef<ConversationHandle | null>(null);
  const compact = useCompactPanel(), reducedMotion = useReducedMotion();
  const open = state === 'open';
  const feed = useAgentFeed(true, open, user.user_id);
  const fundCode = page?.fundCode !== undefined ? page.fundCode : fundFromPath(pathname);
  const note = usePageVisit(true, pathname, fundCode);
  const ring = dockRing(feed.team, feed.teamStatus);
  const badge = dockBadge(feed.queue, note.data, seenPath === pathname);

  useEffect(() => {setMounted(true);}, []);
  useEffect(() => {if (open) setSeenPath(pathname);}, [open, pathname, note.data]);
  // A link followed from inside the panel navigates away: show the new page.
  const previousPath = useRef(pathname);
  useEffect(() => {
    if (previousPath.current !== pathname && state === 'open') setState('closing');
    previousPath.current = pathname;
  }, [pathname]);
  useEffect(() => {
    function external(event: Event) {
      const detail = (event as CustomEvent<{tab?: PanelTab; question?: string; caseId?: string}>).detail;
      if (detail?.caseId && /^[a-f0-9-]{36}$/i.test(detail.caseId)) {
        setDetail({kind: 'case', caseId: detail.caseId});
        show('detail');
      } else show(detail?.tab ?? 'reporter');
      if (detail?.question) window.setTimeout(() => conversation.current?.ask(detail.question!), 50);
    }
    window.addEventListener(AGENTS_OPEN, external);
    window.addEventListener(AGENTS_CLOSE, close);
    return () => {window.removeEventListener(AGENTS_OPEN, external); window.removeEventListener(AGENTS_CLOSE, close);};
  });

  function show(nextTab?: PanelTab) {
    setEverOpened(true);
    if (nextTab) setTab(nextTab);
    else if (tab === 'team' && !compact) setTab('reporter');
    else if (tab === 'detail' && !detail) setTab('reporter');
    setState('open');
  }
  function close() {setState(current => current === 'open' ? 'closing' : current);}

  return <div className="ag-dock" style={dock.style} data-dragging={dock.dragging}>
    <button ref={fab} type="button" className={`ag-fab is-${ring}${open ? ' is-open' : ''}`} aria-haspopup="dialog" aria-expanded={open}
      aria-controls="ag-team-panel" aria-label={dockLabel(ring, feed.team, badge)} aria-describedby={moveId}
      aria-keyshortcuts="ArrowUp ArrowDown ArrowLeft ArrowRight Home" {...dock.handlers}
      onClick={() => {if (!dock.consumeDrag()) open ? close() : show(compact && tab === 'reporter' && !everOpened ? 'team' : undefined);}}>
      <svg className="ag-ring" viewBox="0 0 64 64" aria-hidden="true" focusable="false">
        <circle className="ag-ring-track" cx="32" cy="32" r="30.5"/>
        <circle className="ag-ring-arc" cx="32" cy="32" r="30.5" pathLength="100"/>
      </svg>
      <span className="ag-fab-face"><Mascot size={40}/></span>
      {badge && <span className={`ag-badge is-${badge.kind}`} aria-hidden="true">{badge.kind === 'requests' ? badge.count.toLocaleString('tr-TR') : ''}</span>}
    </button>
    <span id={moveId} className="sr-only">Düğmeyi sürükleyerek veya ok tuşlarıyla taşıyın. Home tuşu başlangıç konumuna döndürür.</span>
    {mounted && everOpened && createPortal(<AgentTeamPanel state={state} onClose={close} onClosed={() => setState('closed')} user={user} feed={feed} note={note}
      path={pathname} fundCode={fundCode} evidenceId={page?.evidenceId} compact={compact} reducedMotion={reducedMotion} tab={tab} setTab={setTab}
      detail={detail} openDetail={setDetail} conversation={conversation} returnFocus={fab} anchor={dock.position} viewport={dock.viewport}/>, document.body)}
  </div>;
}
