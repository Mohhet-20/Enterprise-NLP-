"""
Loading weights from the Hugging Face Hub with retry.

The first request for a model downloads it, which makes the Hub the one
flaky external dependency on the request path. Transient network failures
(connection resets, timeouts) are retried with exponential backoff;
anything else (a wrong repo id, a missing file) fails immediately, since
retrying can't fix it.
"""

from typing import Callable, TypeVar

from backend.core.resilience import retry

T = TypeVar("T")


def _transient_errors() -> tuple:
    errors: list = [ConnectionError, TimeoutError]
    try:
        import requests

        errors += [requests.exceptions.ConnectionError, requests.exceptions.Timeout]
    except ImportError:  # requests ships with transformers; absent only without ML extras
        pass
    return tuple(errors)


def load_with_retry(loader: Callable[[], T], attempts: int = 3) -> T:
    return retry(max_attempts=attempts, initial_delay_seconds=1.0, exceptions=_transient_errors())(loader)()
