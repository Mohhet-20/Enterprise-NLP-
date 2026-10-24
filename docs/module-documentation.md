# Module Documentation

| Module | Responsibility | Depends on |
|---|---|---|
| `backend/config` | Typed settings, logging setup | nothing else in `backend/` |
| `backend/core` | Exceptions, DI container, middleware, constants, cache (Redis-or-in-memory), rate limiting, retry/circuit-breaker | `config` |
| `backend/database` | Engine, session, declarative base | `config` |
| `backend/models` | SQLAlchemy ORM models | `database` |
| `backend/schemas` | Pydantic request/response contracts | `core` (constants) |
| `backend/repositories` | Data access (Repository pattern) | `database`, `models`, `core` |
| `backend/auth` | JWT issuing/verification, RBAC | `config`, `core`, `schemas` |
| `backend/nlp/inference` | Model strategies (HF classifier, zero-shot NLI, sentence-transformer) + LRU-capped factory | `core`, `config` |
| `backend/nlp/tokenization` | Tokenizer adapter | `core` |
| `backend/nlp/embeddings` | Embedding strategy interface + TF-IDF implementation | `core` |
| `backend/nlp/training` | `BaseTrainer` + Hugging Face `Trainer` implementation | `evaluation` |
| `backend/datasets` | Cleaning, validation, profiling, augmentation + interface/registry | `core` |
| `backend/evaluation` | Metrics (sklearn), error analysis, baseline classifier, run persistence | `core` |
| `backend/experiments` | Experiment tracking (JSON-backed) | `config`, `core` |
| `backend/monitoring` | In-process metrics collection + health/observability checks | `database`, `nlp/inference`, `plugins` |
| `backend/reporting` | Report generation | — |
| `backend/explainability` | Explanation interface + Integrated Gradients | — |
| `backend/workflows` | Multi-step pipeline composition | — |
| `backend/plugins` | Task registration (extensibility seam) | `core`, `evaluation`, `explainability` |
| `backend/services` | Business logic orchestration | `nlp`, `repositories`, `plugins`, `monitoring` |
| `backend/api` | HTTP routing | `services`, `schemas`, `auth` |
| `backend/utils` | Shared validation helpers | `core` |

Each module's own docstrings (top of each file) explain the *why*, not just
the *what* — read those before adding to a module.

**Model Registry** deliberately doesn't get its own top-level module — it's
a `ModelRegistryEntry` model + `ModelRegistryRepository` + `ModelRegistryService`
+ API endpoints, following the exact same layering every other persisted
concept (users, experiments) already uses. A new top-level `backend/registry/`
folder would have duplicated that structure for no benefit.

**Audit trail** follows the same pattern: `AuditLog` model +
`AuditLogRepository` + `AuditService`, called from wherever an
audit-worthy action happens (`AuthService`, `ModelRegistryService`,
the dataset upload endpoint) rather than as middleware that would have
to guess which requests matter — explicit call sites make it obvious
exactly what is and isn't audited.

**Background jobs** (`backend/services/background_jobs.py`) are plain
functions dispatched via FastAPI's `BackgroundTasks`, not a separate
task-queue module — there's currently one job. It would graduate to its
own module (and a distributed queue) once there are enough of them to justify it.
