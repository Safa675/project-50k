"""Selected-date boundaries: exact-day runs, bounded retries, leases and worker scope.

Synthetic data only. Every database case runs inside one p50k_dev transaction
that is rolled back, so nothing is committed and the running smoke worker never
sees the fixtures.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, time, timedelta, timezone
from hashlib import sha256
import os
from unittest import TestCase, skipUnless
from unittest.mock import patch
from uuid import uuid4

import psycopg
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb

from p50k.product import analysis_jobs, decisions, queue
from p50k.product.ai_client import AIConfig, AIUnavailable
from p50k.product.analysis_context import (analysis_scope_key, current_cutoff, historical_mode, page_origin,
                                           run_day, run_origins, selection, use_analysis_date)
from p50k.product.app import create_app
from p50k.product.archive import ISTANBUL
from p50k.product.auth import CSRF_COOKIE, Principal, digest_token
from p50k.product.db import connect
from p50k.product.evidence_routes import evidence_detail
from p50k.product.queries import FundQueries
from p50k.product.routes import get_queries, require_session, resolve_cutoff, router
from p50k.product.settings import Settings
from p50k.product.watchlists import _snapshot
from p50k.product.workflow import WorkflowQueries
from tests.unit.test_product_api import SyntheticReader

SELECTED = '2026-09-12'
END_OF_SELECTED = datetime(2026, 9, 12, 23, 59, 59, 999999, tzinfo=ISTANBUL)
LIVE = {'P50K_ANALYSIS_DATE': 'live'}


def replay_cutoff(day: date) -> datetime:
    return datetime.combine(day, time(23, 59, 59), ISTANBUL)


class SelectedDateBoundaryTests(TestCase):
    def test_retrospective_cutoff_rejects_later_and_scopes_earlier_explicit_cutoffs(self):
        with use_analysis_date(SELECTED):
            self.assertEqual(current_cutoff(), END_OF_SELECTED)
            self.assertEqual(resolve_cutoff(None), END_OF_SELECTED)
            for later in (datetime(2026, 9, 13, tzinfo=ISTANBUL), datetime(2026, 9, 12, 21, tzinfo=timezone.utc)):
                with self.subTest(later=later), self.assertRaises(HTTPException) as error:
                    resolve_cutoff(later)
                self.assertEqual(error.exception.detail, 'CUTOFF_AFTER_SELECTED_DATE')
            same_day = datetime(2026, 9, 12, 12, tzinfo=ISTANBUL)
            self.assertEqual(resolve_cutoff(same_day), same_day)
            earlier = resolve_cutoff(datetime(2026, 9, 5, 12, tzinfo=ISTANBUL))
            self.assertEqual(earlier.tzinfo, timezone.utc)
            # An earlier explicit cutoff reads only the run of its own Istanbul day.
            self.assertEqual(run_day(earlier), date(2026, 9, 5))
            self.assertEqual(run_day(datetime(2026, 9, 4, 22, 30, tzinfo=timezone.utc)), date(2026, 9, 5))
            self.assertEqual(page_origin(), 'HISTORICAL_REPLAY')
            self.assertEqual(analysis_scope_key(), 'asof:' + SELECTED)
        with patch.dict(os.environ, LIVE):
            self.assertIsNone(run_day(datetime.now(timezone.utc)))
            self.assertEqual(page_origin(), 'DELAYED')
            with self.assertRaises(HTTPException) as error:
                resolve_cutoff(datetime.now(timezone.utc) + timedelta(days=1))
            self.assertEqual(error.exception.detail, 'FUTURE_CUTOFF_REJECTED')

    def test_run_origins_never_mix_live_and_retrospective_and_keep_synthetic_to_development(self):
        with use_analysis_date(SELECTED):
            self.assertEqual(run_origins(database='p50k_dev'), ['HISTORICAL_REPLAY', 'SYNTHETIC'])
            self.assertEqual(run_origins(database='p50k'), ['HISTORICAL_REPLAY'])
        with patch.dict(os.environ, LIVE):
            self.assertEqual(run_origins(database='p50k'), ['DELAYED'])
        with self.assertRaisesRegex(ValueError, 'ANALYSIS_DATE_REQUIRED'):
            analysis_jobs.run_analysis(Settings(), 'live')

    def test_fund_routes_reject_later_cutoffs_and_label_retrospective_pages(self):
        reader = SyntheticReader()
        application = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
        application.include_router(router)
        application.dependency_overrides[get_queries] = lambda: reader
        application.dependency_overrides[require_session] = lambda: None
        with patch.dict(os.environ, {'P50K_ANALYSIS_DATE': SELECTED}), \
                TestClient(application, base_url='http://localhost') as client:
            for path in ('/funds/ZZZ', '/signals', '/events'):
                with self.subTest(path=path):
                    self.assertEqual(client.get(path, params={'cutoff': '2026-09-13T00:00:00+03:00'}).status_code, 422)
            self.assertEqual(reader.calls, [])
            detail = client.get('/funds/ZZZ')
            self.assertEqual(detail.status_code, 200, detail.text)
            self.assertEqual(detail.json()['origin'], 'HISTORICAL_REPLAY')
            self.assertEqual(datetime.fromisoformat(detail.json()['cutoff']), END_OF_SELECTED)
            self.assertIsNone(detail.json()['fund']['tefas_status'])
            earlier = client.get('/signals', params={'cutoff': '2026-09-05T12:00:00+03:00'})
            self.assertEqual(earlier.status_code, 200, earlier.text)
        self.assertIn(('signals', None, None, date(2026, 9, 5), datetime(2026, 9, 5, 9, tzinfo=timezone.utc), 25, 0),
                      reader.calls)

    def client(self, role='viewer'):
        token = 'k' * 43
        principal = Principal(str(uuid4()), 'synthetic@example.invalid', role, 'synthetic-session', digest_token(token))
        settings = Settings.from_env({})
        authenticate = patch('p50k.product.auth.AuthService.authenticate', return_value=principal)
        authenticate.start()
        self.addCleanup(authenticate.stop)
        client = TestClient(create_app(settings, readiness=lambda _: True), base_url='http://127.0.0.1:3071')
        self.addCleanup(client.close)
        client.cookies.set(CSRF_COOKIE, token)
        return client, {'Origin': settings.allowed_origins[0], 'X-CSRF-Token': token}

    def test_date_cookie_is_set_only_after_the_calculation_request_is_accepted(self):
        client, headers = self.client()
        with patch('p50k.product.context_routes.enqueue_analysis', side_effect=ValueError('ANALYSIS_QUEUE_BUSY')):
            busy = client.post('/context', json={'date': SELECTED}, headers=headers)
        self.assertEqual((busy.status_code, busy.json()['detail']), (409, 'ANALYSIS_QUEUE_BUSY'))
        self.assertNotIn('p50k_as_of', busy.headers.get('set-cookie', ''))
        with patch('p50k.product.context_routes.enqueue_analysis', side_effect=psycopg.OperationalError('synthetic')):
            down = client.post('/context', json={'date': SELECTED}, headers=headers)
        self.assertEqual((down.status_code, down.json()['detail']), (503, 'ANALYSIS_UNAVAILABLE'))
        self.assertNotIn('p50k_as_of', down.headers.get('set-cookie', ''))
        self.assertEqual(client.post('/context', json={'date': '2025-10-05'}, headers=headers).status_code, 422)
        self.assertEqual(client.post('/context', json={'date': SELECTED}).status_code, 403)
        with patch('p50k.product.context_routes.enqueue_analysis', return_value='queued') as enqueue:
            accepted = client.post('/context', json={'date': SELECTED}, headers=headers)
        self.assertEqual(accepted.status_code, 200, accepted.text)
        self.assertEqual(enqueue.call_args.args[1], SELECTED)
        body = accepted.json()
        self.assertEqual((body['analysis_status'], body['mode'], body['scope_key'], body['as_of_date']),
                         ('queued', 'historical', 'asof:' + SELECTED, SELECTED))
        self.assertIn('p50k_as_of=' + SELECTED, accepted.headers['set-cookie'])
        with patch('p50k.product.context_routes.analysis_status', return_value='failed'):
            current = client.get('/context').json()
        self.assertEqual((current['analysis_status'], current['as_of_date']), ('failed', SELECTED))

    def test_reevaluation_without_the_selected_day_evidence_is_a_conflict_and_queues_nothing(self):
        client, headers = self.client('analyst')
        with patch('p50k.product.decision_routes.AIConfig.from_env', return_value=AIConfig(mode='mock')), \
                patch('p50k.product.decision_routes.build_packet', side_effect=AIUnavailable('EVIDENCE_UNAVAILABLE')), \
                patch('p50k.product.decision_routes.enqueue') as enqueue:
            response = client.post('/funds/ZZZ/evaluate', headers=headers)
        self.assertEqual((response.status_code, response.json()['detail']), (409, 'EVIDENCE_UNAVAILABLE'))
        enqueue.assert_not_called()


class SharedTransaction:
    """Route module connections into the test's own transaction, which is rolled back."""

    def __init__(self, connection):
        self.connection = connection

    def __call__(self, *_args, **_kwargs):
        return self

    def __enter__(self):
        return self.connection

    def __exit__(self, *_exc):
        return False


