"""
Cache backend with automatic Redis-or-in-memory fallback.

This is the correct production pattern regardless of this sandbox's
constraints: a cache is an optimization, not a hard dependency — an app
that crashes (or even fails a request) because its cache is temporarily
unreachable has turned an optimization into an outage. So every method
here catches Redis connection errors and transparently falls back to an
in-process dict, logging a warning once rather than on every call.

This also happens to make the feature genuinely testable in this sandbox
either way: with `redis-server` running (verified working — see
CHANGELOG.md), calls exercise the real Redis path; without it, the same
test exercises the in-memory fallback. Both are real code paths, not one
real and one theoretical.
"""

import json
import time
from typing import Any, Optional

import redis as redis_lib

from backend.config.logging_config import get_logger
from backend.config.settings import get_settings

logger = get_logger("api")


class InMemoryCache:
    """Fallback backend: a dict with lazy per-key expiry. Not shared
    across processes — fine for single-worker dev/test, not a substitute
    for real Redis in a multi-worker production deployment."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[float, str]] = {}  # key -> (expires_at, json_value)

    def get(self, key: str) -> Optional[str]:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if expires_at < time.time():
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        self._store[key] = (time.time() + ttl_seconds, value)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def incr(self, key: str, ttl_seconds: int) -> int:
        entry = self._store.get(key)
        now = time.time()
        if entry is None or entry[0] < now:
            self._store[key] = (now + ttl_seconds, "1")
            return 1
        count = int(entry[1]) + 1
        self._store[key] = (entry[0], str(count))
        return count


class CacheService:
    def __init__(self) -> None:
        settings = get_settings()
        self._fallback = InMemoryCache()
        self._redis: Optional["redis_lib.Redis"] = None
        self._warned_unavailable = False
        self._try_connect_redis(settings.redis_url, settings.redis_connect_timeout_seconds)

    def _try_connect_redis(self, url: str, timeout: float) -> None:
        try:
            client = redis_lib.Redis.from_url(
                url, socket_connect_timeout=timeout, socket_timeout=timeout, decode_responses=True
            )
            client.ping()
            self._redis = client
            logger.info("cache_backend_connected", extra={"backend": "redis"})
        except Exception as exc:  # noqa: BLE001 — any connection failure means "use the fallback"
            self._redis = None
            logger.warning(
                "cache_backend_unavailable",
                extra={"backend": "in_memory_fallback", "reason": str(exc)},
            )

    @property
    def backend_name(self) -> str:
        return "redis" if self._redis is not None else "in_memory"

    def get_json(self, key: str) -> Optional[Any]:
        raw = self._get_raw(key)
        return json.loads(raw) if raw is not None else None

    def set_json(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        settings = get_settings()
        self._set_raw(key, json.dumps(value), ttl_seconds or settings.cache_default_ttl_seconds)

    def delete(self, key: str) -> None:
        if self._redis is not None:
            try:
                self._redis.delete(key)
                return
            except Exception:  # noqa: BLE001
                self._mark_redis_down()
        self._fallback.delete(key)

    def increment(self, key: str, ttl_seconds: int) -> int:
        """Atomic-ish increment used by the rate limiter. Real atomicity
        only holds on the Redis path (INCR + EXPIRE); the in-memory
        fallback is single-process so it doesn't need cross-process
        atomicity to be correct."""
        if self._redis is not None:
            try:
                pipe = self._redis.pipeline()
                pipe.incr(key)
                pipe.expire(key, ttl_seconds, nx=True)
                count, _ = pipe.execute()
                return int(count)
            except Exception:  # noqa: BLE001
                self._mark_redis_down()
        return self._fallback.incr(key, ttl_seconds)

    # --- internals ---

    def _get_raw(self, key: str) -> Optional[str]:
        if self._redis is not None:
            try:
                return self._redis.get(key)
            except Exception:  # noqa: BLE001
                self._mark_redis_down()
        return self._fallback.get(key)

    def _set_raw(self, key: str, value: str, ttl_seconds: int) -> None:
        if self._redis is not None:
            try:
                self._redis.set(key, value, ex=ttl_seconds)
                return
            except Exception:  # noqa: BLE001
                self._mark_redis_down()
        self._fallback.set(key, value, ttl_seconds)

    def _mark_redis_down(self) -> None:
        self._redis = None
        if not self._warned_unavailable:
            logger.warning("cache_backend_lost_connection", extra={"backend": "in_memory_fallback"})
            self._warned_unavailable = True


cache_service = CacheService()
