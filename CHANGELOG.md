# Changelog

Follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
[Semantic Versioning](https://semver.org/).

## [1.0.0] — 2026-10-24

### Added
- **Transformer serving for 8 tasks**: sentiment, emotion, toxicity (multi-label),
  topic (multi-label), language ID, zero-shot (NLI), semantic similarity and text
  embeddings. One generic Hugging Face classifier strategy covers BERT, DistilBERT,
  RoBERTa, DeBERTa and XLM-R; zero-shot and sentence-transformers have their own.
- **Fine-tuning pipeline**: `HFSequenceClassificationTrainer` + `scripts/train_sentiment.py`
  fine-tune DistilBERT on SST-2 and write a checkpoint with metrics, config and a model
  card. The sentiment task serves the local checkpoint when present.
- **Explainability**: `POST /explain` runs Integrated Gradients over input embeddings,
  with word-level merging and a reported completeness gap. The Playground renders the
  result as a heatmap.
- `POST /predict/batch` (padded batching, up to 64 texts) and `POST /embed`.
- **Evaluation** of the served model *or* the lexicon baseline on the challenge set,
  SST-2 validation, or any uploaded dataset (zero-shot uses the dataset's label set).
- **Semantic dataset search** with MiniLM embeddings; TF-IDF kept as a no-download
  encoder.
- `ModelFactory` LRU cap on resident models (`MAX_LOADED_MODELS`).
- Retry with backoff on Hugging Face Hub downloads.
- `scripts/evaluate_sentiment.py` and `scripts/benchmark_inference.py` (FP32 vs dynamic
  INT8) produce the README's results tables.
- GitHub Actions: lint, unit tests, real-model integration tests, pip-audit, frontend
  checks, Docker builds; tag-triggered releases.
- Opt-in integration suite (`pytest -m integration`) against every real checkpoint.
- Playground batch tab, zero-shot label input, similarity pair input, per-task examples.
- `docs/model-cards.md`, with measured failure modes (toxicity identity-term bias,
  language ID on one-word inputs).
- `scripts/seed_demo.py` and `scripts/capture_screenshots.py` (Playwright).

### Changed
- `NLPTask` lists only tasks that are actually served (removed hate speech, fake news,
  intent and generic multi-label, which had no model behind them).
- Unit tests run against a deterministic fake model, so they never touch the network.
- JWT library: python-jose → PyJWT; decoding now requires `exp` and `sub`.
- FastAPI 0.115 → 0.162, Starlette 0.46 → 1.9, python-multipart → 0.0.32.
- React Router 6 → 7, Vite 5 → 8, Vitest 2 → 5 (frontend build 15s → 2.5s).
- Removed the non-functional workspace selector from the top nav.
- Docker image ships CPU PyTorch, honours `$PORT`, runs one worker by default;
  Kubernetes memory sized for resident models.

### Fixed
- **The app shell crashed for every signed-in user**: a Tooltip in the top nav was rendered
  outside any `TooltipProvider`. Found by driving the UI with Playwright.
- **Calibration buckets were mislabelled** and most samples went uncounted (sklearn's
  `calibration_curve` drops empty bins, but its output was zipped onto every bin edge).
  Every evaluation now also reports ECE.
- **`/predict` spent ~150 ms per request in `gc.collect()`**, called on every model lookup.
  p50 went from 165 ms to 17.8 ms; found by load testing.
- Reported latency included first-use model loading.
- Zero-shot scored label hypotheses one forward pass at a time (now batched, 3.9× faster).
- `.env.example` CORS origins didn't include the Vite dev server.
- Evaluation run ids are validated as UUIDs before they touch the filesystem
  (path traversal via `..\` on Windows).
- Evaluation history was sorted by UUID instead of by time.
- Local checkpoint paths no longer leak into API responses.
- Kubernetes backend limit (512Mi) would OOM-kill the pod on first model load.

### Security
- Backend `pip-audit`: 18 → 0 known vulnerabilities. Frontend production dependencies:
  2 → 0.

## [0.9.0] — Product pages
- Dashboard, Datasets, Model Registry and Evaluations pages replace placeholders; every
  number comes from a live API call.

## [0.8.0] — Security & QA hardening
- Security headers, request-size limits, CSV formula-injection protection,
  common-password denylist, stricter auth rate limit.
- Frontend test suite (Vitest + Testing Library); ruff and eslint made blocking.
- Load-test script (`scripts/load_test.py`).

## [0.7.0] — Infrastructure
- Redis-backed cache and rate limiting with automatic in-memory fallback.
- Persisted audit trail; retry and circuit-breaker primitives.
- Dockerfiles, Compose profiles, Kubernetes manifests.

## [0.6.0] — Data platform
- Dataset upload, cleaning, validation, profiling, versioning, archive/restore,
  comparison, EDA augmentation; per-dataset TF-IDF search index.

## [0.5.0] — Observability & Model Registry
- 10-endpoint health suite.
- Model Registry with approval (separation of duties), promotion, deploy-with-rollback,
  and champion/challenger rules.

## [0.4.0] — Evaluation center
- scikit-learn metrics (accuracy, F1, ROC-AUC, confusion matrix, calibration), error
  analysis (confidence errors, hard examples, length slices), lexicon baseline,
  Markdown/CSV export.

## [0.3.0] — Authentication
- Persisted users with bcrypt, rotating hashed refresh tokens, account lockout,
  session management, 9-role RBAC.

## [0.2.0] — Frontend shell
- App shell (sidebar, command palette, themes) and the Inference Playground.

## [0.1.0] — Backend architecture
- Layered FastAPI backend: typed settings, structured logging, exception hierarchy,
  repository / service / strategy / factory patterns, plugin registry.
