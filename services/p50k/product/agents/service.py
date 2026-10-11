"""Read models, page notes and the one bounded user action of the agent team (DEC-035).

Every function receives the analysis scope chosen by the server from the request's
cookie view, never from the client body, and reads only that view's cases. Nothing
here calls a model: page notes and statuses are built from stored records.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import re
from typing import Any
from uuid import UUID

from p50k.product.agents import control, llm, store
from p50k.product.agents.config import AgentConfig
from p50k.product.agents.vocabulary import (ACTIVITY_TR, AI_OFF_ACTIVITY_TR, AI_ROLES, CASE_STATUS_TR, COUNTER_TYPE_TR,
                                            DECISION_TR, HYPOTHESIS_TYPE_TR, PAGE_VISIT_PRIORITY, REOPEN_CLOSE_NOTE_TR,
                                            REOPEN_NOTE_TR, REQUEST_NOTE_TR,
                                            ROLE_DESCRIPTIONS, ROLE_NAMES, ROLES, TASK_STATUS_TR, USER_PRIORITY,
                                            VERDICT_TR, WAIT_REASON_TR)
from p50k.product.analysis_context import use_analysis_date
from p50k.product.db import connect
from p50k.product.settings import Settings

FUND = re.compile(r'^[A-Z0-9]{2,12}$')
REQUEST_LIMIT_PER_HOUR = 10
REQUEST_REPEAT_MINUTES = 10
PAGE_VISIT_REPEAT_MINUTES = 5
PAGE_VISIT_LIMIT_PER_HOUR = 120
SENTINEL_ACTIVE_SECONDS = 90
MIN_RESERVATION_USD = Decimal('0.05')
DATA_DETECTORS = {'AN-DQ-001', 'AN-DQ-002'}
ROLE_ORDER = {role: index for index, role in enumerate(ROLES)}


class AgentRequestError(Exception):
    """A rejected user action with a stable code and HTTP status; no data is changed."""

    def __init__(self, code: str, status: int):
        self.code, self.status = code, status
        super().__init__(code)


def iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def money(value: Any) -> float:
    return float(round(Decimal(value or 0), 4))


def valid_case_id(value: str) -> str | None:
    try:
        return str(UUID(value))
    except (ValueError, TypeError, AttributeError):
        return None


def read_only(connection) -> None:
    connection.execute('SET TRANSACTION READ ONLY')
    connection.execute("SET LOCAL statement_timeout='5s'")


# ---------- Budget ----------

def budget_state(connection, config: AgentConfig) -> dict[str, Any]:
    """Today's agent bucket (Istanbul date) and the overall target, without creating anything."""
    day = llm.istanbul_today()
    row = connection.execute('SELECT cap_usd,spent_usd,reserved_usd FROM ai.budget_buckets WHERE bucket=%s',
                             (llm.daily_bucket(day),)).fetchone()
    cap, spent, reserved = (Decimal(row[0]), Decimal(row[1]), Decimal(row[2])) if row else \
        (config.daily_cap_usd, Decimal(0), Decimal(0))
    total = Decimal(connection.execute(
        'SELECT COALESCE(sum(spent_usd+reserved_usd),0) FROM ai.budget_buckets').fetchone()[0])
    if config.mode == 'off':
        state = 'off'
    elif total + MIN_RESERVATION_USD > config.total_target_usd:
        state = 'total_target'
    elif cap - spent - reserved < MIN_RESERVATION_USD:
        state = 'exhausted'
    else:
        state = 'available'
    return {'day': day.isoformat(), 'cap_usd': money(cap), 'spent_usd': money(spent), 'reserved_usd': money(reserved),
            'state': state}


# ---------- Shared row shapes ----------

TASK_COLUMNS = """task.task_id,task.case_id,item.fund_code,fund.name,task.role,task.title_tr,task.status,task.priority,
    task.source,task.created_at,task.started_at,task.finished_at,task.error_class"""
TASK_FROM = """FROM agents.tasks task JOIN agents.cases item USING(case_id)
    JOIN ref.funds fund ON fund.fund_code=item.fund_code"""


def task_item(row) -> dict[str, Any]:
    status, error = row[6], row[12]
    return {'task_id': str(row[0]), 'case_id': str(row[1]), 'fund_code': row[2], 'fund_name': row[3], 'role': row[4],
            'role_tr': ROLE_NAMES[row[4]], 'title_tr': row[5], 'status': status, 'status_tr': TASK_STATUS_TR[status],
            'priority': row[7], 'source': row[8], 'created_at': iso(row[9]), 'started_at': iso(row[10]),
            'finished_at': iso(row[11]),
            'wait_reason_tr': WAIT_REASON_TR.get(error) if status == 'waiting_budget' else None}


MESSAGE_COLUMNS = """message.message_id,message.case_id,message.task_id,message.from_role,message.to_role,message.kind,
    message.body_tr,message.payload,message.model_id,message.created_at,item.fund_code,fund.name"""
MESSAGE_FROM = """FROM agents.messages message JOIN agents.cases item USING(case_id)
    JOIN ref.funds fund ON fund.fund_code=item.fund_code"""


