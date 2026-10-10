'use client';
import Link from 'next/link';
import {useEffect, useRef, useState, type ReactNode, type Ref} from 'react';
import {DatedRequestError, datedErrorKind, loadDateIndex, loadDatedDetail, loadDatedList, requireIndexedBundle, resolveDateEntry,
  type DatedDetailData, type DatedListData} from '@/lib/dated-api';
import type {DateEntry, DateIndex} from '@/lib/dated-contract';
import {DATED_COPY as C, DATED_EXACT as S, documentTitle, liveAnnouncement} from '@/lib/dated-presentation';
import DateSelector from './DateSelector';
import DatedFundList from './DatedFundList';
import DatedFundDetail from './DatedFundDetail';
import EmptyState from './primitives/EmptyState';

const VISUALLY_HIDDEN = {position: 'absolute', width: 1, height: 1, padding: 0, margin: -1, overflow: 'hidden', clip: 'rect(0,0,0,0)', whiteSpace: 'nowrap', border: 0} as const;

/** Header, guard sentence and footer shared by every dated screen (real and synthetic). */
export function DatedShell({children, synthetic = false, announcement = ''}: {children: ReactNode; synthetic?: boolean; announcement?: string}) {
  return <>
    <header className="site-header"><div className="header-inner">
      <Link className="brand" href={synthetic ? '/preview/dates' : '/dates'}>{C.brand} <small>{C.brandSmall}</small></Link>
      <span className="archive-label">{synthetic ? C.syntheticLabel : C.archiveLabel}</span>
    </div></header>
    <main>
      <p className="notice dated-guard" role="note" style={{borderLeftColor: 'var(--warning)'}}><strong>{S.guard}</strong></p>
      <p role="status" aria-live="polite" aria-atomic="true" data-dated-live style={VISUALLY_HIDDEN}>{announcement}</p>
      {children}
      <footer><span>{C.footerSources}</span><span>{C.footerUniverse}</span><span>{C.footerRights}</span></footer>
    </main>
  </>;
}

export type DatedStateKind = 'index-loading' | 'index-error' | 'invalid-date' | 'unregistered-date' | 'bundle-loading' | 'bundle-error' | 'mismatch' | 'not-found';
const TITLES: Record<DatedStateKind, string> = {
  'index-loading': C.indexLoading, 'index-error': C.indexError, 'invalid-date': C.invalidDate, 'unregistered-date': C.unregisteredDate,
  'bundle-loading': C.bundleLoading, 'bundle-error': C.bundleError, mismatch: C.mismatch, 'not-found': C.fundNotFound,
};
const DESCRIPTIONS: Partial<Record<DatedStateKind, string>> = {
  'index-loading': C.indexLoadingDescription, 'invalid-date': C.invalidDateDescription, 'unregistered-date': C.unregisteredDateDescription,
  'bundle-loading': C.bundleLoadingDescription, mismatch: C.mismatchDescription,
};
/** A non-ready dated state. Errors never show fund results; retry is explicit. */
export function DatedStateScreen({kind, message, selector, onRetry, retryHref, registeredHref, backHref, headingRef}: {
  kind: DatedStateKind; message?: string; selector?: ReactNode; onRetry?: () => void; retryHref?: string; registeredHref?: string; backHref?: string;
  headingRef?: Ref<HTMLHeadingElement>;
}) {
  const loading = kind === 'index-loading' || kind === 'bundle-loading';
  const retryable = kind === 'index-error' || kind === 'bundle-error';
  return <div data-dated-state={kind}>
    <h1 ref={headingRef} tabIndex={-1}>{TITLES[kind]}</h1>
    {selector}
    {loading ? <EmptyState title={TITLES[kind]} description={DESCRIPTIONS[kind]}/> : <div role="alert" className="notice error-panel">
      {DESCRIPTIONS[kind] && <p>{DESCRIPTIONS[kind]}</p>}
      {message && <p>{message}</p>}
      <p>{C.noResults}</p>
      {retryable && onRetry && <button type="button" className="button" style={{minHeight: 44}} onClick={onRetry}>{C.retry}</button>}
      {retryable && !onRetry && retryHref && <Link className="button" style={{minHeight: 44}} href={retryHref}>{C.retry}</Link>}
      {kind === 'mismatch' && registeredHref && <Link className="button" style={{minHeight: 44}} href={registeredHref}>{C.openRegistered}</Link>}
    </div>}
    {backHref && <Link href={backHref} className="back-link" style={{minHeight: 44, display: 'inline-flex', alignItems: 'center', marginTop: 16}}>{C.backToDates}</Link>}
  </div>;
}

