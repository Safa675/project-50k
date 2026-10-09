'use client';
import {useEffect, useRef, useState} from 'react';
import Link from 'next/link';
import {loadDetail, loadList, ResearchApiError} from '@/lib/research-api';
import type {DetailResponse} from '@/lib/research-contract';
import FundList from './FundList';
import FundDetail from './FundDetail';
import Shell from './Shell';
import EmptyState from './primitives/EmptyState';

type LoadState<T> = {status: 'loading'} | {status: 'ready'; data: T} | {status: 'error'; error: Error};
function errorValue(error: unknown): Error {
  return error instanceof Error ? error : new Error('Araştırma verisi alınamadı.');
}
function isAbort(error: unknown) { return error instanceof DOMException && error.name === 'AbortError'; }
function PendingView({state, retry, backQuery = ''}: {state: {status: 'loading'} | {status: 'error'; error: Error}; retry: () => void; backQuery?: string}) {
  const notFound = state.status === 'error' && state.error instanceof ResearchApiError && state.error.status === 404;
  return <Shell>
    <h1>{state.status === 'loading' ? 'Araştırma verisi yükleniyor…' : notFound ? 'Fon bulunamadı' : 'Araştırma verisi alınamadı'}</h1>
    {state.status === 'loading' ? <EmptyState title="Seçili arşiv paketi yükleniyor" description="Sonuçlar doğrulandıktan sonra gösterilecek."/> : <div role="alert" className="notice error-panel">
      <p>{state.error.message}</p>
      <p>Bu durumda fon bulguları gösterilemiyor.</p>
      {!notFound && <button className="button" onClick={retry}>Tekrar dene</button>}
    </div>}
    <Link href={`/${backQuery ? '?' + backQuery : ''}`} className="back-link">← Fon listesine dön</Link>
  </Shell>;
}
export function ResearchListView({expectedBundle}: {expectedBundle?: string}) {
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<LoadState<Awaited<ReturnType<typeof loadList>>>>({status: 'loading'});
  const loadedAttempt = useRef(-1);
  useEffect(() => {
    if (state.status === 'ready' && attempt === loadedAttempt.current && (!expectedBundle || expectedBundle === state.data.list.immutable_bundle_id)) return;
    const controller = new AbortController();
    setState({status: 'loading'});
    loadList(controller.signal, expectedBundle).then(data => {
      if (!controller.signal.aborted) {loadedAttempt.current = attempt; setState({status: 'ready', data});}
    }).catch(error => {
      if (!controller.signal.aborted && !isAbort(error)) setState({status: 'error', error: errorValue(error)});
    });
    return () => controller.abort();
  }, [attempt, expectedBundle]);
  if (state.status !== 'ready') return <PendingView state={state} retry={() => setAttempt(value => value + 1)}/>;
  if (expectedBundle && expectedBundle !== state.data.list.immutable_bundle_id) return <PendingView state={{status: 'loading'}} retry={() => setAttempt(value => value + 1)}/>;
  return <FundList funds={state.data.list.funds} summary={state.data.summary.summary} bundleId={state.data.list.immutable_bundle_id}/>;
}
export function ResearchDetailView({code, expectedBundle, backQuery}: {code: string; expectedBundle?: string; backQuery: string}) {
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<LoadState<DetailResponse>>({status: 'loading'});
  useEffect(() => {
    const controller = new AbortController();
    setState({status: 'loading'});
    loadDetail(code, controller.signal, expectedBundle).then(data => {
      if (!controller.signal.aborted) setState({status: 'ready', data});
    }).catch(error => {
      if (!controller.signal.aborted && !isAbort(error)) setState({status: 'error', error: errorValue(error)});
    });
    return () => controller.abort();
  }, [code, expectedBundle, attempt]);
  if (state.status !== 'ready') return <PendingView state={state} retry={() => setAttempt(value => value + 1)} backQuery={backQuery}/>;
  if (state.data.fund.code !== code || (expectedBundle && expectedBundle !== state.data.immutable_bundle_id)) return <PendingView state={{status: 'loading'}} retry={() => setAttempt(value => value + 1)} backQuery={backQuery}/>;
  const back = new URLSearchParams(backQuery);
  back.set('bundle', state.data.immutable_bundle_id);
  return <FundDetail fund={state.data.fund} sources={state.data.sources} bundleId={state.data.immutable_bundle_id} backQuery={back.toString()}/>;
}