def message_item(row) -> dict[str, Any]:
    """Rendered text plus the two categorical labels the interface maps; no raw payload."""
    payload = row[7] or {}
    kind = row[5]
    safe: dict[str, Any] = {}
    if kind in {'hypothesis', 'counter'} and isinstance(payload.get('type'), str):
        safe['type'] = payload['type']
    if kind == 'verification' and payload.get('verdict') in VERDICT_TR:
        safe['verdict'] = payload['verdict']
    return {'message_id': row[0], 'case_id': str(row[1]), 'task_id': str(row[2]) if row[2] else None,
            'from_role': row[3], 'to_role': row[4], 'kind': kind, 'body_tr': row[6], 'payload': safe,
            'model_id': row[8], 'ai_written': row[8] is not None, 'created_at': iso(row[9]),
            'fund_code': row[10], 'fund_name': row[11]}


# ---------- Team ----------

def team(settings: Settings, scope: str, config: AgentConfig | None = None) -> dict[str, Any]:
    config = config or AgentConfig.from_env()
    now = datetime.now(timezone.utc)
    with connect(settings) as connection:
        read_only(connection)
        team_control = control.state(connection)
        budget = budget_state(connection, config)
        current = {row[4]: row for row in connection.execute(f"""SELECT DISTINCT ON (task.role) {TASK_COLUMNS}
            {TASK_FROM} WHERE item.analysis_scope_key=%s AND task.status IN ('running','waiting_budget')
              AND (task.status<>'running' OR task.lease_until>now())
            ORDER BY task.role,(task.status='running') DESC,task.started_at DESC NULLS LAST,task.created_at DESC""",
            (scope,)).fetchall()}
        queued = dict(connection.execute("""SELECT task.role,count(*) FROM agents.tasks task JOIN agents.cases item USING(case_id)
            WHERE item.analysis_scope_key=%s AND task.status='queued' AND item.status IN ('open','investigating')
            GROUP BY task.role""", (scope,)).fetchall())
        last = {row[4]: row for row in connection.execute(f"""SELECT DISTINCT ON (task.role) {TASK_COLUMNS}
            {TASK_FROM} WHERE item.analysis_scope_key=%s AND task.finished_at IS NOT NULL AND task.role<>'sentinel'
            ORDER BY task.role,task.finished_at DESC""", (scope,)).fetchall()}
        scan = connection.execute("""SELECT funds_scanned,cases_opened,detector_run_id,finished_at FROM agents.sentinel_scans
            WHERE analysis_scope_key=%s ORDER BY finished_at DESC LIMIT 1""", (scope,)).fetchone()
        opened = connection.execute("""SELECT item.case_id,item.fund_code,fund.name,item.opened_at FROM agents.cases item
            JOIN ref.funds fund USING(fund_code) WHERE item.analysis_scope_key=%s AND item.opened_by='sentinel'
            ORDER BY item.opened_at DESC LIMIT 1""", (scope,)).fetchone()
        counts = connection.execute("""SELECT
            (SELECT count(*) FROM agents.cases WHERE analysis_scope_key=%(scope)s AND status IN ('open','investigating')),
            (SELECT count(*) FROM agents.tasks task JOIN agents.cases item USING(case_id) WHERE item.analysis_scope_key=%(scope)s
                AND task.status IN ('queued','waiting_budget') AND item.status IN ('open','investigating')),
            (SELECT count(*) FROM agents.tasks task JOIN agents.cases item USING(case_id) WHERE item.analysis_scope_key=%(scope)s
                AND task.status='running'),
            (SELECT count(*) FROM agents.tasks task JOIN agents.cases item USING(case_id) WHERE item.analysis_scope_key=%(scope)s
                AND task.status='done' AND task.role<>'sentinel'
                AND (task.finished_at AT TIME ZONE 'Europe/Istanbul')::date=(now() AT TIME ZONE 'Europe/Istanbul')::date)""",
            {'scope': scope}).fetchone()
        links = connection.execute(f"""SELECT message.from_role,message.to_role,message.kind,message.created_at,message.case_id
            FROM agents.messages message JOIN agents.cases item USING(case_id)
            WHERE item.analysis_scope_key=%s ORDER BY message.message_id DESC LIMIT 20""", (scope,)).fetchall()
    agents = [sentinel_agent(scan, opened, counts[0], now)]
    for role in AI_ROLES:
        agents.append(ai_agent(role, current.get(role), queued.get(role, 0), last.get(role), config))
    if team_control['paused']:
        for agent in agents:
            if agent['role'] == 'sentinel' or agent['state'] != 'working':
                agent.update(state='waiting', activity_tr='Ekip durduruldu; sıradaki işler devam etmeyi bekliyor.')
    return {'scope': scope, 'now': now.isoformat(), 'budget': budget, 'agents': agents,
            'control': team_control,
            'links': [{'from': row[0], 'to': row[1], 'kind': row[2], 'at': iso(row[3]), 'case_id': str(row[4])}
                      for row in links],
            'counts': {'open_cases': counts[0], 'queued': counts[1], 'running': counts[2], 'done_today': counts[3]}}


def sentinel_agent(scan, opened, open_cases: int, now: datetime) -> dict[str, Any]:
    agent = {'role': 'sentinel', 'name_tr': ROLE_NAMES['sentinel'], 'state': 'idle', 'activity_tr': None,
             'case_id': None, 'fund_code': None, 'fund_name': None, 'since': None}
    if opened:
        agent.update(case_id=str(opened[0]), fund_code=opened[1], fund_name=opened[2])
    if not scan:
        agent['activity_tr'] = 'Seçili tarih için ilk tarama bekleniyor.'
        return agent
    agent['since'] = iso(scan[3])
    if (now - scan[3]).total_seconds() <= SENTINEL_ACTIVE_SECONDS:
        agent['state'] = 'working'
    if scan[2] is None:
        agent['activity_tr'] = 'Seçili tarih için tamamlanmış hesaplama bekleniyor.'
    else:
        agent['activity_tr'] = (f'Seçili tarihteki hesaplamayı tarıyor: {scan[0]} fon tarandı, '
                                f'{open_cases} vaka açık.')
    return agent


