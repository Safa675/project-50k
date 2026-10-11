"""Read-only fund summaries, with synthetic evidence and isolated p50k_dev records."""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, time, timedelta
from decimal import Decimal
import hashlib
import os
from pathlib import Path
import random
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
import psycopg
from psycopg.types.json import Jsonb

from p50k.product.agents import checks, service, store
from p50k.product.agents.routes import router
from p50k.product.analysis_context import EARLIEST, use_analysis_date
from p50k.product.archive import ISTANBUL
from p50k.product.auth import Principal, require_session
from p50k.product.db import connect
from p50k.product.settings import Settings


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def seed_run(connection, day: date, funds: dict[str, list[tuple[str, str]]]) -> store.Run:
    cutoff = datetime.combine(day, time.max, ISTANBUL)
    version = 'synthetic-summary-' + uuid4().hex
    connection.execute("""INSERT INTO det.detector_versions(version_id,protocol_version,protocol_sha256,code_sha256,
        thresholds,calibration_input_sha256,calibration_cutoff) VALUES (%s,'synthetic-summary',%s,%s,'{}',%s,%s)""",
        (version, digest(version), digest(version), digest('synthetic-summary-calibration'), cutoff))
    run = connection.execute("""INSERT INTO det.detector_runs(protocol_version,protocol_sha256,origin,cutoff,parameters)
        VALUES ('synthetic-summary',%s,'SYNTHETIC',%s,'{}') RETURNING run_id""", (digest(version), cutoff)).fetchone()[0]
    for code, signals in funds.items():
        for detector, state in signals:
            evidence = 'ev:summary:' + uuid4().hex
            connection.execute("""INSERT INTO det.evidence_items(evidence_id,fund_code,run_id,detector_id,origin,
                effective_date,available_at,unit,values,thresholds,triggered,state,source_references,metadata)
                VALUES (%s,%s,%s,%s,'SYNTHETIC',%s,%s,'synthetic','{}','{}',%s,%s,'[]',%s)""",
                (evidence, code, run, detector, day, None if state == 'ABSTAINED' else cutoff - timedelta(hours=2),
                 {'TRIGGERED': True, 'NOT_TRIGGERED': False}.get(state), state, Jsonb({'is_attribute': detector == 'D5'})))
            connection.execute("""INSERT INTO det.signals(run_id,fund_code,detector_id,state,reason,value,threshold,
                evidence_id,as_of) VALUES (%s,%s,%s,%s,'SYNTHETIC',%s,%s,%s,%s)""",
                (run, code, detector, state, None if state == 'ABSTAINED' else Decimal('2'),
                 None if state == 'ABSTAINED' else Decimal('1.5'), evidence, day))
    connection.execute("""INSERT INTO det.run_inputs(run_id,version_id,input_sha256,input_watermark,as_of,origin,cutoff,complete)
        VALUES (%s,%s,%s,%s,%s,'SYNTHETIC',%s,true)""",
        (run, version, digest(version + ':input'), cutoff - timedelta(hours=2), day, cutoff))
    return store.Run(str(run), day, 'SYNTHETIC', cutoff)


