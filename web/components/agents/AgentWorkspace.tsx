'use client';

import Link from 'next/link';
import {useEffect, useState} from 'react';
import {AGENTS_CLOSE, AGENT_ROLES, type AgentMessage, type AgentRole, type CaseDetail, HUMAN_META, type QueueItem, ROLE_META, type Workspace, caseStatusLabel,
  clockTime, kindLabel, parseCase, parseWorkspace, participantName, relativeTime, taskStatusLabel} from '@/lib/agents';
import RoleGlyph from './RoleGlyph';

type Load<T> = {status: 'loading' | 'ready' | 'unavailable' | 'invalid'; data: T | null};

function usePolled<T>(path: string | null, parse: (value: unknown) => T, intervalMs = 3000): Load<T> {
  const [state, setState] = useState<Load<T>>({status: 'loading', data: null});
  useEffect(() => {
    if (!path) return;
    let stopped = false, timer = 0, failures = 0;
    setState({status: 'loading', data: null});
    async function run() {
      window.clearTimeout(timer);
      if (stopped || document.hidden) return;
      const controller = new AbortController();
      const timeout = window.setTimeout(() => controller.abort(), 10000);
      try {
        const response = await fetch(`/api/p${path}`, {cache: 'no-store', signal: controller.signal});
        if (!response.ok) throw new Error(String(response.status));
        let data: T;
        try {data = parse(await response.json());} catch {if (!stopped) setState(previous => ({status: 'invalid', data: previous.data})); failures++; return;}
        failures = 0;
        if (!stopped) setState({status: 'ready', data});
      } catch {
        failures++;
        if (!stopped) setState(previous => ({status: 'unavailable', data: previous.data}));
      } finally {
        window.clearTimeout(timeout);
        if (!stopped) timer = window.setTimeout(() => void run(), Math.min(intervalMs * 2 ** Math.min(failures, 4), 30000));
      }
    }
    function visibility() {if (!document.hidden) void run(); else window.clearTimeout(timer);}
    void run();
    document.addEventListener('visibilitychange', visibility);
    return () => {stopped = true; window.clearTimeout(timer); document.removeEventListener('visibilitychange', visibility);};
  }, [path, intervalMs]);
  return state;
}

function Timeline({items, role, now}: {items: AgentMessage[]; role?: AgentRole; now: number}) {
  if (!items.length) return <p className="ag-muted">Henüz kayıtlı bir ekip mesajı yok.</p>;
  return <ol className="ag-timeline">{items.map(message => {
    const outgoing = role ? message.from_role === role : false;
    return <li key={message.message_id} className={`ag-timeline-item is-${message.kind}${outgoing ? ' is-outgoing' : ''}`}>
      <span className={`ag-avatar ag-avatar-sm ag-avatar-${message.from_role === 'team' ? 'team' : message.from_role}`} aria-hidden="true">
        {message.from_role === 'team' ? null : <RoleGlyph role={message.from_role} size={message.from_role === 'reporter' ? 18 : 14}/>}</span>
      <div className="ag-timeline-body">
        <p className="ag-timeline-head"><strong>{participantName(message.from_role)}</strong><span aria-hidden="true">→</span><span className="sr-only">kime:</span>
          <span>{participantName(message.to_role)}</span><span className="ag-kind">{kindLabel(message.kind)}</span>
          <time dateTime={message.created_at} title={clockTime(message.created_at)}>{relativeTime(message.created_at, now)}</time></p>
        {(message.hypothesis_type || message.verdict) && <p className="ag-chips">{message.hypothesis_type && <span className="ag-tag">{message.hypothesis_type}</span>}
          {message.verdict && <span className={`ag-tag ag-verdict`}>{message.verdict}</span>}</p>}
        <p className="ag-timeline-text">{message.body_tr}</p>
        <p className="ag-timeline-origin">{message.ai_written ? 'Ajan değerlendirmesi' : message.kind === 'test_result' ? 'Hesaplanan sonuç' : 'Ekip kaydı'}
          {message.fund_code && <> · <Link href={`/funds/${message.fund_code}`}>{message.fund_code}</Link></>}</p>
      </div>
    </li>;
  })}</ol>;
}

