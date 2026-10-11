'use client';

import {createContext, useContext, useEffect, useRef, useState, useSyncExternalStore} from 'react';
import {post} from '@/lib/client';
import {AGENTS_REFRESH, type FeedStatus, type PageVisit, type QueueItem, type TeamSnapshot, parsePageVisit, parseQueue,
  parseTeam, pollDelay} from '@/lib/agents';

// ---------- Page context: pages declare the asset (and evidence focus) the Raportör should talk about ----------

export type AgentPageInfo = {fundCode: string | null; evidenceId?: string; title?: string};
type PageContextValue = {page: AgentPageInfo | null; setPage: (value: AgentPageInfo | null) => void};
export const AgentPageContext = createContext<PageContextValue>({page: null, setPage: () => undefined});
export function useAgentPage() {return useContext(AgentPageContext);}

// ---------- Media and time ----------

function subscribeMotion(callback: () => void) {
  const query = window.matchMedia('(prefers-reduced-motion: reduce)');
  query.addEventListener('change', callback);
  return () => query.removeEventListener('change', callback);
}
export function useReducedMotion(): boolean {
  return useSyncExternalStore(subscribeMotion, () => window.matchMedia('(prefers-reduced-motion: reduce)').matches, () => false);
}
function subscribeCompact(callback: () => void) {
  const query = window.matchMedia('(max-width: 1023px)');
  query.addEventListener('change', callback);
  return () => query.removeEventListener('change', callback);
}
/** Below 1024px the team stage moves into its own tab. */
export function useCompactPanel(): boolean {
  return useSyncExternalStore(subscribeCompact, () => window.matchMedia('(max-width: 1023px)').matches, () => false);
}
/** A clock for relative times; ticks only while a consumer is mounted and the tab is visible. */
export function useNow(intervalMs = 15000): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = window.setInterval(() => {if (!document.hidden) setNow(Date.now());}, intervalMs);
    return () => window.clearInterval(timer);
  }, [intervalMs]);
  return now;
}

// ---------- Team and queue polling (contract section 5: 2 s open, 15 s closed, paused when hidden) ----------

export type AgentFeed = {team: TeamSnapshot | null; queue: QueueItem[] | null; teamStatus: FeedStatus; queueStatus: FeedStatus;
  updatedAt: number | null; stale: boolean; refresh: () => void};

// The dock remounts when navigation crosses route layouts. The last snapshot (for the same user, at most two minutes
// old) seeds the new mount so the stage does not flash an empty state. It is only filled in the browser.
type FeedCache = {user: string; team: TeamSnapshot | null; queue: QueueItem[] | null; at: number};
let feedCache: FeedCache | null = null;
function cached(user: string): FeedCache | null {
  return feedCache && feedCache.user === user && Date.now() - feedCache.at < 120000 ? feedCache : null;
}

async function load<T>(path: string, parse: (value: unknown) => T, signal: AbortSignal): Promise<{status: FeedStatus; value?: T}> {
  try {
    const response = await fetch(`/api/p${path}`, {cache: 'no-store', signal});
    if (response.status === 401) return {status: 'signed-out'};
    if (!response.ok) return {status: 'unavailable'};
    try {return {status: 'ready', value: parse(await response.json())};} catch {return {status: 'invalid'};}
  } catch (error) {
    if (signal.aborted) throw error;
    return {status: 'unavailable'};
  }
}

