import uuid

from backend.repositories.user_repository import UserRepository


def _unique_username(prefix: str = "reguser") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _register_and_login(client, password: str = "StrongPass123!"):
    username = _unique_username()
    email = f"{username}@example.com"
    client.post("/api/v1/auth/register", json={"username": username, "email": email, "password": password})
    login = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    return username, login.json()["access_token"]


def _promote_role(db_session, username: str, role: str) -> None:
    user = UserRepository(db_session).find_by_username(username)
    user.role = role
    db_session.commit()


def _register_model(client, headers, name=None, task="sentiment_analysis"):
    payload = {
        "name": name or f"model-{uuid.uuid4().hex[:8]}",
        "task": task,
        "architecture": "distilbert",
        "version": "1.0.0",
        "model_name_or_path": "lexicon-baseline-v1",
    }
    return client.post("/api/v1/models", headers=headers, json=payload)


def _ml_engineer_headers(client, db_session):
    username, token = _register_and_login(client)
    _promote_role(db_session, username, "ml_engineer")
    return {"Authorization": f"Bearer {token}"}


def _reviewer_headers(client, db_session):
    username, token = _register_and_login(client)
    _promote_role(db_session, username, "reviewer")
    return {"Authorization": f"Bearer {token}"}


# --- Registration & listing ---


