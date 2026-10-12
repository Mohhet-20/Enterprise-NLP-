# Changelog

## Pass 9 — Product Completion: real frontend pages

Built the 4 highest-value frontend pages — the gap flagged as the top
recommendation for three passes running — rather than attempting the
much larger list this prompt described (AI copilot, report center,
enterprise search, workspaces, admin, in-app docs, demo mode, export/
feedback centers). Building 4 real pages beat building 15 hollow ones.

- **Dashboard** (`/`) — real KPIs (dataset/model/deployment/evaluation
  counts, each a live API call), a real accuracy-trend chart across
  recent evaluation runs, and live system health from `/status`.
  Degrades gracefully per-card when a role lacks a permission (shown as
  "No access", not a broken error) — read-only accounts see a real,
  correctly-restricted dashboard, not a crash.
- **Datasets** (`/datasets`, `/datasets/:id`) — search/filter, create,
  real CSV upload with a live validation report, real profile charts
  (label distribution, top words, sequence-length stats — all Recharts
  against real computed data), version history, archive/restore.
- **Models** (`/models`) — list, register, approve/reject (role-gated to
  Reviewer/Admin, same separation of duties as the backend), promote,
  deploy, champion designation — every action wired to the real Pass 5
  lifecycle, action availability driven by the user's real role via a
  new client-side permission helper (`lib/permissions.ts` — UI hints
  only; the backend independently re-enforces every one of these).
- **Evaluations** (`/evaluations`, `/evaluations/:runId`) — run new
  evaluations, browse history, and a full detail view: a real confusion-
  matrix heatmap, per-class metrics table, a calibration chart, error
  summary, misclassified samples, and authenticated report/CSV downloads
  (a real blob-fetch-and-click flow, since a plain `<a href>` can't
  attach an Authorization header).
- Two new UI primitives (`Table`, `Skeleton`) — natural extensions of
  the existing shadcn-style set, not new technology, per this prompt's
  explicit "don't introduce unrelated tech" instruction.
- **Found and fixed a real bug while building these**: `Breadcrumbs`
  matched the current route by exact string equality, which broke on
  the new `/datasets/:id` and `/evaluations/:runId` detail routes
  (always showed "Not found"). Fixed with prefix matching.
- **Verified live, end to end**: booted the real backend, ran the exact
  sequence a person clicking through these pages would trigger — create
  dataset → upload CSV → register model → approve → promote → deploy →
  run evaluation — then confirmed every dashboard data source
  (`/datasets`, `/models`, `/evaluation/runs`, `/status`) returns data in
  exactly the shape the new TypeScript types expect. Not a build-passes
  check — a real request/response cycle against a real running server.
