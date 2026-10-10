"""Synthetic workflow scope, current reviews, authentication and aggregate egress."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import os
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb

from p50k.product.auth import require_session
from p50k.product.db import connect
from p50k.product.settings import Settings
from p50k.product.workflow import WorkflowQueries, safe_ingest_counts
from p50k.product.workflow_routes import get_workflow_queries, router


class WorkflowBoundaryTests(unittest.TestCase):
    def test_ingest_counts_never_return_arbitrary_metadata_or_private_paths(self):
        value = {"obs.fund_prices": {"input": 7, "inserted": 2, "missing": 1, "path": "private/path", "non_null": True},
                 "obs.kap_documents": {"input": -1, "inserted": "4"}, "unknown": {"input": 9},
                 "instruments": 3, "prices": 11, "manifest_sha256": "private-metadata", "actions": False}
        self.assertEqual(safe_ingest_counts(value), {"obs.fund_prices": {"input": 7, "inserted": 2, "missing": 1},
                         "obs.kap_documents": {}, "stocks": {"instruments": 3, "prices": 11}})
        self.assertEqual(safe_ingest_counts(None), {})

    def test_workflow_route_requires_session_before_reading_data(self):
        application = FastAPI()
        application.include_router(router)
        reader = MagicMock()
        application.dependency_overrides[get_workflow_queries] = lambda: reader
        with TestClient(application) as client:
            self.assertEqual(client.get('/workflow').status_code, 401)
        reader.overview.assert_not_called()

    def test_reader_transaction_is_read_only_and_bounded(self):
        connection = MagicMock()
        connection.__enter__.return_value = connection
        request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(product_settings=Settings())))
        with patch('p50k.product.workflow_routes.connect', return_value=connection):
            dependency = get_workflow_queries(request)
            self.assertIsInstance(next(dependency), WorkflowQueries)
            dependency.close()
        self.assertEqual([call.args[0] for call in connection.execute.call_args_list],
                         ['SET TRANSACTION READ ONLY', "SET LOCAL statement_timeout='5s'"])

    def test_missing_stock_schema_returns_actual_unavailability_without_table_queries(self):
        reader = WorkflowQueries(MagicMock())
        with patch.object(reader, 'rows', return_value=[{'present': False}]) as query:
            result = reader.stock_availability(datetime.now(timezone.utc))
        self.assertEqual(result.state, 'SCHEMA_ABSENT')
        self.assertEqual(result.price_observations, 0)
        self.assertEqual(query.call_count, 1)


@unittest.skipUnless(os.environ.get('P50K_TEST_DATABASE') == '1', 'Requires isolated PostgreSQL p50k_dev')
class WorkflowDatabaseTests(unittest.TestCase):
    def setUp(self):
        settings = Settings.from_env()
        if settings.db_name != 'p50k_dev':
            raise RuntimeError('Synthetic workflow fixtures require p50k_dev')
        self.connection = connect(settings)
        self.addCleanup(self.connection.close)
        self.reader = WorkflowQueries(self.connection)
        self.cutoff = datetime.now(timezone.utc)
        self.code = 'WF' + uuid4().hex[:10].upper()
        self.sha = hashlib.sha256(self.code.encode()).hexdigest()
        self.connection.execute("INSERT INTO ref.funds(fund_code,name,source_sha256) VALUES(%s,'Synthetic workflow fund',%s)", (self.code,self.sha))
        self.actor = self.connection.execute("INSERT INTO auth.users(email,password_hash) VALUES(%s,'synthetic-hash') RETURNING user_id", (uuid4().hex+'@example.invalid',)).fetchone()[0]

    def detector_run(self, *, future=False, complete=True, attribute=False):
        version = 'synthetic-workflow-' + uuid4().hex
        self.connection.execute("""INSERT INTO det.detector_versions(version_id,protocol_version,protocol_sha256,code_sha256,thresholds,calibration_input_sha256,calibration_cutoff)
            VALUES(%s,'synthetic-workflow-v1',%s,%s,'{}',%s,'2020-01-01T00:00:00Z')""", (version,self.sha,self.sha,self.sha))
        cutoff = self.cutoff + timedelta(days=1) if future else self.cutoff - timedelta(minutes=1)
        run_id = self.connection.execute("""INSERT INTO det.detector_runs(protocol_version,protocol_sha256,origin,cutoff,parameters,created_at)
            VALUES('synthetic-workflow-v1',%s,'SYNTHETIC',%s,'{}',%s) RETURNING run_id""", (self.sha,cutoff,self.cutoff-timedelta(seconds=30))).fetchone()[0]
        for detector,state,is_attribute in (('D1','TRIGGERED',False),('D5','NOT_TRIGGERED',True)):
            evidence_id = 'synthetic-workflow-' + uuid4().hex
            self.connection.execute("""INSERT INTO det.evidence_items(evidence_id,fund_code,run_id,detector_id,origin,effective_date,available_at,unit,values,triggered,state,source_references,metadata)
                VALUES(%s,%s,%s,%s,'SYNTHETIC',%s,%s,'synthetic','{}',%s,%s,'[]',%s)""",
                (evidence_id,self.code,run_id,detector,cutoff.date(),cutoff,state=='TRIGGERED',state,Jsonb({'is_attribute':is_attribute})))
            self.connection.execute("INSERT INTO det.signals(run_id,fund_code,detector_id,state,reason,evidence_id,as_of) VALUES(%s,%s,%s,%s,'SYNTHETIC',%s,%s)", (run_id,self.code,detector,state,evidence_id,cutoff.date()))
        if complete:
            self.connection.execute("""INSERT INTO det.run_inputs(run_id,version_id,input_sha256,as_of,origin,cutoff)
                VALUES(%s,%s,%s,%s,'SYNTHETIC',%s)""", (run_id,version,self.sha,cutoff.date(),cutoff))
        return run_id

    def packet(self, run_id, *, future=False):
        digest = hashlib.sha256(uuid4().bytes).hexdigest()
        created = self.cutoff + timedelta(days=1) if future else self.cutoff - timedelta(seconds=20)
        return self.connection.execute("""INSERT INTO ai.packets(fund_code,packet_sha256,origin,payload,allowed_options,created_at)
            VALUES(%s,%s,'SYNTHETIC',%s,'["MATERIAL","INSUFFICIENT_EVIDENCE"]',%s) RETURNING packet_id""", (self.code,digest,Jsonb({'run_id':str(run_id)}),created)).fetchone()[0], digest

    def proposal(self, packet_id, digest, state):
        return self.connection.execute("""INSERT INTO ai.decisions(packet_id,fund_code,packet_sha256,decision_value,validation_state,evidence_ids,model_id,prompt_version,schema_version,ai_mode,call_id,created_at)
            VALUES(%s,%s,%s,%s,%s,'[]','synthetic-model','synthetic-prompt','synthetic-schema','mock',%s,%s) RETURNING decision_id""", (packet_id,self.code,digest,'MATERIAL' if state=='VALID' else None,state,uuid4().hex,self.cutoff-timedelta(seconds=10))).fetchone()[0]

    def test_latest_complete_run_excludes_future_cutoff_and_incomplete_results(self):
        run_id = self.detector_run()
        self.detector_run(future=True)
        self.detector_run(future=True, complete=False)
        result = self.reader.overview(self.cutoff, synthetic=True)
        self.assertEqual(result.run.run_id, str(run_id))
        self.assertEqual(result.evidence.total, 2)
        self.assertEqual(result.evidence.funds, 1)
        self.assertEqual(result.evidence.triggered, 1)
        self.assertEqual(result.evidence.not_triggered, 0)
        self.assertEqual(result.evidence.attributes, 1)
        self.assertEqual(result.decisions.packets, 0)

    def test_latest_proposal_and_human_review_are_scoped_to_current_run_packet(self):
        run_id = self.detector_run()
        old_packet,old_sha = self.packet(uuid4())
        self.proposal(old_packet,old_sha,'VALID')
        packet_id,digest = self.packet(run_id)
        first = self.proposal(packet_id,digest,'VALID')
        self.proposal(packet_id,digest,'INVALID')
        self.connection.execute("""INSERT INTO ai.decision_reviews(decision_id,packet_sha256,action,override_value,reason,reviewer_id,created_at)
            VALUES(%s,%s,'OVERRIDE','MATERIAL','Synthetic reviewer note',%s,%s)""", (first,digest,self.actor,self.cutoff-timedelta(seconds=5)))
        future_packet,future_sha = self.packet(run_id,future=True)
        self.proposal(future_packet,future_sha,'VALID')
        result = self.reader.overview(self.cutoff, synthetic=True)
        self.assertEqual(result.decisions.packets, 1)
        self.assertEqual(result.decisions.valid_synthetic, 0)
        self.assertEqual(result.decisions.invalid, 1)
        self.assertEqual(result.decisions.reviewed, 1)
        self.assertEqual(result.decisions.overridden, 1)
        self.assertEqual(result.decisions.models[0].model_id, 'synthetic-model')
        output = result.model_dump_json()
        self.assertNotIn('Synthetic reviewer note', output)
        self.assertNotIn('@example.invalid', output)


if __name__ == '__main__':
    unittest.main()