type Load<T> = {status: 'loading'} | {status: 'ready'; data: T} | {status: 'error'; error: Error};
type Keyed<T> = {key: string} & ({status: 'loading'} | {status: 'ready'; data: T} | {status: 'error'; error: Error});
type Resolution = {kind: 'ok'; entry: DateEntry; key: string} | {kind: 'invalid-date' | 'unregistered-date' | 'mismatch'; message: string; entry?: DateEntry};
const isAbort = (error: unknown) => error instanceof DOMException && error.name === 'AbortError';
const asError = (error: unknown) => error instanceof Error ? error : new Error('Araştırma verisi alınamadı.');

function resolve(index: DateIndex, date: string | null, bundle: string): Resolution {
  let entry: DateEntry;
  try { entry = resolveDateEntry(index, date ?? index.default_date); } catch (error) {
    if (error instanceof DatedRequestError) return {kind: error.code === 'DATE_INVALID' ? 'invalid-date' : 'unregistered-date', message: error.message};
    throw error;
  }
  try { requireIndexedBundle(entry, bundle); } catch (error) {
    return {kind: 'mismatch', message: error instanceof Error ? error.message : '', entry};
  }
  return {kind: 'ok', entry, key: `${entry.date}|${entry.bundle_id}`};
}
function useDateIndex() {
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<Load<DateIndex>>({status: 'loading'});
  useEffect(() => {
    const controller = new AbortController();
    setState({status: 'loading'});
    loadDateIndex(controller.signal).then(data => { if (!controller.signal.aborted) setState({status: 'ready', data}); })
      .catch(error => { if (!controller.signal.aborted && !isAbort(error)) setState({status: 'error', error: asError(error)}); });
    return () => controller.abort();
  }, [attempt]);
  return [state, () => setAttempt(value => value + 1)] as const;
}
function useKeyedLoad<T>(resolution: Resolution | null, load: (entry: DateEntry, signal: AbortSignal) => Promise<T>, extra = '') {
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<Keyed<T> | null>(null);
  const key = resolution?.kind === 'ok' ? resolution.key + extra : null;
  const loader = useRef(load);
  loader.current = load;
  useEffect(() => {
    if (!key || resolution?.kind !== 'ok') return;
    const controller = new AbortController();
    setState({key, status: 'loading'});
    loader.current(resolution.entry, controller.signal).then(data => { if (!controller.signal.aborted) setState({key, status: 'ready', data}); })
      .catch(error => { if (!controller.signal.aborted && !isAbort(error)) setState({key, status: 'error', error: asError(error)}); });
    return () => controller.abort();
    // The key fully identifies (date, bundle[, code]); the entry object follows it.
  }, [key, attempt]);
  // Guard: a state loaded for another (date, bundle) is never rendered.
  const current = state && state.key === key ? state : null;
  return [current, () => setAttempt(value => value + 1)] as const;
}
// Module scope survives the page remount that follows a client-side date change.
// It holds the last settled list screen (ready or a non-loading state).
let lastSettledList: string | null = null;