export function useAgentFeed(enabled: boolean, open: boolean, user: string): AgentFeed {
  const [team, setTeam] = useState<TeamSnapshot | null>(() => cached(user)?.team ?? null);
  const [queue, setQueue] = useState<QueueItem[] | null>(() => cached(user)?.queue ?? null);
  const [teamStatus, setTeamStatus] = useState<FeedStatus>(() => cached(user)?.team ? 'ready' : 'loading');
  const [queueStatus, setQueueStatus] = useState<FeedStatus>(() => cached(user)?.queue ? 'ready' : 'loading');
  const [updatedAt, setUpdatedAt] = useState<number | null>(() => cached(user)?.at ?? null);
  const [stale, setStale] = useState(false);
  const failures = useRef(0);
  const trigger = useRef<() => void>(() => undefined);
  useEffect(() => {
    if (!enabled) return;
    let stopped = false, timer = 0, inflight: AbortController | null = null, running = false;
    async function run() {
      window.clearTimeout(timer);
      if (stopped || running || document.hidden) return;
      running = true;
      const controller = new AbortController();
      inflight = controller;
      try {
        const [teamResult, queueResult] = await Promise.all([
          load('/agents/team', parseTeam, controller.signal), load('/agents/queue?limit=30', parseQueue, controller.signal)]);
        if (stopped) return;
        setTeamStatus(teamResult.status);
        setQueueStatus(queueResult.status);
        if (teamResult.value) setTeam(teamResult.value);
        if (queueResult.value) setQueue(queueResult.value);
        const ok = teamResult.status === 'ready' && queueResult.status === 'ready';
        failures.current = ok ? 0 : failures.current + 1;
        setStale(!ok);
        if (ok) {
          const at = Date.now();
          setUpdatedAt(at);
          feedCache = {user, team: teamResult.value ?? null, queue: queueResult.value ?? null, at};
        }
        if (teamResult.status === 'signed-out' || queueResult.status === 'signed-out') {feedCache = null; stopped = true; return;}
      } catch {
        if (stopped) return;
      } finally {
        running = false;
        if (inflight === controller) inflight = null;
      }
      schedule();
    }
    function schedule() {
      window.clearTimeout(timer);
      const delay = pollDelay(open, document.hidden, failures.current);
      if (!stopped && delay !== null) timer = window.setTimeout(() => void run(), delay);
    }
    function visibility() {
      if (document.hidden) window.clearTimeout(timer);
      else void run();
    }
    trigger.current = () => void run();
    void run();
    document.addEventListener('visibilitychange', visibility);
    window.addEventListener(AGENTS_REFRESH, trigger.current);
    const listener = trigger.current;
    return () => {
      stopped = true;
      window.clearTimeout(timer);
      inflight?.abort();
      document.removeEventListener('visibilitychange', visibility);
      window.removeEventListener(AGENTS_REFRESH, listener);
    };
  }, [enabled, open, user]);
  return {team, queue, teamStatus, queueStatus, updatedAt, stale, refresh: () => trigger.current()};
}

// ---------- Page note (deterministic, no model call) ----------

export type PageNoteState = {status: 'idle' | 'loading' | 'ready' | 'error'; data: PageVisit | null};
const noteCache = new Map<string, {at: number; data: PageVisit}>();

export function usePageVisit(enabled: boolean, path: string, fundCode: string | null, version = 0): PageNoteState {
  const [state, setState] = useState<PageNoteState>({status: 'idle', data: null});
  useEffect(() => {
    if (!enabled) {setState({status: 'idle', data: null}); return;}
    const key = `${path}|${fundCode ?? ''}`;
    const cached = noteCache.get(key);
    if (cached && Date.now() - cached.at < 60000 && version === 0) {setState({status: 'ready', data: cached.data}); return;}
    let cancelled = false;
    setState(previous => ({status: 'loading', data: previous.data}));
    const timer = window.setTimeout(async () => {
      try {
        const response = await post('/agents/page-visit', {path, fund_code: fundCode});
        if (!response.ok) throw new Error(String(response.status));
        const data = parsePageVisit(await response.json());
        noteCache.set(key, {at: Date.now(), data});
        if (!cancelled) setState({status: 'ready', data});
      } catch {
        if (!cancelled) setState({status: 'error', data: null});
      }
    }, 350);
    return () => {cancelled = true; window.clearTimeout(timer);};
  }, [enabled, path, fundCode, version]);
  return state;
}
