def test_health_check_returns_ok(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["environment"] == "testing"


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "docs" in response.json()


def test_liveness_always_returns_alive(client):
    response = client.get("/api/v1/liveness")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_readiness_reports_database_ok(client):
    response = client.get("/api/v1/readiness")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["database"]["status"] == "ok"
    assert "latency_ms" in body["database"]


def test_database_health_runs_a_real_query(client):
    response = client.get("/api/v1/database")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_model_health_reflects_real_plugin_registry(client):
    response = client.get("/api/v1/model")
    assert response.status_code == 200
    body = response.json()
    assert "sentiment_analysis" in body["registered_tasks"]
    assert "bert" in body["registered_architectures"]
    assert "distilbert" in body["registered_architectures"]


def test_embedding_health_is_honest_about_not_being_implemented(client):
    response = client.get("/api/v1/embedding")
    assert response.status_code == 200
    assert response.json()["status"] == "not_implemented"


def test_monitoring_health_reports_real_counts(client):
    # Generate at least one real prediction attempt so the counter is non-trivial.
    client.post(
        "/api/v1/auth/register",
        json={"username": "healthcheckuser", "email": "healthcheckuser@example.com", "password": "StrongPass123!"},
    )
    token = client.post(
        "/api/v1/auth/login", json={"username": "healthcheckuser", "password": "StrongPass123!"}
    ).json()["access_token"]
    client.post(
        "/api/v1/predict",
        headers={"Authorization": f"Bearer {token}"},
        json={"task": "sentiment_analysis", "text": "test"},
    )

    response = client.get("/api/v1/monitoring-health")
    assert response.status_code == 200
    assert response.json()["total_predictions_recorded"] >= 1


def test_system_health_returns_real_resource_percentages(client):
    response = client.get("/api/v1/system")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert 0 <= body["cpu_percent"] <= 100
    assert 0 <= body["memory_percent"] <= 100


def test_version_endpoint_reports_app_metadata(client):
    response = client.get("/api/v1/version")
    assert response.status_code == 200
    body = response.json()
    assert body["app_name"] == "Enterprise NLP Intelligence Platform"
    assert "python_version" in body
    assert "git_commit" in body


def test_overall_status_aggregates_all_subsystems(client):
    response = client.get("/api/v1/status")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert set(body["checks"].keys()) == {"database", "model_registry", "embedding", "monitoring", "cache", "system"}