export function DatedListView({date, bundle}: {date: string | null; bundle: string}) {
  const [indexState, retryIndex] = useDateIndex();
  const index = indexState.status === 'ready' ? indexState.data : null;
  const resolution = index ? resolve(index, date, bundle) : null;
  const [state, retry] = useKeyedLoad<DatedListData>(resolution, (entry, signal) => loadDatedList(index!, entry.date, signal, bundle || undefined));
  const heading = useRef<HTMLHeadingElement>(null);
  const [announcement, setAnnouncement] = useState('');
  const ready = state?.status === 'ready' ? state.data : null;
  const selector = index ? <DateSelector dates={index.entries.map(entry => entry.date)} windowEnd={index.default_date} action="/dates"
    selected={resolution?.kind === 'ok' || resolution?.kind === 'mismatch' ? resolution.entry!.date : index.default_date}/> : null;
  let content: ReactNode;
  // Identity of a settled screen (ready or a non-loading state); loading screens are not settled.
  let settled: string | null = null;
  if (indexState.status === 'loading') content = <DatedStateScreen kind="index-loading"/>;
  else if (indexState.status === 'error') {
    settled = `index-error|${date ?? ''}|${bundle}`;
    content = <DatedStateScreen kind="index-error" message={indexState.error.message} onRetry={retryIndex} headingRef={heading}/>;
  } else if (!resolution || resolution.kind !== 'ok') {
    const kind = resolution?.kind ?? 'invalid-date';
    settled = `${kind}|${date ?? ''}|${bundle}`;
    content = <DatedStateScreen kind={kind} message={resolution?.message} selector={selector} headingRef={heading}
      registeredHref={resolution?.entry ? `/dates?date=${resolution.entry.date}` : undefined}/>;
  } else if (!state || state.status === 'loading') content = <DatedStateScreen kind="bundle-loading" selector={selector}/>;
  else if (state.status === 'error') {
    // The list names no fund, so a not-found answer is a failed load here, never "Fon bulunamadı".
    const found = datedErrorKind(state.error);
    const kind = found === 'not-found' ? 'bundle-error' : found;
    settled = `${kind}|${resolution.entry.date}|${bundle}`;
    content = <DatedStateScreen kind={kind} message={state.error.message} selector={selector} headingRef={heading}
      onRetry={kind === 'bundle-error' ? retry : undefined} registeredHref={kind === 'mismatch' ? `/dates?date=${resolution.entry.date}` : undefined}/>;
  } else {
    settled = `ready|${state.data.entry.date}`;
    content = <DatedFundList list={state.data.list} summary={state.data.summary} selector={selector} headingRef={heading} windowEnd={index!.default_date}/>;
  }
  useEffect(() => {
    if (!settled) return;
    const changed = lastSettledList !== null && lastSettledList !== settled;
    lastSettledList = settled;
    const shown = ready?.entry.date;
    if (shown) document.title = documentTitle(shown);
    if (!changed) return;
    // After "Tarihi göster" or a retry, the new screen's h1 takes focus: for error states as for the ready list.
    heading.current?.focus();
    // Error states announce through their role="alert" panel; clear any earlier "loaded" text.
    if (!shown) { setAnnouncement(''); return; }
    // Fill the live region after it exists, so the change is announced.
    const timer = window.setTimeout(() => setAnnouncement(liveAnnouncement(shown)), 120);
    return () => window.clearTimeout(timer);
    // `settled` fully identifies the screen; `ready` comes from the same render.
  }, [settled]);
  return <DatedShell announcement={announcement}>{content}</DatedShell>;
}

export function DatedDetailView({code, date, bundle}: {code: string; date: string | null; bundle: string}) {
  const [indexState, retryIndex] = useDateIndex();
  const index = indexState.status === 'ready' ? indexState.data : null;
  const resolution = index ? resolve(index, date, bundle) : null;
  const [state, retry] = useKeyedLoad<DatedDetailData>(resolution, (entry, signal) => loadDatedDetail(index!, entry.date, code, signal, bundle || undefined), `|${code}`);
  const ready = state?.status === 'ready' ? state.data : null;
  useEffect(() => { if (ready) document.title = documentTitle(ready.entry.date, ready.detail.fund.code); }, [ready]);
  const back = resolution && resolution.kind !== 'invalid-date' && resolution.kind !== 'unregistered-date' && resolution.entry
    ? `/dates?date=${resolution.entry.date}` : '/dates';
  let content: ReactNode;
  if (indexState.status === 'loading') content = <DatedStateScreen kind="index-loading" backHref="/dates"/>;
  else if (indexState.status === 'error') content = <DatedStateScreen kind="index-error" message={indexState.error.message} onRetry={retryIndex} backHref="/dates"/>;
  else if (!resolution || resolution.kind !== 'ok') content = <DatedStateScreen kind={resolution?.kind ?? 'invalid-date'} message={resolution?.message} backHref={back}
    registeredHref={resolution?.entry ? `/dates/funds/${encodeURIComponent(code)}?date=${resolution.entry.date}` : undefined}/>;
  else if (!state || state.status === 'loading') content = <DatedStateScreen kind="bundle-loading" backHref={back}/>;
  else if (state.status === 'error') {
    const error = state.error;
    // Only a FUND_NOT_FOUND 404 is "Fon bulunamadı"; a DATE_NOT_REGISTERED 404 is an unregistered date.
    const kind = datedErrorKind(error);
    content = <DatedStateScreen kind={kind} message={error.message} backHref={back} onRetry={kind === 'bundle-error' ? retry : undefined}
      registeredHref={kind === 'mismatch' ? `/dates/funds/${encodeURIComponent(code)}?date=${resolution.entry.date}` : undefined}/>;
  } else content = <DatedFundDetail detail={state.data.detail} windowEnd={index!.default_date}/>;
  return <DatedShell>{content}</DatedShell>;
}
