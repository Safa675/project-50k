"""No remote usage for failed connection establishment; uncertainty stays reserved."""
from __future__ import annotations
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path
import socket
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
import httpx2
from openai import APIConnectionError,APITimeoutError
from p50k.product.agents import control,llm,roles,runtime,store
from p50k.product.agents.config import AgentConfig
from p50k.product.settings import Settings
httpx=llm.httpx


def wrapped(cause):
    error=APIConnectionError(request=httpx2.Request('POST','https://example.invalid'))
    error.__cause__=cause
    return error


class ConnectionBudgetTests(TestCase):
    def test_only_connection_and_dns_errors_are_known_unsent(self):
        for cause in (httpx.ConnectError('synthetic'),httpx2.ConnectError('synthetic'),socket.gaierror(-2,'synthetic')):
            self.assertTrue(llm.request_not_sent(wrapped(cause)))
        for cause in (httpx.ReadError('synthetic'),httpx.WriteError('synthetic'),httpx.ConnectTimeout('synthetic'),httpx2.ReadTimeout('synthetic'),TimeoutError()):
            self.assertFalse(llm.request_not_sent(wrapped(cause)))
        self.assertFalse(llm.request_not_sent(APIConnectionError(request=httpx2.Request('POST','https://example.invalid'))))
        timeout=APITimeoutError(request=httpx2.Request('POST','https://example.invalid'))
        timeout.__cause__=httpx2.ConnectError('synthetic')
        self.assertFalse(llm.request_not_sent(timeout))

    def test_call_settles_zero_for_unsent_and_maximum_for_timeout(self):
        with TemporaryDirectory() as folder:
            key=Path(folder)/'synthetic-key';key.write_text('synthetic-credential',encoding='utf-8')
            config=AgentConfig(mode='live',key_file=key)
            for cause,code in ((httpx2.ConnectError('synthetic'),'MODEL_CONNECTION_FAILED'),(httpx2.ReadTimeout('synthetic'),'MODEL_CALL_FAILED')):
                with patch.object(control,'require_running'),patch.object(llm,'OpenAI') as sdk,patch.object(llm,'reserve_agent_budget',return_value='synthetic-reservation') as reserved,patch.object(llm,'settle') as settled:
                    sdk.return_value.responses.create.side_effect=wrapped(cause)
                    with self.assertRaises(llm.CallFailed) as raised:
                        llm.call(Settings(),config,'hypothesizer',instructions='Synthetic',payload={},schema={},schema_name='test',prompt_version='test',schema_version='test')
                    amount=Decimal(0) if code=='MODEL_CONNECTION_FAILED' else reserved.call_args.args[2]
                    self.assertEqual(raised.exception.code,code)
                    self.assertEqual(raised.exception.cost,amount)
                    self.assertEqual(settled.call_args.args[2],amount)

    def test_uncertain_transport_errors_remain_charged_with_nested_connection_failure(self):
        for transport in (httpx, httpx2):
            for error_type in (transport.ReadError, transport.WriteError, transport.ProtocolError):
                with self.subTest(transport=transport.__name__, error=error_type.__name__):
                    uncertain = error_type('synthetic')
                    uncertain.__cause__ = transport.ConnectError('synthetic')
                    self.assertFalse(llm.request_not_sent(wrapped(uncertain)))
                    # Inspect both branches, even when an explicit cause exists beside a context.
                    error = wrapped(transport.ConnectError('synthetic'))
                    error.__context__ = uncertain
                    self.assertFalse(llm.request_not_sent(error))

    def test_known_unsent_failure_does_not_retry_immediately(self):
        with TemporaryDirectory() as folder:
            key=Path(folder)/'synthetic-key';key.write_text('synthetic-credential',encoding='utf-8')
            failure=llm.CallFailed('MODEL_CONNECTION_FAILED','synthetic-reservation',Decimal(0))
            with patch.object(llm,'call',side_effect=failure) as called:
                with self.assertRaises(roles.Failed) as raised:
                    roles.run_ai(Settings(),AgentConfig(mode='live',key_file=key),'hypothesizer',{}, {},lambda item:item,lambda:{})
                self.assertEqual(called.call_count,1)
                self.assertEqual(raised.exception.code,'MODEL_CONNECTION_FAILED')

    def test_connection_retries_back_off_five_then_ten_minutes_and_stop(self):
        failure=roles.Failed('MODEL_CONNECTION_FAILED',['synthetic-reservation'],Decimal(0))
        for attempt,minimum in ((1,300),(2,600)):
            before=datetime.now(timezone.utc)
            with patch.object(runtime,'complete') as complete:
                self.assertTrue(runtime.retry_later(Settings(),AgentConfig(),SimpleNamespace(attempts=attempt),'worker',failure))
                delay=(complete.call_args.kwargs['not_before']-before).total_seconds()
                self.assertGreaterEqual(delay,minimum);self.assertLess(delay,minimum+5)
        with patch.object(runtime,'complete') as complete:
            self.assertFalse(runtime.retry_later(Settings(),AgentConfig(),SimpleNamespace(attempts=store.MAX_ATTEMPTS),'worker',failure))
            complete.assert_not_called()
