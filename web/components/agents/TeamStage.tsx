'use client';

import Link from 'next/link';
import {useLayoutEffect, useRef, useState} from 'react';
import {AGENT_ROLES, type AgentRole, type FeedStatus, HUMAN_META, ROLE_META, STAGE_EDGES, type TeamAgent, type TeamSnapshot,
  agentStateLabel, edgeActivity, kindLabel, participantName, relativeTime} from '@/lib/agents';
import RoleGlyph from './RoleGlyph';

/** The latest interaction, the team's counters and a polite live announcement of who is working. */
export function StageTicker({team, now}: {team: TeamSnapshot | null; now: number}) {
  const link = team?.links.slice().sort((a, b) => Date.parse(b.at) - Date.parse(a.at))[0];
  const working = team?.agents.filter(agent => agent.state === 'working') ?? [];
  const announcement = working.length ? `Çalışan ajanlar: ${working.map(agent => `${agent.name_tr}${agent.fund_code ? `, ${agent.fund_code}` : ''}`).join('; ')}.` :
    team ? 'Şu anda çalışan ajan yok.' : '';
  return <div className="ag-ticker">
    {link ? <p key={`${link.from}${link.to}${link.at}`} className="ag-ticker-line"><span className="ag-ticker-dot" aria-hidden="true"/><span className="ag-label">Son etkileşim</span>
      <strong>{participantName(link.from)}</strong><span aria-hidden="true">→</span><span className="sr-only">kime:</span><strong>{participantName(link.to)}</strong>
      <span className="ag-kind">{kindLabel(link.kind)}</span><span className="ag-muted">{relativeTime(link.at, now)}</span></p> :
      <p className="ag-muted">{team ? 'Henüz kayıtlı bir ekip etkileşimi yok.' : ''}</p>}
    {team && <p className="ag-ticker-counts"><span><strong>{team.counts.open_cases.toLocaleString('tr-TR')}</strong> açık vaka</span>
      <span><strong>{team.counts.running.toLocaleString('tr-TR')}</strong> çalışan</span><span><strong>{team.counts.queued.toLocaleString('tr-TR')}</strong> sırada</span>
      <span>Bugün <strong>{team.counts.done_today.toLocaleString('tr-TR')}</strong> tamamlandı</span></p>}
    <p className="sr-only" aria-live="polite" aria-atomic="true">{announcement}</p>
  </div>;
}

type Geometry = {width: number; height: number; paths: Partial<Record<string, string>>};

function edgePath(a: DOMRect, b: DOMRect, origin: DOMRect): string {
  const ax = a.left - origin.left, ay = a.top - origin.top, bx = b.left - origin.left, by = b.top - origin.top;
  if (bx >= ax + a.width - 1) {
    const sx = ax + a.width, sy = ay + a.height / 2, ex = bx, ey = by + b.height / 2, dx = Math.max(10, (ex - sx) / 2);
    return `M${sx.toFixed(1)} ${sy.toFixed(1)} C${(sx + dx).toFixed(1)} ${sy.toFixed(1)} ${(ex - dx).toFixed(1)} ${ey.toFixed(1)} ${ex.toFixed(1)} ${ey.toFixed(1)}`;
  }
  if (by >= ay + a.height - 1) {
    const sx = ax + a.width / 2, sy = ay + a.height, ex = bx + b.width / 2, ey = by, dy = Math.max(8, (ey - sy) / 2);
    return `M${sx.toFixed(1)} ${sy.toFixed(1)} C${sx.toFixed(1)} ${(sy + dy).toFixed(1)} ${ex.toFixed(1)} ${(ey - dy).toFixed(1)} ${ex.toFixed(1)} ${ey.toFixed(1)}`;
  }
  return '';
}

function idleText(agent: TeamAgent): string {
  switch (agent.state) {
    case 'working': return ROLE_META[agent.role].short;
    case 'waiting': return 'Önceki adımın bitmesini bekliyor.';
    case 'waiting_budget': return 'Yeni günün bütçesini bekliyor.';
    case 'off': return ROLE_META[agent.role].ai ? 'Yapay zekâ kapalı; bu adım çalışmıyor.' : 'Tarama şu anda kapalı.';
    case 'unknown': return 'Durum bilgisi alınamadı.';
    default: return agent.role === 'sentinel' ? 'Yeni bir gelişme için taramayı sürdürüyor.' : 'Yeni bir vaka bekliyor.';
  }
}

export function stageAgents(team: TeamSnapshot | null): TeamAgent[] {
  return AGENT_ROLES.map(role => team?.agents.find(agent => agent.role === role) ??
    {role, name_tr: ROLE_META[role].name, state: 'unknown', activity_tr: null, case_id: null, fund_code: null, fund_name: null, since: null});
}

