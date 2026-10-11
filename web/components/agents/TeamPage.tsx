'use client';

import Link from 'next/link';
import {useRouter} from 'next/navigation';
import {useEffect, useState} from 'react';
import {AGENTS_OPEN, AGENT_ROLES, type AgentRole, ROLE_META, scopeLabel} from '@/lib/agents';
import AgentQueue from './AgentQueue';
import {BudgetMeter} from './AgentTeamPanel';
import {CaseTimeline, RoleWorkspace} from './AgentWorkspace';
import {useAgentFeed, useReducedMotion} from './hooks';
import RoleGlyph from './RoleGlyph';
import TeamStage, {StageTicker} from './TeamStage';
import './agents.css';

// Full-page, read-only views of the agent team (/ekip and /ekip/[role]). Nothing here talks to an agent; the
// Raportör conversation stays in the dock.

function TeamNav({current}: {current: AgentRole | null}) {
  return <nav className="ag-page-nav" aria-label="Ajan çalışma alanları">
    <Link href="/ekip" aria-current={current === null ? 'page' : undefined}>Genel bakış</Link>
    {AGENT_ROLES.map(role => <Link key={role} href={`/ekip/${ROLE_META[role].slug}`} aria-current={current === role ? 'page' : undefined}>
      <span className={`ag-avatar ag-avatar-xs ag-avatar-${role}`} aria-hidden="true"><RoleGlyph role={role} size={role === 'reporter' ? 10 : 12}/></span>
      {ROLE_META[role].name}</Link>)}
  </nav>;
}

function CaseCard({caseId, onClose}: {caseId: string; onClose: () => void}) {
  return <section className="ag-page-card" aria-label="Vakanın akışı">
    <div className="ag-page-card-head"><h2>Vakanın akışı</h2>
      <button type="button" className="ag-ghost" onClick={onClose}>Kapat</button></div>
    <div className="ag-view"><CaseTimeline caseId={caseId}/></div>
  </section>;
}

export function TeamOverviewPage({userId, reviewHref, scopeKey}: {userId: string; reviewHref: string; scopeKey?: string}) {
  const feed = useAgentFeed(true, true, userId);
  const reducedMotion = useReducedMotion();
  const router = useRouter();
  const [caseId, setCaseId] = useState<string | null>(null);
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {setNow(Date.now());}, [feed.team, feed.updatedAt]);
  const scope = scopeLabel(feed.team?.scope ?? scopeKey ?? null);
  return <section className="ag-page">
    <header className="ag-page-head">
      <div>
        <p className="ag-eyebrow">Ajan ekibi · 7/24</p>
        <h1>Ekip şu anda ne yapıyor</h1>
        <p className="ag-muted">Nöbetçi fonları sürekli tarar ve vaka açar. Hipotezci ile Şüpheci aynı anda açıklama ve karşı açıklama yazar, Doğrulayıcı bunları kodla hesaplanan testlerle sınar, Raportör de denetlenebilir bir rapor hazırlar. Son karar her zaman insandadır. Bu sayfa salt okunurdur; Raportörle sağ alttaki düğmeden konuşabilirsiniz.</p>
      </div>
      <div className="ag-page-meta">
        <div className="ag-head-date"><span className="ag-label">İnceleme tarihi</span><strong>{scope.date ?? scope.mode}</strong></div>
        <BudgetMeter team={feed.team}/>
      </div>
    </header>
    <TeamNav current={null}/>
    <div className="ag-page-card">
      <div className="ag-stage-wrap">
        <TeamStage team={feed.team} status={feed.teamStatus} reducedMotion={reducedMotion} reviewHref={reviewHref}
          onSelect={role => router.push(`/ekip/${ROLE_META[role].slug}`)}
          onTalk={() => window.dispatchEvent(new CustomEvent(AGENTS_OPEN, {detail: {tab: 'reporter'}}))}/>
        <StageTicker team={feed.team} now={now}/>
        {!feed.team && feed.teamStatus !== 'loading' && <div className="ag-stage-error" role="status"><span>Ekibin canlı durumu şu anda alınamıyor. Bağlantı kendiliğinden yeniden denenecek.</span>
          <button type="button" className="ag-ghost" onClick={feed.refresh}>Şimdi dene</button></div>}
      </div>
    </div>
    <div className={`ag-page-columns${caseId ? ' has-case' : ''}`}>
      <section className="ag-page-card" aria-labelledby="ag-page-queue">
        <div className="ag-page-card-head"><h2 id="ag-page-queue">Sıra</h2></div>
        <div className="ag-view"><AgentQueue queue={feed.queue} status={feed.queueStatus} team={feed.team} onOpenCase={setCaseId}/></div>
      </section>
      {caseId && <CaseCard caseId={caseId} onClose={() => setCaseId(null)}/>}
    </div>
  </section>;
}

export function AgentRolePage({role}: {role: AgentRole}) {
  const [caseId, setCaseId] = useState<string | null>(null);
  useEffect(() => {setCaseId(null);}, [role]);
  return <section className="ag-page">
    <TeamNav current={role}/>
    <div className={`ag-page-columns${caseId ? ' has-case' : ''}`}>
      <div className="ag-page-card"><div className="ag-view"><RoleWorkspace role={role} standalone onOpenCase={setCaseId}/></div></div>
      {caseId && <CaseCard caseId={caseId} onClose={() => setCaseId(null)}/>}
    </div>
  </section>;
}
