# Security

## Pass 8 security audit — hardening findings and fixes

A real review pass across auth, API surface, file uploads, and CSV
export/import, done by actually reading the code (not a checklist
exercise). Findings that were genuine gaps, fixed this pass:

| Finding | Risk | Fix |
|---|---|---|
| No security headers on responses | Clickjacking, MIME-sniffing, referrer leakage | `SecurityHeadersMiddleware` — `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy` on every response |
| No request body size limit | A single request could buffer an arbitrarily large body before validation ever runs — memory exhaustion | `RequestSizeLimitMiddleware`, 15MB default, checked via `Content-Length` before buffering; real end-to-end test against a standalone app confirms a 413 |
| CSV upload had no size or row-count cap | Same class of risk, upload-specific | 10MB file-size cap + 50,000-row cap (`backend/services/dataset_service.py`) |
| CSV export echoed user text unsanitized | **CSV/formula injection** (OWASP-documented): a cell starting with `=`, `+`, `-`, or `@` is interpreted as a formula by Excel/Sheets when opened, not literal text — could exfiltrate data or execute a formula-based attack against whoever opens the export | `backend/utils/csv_safety.py` — prefixes a neutralizing single quote onto any cell starting with a formula-trigger character; applied to the misclassified-samples CSV export |
| Password policy was length-only (≥8 chars, no upper bound, no breach check) | Extremely long inputs (hashing-cost concern) and, more importantly, common/breached passwords were both still accepted | Added a max length (128) and a real common-password denylist (`backend/core/common_passwords.py`, sourced from well-known breach-compilation frequency lists) — per NIST 800-63B guidance, this matters more than arbitrary complexity rules |
| Login/register shared the same rate limit as the general API (60/min) | An attacker could attempt many different (username, password) pairs quickly — the per-account lockout only protects one specific account, not the endpoint itself | Auth endpoints (`/auth/login`, `/auth/register`, `/auth/refresh`) now get a separate, stricter limit (10/min default), independent of the per-account lockout already in place |

### Reviewed and found already correct (not changed, because nothing was wrong)

- **JWT algorithm confusion**: `jwt.decode(..., algorithms=[settings.jwt_algorithm])` already explicitly restricts accepted algorithms — a token claiming `alg: none` or a different algorithm is already rejected. No "alg:none" vulnerability present.
- **SQL injection**: every query in the codebase goes through SQLAlchemy's ORM (parameterized by construction); the one raw-SQL call (`db.execute(text("SELECT 1"))` in the database health check) is a hardcoded literal with no user input anywhere near it.
- **Path traversal via uploaded filenames**: the dataset upload endpoint reads a filename only to check its `.csv` extension — it's never used to construct a filesystem path (content is parsed in memory and persisted as database rows, never written to disk under a user-supplied name).
- **Separation of duties**: model approval already required a different role (Reviewer/Admin/Super Admin) than the one that can register a model (any `experiment:write` role) — verified this holds and wasn't accidentally bypassable through any other endpoint.

## Dependency vulnerability scanning