class FundSummaryUnitTests(unittest.TestCase):
    def test_latest_test_outcome_wins_and_only_three_notable_results_are_shown(self):
        name = checks.TESTS['kap_monthly_change'][0]
        rows = [('kap_monthly_change', 'notable_change', name + ': Synthetic old detail.'),
                ('kap_monthly_change', 'no_notable_change', name + ': Synthetic latest detail.'),
                ('unknown', 'notable_change', 'Synthetic ignored detail.'),
                ('regulatory_event', 'candidate_only', 'Synthetic candidate detail.'),
                ('peer_window', 'below_peers', 'Synthetic peer detail.'),
                ('data_quality', 'issues_found', 'Synthetic missing detail.'),
                ('category_move', 'isolated', 'Synthetic category detail.')]
        items = service.summary_highlights(rows)
        self.assertEqual([item['test'] for item in items], ['regulatory_event', 'peer_window', 'data_quality'])
        self.assertNotIn('Synthetic old detail.', str(items))
        self.assertEqual(service.summary_highlights([('kap_monthly_change', 'notable_change', name + ': Synthetic detail.')])[0]['detail_tr'], 'Synthetic detail.')

    def test_stage_discloses_human_review_running_work_and_budget_wait(self):
        self.assertIn('insan tarafından incelendi', service.summary_stage('reported', [], {'human_reviewed': True}))
        self.assertIn('insan incelemesini bekliyor', service.summary_stage('reported', [], {'human_reviewed': False}))
        self.assertIn('şu anda', service.summary_stage('investigating', [{'role_tr': 'Doğrulayıcı', 'status': 'running'}], None))
        self.assertIn('bütçenin', service.summary_stage('open', [{'role_tr': 'Raportör', 'status': 'waiting_budget'}], None))

    def test_route_requires_a_session_and_uses_the_server_selected_scope(self):
        app = FastAPI()
        app.state.product_settings = Settings(db_name='p50k_dev')
        app.include_router(router)
        with TestClient(app) as client, patch.object(service, 'fund_summary', return_value={'fund_code': 'TESTA'}) as reader:
            self.assertEqual(client.get('/agents/funds/TESTA/summary').status_code, 401)
            reader.assert_not_called()
            app.dependency_overrides[require_session] = lambda: Principal('synthetic', 'synthetic@example.invalid', 'viewer', 'synthetic', 'a' * 64)
            with use_analysis_date('2026-09-12'):
                self.assertEqual(client.get('/agents/funds/TESTA/summary?scope=live').status_code, 200)
            self.assertEqual(reader.call_args.args[1:], ('asof:2026-09-12', 'TESTA'))
            reader.return_value = None
            self.assertEqual(client.get('/agents/funds/UNKNOWN/summary').status_code, 404)
            reader.side_effect = psycopg.OperationalError('Synthetic unavailable database')
            self.assertEqual(client.get('/agents/funds/TESTA/summary').status_code, 503)


