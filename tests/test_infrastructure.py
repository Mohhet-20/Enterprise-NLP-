import csv
import io
import time
import uuid

import pytest

from backend.core.cache import CacheService
from backend.core.resilience import CircuitBreaker, CircuitOpenError, CircuitState, retry
from backend.config.settings import get_settings
from backend.repositories.user_repository import UserRepository


# --- Cache ---


def test_cache_set_and_get_json_round_trip():
    cache = CacheService()
    cache.set_json("test:key1", {"a": 1, "b": [1, 2, 3]}, ttl_seconds=30)
    assert cache.get_json("test:key1") == {"a": 1, "b": [1, 2, 3]}


def test_cache_get_missing_key_returns_none():
    cache = CacheService()
    assert cache.get_json("test:does-not-exist") is None


def test_cache_delete_removes_key():
    cache = CacheService()
    cache.set_json("test:key2", {"x": 1}, ttl_seconds=30)
    cache.delete("test:key2")
    assert cache.get_json("test:key2") is None


def test_cache_increment_counts_up():
    cache = CacheService()
    key = f"test:counter:{uuid.uuid4().hex}"
    assert cache.increment(key, ttl_seconds=60) == 1
    assert cache.increment(key, ttl_seconds=60) == 2
    assert cache.increment(key, ttl_seconds=60) == 3


def test_cache_backend_name_is_redis_or_in_memory():
    cache = CacheService()
    # Whichever backend is actually reachable in this environment — both
    # are legitimate, tested code paths (see backend/core/cache.py).
    assert cache.backend_name in ("redis", "in_memory")


# --- Retry ---


def test_retry_succeeds_after_transient_failures():
    attempts = {"count": 0}

    @retry(max_attempts=3, initial_delay_seconds=0.01, exceptions=(ValueError,))
    def flaky():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise ValueError("not yet")
        return "success"

    assert flaky() == "success"
    assert attempts["count"] == 3


def test_retry_raises_after_exhausting_attempts():
    @retry(max_attempts=2, initial_delay_seconds=0.01, exceptions=(ValueError,))
    def always_fails():
        raise ValueError("nope")

    with pytest.raises(ValueError):
        always_fails()


def test_retry_does_not_catch_unlisted_exceptions():
    @retry(max_attempts=3, initial_delay_seconds=0.01, exceptions=(ValueError,))
    def wrong_error():
        raise TypeError("not a ValueError")

    with pytest.raises(TypeError):
        wrong_error()


# --- Circuit breaker ---


def test_circuit_breaker_opens_after_threshold_failures():
    breaker = CircuitBreaker(failure_threshold=3, reset_timeout_seconds=60)

    def failing():
        raise RuntimeError("boom")

    for _ in range(3):
        with pytest.raises(RuntimeError):
            breaker.call(failing)

    assert breaker.state == CircuitState.OPEN
    with pytest.raises(CircuitOpenError):
        breaker.call(failing)


def test_circuit_breaker_closes_on_success():
    breaker = CircuitBreaker(failure_threshold=2, reset_timeout_seconds=60)

    def failing():
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        breaker.call(failing)
    assert breaker.state == CircuitState.CLOSED  # only 1 failure, threshold is 2

    breaker.call(lambda: "ok")
    assert breaker.state == CircuitState.CLOSED
    assert breaker.stats().failure_count == 0


