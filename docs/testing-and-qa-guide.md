# Testing & Quality Assurance

## Suites

| Suite | Command | Count | Runtime | Network |
|---|---|---|---|---|
| Backend unit + API | `pytest` | 175 | ~2 min | none |
| Backend integration (real models) | `pytest -m integration` | 14 | ~30 s (after download) | first run downloads ~2.5GB |
| Frontend | `cd frontend && npm test` | 33 | ~10 s | none |
| Lint | `ruff check backend tests scripts`, `npm run lint` | — | seconds | none |

All of them run in CI (`.github/workflows/ci.yml`); integration runs on pushes to `main`.

## How models are handled in tests

An autouse fixture in `tests/conftest.py` replaces `ModelFactory.get_model` with
`FakeKeywordModel`, which labels text POSITIVE when it contains "good", "great" or
"love". That keeps unit tests deterministic, fast and offline, while still running the
full HTTP stack (`TestClient` → middleware → auth → RBAC → service → response). Tests
marked `@pytest.mark.integration` bypass the fixture and are skipped unless selected.

What still runs against real PyTorch code in the unit suite:

- **Integrated Gradients** on a tiny BERT (2 layers, 32-d) built in-process from a
  hand-written vocab. The tests check the completeness axiom (|Σ attributions − score
  gap| < 0.01 at 64 steps), sub-word → word merging, and that unknown labels are rejected.
- **Batch vs single consistency**: padded batch predictions match one-at-a-time
  predictions to 1e-5.
- **Multi-label decoding**: sigmoid thresholding, ordering, and never returning an
  empty result.
- **LRU eviction** in `ModelFactory` (weights are released, then reload on demand).
- **Hub retry**: transient errors are retried; a missing repo fails on the first attempt.

The integration suite asserts behaviour any working model must show on unambiguous
inputs, e.g. French text → `fr`, a clear insult flagged `toxic`, a paraphrase scoring
higher than a word-overlap distractor, and IG ranking "terrible"/"dull" as the top
words behind a NEGATIVE prediction.

## Coverage by area

| Area | Tests |
|---|---|
| Auth: registration, login, lockout, refresh rotation, logout-all, sessions | `test_auth.py` |
| RBAC and separation of duties | `test_rbac.py`, `test_model_registry.py` |
| Security: headers, body limits, CSV injection, password policy, JWT claims, `alg: none` | `test_security_hardening.py` |
| Inference, batch, explain, embed, zero-shot validation, task metadata | `test_inference.py` |
| Evaluation: metrics math, error analysis, served vs baseline, dataset-based runs, run-id traversal | `test_evaluation.py`, `test_inference.py` |
| Datasets: upload, cleaning, validation, profiling, versioning | `test_datasets.py` |
| Embedding index and search | `test_embeddings.py` |
| Cache / rate limiting with Redis up *and* down; retry; circuit breaker | `test_infrastructure.py` |
| Health suite | `test_health.py` |
| Real checkpoints | `test_real_models.py` (integration) |
| Frontend: stores, button, confidence chip, login form, route guard, explanation heatmap, input parsing | `frontend/src/**/*.test.ts(x)` |

## Load testing (`scripts/load_test.py`)

Concurrent HTTP requests against a live `uvicorn` instance, timed with
`time.perf_counter()`. It isn't part of `pytest`, because it needs a running server.

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000
python scripts/load_test.py --base-url http://127.0.0.1:8000 --concurrency 20 --requests 300
```

Results on an Intel Core Ultra 9 185H laptop: one uvicorn worker, SQLite, the fine-tuned
DistilBERT, rate limit raised for the test, client on the same machine.

| Endpoint | Concurrency | Requests | Success | p50 | p95 | p99 | Throughput |
|---|---|---|---|---|---|---|---|
| `POST /predict` (sentiment) | 1 | 200 | 100% | 17.8 ms | 20.4 ms | 25.6 ms | 54.8 req/s |
| `POST /predict` (sentiment) | 8 | 400 | 100% | 119.9 ms | 150.8 ms | 341.9 ms | 63.8 req/s |
| `GET /health` | 20 | 1000 | 100% | 29.0 ms | 53.3 ms | 230.1 ms | 556.6 req/s |

**What the load test found.** The first `/predict` run measured 165 ms p50 and 6 req/s,
even though the forward pass takes ~9 ms. Throughput also *fell* under concurrency, to
4.9 req/s at 8 clients. The cause was `ModelFactory` running `gc.collect()` on every
`get_model` call. A full collection walks the whole heap, which with transformer weights
loaded costs ~150 ms. Collecting only after an actual eviction brought p50 to 17.8 ms
(9.3× faster) and 8-client throughput to 63.8 req/s (13×). A regression test pins the
behaviour (`test_factory_does_not_garbage_collect_on_cache_hits`).

**Reading the numbers.** Inference is CPU-bound and PyTorch already uses every core for a
single forward pass, so extra concurrency mostly queues: throughput rises only ~16% from
1 to 8 clients while latency grows with the queue. More throughput on one box comes from
batching requests together (`/predict/batch`, or server-side micro-batching), INT8 for
batch work (`benchmarks/results.md`), or more replicas.

## Not covered

- Browser end-to-end tests. `scripts/capture_screenshots.py` drives the real UI with
  Playwright, but it isn't an assertion suite.
- Soak testing (hours of sustained load to catch leaks).
- Fault injection beyond Redis being unreachable, e.g. a database dropping mid-request.
- Tests against a live Postgres instance (the suite runs on SQLite).