def test_register_model_requires_experiment_write(client):
    _, token = _register_and_login(client)  # default read_only_user
    response = _register_model(client, {"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_register_model_starts_in_development_pending_not_deployed(client, db_session):
    headers = _ml_engineer_headers(client, db_session)
    response = _register_model(client, headers)
    assert response.status_code == 201
    body = response.json()
    assert body["stage"] == "development"
    assert body["approval_status"] == "pending"
    assert body["deployment_status"] == "not_deployed"
    assert body["is_champion"] is False


def test_list_models_filters_by_task(client, db_session):
    headers = _ml_engineer_headers(client, db_session)
    _register_model(client, headers, task="sentiment_analysis")
    _register_model(client, headers, task="toxicity_detection")

    response = client.get("/api/v1/models?task=toxicity_detection", headers=headers)
    assert response.status_code == 200
    tasks = {m["task"] for m in response.json()}
    assert tasks == {"toxicity_detection"}


# --- Approval workflow / separation of duties ---


def test_ml_engineer_cannot_approve_models(client, db_session):
    headers = _ml_engineer_headers(client, db_session)
    entry = _register_model(client, headers).json()

    response = client.post(f"/api/v1/models/{entry['id']}/approve", headers=headers)
    assert response.status_code == 403


def test_reviewer_can_approve_a_model(client, db_session):
    engineer_headers = _ml_engineer_headers(client, db_session)
    entry = _register_model(client, engineer_headers).json()

    reviewer_headers = _reviewer_headers(client, db_session)
    response = client.post(f"/api/v1/models/{entry['id']}/approve", headers=reviewer_headers)
    assert response.status_code == 200
    assert response.json()["approval_status"] == "approved"


def test_reviewer_can_reject_with_a_reason(client, db_session):
    engineer_headers = _ml_engineer_headers(client, db_session)
    entry = _register_model(client, engineer_headers).json()

    reviewer_headers = _reviewer_headers(client, db_session)
    response = client.post(
        f"/api/v1/models/{entry['id']}/reject",
        headers=reviewer_headers,
        json={"reason": "Accuracy below the threshold for this task."},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["approval_status"] == "rejected"
    assert "Accuracy below the threshold" in body["notes"]


# --- Promotion gating ---


def test_cannot_promote_to_production_without_approval(client, db_session):
    headers = _ml_engineer_headers(client, db_session)
    entry = _register_model(client, headers).json()

    response = client.post(
        f"/api/v1/models/{entry['id']}/promote", headers=headers, json={"stage": "production"}
    )
    assert response.status_code == 409


def test_can_promote_to_staging_without_approval(client, db_session):
    headers = _ml_engineer_headers(client, db_session)
    entry = _register_model(client, headers).json()

    response = client.post(
        f"/api/v1/models/{entry['id']}/promote", headers=headers, json={"stage": "staging"}
    )
    assert response.status_code == 200
    assert response.json()["stage"] == "staging"


def test_can_promote_to_production_once_approved(client, db_session):
    engineer_headers = _ml_engineer_headers(client, db_session)
    entry = _register_model(client, engineer_headers).json()

    reviewer_headers = _reviewer_headers(client, db_session)
    client.post(f"/api/v1/models/{entry['id']}/approve", headers=reviewer_headers)

    response = client.post(
        f"/api/v1/models/{entry['id']}/promote", headers=engineer_headers, json={"stage": "production"}
    )
    assert response.status_code == 200
    assert response.json()["stage"] == "production"


# --- Deployment gating + rollback ---


def _approve_and_promote_to_production(client, engineer_headers, reviewer_headers, entry_id):
    client.post(f"/api/v1/models/{entry_id}/approve", headers=reviewer_headers)
    client.post(f"/api/v1/models/{entry_id}/promote", headers=engineer_headers, json={"stage": "production"})


def test_cannot_deploy_without_approval_and_production_stage(client, db_session):
    headers = _ml_engineer_headers(client, db_session)
    entry = _register_model(client, headers).json()

    response = client.post(f"/api/v1/models/{entry['id']}/deploy", headers=headers)
    assert response.status_code == 409


def test_deploying_a_model_rolls_back_the_previous_deployment_for_the_same_task(client, db_session):
    engineer_headers = _ml_engineer_headers(client, db_session)
    reviewer_headers = _reviewer_headers(client, db_session)

    model_a = _register_model(client, engineer_headers, name="model-a", task="sentiment_analysis").json()
    model_b = _register_model(client, engineer_headers, name="model-b", task="sentiment_analysis").json()

    _approve_and_promote_to_production(client, engineer_headers, reviewer_headers, model_a["id"])
    _approve_and_promote_to_production(client, engineer_headers, reviewer_headers, model_b["id"])

    deploy_a = client.post(f"/api/v1/models/{model_a['id']}/deploy", headers=engineer_headers)
    assert deploy_a.json()["deployment_status"] == "deployed"

    deploy_b = client.post(f"/api/v1/models/{model_b['id']}/deploy", headers=engineer_headers)
    assert deploy_b.json()["deployment_status"] == "deployed"

    # model_a should have been automatically rolled back by deploying model_b
    model_a_after = client.get(f"/api/v1/models/{model_a['id']}", headers=engineer_headers).json()
    assert model_a_after["deployment_status"] == "rolled_back"


# --- Champion/challenger uniqueness ---


def test_setting_a_new_champion_demotes_the_previous_one(client, db_session):
    engineer_headers = _ml_engineer_headers(client, db_session)

    model_a = _register_model(client, engineer_headers, name="champion-a", task="sentiment_analysis").json()
    model_b = _register_model(client, engineer_headers, name="champion-b", task="sentiment_analysis").json()

    client.post(f"/api/v1/models/{model_a['id']}/set-champion", headers=engineer_headers)
    response_b = client.post(f"/api/v1/models/{model_b['id']}/set-champion", headers=engineer_headers)
    assert response_b.json()["is_champion"] is True

    model_a_after = client.get(f"/api/v1/models/{model_a['id']}", headers=engineer_headers).json()
    assert model_a_after["is_champion"] is False


# --- Compare ---


def test_compare_two_models_returns_metric_deltas(client, db_session):
    headers = _ml_engineer_headers(client, db_session)
    model_a = _register_model(client, headers, name="cmp-a").json()
    model_b = _register_model(client, headers, name="cmp-b").json()

    response = client.get(f"/api/v1/models/compare/{model_a['id']}/{model_b['id']}", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["model_a"]["id"] == model_a["id"]
    assert body["model_b"]["id"] == model_b["id"]