def ai_agent(role: str, current, queued: int, last, config: AgentConfig) -> dict[str, Any]:
    agent = {'role': role, 'name_tr': ROLE_NAMES[role], 'state': 'idle', 'activity_tr': None, 'case_id': None,
             'fund_code': None, 'fund_name': None, 'since': None}
    if current is not None:
        item = task_item(current)
        agent.update(case_id=item['case_id'], fund_code=item['fund_code'], fund_name=item['fund_name'])
        if item['status'] == 'running':
            agent.update(state='working', activity_tr=ACTIVITY_TR[role], since=item['started_at'])
        else:
            agent.update(state='waiting_budget', since=item['created_at'],
                         activity_tr=item['wait_reason_tr'] or WAIT_REASON_TR['DAILY_BUDGET'])
        return agent
    if config.mode == 'off':
        agent.update(state='off', activity_tr=AI_OFF_ACTIVITY_TR)
        return agent
    if queued:
        agent.update(state='waiting', activity_tr=f'Sırada {queued} görev var.')
    if last is not None:
        item = task_item(last)
        if not queued:
            agent['activity_tr'] = f"Son iş: {item['title_tr']} ({item['status_tr'].lower()})."
        agent.update(case_id=item['case_id'], fund_code=item['fund_code'], fund_name=item['fund_name'],
                     since=item['finished_at'])
    elif not queued:
        agent['activity_tr'] = 'Yeni vaka bekliyor.'
    return agent


# ---------- Queue, case and workspace ----------

