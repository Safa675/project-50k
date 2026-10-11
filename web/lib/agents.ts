// Agent team client contract (DEC-035, docs/notes/agent-team-design-2026-10-10.md section 4).
// The server owns every number and every sentence; this module only validates the
// responses, maps internal states to plain Turkish and never exposes IDs or enums.

export const AGENT_ROLES = ['sentinel', 'hypothesizer', 'skeptic', 'verifier', 'reporter'] as const;
export type AgentRole = typeof AGENT_ROLES[number];
export type Participant = AgentRole | 'team' | 'human';
export type AgentState = 'idle' | 'working' | 'waiting' | 'waiting_budget' | 'off' | 'unknown';
export type TaskStatus = 'queued' | 'running' | 'done' | 'failed' | 'waiting_budget' | 'skipped' | 'unknown';
export type CaseStatus = 'open' | 'investigating' | 'reported' | 'closed' | 'unknown';
export type MessageKind = 'case_opened' | 'hypothesis' | 'counter' | 'test_plan' | 'test_result' | 'verification' |
  'report' | 'handoff' | 'note' | 'unknown';

export type TeamAgent = {role: AgentRole; name_tr: string; state: AgentState; activity_tr: string | null;
  case_id: string | null; fund_code: string | null; fund_name: string | null; since: string | null};
export type TeamLink = {from: Participant; to: Participant; kind: MessageKind; at: string; case_id: string | null};
export type TeamBudget = {day: string | null; cap_usd: number | null; spent_usd: number; reserved_usd: number; state: string | null};
export type TeamCounts = {open_cases: number; queued: number; running: number; done_today: number};
export type TeamSnapshot = {scope: string | null; now: string; budget: TeamBudget | null; agents: TeamAgent[];
  links: TeamLink[]; counts: TeamCounts};
export type QueueItem = {task_id: string; case_id: string | null; fund_code: string | null; fund_name: string | null;
  role: AgentRole; title_tr: string; status: TaskStatus; priority: number; source: 'system' | 'user';
  created_at: string | null; started_at: string | null; finished_at: string | null};
export type AgentMessage = {message_id: string; case_id: string | null; task_id: string | null; from_role: Participant;
  to_role: Participant; kind: MessageKind; body_tr: string; ai_written: boolean; created_at: string;
  fund_code: string | null; fund_name: string | null; hypothesis_type: string | null; verdict: string | null};
export type AgentCase = {case_id: string; fund_code: string | null; fund_name: string | null; status: CaseStatus;
  opened_by: 'sentinel' | 'user' | null; title_tr: string | null; opened_at: string | null; closed_at: string | null;
  has_decision: boolean};
export type CaseDetail = {case: AgentCase; tasks: QueueItem[]; messages: AgentMessage[]};
export type Workspace = {role: AgentRole; current: QueueItem | null; tasks: QueueItem[]; messages: AgentMessage[]};
export type Suggestion = {label_tr: string; prompt_tr: string};
export type PageVisit = {note_tr: string | null; warning_tr: string | null; suggestions: Suggestion[];
  case: {case_id: string; status: CaseStatus} | null};
export type InvestigationResult = {case_id: string; queued: boolean};

export class AgentDataError extends Error {
  constructor(public readonly code: string) {super(code); this.name = 'AgentDataError';}
}