def test_circuit_breaker_half_opens_after_timeout():
    breaker = CircuitBreaker(failure_threshold=1, reset_timeout_seconds=0.05)

    with pytest.raises(RuntimeError):
        breaker.call(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    assert breaker.state == CircuitState.OPEN

    time.sleep(0.1)
    assert breaker.state == CircuitState.HALF_OPEN


# --- Rate limiting (integration) ---


def _rate_limit_test_user(client):
    username = f"ratelimituser_{uuid.uuid4().hex[:10]}"
    email = f"{username}@example.com"
    password = "StrongPass123!"
    client.post("/api/v1/auth/register", json={"username": username, "email": email, "password": password})
    token = client.post("/api/v1/auth/login", json={"username": username, "password": password}).json()["access_token"]
    return username, token


def test_rate_limit_returns_429_when_exceeded(client, db_session):
    # Authenticated identity (unique per test, via a fresh user) rather
    # than IP — TestClient always reports the same fake host, so an
    # IP-keyed counter would accumulate across every other test sharing
    # this session's cache_service singleton.
    username, token = _rate_limit_test_user(client)
    headers = {"Authorization": f"Bearer {token}"}

    settings = get_settings()
    original_limit = settings.rate_limit_requests_per_minute
    settings.rate_limit_requests_per_minute = 3
    try:
        responses = [client.get("/api/v1/auth/me", headers=headers) for _ in range(4)]
        statuses = [r.status_code for r in responses]
        assert statuses[:3] == [200, 200, 200]
        assert statuses[3] == 429
        assert responses[3].json()["error"]["code"] == "RateLimitExceededError"
        assert "Retry-After" in responses[3].headers
    finally:
        settings.rate_limit_requests_per_minute = original_limit


def test_rate_limit_exempts_health_endpoints(client, db_session):
    username, token = _rate_limit_test_user(client)
    headers = {"Authorization": f"Bearer {token}"}

    settings = get_settings()
    original_limit = settings.rate_limit_requests_per_minute
    settings.rate_limit_requests_per_minute = 2
    try:
        # Far more than the limit — should never 429 because health
        # endpoints are exempt from rate limiting entirely.
        responses = [client.get("/api/v1/liveness", headers=headers) for _ in range(10)]
        assert all(r.status_code == 200 for r in responses)
    finally:
        settings.rate_limit_requests_per_minute = original_limit


def test_cache_health_endpoint(client):
    response = client.get("/api/v1/cache")
    assert response.status_code == 200
    assert response.json()["backend"] in ("redis", "in_memory")


# --- Audit trail ---


def _unique_username(prefix: str = "audituser") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _promote_role(db_session, username: str, role: str) -> None:
    user = UserRepository(db_session).find_by_username(username)
    user.role = role
    db_session.commit()


def test_login_writes_an_audit_log_entry(client, db_session):
    username = _unique_username()
    email = f"{username}@example.com"
    password = "StrongPass123!"
    client.post("/api/v1/auth/register", json={"username": username, "email": email, "password": password})
    client.post("/api/v1/auth/login", json={"username": username, "password": password})

    _promote_role(db_session, username, "auditor")
    token = client.post("/api/v1/auth/login", json={"username": username, "password": password}).json()["access_token"]

    logs = client.get(
        "/api/v1/audit-logs", headers={"Authorization": f"Bearer {token}"}, params={"action": "user.login_success"}
    )
    assert logs.status_code == 200
    matching = [entry for entry in logs.json() if entry["actor_username"] == username]
    assert len(matching) >= 1


def test_failed_login_writes_an_audit_log_entry(client, db_session):
    username = _unique_username()
    email = f"{username}@example.com"
    password = "StrongPass123!"
    client.post("/api/v1/auth/register", json={"username": username, "email": email, "password": password})
    client.post("/api/v1/auth/login", json={"username": username, "password": "WrongPassword1!"})

    _promote_role(db_session, username, "auditor")
    token = client.post("/api/v1/auth/login", json={"username": username, "password": password}).json()["access_token"]

    logs = client.get(
        "/api/v1/audit-logs", headers={"Authorization": f"Bearer {token}"}, params={"action": "user.login_failed"}
    )
    assert logs.status_code == 200
    matching = [entry for entry in logs.json() if entry["actor_username"] == username]
    assert len(matching) >= 1


def test_non_auditor_cannot_read_audit_logs(client, db_session):
    username = _unique_username()
    email = f"{username}@example.com"
    password = "StrongPass123!"
    client.post("/api/v1/auth/register", json={"username": username, "email": email, "password": password})
    token = client.post("/api/v1/auth/login", json={"username": username, "password": password}).json()["access_token"]

    response = client.get("/api/v1/audit-logs", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_model_approval_writes_an_audit_log_entry(client, db_session):
    engineer_username = _unique_username("mreng")
    email = f"{engineer_username}@example.com"
    password = "StrongPass123!"
    client.post("/api/v1/auth/register", json={"username": engineer_username, "email": email, "password": password})
    engineer_token = client.post(
        "/api/v1/auth/login", json={"username": engineer_username, "password": password}
    ).json()["access_token"]
    _promote_role(db_session, engineer_username, "ml_engineer")

    entry = client.post(
        "/api/v1/models",
        headers={"Authorization": f"Bearer {engineer_token}"},
        json={
            "name": "audit-test-model",
            "task": "sentiment_analysis",
            "architecture": "custom",
            "version": "1.0.0",
            "model_name_or_path": "lexicon-baseline-v1",
        },
    ).json()

    reviewer_username = _unique_username("reviewer")
    client.post(
        "/api/v1/auth/register",
        json={"username": reviewer_username, "email": f"{reviewer_username}@example.com", "password": password},
    )
    reviewer_token = client.post(
        "/api/v1/auth/login", json={"username": reviewer_username, "password": password}
    ).json()["access_token"]
    _promote_role(db_session, reviewer_username, "reviewer")
    client.post(f"/api/v1/models/{entry['id']}/approve", headers={"Authorization": f"Bearer {reviewer_token}"})

    _promote_role(db_session, reviewer_username, "auditor")
    auditor_token = client.post(
        "/api/v1/auth/login", json={"username": reviewer_username, "password": password}
    ).json()["access_token"]
    logs = client.get(
        "/api/v1/audit-logs",
        headers={"Authorization": f"Bearer {auditor_token}"},
        params={"resource_id": entry["id"], "action": "model.approved"},
    )
    assert logs.status_code == 200
    assert len(logs.json()) == 1


# --- Background task: automatic embedding rebuild after upload ---


def _ml_engineer_headers(client, db_session):
    username = _unique_username("bgjob")
    email = f"{username}@example.com"
    password = "StrongPass123!"
    client.post("/api/v1/auth/register", json={"username": username, "email": email, "password": password})
    token = client.post("/api/v1/auth/login", json={"username": username, "password": password}).json()["access_token"]
    _promote_role(db_session, username, "ml_engineer")
    return {"Authorization": f"Bearer {token}"}


def test_upload_automatically_rebuilds_embedding_index_in_background(client, db_session):
    headers = _ml_engineer_headers(client, db_session)
    dataset_id = client.post(
        "/api/v1/datasets", headers=headers, json={"name": _unique_username("ds"), "task": "sentiment_analysis"}
    ).json()["id"]

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=["text", "label"])
    writer.writeheader()
    writer.writerow({"text": "The battery life is fantastic", "label": "POSITIVE"})
    writer.writerow({"text": "Battery performance is excellent", "label": "POSITIVE"})
    csv_bytes = buffer.getvalue().encode("utf-8")

    upload = client.post(
        f"/api/v1/datasets/{dataset_id}/upload", headers=headers, files={"file": ("r.csv", csv_bytes, "text/csv")}
    )
    assert upload.status_code == 200

    # No explicit POST .../embeddings/build call — TestClient runs
    # BackgroundTasks to completion before returning control, so the
    # index should already exist.
    search = client.get(
        f"/api/v1/datasets/{dataset_id}/embeddings/search",
        headers=headers,
        params={"query": "battery", "top_k": 2},
    )
    assert search.status_code == 200
    assert len(search.json()) == 2
