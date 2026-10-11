import type {Page, Route} from '@playwright/test';

// Synthetic agent-team responses shaped like the DEC-035 contract. No real fund values or names.
export const CASE_ID = '00000000-0000-4000-8000-0000000000c1';
export const USER_CASE_ID = '00000000-0000-4000-8000-0000000000c2';
const task = (n: number) => `00000000-0000-4000-8000-${String(n).padStart(12, '0')}`;
const ago = (seconds: number) => new Date(Date.now() - seconds * 1000).toISOString();

export type AgentMockOptions = {unavailable?: boolean; budgetExhausted?: boolean; idle?: boolean};
export type AgentMock = {pageVisits: {path: string; fund_code: string | null}[]; requests: unknown[]; chatBodies: Record<string, unknown>[];
  teamCalls: () => number; queueCalls: () => number};

export function team(options: AgentMockOptions = {}) {
  const working = !options.idle;
  return {
    scope: 'live', now: new Date().toISOString(),
    budget: {day: new Date().toISOString().slice(0, 10), cap_usd: '3.00', spent_usd: options.budgetExhausted ? '3.00' : '0.42', reserved_usd: options.budgetExhausted ? '0' : '0.08',
      state: options.budgetExhausted ? 'exhausted' : 'open'},
    agents: [
      {role: 'sentinel', name_tr: 'Nöbetçi', state: working ? 'working' : 'idle', activity_tr: working ? 'Seçili tarihteki sonuçları tarıyor.' : null, case_id: null, fund_code: null, fund_name: null, since: ago(40)},
      {role: 'hypothesizer', name_tr: 'Hipotezci', state: working ? 'working' : 'idle', activity_tr: working ? 'Sentetik vaka için olası açıklamaları yazıyor.' : null, case_id: CASE_ID, fund_code: 'THF', fund_name: 'Synthetic browser fund', since: ago(25)},
      {role: 'skeptic', name_tr: 'Şüpheci', state: options.budgetExhausted ? 'waiting_budget' : working ? 'working' : 'idle', activity_tr: working ? 'Karşı açıklamaları ve testleri seçiyor.' : null, case_id: CASE_ID, fund_code: 'THF', fund_name: 'Synthetic browser fund', since: ago(18)},
      {role: 'verifier', name_tr: 'Doğrulayıcı', state: working ? 'waiting' : 'idle', activity_tr: null, case_id: null, fund_code: null, fund_name: null, since: null},
      {role: 'reporter', name_tr: 'Raportör', state: 'idle', activity_tr: null, case_id: null, fund_code: null, fund_name: null, since: null},
    ],
    links: working ? [
      {from: 'sentinel', to: 'team', kind: 'case_opened', at: ago(30), case_id: CASE_ID},
      {from: 'hypothesizer', to: 'verifier', kind: 'hypothesis', at: ago(12), case_id: CASE_ID},
      {from: 'skeptic', to: 'hypothesizer', kind: 'counter', at: ago(8), case_id: CASE_ID},
    ] : [],
    counts: {open_cases: 2, queued: 3, running: working ? 2 : 0, done_today: 4},
  };
}

export function queue() {
  return {items: [
    {task_id: task(1), case_id: CASE_ID, fund_code: 'THF', fund_name: 'Synthetic browser fund', role: 'hypothesizer', title_tr: 'Olası açıklamaları çıkar', status: 'running', priority: 50, source: 'system', created_at: ago(120), started_at: ago(25), finished_at: null},
    {task_id: task(2), case_id: CASE_ID, fund_code: 'THF', fund_name: 'Synthetic browser fund', role: 'skeptic', title_tr: 'Karşı açıklamaları ve testleri seç', status: 'running', priority: 50, source: 'system', created_at: ago(120), started_at: ago(18), finished_at: null},
    {task_id: task(3), case_id: CASE_ID, fund_code: 'THF', fund_name: 'Synthetic browser fund', role: 'verifier', title_tr: 'Açıklamaları kaynak ve hesaplamayla sına', status: 'queued', priority: 50, source: 'system', created_at: ago(120), started_at: null, finished_at: null},
    {task_id: task(4), case_id: USER_CASE_ID, fund_code: 'SYN1', fund_name: 'Sentetik test fonu', role: 'hypothesizer', title_tr: 'Kullanıcı isteği: sentetik fonu incele', status: 'queued', priority: 100, source: 'user', created_at: ago(60), started_at: null, finished_at: null},
    {task_id: task(5), case_id: CASE_ID, fund_code: 'THF', fund_name: 'Synthetic browser fund', role: 'reporter', title_tr: 'Raporu yaz', status: 'queued', priority: 50, source: 'system', created_at: ago(120), started_at: null, finished_at: null},
    {task_id: task(6), case_id: USER_CASE_ID, fund_code: 'SYN2', fund_name: 'Sentetik ikinci fon', role: 'reporter', title_tr: 'Raporu yaz', status: 'done', priority: 50, source: 'system', created_at: ago(900), started_at: ago(700), finished_at: ago(600)},
    {task_id: task(7), case_id: USER_CASE_ID, fund_code: 'SYN2', fund_name: 'Sentetik ikinci fon', role: 'verifier', title_tr: 'Açıklamaları kaynak ve hesaplamayla sına', status: 'waiting_budget', priority: 50, source: 'system', created_at: ago(300), started_at: null, finished_at: null},
  ]};
}