const UUID = /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i;
const FUND = /^[A-Z0-9]{2,12}$/;
const SCOPE = /^(live|asof:\d{4}-\d{2}-\d{2})$/;
const STATES = new Set<string>(['idle', 'working', 'waiting', 'waiting_budget', 'off']);
const TASK_STATUSES = new Set<string>(['queued', 'running', 'done', 'failed', 'waiting_budget', 'skipped']);
const CASE_STATUSES = new Set<string>(['open', 'investigating', 'reported', 'closed']);
const KINDS = new Set<string>(['case_opened', 'hypothesis', 'counter', 'test_plan', 'test_result', 'verification',
  'report', 'handoff', 'note']);

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}
function text(value: unknown, max: number): string | null {
  if (typeof value !== 'string') return null;
  const trimmed = value.trim();
  return trimmed && trimmed.length <= max ? trimmed : null;
}
function time(value: unknown): string | null {
  return typeof value === 'string' && value.length <= 64 && Number.isFinite(Date.parse(value)) ? value : null;
}
function uuid(value: unknown): string | null {return typeof value === 'string' && UUID.test(value) ? value : null;}
function fund(value: unknown): string | null {return typeof value === 'string' && FUND.test(value) ? value : null;}
function count(value: unknown): number {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0 ? value : 0;
}
// Budget amounts may arrive as JSON numbers or as decimal strings.
export function money(value: unknown): number | null {
  if (typeof value === 'number') return Number.isFinite(value) && value >= 0 ? value : null;
  if (typeof value === 'string' && /^\d{1,9}(\.\d{1,12})?$/.test(value)) return Number(value);
  return null;
}
export function isRole(value: unknown): value is AgentRole {
  return typeof value === 'string' && (AGENT_ROLES as readonly string[]).includes(value);
}
function participant(value: unknown): Participant | null {
  return isRole(value) || value === 'team' || value === 'human' ? value : null;
}

function parseAgent(value: unknown): TeamAgent | null {
  if (!record(value) || !isRole(value.role)) return null;
  return {role: value.role, name_tr: text(value.name_tr, 40) ?? ROLE_META[value.role].name,
    state: typeof value.state === 'string' && STATES.has(value.state) ? value.state as AgentState : 'unknown',
    activity_tr: text(value.activity_tr, 400), case_id: uuid(value.case_id), fund_code: fund(value.fund_code),
    fund_name: text(value.fund_name, 200), since: time(value.since)};
}
function parseLink(value: unknown): TeamLink | null {
  if (!record(value)) return null;
  const from = participant(value.from), to = participant(value.to), at = time(value.at);
  if (!from || !to || !at || from === to) return null;
  return {from, to, at, case_id: uuid(value.case_id),
    kind: typeof value.kind === 'string' && KINDS.has(value.kind) ? value.kind as MessageKind : 'unknown'};
}

export function parseTeam(value: unknown): TeamSnapshot {
  if (!record(value) || !Array.isArray(value.agents)) throw new AgentDataError('TEAM_INVALID');
  const now = time(value.now);
  if (!now) throw new AgentDataError('TEAM_INVALID');
  const agents: TeamAgent[] = [];
  for (const item of value.agents.slice(0, 20)) {
    const agent = parseAgent(item);
    if (agent && !agents.some(existing => existing.role === agent.role)) agents.push(agent);
  }
  const links = Array.isArray(value.links) ? value.links.slice(0, 50).map(parseLink).filter((item): item is TeamLink => item !== null) : [];
  const budget = record(value.budget) ? {day: typeof value.budget.day === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value.budget.day) ? value.budget.day : null,
    cap_usd: money(value.budget.cap_usd), spent_usd: money(value.budget.spent_usd) ?? 0,
    reserved_usd: money(value.budget.reserved_usd) ?? 0, state: text(value.budget.state, 40)} : null;
  const counts = record(value.counts) ? value.counts : {};
  return {scope: typeof value.scope === 'string' && SCOPE.test(value.scope) ? value.scope : null, now, budget, agents, links,
    counts: {open_cases: count(counts.open_cases), queued: count(counts.queued), running: count(counts.running),
      done_today: count(counts.done_today)}};
}

