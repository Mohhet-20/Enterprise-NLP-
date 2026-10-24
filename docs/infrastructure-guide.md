# Infrastructure & Operations Guide

Containers, orchestration, CI/CD, reliability and observability in one place. For
sizing and environment variables, see `docs/deployment-guide.md`.

## Containers

- **`docker/Dockerfile`** (backend): multi-stage. A `builder` stage with the compiler
  toolchain installs CPU-only PyTorch and `requirements-ml.txt`; the slim `runtime`
  stage copies only the installed packages. It runs as non-root `appuser` (uid 1000),
  listens on `$PORT`, runs one worker by default (each worker holds its own copy of the
  models), and keeps weights in `/app/.model_cache` so a volume can persist them. The
  `HEALTHCHECK` calls `/api/v1/health`.
- **`docker/frontend.Dockerfile`**: Node builds the Vite app and
  `nginxinc/nginx-unprivileged` serves it on 8080. `docker/nginx.conf` handles SPA
  routing and exposes `/healthz`.
- **`docker/docker-compose.yml`** profiles:
  - `dev` — hot-reload backend with bind-mounted source, Redis, SQLite
  - `prod` — built images, a model-cache volume, `artifacts/models` mounted read-only,
    frontend behind nginx
  - `prod-postgres` — adds Postgres in place of SQLite (no code changes, just `DATABASE_URL`)

## Kubernetes (`deployment/k8s/`)

| File | Contains |
|---|---|
| `namespace.yaml` | The `nlp-platform` namespace |
| `configmap.yaml` | Non-secret config, including `MAX_LOADED_MODELS` and `EMBEDDING_ENCODER` |
| `secret.yaml` | Template with placeholder values; never apply as-is |
| `redis.yaml` | Redis Deployment + Service |
| `backend.yaml` | Deployment (soft anti-affinity, non-root `securityContext`, 3Gi/5Gi memory sized for resident models, model-cache `emptyDir`), SQLite PVC, Service, and an HPA (CPU + memory, 2→10) |
| `frontend.yaml` | Frontend Deployment (non-root) + Service |
| `ingress.yaml` | `/api` → backend, everything else → frontend; TLS via a cert-manager `ClusterIssuer` |

Probes use `/api/v1/liveness` (process responds) and `/api/v1/readiness` (database
reachable).

**Replica count vs. storage:** the SQLite PVC is `ReadWriteOnce`, which is correct for
one backend replica. The HPA's minimum of 2 assumes Postgres. For SQLite, set
`minReplicas: 1`, or switch `DATABASE_URL`.

**Cold starts:** with an `emptyDir` model cache, each new pod downloads weights on
first use. For instant scale-out, pre-populate a `ReadOnlyMany` volume with a Job and
mount that instead.

## CI/CD (`.github/workflows/`)

`ci.yml`:

| Job | Runs | Trigger |
|---|---|---|
| `dependency-review` | GitHub's dependency review | PRs |
| `backend` | `ruff check`, `pytest -q` (fake models, no network) | every push / PR |
| `backend-integration` | `pytest -m integration` against real checkpoints, with a cached model directory | pushes to `main` |
| `backend-security-scan` | `pip-audit -r requirements.txt` | every push / PR |
| `frontend` | `npm ci`, lint, Vitest, production build | every push / PR |
| `docker-build` | builds both images (no push), with GHA layer cache | after backend + frontend pass |

`release.yml` runs on `v*.*.*` tags: it re-runs the test suite against the tagged commit,
then publishes a GitHub Release with generated notes.

## Cloud mapping

The images and manifests are provider-agnostic:

| Provider | Compute | Database | Cache |
|---|---|---|---|
| AWS | EKS | RDS Postgres | ElastiCache |
| GCP | GKE / Cloud Run | Cloud SQL | Memorystore |
| Azure | AKS | Azure Database for PostgreSQL | Azure Cache for Redis |
| Render / Railway / HF Spaces | Dockerfile as-is (`$PORT` honoured) | managed Postgres or SQLite volume | optional |

## Reliability

- **Retry with backoff** (`backend/core/resilience.py`) wraps every Hugging Face Hub
  load (`backend/nlp/inference/hub.py`). Transient network errors are retried three
  times; permanent errors (unknown repo, missing file) fail immediately.
- **Circuit breaker** in the same module: opens after N consecutive failures, goes
  half-open after a timeout, closes on the next success.
- **Cache / rate-limit fallback** (`backend/core/cache.py`): Redis when reachable, an
  in-process dict when not. The infrastructure tests pass both with Redis running and
  with it unreachable.
- **Model memory bound**: `ModelFactory` LRU-evicts loaded models beyond
  `MAX_LOADED_MODELS`, so serving every task can't exhaust the pod's memory.

## Background processing

`backend/services/background_jobs.py`, dispatched via FastAPI `BackgroundTasks`. After a
dataset CSV upload, the validation report returns immediately and the embedding index
rebuilds afterwards, in-process.

A background job opens its **own** database session: the request-scoped one is closed
by the time the job runs. `tests/conftest.py` also patches the session factory itself,
because FastAPI's dependency override doesn't reach code that bypasses `Depends`.
Without that patch, a background job in tests would silently use a different database
from the request that queued it.

A distributed queue (Celery / RQ / Arq) is the next step once jobs must survive
restarts or run on separate workers.

## Observability

- Structured JSON logs with category-scoped loggers and a `request_id` on every line,
  which matches the `X-Request-ID` response header and the `request_id` in error bodies
- A 10-endpoint health suite (`/liveness`, `/readiness`, `/database`, `/model`,
  `/embedding`, `/cache`, `/system`, `/version`, `/monitoring-health`, `/status`)
- Per-task, per-model inference count, error rate and latency (`/metrics`)
- A persisted, queryable audit trail for security-relevant actions (`/audit-logs`)

Not yet built: OpenTelemetry tracing, a Prometheus scrape endpoint, log shipping,
scheduled jobs (e.g. nightly re-evaluation via APScheduler), and automated
backup/restore. SQLite is a single file and Postgres uses `pg_dump`, but neither is
scheduled or restore-tested.