function messages() {
  return [
    {message_id: 1, case_id: CASE_ID, task_id: null, from_role: 'sentinel', to_role: 'team', kind: 'case_opened', body_tr: 'Sentetik fonda inceleme sınırını aşan bir fiyat gelişmesi görüldü; vaka açıldı.', payload: {}, model_id: null, prompt_version: null, created_at: ago(30), fund_code: 'THF'},
    {message_id: 2, case_id: CASE_ID, task_id: task(1), from_role: 'hypothesizer', to_role: 'verifier', kind: 'hypothesis', body_tr: 'Gelişme benzer fonlardan ayrışan bir fiyat hareketiyle açıklanabilir.', payload: {type: 'peer_divergence'}, model_id: 'synthetic-model', prompt_version: 'synthetic', created_at: ago(12), fund_code: 'THF'},
    {message_id: 3, case_id: CASE_ID, task_id: task(2), from_role: 'skeptic', to_role: 'hypothesizer', kind: 'counter', body_tr: 'Aynı günlerde fon türünün genelinde benzer bir hareket olup olmadığı sınanmalı.', payload: {type: 'market_wide_move'}, model_id: 'synthetic-model', prompt_version: 'synthetic', created_at: ago(8), fund_code: 'THF'},
  ];
}

export function workspace(role: string) {
  const all = messages();
  const tasks = queue().items.filter(item => item.role === role);
  return {role, current: tasks.find(item => item.status === 'running') ?? null, tasks,
    messages: all.filter(message => message.from_role === role || message.to_role === role || message.to_role === 'team')};
}

export function caseDetail(id: string) {
  return {case: {case_id: id, fund_code: 'THF', fund_name: 'Synthetic browser fund', status: 'investigating', opened_by: 'sentinel', priority: 50,
    title_tr: 'Sentetik fonda fiyat gelişmesi', opened_at: ago(30), closed_at: null, decision_id: null},
  tasks: queue().items.filter(item => item.case_id === id), messages: messages()};
}

export function pageVisit(fundCode: string | null) {
  return fundCode ? {note_tr: 'Bu fonda seçili tarihte inceleme sınırını aşan bir fiyat gelişmesi var. Ekip bu gelişmeyi şu anda inceliyor.',
    warning_tr: 'Son tarihte kullanılabilir fiyat yok; önceki fiyat kendi tarihiyle gösteriliyor.',
    suggestions: [{label_tr: 'Ne değişti?', prompt_tr: 'Bu fonda ne değişti?'}, {label_tr: 'Ekip neyi inceliyor?', prompt_tr: 'Ekip bu fonda neyi inceliyor?'}],
    case: {case_id: CASE_ID, status: 'investigating'}} :
    {note_tr: 'Ekip şu anda iki açık vaka üzerinde çalışıyor.', warning_tr: null,
      suggestions: [{label_tr: 'Ekip ne yapıyor?', prompt_tr: 'Ekip şu anda ne yapıyor?'}], case: null};
}

type Conversation = {thread_id: string; fund_code: string | null; items: Record<string, unknown>[]};

