"""Real-work demo pacing, protected user budget, and fresh isolated review rounds."""
from __future__ import annotations
from dataclasses import replace
from decimal import Decimal
import os
import unittest
from unittest.mock import patch
from uuid import uuid4
from p50k.product import ai_client, decisions
from p50k.product.agents import llm, runtime, sentinel, service, store
from p50k.product.agents.config import AgentConfig
from p50k.product.analysis_context import use_analysis_date
from p50k.product.db import connect
from p50k.product.settings import Settings
from tests.unit import test_product_agents_database as fixture


class DemoConfigurationTests(unittest.TestCase):
    def test_demo_default_and_explicit_gap_leave_cap_unchanged(self):
        self.assertEqual(AgentConfig.from_env({}).case_gap_seconds, 300)
        demo = AgentConfig.from_env({'P50K_AGENT_DEMO': '1'})
        self.assertEqual((demo.demo, demo.case_gap_seconds, demo.daily_cap_usd), (True, 120, Decimal('3')))
        override = AgentConfig.from_env({'P50K_AGENT_DEMO': '1', 'P50K_AGENT_CASE_GAP_SECONDS': '180', 'P50K_AGENT_DAILY_CAP_USD': '5.25'})
        self.assertEqual((override.case_gap_seconds, override.daily_cap_usd), (180, Decimal('5.25')))

    def test_user_budget_context_is_isolated_and_always_reset(self):
        config = AgentConfig(demo=True, total_target_usd=Decimal('100'))
        with patch.object(llm, 'connect') as connection, patch.object(llm, 'reserve', return_value='synthetic') as reserve:
            connection.return_value.__enter__.return_value.execute.return_value.fetchone.return_value = (Decimal(0),)
            llm.reserve_agent_budget(Settings(), config, Decimal('.01'))
            self.assertEqual(reserve.call_args.kwargs['protected_usd'], Decimal('.25'))
            with llm.task_budget(True):
                llm.reserve_agent_budget(Settings(), config, Decimal('.01'))
                self.assertEqual(reserve.call_args.kwargs['protected_usd'], Decimal(0))
            self.assertFalse(llm.USER_REQUEST.get())