@skipUnless(os.environ.get('P50K_TEST_DATABASE') == '1', 'Requires isolated PostgreSQL p50k_dev')
class SelectedDateDatabaseTests(TestCase):
    def setUp(self):
        self.settings = Settings.from_env()
        if self.settings.db_name != 'p50k_dev' or self.settings.analysis_date != 'live':
            raise RuntimeError('Synthetic date-scope fixtures require p50k_dev with the live default selection')
        self.connection = connect(self.settings)
        self.addCleanup(self.connection.close)
        self.addCleanup(self.connection.rollback)
        self.shared = SharedTransaction(self.connection)
        self.version = 'synthetic-scope-' + uuid4().hex
        version = patch.object(analysis_jobs, 'VERSION_ID', self.version)
        version.start()
        self.addCleanup(version.stop)
        self.code = 'SCP' + uuid4().hex[:9].upper()
        self.sha = sha256(self.code.encode()).hexdigest()
        self.connection.execute("""INSERT INTO ref.funds(fund_code,name,category,source_sha256)
            VALUES(%s,'Synthetic scope fund','Synthetic scope category',%s)""", (self.code, self.sha))
        self.actor = str(self.connection.execute("INSERT INTO auth.users(email,password_hash) VALUES(%s,'synthetic-hash') RETURNING user_id",
                                                 (uuid4().hex + '@example.invalid',)).fetchone()[0])
        self.register(self.version)
        self.day = self.free_day()
        self.selected = self.day.isoformat()

    def free_day(self) -> date:
        """First day whose two preceding days also have no stored run or scoped job."""
        row = self.connection.execute("""SELECT days.day FROM
                (SELECT generate_series(%s::date,%s::date,interval '1 day')::date AS day) days
            WHERE NOT EXISTS (SELECT 1 FROM det.detector_runs run
                    WHERE (run.cutoff AT TIME ZONE 'Europe/Istanbul')::date BETWEEN days.day-2 AND days.day)
              AND NOT EXISTS (SELECT 1 FROM ops.jobs job WHERE job.payload->>'analysis_date' IN
                    (to_char(days.day,'YYYY-MM-DD'),to_char(days.day-1,'YYYY-MM-DD'),to_char(days.day-2,'YYYY-MM-DD')))
            ORDER BY days.day LIMIT 1""", (date(2025, 10, 20), date(2026, 8, 31))).fetchone()
        self.assertIsNotNone(row)
        return row[0]

    def register(self, version: str) -> None:
        self.connection.execute("""INSERT INTO det.detector_versions(version_id,protocol_version,protocol_sha256,code_sha256,
                thresholds,calibration_input_sha256,calibration_cutoff)
            VALUES(%s,'synthetic-scope-v1',%s,%s,'{}',%s,'2025-10-01T00:00:00+03:00')""", (version, self.sha, self.sha, self.sha))

    def make_run(self, day: date | None, *, origin='HISTORICAL_REPLAY', version=None, cutoff=None) -> tuple[str, str]:
        cutoff = cutoff or replay_cutoff(day)
        observed = cutoff.astimezone(ISTANBUL).date() - timedelta(days=1)
        run_id = self.connection.execute("""INSERT INTO det.detector_runs(protocol_version,protocol_sha256,origin,cutoff,parameters)
            VALUES('synthetic-scope-v1',%s,%s,%s,'{}') RETURNING run_id""", (self.sha, origin, cutoff)).fetchone()[0]
        evidence_id = 'synthetic-scope-' + uuid4().hex
        self.connection.execute("""INSERT INTO det.evidence_items(evidence_id,fund_code,run_id,detector_id,origin,effective_date,
                available_at,unit,values,thresholds,triggered,state,source_references)
            VALUES(%s,%s,%s,'D1',%s,%s,%s,'ratio','{"score":"3"}','{"threshold":"2"}',true,'TRIGGERED','[]')""",
                                (evidence_id, self.code, run_id, origin, observed, cutoff - timedelta(hours=12)))
        self.connection.execute("""INSERT INTO det.signals(run_id,fund_code,detector_id,state,reason,value,threshold,evidence_id,as_of)
            VALUES(%s,%s,'D1','TRIGGERED','SYNTHETIC_TEST_REASON',3,2,%s,%s)""", (run_id, self.code, evidence_id, observed))
        self.connection.execute("""INSERT INTO det.run_inputs(run_id,version_id,input_sha256,as_of,origin,cutoff)
            VALUES(%s,%s,%s,%s,%s,%s)""", (run_id, version or self.version, sha256(uuid4().bytes).hexdigest(), observed, origin, cutoff))
        return str(run_id), evidence_id

    def status(self, selected=None, settings=None) -> str:
        return analysis_jobs.scope_status(self.connection, settings or self.settings, selected or self.selected)

    def job_id(self, selected=None) -> str:
        return str(self.connection.execute('SELECT job_id FROM ops.jobs WHERE idempotency_key=%s',
                                           (analysis_jobs.job_key(selected or self.selected),)).fetchone()[0])

    def first_in_line(self, job: str) -> None:
        self.connection.execute("UPDATE ops.jobs SET priority=-1000000,available_at=now()-interval '1 hour' WHERE job_id=%s", (job,))

    def test_status_requires_the_persisted_run_of_the_exact_day_and_current_version(self):
        production = replace(self.settings, db_name='p50k')
        self.assertEqual(self.status(), 'not_started')
        other = 'synthetic-scope-other-' + uuid4().hex
        self.register(other)
        self.make_run(self.day, version=other)
        self.make_run(self.day - timedelta(days=1))
        self.assertEqual(self.status(), 'not_started')
        self.assertEqual(self.status((self.day - timedelta(days=1)).isoformat()), 'ready')
        self.make_run(self.day, origin='SYNTHETIC')
        self.assertEqual(self.status(), 'ready')
        self.assertEqual(self.status(settings=production), 'not_started')
        self.make_run(self.day)
        self.assertEqual(self.status(settings=production), 'ready')
        self.assertEqual(self.status('live'), 'ready')

    def test_job_state_is_reported_only_while_the_day_run_is_absent(self):
        job = self.connection.execute("""INSERT INTO ops.jobs(job_type,idempotency_key,payload,priority)
            VALUES('analysis_replay',%s,%s,0) RETURNING job_id""",
                                      (analysis_jobs.job_key(self.selected), Jsonb({'analysis_date': self.selected}))).fetchone()[0]

        def state(status, attempts=0, lease=None):
            self.connection.execute('UPDATE ops.jobs SET status=%s,attempts=%s,lease_until=now()+%s::interval WHERE job_id=%s',
                                    (status, attempts, lease, job))
            return self.status()

        self.assertEqual(state('READY'), 'queued')
        self.assertEqual(state('RUNNING', 1, timedelta(minutes=3)), 'running')
        self.assertEqual(state('RUNNING', 1, -timedelta(seconds=1)), 'queued')
        self.assertEqual(state('RUNNING', 3, -timedelta(seconds=1)), 'failed')
        self.assertEqual(state('FAILED', 3), 'failed')
        # A finished job is not proof: without the day's persisted run it is a failure.
        self.assertEqual(state('SUCCEEDED', 1), 'failed')
        self.make_run(self.day)
        self.assertEqual(state('SUCCEEDED', 1), 'ready')

    def test_requests_deduplicate_respect_the_cap_and_retry_a_failed_day_a_bounded_number_of_times(self):
        key = analysis_jobs.job_key(self.selected)
        active = self.connection.execute("""SELECT count(*) FROM ops.jobs
            WHERE job_type='analysis_replay' AND status IN ('READY','RUNNING')""").fetchone()[0]

        def row():
            return self.connection.execute("""SELECT status,attempts,error_class,payload->>'retries',priority
                FROM ops.jobs WHERE idempotency_key=%s""", (key,)).fetchall()

        with patch.object(analysis_jobs, 'MAX_ACTIVE_JOBS', active + 1):
            self.assertEqual(analysis_jobs.request_analysis(self.connection, self.settings, self.selected), 'queued')
            self.assertEqual(analysis_jobs.request_analysis(self.connection, self.settings, self.selected), 'queued')
            self.assertEqual(row(), [('READY', 0, None, None, 0)])
            self.assertEqual(self.connection.execute('SELECT payload FROM ops.jobs WHERE idempotency_key=%s', (key,)).fetchone()[0],
                             {'analysis_date': self.selected})
            other = (self.day - timedelta(days=1)).isoformat()
            with self.assertRaisesRegex(ValueError, 'ANALYSIS_QUEUE_BUSY'):
                analysis_jobs.request_analysis(self.connection, self.settings, other)
            self.assertEqual(self.status(other), 'not_started')
            failures = ("status='SUCCEEDED',attempts=1",
                        "status='RUNNING',attempts=max_attempts,lease_owner='synthetic-lost-worker',lease_until=now()-interval '1 second'",
                        "status='FAILED',attempts=max_attempts,error_class='SyntheticFailure'")
            self.assertEqual(len(failures), analysis_jobs.MAX_RETRIES)
            for retry, failure in enumerate(failures, start=1):
                with self.subTest(failure=failure):
                    self.connection.execute('UPDATE ops.jobs SET ' + failure + ' WHERE idempotency_key=%s', (key,))
                    self.assertEqual(self.status(), 'failed')
                    self.assertEqual(analysis_jobs.request_analysis(self.connection, self.settings, self.selected), 'queued')
                    self.assertEqual(row(), [('READY', 0, None, str(retry), 0)])
            self.connection.execute("UPDATE ops.jobs SET status='FAILED',attempts=max_attempts,error_class='SyntheticFailure' WHERE idempotency_key=%s", (key,))
            self.assertEqual(analysis_jobs.request_analysis(self.connection, self.settings, self.selected), 'failed')
            self.assertEqual(row(), [('FAILED', 3, 'SyntheticFailure', str(analysis_jobs.MAX_RETRIES), 0)])
            self.make_run(self.day)
            self.assertEqual(analysis_jobs.request_analysis(self.connection, self.settings, self.selected), 'ready')

    def test_claim_lease_expiry_and_owner_bound_completion(self):
        with patch.object(queue, 'connect', self.shared):
            analysis_jobs.request_analysis(self.connection, self.settings, self.selected)
            job = self.job_id()
            self.first_in_line(job)
            first = queue.claim(self.settings, 'synthetic-worker-a')
            self.assertEqual((str(first[0]), first[1], first[2], first[4]), (job, {'analysis_date': self.selected}, 1, 'analysis_replay'))
            self.assertEqual(self.status(), 'running')
            competing = queue.claim(self.settings, 'synthetic-worker-b')
            self.assertTrue(competing is None or str(competing[0]) != job)
            self.connection.execute("UPDATE ops.jobs SET lease_until=now()-interval '1 second' WHERE job_id=%s", (job,))
            self.assertEqual(self.status(), 'queued')
            second = queue.claim(self.settings, 'synthetic-worker-c')
            self.assertEqual((str(second[0]), second[2]), (job, 2))
            self.assertFalse(queue.finish(self.settings, job, 'synthetic-worker-a'))
            self.assertTrue(queue.finish(self.settings, job, 'synthetic-worker-c', 'SyntheticError'))
            self.assertEqual(self.connection.execute("""SELECT status,attempts,lease_owner,error_class,available_at>now()
                FROM ops.jobs WHERE job_id=%s""", (job,)).fetchone(), ('READY', 2, None, 'SyntheticError', True))
            backoff = queue.claim(self.settings, 'synthetic-worker-d')
            self.assertTrue(backoff is None or str(backoff[0]) != job)
            self.connection.execute("""UPDATE ops.jobs SET status='RUNNING',attempts=max_attempts,lease_owner='synthetic-worker-e',
                lease_until=now()-interval '1 second' WHERE job_id=%s""", (job,))
            self.assertEqual(self.status(), 'failed')
            swept = queue.claim(self.settings, 'synthetic-worker-f')
            self.assertTrue(swept is None or str(swept[0]) != job)
            self.assertEqual(self.connection.execute('SELECT status,error_class,lease_owner FROM ops.jobs WHERE job_id=%s', (job,)).fetchone(),
                             ('FAILED', 'AttemptsExhausted', None))

    def test_worker_restores_the_job_payload_scope_for_both_job_types(self):
        from p50k.product import ai_worker
        captured = []

        def detector(connection, cutoff, origin):
            captured.append((selection(), analysis_scope_key(), historical_mode(), cutoff, origin, connection is self.connection))
            return {'run_id': str(uuid4()), 'reused': False}

        def proposal(settings, code, **policy):
            captured.append((selection(), analysis_scope_key(), code, policy))
            return {'decision_id': 0, 'cached': False, 'validation_state': 'VALID'}

        with patch.object(queue, 'connect', self.shared), patch.object(analysis_jobs, 'connect', self.shared), \
                patch('p50k.product.detector_runner.run', side_effect=detector), \
                patch.object(ai_worker, 'evaluate', side_effect=proposal), patch.dict(os.environ, LIVE):
            analysis_jobs.request_analysis(self.connection, self.settings, self.selected)
            replay = self.job_id()
            self.first_in_line(replay)
            self.assertTrue(ai_worker.step(self.settings, 'synthetic-worker-scope'))
            with use_analysis_date(self.selected):
                retrospective = queue.enqueue(self.settings, self.code, self.sha)
            live = queue.enqueue(self.settings, self.code, self.sha)
            self.assertNotEqual(retrospective, live)
            self.first_in_line(retrospective)
            self.assertTrue(ai_worker.step(self.settings, 'synthetic-worker-scope'))
        expected = datetime.combine(self.day, time.max, ISTANBUL)
        self.assertEqual(captured, [
            (self.selected, 'asof:' + self.selected, True, expected, 'HISTORICAL_REPLAY', True),
            (self.selected, 'asof:' + self.selected, self.code, {'bucket': 'batch', 'max_calls': 1}),
        ])
        states = dict(self.connection.execute("""SELECT job_id::text,status FROM ops.jobs WHERE job_id IN (%s,%s,%s)""",
                                              (replay, retrospective, live)).fetchall())
        self.assertEqual(states, {replay: 'SUCCEEDED', retrospective: 'SUCCEEDED', live: 'READY'})
        payloads = dict(self.connection.execute("SELECT job_id::text,payload->>'analysis_date' FROM ops.jobs WHERE job_id IN (%s,%s)",
                                                (retrospective, live)).fetchall())
        self.assertEqual(payloads, {retrospective: self.selected, live: 'live'})
        self.assertEqual(selection(self.settings), 'live')

    def test_workflow_reads_only_the_selected_day_and_its_own_jobs(self):
        older_day = self.day - timedelta(days=2)
        older_run, _ = self.make_run(older_day, origin='SYNTHETIC')
        reader = WorkflowQueries(self.connection)
        with use_analysis_date(self.selected):
            waiting = reader.overview(current_cutoff(), synthetic=True)
        self.assertIsNone(waiting.run)
        self.assertEqual((waiting.evidence.total, waiting.decisions.packets), (0, 0))
        own_run, _ = self.make_run(self.day, origin='SYNTHETIC')
        with use_analysis_date(self.selected):
            self.assertEqual(reader.overview(current_cutoff(), synthetic=True).run.run_id, own_run)
        with use_analysis_date(older_day.isoformat()):
            self.assertEqual(reader.overview(current_cutoff(), synthetic=True).run.run_id, older_run)

        def total(jobs):
            return jobs.ready + jobs.running + jobs.succeeded + jobs.failed

        with patch.dict(os.environ, LIVE):
            live_before = total(reader.overview(datetime.now(timezone.utc), synthetic=True).jobs)
        for selected, status in ((self.selected, 'READY'), (self.selected, 'FAILED'), ('live', 'SUCCEEDED')):
            self.connection.execute("INSERT INTO ops.jobs(job_type,idempotency_key,payload,status) VALUES('ai_decide',%s,%s,%s)",
                                    ('synthetic-scope:' + uuid4().hex,
                                     Jsonb({'fund_code': self.code, 'analysis_date': selected, 'budget_bucket': 'batch'}), status))
        with use_analysis_date(self.selected):
            jobs = reader.overview(current_cutoff(), synthetic=True).jobs
        self.assertEqual((jobs.ready, jobs.running, jobs.succeeded, jobs.failed), (1, 0, 0, 1))
        with patch.dict(os.environ, LIVE):
            self.assertEqual(total(reader.overview(datetime.now(timezone.utc), synthetic=True).jobs), live_before + 1)

    def test_fund_evidence_never_substitutes_another_day_or_scope(self):
        reader = FundQueries(self.connection)
        older_day = self.day - timedelta(days=2)
        _, older = self.make_run(older_day)

        def signals(cutoff):
            return reader.signals(self.code, None, cutoff.astimezone(ISTANBUL).date(), cutoff, 10, 0)

        with use_analysis_date(self.selected):
            end = current_cutoff()
            waiting = signals(end)
            self.assertEqual((waiting.total, waiting.origin), (0, 'HISTORICAL_REPLAY'))
            self.assertIsNone(evidence_detail(reader, older, self.actor, end))
            self.assertEqual(signals(end - timedelta(days=1)).total, 0)
            self.assertEqual([item.evidence_id for item in signals(replay_cutoff(older_day)).items], [older])
        _, current = self.make_run(self.day)
        _, live = self.make_run(None, origin='DELAYED', cutoff=datetime.now(timezone.utc) - timedelta(minutes=5))
        with use_analysis_date(self.selected):
            end = current_cutoff()
            self.assertEqual([item.evidence_id for item in signals(end).items], [current])
            detail = evidence_detail(reader, current, self.actor, end)
            self.assertTrue(detail['is_current'])
            self.assertEqual(detail['signal'].origin, 'HISTORICAL_REPLAY')
            self.assertIsNone(evidence_detail(reader, older, self.actor, end))
            self.assertIsNone(evidence_detail(reader, live, self.actor, end))
        with patch.dict(os.environ, LIVE):
            now = datetime.now(timezone.utc)
            self.assertIsNone(evidence_detail(reader, current, self.actor, now))
            self.assertEqual(evidence_detail(reader, live, self.actor, now)['signal'].origin, 'DELAYED')
            self.assertNotIn(current, [item.evidence_id for item in signals(now).items])
            self.assertEqual(signals(now).origin, 'DELAYED')

    def test_saved_funds_and_notifications_read_only_the_selected_day(self):
        self.connection.execute('INSERT INTO auth.watchlist_funds(user_id,fund_code) VALUES(%s,%s)', (self.actor, self.code))
        older_day = self.day - timedelta(days=2)
        _, older = self.make_run(older_day, origin='SYNTHETIC')
        with use_analysis_date(self.selected):
            waiting = _snapshot(self.connection, self.settings, self.actor, current_cutoff())
        self.assertIsNone(waiting['run_id'])
        self.assertEqual(waiting['signals'], [])
        self.assertEqual([(item['fund_code'], item['triggered_count'], item['signal_count']) for item in waiting['items']],
                         [(self.code, 0, 0)])
        own_run, own = self.make_run(self.day, origin='SYNTHETIC')
        with use_analysis_date(self.selected):
            current = _snapshot(self.connection, self.settings, self.actor, current_cutoff())
        self.assertEqual(current['run_id'], own_run)
        self.assertEqual([item['evidence_id'] for item in current['signals']], [own])
        with use_analysis_date(older_day.isoformat()):
            earlier = _snapshot(self.connection, self.settings, self.actor, current_cutoff())
        self.assertEqual([item['evidence_id'] for item in earlier['signals']], [older])

    def decision(self, origin: str, cutoff: datetime, *, method: str = 'SINGLE', prompt: str = 'synthetic-prompt',
                 rationale: str | None = None) -> int:
        digest = sha256(uuid4().bytes).hexdigest()
        evidence = 'synthetic-scope-' + uuid4().hex
        packet = {'fund_code': self.code, 'fund_name': 'Synthetic scope fund', 'category': 'Synthetic scope category',
                  'as_of': (cutoff.astimezone(ISTANBUL).date() - timedelta(days=1)).isoformat(),
                  'evidence': [{'evidence_id': evidence, 'detector_id': 'D1', 'state': 'TRIGGERED', 'value': '3',
                                'threshold': '2', 'effective_date': None, 'is_attribute': False}],
                  'allowed_options': ['MATERIAL', 'INSUFFICIENT_EVIDENCE']}
        packet_id = self.connection.execute("""INSERT INTO ai.packets(fund_code,packet_sha256,origin,cutoff,payload,allowed_options)
            VALUES(%s,%s,%s,%s,%s,'["MATERIAL","INSUFFICIENT_EVIDENCE"]') RETURNING packet_id""",
                                            (self.code, digest, origin, None if origin == 'DELAYED' else cutoff,
                                             Jsonb({**packet, 'run_id': str(uuid4()), 'origin': origin,
                                                    'cutoff': cutoff.isoformat()}))).fetchone()[0]
        return self.connection.execute("""INSERT INTO ai.decisions(packet_id,fund_code,packet_sha256,decision_value,validation_state,
                evidence_ids,rationale,model_id,prompt_version,schema_version,ai_mode,call_id,method)
            VALUES(%s,%s,%s,'MATERIAL','VALID',%s,%s,'synthetic-model',%s,'synthetic-schema','mock',%s,%s)
            RETURNING decision_id""", (packet_id, self.code, digest, Jsonb([evidence]), rationale, prompt, uuid4().hex,
                                       method)).fetchone()[0]

    def test_proposals_are_listed_only_in_their_own_scope_and_mark_team_filings(self):
        text = '{{fund}} için ekip gözlemi sınadı; sonuç insan incelemesine sunuldu.'
        team = self.decision('HISTORICAL_REPLAY', replay_cutoff(self.day), method='TEAM', prompt='agent-reporter-v1',
                             rationale=text)
        older_day = (self.day - timedelta(days=1)).isoformat()
        older = self.decision('HISTORICAL_REPLAY', replay_cutoff(self.day - timedelta(days=1)))
        live = self.decision('DELAYED', datetime.now(timezone.utc) - timedelta(minutes=5))

        def listed(selected: str, review_only=False):
            with patch.object(decisions, 'connect', self.shared), use_analysis_date(selected):
                return decisions.decision_rows(self.settings, self.code, review_only)

        self.assertEqual([(row['decision_id'], row['team_proposal']) for row in listed(self.selected)], [(team, True)])
        self.assertEqual([(row['decision_id'], row['team_proposal']) for row in listed(older_day)], [(older, False)])
        self.assertEqual([(row['decision_id'], row['team_proposal']) for row in listed('live')], [(live, False)])
        # The Raportör's stored text uses the same plain-language renderer as materiality-v4.
        self.assertEqual(listed(self.selected)[0]['rationale_tr'], text.replace('{{fund}}', self.code))
        self.assertEqual([row['decision_id'] for row in listed(self.selected, review_only=True)], [team])
        with patch.object(decisions, 'connect', self.shared), use_analysis_date(self.selected):
            decisions.review(self.settings, team, self.actor, 'OVERRIDE', 'INSUFFICIENT_EVIDENCE', 'Synthetic reviewer reason')
        self.assertEqual(listed(self.selected, review_only=True), [])
        reviewed, = listed(self.selected)
        self.assertEqual((reviewed['effective_value'], reviewed['decided_by'], reviewed['original_value'], reviewed['team_proposal']),
                         ('INSUFFICIENT_EVIDENCE', 'HUMAN', 'MATERIAL', True))
        self.assertEqual([row['decision_id'] for row in listed('live', review_only=True)], [live])

    def test_reviews_are_accepted_only_within_the_scope_of_the_reviewed_decision(self):
        retrospective = self.decision('HISTORICAL_REPLAY', replay_cutoff(self.day))
        live = self.decision('DELAYED', datetime.now(timezone.utc) - timedelta(minutes=5))
        with patch.object(decisions, 'connect', self.shared):
            with self.assertRaisesRegex(ValueError, 'DECISION_OUTSIDE_SELECTED_DATE'):
                decisions.review(self.settings, retrospective, self.actor, 'ACCEPT', None, None)
            self.assertIsInstance(decisions.review(self.settings, live, self.actor, 'ACCEPT', None, None), int)
            with use_analysis_date((self.day - timedelta(days=1)).isoformat()), \
                    self.assertRaisesRegex(ValueError, 'DECISION_OUTSIDE_SELECTED_DATE'):
                decisions.review(self.settings, retrospective, self.actor, 'ACCEPT', None, None)
            with use_analysis_date(self.selected):
                with self.assertRaisesRegex(ValueError, 'DECISION_OUTSIDE_SELECTED_DATE'):
                    decisions.review(self.settings, live, self.actor, 'ACCEPT', None, None)
                self.assertIsInstance(decisions.review(self.settings, retrospective, self.actor, 'OVERRIDE',
                                                       'INSUFFICIENT_EVIDENCE', 'Synthetic reviewer reason'), int)
