"""PostgreSQL (p50k_dev only) checks for the DEC-035 agent team: sentinel scans, the leased
scheduler, budget waits, scope isolation, user requests, page notes and the append-only audit.

Run with the smoke worker's agent loop stopped, so no other process claims these tasks."""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
import hashlib
import json
import os
import random
import unittest
from unittest.mock import patch
from uuid import uuid4

import psycopg
from fastapi import FastAPI
from fastapi.testclient import TestClient

from p50k.product import ai_client, chat, decisions
from p50k.product.agents import general_chat, llm, roles, runtime, sentinel, service, store
from p50k.product.agents.config import AgentConfig
from p50k.product.agents.routes import router
from p50k.product.agents.vocabulary import FAILED_STEP_TR, ROLES, SKIP_NOTES
from p50k.product.ai_client import AIConfig, settle
from p50k.product.analysis_context import EARLIEST, use_analysis_date
from p50k.product.archive import ISTANBUL
from p50k.product.auth import Principal, require_session
from p50k.product.chat_tools import invoke_tool, load_context
from p50k.product.db import connect
from p50k.product.settings import Settings

NO_MODEL = AssertionError('The agent team must not call a model here')


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def seed_run(connection, day: date, funds: dict[str, list[tuple[str, str]]]) -> str:
    """A sealed synthetic detector run for one Istanbul day, with signals bound to evidence."""
    cutoff = datetime.combine(day, time.max, ISTANBUL)
    version = 'synthetic-agents-' + uuid4().hex
    connection.execute("""INSERT INTO det.detector_versions(version_id,protocol_version,protocol_sha256,code_sha256,
        thresholds,calibration_input_sha256,calibration_cutoff) VALUES (%s,'synthetic-agents',%s,%s,'{}'::jsonb,%s,%s)""",
        (version, sha('synthetic-agents'), sha(version), sha('synthetic-calibration'), cutoff))
    run = connection.execute("""INSERT INTO det.detector_runs(protocol_version,protocol_sha256,origin,cutoff,parameters)
        VALUES ('synthetic-agents',%s,'SYNTHETIC',%s,'{}'::jsonb) RETURNING run_id""",
        (sha('synthetic-agents'), cutoff)).fetchone()[0]
    for code, items in funds.items():
        for detector, state in items:
            evidence = 'ev:agents:' + uuid4().hex
            connection.execute("""INSERT INTO det.evidence_items(evidence_id,fund_code,run_id,detector_id,origin,
                effective_date,available_at,unit,values,thresholds,triggered,state,source_references)
                VALUES (%s,%s,%s,%s,'SYNTHETIC',%s,%s,'synthetic','{}','{}',%s,%s,'[]')""",
                (evidence, code, run, detector, day, cutoff - timedelta(hours=2),
                 {'TRIGGERED': True, 'NOT_TRIGGERED': False}.get(state), state))
            connection.execute("""INSERT INTO det.signals(run_id,fund_code,detector_id,state,reason,value,threshold,
                evidence_id,as_of) VALUES (%s,%s,%s,%s,'SYNTHETIC',%s,%s,%s,%s)""",
                (run, code, detector, state, Decimal('2') if state == 'TRIGGERED' else Decimal('1'), Decimal('1.5'),
                 evidence, day))
    connection.execute("""INSERT INTO det.run_inputs(run_id,version_id,input_sha256,input_watermark,as_of,origin,cutoff,complete)
        VALUES (%s,%s,%s,%s,%s,'SYNTHETIC',%s,true)""",
        (run, version, sha(version + ':input'), cutoff - timedelta(hours=2), day, cutoff))
    return str(run)