@unittest.skipUnless(os.environ.get('P50K_TEST_DATABASE') == '1', 'Requires isolated p50k_dev')
class DemoDatabaseTests(unittest.TestCase):
    setUp = fixture.AgentTeamDatabaseTests.setUp
    case_row = fixture.AgentTeamDatabaseTests.case_row

    def test_review_of_earlier_proposal_protects_later_round_on_the_same_packet(self):
        sentinel.scan(self.settings, self.scope)
        for _ in range(20):
            if runtime.run_one(self.settings, AgentConfig(mode='mock', case_gap_seconds=0), 'synthetic:packet-review') is None:
                break
        original, decision, _ = self.case_row('A', 'case_id,decision_id,status')
        with use_analysis_date(self.day.isoformat()):
            decisions.review(self.settings, decision, self.user, 'ACCEPT', None, None)
        run = store.Run(self.run, self.day, 'SYNTHETIC', fixture.datetime.combine(self.day, fixture.time.max, fixture.ISTANBUL))
        with connect(self.settings) as c:
            newer = c.execute("""INSERT INTO ai.decisions(packet_id,fund_code,packet_sha256,decision_value,validation_state,
                evidence_ids,rationale,output,model_id,prompt_version,schema_version,ai_mode,effort,method,call_id)
                SELECT packet_id,fund_code,packet_sha256,decision_value,validation_state,evidence_ids,rationale,output,
                model_id,prompt_version,schema_version,ai_mode,effort,method,%s FROM ai.decisions WHERE decision_id=%s
                RETURNING decision_id""", ('synthetic-later-proposal:'+uuid4().hex, decision)).fetchone()[0]
            store.close_case(c, str(original), 'Synthetic earlier review round retained.')
            later = store.open_case(c, scope=self.scope, fund_code=self.code['A'], run=run, opened_by='sentinel',
                priority=1, title='Synthetic later review', opening_note='Synthetic later review.')
            c.execute("""UPDATE agents.cases SET status='reported',decision_id=%s,started_at=clock_timestamp(),
                packet_sha256=(SELECT packet_sha256 FROM ai.decisions WHERE decision_id=%s) WHERE case_id=%s""", (newer, newer, later))
            c.execute("UPDATE agents.tasks SET status='done',finished_at=now()-interval '31 minutes' WHERE case_id=%s", (later,))
            self.assertIsNone(sentinel.reopen_idle_case(c, self.scope, run, AgentConfig(mode='live', demo=True)))
            self.assertEqual(c.execute('SELECT status FROM agents.cases WHERE case_id=%s', (later,)).fetchone()[0], 'reported')
            self.assertEqual(c.execute('SELECT count(*) FROM ai.decision_reviews WHERE decision_id=%s', (newer,)).fetchone()[0], 0)

    def test_background_reserve_is_atomic_and_user_can_use_it(self):
        bucket = 'synthetic-demo:' + uuid4().hex
        with connect(self.settings) as c:
            c.execute('INSERT INTO ai.budget_buckets(bucket,cap_usd,spent_usd,enabled) VALUES (%s,1,.7,true)', (bucket,))
        with self.assertRaises(ai_client.AIUnavailable):
            ai_client.reserve(self.settings, bucket, Decimal('.1'), protected_usd=Decimal('.25'))
        reservation = ai_client.reserve(self.settings, bucket, Decimal('.1'))
        ai_client.settle(self.settings, reservation, Decimal(0))

    def test_idle_round_is_new_paced_scoped_and_keeps_human_decisions(self):
        sentinel.scan(self.settings, self.scope)
        for _ in range(20):
            if runtime.run_one(self.settings, AgentConfig(mode='mock', case_gap_seconds=0), 'synthetic:demo') is None:
                break
        original, decision, _ = self.case_row('A', 'case_id,decision_id,status')
        config = AgentConfig(mode='live', demo=True)
        run = store.Run(self.run, self.day, 'SYNTHETIC', fixture.datetime.combine(self.day, fixture.time.max, fixture.ISTANBUL))
        with connect(self.settings) as c:
            self.assertIsNone(sentinel.reopen_idle_case(c, self.scope, run, config))
            c.execute("UPDATE agents.tasks SET finished_at=now()-interval '31 minutes' WHERE case_id IN (SELECT case_id FROM agents.cases WHERE analysis_scope_key=%s)", (self.scope,))
        # Human review protects a proposal from automatic rounds.
        with use_analysis_date(self.day.isoformat()):
            decisions.review(self.settings, decision, self.user, 'ACCEPT', None, None)
        with connect(self.settings) as c:
            new = sentinel.reopen_idle_case(c, self.scope, run, config)
            self.assertIsNotNone(new)
            self.assertIsNone(sentinel.reopen_idle_case(c, self.scope, run, config))
            self.assertEqual(c.execute('SELECT status FROM agents.cases WHERE case_id=%s', (original,)).fetchone()[0], 'reported')
            self.assertEqual(c.execute("SELECT count(*) FROM agents.messages WHERE case_id=%s AND kind IN ('hypothesis','counter','verification','report')", (new,)).fetchone()[0], 0)
            self.assertEqual(c.execute("SELECT opened_by,priority FROM agents.cases WHERE case_id=%s", (new,)).fetchone()[0], 'sentinel')
            self.assertLess(c.execute('SELECT priority FROM agents.cases WHERE case_id=%s', (new,)).fetchone()[0], 100)
            self.assertIsNone(sentinel.reopen_idle_case(c, 'asof:2026-09-12', run, config))
            self.assertIsNone(sentinel.reopen_idle_case(c, self.scope, run, replace(config, demo=False)))

    def test_user_request_unblocks_a_background_budget_wait(self):
        sentinel.scan(self.settings, self.scope)
        case = self.case_row('B')[0]
        with connect(self.settings) as c:
            c.execute("UPDATE agents.tasks SET status='waiting_budget',not_before=now()+interval '1 day' WHERE case_id=%s AND role='hypothesizer'", (case,))
        service.request_investigation(self.settings, self.scope, self.user, self.code['B'])
        with connect(self.settings) as c:
            row = c.execute("SELECT source,not_before<=now() FROM agents.tasks WHERE case_id=%s AND role='hypothesizer'", (case,)).fetchone()
            self.assertEqual(row, ('user', True))

    def test_user_promotion_during_a_claim_can_use_reserve_without_another_request(self):
        sentinel.scan(self.settings, self.scope)
        def promote_then_wait(*args):
            service.request_investigation(self.settings, self.scope, self.user, self.code['A'])
            raise llm.BudgetWait('DAILY_BUDGET', llm.next_budget_day())
        with patch.object(runtime.roles, 'hypothesizer', side_effect=promote_then_wait):
            self.assertEqual(runtime.run_one(self.settings, AgentConfig(mode='live', demo=True, case_gap_seconds=0),
                                            'synthetic:promotion'), 'waiting_budget')
        with connect(self.settings) as c:
            row = c.execute("""SELECT task.source,task.not_before<=now(),task.attempts FROM agents.tasks task
                JOIN agents.cases item USING(case_id) WHERE item.analysis_scope_key=%s
                AND item.fund_code=%s AND task.role='hypothesizer'""", (self.scope, self.code['A'])).fetchone()
            self.assertEqual(row, ('user', True, 0))
