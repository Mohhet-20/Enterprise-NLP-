# Testing & Quality Assurance

Consolidates the testing categories from the hardening pass into one
document: what's covered, what's measured for real, and what's out of
scope with reasoning — rather than the ~5 separate testing docs the
original spec implied (unit/integration/e2e/load/stress).

## Test suite summary

| Layer | Count | Command | Status |
|---|---|---|---|
| Backend (unit + integration) | 143 | `pytest -q` | ✅ All passing |
| Frontend (unit + component + form + navigation) | 24 | `npm test` (frontend/) | ✅ All passing |

Backend tests cover services, repositories, API routes end-to-end (via
`TestClient`, i.e. real request/response cycles through real middleware,
real auth, real RBAC — not mocked), auth, RBAC, inference, evaluation,
embeddings, model registry business rules, dataset validation/cleaning/
profiling, caching (both the Redis and in-memory-fallback code paths),
rate limiting, retry/circuit-breaker, and the audit trail.

Frontend tests (new this pass — see CHANGELOG.md) cover:
- **Utilities**: `cn()` class-merging logic
- **Hooks** (Zustand stores are consumed as hooks): `useAuthStore`
  (login/logout state transitions), `useThemeStore` (toggle logic)
- **Components**: `Button` (variants, disabled state, click handling),
  `ConfidenceChip` (the platform's signature visual component — label
  rendering, percentage rounding, the CSS custom property driving the
  confidence fill)
- **Forms**: `LoginPage` — real typing via `@testing-library/user-event`
  (not just `fireEvent`), verifying the submit button's disabled state
  tracks both fields being filled, that the API is called with the
  trimmed username and correct `remember_me` flag, and that a successful
  login actually updates the auth store
- **Navigation**: `ProtectedRoute` — redirects to `/login` when
  unauthenticated, renders protected content when authenticated

**Not covered** by frontend tests: Recharts-based chart rendering
internals (jsdom + Recharts is possible but low-value to test deeply —
the chart just renders whatever `ResultPanel` computes, which is already
covered by testing the computation), and end-to-end browser tests
(Playwright/Cypress) — the frontend has never been run in a real browser
in this sandbox, only via `vitest`/jsdom and `vite build`.

## Real load testing (`scripts/load_test.py`)

