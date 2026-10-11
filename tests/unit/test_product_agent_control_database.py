"""Persistent pause and lease checks against isolated p50k_dev only."""
from __future__ import annotations

import os
import unittest

import psycopg

from p50k.product.agents import control, sentinel, service, store
from p50k.product.agents.config import AgentConfig
from p50k.product.db import connect
from tests.unit import test_product_agents_database as agent_fixture


@unittest.skipUnless(os.environ.get('P50K_TEST_DATABASE') == '1', 'Requires isolated PostgreSQL p50k_dev')
class AgentControlDatabaseTests(unittest.TestCase):
    def setUp(self):
        agent_fixture.AgentTeamDatabaseTests.setUp(self)
        # The inherited fixture explicitly rejects every database except p50k_dev.
        self.addCleanup(control.set_state, self.settings, self.user, 'admin', 'RESUME')
        control.set_state(self.settings, self.user, 'admin', 'RESUME')

    claim = agent_fixture.AgentTeamDatabaseTests.claim

    def test_persistent_pause_preserves_running_lease_and_resume_claims_remaining_work(self):
        sentinel.scan(self.settings, self.scope)
        first = self.claim('synthetic-control-first', 0)
        self.assertIsNotNone(first)
        with connect(self.settings) as connection:
            before = connection.execute('SELECT count(*) FROM agents.messages').fetchone()[0]
        paused = control.set_state(self.settings, self.user, 'admin', 'PAUSE')
        self.assertTrue(paused['paused'])
        self.assertTrue(paused['finishing'])
        with connect(self.settings) as connection:
            self.assertTrue(control.state(connection)['paused'])
            self.assertIsNone(store.claim(connection, 'synthetic-control-paused', 0))
            self.assertTrue(store.owns(connection, first, 'synthetic-control-first'))
            self.assertTrue(store.finish(connection, first, 'synthetic-control-first', 'done'))
            self.assertEqual(connection.execute('SELECT count(*) FROM agents.messages').fetchone()[0], before)
        result = sentinel.scan(self.settings, self.scope)
        self.assertTrue(result['paused'])
        feed = service.team(self.settings, self.scope, AgentConfig(mode='off'))
        self.assertTrue(feed['control']['paused'])
        resumed = control.set_state(self.settings, self.user, 'admin', 'RESUME')
        self.assertFalse(resumed['paused'])
        remaining = self.claim('synthetic-control-resumed', 0)
        self.assertIsNotNone(remaining)
        self.assertNotEqual(first.task_id, remaining.task_id)
        with connect(self.settings) as connection:
            actions = connection.execute('SELECT action FROM agents.control_events WHERE actor_id=%s ORDER BY event_id',
                                         (self.user,)).fetchall()
            self.assertEqual(actions[-2:], [('PAUSE',), ('RESUME',)])
            attempts = connection.execute('SELECT attempts FROM agents.tasks WHERE task_id=%s', (remaining.task_id,)).fetchone()[0]
            self.assertTrue(store.finish(connection, remaining, 'synthetic-control-resumed', 'queued', error_class='TEAM_PAUSED'))
            self.assertEqual(connection.execute('SELECT attempts,status FROM agents.tasks WHERE task_id=%s',
                                                (remaining.task_id,)).fetchone(), (attempts - 1, 'queued'))

    def test_control_audit_cannot_be_changed(self):
        control.set_state(self.settings, self.user, 'admin', 'PAUSE')
        with self.assertRaises(psycopg.Error):
            with connect(self.settings) as connection:
                connection.execute("UPDATE agents.control_events SET action='RESUME' WHERE actor_id=%s", (self.user,))
        with self.assertRaises(psycopg.Error):
            with connect(self.settings) as connection:
                connection.execute('DELETE FROM agents.control_events WHERE actor_id=%s', (self.user,))

    def test_expired_lease_waits_for_resume_without_consuming_an_attempt(self):
        sentinel.scan(self.settings, self.scope)
        claimed = self.claim('synthetic-control-expired', 0)
        self.assertIsNotNone(claimed)
        with connect(self.settings) as connection:
            connection.execute("UPDATE agents.tasks SET lease_until=now()-interval '1 second' WHERE task_id=%s", (claimed.task_id,))
        control.set_state(self.settings, self.user, 'admin', 'PAUSE')
        self.assertIsNone(self.claim('synthetic-control-blocked', 0))
        with connect(self.settings) as connection:
            self.assertEqual(connection.execute('SELECT attempts,lease_owner FROM agents.tasks WHERE task_id=%s',
                                                (claimed.task_id,)).fetchone(), (claimed.attempts, 'synthetic-control-expired'))
        control.set_state(self.settings, self.user, 'admin', 'RESUME')
        resumed = self.claim('synthetic-control-recovered', 0)
        self.assertIsNotNone(resumed)
        self.assertEqual(resumed.task_id, claimed.task_id)
        self.assertEqual(resumed.attempts, claimed.attempts + 1)


if __name__ == '__main__':
    unittest.main()