@unittest.skipUnless(os.environ.get('P50K_TEST_DATABASE') == '1', 'Requires isolated owner PostgreSQL p50k_dev')
class FundSummaryDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.owner = Settings.from_env()
        if self.owner.db_name != 'p50k_dev' or self.owner.db_user != 'p50k_owner':
            raise RuntimeError('Synthetic fund-summary tests require owner p50k_dev')
        self.settings = replace(self.owner, db_user='p50k_app', db_password_file=Path(os.environ['P50K_APP_PASSWORD_FILE']))
        tag = uuid4().hex[:7].upper()
        self.codes = {name: 'FS' + tag + name for name in 'ABCDE'}
        with connect(self.owner) as connection:
            for _ in range(100):
                candidate = EARLIEST + timedelta(days=random.randrange(0, 290))
                occupied = connection.execute("""SELECT 1 FROM det.detector_runs WHERE
                    (cutoff AT TIME ZONE 'Europe/Istanbul')::date BETWEEN %s AND %s LIMIT 1""",
                    (candidate, candidate + timedelta(days=3))).fetchone()
                if occupied is None:
                    self.day = candidate
                    break
            else:
                raise RuntimeError('No isolated synthetic summary dates remain')
            for code in self.codes.values():
                connection.execute("INSERT INTO ref.funds(fund_code,name,category,source_sha256) VALUES (%s,%s,'Synthetic summary category',%s)",
                                   (code, 'Synthetic summary fund ' + code, digest(code)))
            self.run = seed_run(connection, self.day, {
                self.codes['A']: [('D1', 'TRIGGERED'), ('AN-FND-005', 'TRIGGERED'), ('D5', 'TRIGGERED')],
                self.codes['B']: [('D1', 'NOT_TRIGGERED'), ('D5', 'TRIGGERED')],
                self.codes['C']: [('D1', 'ABSTAINED'), ('D2', 'ABSTAINED')],
                self.codes['D']: [('D5', 'TRIGGERED')]})
        self.scope = 'asof:' + self.day.isoformat()
        patcher = patch.object(service.llm, 'OpenAI', side_effect=AssertionError('A summary must never call a model'))
        patcher.start()
        self.addCleanup(patcher.stop)

    def summary(self, name: str, scope: str | None = None):
        return service.fund_summary(self.settings, scope or self.scope, self.codes[name])

    def test_triggered_clear_limited_attributes_and_uncovered_funds_are_distinct(self):
        triggered = self.summary('A')
        self.assertEqual(triggered['calculation'], 'triggered')
        self.assertEqual([item['detector_id'] for item in triggered['triggered']], ['AN-FND-005', 'D1'])
        self.assertTrue(all(item['label_tr'] and item['fact_tr'] for item in triggered['triggered']))
        self.assertEqual(triggered['measured'], 2)
        for name, expected in [('B', 'clear'), ('C', 'limited'), ('D', 'not_covered'), ('E', 'not_covered')]:
            with self.subTest(name=name):
                self.assertEqual(self.summary(name)['calculation'], expected)
                self.assertEqual(self.summary(name)['triggered'], [])
        self.assertIsNone(service.fund_summary(self.settings, self.scope, 'invalid'))
        self.assertIsNone(service.fund_summary(self.settings, self.scope, 'UNKNOWN'))

    def test_future_run_cannot_leak_into_the_selected_day_or_fill_a_day_without_a_run(self):
        with connect(self.owner) as connection:
            seed_run(connection, self.day + timedelta(days=1), {self.codes['B']: [('D1', 'TRIGGERED')]})
        selected = self.summary('B')
        self.assertEqual((selected['calculation'], selected['as_of']), ('clear', self.day.isoformat()))
        empty = self.summary('A', 'asof:' + (self.day + timedelta(days=2)).isoformat())
        self.assertEqual((empty['calculation'], empty['as_of'], empty['measured']), ('none', None, 0))
        self.assertEqual(empty['triggered'], [])

    def test_team_highlights_and_human_override_keep_the_original_proposal(self):
        code = self.codes['A']
        checksum = digest(code + ':packet')
        with connect(self.owner) as connection:
            actor = connection.execute("INSERT INTO auth.users(email,password_hash,role) VALUES (%s,'synthetic-hash','analyst') RETURNING user_id",
                                       (uuid4().hex + '@example.invalid',)).fetchone()[0]
            packet = connection.execute("""INSERT INTO ai.packets(fund_code,packet_sha256,origin,as_of,cutoff,payload,allowed_options)
                VALUES (%s,%s,'SYNTHETIC',%s,%s,'{}','["MATERIAL","INSUFFICIENT_EVIDENCE"]') RETURNING packet_id""",
                (code, checksum, self.day, self.run.cutoff)).fetchone()[0]
            decision = connection.execute("""INSERT INTO ai.decisions(packet_id,fund_code,packet_sha256,decision_value,
                validation_state,evidence_ids,model_id,prompt_version,schema_version,ai_mode,call_id,method)
                VALUES (%s,%s,%s,'MATERIAL','VALID','[]','synthetic','synthetic','synthetic','off',%s,'TEAM') RETURNING decision_id""",
                (packet, code, checksum, 'synthetic-summary:' + uuid4().hex)).fetchone()[0]
            case = store.open_case(connection, scope=self.scope, fund_code=code, run=self.run, opened_by='sentinel', priority=1,
                                   title='Synthetic summary case', opening_note='Sentetik test vakası.')
            connection.execute("UPDATE agents.tasks SET status='done',started_at=clock_timestamp(),finished_at=clock_timestamp() WHERE case_id=%s AND status<>'done'", (case,))
            connection.execute("UPDATE agents.cases SET status='reported',started_at=clock_timestamp(),decision_id=%s,packet_sha256=%s WHERE case_id=%s", (decision, checksum, case))
            name = checks.TESTS['kap_monthly_change'][0]
            store.add_message(connection, case, None, 'verifier', 'team', 'test_result', name + ': Sentetik raporda belirgin değişim var.',
                              {'test': 'kap_monthly_change', 'outcome': 'notable_change'})
        original = self.summary('A')['case']
        self.assertEqual((original['status'], original['tests_run'], original['decision']['proposal'], original['decision']['human_reviewed']),
                         ('reported', 1, 'MATERIAL', False))
        self.assertEqual(original['highlights'][0]['detail_tr'], 'Sentetik raporda belirgin değişim var.')
        self.assertIn('insan incelemesini bekliyor', original['stage_tr'])
        with connect(self.owner) as connection:
            connection.execute("""INSERT INTO ai.decision_reviews(decision_id,packet_sha256,action,override_value,reason,reviewer_id)
                VALUES (%s,%s,'OVERRIDE','INSUFFICIENT_EVIDENCE','Synthetic human reason',%s)""", (decision, checksum, actor))
        reviewed = self.summary('A')['case']
        self.assertEqual((reviewed['decision']['proposal'], reviewed['decision']['effective'], reviewed['decision']['human_reviewed'],
                          reviewed['decision']['decided_by']), ('MATERIAL', 'INSUFFICIENT_EVIDENCE', True, 'HUMAN'))
        self.assertIn('insan tarafından incelendi', reviewed['stage_tr'])
        self.assertIsNone(self.summary('A', 'asof:' + (self.day + timedelta(days=2)).isoformat())['case'])
        with connect(self.owner) as connection:
            self.assertEqual(connection.execute('SELECT decision_value FROM ai.decisions WHERE decision_id=%s', (decision,)).fetchone()[0], 'MATERIAL')


if __name__ == '__main__':
    unittest.main()
