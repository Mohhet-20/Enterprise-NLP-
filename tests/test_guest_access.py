"""Public-demo controls: guest sessions, the registration switch, and serving a subset of tasks."""

import pytest

from backend.config.settings import get_settings
from backend.core.constants import NLPTask, UserRole
from backend.models.user import User
from backend.repositories.user_repository import UserRepository


@pytest.fixture
def demo_settings(monkeypatch):
    def apply(**env):
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        get_settings.cache_clear()

    yield apply
    get_settings.cache_clear()


def test_guest_access_is_off_by_default(client):
    assert client.post("/api/v1/auth/guest").status_code == 404


def test_guest_session_is_a_data_scientist_never_an_admin(client, demo_settings):
    demo_settings(GUEST_ACCESS_ENABLED="true", GUEST_USERNAME="guest-ds")
    res = client.post("/api/v1/auth/guest")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["user"]["username"] == "guest-ds" and body["user"]["role"] == UserRole.DATA_SCIENTIST.value
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200 and me.json()["role"] == UserRole.DATA_SCIENTIST.value
    # Reuses the same account on the next visit.
    again = client.post("/api/v1/auth/guest").json()
    assert again["user"]["id"] == body["user"]["id"]


def test_guest_cannot_read_the_audit_log(client, demo_settings):
    demo_settings(GUEST_ACCESS_ENABLED="true", GUEST_USERNAME="guest-audit")
    token = client.post("/api/v1/auth/guest").json()["access_token"]
    assert client.get("/api/v1/audit-logs", headers={"Authorization": f"Bearer {token}"}).status_code == 403


def test_an_admin_account_is_never_handed_out_as_the_guest(client, db_session, demo_settings):
    UserRepository(db_session).create(User(username="guest-admin", email="ga@example.com", hashed_password="x",
                                           role=UserRole.ADMIN.value))
    demo_settings(GUEST_ACCESS_ENABLED="true", GUEST_USERNAME="guest-admin")
    assert client.post("/api/v1/auth/guest").status_code == 403


def test_registration_can_be_turned_off(client, demo_settings):
    demo_settings(REGISTRATION_ENABLED="false")
    res = client.post("/api/v1/auth/register", json={"username": "newbie", "email": "n@example.com",
                                                     "password": "Sufficiently-Long-9"})
    assert res.status_code == 404


def test_served_tasks_limits_what_an_instance_serves(demo_settings):
    from backend.plugins.plugin_registry import _served

    assert _served(NLPTask.EMOTION_DETECTION)  # empty setting = everything
    demo_settings(SERVED_TASKS="sentiment_analysis, semantic_similarity")
    assert _served(NLPTask.SENTIMENT_ANALYSIS) and _served(NLPTask.SEMANTIC_SIMILARITY)
    assert not _served(NLPTask.EMOTION_DETECTION)


def test_tasks_endpoint_reports_tasks_not_served_here(client):
    body = client.get("/api/v1/tasks").json()
    assert "not_served" in body and isinstance(body["not_served"], list)


def test_sst2_validation_can_come_from_a_local_export(tmp_path, demo_settings):
    import json

    from backend.services.evaluation_service import _load_sst2_validation

    path = tmp_path / "sst2.json"
    path.write_text(json.dumps([{"sentence": "a gem", "label": "positive"}, {"sentence": "a mess", "label": "negative"}]))
    demo_settings(SST2_VALIDATION_FILE=str(path))
    rows = _load_sst2_validation()
    assert [(r.text, r.true_label) for r in rows] == [("a gem", "POSITIVE"), ("a mess", "NEGATIVE")]


def test_concurrent_loads_of_one_model_load_it_once():
    # A request arriving while the startup preload is still loading must wait for it, not load a second copy.
    import threading
    import time

    from backend.nlp.inference.base_model import BaseNLPModel

    calls = []

    class SlowModel(BaseNLPModel):
        supported_tasks = []

        def load(self) -> None:
            if self._is_loaded:
                return
            calls.append(1)
            time.sleep(0.2)
            self._is_loaded = True

        def predict(self, text, task, **kwargs):
            return []

    model = SlowModel("slow")
    threads = [threading.Thread(target=model.load) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert calls == [1] and model.is_loaded


def test_small_hosts_can_cap_served_evaluations_but_not_the_baseline(client, demo_settings):
    demo_settings(MAX_SERVED_EVAL_EXAMPLES="10")
    from backend.core.exceptions import ValidationError
    from backend.services.evaluation_service import evaluation_service

    with pytest.raises(ValidationError, match="at most 10 examples"):
        evaluation_service.run_evaluation(NLPTask.SENTIMENT_ANALYSIS, model="served", eval_set="challenge_set")
    run = evaluation_service.run_evaluation(NLPTask.SENTIMENT_ANALYSIS, model="lexicon_baseline", eval_set="challenge_set")
    assert run["accuracy"] > 0
