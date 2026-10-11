'use client';

import {type FeedStatus, type QueueItem, ROLE_META, budgetView, groupQueue, relativeTime, taskStatusLabel, type TeamSnapshot} from '@/lib/agents';
import RoleGlyph from './RoleGlyph';

const GROUPS: {key: 'running' | 'queued' | 'waiting_budget' | 'done' | 'failed'; title: string}[] = [
  {key: 'running', title: 'Çalışıyor'}, {key: 'queued', title: 'Sırada'}, {key: 'waiting_budget', title: 'Bütçe bekliyor'},
  {key: 'done', title: 'Bugün tamamlandı'}, {key: 'failed', title: 'Tamamlanamadı'},
];

function when(item: QueueItem, now: string): string {
  if (item.status === 'running') return item.started_at ? `${relativeTime(item.started_at, now)} başladı` : 'Çalışıyor';
  if (item.status === 'done' || item.status === 'skipped' || item.status === 'failed') return item.finished_at ? relativeTime(item.finished_at, now) : '';
  return item.created_at ? `${relativeTime(item.created_at, now)} eklendi` : '';
}

export default function AgentQueue({queue, status, team, onOpenCase}: {
  queue: QueueItem[] | null; status: FeedStatus; team: TeamSnapshot | null; onOpenCase: (caseId: string) => void;
}) {
  if (!queue) {
    if (status === 'loading') return <p className="ag-empty" role="status">Ekibin iş sırası yükleniyor…</p>;
    return <div className="ag-empty" role="status"><strong>İş sırası şu anda alınamıyor.</strong><p>Bağlantı yeniden denenecek. Bu sırada ekip çalışmaya devam edebilir.</p></div>;
  }
  const now = team?.now ?? new Date().toISOString();
  const groups = groupQueue(queue, now);
  const budget = budgetView(team?.budget ?? null);
  const empty = GROUPS.every(group => groups[group.key].length === 0);
  return <div className="ag-queue">
    {budget?.exhausted && <p className="ag-budget-note" role="note">{budget.reason}</p>}
    {empty && <div className="ag-empty"><strong>Sırada bekleyen iş yok.</strong><p>Nöbetçi yeni bir vaka açtığında ya da siz Raportörden inceleme istediğinizde işler burada görünür.</p></div>}
    {GROUPS.map(group => {
      const items = groups[group.key];
      if (!items.length) return null;
      return <section key={group.key} className={`ag-queue-group is-${group.key}`} aria-labelledby={`ag-queue-${group.key}`}>
        <h3 id={`ag-queue-${group.key}`}>{group.title}<span className="ag-count">{items.length.toLocaleString('tr-TR')}</span></h3>
        <ul>{items.map(item => {
          const meta = ROLE_META[item.role];
          const content = <>
            <span className={`ag-avatar ag-avatar-sm ag-avatar-${item.role}`}><RoleGlyph role={item.role} size={item.role === 'reporter' ? 18 : 14}/></span>
            <span className="ag-task-main">
              <span className="ag-task-title">{item.title_tr}</span>
              <span className="ag-task-meta">
                <span>{meta.name}</span>
                {item.fund_code && <span className="ag-code">{item.fund_code}</span>}
                {item.fund_name && <span className="ag-task-fund">{item.fund_name}</span>}
              </span>
            </span>
            <span className="ag-task-side">
              {item.source === 'user' && <span className="ag-tag ag-tag-user">Kullanıcı isteği</span>}
              <span className={`ag-status is-${item.status}`}>{taskStatusLabel(item.status)}</span>
              <span className="ag-task-time">{when(item, now)}</span>
            </span>
          </>;
          return <li key={item.task_id} className={`ag-task is-${item.status}${item.source === 'user' ? ' is-user' : ''}`}>
            {item.case_id ? <button type="button" className="ag-task-row" onClick={() => onOpenCase(item.case_id!)}
              aria-label={`${item.title_tr}. ${meta.name}. ${taskStatusLabel(item.status)}${item.fund_code ? `. Fon ${item.fund_code}` : ''}${item.source === 'user' ? '. Kullanıcı isteği' : ''}. Vakanın akışını aç.`}>{content}</button> :
              <div className="ag-task-row">{content}</div>}
          </li>;
        })}</ul>
      </section>;
    })}
  </div>;
}