function TaskLine({task, now}: {task: QueueItem; now: number}) {
  return <li className={`ag-task-line is-${task.status}`}><span className={`ag-status is-${task.status}`}>{taskStatusLabel(task.status)}</span>
    <span className="ag-task-title">{task.title_tr}</span>{task.fund_code && <span className="ag-code">{task.fund_code}</span>}
    {task.source === 'user' && <span className="ag-tag ag-tag-user">Kullanıcı isteği</span>}
    <span className="ag-task-time">{relativeTime(task.finished_at ?? task.started_at ?? task.created_at, now)}</span></li>;
}

export function RoleWorkspace({role, onOpenCase, standalone = false}: {role: AgentRole; onOpenCase?: (caseId: string) => void; standalone?: boolean}) {
  const meta = ROLE_META[role];
  const state = usePolled<Workspace>(`/agents/workspace/${role}?limit=20`, value => parseWorkspace(value, role));
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {setNow(Date.now());}, [state.data]);
  const data = state.data;
  const incoming = data?.messages.filter(message => message.to_role === role || (message.to_role === 'team' && message.from_role !== role)) ?? [];
  const outgoing = data?.messages.filter(message => message.from_role === role) ?? [];
  const Heading = standalone ? 'h1' : 'h2';
  return <div className={`ag-workspace${standalone ? ' is-standalone' : ''}`}>
    <div className="ag-workspace-head">
      <span className={`ag-avatar ag-avatar-lg ag-avatar-${role}`} aria-hidden="true"><RoleGlyph role={role} size={role === 'reporter' ? 34 : 24}/></span>
      <div><p className="ag-eyebrow">Ekip çalışması</p>
        <Heading>{meta.name}</Heading><p className="ag-muted">{meta.description}</p></div>
    </div>
    {state.status === 'loading' && !data && <p className="ag-empty" role="status">Çalışma alanı yükleniyor…</p>}
    {!data && (state.status === 'unavailable' || state.status === 'invalid') && <div className="ag-empty" role="status"><strong>Çalışma alanı şu anda alınamıyor.</strong><p>Bağlantı birkaç saniye içinde yeniden denenecek.</p></div>}
    {data && <div className="ag-workspace-grid">
      <div className="ag-workspace-col">
        <section className="ag-block" aria-labelledby={`ag-current-${role}`}><h3 id={`ag-current-${role}`}>Şu anki görev</h3>
          {data.current ? <div className="ag-current">
            <p className="ag-current-title">{data.current.title_tr}</p>
            <p className="ag-task-meta"><span className={`ag-status is-${data.current.status}`}>{taskStatusLabel(data.current.status)}</span>
              {data.current.fund_code && <Link className="ag-code" href={`/funds/${data.current.fund_code}`}>{data.current.fund_code}</Link>}
              {data.current.fund_name && <span className="ag-task-fund">{data.current.fund_name}</span>}
              {data.current.started_at && <span>{relativeTime(data.current.started_at, now)} başladı</span>}</p>
            {data.current.case_id && onOpenCase && <button type="button" className="ag-ghost" onClick={() => onOpenCase(data.current!.case_id!)}>Vakanın tüm akışını aç</button>}
          </div> : <p className="ag-muted">Şu anda üzerinde çalıştığı bir görev yok.</p>}
        </section>
        <section className="ag-block" aria-labelledby={`ag-inputs-${role}`}><h3 id={`ag-inputs-${role}`}>Girdiler</h3>
          <p className="ag-muted">{meta.inputs}</p>
          {incoming.length > 0 && <Timeline items={incoming.slice(-3)} now={now}/>}
        </section>
        {data.tasks.length > 0 && <section className="ag-block" aria-labelledby={`ag-tasks-${role}`}><h3 id={`ag-tasks-${role}`}>Son görevler</h3>
          <ul className="ag-task-lines">{data.tasks.slice(0, 8).map(task => <TaskLine key={task.task_id} task={task} now={now}/>)}</ul></section>}
      </div>
      <div className="ag-workspace-col">
        <section className="ag-block ag-output-block" aria-labelledby={`ag-outputs-${role}`}><h3 id={`ag-outputs-${role}`}>Çıktılar ve ekip yazışmaları</h3>
          {outgoing.length === 0 && incoming.length === 0 ? <p className="ag-muted">Bu ajanın henüz kayıtlı bir çıktısı yok.</p> : <Timeline items={data.messages} role={role} now={now}/>}
        </section>
      </div>
    </div>}
  </div>;
}

