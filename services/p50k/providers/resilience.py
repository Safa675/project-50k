"""Circuit breaker and retry with backoff for provider calls.

Adapted from bist-quant (github.com/Safa675/bist-quant @ 8473426,
src/bist_quant/common/resilience.py, Apache-2.0), with these changes:
- retry_with_backoff requires `retry_on`, the exception types worth retrying,
  so certificate failures or unknown fund codes are not retried by default;
- an open circuit (CircuitBreakerError) is never retried;
- CircuitBreaker takes `failure_on`, so errors that say nothing about the
  provider's health (for example "no data for this fund") don't trip it;
- a half-open circuit lets one trial call through at a time;
- monotonic clock, and injectable clock, sleep and random source for tests;
- log lines name the exception class, not its message, which may carry URLs;
- the per-instance `_retry_policy` hook and borsapy logging setup are dropped.
"""
from __future__ import annotations

import logging
import random
import time
from enum import Enum
from functools import wraps
from threading import Lock
from typing import Callable, ParamSpec, TypeVar

logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerError(RuntimeError):
    """Raised when the circuit breaker blocks a call."""


class CircuitBreaker:
    """Thread-safe circuit breaker.

    After `failure_threshold` consecutive counted failures the circuit opens and
    calls fail fast with CircuitBreakerError. Once `recovery_timeout` seconds
    have passed, one trial call is let through (HALF_OPEN): success closes the
    circuit, a counted failure opens it again.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        *,
        failure_on: tuple[type[BaseException], ...] = (Exception,),
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if isinstance(failure_threshold, bool) or failure_threshold < 1:
            raise ValueError("failure_threshold must be at least 1")
        if recovery_timeout < 0:
            raise ValueError("recovery_timeout must not be negative")
        if not failure_on:
            raise ValueError("failure_on must name at least one exception type")
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._failure_on = failure_on
        self._clock = clock
        self._lock = Lock()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._opened_at = 0.0
        self._trial_in_flight = False

    @property
    def state(self) -> CircuitState:
        with self._lock:
            return self._state

    @property
    def failure_count(self) -> int:
        with self._lock:
            return self._failure_count

    def call(self, func: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> R:
        self._before_call()
        try:
            result = func(*args, **kwargs)
        except self._failure_on:
            self.record_failure()
            raise
        except BaseException:
            # Not a health signal: neither a failure nor a success.
            self._end_trial()
            raise
        self.record_success()
        return result

    def record_success(self) -> None:
        with self._lock:
            self._failure_count = 0
            self._state = CircuitState.CLOSED
            self._trial_in_flight = False

    def record_failure(self) -> None:
        with self._lock:
            self._failure_count += 1
            if (self._state is not CircuitState.CLOSED
                    or self._failure_count >= self.failure_threshold):
                self._state = CircuitState.OPEN
                self._opened_at = self._clock()
            self._trial_in_flight = False

    def _before_call(self) -> None:
        with self._lock:
            if self._state is CircuitState.CLOSED:
                return
            if self._state is CircuitState.OPEN:
                if self._clock() - self._opened_at < self.recovery_timeout:
                    raise CircuitBreakerError("Circuit breaker is open")
                self._state = CircuitState.HALF_OPEN
                self._trial_in_flight = False
            if self._trial_in_flight:
                raise CircuitBreakerError("Circuit breaker is half-open; a trial call is in progress")
            self._trial_in_flight = True

    def _end_trial(self) -> None:
        with self._lock:
            self._trial_in_flight = False


def retry_with_backoff(
    *,
    retry_on: tuple[type[BaseException], ...],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    sleep: Callable[[float], None] = time.sleep,
    uniform: Callable[[float, float], float] = random.uniform,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Retry a call on the given exception types with exponential backoff.

    Delays start at `base_delay` and grow by `backoff_factor` up to `max_delay`.
    With `jitter`, each sleep is drawn uniformly from [0, delay] ("full
    jitter"). CircuitBreakerError is never retried, even if it matches
    `retry_on`. After the last attempt the last exception is re-raised.

    To combine with a CircuitBreaker, retry around the breaker so every attempt
    counts toward it and an open circuit stops the retries:
    `retrying(lambda: breaker.call(fetch))`.
    """
    if not isinstance(retry_on, tuple) or not retry_on:
        raise ValueError("retry_on must be a non-empty tuple of exception types")
    if isinstance(max_retries, bool) or max_retries < 0:
        raise ValueError("max_retries must not be negative")
    if base_delay < 0 or max_delay < 0:
        raise ValueError("delays must not be negative")
    if backoff_factor < 1:
        raise ValueError("backoff_factor must be at least 1")

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            delay = min(base_delay, max_delay)
            attempt = 0
            while True:
                attempt += 1
                try:
                    return func(*args, **kwargs)
                except CircuitBreakerError:
                    raise
                except retry_on as exc:
                    if attempt > max_retries:
                        raise
                    pause = uniform(0.0, delay) if jitter and delay > 0 else delay
                    logger.warning(
                        "%s failed with %s (attempt %d of %d); retrying in %.2fs",
                        getattr(func, "__qualname__", repr(func)), type(exc).__name__,
                        attempt, max_retries + 1, pause,
                    )
                    sleep(pause)
                    delay = min(delay * backoff_factor, max_delay)

        return wrapper

    return decorator
