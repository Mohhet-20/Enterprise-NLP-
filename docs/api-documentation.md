# API Documentation

Full interactive schema: `/docs` (Swagger UI) or `/redoc` when the app is running.

## `POST /api/v1/auth/register`
Creates a new user (`username`, `email`, `password`). New accounts start as
`read_only_user`. Username: 3–32 chars, letters/numbers/underscores only.
Password: minimum 8 characters. Returns `UserPublic` (never the password
or its hash).

## `POST /api/v1/auth/login`
`{"username", "password", "remember_me"}` → `TokenResponse` (`access_token`,
`refresh_token`, `expires_in`, `user`). Fails with 401 on wrong credentials
(username-not-found and wrong-password return the identical message, to
avoid username enumeration) and 423 if the account is locked after
`max_failed_login_attempts` (default 5) consecutive failures, for
`account_lockout_minutes` (default 15).

## `POST /api/v1/auth/refresh`
`{"refresh_token"}` → a new `TokenResponse`. Refresh tokens are opaque
random strings, hashed (SHA-256) at rest, and **rotate on every use**: the
presented token is revoked and a new one issued in the same call, so a
reused/stolen-then-rotated token stops working immediately.

## `POST /api/v1/auth/logout`
`{"refresh_token"}` → 204. Revokes that one session. Idempotent — logging
out twice, or with an already-invalid token, is a no-op, not an error.

## `POST /api/v1/auth/logout-all`
Auth required. Revokes every active refresh token for the current user
(all devices/sessions) → 204.

## `GET /api/v1/auth/sessions`
Auth required. Lists the current user's active (non-revoked, unexpired)
sessions: `id`, `issued_at`, `expires_at`.

## `GET /api/v1/auth/me`
Auth required. Returns the current user's `UserPublic`.

## `GET /api/v1/health`
Returns app name, environment, and status. No auth required.

## `GET /api/v1/liveness`
No dependencies checked — always `{"status": "alive"}` if the process can
respond at all. For an orchestrator's liveness probe.

## `GET /api/v1/readiness`
Checks the database is actually reachable (`SELECT 1`). Returns 503 if not
— for an orchestrator's readiness probe (whether to route traffic here).

## `GET /api/v1/database`
The same database check as `/readiness`, standalone, with latency.

## `GET /api/v1/model`
Introspection: which tasks are registered in the plugin registry,
which architectures the model factory can construct, and which model
instances are actually cached in memory right now.

## `GET /api/v1/embedding`
Which encoder backs the dataset vector index (`dense` or `tfidf`), the
embedding model, and how many dataset indices are currently built.

