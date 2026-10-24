import uuid


def _unique_username(prefix: str = "user") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _register(client, password: str = "StrongPass123!"):
    username = _unique_username()
    email = f"{username}@example.com"
    response = client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email, "password": password},
    )
    return username, email, password, response


def _register_and_login(client, password: str = "StrongPass123!"):
    username, email, password, register_response = _register(client, password)
    login_response = client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )
    return username, password, login_response.json()


# --- Registration ---


def test_register_creates_read_only_user(client):
    username, email, password, response = _register(client)
    assert response.status_code == 201
    body = response.json()
    assert body["username"] == username
    assert body["email"] == email
    assert body["role"] == "read_only_user"
    assert body["is_active"] is True
    assert "hashed_password" not in body
    assert "password" not in body


def test_register_rejects_duplicate_username(client):
    username, email, password, _ = _register(client)
    response = client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": f"other_{username}@example.com", "password": password},
    )
    assert response.status_code == 409


def test_register_rejects_short_password(client):
    username = _unique_username()
    response = client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": f"{username}@example.com", "password": "short"},
    )
    assert response.status_code == 422


def test_register_rejects_invalid_email(client):
    username = _unique_username()
    response = client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": "not-an-email", "password": "StrongPass123!"},
    )
    assert response.status_code == 422


# --- Login ---


def test_login_wrong_password_fails(client):
    username, _, password, _ = _register(client)
    response = client.post(
        "/api/v1/auth/login", json={"username": username, "password": "WrongPassword1!"}
    )
    assert response.status_code == 401


def test_login_unknown_username_fails(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": _unique_username("ghost"), "password": "Whatever123!"},
    )
    assert response.status_code == 401


def test_login_success_returns_tokens_and_user(client):
    username, _, body = _register_and_login(client)
    assert body["user"]["username"] == username
    assert len(body["access_token"]) > 20
    assert len(body["refresh_token"]) > 20
    assert body["expires_in"] > 0


def test_account_locks_after_max_failed_attempts(client):
    username, _, password, _ = _register(client)
    for _ in range(5):
        response = client.post(
            "/api/v1/auth/login", json={"username": username, "password": "WrongPassword1!"}
        )
        assert response.status_code == 401

    # Even the correct password is rejected while locked.
    locked_response = client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )
    assert locked_response.status_code == 423


# --- /auth/me ---


def test_me_endpoint_returns_current_user(client):
    username, _, body = _register_and_login(client)
    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    )
    assert response.status_code == 200
    assert response.json()["username"] == username


# --- Refresh token rotation ---


def test_refresh_rotates_token_and_invalidates_old_one(client):
    _, _, login_body = _register_and_login(client)
    old_refresh = login_body["refresh_token"]

    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert refreshed.status_code == 200
    new_refresh = refreshed.json()["refresh_token"]
    assert new_refresh != old_refresh

    reuse_attempt = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert reuse_attempt.status_code == 401

    second_refresh = client.post("/api/v1/auth/refresh", json={"refresh_token": new_refresh})
    assert second_refresh.status_code == 200


def test_refresh_with_garbage_token_fails(client):
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": "not-a-real-token"})
    assert response.status_code == 401


# --- Logout / session revocation ---


def test_logout_revokes_refresh_token(client):
    _, _, login_body = _register_and_login(client)
    refresh_token = login_body["refresh_token"]

    logout_response = client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
    assert logout_response.status_code == 204

    reuse = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert reuse.status_code == 401


def test_logout_all_revokes_every_session(client):
    username, password, login1 = _register_and_login(client)
    login2 = client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    ).json()

    access_token = login1["access_token"]
    logout_all = client.post(
        "/api/v1/auth/logout-all", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert logout_all.status_code == 204

    for refresh_token in (login1["refresh_token"], login2["refresh_token"]):
        response = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert response.status_code == 401


def test_sessions_endpoint_lists_active_sessions(client):
    username, password, login1 = _register_and_login(client)
    client.post("/api/v1/auth/login", json={"username": username, "password": password})

    response = client.get(
        "/api/v1/auth/sessions",
        headers={"Authorization": f"Bearer {login1['access_token']}"},
    )
    assert response.status_code == 200
    assert len(response.json()) >= 2


# --- Integration with existing RBAC-protected endpoint ---


def test_predict_still_requires_auth(client):
    response = client.post(
        "/api/v1/predict", json={"task": "sentiment_analysis", "text": "hi"}
    )
    assert response.status_code == 401


def test_registered_user_can_call_predict(client):
    _, _, login_body = _register_and_login(client)
    response = client.post(
        "/api/v1/predict",
        headers={"Authorization": f"Bearer {login_body['access_token']}"},
        json={"task": "sentiment_analysis", "text": "Great news."},
    )
    assert response.status_code == 200
    assert response.json()["results"][0]["label"] == "POSITIVE"