export default function TeamStage({team, status, reducedMotion, selected, onSelect, onTalk, reviewHref}: {
  team: TeamSnapshot | null; status: FeedStatus; reducedMotion: boolean; selected?: AgentRole | null;
  onSelect: (role: AgentRole) => void; onTalk?: () => void; reviewHref: string;
}) {
  const stage = useRef<HTMLDivElement | null>(null);
  const nodes = useRef<Partial<Record<AgentRole | 'human', HTMLElement | null>>>({});
  const [geometry, setGeometry] = useState<Geometry>({width: 0, height: 0, paths: {}});
  const agents = stageAgents(team);
  const activity = team ? edgeActivity(team.links, team.now, team.agents) : [];
  const signature = agents.map(agent => `${agent.state}:${agent.activity_tr ?? ''}:${agent.fund_code ?? ''}`).join('|');

  useLayoutEffect(() => {
    const element = stage.current;
    if (!element) return;
    let frame = 0;
    function measure() {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        if (!element) return;
        const origin = element.getBoundingClientRect();
        const paths: Geometry['paths'] = {};
        for (const edge of STAGE_EDGES) {
          const from = nodes.current[edge.from], to = nodes.current[edge.to];
          if (from && to) paths[edge.key] = edgePath(from.getBoundingClientRect(), to.getBoundingClientRect(), origin);
        }
        setGeometry({width: origin.width, height: origin.height, paths});
      });
    }
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    for (const node of Object.values(nodes.current)) if (node) observer.observe(node);
    return () => {cancelAnimationFrame(frame); observer.disconnect();};
  }, [signature]);

  const unavailable = !team && status !== 'loading';
  return <div className={`ag-stage${unavailable ? ' is-unavailable' : ''}${!team && status === 'loading' ? ' is-loading' : ''}`} ref={stage}>
    <svg className="ag-edges" width={geometry.width} height={geometry.height} viewBox={`0 0 ${geometry.width || 1} ${geometry.height || 1}`} aria-hidden="true" focusable="false">
      {STAGE_EDGES.map(edge => {
        const d = geometry.paths[edge.key];
        if (!d) return null;
        const active = activity.find(item => item.key === edge.key);
        return <g key={edge.key} className={`ag-edge${active ? active.fresh ? ' is-fresh' : ' is-recent' : ''}`}>
          <path className="ag-edge-base" d={d}/>
          {active && <path className={`ag-edge-flow${active.reverse ? ' is-reverse' : ''}`} d={d}/>}
          {active?.fresh && !reducedMotion && <circle className="ag-edge-pulse" r="3.2">
            <animateMotion dur="1.5s" repeatCount="indefinite" path={d} keyPoints={active.reverse ? '1;0' : '0;1'} keyTimes="0;1" calcMode="linear"/>
          </circle>}
        </g>;
      })}
    </svg>
    <ol className="ag-stage-grid" aria-label="Ekibin iş akışı">
      {agents.map(agent => {
        const meta = ROLE_META[agent.role];
        const state = agentStateLabel(agent.state, agent.role);
        const detail = agent.activity_tr ?? idleText(agent);
        const fund = agent.fund_code ? `${agent.fund_code}${agent.fund_name ? ` · ${agent.fund_name}` : ''}` : null;
        return <li key={agent.role} ref={node => {nodes.current[agent.role] = node;}}
          className={`ag-node ag-node-${agent.role} is-${agent.state}${selected === agent.role ? ' is-selected' : ''}`}>
          {agent.role === 'reporter' && <span className="ag-node-eyebrow">Sizinle konuşan ajan</span>}
          <button type="button" className="ag-node-main" onClick={() => onSelect(agent.role)} title={meta.short}
            aria-label={`${agent.name_tr}: ${meta.short}. ${state}. ${detail}${fund ? `. Fon: ${fund}` : ''}. Çalışma alanını aç.`}>
            <span className="ag-node-head">
              <span className={`ag-avatar ag-avatar-${agent.role}`}><RoleGlyph role={agent.role} size={agent.role === 'reporter' ? 26 : 16}/></span>
              <span className="ag-node-name"><strong>{agent.name_tr}</strong>
                <span className="ag-node-state"><span className="ag-dot" aria-hidden="true"/><span className="ag-node-state-text">{state}{agent.since && agent.state === 'working' && team ?
                  <span className="ag-node-since"> · {relativeTime(agent.since, team.now)}</span> : null}</span></span></span>
            </span>
            <span className="ag-node-activity">{detail}</span>
            {fund && <span className="ag-node-fund"><span className="ag-code">{agent.fund_code}</span>{agent.fund_name && <span className="ag-node-fund-name">{agent.fund_name}</span>}</span>}
          </button>
          {agent.role === 'reporter' && onTalk && <button type="button" className="ag-node-talk" onClick={onTalk}>
            <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/></svg>
            Raportörle konuş</button>}
        </li>;
      })}
      <li ref={node => {nodes.current.human = node;}} className="ag-node ag-node-human">
        <Link className="ag-node-main" href={reviewHref}>
          <span className="ag-node-head">
            <span className="ag-avatar ag-avatar-human"><RoleGlyph role="human" size={16}/></span>
            <span className="ag-node-name"><strong>{HUMAN_META.name}</strong><span className="ag-node-state">Son söz insanda</span></span>
          </span>
          <span className="ag-node-activity">Öneriyi kabul eder, gerekçesiyle değiştirir ya da reddeder.</span>
        </Link>
      </li>
    </ol>
  </div>;
}