function parseTask(value: unknown): QueueItem | null {
  if (!record(value) || !isRole(value.role)) return null;
  const id = uuid(value.task_id);
  if (!id) return null;
  return {task_id: id, case_id: uuid(value.case_id), fund_code: fund(value.fund_code), fund_name: text(value.fund_name, 200),
    role: value.role, title_tr: text(value.title_tr, 240) ?? ROLE_META[value.role].task,
    status: typeof value.status === 'string' && TASK_STATUSES.has(value.status) ? value.status as TaskStatus : 'unknown',
    priority: typeof value.priority === 'number' && Number.isFinite(value.priority) ? value.priority : 0,
    source: value.source === 'user' ? 'user' : 'system', created_at: time(value.created_at),
    started_at: time(value.started_at), finished_at: time(value.finished_at)};
}
export function parseQueue(value: unknown): QueueItem[] {
  if (!record(value) || !Array.isArray(value.items)) throw new AgentDataError('QUEUE_INVALID');
  const items: QueueItem[] = [];
  for (const item of value.items.slice(0, 100)) {
    const task = parseTask(item);
    if (task && !items.some(existing => existing.task_id === task.task_id)) items.push(task);
  }
  return items;
}

const HYPOTHESIS_TYPES: Record<string, string> = {
  peer_divergence: 'Benzer fonlardan ayrışma', flow_change: 'Fon akışında değişim',
  allocation_shift: 'Varlık dağılımında değişim', regulatory_action: 'Düzenleyici işlem',
  data_issue: 'Veri sorunu', market_wide_move: 'Piyasa geneli hareket',
};
const VERDICTS: Record<string, string> = {
  supported: 'Kanıtla destekleniyor', refuted: 'Kanıtla desteklenmiyor', undetermined: 'Belirsiz',
};
function parseMessage(value: unknown): AgentMessage | null {
  if (!record(value)) return null;
  const from = participant(value.from_role), to = participant(value.to_role) ?? 'team';
  const body = text(value.body_tr, 6000), created = time(value.created_at);
  const id = typeof value.message_id === 'number' && Number.isSafeInteger(value.message_id) ? String(value.message_id) :
    typeof value.message_id === 'string' && /^[A-Za-z0-9-]{1,64}$/.test(value.message_id) ? value.message_id : null;
  if (!from || !body || !created || !id) return null;
  const payload = record(value.payload) ? value.payload : {};
  const type = typeof payload.type === 'string' && HYPOTHESIS_TYPES[payload.type] ? HYPOTHESIS_TYPES[payload.type] : null;
  const rawVerdict = typeof payload.verdict === 'string' ? payload.verdict : typeof payload.rating === 'string' ? payload.rating : null;
  return {message_id: id, case_id: uuid(value.case_id), task_id: uuid(value.task_id), from_role: from, to_role: to,
    kind: typeof value.kind === 'string' && KINDS.has(value.kind) ? value.kind as MessageKind : 'unknown',
    body_tr: body, ai_written: typeof value.model_id === 'string' && value.model_id.length > 0, created_at: created,
    fund_code: fund(value.fund_code), fund_name: text(value.fund_name, 200), hypothesis_type: type,
    verdict: rawVerdict && VERDICTS[rawVerdict] ? VERDICTS[rawVerdict] : null};
}
function messages(value: unknown): AgentMessage[] {
  if (!Array.isArray(value)) return [];
  const items: AgentMessage[] = [];
  for (const item of value.slice(0, 200)) {
    const message = parseMessage(item);
    if (message && !items.some(existing => existing.message_id === message.message_id)) items.push(message);
  }
  return items.sort((a, b) => Date.parse(a.created_at) - Date.parse(b.created_at));
}
function tasks(value: unknown): QueueItem[] {
  return Array.isArray(value) ? value.slice(0, 100).map(parseTask).filter((item): item is QueueItem => item !== null) : [];
}

export function parseCase(value: unknown): CaseDetail {
  if (!record(value)) throw new AgentDataError('CASE_INVALID');
  const source = record(value.case) ? value.case : value;
  const id = uuid(source.case_id);
  if (!id) throw new AgentDataError('CASE_INVALID');
  return {case: {case_id: id, fund_code: fund(source.fund_code), fund_name: text(source.fund_name, 200),
    status: typeof source.status === 'string' && CASE_STATUSES.has(source.status) ? source.status as CaseStatus : 'unknown',
    opened_by: source.opened_by === 'user' ? 'user' : source.opened_by === 'sentinel' ? 'sentinel' : null,
    title_tr: text(source.title_tr, 240), opened_at: time(source.opened_at), closed_at: time(source.closed_at),
    has_decision: uuid(source.decision_id) !== null || typeof source.decision_id === 'number'},
  tasks: tasks(value.tasks), messages: messages(value.messages)};
}