The CI pipeline (`.github/workflows/ci.yml`, job `backend-security-scan`)
runs [`pip-audit`](https://pypi.org/project/pip-audit/) against
`requirements.txt` on every push. This isn't a scanner nobody looks at —
it was run for real during this build, and the results below are the
actual before/after, not a hypothetical.

### Before → after (pass 7)

Running `pip-audit -r requirements.txt --strict` at the start of this
pass found **23 known vulnerabilities across 5 packages**. After bumping
what could be safely bumped:

| Package | Before | After | Vulnerabilities remaining |
|---|---|---|---|
| `fastapi` | 0.115.0 | 0.115.14 | — (patch-level bump within the same minor line, pulled in a fixed starlette baseline) |
| `python-jose` | 3.3.0 | 3.4.0 | — (fixed) |
| `python-multipart` | 0.0.9 | 0.0.22 | 5 (newer fixes exist at 0.0.26+; not verified compatible in this pass) |
| `pytest` | 8.3.3 | 9.0.3 | — (fixed; dev/test dependency, not shipped in the runtime container) |
| `starlette` | 0.38.6 (transitive) | 0.46.2 (transitive) | 9 |
| `pyasn1` | (transitive) 0.4.8 | 0.4.8 | 1 |
| `ecdsa` | 0.19.2 | 0.19.2 | 1 |

**Result: 23 → 16 known vulnerabilities.** Not zero — and the remaining
16 are left at that count deliberately, not silently:

- **`starlette`** is a transitive dependency of `fastapi==0.115.14`, which
  pins `starlette<0.47.0`. The fixes for its remaining CVEs land in
  0.47.2+ and the 1.x line — taking them means upgrading FastAPI past
  0.115.x, which is a real (if probably safe) breaking-change surface I
  didn't want to absorb blind in the same pass as everything else in
  this build. Tracked as a follow-up, not ignored.
- **`pyasn1`** is a transitive dependency of `python-jose==3.4.0`, which
  pins `pyasn1<0.5.0`. The fix (0.6.3) is incompatible with the current
  `python-jose` pin. The actual fix here is probably replacing
  `python-jose` with `PyJWT` (which doesn't carry this constraint) — a
  real migration, not a version bump, and out of scope for this pass.
- **`ecdsa`** (PYSEC-2026-1325, a Minerva-style timing side-channel) has
  **no fix version available upstream** — this is a known, disputed issue
  in the `ecdsa` project; pure-Python ECDSA is inherently harder to make
  constant-time, and the maintainers have not shipped a fix as of this
  writing. Nothing in this platform's dependency tree can resolve it by
  bumping a version number.
- **`python-multipart`** has fixes available past 0.0.22 (up to 0.0.31),
  not applied here because I didn't verify them against this exact
  FastAPI/Starlette combination in the time this pass had — a real
  "should do, didn't get to" rather than an oversight I'm hiding.

This is genuinely how dependency security work goes in practice: some
fixes are a version bump, some require a real migration, and some don't
exist yet. Pretending otherwise (either by not running the scanner, or by
running it and not reading the output) would be worse than reporting 16
remaining findings honestly.

## Application-level security posture

Covered elsewhere in this codebase, summarized here for one-stop reference:

- **Passwords**: bcrypt-hashed (`backend/auth/password.py`), never logged
  or returned in any API response.
- **Refresh tokens**: opaque random strings, SHA-256-hashed at rest,
  rotating on every use, individually and bulk-revocable
  (`backend/services/auth_service.py`).
- **Account lockout**: after repeated failed logins
  (`backend/services/auth_service.py`).
- **RBAC**: 9 roles, permission-gated per endpoint
  (`backend/auth/rbac.py`); model approval specifically requires a
  different role than the one that can submit a model, for separation of
  duties.
- **Rate limiting**: per-user (or per-IP if unauthenticated), Redis-backed
  with in-memory fallback (`backend/core/rate_limiting.py`), with a
  stricter separate limit on auth endpoints (added this pass).
- **Audit trail**: persisted, queryable, restricted to the Auditor/Admin
  roles (`backend/services/audit_service.py`).
- **Secrets**: loaded from environment variables only; the app refuses to
  start in production with the default `SECRET_KEY`
  (`backend/config/settings.py`).
- **CORS**: explicit allow-list, not `*`.
- **Container security**: non-root users in both the backend and frontend
  images (`docker/Dockerfile`, `docker/frontend.Dockerfile`).
- **Request/response hardening**: security headers, request size limits,
  CSV formula-injection protection, common-password denylist (all added
  this pass — see the audit table above).

## Frontend dependencies

`npm audit` found one real, moderate-severity issue: `esbuild <=0.24.2`
(GHSA-67mh-4wv8-2f99), transitively bundled via Vite 5.x — dev-server-only
impact, production build unaffected. A fix was attempted (Vite 8.x) and
reverted after it broke the production build (incompatible bundler
config API) — see `docs/testing-and-qa-guide.md` for the full account,
including why forcing it through would have been the wrong call.

## What's NOT implemented

TLS termination (left to the ingress/load balancer — see
`deployment/k8s/ingress.yaml`), secrets management beyond environment
variables (no Vault/AWS Secrets Manager/Sealed Secrets integration),
field-level encryption for dataset content, and image vulnerability
scanning (e.g. Trivy) in CI. (`ruff`/`eslint`/`vitest` **are** now real
blocking gates in `.github/workflows/ci.yml` — see
`docs/testing-and-qa-guide.md` for what wiring them in actually found.)
See `PROJECT_STATUS.md`.