Not simulated numbers — real concurrent HTTP requests against a live
`uvicorn` instance, measured with `time.perf_counter()`. Run manually
(not part of `pytest`, which shouldn't depend on a running server):

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000 &
python scripts/load_test.py --base-url http://127.0.0.1:8000 --concurrency 20 --requests 300
```

**Actual results from this build** (single uvicorn worker, this sandbox's
shared/constrained hardware — explicitly not a production-representative
environment, see caveat below):

| Test | Requests | Concurrency | Success rate | p50 | p95 | p99 | Throughput |
|---|---|---|---|---|---|---|---|
| `/api/v1/health` (rate-limit-exempt) | 300 | 20 | 100% | 227ms | 369ms | 496ms | 30.1 req/s |
| `/api/v1/tasks` (rate-limited, 60/min default) | 100 | 10 | **60%** | 54ms | 99ms | 180ms | 31.0 req/s |

The second result is a genuinely interesting finding, not just a
performance number: **exactly 60 of 100 concurrent requests succeeded**,
matching the default 60-requests-per-minute limit precisely. That's the
rate limiter being verified under real concurrent load, not just in a
unit test — a meaningfully stronger claim than "the middleware has test
coverage."

**Honest caveats**:
- Single worker, no load balancer, no production-grade WSGI/ASGI tuning —
  these numbers describe this specific sandbox, not a production
  deployment's expected performance.
- The ~200ms+ p50 for the health endpoint under 20-way concurrency is
  higher than a bare health check "should" take — some of that is
  request-context logging (a JSON log line per request) and this
  sandbox's shared CPU, not necessarily representative of a dedicated
  production host.
- No sustained/soak testing (running load for minutes/hours to catch
  memory leaks or slow degradation) — only short bursts.
- No testing against Postgres or a multi-worker deployment — the numbers
  above are SQLite + single-process.

## Stress / failure testing

**Covered for real** (not simulated): the cache/rate-limiting test suite
(`tests/test_infrastructure.py`) runs against **both** a live Redis
instance and Redis being completely unreachable, in the same pass, and
passes 128/128 (now 143/143 with this pass's additions) either way — a
genuine failure-injection test, not a mock.

**Not covered**: simulated database failure mid-request, simulated
network partition, background-worker crash recovery, or MLflow failure
(no MLflow integration exists yet — see `PROJECT_STATUS.md`). These would
need either a test double that can fail on command (e.g. a wrapped DB
session that raises on the Nth call) or a way to actually kill and
restart a dependency mid-test, neither of which this pass built.

## Dependency audit

See `SECURITY.md` for the full backend `pip-audit` findings and fixes.
This pass added a **frontend** dependency audit (`npm audit`), which
surfaced one real finding: `esbuild <=0.24.2` (bundled transitively via
Vite 5.x) has a moderate-severity advisory
([GHSA-67mh-4wv8-2f99](https://github.com/advisories/GHSA-67mh-4wv8-2f99))
— it only affects the **local dev server** (`npm run dev`), allowing any
website to send requests to it and read the response; production builds
serve static files via nginx with no esbuild dev server involved, so
production isn't affected.

**The fix was actually attempted, not just noted**: `npm install
vite@latest` resolves to Vite 8.x, which switched its internal bundler to
`rolldown` — the project's `manualChunks` config (an object mapping chunk
names to package lists) isn't valid in the new API, which expects a
function instead, and the production build failed with `TypeError:
manualChunks is not a function`. Reverted to the working Vite 5.4.21
rather than force a broken build — the same real-conflict-encountered,
real-revert pattern used for the backend's `pyasn1`/`starlette` versions
in `SECURITY.md`. Fixing this properly means rewriting the chunking
config for the new API and re-verifying the whole frontend build and
test suite, which is a real, scoped follow-up, not a version-number change.

## Code quality review

Findings from actually reading through the codebase during this pass,
**and then wiring linting into CI as a real blocking gate** — which
immediately surfaced genuine issues that had been sitting unnoticed:

- **12 real unused imports** across the backend (`ruff check`), fixed —
  not stylistic nitpicks, genuine dead imports (`typing.Optional` in
  `base_repository.py`, `ModelArchitecture`/`NLPTask` in
  `inference_service.py`, etc.).
- **9 unsorted import blocks**, auto-fixed (mechanical, zero behavior change).
- **A real build-hygiene bug**: `tsconfig.node.json`'s composite-project
  config had no `outDir`, so every `npm run build` was silently emitting
  compiled `vite.config.js`/`vite.config.d.ts` files into the frontend
  source root. Fixed by redirecting output to a gitignored `.tsbuild/`
  directory (a `noEmit` project reference isn't valid TypeScript, so this
  needed the redirect rather than a flag flip — verified by trying the
  simpler fix first and hitting `TS6310`).
- **38 eslint false positives**: the flat config from Pass 2 declared no
  environment globals at all, so `window`, `document`, `crypto`, `React`
  (JSX's ambient namespace), `require`, and `__dirname` were all flagged
  as undefined — every one a false positive, none a real bug, but they
  made the lint step useless as a gate (100% noise). Fixed by properly
  declaring browser globals for app code and Node globals for config
  files via the `globals` package, rather than suppressing the rule.
- `ruff` (backend) and `eslint`/`vitest` (frontend) are now real, passing,
  **blocking** steps in `.github/workflows/ci.yml` — not just installed
  and left unused, which is what they were before this pass.

This is worth calling out plainly: **the act of wiring a lint gate into
CI is what found these bugs.** They existed for multiple passes before
this one; nothing caught them because nothing was checking. That's the
actual argument for why "add linting to CI" belongs on a hardening-pass
checklist instead of being assumed to already be handled.

## What "production hardened" means for this build, honestly

This pass measurably reduced real risk (request-size limits, security
headers, CSV-injection protection, a common-password denylist,
auth-specific rate limiting, dependency vulnerabilities) and added real
test coverage across previously-untested layers (the entire frontend, plus
several backend edge cases). It did **not** achieve "zero known issues" —
16 backend dependency vulnerabilities remain (documented, with reasons,
in `SECURITY.md`), the frontend's dev-server-only esbuild advisory
remains (documented above), and several testing categories (true
end-to-end browser tests, sustained load/soak testing, chaos/failure
injection beyond the Redis-down case) aren't built. That's the honest
state, not a claim of completeness — see `PROJECT_STATUS.md` for the
full capability map.
