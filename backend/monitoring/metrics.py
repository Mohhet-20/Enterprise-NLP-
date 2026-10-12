"""
In-process metrics collection for model/inference monitoring: request
counts, latency, and error rates per (task, model). Exposed as a plain
dict today; swap `MetricsRegistry` internals for a `prometheus_client`
Counter/Histogram later — callers (services, middleware) don't change.
"""

import threading
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict


@dataclass
class InferenceStats:
    count: int = 0
    error_count: int = 0
    total_latency_ms: float = 0.0

    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / self.count if self.count else 0.0

    @property
    def error_rate(self) -> float:
        return self.error_count / self.count if self.count else 0.0


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._stats: Dict[str, InferenceStats] = defaultdict(InferenceStats)

    def _key(self, task: str, model_name: str) -> str:
        return f"{task}:{model_name}"

    def record_inference(self, task: str, model_name: str, latency_ms: float, success: bool) -> None:
        key = self._key(task, model_name)
        with self._lock:
            stats = self._stats[key]
            stats.count += 1
            stats.total_latency_ms += latency_ms
            if not success:
                stats.error_count += 1

    def snapshot(self) -> Dict[str, Dict[str, float]]:
        with self._lock:
            return {
                key: {
                    "count": s.count,
                    "error_rate": s.error_rate,
                    "avg_latency_ms": s.avg_latency_ms,
                }
                for key, s in self._stats.items()
            }


metrics_registry = MetricsRegistry()


class Timer:
    """`with Timer() as t: ...` then read `t.elapsed_ms`."""

    def __enter__(self) -> "Timer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, *exc_info) -> None:
        self.elapsed_ms = (time.perf_counter() - self._start) * 1000
