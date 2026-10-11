"""Global team admission controls use synthetic data and never pause the real DB."""
from __future__ import annotations

from decimal import Decimal
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from p50k.product.agents import control, llm, roles, runtime, sentinel, store
from p50k.product.agents.config import AgentConfig
from p50k.product.app import create_app
from p50k.product.auth import AuthService, Principal
from p50k.product.settings import Settings


class AgentControlTests(unittest.TestCase):
    def test_paused_claim_does_not_claim_or_modify_any_task(self):
        connection = MagicMock()
        with patch.object(control, 'allows_new_work', return_value=False):
            self.assertIsNone(store.claim(connection, 'synthetic-owner', 0))
        self.assertEqual(connection.execute.call_count, 1)  # statement timeout only

    def test_paused_sentinel_does_not_scan_or_create_messages(self):
        with patch.object(sentinel, 'connect') as opened, patch.object(control, 'allows_new_work', return_value=False), \
                patch.object(store, 'scope_run') as selected:
            result = sentinel.scan(Settings(), 'asof:2026-09-12')
        self.assertTrue(result['paused'])
        self.assertEqual(result['funds_scanned'], 0)
        selected.assert_not_called()
        self.assertEqual(opened.return_value.__enter__.return_value.execute.call_count, 1)

    def test_paused_call_never_reserves_budget_or_constructs_client(self):
        with TemporaryDirectory() as folder:
            key = Path(folder) / 'synthetic-key'
            key.write_text('synthetic-credential', encoding='utf-8')
            config = AgentConfig(mode='live', key_file=key)
            with patch.object(control, 'require_running', side_effect=control.TeamPaused()), \
                    patch.object(llm, 'reserve_agent_budget') as reserved, patch.object(llm, 'OpenAI') as client:
                with self.assertRaises(control.TeamPaused):
                    llm.call(Settings(), config, 'hypothesizer', instructions='synthetic', payload={},
                             schema={}, schema_name='synthetic', prompt_version='synthetic', schema_version='synthetic')
            reserved.assert_not_called()
            client.assert_not_called()

    def test_paused_task_returns_to_queue_with_prior_cost_and_no_skip_message(self):
        task = store.Task(str(uuid4()), str(uuid4()), 'hypothesizer', 1, 10, 'user',
                          'asof:2026-09-12', 'SYN1', str(uuid4()), None, 'investigating')
        with patch.object(runtime, 'load_case', return_value=SimpleNamespace()), \
                patch.object(roles, 'hypothesizer', side_effect=control.TeamPaused(['synthetic-call'], Decimal('.01'))), \
                patch.object(runtime, 'complete', return_value=True) as finished:
            self.assertEqual(runtime.execute(Settings(), AgentConfig(), task, 'synthetic-owner'), 'queued')
        self.assertEqual(finished.call_args.args[4], 'queued')
        self.assertEqual(finished.call_args.kwargs, {'error_class': 'TEAM_PAUSED',
                         'calls': ['synthetic-call'], 'cost': Decimal('.01')})

    def test_non_admin_and_invalid_action_fail_before_connecting(self):
        with patch.object(control, 'connect') as opened:
            for role in ('viewer', 'analyst'):
                with self.assertRaises(PermissionError):
                    control.set_state(Settings(), str(uuid4()), role, 'PAUSE')
            with self.assertRaises(ValueError):
                control.set_state(Settings(), str(uuid4()), 'admin', 'STOP')
        opened.assert_not_called()

    def test_control_route_checks_admin_action_and_standard_csrf(self):
        csrf = 's' * 43
        principal = Principal(str(uuid4()), 'synthetic@example.invalid', 'admin', str(uuid4()),
                              hashlib.sha256(csrf.encode()).hexdigest())
        application = create_app(Settings())
        snapshot = {'paused': True, 'changed_at': '2026-10-11T09:00:00+00:00', 'running_tasks': 0, 'finishing': False}
        with patch.object(AuthService, 'authenticate', return_value=principal), \
                patch.object(control, 'set_state', return_value=snapshot) as changed, \
                TestClient(application, base_url='http://localhost') as client:
            client.cookies.set('p50k_csrf', csrf)
            headers = {'origin': 'http://localhost:3070', 'x-csrf-token': csrf}
            self.assertEqual(client.post('/agents/control', json={'action': 'PAUSE'}).status_code, 403)
            self.assertEqual(client.post('/agents/control', headers=headers, json={'action': 'STOP'}).status_code, 422)
            self.assertEqual(client.post('/agents/control', headers=headers,
                                         json={'action': 'PAUSE', 'scope': 'live'}).status_code, 422)
            for role in ('viewer', 'analyst'):
                other = Principal(principal.user_id, principal.email, role, principal.session_id, principal.csrf_sha256)
                with patch.object(AuthService, 'authenticate', return_value=other):
                    self.assertEqual(client.post('/agents/control', headers=headers, json={'action': 'PAUSE'}).status_code, 403)
            changed.assert_not_called()
            self.assertEqual(client.post('/agents/control', headers=headers, json={'action': 'PAUSE'}).json(), snapshot)
            self.assertEqual(client.post('/agents/control', headers=headers, json={'action': 'RESUME'}).status_code, 200)
            self.assertEqual(changed.call_args.args[-1], 'RESUME')


if __name__ == '__main__':
    unittest.main()