## `GET /api/v1/monitoring-health`
Lightweight check that the metrics-collection subsystem itself is
functioning (distinct from `GET /monitoring/metrics`, which returns the
full data it's collected).

## `GET /api/v1/cache`
Reports which cache backend is actually serving requests right now —
`"redis"` if reachable, `"in_memory"` if it fell back
(`backend/core/cache.py`). Both are a healthy `"ok"` status.

## `GET /api/v1/system`
CPU/memory/disk percentages via `psutil`.

## `GET /api/v1/version`
App name, version, environment, Python version, and git commit (`unknown`
if not running from a git checkout).

## `GET /api/v1/status`
Aggregates every check above into one page. `"status": "error"` only if a
*critical* dependency (the database) is down.

## `GET /api/v1/tasks`
Returns every registered task with its default model, a one-line
description, and whether `/explain` supports it. Drives the frontend's task
selector so it never hardcodes a task list.

## `POST /api/v1/evaluation/run`
Requires `experiment:write` (plus `dataset:read` when `dataset_id` is set).

```json
{
  "task": "sentiment_analysis",
  "model": "served",
  "eval_set": "sst2_validation",
  "dataset_id": null
}
```

- `model`: `served` (the task's transformer) or `lexicon_baseline` (sentiment only).
- `eval_set`: `challenge_set` (48 hand-labelled hard cases) or `sst2_validation`
  (872 sentences, fetched once via `datasets`). Built-in sets are sentiment-only.
- `dataset_id`: evaluate on any uploaded, labelled Data Platform dataset instead.
  Works for every single-label task; for zero-shot, the dataset's `label_set`
  becomes the candidate labels.

Multi-label tasks (toxicity, topic) and pair/vector tasks return 400 — accuracy
against one gold label isn't defined for them. Metrics come from scikit-learn and
the full report is persisted. Returns
`EvaluationRunResult`: accuracy, macro/weighted F1, ROC-AUC, confusion
matrix, per-class precision/recall/F1, calibration bins, and an error
summary (confidence errors, hard examples, per-class and per-length-slice
error breakdown).

## `GET /api/v1/evaluation/runs`
Requires `experiment:read`. Lists past evaluation runs (summary only).

## `GET /api/v1/evaluation/runs/{run_id}`
Requires `experiment:read`. Full `EvaluationRunResult` for one run.

## `GET /api/v1/evaluation/runs/{run_id}/report`
Requires `experiment:read`. The same run rendered as a downloadable
Markdown report (overall metrics, confusion matrix table, error summary,
misclassified samples).

## `GET /api/v1/evaluation/runs/{run_id}/misclassified.csv`
Requires `experiment:read`. CSV export of every misclassified sample
(`text, true_label, predicted_label, confidence`) — not capped, unlike the
inline `misclassified_samples` field on the JSON result.

## `POST /api/v1/predict`
Runs inference for a registered NLP task.

Requires a bearer token (`Authorization: Bearer <token>`) with the
`model:infer` permission (see `backend/auth/rbac.py`).

**Request body** (`InferenceRequest`):
```json
{
  "task": "sentiment_analysis",
  "text": "This product exceeded expectations.",
  "model_name": null,
  "candidate_labels": null
}
```

`model_name` is optional — omitted, it falls back to the task's registered
default model (see `backend/plugins/__init__.py`). Task-specific fields:

| Task | Extra fields |
|---|---|
| `zero_shot_classification` | `candidate_labels` (2–20, required), `multi_label` |
| `semantic_similarity` | `text_pair` (required) — result is the cosine similarity |

**Response** (`InferenceResponse`):
```json
{
  "task": "sentiment_analysis",
  "model_name": "distilbert-sst2",
  "results": [{"label": "POSITIVE", "score": 0.98, "raw_scores": {"NEGATIVE": 0.02, "POSITIVE": 0.98}}],
  "latency_ms": 18.4
}
```

Multi-label tasks (`toxicity_detection`, `topic_classification`) return one result per
label whose sigmoid score is ≥ 0.5 (always at least the top label).

## `POST /api/v1/predict/batch`
Same permission. `{"task", "texts": [...], "candidate_labels"?}`, up to 64 texts. Texts
are padded and run `INFERENCE_BATCH_SIZE` at a time. Returns one item per input, in
order, plus total latency and throughput.

## `POST /api/v1/explain`
Same permission. `{"task", "text", "target_label"?, "n_steps"?}` (text ≤ 5,000 chars,
8–128 steps, default 32). Integrated Gradients attributions for the served model:

```json
{
  "label": "NEGATIVE",
  "method": "integrated_gradients",
  "target_score": 0.9987,
  "baseline_score": 0.4113,
  "convergence_delta": 0.0042,
  "attributions": [{"token": "dull", "importance": 0.21}, {"token": "terrible", "importance": 0.34}]
}
```

`convergence_delta` is Σ attributions − (target − baseline); near zero means the
approximation is faithful. Available for tasks whose `/tasks` entry has
`explainable: true` (sentiment, emotion, toxicity).

## `POST /api/v1/embed`
Same permission. `{"texts": [...]}` (≤ 64) → 384-dimensional L2-normalised vectors
from `all-MiniLM-L6-v2`.

## Model Registry

All require `experiment:write` unless noted.

- `POST /api/v1/models` — register a version (`name`, `task`, `architecture`,
  `version`, `model_name_or_path`, optional `evaluation_run_id`/`notes`).
  Starts at stage `development`, approval `pending`, not deployed.
- `GET /api/v1/models?task=&stage=` — list, filterable. Requires `experiment:read`.
- `GET /api/v1/models/{id}` — one entry. Requires `experiment:read`.
- `POST /api/v1/models/{id}/approve` / `/reject` — **requires the Reviewer,
  Admin, or Super Admin role specifically** (checked via `require_any_role`,
  not the generic `experiment:write` permission) — separation of duties: the
  engineer who registered a model shouldn't be the one who approves it.
- `POST /api/v1/models/{id}/promote` (`{"stage": "staging"|"production"|"archived"}`)
  — promoting to `production` returns 409 unless the model is `approved`.
- `POST /api/v1/models/{id}/deploy` — 409 unless `approved` **and**
  already staged to `production`. Deploying automatically rolls back
  whatever was previously deployed for the same task — never more than
  one deployed model per task.
- `POST /api/v1/models/{id}/rollback` — manually mark a deployed model rolled back.
- `POST /api/v1/models/{id}/set-champion` — automatically un-champions the
  previous champion for that task — never more than one champion per task.
- `GET /api/v1/models/compare/{id_a}/{id_b}` — side-by-side accuracy/F1 deltas.
  Requires `experiment:read`.

## Dataset Management

`POST /datasets`, `.../upload` (CSV, multipart), `.../version`, `.../archive`,
`.../restore`, `PUT .../tags` require `dataset:write`. Everything else below
requires `dataset:read` (granted to ML Engineer, NLP Engineer, Data
Scientist, Admin, Super Admin — not the read-only/analyst roles by default).

- `POST /api/v1/datasets` — create a dataset shell (`name`, `task`,
  optional `description`/`label_set`). Starts empty, `status: draft`.
- `POST /api/v1/datasets/{id}/upload` — multipart CSV upload (`text`,
  `label` columns). Runs the cleaning pipeline (toggle with
  `?apply_cleaning=false`), then validation, then persists every row
  as a `DatasetRecord`. Returns the updated dataset + a full
  `ValidationReportSchema` (duplicate/empty/short/long/missing-label/
  invalid-label counts, per-issue affected row indices, label
  distribution). `status` becomes `validated` only if there are no
  *blocking* issues (encoding errors, empty documents) — everything else
  (duplicates, imbalance, short/long text) is a warning, not a block.
- `GET /api/v1/datasets?query=&task=&tag=&include_archived=` — search/filter.
- `GET /api/v1/datasets/{id}` — one dataset's metadata.
- `GET /api/v1/datasets/{id}/preview?limit=&offset=` — paginated records.
- `GET /api/v1/datasets/{id}/validation-report` — re-runs validation
  against the dataset's *current* records (always fresh, never stale).
- `GET /api/v1/datasets/{id}/profile` — token/vocabulary stats, sequence
  length distribution, label distribution, top word frequencies.
- `GET /api/v1/datasets/{id}/versions` — full version history (oldest→newest).
- `POST /api/v1/datasets/{id}/version` — create a new version: copies
  metadata + every record, increments `version`, sets `parent_version_id`.
- `POST /api/v1/datasets/{id}/archive` / `/restore` — soft delete, never a hard `DELETE`.
- `PUT /api/v1/datasets/{id}/tags` — replace the tag list.
- `GET /api/v1/datasets/compare/{id_a}/{id_b}` — row-count/vocabulary/label-distribution deltas.
- `POST /api/v1/datasets/augment` — run EDA-style augmentation
  (`synonym_replacement`, `random_deletion`, `random_swap`,
  `random_insertion`) on arbitrary text, standalone (not tied to a stored dataset).

## Embedding Platform

A per-dataset vector index, encoded with MiniLM sentence embeddings by default
(`EMBEDDING_ENCODER=tfidf` for a lexical, download-free index). All three require
`dataset:read`.

- `POST /api/v1/datasets/{id}/embeddings/build` — encodes the dataset's current
  records into an in-memory index. Returns vector count, dimension, encoder, model
  and build time.
- `GET /api/v1/datasets/{id}/embeddings/search?query=&top_k=` — exact top-k cosine
  search; 404 if `/build` hasn't been called for this dataset.
- `GET /api/v1/datasets/{id}/embeddings/similarity?record_id_a=&record_id_b=`
  — pairwise cosine similarity between two records already in the index.

## `GET /api/v1/metrics`
Returns in-process inference metrics (count, error rate, avg latency) keyed
by `task:model_name`. Backing implementation: `backend/monitoring/metrics.py`.

## `GET /api/v1/audit-logs`
Requires `audit:read` (Auditor, Admin, Super Admin only — deliberately not
readable by every role that can read experiments/datasets). Filterable by
`actor_id`, `action`, `resource_type`, `resource_id`. Populated by these
events: login success/failure/lockout, registration, model
approve/reject/deploy/rollback/champion-set, dataset upload — written
synchronously in the same request as the action (never as a background
task — see `docs/infrastructure-guide.md` for why audit correctness
shouldn't be droppable).

## Error format

Every error response (4xx/5xx) has this shape:
```json
{
  "error": {
    "code": "ValidationError",
    "message": "...",
    "details": {},
    "request_id": "..."
  }
}
```
`request_id` matches the `X-Request-ID` response header and the structured
log line for that request — use it to correlate a client-reported error
with server logs.
