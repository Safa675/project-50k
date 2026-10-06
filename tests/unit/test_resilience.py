import logging
import unittest

from p50k.providers.resilience import (CircuitBreaker, CircuitBreakerError, CircuitState,
                                       retry_with_backoff)


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class Transient(Exception):
    pass


class Permanent(Exception):
    pass


def raising(exc: BaseException):
    def run():
        raise exc
    return run


class CircuitBreakerTest(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=10, clock=self.clock)

    def trip(self):
        for _ in range(2):
            with self.assertRaises(Transient):
                self.breaker.call(raising(Transient()))

    def test_opens_after_threshold_and_fails_fast(self):
        self.trip()
        self.assertIs(self.breaker.state, CircuitState.OPEN)
        calls = []
        with self.assertRaises(CircuitBreakerError):
            self.breaker.call(lambda: calls.append(1))
        self.assertEqual(calls, [])

    def test_success_resets_consecutive_failures(self):
        with self.assertRaises(Transient):
            self.breaker.call(raising(Transient()))
        self.assertEqual(self.breaker.call(lambda: "ok"), "ok")
        with self.assertRaises(Transient):
            self.breaker.call(raising(Transient()))
        self.assertIs(self.breaker.state, CircuitState.CLOSED)
        self.assertEqual(self.breaker.failure_count, 1)

    def test_stays_open_until_recovery_timeout(self):
        self.trip()
        self.clock.now = 9.99
        with self.assertRaises(CircuitBreakerError):
            self.breaker.call(lambda: None)

    def test_successful_trial_closes(self):
        self.trip()
        self.clock.now = 10
        self.assertEqual(self.breaker.call(lambda: "ok"), "ok")
        self.assertIs(self.breaker.state, CircuitState.CLOSED)
        self.assertEqual(self.breaker.failure_count, 0)

    def test_failed_trial_reopens_and_restarts_timeout(self):
        self.trip()
        self.clock.now = 10
        with self.assertRaises(Transient):
            self.breaker.call(raising(Transient()))
        self.assertIs(self.breaker.state, CircuitState.OPEN)
        self.clock.now = 19.99
        with self.assertRaises(CircuitBreakerError):
            self.breaker.call(lambda: None)

    def test_only_one_trial_call_while_half_open(self):
        self.trip()
        self.clock.now = 10
        second = []

        def trial():
            # Another caller arriving during the trial is turned away.
            with self.assertRaises(CircuitBreakerError):
                self.breaker.call(lambda: second.append(1))
            return "first"

        self.assertEqual(self.breaker.call(trial), "first")
        self.assertEqual(second, [])
        self.assertIs(self.breaker.state, CircuitState.CLOSED)

    def test_excluded_errors_do_not_count(self):
        breaker = CircuitBreaker(failure_threshold=1, failure_on=(Transient,), clock=self.clock)
        with self.assertRaises(Permanent):
            breaker.call(raising(Permanent()))
        self.assertIs(breaker.state, CircuitState.CLOSED)
        self.assertEqual(breaker.failure_count, 0)

    def test_excluded_error_during_trial_frees_the_trial(self):
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=10,
                                 failure_on=(Transient,), clock=self.clock)
        with self.assertRaises(Transient):
            breaker.call(raising(Transient()))
        self.clock.now = 10
        with self.assertRaises(Permanent):
            breaker.call(raising(Permanent()))
        self.assertIs(breaker.state, CircuitState.HALF_OPEN)
        self.assertEqual(breaker.call(lambda: "ok"), "ok")
        self.assertIs(breaker.state, CircuitState.CLOSED)

    def test_rejects_invalid_configuration(self):
        for kwargs in ({"failure_threshold": 0}, {"failure_threshold": True},
                       {"recovery_timeout": -1}, {"failure_on": ()}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                CircuitBreaker(**kwargs)


class RetryWithBackoffTest(unittest.TestCase):
    def setUp(self):
        self.sleeps = []
        # Keep expected retry warnings out of the test output.
        logger = logging.getLogger("p50k.providers.resilience")
        handler = logging.NullHandler()
        logger.addHandler(handler)
        self.addCleanup(logger.removeHandler, handler)

    def retrying(self, **overrides):
        options = {"retry_on": (Transient,), "max_retries": 3, "base_delay": 1.0,
                   "max_delay": 60.0, "backoff_factor": 2.0, "jitter": False,
                   "sleep": self.sleeps.append}
        options.update(overrides)
        return retry_with_backoff(**options)

    def test_succeeds_after_transient_failures(self):
        outcomes = [Transient(), Transient(), "ok"]

        @self.retrying()
        def fetch():
            outcome = outcomes.pop(0)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        self.assertEqual(fetch(), "ok")
        self.assertEqual(self.sleeps, [1.0, 2.0])

    def test_gives_up_after_max_retries_and_reraises_last_error(self):
        errors = [Transient(i) for i in range(4)]
        attempts = []

        @self.retrying()
        def fetch():
            attempts.append(1)
            raise errors[len(attempts) - 1]

        with self.assertRaises(Transient) as caught:
            fetch()
        self.assertIs(caught.exception, errors[-1])
        self.assertEqual(len(attempts), 4)
        self.assertEqual(self.sleeps, [1.0, 2.0, 4.0])

    def test_delay_is_capped(self):
        @self.retrying(max_retries=4, base_delay=3.0, max_delay=5.0)
        def fetch():
            raise Transient()

        with self.assertRaises(Transient):
            fetch()
        self.assertEqual(self.sleeps, [3.0, 5.0, 5.0, 5.0])

    def test_does_not_retry_unlisted_errors(self):
        attempts = []

        @self.retrying()
        def fetch():
            attempts.append(1)
            raise Permanent()

        with self.assertRaises(Permanent):
            fetch()
        self.assertEqual(len(attempts), 1)
        self.assertEqual(self.sleeps, [])

    def test_never_retries_an_open_circuit(self):
        attempts = []

        @self.retrying(retry_on=(Exception,))
        def fetch():
            attempts.append(1)
            raise CircuitBreakerError("open")

        with self.assertRaises(CircuitBreakerError):
            fetch()
        self.assertEqual(len(attempts), 1)

    def test_full_jitter_draws_between_zero_and_delay(self):
        draws = []

        def uniform(low, high):
            draws.append((low, high))
            return high / 2

        @self.retrying(jitter=True, uniform=uniform, max_retries=2)
        def fetch():
            raise Transient()

        with self.assertRaises(Transient):
            fetch()
        self.assertEqual(draws, [(0.0, 1.0), (0.0, 2.0)])
        self.assertEqual(self.sleeps, [0.5, 1.0])

    def test_retry_around_breaker_stops_when_circuit_opens(self):
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=60, clock=FakeClock())
        attempts = []

        def fetch():
            attempts.append(1)
            raise Transient()

        @self.retrying(max_retries=5)
        def guarded():
            return breaker.call(fetch)

        with self.assertRaises(CircuitBreakerError):
            guarded()
        self.assertEqual(len(attempts), 2)
        self.assertIs(breaker.state, CircuitState.OPEN)

    def test_log_names_the_error_class_not_its_message(self):
        @self.retrying(max_retries=1)
        def fetch():
            raise Transient("https://example.test/?token=secret")

        with self.assertLogs("p50k.providers.resilience", level="WARNING") as logs:
            with self.assertRaises(Transient):
                fetch()
        self.assertIn("Transient", logs.output[0])
        self.assertNotIn("secret", logs.output[0])

    def test_preserves_function_metadata(self):
        @self.retrying()
        def fetch_fund():
            """Fetch one fund."""

        self.assertEqual(fetch_fund.__name__, "fetch_fund")
        self.assertEqual(fetch_fund.__doc__, "Fetch one fund.")

    def test_requires_explicit_retryable_errors(self):
        with self.assertRaises(TypeError):
            retry_with_backoff()
        for kwargs in ({"retry_on": ()}, {"retry_on": Transient},
                       {"retry_on": (Transient,), "max_retries": -1},
                       {"retry_on": (Transient,), "base_delay": -1},
                       {"retry_on": (Transient,), "backoff_factor": 0.5}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                retry_with_backoff(**kwargs)


if __name__ == "__main__":
    unittest.main()
