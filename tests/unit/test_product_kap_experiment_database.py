"""Synthetic PostgreSQL checks for the separately registered monthly experiment.

Only p50k_dev is permitted. Existing baseline records remain untouched; later
labels enter only the explicit after-the-fact comparison.
"""
from __future__ import annotations

from datetime import datetime, timedelta
import os
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb

from p50k.product import evaluation, kap_experiment
from p50k.product.auth import Principal, require_session
from p50k.product.db import connect
from p50k.product.evaluation_routes import router
from p50k.product.settings import Settings
from tests.unit.test_product_evaluation_database import seed_event, seed_run, sha


@unittest.skipUnless(os.environ.get('P50K_TEST_DATABASE') == '1', 'Requires isolated PostgreSQL p50k_dev')
class MonthlyExperimentDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.settings = Settings.from_env()
        if self.settings.db_name != 'p50k_dev':
            raise RuntimeError('Synthetic monthly experiment tests require p50k_dev')
        self.cutoff = evaluation.scan_cutoff()
        self.published = self.cutoff - timedelta(days=10)
        tag = uuid4().hex[:7].upper()
        self.codes = ['KE' + str(index) + tag for index in range(4)]
        with connect(self.settings) as connection:
            for code in self.codes:
                connection.execute('INSERT INTO ref.funds(fund_code,name,category,source_sha256) VALUES (%s,%s,%s,%s)',
                                   (code, 'Synthetic monthly experiment ' + code, 'Synthetic monthly ' + tag, sha(code)))
            self.run_id = seed_run(connection, {
                self.codes[0]: [('D1', 'TRIGGERED')],
                self.codes[1]: [('D1', 'NOT_TRIGGERED')],
                self.codes[2]: [('D2', 'TRIGGERED')],
                self.codes[3]: [('D1', 'NOT_TRIGGERED')],
            })

    def add_report(self, connection, code, period, value, units, *, published='DEFAULT',
                   available='DEFAULT', observed='DEFAULT', cadence='monthly'):
        published = self.published if published == 'DEFAULT' else published
        available = self.published if available == 'DEFAULT' else available
        observed = self.published if observed == 'DEFAULT' else observed
        identity = uuid4().hex
        report = {'period': period, 'total_value': value, 'units_outstanding': units}
        connection.execute('''INSERT INTO obs.kap_series
            (fund_code,series_key,report_period,cadence,source_sha256,origin,published_at,
             available_at,observed_at,availability_rule,metadata)
            VALUES (%s,%s,%s,%s,%s,'SYNTHETIC',%s,%s,%s,'synthetic-monthly-experiment',%s)''',
            (code, identity, period, cadence, sha(identity), published, available, observed, Jsonb({'report': report})))

    def canonical(self, codes=None, *, include_synthetic=True):
        with connect(self.settings) as connection:
            connection.execute('SET TRANSACTION READ ONLY')
            return connection.execute(kap_experiment.REPORT_SQL,
                (codes or self.codes, self.cutoff, self.cutoff, self.cutoff.date(), include_synthetic)).fetchall()

    def classify_rows(self, rows, code):
        reports = [kap_experiment.Monthly(period, value, units, published, available, ambiguous)
                   for fund, period, value, units, published, available, ambiguous in rows if fund == code]
        return kap_experiment.classify(reports, self.cutoff)

    def report(self):
        with connect(self.settings) as connection:
            connection.execute('SET TRANSACTION READ ONLY')
            return kap_experiment.report(connection, version_id='synthetic-independent-monthly', include_synthetic=True)

    def baseline_snapshot(self):
        with connect(self.settings) as connection:
            connection.execute('SET TRANSACTION READ ONLY')
            result = {}
            for table, key in (('det.detector_runs', 'run_id'), ('det.run_inputs', 'run_id'),
                               ('det.signals', 'evidence_id'), ('det.evidence_items', 'evidence_id')):
                result[table] = connection.execute(
                    f'SELECT row_to_json(item)::text FROM {table} item WHERE run_id=%s ORDER BY {key}',
                    (self.run_id,)).fetchall()
            return result

    def test_canonical_latest_revision_ties_and_partial_ties_fail_closed(self):
        with connect(self.settings) as connection:
            for code in self.codes:
                self.add_report(connection, code, '2026-07', '100', '100')
            latest, conflicting, partial, identical = self.codes
            self.add_report(connection, latest, '2026-08', '100', '100', available=self.published - timedelta(days=1))
            self.add_report(connection, latest, '2026-08', '200', '200')
            for value in ('200', '300'):
                self.add_report(connection, conflicting, '2026-08', value, value)
            self.add_report(connection, partial, '2026-08', None, '300')
            self.add_report(connection, partial, '2026-08', '300', '300')
            for _ in range(2):
                self.add_report(connection, identical, '2026-08', '200', '200')
        rows = self.canonical()
        self.assertEqual(len(rows), 8)
        self.assertEqual(self.classify_rows(rows, latest)['state'], 'FLAGGED')
        self.assertEqual(self.classify_rows(rows, identical)['state'], 'FLAGGED')
        for code in (conflicting, partial):
            self.assertEqual(self.classify_rows(rows, code), {'state': 'ABSTAINED', 'reason': 'AMBIGUOUS_REVISION'})
        self.assertEqual(self.canonical(include_synthetic=False), [])

    def test_future_unknown_and_unfinished_inputs_do_not_change_cutoff_classification(self):
        code = self.codes[0]
        with connect(self.settings) as connection:
            self.add_report(connection, code, '2026-07', '100', '100')
            self.add_report(connection, code, '2026-08', '110', '110')
        original = self.canonical([code])
        with connect(self.settings) as connection:
            future = self.cutoff + timedelta(microseconds=1)
            self.add_report(connection, code, '2026-08', '500', '500', published=future)
            self.add_report(connection, code, '2026-08', '500', '500', available=future)
            self.add_report(connection, code, '2026-08', '500', '500', published=None)
            self.add_report(connection, code, '2026-08', '500', '500', available=None)
            self.add_report(connection, code, '2026-09', '500', '500')
            self.add_report(connection, code, '2026-W35', '500', '500', cadence='weekly')
        self.assertEqual(self.canonical([code]), original)
        self.assertEqual(self.classify_rows(original, code)['state'], 'NOT_FLAGGED')

    def test_latest_missing_month_and_latest_missing_revision_never_fall_back(self):
        missing_month, missing_revision = self.codes[:2]
        with connect(self.settings) as connection:
            for code in (missing_month, missing_revision):
                self.add_report(connection, code, '2026-06', '100', '100')
                self.add_report(connection, code, '2026-07', '200', '200')
            self.add_report(connection, missing_month, '2026-08', None, None)
            self.add_report(connection, missing_revision, '2026-08', '400', '400', available=self.published-timedelta(days=1))
            self.add_report(connection, missing_revision, '2026-08', None, None)
        rows = self.canonical()
        for code in (missing_month, missing_revision):
            self.assertEqual(self.classify_rows(rows, code), {'state': 'ABSTAINED', 'reason': 'MISSING_OR_NONPOSITIVE'})

    def test_added_comparison_is_separate_read_only_and_endpoint_requires_session(self):
        with connect(self.settings) as connection:
            for index, code in enumerate(self.codes):
                self.add_report(connection, code, '2026-07', '100', '100')
                value = str((index + 1) * 100) if index else '110'
                self.add_report(connection, code, '2026-08', value, value)
        before = self.baseline_snapshot()
        no_labels = self.report()
        self.assertEqual(no_labels['counts']['flagged'], 3)
        self.assertEqual(no_labels['counts']['caught'], 0)
        with connect(self.settings) as connection:
            for code in self.codes[:3]:
                seed_event(connection, code)
        result = self.report()
        self.assertEqual(result['counts'], {'cohort': 4, 'assessed': 4, 'abstained': 0, 'flagged': 3,
            'listed_total': 3, 'caught': 2, 'baseline_caught': 2, 'added_to_price': 1,
            'union_price_caught': 3, 'outside_list': 1, 'listed_assessed': 3})
        self.assertTrue(result['baseline_unchanged'])
        self.assertFalse(result['feeds_agents'])
        self.assertTrue(result['development_result'])
        self.assertEqual(self.baseline_snapshot(), before)
        application = FastAPI()
        application.state.product_settings = self.settings
        application.include_router(router)
        with TestClient(application) as client:
            self.assertEqual(client.get('/evaluation/kap-scale-experiment').status_code, 401)
        application.dependency_overrides[require_session] = lambda: Principal(
            str(uuid4()), 'synthetic@example.invalid', 'viewer', 'synthetic-session', '0' * 64)
        actual_report = kap_experiment.report

        def assert_read_only(connection, **kwargs):
            self.assertEqual(connection.execute('SHOW transaction_read_only').fetchone()[0], 'on')
            return actual_report(connection, **kwargs)

        with patch.object(kap_experiment, 'report', side_effect=assert_read_only), TestClient(application) as client:
            response = client.get('/evaluation/kap-scale-experiment')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['counts'], result['counts'])
        self.assertEqual(self.baseline_snapshot(), before)


if __name__ == '__main__':
    unittest.main()