export function parseWorkspace(value: unknown, role: AgentRole): Workspace {
  if (!record(value)) throw new AgentDataError('WORKSPACE_INVALID');
  if (value.role !== undefined && value.role !== role) throw new AgentDataError('WORKSPACE_INVALID');
  const list = tasks(Array.isArray(value.tasks) ? value.tasks : value.items).filter(item => item.role === role);
  const current = parseTask(value.current) ?? list.find(item => item.status === 'running') ?? null;
  return {role, current: current && current.role === role ? current : null, tasks: list, messages: messages(value.messages)};
}

export function parsePageVisit(value: unknown): PageVisit {
  if (!record(value)) throw new AgentDataError('PAGE_NOTE_INVALID');
  const suggestions: Suggestion[] = [];
  if (Array.isArray(value.suggestions)) for (const item of value.suggestions.slice(0, 6)) {
    if (!record(item)) continue;
    const label = text(item.label_tr, 90), prompt = text(item.prompt_tr, 400);
    if (label && prompt && suggestions.length < 3 && !suggestions.some(existing => existing.prompt_tr === prompt)) {
      suggestions.push({label_tr: label, prompt_tr: prompt});
    }
  }
  const caseId = record(value.case) ? uuid(value.case.case_id) : null;
  const caseStatus = record(value.case) && typeof value.case.status === 'string' && CASE_STATUSES.has(value.case.status) ?
    value.case.status as CaseStatus : 'unknown';
  return {note_tr: text(value.note_tr, 1200), warning_tr: text(value.warning_tr, 600), suggestions,
    case: caseId ? {case_id: caseId, status: caseStatus} : null};
}

export function parseInvestigation(value: unknown): InvestigationResult {
  if (!record(value) || !uuid(value.case_id)) throw new AgentDataError('REQUEST_INVALID');
  return {case_id: value.case_id as string, queued: value.queued === true};
}

// ---------- Plain-language vocabulary ----------

export type RoleMeta = {name: string; slug: string; short: string; description: string; inputs: string; task: string; ai: boolean};
export const ROLE_META: Record<AgentRole, RoleMeta> = {
  sentinel: {name: 'Nöbetçi', slug: 'nobetci', short: 'Fonları tarar, vaka açar', ai: false,
    description: 'Seçili tarihteki tamamlanmış hesaplamaları sürekli tarar. Bir fonda inceleme sınırını aşan bir gelişme gördüğünde vaka açar ve ekibe devreder. Yapay zekâ kullanmaz; sonuçları sabit kurallar hesaplar.',
    inputs: 'Seçili tarihe kadar yayımlanmış verilerle yapılmış hesaplamalar ve fonla eşleşen resmî duyurular.',
    task: 'Fonları tarama'},
  hypothesizer: {name: 'Hipotezci', slug: 'hipotezci', short: 'Olası açıklamaları çıkarır', ai: true,
    description: 'Vakadaki kanıtlara bakarak gelişmeyi açıklayabilecek en fazla üç olası açıklama yazar. Her açıklama dayandığı kanıta bağlanır; sayı yazmaz.',
    inputs: 'Nöbetçinin açtığı vaka ve vakaya ait hesaplanmış kanıt kayıtları.',
    task: 'Olası açıklamaları çıkarma'},
  skeptic: {name: 'Şüpheci', slug: 'supheci', short: 'Karşı açıklama ve sınama testi önerir', ai: true,
    description: 'Aynı kanıtlara karşıt bir gözle bakar. Gelişmeyi başka nedenlerin de açıklayıp açıklayamayacağını sorar ve Doğrulayıcının çalıştıracağı testleri sabit bir listeden seçer.',
    inputs: 'Vakanın kanıt kayıtları ve kodla çalıştırılabilen sınama testlerinin listesi.',
    task: 'Karşı açıklamaları ve testleri seçme'},
  verifier: {name: 'Doğrulayıcı', slug: 'dogrulayici', short: 'Açıklamaları kaynak ve hesaplamayla sınar', ai: true,
    description: 'İstenen testleri önce kodla çalıştırır; sayıların tamamı bu hesaplamalardan gelir. Ardından her açıklamayı kanıtla destekleniyor, desteklenmiyor veya belirsiz olarak değerlendirir.',
    inputs: 'Hipotezcinin açıklamaları, Şüphecinin testleri ve seçili tarihe kadar yayımlanmış veriler.',
    task: 'Açıklamaları sınama'},
  reporter: {name: 'Raportör', slug: 'raportor', short: 'Raporu yazar, sizinle konuşur', ai: true,
    description: 'Ekibin bulgularını kaynaklarıyla birlikte denetlenebilir bir rapora dönüştürür ve bir inceleme önerisi hazırlar. Sizinle konuşan tek ajandır; isteğinizi ekibin sırasına ekleyebilir.',
    inputs: 'Doğrulayıcının değerlendirmesi, vakanın kanıt kayıtları ve sizin sorularınız.',
    task: 'Raporu yazma'},
};
export const HUMAN_META = {name: 'İnsan kararı',
  description: 'Raportörün önerisi bir insan tarafından kabul edilir, gerekçesiyle değiştirilir veya reddedilir. Yapay zekânın ilk önerisi her durumda korunur.'};

