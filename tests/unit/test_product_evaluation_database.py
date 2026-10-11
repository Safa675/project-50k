"""PostgreSQL (p50k_dev only) checks for the after-the-fact comparison of the 12 September scan with
confirmed SPK liquidation orders: every count, the AN-FND-005 exclusion, abstentions and the route.

Other synthetic tests may leave liquidation orders for their own funds; assertions are scoped to this
test's run, whose universe holds only the funds seeded here."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
import hashlib
import os
import unittest
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb
from psycopg.errors import CheckViolation

from p50k.product import evaluation
from p50k.product.archive import ISTANBUL
from p50k.product.auth import Principal, require_session
from p50k.product.db import connect
from p50k.product.evaluation_routes import router
from p50k.product.settings import Settings

SCAN = date(2026, 9, 12)
AS_OF = date(2026, 9, 11)


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def seed_run(connection, funds: dict[str, list[tuple]]) -> str:
    """A sealed synthetic run for 12 September; a signal may carry (detector, state, late, attribute)."""
    cutoff = datetime.combine(SCAN, time.max, ISTANBUL)
    version = 'synthetic-evaluation-' + uuid4().hex
    connection.execute("""INSERT INTO det.detector_versions(version_id,protocol_version,protocol_sha256,code_sha256,
        thresholds,calibration_input_sha256,calibration_cutoff) VALUES (%s,'synthetic-evaluation',%s,%s,'{}'::jsonb,%s,%s)""",
        (version, sha('synthetic-evaluation'), sha(version), sha('synthetic-calibration'), cutoff))
    run = connection.execute("""INSERT INTO det.detector_runs(protocol_version,protocol_sha256,origin,cutoff,parameters)
        VALUES ('synthetic-evaluation',%s,'SYNTHETIC',%s,'{}'::jsonb) RETURNING run_id""",
        (sha('synthetic-evaluation'), cutoff)).fetchone()[0]
    for code, items in funds.items():
        for detector, state, *flags in items:
            late, attribute = (list(flags) + [False, False])[:2]
            evidence = 'ev:evaluation:' + uuid4().hex
            statement = """INSERT INTO det.evidence_items(evidence_id,fund_code,run_id,detector_id,origin,
                effective_date,available_at,unit,values,thresholds,triggered,state,source_references,metadata)
                VALUES (%s,%s,%s,%s,'SYNTHETIC',%s,%s,'synthetic','{}','{}',%s,%s,'[]',%s)"""
            values = (evidence, code, run, detector, AS_OF, cutoff + timedelta(days=2) if late else cutoff - timedelta(hours=2),
                      {'TRIGGERED': True, 'NOT_TRIGGERED': False}.get(state), state, Jsonb({'is_attribute': True} if attribute else {}))
            if late:
                # Stored replay evidence is already guarded against look-ahead.
                # Verify that guard instead of bypassing it to construct a fixture.
                try:
                    with connection.transaction():
                        connection.execute(statement, values)
                except CheckViolation:
                    continue
                raise AssertionError('Future evidence was admitted to the stored scan')
            connection.execute(statement, values)
            connection.execute("""INSERT INTO det.signals(run_id,fund_code,detector_id,state,reason,value,threshold,
                evidence_id,as_of) VALUES (%s,%s,%s,%s,'SYNTHETIC',%s,%s,%s,%s)""",
                (run, code, detector, state, Decimal('2') if state == 'TRIGGERED' else Decimal('1'), Decimal('1.5'),
                 evidence, AS_OF))
    connection.execute("""INSERT INTO det.run_inputs(run_id,version_id,input_sha256,input_watermark,as_of,origin,cutoff,complete)
        VALUES (%s,%s,%s,%s,%s,'SYNTHETIC',%s,true)""",
        (run, version, sha(version + ':input'), cutoff - timedelta(hours=2), AS_OF, cutoff))
    return str(run)


def seed_event(connection, code: str, status: str = 'CONFIRMED', effective: date = date(2026, 9, 17)) -> None:
    confirmed = datetime(2026, 9, 18, 10, 0, tzinfo=ISTANBUL)
    connection.execute("""INSERT INTO obs.regulatory_events(event_id,fund_code,event_type,effective_date,status,confirmed_by,
        confirmed_at,source_sha256,origin,published_at,available_at,availability_rule,metadata)
        VALUES (%s,%s,'SPK_LIQUIDATION_ORDER',%s,%s,%s,%s,%s,'SYNTHETIC',NULL,NULL,'synthetic-evaluation',%s)""",
        ('synthetic-evaluation:' + uuid4().hex, code, effective, status,
         'synthetic-reviewer' if status == 'CONFIRMED' else None, confirmed if status == 'CONFIRMED' else None,
         sha(code + status), Jsonb({'bulletin_id': '2026-61', 'publication_date': '2026-09-17',
                                    'source_url': 'https://example.invalid/synthetic.pdf'})))


@unittest.skipUnless(os.environ.get('P50K_TEST_DATABASE') == '1', 'Requires isolated PostgreSQL p50k_dev')
class RetrospectiveDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.settings = Settings.from_env()
        if self.settings.db_name != 'p50k_dev':
            raise RuntimeError('Synthetic evaluation tests require p50k_dev')
        tag = uuid4().hex[:7].upper()
        self.code = {name: 'EV' + str(index).zfill(2) + tag for index, name in enumerate(
            ('CAUGHT', 'REG', 'NA', 'DQ', 'OUT', 'QUIET', 'OTHERNA', 'LATE', 'CAND', 'DATE', 'GONE'))}
        with connect(self.settings) as connection:
            for code in self.code.values():
                connection.execute('INSERT INTO ref.funds(fund_code,name,category,source_sha256) VALUES (%s,%s,%s,%s)',
                                   (code, 'Synthetic evaluation fund ' + code, 'Synthetic evaluation ' + tag, sha(code)))
            self.run = seed_run(connection, {
                self.code['CAUGHT']: [('D1', 'TRIGGERED'), ('AN-DQ-002', 'NOT_TRIGGERED')],
                self.code['REG']: [('AN-FND-005', 'TRIGGERED'), ('D1', 'NOT_TRIGGERED')],
                self.code['NA']: [('D1', 'ABSTAINED'), ('D2', 'NOT_TRIGGERED', False, True), ('AN-DQ-002', 'NOT_TRIGGERED')],
                self.code['DQ']: [('AN-DQ-002', 'TRIGGERED'), ('D1', 'NOT_TRIGGERED')],
                self.code['OUT']: [('D3', 'TRIGGERED')],
                self.code['QUIET']: [('D1', 'NOT_TRIGGERED'), ('D5', 'NOT_TRIGGERED', False, True)],
                self.code['OTHERNA']: [('D1', 'ABSTAINED'), ('AN-FND-005', 'ABSTAINED')],
                self.code['LATE']: [('D2', 'TRIGGERED', True), ('D1', 'NOT_TRIGGERED')],
                self.code['CAND']: [('D4', 'TRIGGERED')],
                self.code['DATE']: [('D1', 'NOT_TRIGGERED')]})
            for name in ('CAUGHT', 'CAUGHT', 'REG', 'NA', 'DQ', 'GONE'):
                seed_event(connection, self.code[name])
            seed_event(connection, self.code['CAND'], 'CANDIDATE')
            seed_event(connection, self.code['DATE'], effective=date(2026, 9, 24))

    def report(self):
        with connect(self.settings) as connection:
            return evaluation.retrospective(connection, version_id='synthetic-not-a-replay-version', include_synthetic=True)

    def test_counts_exclusions_and_abstentions(self):
        report = self.report()
        self.assertEqual(report['run']['run_id'], self.run)
        self.assertEqual((report['run']['as_of'], report['run']['origin']), (AS_OF.isoformat(), 'SYNTHETIC'))
        expected = {
            'all': {'caught': 2, 'missed': 1, 'listed_not_assessable': 1, 'flagged_outside': 2, 'quiet': 3,
                    'other_not_assessable': 1, 'listed_funds': 4, 'other_funds': 6, 'flagged': 4, 'scanned': 10},
            'price': {'caught': 1, 'missed': 2, 'listed_not_assessable': 1, 'flagged_outside': 2, 'quiet': 3,
                      'other_not_assessable': 1, 'listed_funds': 4, 'other_funds': 6, 'flagged': 3, 'scanned': 10},
            'data_quality': {'caught': 1, 'missed': 2, 'listed_not_assessable': 1, 'flagged_outside': 0, 'quiet': 0,
                             'other_not_assessable': 6, 'listed_funds': 4, 'other_funds': 6, 'flagged': 1, 'scanned': 10}}
        self.assertEqual({view: report['summaries'][view]['counts'] for view in evaluation.VIEWS}, expected)
        summary = report['summaries']['all']
        self.assertEqual(summary['detection_rate'], {'numerator': 2, 'denominator': 4, 'percent': '50.0'})
        self.assertEqual(summary['on_list_share'], {'numerator': 2, 'denominator': 4, 'percent': '50.0'})
        self.assertEqual(summary['other_flag_rate'], {'numerator': 2, 'denominator': 6, 'percent': '33.3'})
        self.assertEqual(summary['times_more_often'], '1.5')
        rows = {row['fund_code']: row for row in report['funds']}
        self.assertEqual(set(rows), {self.code[name] for name in ('CAUGHT', 'REG', 'NA', 'DQ', 'OUT', 'CAND')})
        self.assertEqual(rows[self.code['REG']]['detectors'], [])
        self.assertEqual(rows[self.code['REG']]['outcomes']['all'], 'missed')
        self.assertEqual(rows[self.code['NA']]['outcomes']['all'], 'listed_not_assessable')
        self.assertEqual(rows[self.code['CAND']]['outcomes']['all'], 'flagged_outside')
        self.assertFalse(rows[self.code['CAND']]['listed'])
        self.assertEqual(rows[self.code['CAUGHT']]['href'], '/funds/' + self.code['CAUGHT'])
        self.assertEqual(rows[self.code['DQ']]['outcomes'], {'all': 'caught', 'price': 'missed', 'data_quality': 'caught'})
        truth = report['ground_truth']
        self.assertIn({'fund_code': self.code['GONE'], 'name': 'Synthetic evaluation fund ' + self.code['GONE']}, truth['outside_scan'])
        self.assertNotIn(self.code['CAND'], [item['fund_code'] for item in truth['outside_scan']])
        self.assertIn('2026-61', truth['bulletins'])
        self.assertEqual((truth['status'], truth['decision_date']), ('CONFIRMED', '2026-09-17'))
        self.assertNotIn('https://example.invalid/synthetic.pdf', truth['source_urls'])

    def test_replay_runs_need_the_current_detector_version(self):
        with connect(self.settings) as connection:
            self.assertIsNone(evaluation.find_run(connection, 'synthetic-not-a-replay-version', False))
            self.assertEqual(evaluation.find_run(connection, 'synthetic-not-a-replay-version', True)['run_id'], self.run)

    def test_route_is_session_protected_and_read_only(self):
        application = FastAPI()
        application.state.product_settings = self.settings
        application.include_router(router)
        with TestClient(application) as client:
            self.assertIn(client.get('/evaluation/retrospective').status_code, {401, 403})
        application.dependency_overrides[require_session] = lambda: Principal(
            user_id=str(uuid4()), email='synthetic@example.invalid', role='viewer', session_id='synthetic-session', csrf_sha256='0' * 64)
        with TestClient(application) as client:
            response = client.get('/evaluation/retrospective')
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['run']['run_id'], self.run)
        self.assertEqual(body['summaries']['all']['counts']['caught'], 2)
        self.assertEqual(body['method']['excluded_detectors'], ['AN-FND-005'])


if __name__ == '__main__':
    unittest.main()
