import os

os.environ["ENVIRONMENT"] = "testing"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database.base import Base
from backend.database.session import get_db_session
from backend.main import app

# StaticPool is required for `sqlite:///:memory:` — without it, every new
# connection SQLAlchemy opens gets its own separate, empty in-memory
# database, which surfaces as "no such table" errors the moment more than
# one connection is used (exactly what happens once a test does a real
# query through the ORM, e.g. anything touching auth/users).
_test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestSessionLocal = sessionmaker(bind=_test_engine, autoflush=False, autocommit=False)

# Background jobs (backend/services/background_jobs.py) deliberately open
# their own session via `from backend.database.session import SessionLocal`
# rather than using the `get_db_session` FastAPI dependency — they run
# outside the request lifecycle, so there's no dependency injection to
# hook into. `app.dependency_overrides` only affects the DI path, so
# without this, a background task in tests would silently query the real
# on-disk test database while the request that queued it used this
# in-memory one — two different databases, same test. Patching the
# module-level name directly closes that gap for every future background
# job, not just today's.
import backend.database.session as _db_session_module  # noqa: E402

_db_session_module.SessionLocal = _TestSessionLocal


def _override_get_db_session():
    session = _TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="session", autouse=True)
def _create_test_tables():
    import backend.models  # noqa: F401
    Base.metadata.create_all(bind=_test_engine)
    yield
    Base.metadata.drop_all(bind=_test_engine)


@pytest.fixture
def client() -> TestClient:
    app.dependency_overrides[get_db_session] = _override_get_db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def db_session():
    """Direct access to the same in-memory test database the app uses via
    the overridden dependency — for tests that need to inspect or set up
    state the public API doesn't expose a way to create (e.g. a user with
    a non-default role)."""
    session = _TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


# --- Model stubbing -------------------------------------------------------
#
# Unit tests must never download weights or depend on network access, so
# every test gets a deterministic fake behind ModelFactory.get_model by
# default. Tests marked `@pytest.mark.integration` opt out and exercise the
# real Hugging Face checkpoints (run with: pytest -m integration).

from backend.nlp.inference.base_model import BaseNLPModel, Prediction  # noqa: E402


class FakeKeywordModel(BaseNLPModel):
    """Labels text POSITIVE iff it contains 'good'/'great'/'love'. Simple
    enough that tests can assert exact outputs."""

    supported_tasks = []
    calls: list = []

    def load(self) -> None:
        self._is_loaded = True

    def predict(self, text, task, **kwargs):
        FakeKeywordModel.calls.append({"text": text, "task": task, **kwargs})
        candidates = kwargs.get("candidate_labels")
        if candidates:
            label = candidates[0]
            return [Prediction(label=label, score=0.8, raw_scores={c: 0.8 if c == label else 0.2 for c in candidates})]
        positive = any(w in text.lower() for w in ("good", "great", "love"))
        label = "POSITIVE" if positive else "NEGATIVE"
        score = 0.9 if positive else 0.7
        return [Prediction(label=label, score=score, raw_scores={label: score, "OTHER": round(1 - score, 6)})]

    def embed(self, texts):
        return [[float(len(t)), 1.0, 0.0] for t in texts]


@pytest.fixture(autouse=True)
def _stub_models(request, monkeypatch):
    if request.node.get_closest_marker("integration"):
        yield
        return
    from backend.nlp.inference.model_factory import model_factory

    fake = FakeKeywordModel("fake-model")
    FakeKeywordModel.calls = []
    monkeypatch.setattr(model_factory, "get_model", lambda *a, **k: fake)
    yield fake


def pytest_collection_modifyitems(config, items):
    if config.getoption("-m") and "integration" in config.getoption("-m"):
        return
    skip = pytest.mark.skip(reason="integration test: run with `pytest -m integration`")
    for item in items:
        if item.get_closest_marker("integration"):
            item.add_marker(skip)