export function roleFromSlug(slug: string): AgentRole | null {
  return AGENT_ROLES.find(role => ROLE_META[role].slug === slug) ?? null;
}
export function participantName(value: Participant): string {
  return value === 'team' ? 'Ekip' : value === 'human' ? 'İnsan incelemesi' : ROLE_META[value].name;
}

const STATE_LABELS: Record<AgentState, string> = {idle: 'Beklemede', working: 'Çalışıyor', waiting: 'Sırasını bekliyor',
  waiting_budget: 'Bütçe bekliyor', off: 'Yapay zekâ kapalı', unknown: 'Durumu bilinmiyor'};
export function agentStateLabel(state: AgentState, role?: AgentRole): string {
  if (state === 'off' && role && !ROLE_META[role].ai) return 'Kapalı';
  return STATE_LABELS[state] ?? STATE_LABELS.unknown;
}
const TASK_LABELS: Record<TaskStatus, string> = {queued: 'Sırada', running: 'Çalışıyor', done: 'Tamamlandı',
  failed: 'Tamamlanamadı', waiting_budget: 'Bütçe bekliyor', skipped: 'Atlandı', unknown: 'Durumu bilinmiyor'};
export function taskStatusLabel(status: TaskStatus): string {return TASK_LABELS[status] ?? TASK_LABELS.unknown;}
const CASE_LABELS: Record<CaseStatus, string> = {open: 'Açık', investigating: 'İnceleniyor', reported: 'Raporlandı',
  closed: 'Kapandı', unknown: 'Durumu bilinmiyor'};
export function caseStatusLabel(status: CaseStatus): string {return CASE_LABELS[status] ?? CASE_LABELS.unknown;}
const KIND_LABELS: Record<MessageKind, string> = {case_opened: 'Vaka açıldı', hypothesis: 'Olası açıklama',
  counter: 'Karşı açıklama', test_plan: 'Test planı', test_result: 'Test sonucu', verification: 'Değerlendirme',
  report: 'Rapor', handoff: 'Devir', note: 'Not', unknown: 'Mesaj'};
export function kindLabel(kind: MessageKind): string {return KIND_LABELS[kind] ?? KIND_LABELS.unknown;}

// ---------- Queue ordering ----------

