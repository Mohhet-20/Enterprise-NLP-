"""
Reliability primitives: retry with exponential backoff, and a lightweight
circuit breaker, in plain dependency-free Python, for wrapping anything
that can transiently fail (an external API, a model-hub download). The
tests drive the failure behaviour directly, so no flaky dependency is needed.
"""

import functools
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Tuple, Type, TypeVar

from backend.config.logging_config import get_logger

logger = get_logger("api")

T = TypeVar("T")


def retry(
    max_attempts: int = 3,
    initial_delay_seconds: float = 0.1,
    backoff_multiplier: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
):
    """Retries the decorated function on the given exception types, with
    exponential backoff. Re-raises the last exception if all attempts fail."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            delay = initial_delay_seconds
            last_exception: Exception = None  # type: ignore[assignment]
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exception = exc
                    if attempt == max_attempts:
                        logger.warning(
                            "retry_exhausted",
                            extra={"function": func.__name__, "attempts": attempt},
                        )
                        raise
                    logger.info(
                        "retry_attempt_failed",
                        extra={"function": func.__name__, "attempt": attempt, "next_delay_seconds": delay},
                    )
                    time.sleep(delay)
                    delay *= backoff_multiplier
            raise last_exception  # unreachable, satisfies type checkers

        return wrapper

    return decorator


class CircuitState(str, Enum):
    CLOSED = "closed"  # normal operation
    OPEN = "open"  # failing — reject calls immediately
    HALF_OPEN = "half_open"  # trial period — allow one call through to test recovery


@dataclass
class CircuitBreakerStats:
    state: CircuitState
    failure_count: int
    last_failure_time: float = 0.0


class CircuitOpenError(Exception):
    """Raised when a call is rejected because the breaker is open."""


class CircuitBreaker:
    """
    Wraps calls to a potentially-failing dependency. After
    `failure_threshold` consecutive failures, the breaker opens and
    rejects calls immediately (without even attempting them) for
    `reset_timeout_seconds` — protecting a struggling dependency from
    being hammered by retries while it recovers. After the timeout, one
    trial call is allowed through (half-open); success closes the
    breaker, failure re-opens it.
    """

    def __init__(self, failure_threshold: int = 5, reset_timeout_seconds: float = 30.0) -> None:
        self._failure_threshold = failure_threshold
        self._reset_timeout_seconds = reset_timeout_seconds
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0.0

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN and self._seconds_since_last_failure() >= self._reset_timeout_seconds:
            self._state = CircuitState.HALF_OPEN
        return self._state

    def stats(self) -> CircuitBreakerStats:
        return CircuitBreakerStats(
            state=self.state, failure_count=self._failure_count, last_failure_time=self._last_failure_time
        )

    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        current_state = self.state
        if current_state == CircuitState.OPEN:
            raise CircuitOpenError(
                f"Circuit is open ({self._failure_count} consecutive failures) — "
                f"rejecting call without attempting it."
            )

        try:
            result = func(*args, **kwargs)
        except Exception:
            self._record_failure()
            raise
        else:
            self._record_success()
            return result

    def _record_success(self) -> None:
        self._failure_count = 0
        self._state = CircuitState.CLOSED

    def _record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._failure_count >= self._failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning("circuit_breaker_opened", extra={"failure_count": self._failure_count})

    def _seconds_since_last_failure(self) -> float:
        return time.time() - self._last_failure_time