def queue(settings: Settings, scope: str, limit: int = 30) -> dict[str, Any]:
    """Running and waiting work in claim order, then the latest finished work."""
    limit = max(1, min(100, limit))
    finished_quota = min(10, max(1, limit // 3))
    with connect(settings) as connection:
        read_only(connection)
        finished = connection.execute(f"""SELECT {TASK_COLUMNS} {TASK_FROM}
            WHERE item.analysis_scope_key=%s AND task.role<>'sentinel' AND task.finished_at IS NOT NULL
            ORDER BY task.finished_at DESC,task.task_id LIMIT %s""", (scope, finished_quota)).fetchall()
        active = connection.execute(f"""SELECT {TASK_COLUMNS} {TASK_FROM}
            WHERE item.analysis_scope_key=%s AND task.role<>'sentinel'
              AND task.status IN ('running','queued','waiting_budget') AND item.status IN ('open','investigating')
            ORDER BY (task.status='running') DESC,task.priority DESC,task.created_at,task.task_id LIMIT %s""",
            (scope, limit - len(finished))).fetchall()
    return {'scope': scope, 'items': [task_item(row) for row in active + finished]}


def decision_view(connection, decision_id: int | None) -> dict[str, Any] | None:
    if decision_id is None:
        return None
    row = connection.execute("""SELECT decision.decision_value,effective.effective_value,effective.effective_source,
            COALESCE(effective.has_current_review,false)
        FROM ai.decisions decision LEFT JOIN ai.effective_decisions effective ON effective.packet_id=decision.packet_id
        WHERE decision.decision_id=%s""", (decision_id,)).fetchone()
    if not row:
        return None
    effective = row[1] or row[0]
    return {'proposal': row[0], 'proposal_tr': DECISION_TR.get(row[0]), 'effective': effective,
            'effective_tr': DECISION_TR.get(effective), 'human_reviewed': bool(row[3]),
            'decided_by': 'HUMAN' if row[2] == 'HUMAN' else 'AI'}


def case_detail(settings: Settings, scope: str, case_id: str) -> dict[str, Any] | None:
    case_id = valid_case_id(case_id)
    if case_id is None:
        return None
    with connect(settings) as connection:
        read_only(connection)
        row = connection.execute("""SELECT item.case_id,item.fund_code,fund.name,item.status,item.opened_by,item.title_tr,
                item.opened_at,item.closed_at,item.decision_id,item.priority
            FROM agents.cases item JOIN ref.funds fund USING(fund_code)
            WHERE item.case_id=%s AND item.analysis_scope_key=%s""", (case_id, scope)).fetchone()
        if not row:
            return None
        tasks = connection.execute(f"""SELECT {TASK_COLUMNS} {TASK_FROM} WHERE task.case_id=%s""", (case_id,)).fetchall()
        messages = connection.execute(f"""SELECT {MESSAGE_COLUMNS} {MESSAGE_FROM}
            WHERE message.case_id=%s ORDER BY message.message_id LIMIT 200""", (case_id,)).fetchall()
        decision = decision_view(connection, row[8])
    return {'case': {'case_id': str(row[0]), 'fund_code': row[1], 'fund_name': row[2], 'status': row[3],
                     'status_tr': CASE_STATUS_TR[row[3]], 'opened_by': row[4], 'title_tr': row[5],
                     'opened_at': iso(row[6]), 'closed_at': iso(row[7]), 'decision_id': row[8],
                     'decision': decision, 'priority': row[9]},
            'tasks': sorted((task_item(task) for task in tasks), key=lambda item: ROLE_ORDER[item['role']]),
            'messages': [message_item(message) for message in messages]}


def workspace(settings: Settings, scope: str, role: str, limit: int = 20) -> dict[str, Any]:
    limit = max(1, min(50, limit))
    with connect(settings) as connection:
        read_only(connection)
        tasks = connection.execute(f"""SELECT {TASK_COLUMNS} {TASK_FROM}
            WHERE item.analysis_scope_key=%s AND task.role=%s
            ORDER BY (task.status='running') DESC,(task.status IN ('queued','waiting_budget')) DESC,
                COALESCE(task.finished_at,task.started_at,task.created_at) DESC,task.task_id LIMIT %s""",
            (scope, role, limit)).fetchall()
        messages = connection.execute(f"""SELECT {MESSAGE_COLUMNS} {MESSAGE_FROM}
            WHERE item.analysis_scope_key=%s AND (message.from_role=%s OR message.to_role=%s)
            ORDER BY message.message_id DESC LIMIT %s""", (scope, role, role, limit)).fetchall()
        scans = connection.execute("""SELECT funds_scanned,cases_opened,cases_refreshed,finished_at FROM agents.sentinel_scans
            WHERE analysis_scope_key=%s ORDER BY finished_at DESC LIMIT 5""", (scope,)).fetchall() if role == 'sentinel' else []
    items = [task_item(row) for row in tasks]
    current = next((item for item in items if item['status'] == 'running'), None)
    return {'role': role, 'name_tr': ROLE_NAMES[role], 'description_tr': ROLE_DESCRIPTIONS[role], 'current': current,
            'tasks': items, 'messages': [message_item(row) for row in reversed(messages)],
            'scans': [{'funds_scanned': row[0], 'cases_opened': row[1], 'cases_refreshed': row[2],
                       'finished_at': iso(row[3])} for row in scans]}


# ---------- Page awareness (deterministic, no model) ----------

def page_kind(path: str) -> str:
    if path in {'/', ''}:
        return 'home'
    if re.fullmatch(r'/funds/?', path):
        return 'fund_catalog'
    if re.fullmatch(r'/funds/[A-Z0-9]{2,12}/?', path):
        return 'fund_detail'
    for prefix, kind in (('/stocks', 'stock'), ('/developments', 'evidence'), ('/workflow', 'workflow'),
                         ('/watchlist', 'watchlist'), ('/ekip', 'team')):
        if path.startswith(prefix):
            return kind
    return 'other'


def fund_signals(connection, settings: Settings, scope: str, fund_code: str):
    """The fund's admitted signals in this view's exact run; None when the view has no run."""
    with use_analysis_date(store.scope_date(scope)):
        run = store.scope_run(connection, settings)
    if not run:
        return None
    return connection.execute("""SELECT signal.detector_id,signal.state,COALESCE((item.metadata->>'is_attribute')::boolean,false)
        FROM det.signals signal JOIN det.evidence_items item USING(evidence_id)
        WHERE signal.run_id=%s AND signal.fund_code=%s AND signal.as_of<=%s
          AND (item.available_at<=%s OR (item.available_at IS NULL AND signal.state='ABSTAINED'))
        ORDER BY signal.detector_id""", (run.run_id, fund_code, run.as_of, run.cutoff)).fetchall()


def record_visit(connection, user_id: str, scope: str, fund_code: str | None) -> bool:
    """At most one recorded visit per user, view and page subject every few minutes, and a bounded hourly count."""
    connection.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,%s))', (user_id, store.REQUEST_LOCK))
    repeated = connection.execute(f"""SELECT 1 FROM agents.requests WHERE user_id=%s AND kind='page_visit'
        AND analysis_scope_key=%s AND fund_code IS NOT DISTINCT FROM %s
        AND created_at>now()-interval '{PAGE_VISIT_REPEAT_MINUTES} minutes' LIMIT 1""",
        (user_id, scope, fund_code)).fetchone()
    if repeated:
        return False
    count = connection.execute("""SELECT count(*) FROM agents.requests WHERE user_id=%s AND kind='page_visit'
        AND created_at>now()-interval '1 hour'""", (user_id,)).fetchone()[0]
    return count < PAGE_VISIT_LIMIT_PER_HOUR


def page_visit(settings: Settings, scope: str, user_id: str, path: str, fund_code: str | None) -> dict[str, Any]:
    """A quiet note from stored evidence; an open case for the fund moves up the queue."""
    kind = page_kind(path)
    if fund_code is not None and not FUND.fullmatch(fund_code):
        fund_code = None
    with connect(settings) as connection:
        connection.execute("SET LOCAL statement_timeout='5s'")
        fund = connection.execute('SELECT name FROM ref.funds WHERE fund_code=%s', (fund_code,)).fetchone() \
            if fund_code else None
        if fund_code and not fund:
            fund_code = None
        recorded = record_visit(connection, user_id, scope, fund_code)
        case = connection.execute("""SELECT case_id,status,priority FROM agents.cases
            WHERE analysis_scope_key=%s AND fund_code=%s AND status<>'closed'""", (scope, fund_code)).fetchone() \
            if fund_code else None
        outcome = 'activity'
        if recorded and case and case[1] in {'open', 'investigating'} and case[2] < PAGE_VISIT_PRIORITY:
            store.raise_case(connection, str(case[0]), PAGE_VISIT_PRIORITY)
            outcome = 'raised'
        if recorded:
            connection.execute("""INSERT INTO agents.requests(user_id,analysis_scope_key,fund_code,kind,case_id,outcome)
                VALUES (%s,%s,%s,'page_visit',%s,%s)""", (user_id, scope, fund_code, case[0] if case else None, outcome))
        if fund_code:
            signals = fund_signals(connection, settings, scope, fund_code)
            return fund_note(signals, case)
        counts = connection.execute("""SELECT
            (SELECT count(*) FROM agents.cases WHERE analysis_scope_key=%(scope)s AND status IN ('open','investigating')),
            (SELECT count(*) FROM agents.cases WHERE analysis_scope_key=%(scope)s AND status='reported')""",
            {'scope': scope}).fetchone()
    return general_note(kind, counts[0], counts[1])