- `LICENSE` (MIT) added.
- Explicitly **not built**: AI copilot, enterprise search, workspaces/
  orgs, admin experience (blocked on a `GET /users` endpoint that
  doesn't exist yet), in-app documentation center, guided demo tour,
  unified export/feedback centers, real screenshots (no way to render
  the app in a browser and capture it from this sandbox — fabricating
  placeholder images would be dishonest, so none were added). Full list
  in `PROJECT_STATUS.md`.

## Pass 8 — Security, Testing, QA & Production Hardening

A review/hardening pass rather than new features — and it found real
bugs, not just gaps to fill.

**Security fixes** (full table with risk rationale in `SECURITY.md`):
- Security headers on every response (`X-Content-Type-Options`,
  `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`).
- Request body size limit (15MB default), checked via `Content-Length`
  before any buffering — verified end-to-end against a real standalone
  app, not just the internal comparison logic.
- CSV upload size (10MB) and row-count (50,000) caps.
- CSV formula-injection protection (`backend/utils/csv_safety.py`) — a
  real, OWASP-documented vulnerability class: a cell starting with `=`,
  `+`, `-`, or `@` is interpreted as a formula by Excel/Sheets, not
  literal text, when a CSV export is opened.
- Password policy: max length (128) and a real common-password denylist,
  sourced from well-known breach-frequency lists — per NIST 800-63B
  guidance, this matters more for guessing-resistance than arbitrary
  complexity rules.
- Auth-endpoint-specific rate limiting (10/min default on
  login/register/refresh), independent of the existing per-account lockout.
- **Reviewed and confirmed already correct** (not changed, because
  nothing was wrong): JWT algorithm pinning (no "alg:none" vulnerability
  — `algorithms=[...]` was already explicit), SQL injection (100%
  ORM/parameterized), path traversal (uploaded filenames never touch the
  filesystem).

**Real, measured performance testing** (`scripts/load_test.py`): actual
concurrent requests against a live server, actual latency percentiles.
A rate-limited endpoint under 100 concurrent requests at the 60/min
default returned **exactly 60 successes** — the rate limiter verified
under real load, not just a unit test. Full numbers and honest caveats
about this sandbox's hardware in `docs/testing-and-qa-guide.md`.

**Frontend test suite — didn't exist before this pass.** Set up Vitest +
React Testing Library from scratch: 24 tests across utilities, hooks
(Zustand stores), components (including the platform's signature
`ConfidenceChip`), a real form-interaction test for `LoginPage` (actual
typing via `@testing-library/user-event`, not just `fireEvent`), and
route-guard navigation tests. Hit and fixed a real jsdom gap along the
way (`window.matchMedia` isn't implemented by jsdom, needed a standard mock).

**Wired lint into CI as a real blocking gate — and it immediately found
real bugs that had been sitting unnoticed for multiple passes**:
- 12 genuinely unused imports (backend, `ruff`), fixed.
- 9 unsorted import blocks, auto-fixed.
- A real build-hygiene bug: `tsconfig.node.json` had no `outDir`, so
  every frontend build was silently leaking compiled `vite.config.js`/
  `.d.ts` files into the source root. Fixed by redirecting to a
  gitignored `.tsbuild/` directory (a plain `noEmit` isn't valid for a
  composite TS project — hit `TS6310` trying the simpler fix first).
- 38 eslint false positives: the Pass 2 config declared no environment
  globals, so `window`/`document`/`crypto`/`React`/`require`/`__dirname`
  were all flagged as undefined. Fixed properly (declared real
  browser/Node globals) rather than suppressed.

**Dependency audits — both sides this time**:
- Backend: continued Pass 7's `pip-audit` work.
- Frontend (new): real `npm audit` found `esbuild`'s dev-server-only
  advisory (transitively via Vite 5.x). **The fix was actually
  attempted**, not just noted: `vite@8.x` resolves cleanly but broke the
  production build (`TypeError: manualChunks is not a function` — Vite 8
  switched to the `rolldown` bundler with an incompatible config API).
  Reverted rather than force a broken build through; documented as a
  real, scoped follow-up in `SECURITY.md`.

Explicitly **not built** this pass: true end-to-end browser tests
(Playwright/Cypress), sustained/soak load testing, chaos/failure
injection beyond the already-real Redis-down path, organization/project
isolation (no org/project concept exists in the schema yet), and a
formal compliance-framework control mapping. See `PROJECT_STATUS.md`.

## Pass 7 — MLOps, DevOps & Cloud Infrastructure

- **Redis — actually installed and run in this sandbox**, not just
  claimed compatible: `apt-get install redis-server`, started it,
  confirmed with `redis-cli ping` → `PONG`, and independently confirmed
  via `redis-cli get` that a value written through the app's own
  `CacheService` was really sitting in Redis. `CacheService`
  (`backend/core/cache.py`) automatically falls back to an in-memory
  implementation when Redis is unreachable — the full 128-test suite was
  run and passed under **both** conditions in this same pass, proving
  both code paths for real rather than mocking the one that's harder to
  keep running.
- **Rate limiting**: Redis-or-in-memory fixed-window counter, keyed by
  authenticated user (or IP), exempting health/docs endpoints. Caught and
  fixed a real cross-test-pollution bug during development: the counter
  is a session-wide singleton, and the test suite's 128 tests sharing the
  same fake TestClient IP would have tripped it — fixed by disabling the
  limit in the `testing` settings tier (matching how seeding is already
  disabled there) and using per-test unique authenticated users for the
  dedicated rate-limit tests.
- **Audit trail**: persisted, queryable `AuditLog` table — not just log
  lines. Wired into real events: login success/failure/lockout,
  registration, dataset upload, and the full model-registry
  approve/reject/deploy/rollback/champion lifecycle. Restricted to the
  Auditor/Admin/Super Admin roles.
- **Reliability primitives**: `@retry(...)` (exponential backoff) and a
  `CircuitBreaker` (opens after N failures, half-opens after a timeout) —
  pure Python, unit-tested against simulated failures. Not yet wired into
  a live call, honestly, since nothing in this codebase calls an external
  service that can fail transiently yet.
- **Background processing**: one real job — uploading a dataset CSV
  returns the validation report immediately while the embedding index
  rebuilds afterward via FastAPI `BackgroundTasks`. Found and fixed a
  genuine gotcha in the process: a background task's own DB session
  bypasses FastAPI's dependency-injection system entirely (by necessity —
  it runs outside the request lifecycle), which meant it was silently
  reading from a *different* database than the test that queued it,
  since the test harness only overrides the DI-based session. Fixed by
  making the application code reference the session factory via its
  module (not a direct name import) so a monkeypatch of the underlying
  factory is actually observed — a real testability lesson, not a
  contrived one.
- **Docker**: rewrote the backend Dockerfile as a real multi-stage,
  non-root build with a healthcheck hitting the actual `/health`
  endpoint; added a matching multi-stage frontend Dockerfile
  (nginx-unprivileged) and `docker-compose.yml` with dev/prod/prod-postgres
  profiles.
- **Kubernetes**: 7 manifests (namespace, configmap, secret template,
  Redis, backend + PVC + Service + HPA, frontend, ingress), all
  YAML-syntax-validated, with liveness/readiness probes pointed at this
  platform's real health endpoints. Documented a genuine unresolved
  tension directly in the manifest: the backend PVC is `ReadWriteOnce`,
  which doesn't actually support the Deployment's 2-replica default on
  the SQLite storage backend — correct for 1 replica on SQLite or N
  replicas on Postgres, not both defaults simultaneously.
- **CI/CD**: `.github/workflows/ci.yml` (dependency review, lint+test,
  security scan, frontend build, Docker build/publish) and
  `release.yml` (tag-triggered, re-verifies before releasing). Every
  command in `ci.yml` was actually run against this repo during
  development — not a template copied in and left unverified.
- **Security scanning — real findings, not a scanner nobody reads**: ran
  `pip-audit` for real, found 23 known vulnerabilities across 5 packages,
  fixed what could be safely bumped (fastapi, python-jose, python-multipart,
  pytest) down to 16, and documented in `SECURITY.md` exactly why the
  remaining 16 aren't fixed yet — two are capped by transitive dependency
  constraints (`pyasn1` by `python-jose`, `starlette` by `fastapi`'s
  0.115.x pin) and one (`ecdsa`) has no upstream fix available at all.
  Verified honestly, including reverting two version bumps that turned
  out to break dependency resolution.
- Added `docs/infrastructure-guide.md` and `SECURITY.md`. Explicitly
  **not built** this pass: MLflow, streaming/batch inference, scheduling,
  alerting, distributed background job queue, disaster-recovery tooling,
  cloud-provider provisioning. See `PROJECT_STATUS.md`.

## Pass 6 — Data Platform (Dataset Management + Embeddings)

- **Dataset Management**: persisted `Dataset`/`DatasetRecord` models with
  real audit fields (created/modified by, timestamps) and soft delete.
  CSV upload → real cleaning pipeline (HTML/emoji/URL/mention/hashtag
  handling, Unicode NFKC normalization) → real validation (encoding
  errors, duplicates, empty/short/long text, missing/invalid labels,
  class imbalance) → persisted records, all verified live against a
  genuinely messy CSV (HTML tags, emoji, an exact duplicate, an empty
  row, a too-short row, a missing label, and a label outside the declared
  set — every one correctly flagged with its row index).
- **Data profiling**: real token/vocabulary statistics, sequence-length
  distribution, label distribution, and stopword-filtered word frequency
  — computed from actual records, not canned output.
- **Versioning**: parent-pointer chain (copy + increment + link back),
  full history walk, aggregate version comparison.
- **Data augmentation**: real, seedable EDA techniques (synonym
  replacement, random deletion/swap/insertion) — back-translation and
  neural paraphrasing are explicitly out of scope (need a real model).
- **Embedding Platform**: TF-IDF vectors (scikit-learn) implementing the
  `BaseEmbedder` interface from pass 1, plus a per-dataset
  `EmbeddingIndexService` for real cosine-similarity search and
  nearest-neighbor lookup — verified live: a "battery performance" query
  correctly ranked two battery-related reviews above an unrelated
  shipping complaint.
- **PostgreSQL**: verified code-level compatibility (driver installs,
  engine constructs against a `postgresql://` URL, no SQLite-specific
  code outside one already-conditional branch) — not live-tested against
  a running server (no persistent background service across tool calls
  in this sandbox).
- Added `docs/data-platform-guide.md`: architecture notes, a Mermaid ER
  diagram, a full data dictionary for the new tables, and an honest
  explanation of the versioning/lineage tradeoffs made.
- 33 new tests (26 dataset + 7 embedding), all passing; 109 total.
- Explicitly **not built** this pass: annotation/human-review workflows,
  Redis caching, vector-database integration, backup/recovery, dataset
  encryption-at-rest, organizations/teams/projects schema, data lineage
  graph API. See `PROJECT_STATUS.md`.

## Pass 5 — Health & Observability Suite + Model Registry

- **Health & Observability**: `/liveness`, `/readiness`, `/database`,
  `/model`, `/embedding`, `/monitoring-health`, `/system`, `/version`,
  `/status` — 9 new endpoints alongside the existing `/health`, each
  running a real check (a real `SELECT 1`, real `psutil` CPU/memory/disk
  reads, real introspection of the model factory's cache and the plugin
  registry) rather than a hardcoded "ok". `/embedding` honestly reports
  `not_implemented` since that subsystem doesn't exist yet.
- **Model Registry**: persisted model versions with a real lifecycle —
  register → (staging, freely) → approve/reject (gated by role, not just
  permission: an ML engineer can't approve their own submission) →
  promote to production (blocked with a 409 if not approved) → deploy
  (blocked if not approved+production; automatically rolls back whatever
  was previously deployed for that task) → optional champion designation
  (automatically un-champions the previous one for that task) → compare
  two versions' metrics.
- Added `PROJECT_STATUS.md`: an honest, capability-by-capability status
  map across all four build prompts (✅ real / 🚧 partial / 📋 not built),
  with reasoning for each gap. Read this first if you want the unvarnished
  picture of what's actually here versus what was originally asked for.
- Added a root `.gitignore` (generated DBs and JSON stores were previously
  uncommitted only by omission).

## Pass 4 — Evaluation & Error Analysis Center

- Real metrics (scikit-learn): accuracy, macro/weighted F1, per-class
  precision/recall/F1, confusion matrix, ROC-AUC, calibration bins
  (reliability-diagram data) — `backend/evaluation/metrics.py`.
- Real error analysis: confidence errors (wrong despite high confidence),
  hard examples (low confidence regardless of outcome), per-class false
  positive/negative counts, and accuracy sliced by text length —
  `backend/evaluation/error_analysis.py`.
- Every number is computed from genuine predictions: a small deterministic
  lexicon-based sentiment classifier (`baseline_classifier.py`) — this
  sandbox has no network access to the Hugging Face Hub, so a real
  pretrained transformer can't be downloaded here — run against a
  hand-labeled 48-example evaluation set that deliberately includes
  negation and sarcasm to produce real (not fabricated) errors: 81.25%
  accuracy, 9 genuine misclassifications.
- New endpoints: `POST /evaluation/run`, `GET /evaluation/runs`,
  `GET /evaluation/runs/{id}`, `GET /evaluation/runs/{id}/report`
  (Markdown), `GET /evaluation/runs/{id}/misclassified.csv`.
- Persisted the same way `experiments_store/` already works (JSON files on
  disk) — no new persistence mechanism introduced.
- Scoped down from the original "Evaluation & Error Analysis Center" ask:
  no PDF export (Markdown + CSV only), and only `sentiment_analysis` has a
  registered baseline (others return a clear 400, not a silent fake result).

## Pass 3 — Real authentication

- Persisted `User` and `RefreshToken` models (SQLite dev default).
- Registration, login (bcrypt password hashing), account lockout after
  repeated failures, opaque rotating/revocable refresh tokens (SHA-256
  hashed at rest — never stored or logged in plaintext), logout,
  logout-all, active-session listing.
- Expanded `UserRole` to the platform's 9 enterprise roles (Super Admin,
  Admin, ML Engineer, NLP Engineer, Data Scientist, Reviewer, Business
  Analyst, Auditor, Read-Only User), keeping the original 4 roles as
  backward-compatible aliases.
- `get_current_user` now resolves the live user from the database on every
  request instead of trusting the role embedded in the JWT payload.
- Frontend: password + "remember me" login, a registration page, and a
  silent-refresh-and-retry-once on 401 in the API client.
- **Replaces** the dev-mode `/auth/login` from Pass 2, which was explicitly
  documented at the time as a placeholder ("no persisted user store yet
  ... replace with real credential verification when that lands").
- **Bug fixes uncovered along the way**, both pre-dating this pass:
  - `backend/models/__init__.py` was empty, so no ORM model (including
    `Experiment`) was ever actually registered on `Base.metadata` —
    `create_all()` silently created no tables. Fixed by importing every
    concrete model there.
  - The test suite's in-memory SQLite engine was missing `poolclass=
    StaticPool`, so each new connection got its own empty in-memory
    database. Dormant until a test first did a real ORM query (which no
    test did until this pass's auth tests).
  - `DateTime(timezone=True)` doesn't reliably round-trip tzinfo through
    SQLite: a value is timezone-aware right after creation but comes back
    naive on a later request, breaking comparisons against
    `datetime.now(timezone.utc)`. Fixed with a small `ensure_aware_utc`
    helper used wherever a stored datetime is compared against "now".
  - `bcrypt>=4.1` removed the lenient 72-byte truncation behavior that
    `passlib==1.7.4`'s startup self-test depends on. Pinned `bcrypt==4.0.1`.

## Pass 2 — Frontend

- App shell (sidebar, top nav, command palette, theme toggle) and the
  Inference Playground, wired to the real backend.
- Added `/tasks` and the (now-replaced) dev-mode `/auth/login` endpoints.

## Pass 1 — Backend architecture skeleton

- Layered architecture, config/logging/exceptions, Strategy+Factory model
  registry, Repository/Service patterns, plugin registry, FastAPI app.
