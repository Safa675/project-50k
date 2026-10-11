import {describe, expect, it} from 'vitest';
import {AgentDataError, type QueueItem, type TeamAgent, budgetView, dockBadge, dockLabel, dockRing, edgeActivity, fundFromPath,
  groupQueue, parseCase, parsePageVisit, parseQueue, parseTeam, parseWorkspace, pollDelay, relativeTime, roleFromSlug,
  scopeLabel} from '../lib/agents';

// Synthetic contract-shaped payloads only; no real fund values or names.
const NOW = '2026-10-10T19:30:00.000Z';
const CASE = '00000000-0000-4000-8000-0000000000c1';
const id = (n: number) => `00000000-0000-4000-8000-${String(n).padStart(12, '0')}`;
const ago = (seconds: number) => new Date(Date.parse(NOW) - seconds * 1000).toISOString();
const agent = (role: string, state: string, extra: Record<string, unknown> = {}) =>
  ({role, name_tr: role, state, activity_tr: null, case_id: null, fund_code: null, fund_name: null, since: null, ...extra});
const team = (overrides: Record<string, unknown> = {}) => ({scope: 'asof:2026-09-12', now: NOW,
  budget: {day: '2026-10-10', cap_usd: '3.00', spent_usd: '0.42', reserved_usd: '0.08', state: 'open'},
  agents: [agent('sentinel', 'working'), agent('hypothesizer', 'idle'), agent('skeptic', 'idle'), agent('verifier', 'idle'), agent('reporter', 'idle')],
  links: [], counts: {open_cases: 2, queued: 3, running: 1, done_today: 4}, ...overrides});
const task = (n: number, overrides: Partial<QueueItem> & Record<string, unknown> = {}) => ({task_id: id(n), case_id: CASE, fund_code: 'SYN1',
  fund_name: 'Sentetik fon', role: 'hypothesizer', title_tr: 'Sentetik görev', status: 'queued', priority: 50, source: 'system',
  created_at: ago(600), started_at: null, finished_at: null, ...overrides});

describe('team snapshot parsing', () => {
  it('keeps known roles once, maps unknown states and parses decimal budget strings', () => {
    const parsed = parseTeam(team({agents: [agent('sentinel', 'working'), agent('sentinel', 'idle'), agent('intruder', 'working'),
      agent('verifier', 'dreaming')]}));
    expect(parsed.agents.map(item => [item.role, item.state])).toEqual([['sentinel', 'working'], ['verifier', 'unknown']]);
    expect(parsed.budget).toEqual({day: '2026-10-10', cap_usd: 3, spent_usd: 0.42, reserved_usd: 0.08, state: 'open'});
    expect(parsed.scope).toBe('asof:2026-09-12');
    expect(parseTeam(team({scope: 'tomorrow'})).scope).toBeNull();
  });
  it('rejects a response without agents or a valid clock', () => {
    expect(() => parseTeam({now: NOW})).toThrow(AgentDataError);
    expect(() => parseTeam(team({now: 'later'}))).toThrow(AgentDataError);
    expect(() => parseTeam(null)).toThrow(AgentDataError);
  });
  it('drops malformed links and self links', () => {
    const parsed = parseTeam(team({links: [{from: 'sentinel', to: 'team', kind: 'case_opened', at: ago(10), case_id: CASE},
      {from: 'skeptic', to: 'skeptic', kind: 'note', at: ago(5)}, {from: 'ghost', to: 'team', kind: 'note', at: ago(5)},
      {from: 'verifier', to: 'reporter', kind: 'mystery', at: ago(5)}]}));
    expect(parsed.links.map(link => `${link.from}>${link.to}:${link.kind}`)).toEqual(['sentinel>team:case_opened', 'verifier>reporter:unknown']);
  });
});