@unittest.skipUnless(os.environ.get('P50K_TEST_DATABASE') == '1', 'Requires isolated PostgreSQL p50k_dev')
class AgentTeamDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.settings = Settings.from_env()
        if self.settings.db_name != 'p50k_dev':
            raise RuntimeError('Synthetic agent tests require p50k_dev')
        tag = uuid4().hex[:7].upper()
        self.code = {name: 'AG' + name + tag for name in 'ABCDE'}
        category = 'Synthetic agents category ' + tag
        latest = datetime.now(ISTANBUL).date() - timedelta(days=2)
        self.day = EARLIEST + timedelta(days=random.randrange((latest - EARLIEST).days))
        if self.day in {date(2026, 9, 11), date(2026, 9, 12)}:
            self.day -= timedelta(days=30)
        self.scope = 'asof:' + self.day.isoformat()
        with connect(self.settings) as connection:
            # Earlier synthetic agent cases must not compete for these claims.
            for (case_id,) in connection.execute("""SELECT item.case_id FROM agents.cases item JOIN ref.funds fund USING(fund_code)
                    WHERE item.status<>'closed' AND fund.name LIKE 'Synthetic agents fund %'""").fetchall():
                store.close_case(connection, str(case_id), 'Sentetik test için önceki vaka kapatıldı.')
            for code in self.code.values():
                connection.execute('INSERT INTO ref.funds(fund_code,name,category,source_sha256) VALUES (%s,%s,%s,%s)',
                                   (code, 'Synthetic agents fund ' + code, category, sha(code)))
            self.user = str(connection.execute("INSERT INTO auth.users(email,password_hash) VALUES (%s,'synthetic-hash') RETURNING user_id",
                                               (uuid4().hex + '@example.invalid',)).fetchone()[0])
            self.run = seed_run(connection, self.day, {
                self.code['A']: [('AN-FND-005', 'TRIGGERED'), ('D1', 'NOT_TRIGGERED')],
                self.code['B']: [('D1', 'TRIGGERED'), ('D2', 'TRIGGERED')],
                self.code['C']: [('D1', 'TRIGGERED')],
                self.code['D']: [('D1', 'NOT_TRIGGERED')]})

    def claim(self, owner: str, gap: int = 300):
        with connect(self.settings) as connection:
            return store.claim(connection, owner, gap)

    def case_row(self, name: str, columns: str = 'case_id'):
        with connect(self.settings) as connection:
            return connection.execute(f"SELECT {columns} FROM agents.cases WHERE analysis_scope_key=%s AND fund_code=%s AND status<>'closed'",
                                      (self.scope, self.code[name])).fetchone()

    def no_model(self):
        stack = [patch.object(module, 'OpenAI', side_effect=NO_MODEL) for module in (llm, chat, ai_client)]
        for item in stack:
            item.start()
            self.addCleanup(item.stop)

    def test_sentinel_opens_ordered_deduplicated_cases_without_a_model(self):
        self.no_model()
        first = sentinel.scan(self.settings, self.scope)
        second = sentinel.scan(self.settings, self.scope)
        self.assertEqual((first['run_id'], first['funds_scanned'], first['cases_opened']), (self.run, 4, 3))
        self.assertEqual(second['cases_opened'], 0)
        with connect(self.settings) as connection:
            rows = connection.execute("""SELECT fund_code,priority,opened_by FROM agents.cases WHERE analysis_scope_key=%s
                AND status<>'closed' ORDER BY priority DESC""", (self.scope,)).fetchall()
            self.assertEqual(rows, [(self.code['A'], 51, 'sentinel'), (self.code['B'], 2, 'sentinel'),
                                    (self.code['C'], 1, 'sentinel')])
            tasks = dict(connection.execute("""SELECT task.role,task.status FROM agents.tasks task JOIN agents.cases item USING(case_id)
                WHERE item.fund_code=%s AND item.analysis_scope_key=%s""", (self.code['A'], self.scope)).fetchall())
            self.assertEqual(tasks, {'sentinel': 'done', 'hypothesizer': 'queued', 'skeptic': 'queued',
                                     'verifier': 'queued', 'reporter': 'queued'})
            messages = connection.execute("""SELECT message.from_role,message.to_role,message.kind,message.body_tr,message.model_id
                FROM agents.messages message JOIN agents.cases item USING(case_id)
                WHERE item.fund_code=%s AND item.analysis_scope_key=%s""", (self.code['A'], self.scope)).fetchall()
            self.assertEqual([row[:3] for row in messages], [('sentinel', 'team', 'case_opened')])
            self.assertIn('Resmî duyuruların incelenmesi', messages[0][3])
            self.assertIsNone(messages[0][4])
            self.assertEqual(connection.execute('SELECT count(*) FROM agents.sentinel_scans WHERE analysis_scope_key=%s AND detector_run_id=%s',
                                                (self.scope, self.run)).fetchone()[0], 2)

    def test_scheduler_priority_dependencies_pacing_and_lease(self):
        sentinel.scan(self.settings, self.scope)
        first = self.claim('synthetic:1', gap=0)
        second = self.claim('synthetic:2')
        self.assertEqual({(first.fund_code, first.role), (second.fund_code, second.role)},
                         {(self.code['A'], 'hypothesizer'), (self.code['A'], 'skeptic')})
        # The verifier waits for both; the next background case waits for the pacing gap.
        self.assertIsNone(self.claim('synthetic:3'))
        with connect(self.settings) as connection:
            self.assertTrue(store.finish(connection, first, 'synthetic:1', 'done'))
            self.assertFalse(store.finish(connection, second, 'synthetic:not-the-owner', 'done'))
        self.assertIsNone(self.claim('synthetic:3'))
        with connect(self.settings) as connection:
            connection.execute("UPDATE agents.tasks SET lease_until=now()-interval '1 second' WHERE task_id=%s", (second.task_id,))
        reclaimed = self.claim('synthetic:4')
        self.assertEqual((reclaimed.task_id, reclaimed.attempts), (second.task_id, 2))
        with connect(self.settings) as connection:
            self.assertFalse(store.finish(connection, second, 'synthetic:2', 'done'))
            self.assertTrue(store.finish(connection, reclaimed, 'synthetic:4', 'done'))
        verifier = self.claim('synthetic:5')
        self.assertEqual((verifier.fund_code, verifier.role), (self.code['A'], 'verifier'))
        following = self.claim('synthetic:6', gap=0)
        self.assertEqual((following.fund_code, following.role), (self.code['B'], 'hypothesizer'))

    def test_user_request_jumps_the_queue_and_is_deduplicated_and_rate_limited(self):
        sentinel.scan(self.settings, self.scope)
        self.assertEqual(self.claim('synthetic:1', gap=0).fund_code, self.code['A'])
        raised = service.request_investigation(self.settings, self.scope, self.user, self.code['C'])
        self.assertEqual((raised['outcome'], raised['queued']), ('raised', True))
        claimed = self.claim('synthetic:2')
        self.assertEqual((claimed.fund_code, claimed.role, claimed.priority, claimed.source),
                         (self.code['C'], 'hypothesizer', 100, 'user'))
        again = service.request_investigation(self.settings, self.scope, self.user, self.code['C'])
        self.assertEqual((again['case_id'], again['outcome']), (raised['case_id'], 'unchanged'))
        opened = service.request_investigation(self.settings, self.scope, self.user, self.code['D'])
        self.assertEqual((opened['outcome'], opened['status']), ('opened', 'open'))
        with connect(self.settings) as connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM agents.requests WHERE user_id=%s AND kind='investigate'",
                                                (self.user,)).fetchone()[0], 2)
            row = connection.execute('SELECT opened_by,requested_by,priority FROM agents.cases WHERE case_id=%s',
                                     (opened['case_id'],)).fetchone()
            self.assertEqual((row[0], str(row[1]), row[2]), ('user', self.user, 100))
            handoff = connection.execute('SELECT from_role,to_role,kind FROM agents.messages WHERE case_id=%s',
                                         (opened['case_id'],)).fetchall()
            self.assertEqual(handoff, [('reporter', 'team', 'handoff')])
            for _ in range(8):
                connection.execute("""INSERT INTO agents.requests(user_id,analysis_scope_key,fund_code,kind,outcome)
                    VALUES (%s,%s,%s,'investigate','unchanged')""", (self.user, self.scope, self.code['B']))
        with self.assertRaises(service.AgentRequestError) as limited:
            service.request_investigation(self.settings, self.scope, self.user, self.code['B'])
        self.assertEqual((limited.exception.code, limited.exception.status), ('AGENT_REQUEST_LIMIT', 429))
        with self.assertRaises(service.AgentRequestError) as missing:
            service.request_investigation(self.settings, self.scope, self.user, 'ZZ' + self.code['A'][3:])
        self.assertEqual(missing.exception.status, 404)

    def test_page_visit_is_deterministic_raises_an_open_case_once_and_uses_no_model(self):
        sentinel.scan(self.settings, self.scope)
        self.no_model()
        first = service.page_visit(self.settings, self.scope, self.user, '/funds/' + self.code['B'], self.code['B'])
        second = service.page_visit(self.settings, self.scope, self.user, '/funds/' + self.code['B'], self.code['B'])
        quiet = service.page_visit(self.settings, self.scope, self.user, '/funds/' + self.code['D'], self.code['D'])
        general = service.page_visit(self.settings, self.scope, self.user, '/', None)
        self.assertEqual(first, second)
        self.assertIn('Benzer fonlarla getiri karşılaştırması', first['note_tr'])
        self.assertEqual(first['case']['status'], 'open')
        self.assertTrue(first['suggestions'])
        self.assertIsNone(quiet['case'])
        self.assertIn('aşılmadı', quiet['note_tr'])
        self.assertIn('3 açık vaka', general['note_tr'])
        with connect(self.settings) as connection:
            self.assertEqual(connection.execute('SELECT priority FROM agents.cases WHERE case_id=%s',
                                                (first['case']['case_id'],)).fetchone()[0], 70)
            self.assertEqual(connection.execute("""SELECT count(*) FROM agents.requests WHERE user_id=%s AND kind='page_visit'
                AND fund_code=%s""", (self.user, self.code['B'])).fetchone()[0], 1)

    def test_team_queue_case_and_workspace_never_cross_analysis_views(self):
        other_day = self.day - timedelta(days=1) if self.day > EARLIEST else self.day + timedelta(days=1)
        other_scope = 'asof:' + other_day.isoformat()
        with connect(self.settings) as connection:
            seed_run(connection, other_day, {self.code['E']: [('D3', 'TRIGGERED')]})
        sentinel.scan(self.settings, self.scope)
        sentinel.scan(self.settings, other_scope)
        mine, theirs = service.team(self.settings, self.scope), service.team(self.settings, other_scope)
        self.assertEqual((mine['counts']['open_cases'], theirs['counts']['open_cases']), (3, 1))
        own_codes = {self.code[name] for name in 'ABC'}
        self.assertEqual({item['fund_code'] for item in service.queue(self.settings, self.scope)['items']}, own_codes)
        self.assertEqual({item['fund_code'] for item in service.queue(self.settings, other_scope)['items']}, {self.code['E']})
        case_id = str(self.case_row('A')[0])
        self.assertIsNotNone(service.case_detail(self.settings, self.scope, case_id))
        self.assertIsNone(service.case_detail(self.settings, other_scope, case_id))
        self.assertIsNone(service.case_detail(self.settings, self.scope, 'not-a-case'))
        foreign = service.workspace(self.settings, other_scope, 'sentinel')
        self.assertEqual({item['fund_code'] for item in foreign['messages']}, {self.code['E']})
        self.assertTrue({link['case_id'] for link in theirs['links']}.isdisjoint({link['case_id'] for link in mine['links']}))
        self.assertEqual(service.case_status(self.settings, other_scope, self.code['A']), {'case': None})

    def test_mock_team_files_a_decision_that_a_human_can_override(self):
        sentinel.scan(self.settings, self.scope)
        config = AgentConfig(mode='mock', case_gap_seconds=0)
        statuses = []
        for _ in range(20):
            status = runtime.run_one(self.settings, config, 'synthetic:mock')
            if status is None:
                break
            statuses.append(status)
        self.assertEqual(statuses, ['done'] * 12)
        case_id, decision_id, status = self.case_row('B', 'case_id,decision_id,status') or \
            self.fail('The reported case must stay visible')
        self.assertEqual(status, 'reported')
        with connect(self.settings) as connection:
            decision = connection.execute('SELECT method,ai_mode,validation_state,decision_value FROM ai.decisions WHERE decision_id=%s',
                                          (decision_id,)).fetchone()
            self.assertEqual(decision, ('TEAM', 'mock', 'VALID', 'INSUFFICIENT_EVIDENCE'))
            messages = connection.execute('SELECT kind,body_tr,model_id FROM agents.messages WHERE case_id=%s ORDER BY message_id',
                                          (case_id,)).fetchall()
        self.assertEqual({row[0] for row in messages},
                         {'case_opened', 'hypothesis', 'counter', 'test_plan', 'test_result', 'verification', 'report'})
        self.assertFalse(any('{{' in row[1] or '}}' in row[1] for row in messages))
        self.assertTrue(all(row[2] == 'synthetic' for row in messages if row[0] in {'hypothesis', 'counter', 'verification', 'report'}))
        self.assertTrue(all(row[2] is None for row in messages if row[0] in {'case_opened', 'test_result'}))
        with use_analysis_date(self.day.isoformat()):
            decisions.review(self.settings, decision_id, self.user, 'OVERRIDE', 'MATERIAL', 'Sentetik insan incelemesi.')
            context = replace(load_context(self.settings, self.code['B']), scope=self.scope, user_id=self.user)
        detail = service.case_detail(self.settings, self.scope, str(case_id))
        self.assertEqual((detail['case']['decision']['proposal'], detail['case']['decision']['effective'],
                          detail['case']['decision']['human_reviewed']), ('INSUFFICIENT_EVIDENCE', 'MATERIAL', True))
        status = json.loads(invoke_tool(self.settings, context, 'get_case_status',
                                        json.dumps({'fund_code': self.code['B']})))['case']
        self.assertEqual((status['status'], status['decision']['effective']), ('reported', 'MATERIAL'))
        self.assertTrue(status['hypotheses'][0]['text'].startswith('{{ev:e'))
        # The verifier runs every standard test, not only the skeptic's picks.
        self.assertEqual(len(status['test_results']), 5)
        self.assertEqual({item['outcome'] for item in status['test_results'] if item['test'] != 'regulatory_event'},
                         {'unavailable'})
        self.assertNotIn(self.code['B'], json.dumps(status, ensure_ascii=False))
        self.assertNotIn('ev:agents:', json.dumps(status, ensure_ascii=False))

    def test_a_request_on_a_reported_case_opens_a_new_round_unless_a_human_reviewed_it(self):
        sentinel.scan(self.settings, self.scope)
        config = AgentConfig(mode='mock', case_gap_seconds=0)
        for _ in range(20):
            if runtime.run_one(self.settings, config, 'synthetic:round') is None:
                break
        case_b, decision_b = self.case_row('B', 'case_id,decision_id')
        case_c = str(self.case_row('C')[0])
        with use_analysis_date(self.day.isoformat()):
            decisions.review(self.settings, decision_b, self.user, 'ACCEPT', None, None)
        kept = service.request_investigation(self.settings, self.scope, self.user, self.code['B'])
        self.assertEqual((kept['case_id'], kept['outcome'], kept['status'], kept['queued']),
                         (str(case_b), 'unchanged', 'reported', False))
        self.assertIn('son söz insanda', kept['message_tr'])
        again = service.request_investigation(self.settings, self.scope, self.user, self.code['C'])
        self.assertEqual((again['outcome'], again['status'], again['queued']), ('reopened', 'open', True))
        self.assertNotEqual(again['case_id'], case_c)
        with connect(self.settings) as connection:
            old = connection.execute('SELECT status,closed_at IS NOT NULL,decision_id IS NOT NULL FROM agents.cases WHERE case_id=%s',
                                     (case_c,)).fetchone()
            new = connection.execute('SELECT opened_by,priority,title_tr FROM agents.cases WHERE case_id=%s',
                                     (again['case_id'],)).fetchone()
            notes = connection.execute("SELECT from_role,to_role FROM agents.messages WHERE case_id=%s AND kind='note'",
                                       (case_c,)).fetchall()
            stored = connection.execute('SELECT outcome FROM agents.requests WHERE case_id=%s',
                                        (again['case_id'],)).fetchall()
            tasks = dict(connection.execute('SELECT role,status FROM agents.tasks WHERE case_id=%s',
                                            (again['case_id'],)).fetchall())
        self.assertEqual(old, ('closed', True, True))
        self.assertEqual(new[:2], ('user', 100))
        self.assertTrue(new[2].startswith('Kullanıcı isteğiyle yeniden inceleme'))
        self.assertEqual(notes, [('reporter', 'team')])
        self.assertEqual(stored, [('opened',)])
        self.assertEqual(tasks, {role: 'queued' for role in ('hypothesizer', 'skeptic', 'verifier', 'reporter')})
        repeat = service.request_investigation(self.settings, self.scope, self.user, self.code['C'])
        self.assertEqual((repeat['case_id'], repeat['outcome']), (again['case_id'], 'unchanged'))
        self.assertIsNotNone(service.case_detail(self.settings, self.scope, case_c))

    def test_ai_off_still_runs_the_deterministic_steps(self):
        sentinel.scan(self.settings, self.scope)
        config = AgentConfig(mode='off', case_gap_seconds=0)
        statuses = [runtime.run_one(self.settings, config, 'synthetic:off') for _ in range(12)]
        self.assertEqual(statuses, ['skipped'] * 12)
        self.assertIsNone(runtime.run_one(self.settings, config, 'synthetic:off'))
        case_id = self.case_row('C')[0]
        with connect(self.settings) as connection:
            tasks = dict(connection.execute("SELECT role,error_class FROM agents.tasks WHERE case_id=%s AND role<>'sentinel'",
                                            (case_id,)).fetchall())
            self.assertEqual(tasks, {role: 'AI_OFF' for role in ('hypothesizer', 'skeptic', 'verifier', 'reporter')})
            results = connection.execute("SELECT count(*) FROM agents.messages WHERE case_id=%s AND kind='test_result'",
                                         (case_id,)).fetchone()[0]
            notes = [row[0] for row in connection.execute("SELECT body_tr FROM agents.messages WHERE case_id=%s AND kind='note'",
                                                           (case_id,)).fetchall()]
            filed = connection.execute("SELECT count(*) FROM ai.decisions WHERE fund_code=%s AND method='TEAM'",
                                       (self.code['C'],)).fetchone()[0]
        self.assertEqual(results, 5)
        self.assertIn(runtime.VERIFIER_AI_OFF_TR, notes)
        self.assertIn(SKIP_NOTES['AI_OFF'], notes)
        self.assertNotIn(FAILED_STEP_TR, notes)
        self.assertEqual(filed, 0)
        team = service.team(self.settings, self.scope, config)
        self.assertEqual({agent['role']: agent['state'] for agent in team['agents'] if agent['role'] != 'sentinel'},
                         {role: 'off' for role in ('hypothesizer', 'skeptic', 'verifier', 'reporter')})

    def test_daily_bucket_cap_and_total_target_wait_instead_of_failing(self):
        bucket = 'agents:synthetic-' + uuid4().hex
        with connect(self.settings) as connection:
            total = Decimal(connection.execute('SELECT COALESCE(sum(spent_usd+reserved_usd),0) FROM ai.budget_buckets').fetchone()[0])
        config = AgentConfig(mode='live', daily_cap_usd=Decimal('0.10'), total_target_usd=total + Decimal('5'))
        with patch.object(llm, 'daily_bucket', return_value=bucket):
            reservation = llm.reserve_agent_budget(self.settings, config, Decimal('0.06'))
            settle(self.settings, reservation, Decimal('0.06'))
            with self.assertRaises(llm.BudgetWait) as daily:
                llm.reserve_agent_budget(self.settings, config, Decimal('0.06'))
            self.assertEqual(daily.exception.reason, 'DAILY_BUDGET')
            self.assertGreater(daily.exception.until, datetime.now(timezone.utc))
            with self.assertRaises(llm.BudgetWait) as target:
                llm.reserve_agent_budget(self.settings, replace(config, total_target_usd=total + Decimal('0.07')), Decimal('0.02'))
            self.assertEqual(target.exception.reason, 'TOTAL_TARGET')
        with connect(self.settings) as connection:
            self.assertEqual(connection.execute('SELECT cap_usd,spent_usd,reserved_usd FROM ai.budget_buckets WHERE bucket=%s',
                                                (bucket,)).fetchone(), (Decimal('0.10'), Decimal('0.06'), Decimal('0')))

    def test_budget_wait_keeps_the_attempt_and_shows_as_waiting(self):
        sentinel.scan(self.settings, self.scope)
        until = datetime.now(timezone.utc) + timedelta(hours=3)
        config = AgentConfig(mode='mock', case_gap_seconds=0)
        with patch.object(roles, 'hypothesizer', side_effect=llm.BudgetWait('DAILY_BUDGET', until)):
            self.assertEqual(runtime.run_one(self.settings, config, 'synthetic:budget'), 'waiting_budget')
        with connect(self.settings) as connection:
            row = connection.execute("""SELECT task.status,task.attempts,task.not_before,task.error_class
                FROM agents.tasks task JOIN agents.cases item USING(case_id)
                WHERE item.fund_code=%s AND item.analysis_scope_key=%s AND task.role='hypothesizer'""",
                (self.code['A'], self.scope)).fetchone()
        self.assertEqual((row[0], row[1], row[3]), ('waiting_budget', 0, 'DAILY_BUDGET'))
        self.assertGreaterEqual(row[2], until - timedelta(seconds=1))
        agent = next(item for item in service.team(self.settings, self.scope, config)['agents'] if item['role'] == 'hypothesizer')
        self.assertEqual(agent['state'], 'waiting_budget')
        self.assertIn('bütçe', agent['activity_tr'])
        self.assertIn('waiting_budget', {item['status'] for item in service.queue(self.settings, self.scope)['items']})

    def test_agent_messages_scans_requests_and_finished_tasks_are_append_only(self):
        sentinel.scan(self.settings, self.scope)
        service.page_visit(self.settings, self.scope, self.user, '/', None)
        cases = "SELECT case_id FROM agents.cases WHERE analysis_scope_key=%s"
        for statement in (f"UPDATE agents.messages SET body_tr='x' WHERE case_id IN ({cases})",
                          f"DELETE FROM agents.messages WHERE case_id IN ({cases})",
                          "UPDATE agents.sentinel_scans SET cases_opened=0 WHERE analysis_scope_key=%s",
                          "DELETE FROM agents.requests WHERE analysis_scope_key=%s",
                          "DELETE FROM agents.cases WHERE analysis_scope_key=%s",
                          f"UPDATE agents.tasks SET status='queued' WHERE role='sentinel' AND case_id IN ({cases})"):
            with self.subTest(statement=statement), self.assertRaises(psycopg.Error), connect(self.settings) as connection:
                connection.execute(statement, (self.scope,))

    def test_general_reporter_thread_and_agent_routes_use_the_server_scope(self):
        sentinel.scan(self.settings, self.scope)
        with use_analysis_date(self.day.isoformat()):
            general = general_chat.load_general(self.settings, self.scope, self.user, 'home', AgentConfig(mode='mock'))
            self.assertEqual([item.fund_code for item in general.cases], [self.code[name] for name in 'ABC'])
            body = chat.ChatBody(question='Ekip şu anda ne yapıyor?')
            thread, turn, _ = general_chat.begin(self.settings, self.user, body, general)
            emitted = list(general_chat.events(self.settings, AIConfig(mode='mock'), body, general, thread, turn, []))
            self.assertEqual(emitted[-1][0], 'answer')
            self.assertEqual([item['thread_id'] for item in chat.thread_list(self.settings, self.user, None)['items']], [thread])
            self.assertEqual(chat.thread_list(self.settings, self.user, self.code['B'])['items'], [])
            self.assertEqual([row['role'] for row in chat.history(self.settings, self.user, thread, None)], ['user', 'assistant'])
            with self.assertRaises(chat.AIUnavailable):
                chat.history(self.settings, self.user, thread, self.code['B'])
        application = FastAPI()
        application.state.product_settings = self.settings
        application.include_router(router)
        principal = Principal(user_id=self.user, email='synthetic@example.invalid', role='analyst',
                              session_id='synthetic-session', csrf_sha256='0' * 64)
        application.dependency_overrides[require_session] = lambda: principal
        selected = self.day.isoformat()

        @application.middleware('http')
        async def view(request, call_next):
            with use_analysis_date(selected):
                return await call_next(request)

        with TestClient(application) as client:
            team = client.get('/agents/team').json()
            self.assertEqual((team['scope'], team['counts']['open_cases']), (self.scope, 3))
            self.assertEqual([agent['role'] for agent in team['agents']], list(ROLES))
            self.assertEqual(team['agents'][0]['state'], 'working')
            self.assertLessEqual(len(client.get('/agents/queue', params={'limit': 5}).json()['items']), 5)
            detail = client.get(f"/agents/cases/{team['links'][0]['case_id']}").json()
            self.assertEqual(detail['messages'][0]['kind'], 'case_opened')
            self.assertEqual(client.get(f'/agents/cases/{uuid4()}').status_code, 404)
            self.assertEqual(client.get('/agents/workspace/unknown').status_code, 404)
            self.assertEqual(client.get('/agents/workspace/sentinel').json()['scans'][0]['funds_scanned'], 4)
            self.assertEqual(client.post('/agents/requests', json={'fund_code': self.code['C'], 'kind': 'investigate',
                                                                   'scope': 'live'}).status_code, 422)
            self.assertTrue(client.post('/agents/requests', json={'fund_code': self.code['C'], 'kind': 'investigate'}).json()['queued'])
            note = client.post('/agents/page-visit', json={'path': '/funds/' + self.code['B'], 'fund_code': self.code['B']}).json()
            self.assertEqual(note['case']['status'], 'open')


if __name__ == '__main__':
    unittest.main()
