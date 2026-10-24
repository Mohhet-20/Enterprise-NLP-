# Developer Guide

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install torch --index-url https://download.pytorch.org/whl/cpu   # CPU wheel, ~200MB
pip install -r requirements-ml.txt  # includes requirements.txt
cp .env.example .env
uvicorn backend.main:app --reload
```

Interactive API docs: http://localhost:8000/docs. The API runs with only
`requirements.txt` installed too; prediction endpoints then return a clear
`ModelLoadError` until the ML extras are installed.

## Tests

```bash
pytest                    # unit tests: in-memory SQLite, fake model, no network (~2 min)
pytest -m integration     # real Hugging Face checkpoints (~2.5GB download on first run)
ruff check backend tests scripts
cd frontend && npm test && npm run lint
```

An autouse fixture in `tests/conftest.py` replaces `ModelFactory.get_model` with a
deterministic keyword model, so unit tests never download weights. Mark a test
`@pytest.mark.integration` to opt it back into real models.

## Training and evaluation

```bash
python scripts/train_sentiment.py                     # fine-tune DistilBERT on SST-2
python scripts/evaluate_sentiment.py                  # baseline vs public vs ours -> reports/
python scripts/benchmark_inference.py                 # FP32 vs INT8 -> benchmarks/
python scripts/load_test.py --base-url http://127.0.0.1:8000
```

## Conventions

- **Type hints everywhere.**
- **No bare `except Exception` without re-raising as a `PlatformError` subclass.**
  This keeps the mapping in `backend/core/exception_handlers.py` exhaustive.
- **Services, not endpoints, contain logic.** An endpoint parses, calls one service
  method, and returns.
- **Settings live in `backend/config/settings.py`**, never hardcoded.
- **Heavy ML imports are lazy** (inside `load()` / `train()`), so importing the
  platform stays fast and works without the ML extras.
- **Logging uses the category-scoped loggers** (`get_logger("training")`,
  `get_logger("audit")`, …) from `backend/config/logging_config.py`.

## Adding an endpoint

1. Write the handler in `backend/api/v1/endpoints/<module>.py`.
2. Register its router in `backend/api/v1/router.py`.
3. Add request/response schemas in `backend/schemas/`.
4. Add a test in `tests/`.

See `docs/architecture-guide.md` for adding tasks and architectures.