describe('queue parsing and ordering', () => {
  it('drops tasks without a valid identifier or role and deduplicates', () => {
    const items = parseQueue({items: [task(1), task(1), {...task(2), task_id: 'not-a-uuid'}, {...task(3), role: 'boss'}, {...task(4), status: 'paused', source: 'admin'}]});
    expect(items.map(item => [item.task_id, item.status, item.source])).toEqual([[id(1), 'queued', 'system'], [id(4), 'unknown', 'system']]);
    expect(() => parseQueue({})).toThrow(AgentDataError);
  });
  it('lists running work, then user requests ahead of system work, budget waits and only today’s finished work', () => {
    const items = parseQueue({items: [
      task(1, {status: 'queued', priority: 50, created_at: ago(900)}),
      task(2, {status: 'queued', priority: 100, source: 'user', created_at: ago(60)}),
      task(3, {status: 'running', started_at: ago(30)}),
      task(4, {status: 'running', started_at: ago(90)}),
      task(5, {status: 'done', finished_at: ago(120)}),
      task(6, {status: 'done', finished_at: '2026-10-08T10:00:00.000Z'}),
      task(7, {status: 'waiting_budget'}),
      task(8, {status: 'failed', finished_at: ago(300)}),
      task(9, {status: 'queued', priority: 70, created_at: ago(30)}),
    ]});
    const groups = groupQueue(items, NOW);
    expect(groups.running.map(item => item.task_id)).toEqual([id(4), id(3)]);
    expect(groups.queued.map(item => item.task_id)).toEqual([id(2), id(9), id(1)]);
    expect(groups.waiting_budget.map(item => item.task_id)).toEqual([id(7)]);
    expect(groups.done.map(item => item.task_id)).toEqual([id(5)]);
    expect(groups.failed.map(item => item.task_id)).toEqual([id(8)]);
  });
});

describe('budget, dock ring and badge', () => {
  it('shows spending against the daily cap and explains a full budget', () => {
    expect(budgetView(null)).toBeNull();
    expect(budgetView({day: null, cap_usd: null, spent_usd: 0, reserved_usd: 0, state: null})).toBeNull();
    const open = budgetView({day: '2026-10-10', cap_usd: 3, spent_usd: 0.42, reserved_usd: 0.08, state: 'open'})!;
    expect(open.exhausted).toBe(false);
    expect(open.reason).toBeNull();
    expect(open.label).toMatch(/0,42.*3,00/);
    const daily = budgetView({day: '2026-10-10', cap_usd: 3, spent_usd: 2.9, reserved_usd: 0.1, state: 'open'})!;
    expect(daily.exhausted).toBe(true);
    expect(daily.reason).toContain('yarın');
    const total = budgetView({day: '2026-10-10', cap_usd: 3, spent_usd: 1, reserved_usd: 0, state: 'total_target'})!;
    expect(total.reason).toContain('Toplam bütçe hedefine');
  });
  it('maps team state to the floating button ring', () => {
    expect(dockRing(null, 'loading')).toBe('loading');
    expect(dockRing(null, 'unavailable')).toBe('unavailable');
    expect(dockRing(parseTeam(team()), 'ready')).toBe('working');
    const idleAgents = ['sentinel', 'hypothesizer', 'skeptic', 'verifier', 'reporter'].map(role => agent(role, 'idle'));
    expect(dockRing(parseTeam(team({agents: idleAgents})), 'ready')).toBe('idle');
    expect(dockRing(parseTeam(team({agents: idleAgents, budget: {cap_usd: 3, spent_usd: 3, reserved_usd: 0, state: 'exhausted'}})), 'ready')).toBe('waiting_budget');
    const off = [agent('sentinel', 'idle'), ...['hypothesizer', 'skeptic', 'verifier', 'reporter'].map(role => agent(role, 'off'))];
    expect(dockRing(parseTeam(team({agents: off})), 'ready')).toBe('off');
  });
  it('badges user requests by case, then an unseen page warning or note', () => {
    const queue = parseQueue({items: [task(1, {source: 'user', status: 'running', started_at: ago(5)}), task(2, {source: 'user'}),
      task(3, {source: 'user', case_id: id(99), status: 'waiting_budget'}), task(4, {source: 'user', status: 'done', finished_at: ago(5)})]});
    expect(dockBadge(queue, null, false)).toMatchObject({kind: 'requests', count: 2});
    const page = parsePageVisit({note_tr: 'Sentetik not.', warning_tr: 'Sentetik uyarı.', suggestions: [], case: null});
    expect(dockBadge([], page, false)).toMatchObject({kind: 'warning'});
    expect(dockBadge([], {...page, warning_tr: null}, false)).toMatchObject({kind: 'note'});
    expect(dockBadge([], page, true)).toBeNull();
    expect(dockLabel('working', parseTeam(team()), null)).toBe('Ajan ekibi ve Raportör, bir ajan çalışıyor');
  });
});