export type QueueGroups = {running: QueueItem[]; queued: QueueItem[]; waiting_budget: QueueItem[]; done: QueueItem[]; failed: QueueItem[]};
function stamp(value: string | null): number {return value ? Date.parse(value) : 0;}
export function istanbulDay(value: string): string {
  return new Intl.DateTimeFormat('en-CA', {timeZone: 'Europe/Istanbul', year: 'numeric', month: '2-digit', day: '2-digit'})
    .format(new Date(value));
}
/** Running first, then queued (user requests first), budget waits, today's completed work and failures. */
export function groupQueue(items: QueueItem[], now: string): QueueGroups {
  const today = istanbulDay(now);
  const groups: QueueGroups = {running: [], queued: [], waiting_budget: [], done: [], failed: []};
  for (const item of items) {
    if (item.status === 'running') groups.running.push(item);
    else if (item.status === 'queued') groups.queued.push(item);
    else if (item.status === 'waiting_budget') groups.waiting_budget.push(item);
    else if ((item.status === 'done' || item.status === 'skipped') && item.finished_at && istanbulDay(item.finished_at) === today) groups.done.push(item);
    else if (item.status === 'failed' && (!item.finished_at || istanbulDay(item.finished_at) === today)) groups.failed.push(item);
  }
  const waiting = (a: QueueItem, b: QueueItem) => Number(b.source === 'user') - Number(a.source === 'user') ||
    b.priority - a.priority || stamp(a.created_at) - stamp(b.created_at);
  groups.running.sort((a, b) => stamp(a.started_at) - stamp(b.started_at));
  groups.queued.sort(waiting);
  groups.waiting_budget.sort(waiting);
  groups.done.sort((a, b) => stamp(b.finished_at) - stamp(a.finished_at));
  groups.failed.sort((a, b) => stamp(b.finished_at) - stamp(a.finished_at));
  return groups;
}

// ---------- Budget ----------

export type BudgetView = {cap: number; spent: number; reserved: number; spentRatio: number; reservedRatio: number;
  exhausted: boolean; reason: string | null; label: string};
export function usd(value: number): string {
  return new Intl.NumberFormat('tr-TR', {style: 'currency', currency: 'USD', minimumFractionDigits: 2, maximumFractionDigits: 2}).format(value);
}
export function budgetView(budget: TeamBudget | null): BudgetView | null {
  if (!budget || budget.cap_usd === null || budget.cap_usd <= 0) return null;
  const cap = budget.cap_usd, spent = budget.spent_usd, reserved = budget.reserved_usd;
  const state = budget.state?.toLowerCase() ?? '';
  const total = state.includes('total');
  const exhausted = total || ['exhausted', 'waiting_budget', 'closed'].includes(state) || spent + reserved >= cap;
  return {cap, spent, reserved, spentRatio: Math.min(1, spent / cap), reservedRatio: Math.min(1 - Math.min(1, spent / cap), reserved / cap),
    exhausted, reason: total ? 'Toplam bütçe hedefine ulaşıldı. Yapay zekâ adımları yeni bir onay bekliyor.' :
      exhausted ? 'Bugünün bütçesi doldu. Yapay zekâ adımları yarın kaldığı yerden devam eder.' : null,
    label: `${usd(spent)} / ${usd(cap)}`};
}

// ---------- Dock signal ----------

