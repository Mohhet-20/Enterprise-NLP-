# Architecture Guide

## Layers (top to bottom)

```
API layer          backend/api/            HTTP concerns only: parse request, call service, return response
Service layer       backend/services/       Business logic/orchestration
NLP subsystem       backend/nlp/            Model strategies, tokenization, embeddings, training
Repository layer    backend/repositories/   Data access, hides SQLAlchemy from services
Database layer      backend/database/       Engine/session/ORM base
Core                backend/core/           Exceptions, DI container, middleware, constants
Config              backend/config/         Typed settings, logging setup
```

Dependencies only point downward (API -> Service -> Repository/NLP -> Database/Core).
Nothing in `core/` or `config/` imports from any layer above it.

## Design patterns and where they live

- **Strategy** — `backend/nlp/inference/base_model.py` (`BaseNLPModel`). Every
  transformer architecture is an interchangeable strategy.
- **Factory** — `backend/nlp/inference/model_factory.py`. Turns
  `(architecture, model_name)` into a concrete strategy instance, with caching.
- **Repository** — `backend/repositories/base_repository.py`. Generic CRUD
  over any SQLAlchemy model; concrete repos (e.g. `ExperimentRepository`) add
  domain-specific queries.
- **Service layer** — `backend/services/`. Endpoints call services; services
  call repositories + the NLP subsystem. Endpoints never touch SQLAlchemy or
  model classes directly.
- **Adapter** — `backend/nlp/tokenization/tokenizer_factory.py`. Wraps the
  third-party `transformers` tokenizer API behind a platform-owned interface.
- **Plugin registry** — `backend/plugins/`. Declarative task registration
  (default model, evaluator, explainer) so new NLP tasks don't require
  editing the API or service layer.
- **Dependency injection** — FastAPI's `Depends` for request-scoped
  dependencies (DB session, current user); `backend/core/container.py` for
  service/repository wiring that isn't naturally request-scoped.

## Extending the platform

### Add a new NLP task (e.g. "emotion_detection")
1. Confirm the task exists in `NLPTask` (`backend/core/constants.py`) — most
   are already declared.
2. Register a `TaskPlugin` in `backend/plugins/__init__.py` pointing at a
   default architecture/model.
3. If the task needs a new API shape, add an endpoint in
   `backend/api/v1/endpoints/`; otherwise the generic `/predict` endpoint
   already routes any registered task through `InferenceService`.

### Add a new transformer architecture (e.g. RoBERTa)
1. Create `backend/nlp/inference/models/roberta_model.py` implementing
   `BaseNLPModel` (or subclass `BertModel` if the HF API shape matches).
2. Add one line to `_ARCHITECTURE_REGISTRY` in `model_factory.py`.

### Add a new dataset
1. Implement `BaseDataset` (`backend/datasets/base_dataset.py`).
2. Decorate the class with `@register_dataset("your_dataset_name")`.

### Add a new persisted domain object (e.g. `TrainingRun`)
1. Add an ORM model in `backend/models/`, subclassing `Base`.
2. Add a repository in `backend/repositories/`, subclassing `BaseRepository`.
3. Add/extend a service in `backend/services/` to use it.

## What's NOT built yet (by design, this stage)

- Real trained model checkpoints / training loops (`BaseTrainer` has one
  interface, no concrete implementation)
- A production database (SQLite dev default; swap `DATABASE_URL`)
- MFA, email verification, and password reset (real auth — registration,
  login, refresh-token rotation, account lockout, 9-role RBAC — is now
  implemented; these three were explicitly out of scope for that pass)
- Most of the frontend (app shell + Inference Playground + auth pages are
  built; the analytics/model/dataset/monitoring/admin dashboards are not)
- Real explainability implementations (SHAP/Captum) — interface only