describe('workflow edges', () => {
  const agents = (states: Record<string, string>): TeamAgent[] => parseTeam(team({agents: ['sentinel', 'hypothesizer', 'skeptic', 'verifier', 'reporter']
    .map(role => agent(role, states[role] ?? 'idle'))})).agents;
  it('pulses direct messages, keeps older traffic highlighted and ignores stale links', () => {
    const links = parseTeam(team({links: [
      {from: 'hypothesizer', to: 'verifier', kind: 'hypothesis', at: ago(20)},
      {from: 'skeptic', to: 'verifier', kind: 'counter', at: ago(400)},
      {from: 'verifier', to: 'reporter', kind: 'verification', at: ago(5000)},
    ]})).links;
    expect(edgeActivity(links, NOW)).toEqual([
      {key: 'hypothesizer>verifier', reverse: false, fresh: true},
      {key: 'skeptic>verifier', reverse: false, fresh: false},
    ]);
  });
  it('spreads a team note along the sender’s edges but never sends the Raportör hand-off to the human step', () => {
    const links = parseTeam(team({links: [{from: 'sentinel', to: 'team', kind: 'case_opened', at: ago(10)},
      {from: 'reporter', to: 'team', kind: 'handoff', at: ago(10)}]})).links;
    expect(edgeActivity(links, NOW).map(item => item.key).sort()).toEqual(['sentinel>hypothesizer', 'sentinel>skeptic']);
  });
  it('pulses the inputs of an agent that is working', () => {
    expect(edgeActivity([], NOW, agents({verifier: 'working'})).map(item => item.key).sort()).toEqual(['hypothesizer>verifier', 'skeptic>verifier']);
    expect(edgeActivity([], NOW, agents({reporter: 'working'}))).toEqual([{key: 'verifier>reporter', reverse: false, fresh: true}]);
    expect(edgeActivity([], NOW, agents({sentinel: 'working'}))).toEqual([]);
  });
});