export type FeedStatus = 'loading' | 'ready' | 'unavailable' | 'invalid' | 'signed-out';
export type DockRing = 'loading' | 'working' | 'idle' | 'waiting_budget' | 'off' | 'unavailable';
export function dockRing(team: TeamSnapshot | null, status: FeedStatus): DockRing {
  if (!team) return status === 'loading' ? 'loading' : 'unavailable';
  if (team.agents.some(agent => agent.state === 'working')) return 'working';
  const view = budgetView(team.budget);
  if (team.agents.some(agent => agent.state === 'waiting_budget') || view?.exhausted) return 'waiting_budget';
  const ai = team.agents.filter(agent => ROLE_META[agent.role].ai);
  if (ai.length > 0 && ai.every(agent => agent.state === 'off')) return 'off';
  return 'idle';
}
export type DockBadge = {kind: 'requests' | 'warning' | 'note'; count: number; label: string} | null;
export function dockBadge(queue: QueueItem[] | null, page: PageVisit | null, pageSeen: boolean): DockBadge {
  const active = (queue ?? []).filter(item => item.source === 'user' && (item.status === 'running' || item.status === 'queued' || item.status === 'waiting_budget'));
  const cases = new Set(active.map(item => item.case_id ?? item.task_id)).size;
  if (cases > 0) return {kind: 'requests', count: cases, label: cases === 1 ? 'Bir kullanıcı isteği işleniyor' : `${cases} kullanıcı isteği işleniyor`};
  if (!pageSeen && page?.warning_tr) return {kind: 'warning', count: 1, label: 'Bu sayfa için bir uyarı var'};
  if (!pageSeen && (page?.note_tr || (page?.suggestions.length ?? 0) > 0)) return {kind: 'note', count: 1, label: 'Bu sayfa için bir not var'};
  return null;
}
export function dockLabel(ring: DockRing, team: TeamSnapshot | null, badge: DockBadge): string {
  const working = team?.agents.filter(agent => agent.state === 'working').length ?? 0;
  const state = ring === 'working' ? (working === 1 ? 'bir ajan çalışıyor' : `${working} ajan çalışıyor`) :
    ring === 'idle' ? 'ekip beklemede' : ring === 'waiting_budget' ? 'ekip bütçe bekliyor' :
    ring === 'off' ? 'yapay zekâ kapalı' : ring === 'loading' ? 'durum yükleniyor' : 'durum alınamadı';
  return `Ajan ekibi ve Raportör, ${state}${badge ? `. ${badge.label}` : ''}`;
}

// ---------- Polling ----------

export function pollDelay(open: boolean, hidden: boolean, failures = 0): number | null {
  if (hidden) return null;
  const base = open ? 2000 : 15000;
  if (failures <= 0) return base;
  return Math.min(base * 2 ** Math.min(failures, 5), open ? 30000 : 120000);
}

// ---------- Stage edges ----------

// The workflow graph: Nöbetçi → (Hipotezci ∥ Şüpheci) → Doğrulayıcı → Raportör → İnsan kararı.
// Hipotezci and Şüpheci work in parallel and exchange no messages, so no edge joins them.
export type EdgeKey = 'sentinel>hypothesizer' | 'sentinel>skeptic' | 'hypothesizer>verifier' | 'skeptic>verifier' |
  'verifier>reporter' | 'reporter>human';
export const STAGE_EDGES: {key: EdgeKey; from: AgentRole; to: AgentRole | 'human'}[] = [
  {key: 'sentinel>hypothesizer', from: 'sentinel', to: 'hypothesizer'},
  {key: 'sentinel>skeptic', from: 'sentinel', to: 'skeptic'},
  {key: 'hypothesizer>verifier', from: 'hypothesizer', to: 'verifier'},
  {key: 'skeptic>verifier', from: 'skeptic', to: 'verifier'},
  {key: 'verifier>reporter', from: 'verifier', to: 'reporter'},
  {key: 'reporter>human', from: 'reporter', to: 'human'},
];
/** The edges whose upstream output a working agent is reading right now. */
const INPUT_EDGES: Record<AgentRole, EdgeKey[]> = {
  sentinel: [], hypothesizer: ['sentinel>hypothesizer'], skeptic: ['sentinel>skeptic'],
  verifier: ['hypothesizer>verifier', 'skeptic>verifier'], reporter: ['verifier>reporter'],
};
export type EdgeActivity = {key: EdgeKey; reverse: boolean; fresh: boolean};
/**
 * Maps recent interactions and current work onto the drawn workflow edges. `fresh` edges pulse: a message crossed
 * them in the last `freshSeconds`, or the agent at their end is working on what came along them. Older traffic
 * within `recentSeconds` stays highlighted without motion.
 */