def fund_note(signals, case) -> dict[str, Any]:
    from p50k.product.chat_language import DEFINITIONS
    case_view = {'case_id': str(case[0]), 'status': case[1]} if case else None
    if signals is None:
        return {'note_tr': 'Seçili tarih için tamamlanmış hesaplama henüz yok; Nöbetçi hesaplama hazır olduğunda bu fonu da tarayacak.',
                'warning_tr': None, 'suggestions': [], 'case': case_view}
    if not signals:
        return {'note_tr': 'Seçili tarihteki hesaplamada bu fon için kayıt bulunmuyor.', 'warning_tr': None,
                'suggestions': [], 'case': case_view}
    triggered = [row[0] for row in signals if row[1] == 'TRIGGERED' and not row[2]]
    labels = list(dict.fromkeys(DEFINITIONS.get(item, ('Kaynak incelemesi',))[0]
                                for item in sorted(triggered, key=lambda value: (value != 'AN-FND-005', value))))
    if labels:
        note = 'Seçili tarihteki hesaplamada bu fon için inceleme sınırı aşılan ölçümler: ' + ', '.join(labels) + '.'
    else:
        note = ('Seçili tarihteki hesaplamada bu fon için inceleme sınırı aşılmadı. '
                'Bu, fon hakkında bir güvence anlamına gelmez; yalnızca incelenen ölçümleri anlatır.')
    if case:
        note += ' ' + {'open': 'Ekip bu fon için bir vaka açtı; vaka sırasını bekliyor.',
                       'investigating': 'Ekip bu fon için açılan vakayı şu anda inceliyor.',
                       'reported': 'Ekip bu fon için raporunu yazdı; karar önerisi insan incelemesinde.'}[case[1]]
    warnings = []
    if 'AN-FND-005' in triggered:
        warnings.append('Bu fonla eşleşen ve zamanı belli resmî bir kayıt incelemeye alınmış.')
    if DATA_DETECTORS & set(triggered):
        warnings.append('Fonun son fiyat kaydı eksik veya güncel değil; fiyata dayalı ölçümler bu yüzden sınırlı olabilir.')
    suggestions = []
    if labels:
        suggestions.append({'label_tr': 'Bu gözlem ne anlama geliyor?',
                            'prompt_tr': 'Bu fonda inceleme sınırını aşan gözlemler ne anlama geliyor?'})
    else:
        suggestions.append({'label_tr': 'Hangi ölçümler incelendi?',
                            'prompt_tr': 'Bu fon için hangi ölçümler incelendi ve ne gösteriyor?'})
    if case and case[1] == 'reported':
        suggestions.append({'label_tr': 'Ekibin raporunu özetle', 'prompt_tr': 'Ekibin bu fon için yazdığı raporu özetler misin?'})
        suggestions.append({'label_tr': 'Ekibe yeniden incelet', 'prompt_tr': 'Bu fonu ekibe yeniden inceletir misin?'})
    elif case:
        suggestions.append({'label_tr': 'Ekip ne buldu?',
                            'prompt_tr': 'Ekibin bu fon için incelemesi hangi aşamada ve şimdiye kadar ne buldu?'})
    elif labels:
        suggestions.append({'label_tr': 'Ekipten inceleme iste', 'prompt_tr': 'Bu fonun ekip tarafından incelenmesini istiyorum.'})
    if DATA_DETECTORS & set(triggered):
        suggestions.append({'label_tr': 'Fiyat kaydı neden önemli?',
                            'prompt_tr': 'Bu fonun fiyat kaydındaki eksiklik incelemeyi nasıl etkiliyor?'})
    return {'note_tr': note, 'warning_tr': ' '.join(warnings) or None, 'suggestions': suggestions[:3], 'case': case_view}


def general_note(kind: str, open_cases: int, reported: int) -> dict[str, Any]:
    if open_cases or reported:
        note = (f'Ekip seçili tarihte {open_cases} açık vaka üzerinde çalışıyor; {reported} vakanın raporu insan '
                'incelemesini bekliyor.') if reported else f'Ekip seçili tarihte {open_cases} açık vaka üzerinde çalışıyor.'
    else:
        note = 'Seçili tarihte açık vaka yok; Nöbetçi tamamlanmış hesaplamaları taramaya devam ediyor.'
    if kind == 'stock':
        note += ' Ajan ekibi şu anda fonları inceliyor; bu sayfadaki hisse fiyatları kendi tarihleriyle gösteriliyor.'
    suggestions = [{'label_tr': 'Ekip şu anda ne yapıyor?', 'prompt_tr': 'Ekip şu anda hangi vakalar üzerinde çalışıyor?'},
                   {'label_tr': 'Bir vaka nasıl incelenir?', 'prompt_tr': 'Ajan ekibi bir vakayı hangi sırayla inceliyor?'}]
    return {'note_tr': note, 'warning_tr': None, 'suggestions': suggestions, 'case': None}