export async function mockAgents(page: Page, options: AgentMockOptions = {}): Promise<AgentMock> {
  const state: AgentMock & {team: number; queue: number} = {pageVisits: [], requests: [], chatBodies: [], team: 0, queue: 0,
    teamCalls: () => state.team, queueCalls: () => state.queue};
  const missing = (route: Route) => route.fulfill({status: 404, json: {detail: 'Not Found'}});
  await page.route('**/api/p/agents/team', route => {state.team++; return options.unavailable ? missing(route) : route.fulfill({json: team(options)});});
  await page.route('**/api/p/agents/queue**', route => {state.queue++; return options.unavailable ? missing(route) : route.fulfill({json: queue()});});
  await page.route('**/api/p/agents/workspace/**', route => {
    if (options.unavailable) return missing(route);
    const role = new URL(route.request().url()).pathname.split('/').at(-1)!;
    return route.fulfill({json: workspace(role)});
  });
  await page.route('**/api/p/agents/cases/**', route => options.unavailable ? missing(route) :
    route.fulfill({json: caseDetail(new URL(route.request().url()).pathname.split('/').at(-1)!)}));
  await page.route('**/api/p/agents/page-visit', route => {
    const body = route.request().postDataJSON();
    state.pageVisits.push(body);
    return options.unavailable ? missing(route) : route.fulfill({json: pageVisit(body.fund_code)});
  });
  await page.route('**/api/p/agents/requests', route => {
    state.requests.push(route.request().postDataJSON());
    return options.unavailable ? missing(route) : route.fulfill({json: {case_id: CASE_ID, queued: true}});
  });
  const conversations: Conversation[] = [];
  let counter = 0;
  await page.route('**/api/p/chat/threads**', route => {
    const fund = new URL(route.request().url()).searchParams.get('fund_code');
    return route.fulfill({json: {fund_code: fund, analysis_scope_key: 'live', items: conversations.filter(item => item.fund_code === fund).slice().reverse()
      .map(item => ({thread_id: item.thread_id, title: String(item.items[0]?.content ?? ''), created_at: ago(60), last_message_at: ago(30), message_count: item.items.length}))}});
  });
  await page.route(/\/api\/p\/chat\/[a-f0-9-]{36}(\?|$)/, route => {
    const url = new URL(route.request().url()), id = url.pathname.split('/').at(-1), fund = url.searchParams.get('fund_code');
    const item = conversations.find(entry => entry.thread_id === id && entry.fund_code === fund);
    return item ? route.fulfill({json: {thread_id: id, fund_code: fund, analysis_scope_key: 'live', items: item.items}}) : route.fulfill({status: 404, json: {detail: 'THREAD_NOT_FOUND'}});
  });
  await page.route('**/api/p/chat', route => {
    const body = route.request().postDataJSON();
    state.chatBodies.push(body);
    let item = conversations.find(entry => entry.thread_id === body.thread_id && entry.fund_code === body.fund_code);
    if (!item) {item = {thread_id: `00000000-0000-4000-8000-${String(++counter).padStart(12, '0')}`, fund_code: body.fund_code, items: []}; conversations.push(item);}
    const content = `Sentetik Raportör yanıtı: ${body.question}`;
    item.items.push({role: 'user', content: body.question, evidence_ids: [], message_id: String(item.items.length + 1), created_at: ago(1), status: 'VALID'},
      {role: 'assistant', content, evidence_ids: ['ev:synthetic-agent'], message_id: String(item.items.length + 2), created_at: ago(0), status: 'VALID'});
    return route.fulfill({contentType: 'text/event-stream', body:
      `event: thread\ndata: ${JSON.stringify({thread_id: item.thread_id, analysis_scope_key: 'live'})}\n\n` +
      'event: tool\ndata: {"name":"get_case_status"}\n\n' +
      `event: paragraph\ndata: ${JSON.stringify({index: 0, content, evidence_ids: ['ev:synthetic-agent']})}\n\n` +
      `event: answer\ndata: ${JSON.stringify({thread_id: item.thread_id, content, evidence_ids: ['ev:synthetic-agent'], evidence_labels: {'ev:synthetic-agent': 'Sentetik kanıt'}, model: 'synthetic-browser-model'})}\n\n`});
  });
  return state;
}

export async function login(page: Page) {
  await page.goto('/login');
  await page.getByLabel('E-posta').fill('synthetic-browser@example.invalid');
  await page.getByLabel('Parola', {exact: true}).fill('synthetic-browser-password');
  await page.getByRole('button', {name: 'Giriş yap', exact: true}).click();
  await page.waitForURL(/\/funds$/);
}