export function edgeActivity(links: TeamLink[], now: string, agents: TeamAgent[] = [], freshSeconds = 90,
  recentSeconds = 900): EdgeActivity[] {
  const current = Date.parse(now), result = new Map<EdgeKey, EdgeActivity>();
  const add = (key: EdgeKey, reverse: boolean, fresh: boolean) => {
    const existing = result.get(key);
    if (!existing || (fresh && !existing.fresh)) result.set(key, {key, reverse, fresh});
  };
  for (const link of links) {
    const age = (current - Date.parse(link.at)) / 1000;
    if (!(age <= recentSeconds) || age < -60) continue;
    const fresh = age <= freshSeconds;
    let matched = false;
    for (const edge of STAGE_EDGES) {
      if (edge.from === link.from && edge.to === link.to) {add(edge.key, false, fresh); matched = true;}
      else if (edge.from === link.to && edge.to === link.from) {add(edge.key, true, fresh); matched = true;}
    }
    // A note addressed to the whole team travels along the sender's outgoing edges. The Raportör's hand-off of a
    // user request goes back to the team, not to the human reviewer, so it draws no forward edge.
    if (!matched && link.to === 'team' && isRole(link.from) && link.from !== 'reporter') {
      for (const edge of STAGE_EDGES) if (edge.from === link.from) add(edge.key, false, fresh);
    }
  }
  for (const agent of agents) if (agent.state === 'working') for (const key of INPUT_EDGES[agent.role]) add(key, false, true);
  return [...result.values()];
}

// ---------- Time and scope ----------

export function relativeTime(value: string | null, now: string | number): string {
  if (!value) return 'Zamanı bilinmiyor';
  const seconds = Math.round(((typeof now === 'number' ? now : Date.parse(now)) - Date.parse(value)) / 1000);
  if (seconds < 45) return 'az önce';
  if (seconds < 3600) return `${Math.max(1, Math.round(seconds / 60))} dk önce`;
  if (seconds < 86400) return `${Math.round(seconds / 3600)} sa önce`;
  return new Intl.DateTimeFormat('tr-TR', {day: 'numeric', month: 'short', timeZone: 'Europe/Istanbul'}).format(new Date(value));
}
export function clockTime(value: string): string {
  return new Intl.DateTimeFormat('tr-TR', {day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: 'Europe/Istanbul'}).format(new Date(value));
}
export function scopeLabel(scope: string | null): {date: string | null; mode: string} {
  if (scope === 'live') return {date: null, mode: 'Güncel görünüm'};
  const match = scope ? /^asof:(\d{4}-\d{2}-\d{2})$/.exec(scope) : null;
  const day = match ? new Date(`${match[1]}T12:00:00+03:00`) : null;
  if (!day || !Number.isFinite(day.getTime())) return {date: null, mode: 'İnceleme tarihi bilinmiyor'};
  return {date: new Intl.DateTimeFormat('tr-TR', {day: 'numeric', month: 'long', year: 'numeric', timeZone: 'Europe/Istanbul'}).format(day),
    mode: 'İnceleme tarihi'};
}
export function fundFromPath(path: string): string | null {
  const match = /^\/funds\/([A-Z0-9]{2,12})\/?$/.exec(path);
  return match ? match[1] : null;
}

export const AGENTS_REFRESH = 'blackswan-agents-refresh';
export const AGENTS_OPEN = 'blackswan-agents-open';
/** Closes the panel, e.g. when a link inside it points at a section of the current page. */
export const AGENTS_CLOSE = 'blackswan-agents-close';

export function requestError(status: number, code?: string | null): string {
  if (status === 401) return 'Oturumunuz sona erdi. Yeniden giriş yapın.';
  if (status === 403 || code === 'CSRF_REJECTED') return 'Oturum doğrulanamadı. Sayfayı yenileyip yeniden deneyin.';
  if (status === 429) return 'Saatlik inceleme isteği sınırına ulaşıldı. Bir süre sonra yeniden deneyin.';
  if (status === 404) return 'Bu fon için ekipten inceleme istenemedi.';
  return 'İstek şu anda gönderilemedi. Yeniden deneyin.';
}