# ---------- The one bounded action: queue an investigation ----------

def request_investigation(settings: Settings, scope: str, user_id: str, fund_code: str) -> dict[str, Any]:
    """Open a case, raise it to user priority or start a new round for a reported case.

    A reported case whose proposal no human has reviewed is closed with its records kept and
    a fresh user case is opened; a human-reviewed case stays as it is, since the human has
    the last word. Deduplicated and at most ten per user per hour.
    """
    if not isinstance(fund_code, str) or not FUND.fullmatch(fund_code):
        raise AgentRequestError('FUND_NOT_FOUND', 404)
    with use_analysis_date(store.scope_date(scope)), connect(settings) as connection:
        connection.execute("SET LOCAL statement_timeout='5s'")
        connection.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,%s))', (user_id, store.REQUEST_LOCK))
        if not connection.execute('SELECT 1 FROM ref.funds WHERE fund_code=%s', (fund_code,)).fetchone():
            raise AgentRequestError('FUND_NOT_FOUND', 404)
        case = connection.execute("""SELECT case_id,status,decision_id FROM agents.cases
            WHERE analysis_scope_key=%s AND fund_code=%s AND status<>'closed'""", (scope, fund_code)).fetchone()
        if case and connection.execute(f"""SELECT 1 FROM agents.requests WHERE user_id=%s AND kind='investigate'
                AND case_id=%s AND created_at>now()-interval '{REQUEST_REPEAT_MINUTES} minutes' LIMIT 1""",
                (user_id, case[0])).fetchone():
            return result(str(case[0]), case[1], 'unchanged')
        used = connection.execute("""SELECT count(*) FROM agents.requests WHERE user_id=%s AND kind='investigate'
            AND created_at>now()-interval '1 hour'""", (user_id,)).fetchone()[0]
        if used >= REQUEST_LIMIT_PER_HOUR:
            raise AgentRequestError('AGENT_REQUEST_LIMIT', 429)
        reviewed = False
        if case:
            case_id, status = str(case[0]), case[1]
            outcome = 'unchanged'
            if status in {'open', 'investigating'}:
                store.raise_case(connection, case_id, USER_PRIORITY, user=user_id)
                outcome = 'raised'
            elif status == 'reported':
                reviewed = bool((decision_view(connection, case[2]) or {}).get('human_reviewed'))
                if not reviewed:
                    store.close_case(connection, case_id, REOPEN_CLOSE_NOTE_TR, from_role='reporter')
                    case_id = open_user_case(connection, settings, scope, fund_code, user_id, again=True)
                    status, outcome = 'open', 'reopened'
        else:
            case_id = open_user_case(connection, settings, scope, fund_code, user_id)
            status, outcome = 'open', 'opened'
        # The stored outcome keeps the original vocabulary: a new round opens a new case.
        connection.execute("""INSERT INTO agents.requests(user_id,analysis_scope_key,fund_code,kind,case_id,outcome)
            VALUES (%s,%s,%s,'investigate',%s,%s)""",
            (user_id, scope, fund_code, case_id, 'opened' if outcome == 'reopened' else outcome))
    return result(case_id, status, outcome, reviewed=reviewed)


def open_user_case(connection, settings: Settings, scope: str, fund_code: str, user_id: str, *,
                   again: bool = False) -> str:
    run = store.scope_run(connection, settings)
    if not run or not connection.execute('SELECT 1 FROM det.signals WHERE run_id=%s AND fund_code=%s LIMIT 1',
                                         (run.run_id, fund_code)).fetchone():
        raise AgentRequestError('EVIDENCE_UNAVAILABLE', 409)
    entries = [entry for entry in store.triggered_funds(connection, run) if entry['fund_code'] == fund_code]
    labels = list(dict.fromkeys(store.label(item) for item in (entries[0]['detectors'] if entries else [])))
    title = (('Kullanıcı isteğiyle yeniden inceleme' if again else 'Kullanıcı isteğiyle inceleme')
             + (': ' + ', '.join(labels) if labels else ''))[:240]
    case_id = store.open_case(connection, scope=scope, fund_code=fund_code, run=run, opened_by='user',
                              priority=USER_PRIORITY, title=title, requested_by=user_id,
                              opening_note=REOPEN_NOTE_TR if again else REQUEST_NOTE_TR,
                              payload={'run_id': run.run_id, 'requested': True, 'again': again,
                                       'evidence_ids': entries[0]['evidence_ids'] if entries else [],
                                       'detectors': entries[0]['detectors'] if entries else []})
    if case_id is None:
        raise AgentRequestError('AGENT_REQUEST_CONFLICT', 409)
    return case_id


def result(case_id: str, status: str, outcome: str, *, reviewed: bool = False) -> dict[str, Any]:
    queued = status in {'open', 'investigating'}
    if outcome == 'reopened':
        message = 'Ekip bu fonu yeniden incelemek için yeni bir vaka açtı; önceki rapor ve karar önerisi kayıtlı kalır.'
    elif queued:
        message = 'İstek ekibin sırasına öncelikli olarak eklendi.'
    elif reviewed:
        message = ('Ekibin bu fon için önerisi insan tarafından incelendi; son söz insanda olduğu için '
                   'yeni bir inceleme açılmadı.')
    else:
        message = 'Ekip bu fon için raporunu zaten yazdı; karar önerisi insan incelemesinde.'
    return {'case_id': case_id, 'queued': queued, 'status': status, 'status_tr': CASE_STATUS_TR[status],
            'outcome': outcome, 'message_tr': message}