describe('cases, workspaces and page notes', () => {
  it('maps message payloads to plain-language labels and marks model-written text', () => {
    const detail = parseCase({case: {case_id: CASE, fund_code: 'SYN1', fund_name: 'Sentetik fon', status: 'reported', opened_by: 'sentinel',
      title_tr: 'Sentetik vaka', opened_at: ago(600), closed_at: null, decision_id: 7}, tasks: [task(1, {status: 'done', finished_at: ago(60)})],
    messages: [
      {message_id: 2, case_id: CASE, task_id: id(1), from_role: 'verifier', to_role: 'reporter', kind: 'verification', body_tr: 'Sentetik değerlendirme.',
        payload: {verdict: 'supported'}, model_id: 'synthetic-model', created_at: ago(30)},
      {message_id: 1, case_id: CASE, task_id: null, from_role: 'sentinel', to_role: 'team', kind: 'case_opened', body_tr: 'Sentetik vaka açıldı.',
        payload: {type: 'peer_divergence'}, model_id: null, created_at: ago(600)},
      {message_id: 3, case_id: CASE, from_role: 'hypothesizer', to_role: 'verifier', kind: 'hypothesis', body_tr: '', created_at: ago(20)},
    ]});
    expect(detail.case.has_decision).toBe(true);
    expect(detail.messages.map(item => [item.message_id, item.ai_written, item.hypothesis_type, item.verdict])).toEqual([
      ['1', false, 'Benzer fonlardan ayrışma', null], ['2', true, null, 'Kanıtla destekleniyor']]);
    expect(() => parseCase({case: {case_id: 'nope'}})).toThrow(AgentDataError);
  });
  it('accepts only the requested role’s workspace', () => {
    const workspace = parseWorkspace({role: 'verifier', current: null, tasks: [task(1, {role: 'verifier', status: 'running', started_at: ago(5)}),
      task(2, {role: 'skeptic'})], messages: []}, 'verifier');
    expect(workspace.current?.task_id).toBe(id(1));
    expect(workspace.tasks).toHaveLength(1);
    expect(() => parseWorkspace({role: 'skeptic', tasks: []}, 'verifier')).toThrow(AgentDataError);
  });
  it('keeps at most three distinct suggestions and a valid open case', () => {
    const page = parsePageVisit({note_tr: '  Sentetik not.  ', warning_tr: null, suggestions: [
      {label_tr: 'Bir', prompt_tr: 'Birinci soru?'}, {label_tr: 'Bir tekrar', prompt_tr: 'Birinci soru?'}, {label_tr: 'İki', prompt_tr: 'İkinci soru?'},
      {label_tr: 'Üç', prompt_tr: 'Üçüncü soru?'}, {label_tr: 'Dört', prompt_tr: 'Dördüncü soru?'}, {label_tr: 'Eksik'}],
    case: {case_id: CASE, status: 'investigating'}});
    expect(page.note_tr).toBe('Sentetik not.');
    expect(page.suggestions.map(item => item.label_tr)).toEqual(['Bir', 'İki', 'Üç']);
    expect(page.case).toEqual({case_id: CASE, status: 'investigating'});
    expect(parsePageVisit({suggestions: [], case: {case_id: 'x'}}).case).toBeNull();
  });
});

describe('polling, scope and paths', () => {
  it('polls every 2 s open and 15 s closed, pauses when hidden and backs off on failures', () => {
    expect(pollDelay(true, false)).toBe(2000);
    expect(pollDelay(false, false)).toBe(15000);
    expect(pollDelay(true, true)).toBeNull();
    expect(pollDelay(true, false, 2)).toBe(8000);
    expect(pollDelay(true, false, 9)).toBe(30000);
    expect(pollDelay(false, false, 9)).toBe(120000);
  });
  it('names the analysis date in Turkish and recognises fund pages', () => {
    expect(scopeLabel('asof:2026-09-12')).toEqual({date: '12 Eylül 2026', mode: 'İnceleme tarihi'});
    expect(scopeLabel('live')).toEqual({date: null, mode: 'Güncel görünüm'});
    expect(fundFromPath('/funds/SYN1')).toBe('SYN1');
    expect(fundFromPath('/funds')).toBeNull();
    expect(fundFromPath('/funds/syn1')).toBeNull();
    expect(fundFromPath('/stocks/SYN1')).toBeNull();
    expect(roleFromSlug('dogrulayici')).toBe('verifier');
    expect(roleFromSlug('verifier')).toBeNull();
  });
  it('writes relative times in Turkish', () => {
    expect(relativeTime(ago(10), NOW)).toBe('az önce');
    expect(relativeTime(ago(300), NOW)).toBe('5 dk önce');
    expect(relativeTime(ago(7200), NOW)).toBe('2 sa önce');
    expect(relativeTime(null, NOW)).toBe('Zamanı bilinmiyor');
  });
});
