from backend.core.exceptions import (
    AuthenticationError,
    ModelNotFoundError,
    PlatformError,
    ValidationError,
)


def test_default_messages_and_status_codes():
    assert PlatformError().status_code == 500
    assert ValidationError().status_code == 422
    assert AuthenticationError().status_code == 401
    assert ModelNotFoundError().status_code == 404


def test_custom_message_and_details_are_preserved():
    exc = ValidationError("bad field", details={"field": "text"})
    assert exc.message == "bad field"
    assert exc.details == {"field": "text"}


def test_unauthenticated_predict_request_returns_401(client):
    response = client.post(
        "/api/v1/predict",
        json={"task": "sentiment_analysis", "text": "I love this."},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AuthenticationError"