# ---------- Case status for the Raportör (number-free, aliased evidence) ----------

def case_status(settings: Settings, scope: str, fund_code: str, packet=None, run_id: str | None = None) -> dict[str, Any]:
    """The fund's active case in this view for model input: statuses and validated team output only.

    Team texts are passed as their validated templates with the packet's short evidence
    aliases, and test results only as categorical outcomes, so no number or identity leaves.
    """
    from p50k.product.agents import checks
    from p50k.product.evidence_aliases import references
    from p50k.product.validator import PLACEHOLDER
    with connect(settings) as connection:
        read_only(connection)
        case = connection.execute("""SELECT case_id,status,opened_by,detector_run_id,decision_id FROM agents.cases
            WHERE analysis_scope_key=%s AND fund_code=%s AND status<>'closed'""", (scope, fund_code)).fetchone()
        if not case:
            return {'case': None}
        tasks = connection.execute("SELECT role,status FROM agents.tasks WHERE case_id=%s", (case[0],)).fetchall()
        rows = connection.execute("""SELECT kind,payload FROM agents.messages WHERE case_id=%s
            AND kind IN ('hypothesis','counter','test_result','verification','report') ORDER BY message_id""",
            (case[0],)).fetchall()
        decision = decision_view(connection, case[4])
    view: dict[str, Any] = {
        'status': case[1], 'status_tr': CASE_STATUS_TR[case[1]], 'opened_by': case[2],
        'steps': [{'role': role, 'role_tr': ROLE_NAMES[role], 'status': status, 'status_tr': TASK_STATUS_TR[status]}
                  for role, status in sorted(tasks, key=lambda item: ROLE_ORDER[item[0]]) if role != 'sentinel'],
        'decision': ({'proposal': decision['proposal'], 'effective': decision['effective'],
                      'human_reviewed': decision['human_reviewed']} if decision else None)}
    if packet is None or run_id is None or str(case[3]) != run_id:
        return {'case': view}
    inverse = {value: key for key, value in references(packet).items()}

    def alias(text: str) -> str | None:
        unknown = [match.group(1) for match in PLACEHOLDER.finditer(text) if match.group(1) and match.group(1) not in inverse]
        if unknown:
            return None
        return PLACEHOLDER.sub(lambda match: '{{ev:' + inverse[match.group(1)] + '}}' if match.group(1) else match.group(0),
                               text)[:600]

    def explained(payload: dict, names: dict) -> dict | None:
        text = alias(payload.get('text_template', ''))
        cited = [inverse[item] for item in payload.get('cited_evidence_ids', []) if item in inverse]
        if text is None or not cited:
            return None
        return {'ref': payload.get('ref'), 'type': payload.get('type'), 'type_tr': names.get(payload.get('type')),
                'text': text, 'cited_evidence_ids': cited}

    hypotheses, counters, tests, ratings, report = [], [], [], [], None
    for kind, payload in rows:
        if kind == 'hypothesis' and (item := explained(payload, HYPOTHESIS_TYPE_TR)):
            hypotheses.append(item)
        elif kind == 'counter' and (item := explained(payload, COUNTER_TYPE_TR)):
            counters.append(item)
        elif kind == 'test_result' and payload.get('test') in checks.TESTS and payload.get('outcome') in checks.FINDINGS[payload['test']]:
            tests.append(checks.model_view(payload.get('ref', ''), {'test': payload['test'], 'outcome': payload['outcome']}))
        elif kind == 'verification' and payload.get('verdict') in VERDICT_TR and (text := alias(payload.get('text_template', ''))):
            ratings.append({'target': payload.get('target'), 'verdict': payload['verdict'], 'text': text})
        elif kind == 'report':
            paragraphs = [{'text': text, 'cited_evidence_ids': [inverse[key] for key in item.get('cited_evidence_ids', [])
                                                                  if key in inverse]}
                          for item in payload.get('paragraphs', []) if (text := alias(item.get('text_template', '')))]
            report = {'paragraphs': paragraphs[:4], 'decision': payload.get('decision')}
    view.update(hypotheses=hypotheses[:3], counter_explanations=counters[:3], test_results=tests[:5],
                ratings=ratings[:6], report=report)
    return {'case': view}


# ---------- Fund page summary (read-only, no model) ----------

# Test outcomes worth showing on the fund page, in display order; "nothing found" outcomes stay in the case flow.
SUMMARY_TESTS = {
    'kap_monthly_change': {'notable_change'},
    'regulatory_event': {'confirmed_event', 'candidate_only'},
    'peer_window': {'above_peers', 'below_peers'},
    'data_quality': {'issues_found'},
    'category_move': {'widespread', 'mixed', 'isolated'},
}
SUMMARY_TEST_LIMIT = 3


def summary_highlights(rows) -> list[dict[str, str]]:
    """The latest stored result per test whose outcome is notable, as its server-rendered sentence."""
    from p50k.product.agents import checks
    latest: dict[str, tuple[str, str]] = {}
    for test, outcome, body in rows:
        if test in SUMMARY_TESTS and isinstance(body, str) and body.strip():
            latest[test] = (outcome, body.strip())
    items = []
    for test, notable in SUMMARY_TESTS.items():
        if test not in latest or latest[test][0] not in notable:
            continue
        outcome, body = latest[test]
        name = checks.TESTS[test][0]
        detail = body[len(name) + 2:] if body.startswith(name + ': ') else body
        items.append({'test': test, 'outcome': outcome, 'name_tr': name, 'detail_tr': detail})
    return items[:SUMMARY_TEST_LIMIT]


