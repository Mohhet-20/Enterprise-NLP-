# Enterprise NLP Intelligence Platform

A modular, production-oriented architecture for training, evaluating, deploying,
monitoring, and explaining Transformer-based NLP models across multiple tasks
(sentiment, emotion, topic, toxicity, hate speech, fake news, language ID,
intent, multi-label, zero-shot, semantic similarity, embeddings).

## Status

Nine passes in — see `CHANGELOG.md` for what shipped in each, and
**`PROJECT_STATUS.md` for an honest, capability-by-capability map against
everything originally asked for** (what's real, what's partial, what's
not built, and why).

1. Core backend architecture skeleton (layers, patterns, plugin registry)
2. Frontend app shell + Inference Playground (`frontend/`)
3. Real authentication (persisted users, refresh-token rotation, account
   lockout, 9-role RBAC)
4. Evaluation & Error Analysis Center (real scikit-learn metrics, error
   analysis, and a lexicon baseline classifier standing in for a
   transformer — no HF Hub network access in this sandbox)
5. Health & Observability Suite (10 real endpoints) + Model Registry
   (real approval/promotion/deployment/champion lifecycle)
6. Data Platform: real dataset upload/cleaning/validation/profiling/
   versioning, plus a TF-IDF-based embedding & similarity-search platform
   (`docs/data-platform-guide.md`)
7. MLOps/DevOps: Redis (actually installed and run in this sandbox) with
   automatic in-memory fallback, rate limiting, a persisted audit trail,
   reliability primitives, Docker/Kubernetes/CI-CD artifacts, and a real
   `pip-audit` security scan with documented findings (`SECURITY.md`)
8. Security hardening + QA: real security fixes (headers, size limits,
   CSV-injection protection, password policy, auth rate limiting), a
   frontend test suite built from scratch (24 tests), real measured load
   testing, and lint wired into CI as a blocking gate — which immediately
   found and fixed 12 unused imports, a build-hygiene bug, and 38 eslint
   false positives (`docs/testing-and-qa-guide.md`)
9. Product completion: 4 real frontend pages (Dashboard, Datasets, Model
   Registry, Evaluations) replacing "Coming Soon" placeholders — every
   number and chart backed by a live API call, verified end to end
   against a real running server

**Try it**: log in with the seeded `admin` / `ChangeMe123!` account (dev
only, see below), then create a dataset, upload a CSV, register a model,
approve → promote → deploy it, and run an evaluation — the Dashboard
updates with real numbers as you go.

Still **not** built:
- Real transformer model weights, trained checkpoints, or full training loops
- A production database (SQLite dev default; PostgreSQL is code-verified
  but not live-tested — see `docs/data-platform-guide.md`)
- MFA, email verification, password reset
- AI copilot, enterprise search, workspaces/organizations, admin
  experience (no user-list endpoint yet), in-app documentation center,
  guided demo tour, unified export/feedback centers, a Monitoring
  dashboard page
- MLflow, streaming/batch inference, scheduling, alerting, human
  review/annotation, notifications, backup/recovery, true end-to-end
  browser tests, a distributed background job queue, real screenshots
  (no way to render the app in a browser from this sandbox) — see
  `PROJECT_STATUS.md` for the full list

Each of those is a follow-up build on top of this skeleton, and each one
plugs into an interface defined here without requiring changes to the core.

## Why the code is structured this way

| Concern | Pattern used | Where |
|---|---|---|
| Swappable transformer models | Strategy + Factory | `backend/nlp/inference/` |
| Data access | Repository | `backend/repositories/` |
| Business logic | Service layer | `backend/services/` |
| Cross-cutting config | Centralized typed settings | `backend/config/settings.py` |
| Consistent errors | Exception hierarchy + handlers | `backend/core/exceptions.py` |
| Wiring dependencies | Lightweight DI container | `backend/core/container.py` |
| External services | Adapter | `backend/nlp/tokenization/tokenizer_factory.py` |

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn backend.main:app --reload
```

Health check: `GET /api/v1/health`

In development, a bootstrap admin account is seeded automatically on first
run if no users exist yet: `admin` / `ChangeMe123!`. This never happens in
`production` or `testing` — see `backend/database/seed.py`. Change this
password (or just register your own account) immediately outside a local
sandbox.

## Adding a new NLP task or model

You should never need to touch `backend/core`, `backend/config`, or the API
router internals to add a task. See `docs/architecture-guide.md` →
"Extending the platform" for the exact 3 steps.

## Project layout

See `docs/architecture-guide.md` for the full breakdown of every directory
and why it exists.
