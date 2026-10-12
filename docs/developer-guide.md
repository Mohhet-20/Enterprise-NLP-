# Developer Guide

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn backend.main:app --reload
```

Interactive API docs: http://localhost:8000/docs

## Running tests

```bash
pytest
```

Tests use an in-memory SQLite database and override the `get_db_session`
dependency — no external services required.

## Conventions

- **Type hints everywhere.** Every function signature is typed; this is
  enforced by convention, not yet by a CI type-checker (add `mypy`/`pyright`
  when the codebase grows past the skeleton stage).
- **No bare `except Exception` without re-raising as a `PlatformError`
  subclass.** This keeps the exception-handler mapping in
  `backend/core/exception_handlers.py` exhaustive.
- **Services, not endpoints, contain logic.** An endpoint function should
  be parse -> call one service method -> return. If you're writing an `if`
  statement in an endpoint, it probably belongs in a service.
- **New settings go in `backend/config/settings.py`, never hardcoded.**
- **Logging uses the category-scoped loggers** (`get_logger("training")`,
  `get_logger("audit")`, etc.) defined in `backend/config/logging_config.py`
  so log routing/verbosity can be tuned per category later.

## Adding an endpoint

1. Write the handler in `backend/api/v1/endpoints/<module>.py`.
2. Register its router in `backend/api/v1/router.py`.
3. Add request/response schemas in `backend/schemas/`.
4. Add a test in `tests/`.

See `docs/architecture-guide.md` for extending the NLP subsystem
(new models, tasks, datasets).