def summary_stage(status: str, steps: list[dict[str, Any]], decision: dict[str, Any] | None) -> str:
    if status == 'reported':
        if decision and decision['human_reviewed']:
            return 'Raportör raporu yazdı; karar önerisi insan tarafından incelendi.'
        return 'Raportör raporu yazdı; karar önerisi insan incelemesini bekliyor.'
    running = [step['role_tr'] for step in steps if step['status'] == 'running']
    if running:
        return f'{running[0]} şu anda vaka üzerinde çalışıyor.'
    if any(step['status'] == 'waiting_budget' for step in steps):
        return 'Yapay zekâ adımları günlük bütçenin açılmasını bekliyor; vaka kayıtlı ve sırasında.'
    done = sum(step['status'] in {'done', 'skipped'} for step in steps)
    if status == 'open' and not done:
        return 'Vaka ekibin sırasında; inceleme henüz başlamadı.'
    return f'Ekip vakayı inceliyor: {len(steps)} adımdan {done} tanesi tamamlandı.'


def fund_summary(settings: Settings, scope: str, fund_code: str) -> dict[str, Any] | None:
    """What the fund page shows first: the view's triggered measurements, the team's case and its decision state.

    Read-only and model-free. Measurements use the sentinel's admission rule on this view's
    exact run; case texts are the stored server-rendered sentences. None for an unknown fund.
    """
    from p50k.product.chat_language import evidence_fact, label
    from p50k.product.egress import Evidence
    if not isinstance(fund_code, str) or not FUND.fullmatch(fund_code):
        return None
    with connect(settings) as connection:
        read_only(connection)
        if not connection.execute('SELECT 1 FROM ref.funds WHERE fund_code=%s', (fund_code,)).fetchone():
            return None
        with use_analysis_date(store.scope_date(scope)):
            run = store.scope_run(connection, settings)
        rows = connection.execute("""SELECT signal.detector_id,signal.state,signal.value,signal.threshold,signal.evidence_id,
                item.effective_date,COALESCE(item.available_at<=%s,false)
            FROM det.signals signal JOIN det.evidence_items item USING(evidence_id)
            WHERE signal.run_id=%s AND signal.fund_code=%s AND signal.as_of<=%s
              AND NOT COALESCE((item.metadata->>'is_attribute')::boolean,false)
              AND (item.available_at<=%s OR (item.available_at IS NULL AND signal.state='ABSTAINED'))
            ORDER BY signal.detector_id""", (run.cutoff, run.run_id, fund_code, run.as_of, run.cutoff)).fetchall() \
            if run else []
        case = connection.execute("""SELECT case_id,status,opened_by,opened_at,decision_id FROM agents.cases
            WHERE analysis_scope_key=%s AND fund_code=%s AND status<>'closed'""", (scope, fund_code)).fetchone()
        tasks, tests, decision = [], [], None
        if case:
            tasks = connection.execute("SELECT role,status FROM agents.tasks WHERE case_id=%s AND role<>'sentinel'",
                                       (case[0],)).fetchall()
            tests = connection.execute("""SELECT payload->>'test',payload->>'outcome',body_tr FROM agents.messages
                WHERE case_id=%s AND kind='test_result' ORDER BY message_id""", (case[0],)).fetchall()
            decision = decision_view(connection, case[4])
    triggered = []
    for detector, state, value, threshold, evidence_id, effective, admitted in rows:
        if state != 'TRIGGERED' or not admitted:
            continue
        item = Evidence(evidence_id=evidence_id, detector_id=detector, state=state,
                        value=None if value is None else str(value), threshold=None if threshold is None else str(threshold),
                        effective_date=effective.isoformat() if effective else None, is_attribute=False)
        triggered.append({'detector_id': detector, 'evidence_id': evidence_id, 'label_tr': label(item),
                          'fact_tr': evidence_fact(item), 'effective_date': item.effective_date})
    triggered.sort(key=lambda entry: (entry['detector_id'] != 'AN-FND-005', entry['detector_id']))
    if run is None:
        calculation = 'none'
    elif not rows:
        calculation = 'not_covered'
    elif triggered:
        calculation = 'triggered'
    elif all(row[1] == 'ABSTAINED' for row in rows):
        calculation = 'limited'
    else:
        calculation = 'clear'
    case_view = None
    if case:
        steps = [{'role': role, 'role_tr': ROLE_NAMES[role], 'status': status, 'status_tr': TASK_STATUS_TR[status]}
                 for role, status in sorted(tasks, key=lambda item: ROLE_ORDER[item[0]])]
        case_view = {'case_id': str(case[0]), 'status': case[1], 'status_tr': CASE_STATUS_TR[case[1]],
                     'opened_by': case[2], 'opened_at': iso(case[3]), 'steps': steps,
                     'stage_tr': summary_stage(case[1], steps, decision), 'highlights': summary_highlights(tests),
                     'tests_run': len({row[0] for row in tests if row[0]}), 'decision': decision}
    return {'fund_code': fund_code, 'scope': scope, 'calculation': calculation,
            'as_of': run.as_of.isoformat() if run else None, 'measured': len(rows), 'triggered': triggered,
            'case': case_view}