export function CaseTimeline({caseId}: {caseId: string}) {
  const state = usePolled<CaseDetail>(`/agents/cases/${caseId}`, parseCase);
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {setNow(Date.now());}, [state.data]);
  const data = state.data;
  if (!data) return state.status === 'loading' ? <p className="ag-empty" role="status">Vaka yükleniyor…</p> :
    <div className="ag-empty" role="status"><strong>Vaka şu anda alınamıyor.</strong><p>Bağlantı birkaç saniye içinde yeniden denenecek.</p></div>;
  const steps = AGENT_ROLES.map(role =>
    ({role, task: data.tasks.filter(task => task.role === role).sort((a, b) => Date.parse(b.created_at ?? '') - Date.parse(a.created_at ?? ''))[0]}));
  return <div className="ag-case">
    <div className="ag-case-head">
      <p className="ag-eyebrow">Vaka · {caseStatusLabel(data.case.status)}{data.case.opened_by === 'user' ? ' · Kullanıcı isteğiyle açıldı' : data.case.opened_by === 'sentinel' ? ' · Nöbetçi açtı' : ''}</p>
      <h2>{data.case.title_tr ?? (data.case.fund_code ? `${data.case.fund_code} incelemesi` : 'Vaka')}</h2>
      <p className="ag-task-meta">{data.case.fund_code && <Link className="ag-code" href={`/funds/${data.case.fund_code}`}>{data.case.fund_code}</Link>}
        {data.case.fund_name && <span className="ag-task-fund">{data.case.fund_name}</span>}
        {data.case.opened_at && <span>{relativeTime(data.case.opened_at, now)} açıldı</span>}</p>
    </div>
    <ol className="ag-steps" aria-label="Vakadaki adımlar">{steps.map(step => <li key={step.role} className={`ag-step is-${step.task?.status ?? 'none'}`}>
      <span className={`ag-avatar ag-avatar-sm ag-avatar-${step.role}`} aria-hidden="true"><RoleGlyph role={step.role} size={step.role === 'reporter' ? 18 : 14}/></span>
      <span><strong>{ROLE_META[step.role].name}</strong><span className="ag-muted">{step.task ? taskStatusLabel(step.task.status) :
        step.role === 'sentinel' && data.case.opened_by === 'sentinel' ? 'Vakayı açtı' :
        step.role === 'sentinel' && data.case.opened_by === 'user' ? 'Kullanıcı isteğiyle açıldı' : 'Henüz sıraya girmedi'}</span></span>
    </li>)}
      <li className={`ag-step ag-step-human is-${data.case.has_decision ? 'done' : 'none'}`}>
        <span className="ag-avatar ag-avatar-sm ag-avatar-human" aria-hidden="true"><RoleGlyph role="human" size={14}/></span>
        <span><strong>{HUMAN_META.name}</strong><span className="ag-muted">{data.case.has_decision ? 'Öneri incelemeye sunuldu' : 'Rapor bekleniyor'}</span></span>
      </li></ol>
    {data.case.has_decision && data.case.fund_code && <div className="ag-decision">
      <p>Raportörün önerisi insan incelemesine sunuldu. Bir analist öneriyi kabul edebilir, gerekçesiyle değiştirebilir veya reddedebilir; yapay zekânın ilk önerisi her durumda korunur.</p>
      <Link className="ag-primary" href={`/funds/${data.case.fund_code}#karar`}
        onClick={() => window.dispatchEvent(new Event(AGENTS_CLOSE))}>İnsan kararına git</Link>
    </div>}
    <Timeline items={data.messages} now={now}/>
  </div>;
}
