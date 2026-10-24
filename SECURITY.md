# Security

## Reporting a vulnerability

Please open a private security advisory on the repository rather than a public issue.

## Controls

| Area | Control | Where |
|---|---|---|
| Passwords | bcrypt hashing; 8–128 chars; common-password denylist (NIST 800-63B) | `backend/auth/password.py`, `backend/core/common_passwords.py` |
| Access tokens | HS256 JWT via PyJWT; algorithm allow-list (rejects `alg: none`); `exp` and `sub` required | `backend/auth/jwt_handler.py` |
| Refresh tokens | Opaque random strings, SHA-256 hashed at rest, rotated on every use, individually and bulk revocable | `backend/services/auth_service.py` |
| Brute force | Per-account lockout after repeated failures, plus a stricter 10/min rate limit on login/register/refresh | `backend/services/auth_service.py`, `backend/core/rate_limiting.py` |
| Authorisation | 9-role RBAC checked per endpoint; model approval requires a different role from the one that registers it (separation of duties) | `backend/auth/rbac.py` |
| Rate limiting | Per user (or per IP when anonymous), Redis-backed with in-memory fallback | `backend/core/rate_limiting.py` |
| Request limits | 15MB body cap checked from `Content-Length` before buffering; 10MB / 50k-row CSV cap; 64 texts per batch inference call | `backend/core/security_headers.py`, `backend/services/dataset_service.py`, `backend/config/settings.py` |
| Response headers | `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy` | `backend/core/security_headers.py` |
| CSV injection | Cells starting with `= + - @` are neutralised in every CSV export | `backend/utils/csv_safety.py` |
| Path traversal | Evaluation run ids must parse as UUIDs before touching the filesystem; uploaded filenames are never used as paths | `backend/evaluation/evaluation_store.py` |
| Information leakage | Local checkpoint paths are reduced to a directory name in every API response | `backend/plugins/plugin_registry.py` |
| SQL injection | All queries go through the SQLAlchemy ORM; the one raw statement (`SELECT 1` health probe) takes no input | — |
| Audit trail | Persisted, queryable, restricted to Auditor/Admin roles | `backend/services/audit_service.py` |
| Secrets | Environment variables only; the app refuses to start in production with the default `SECRET_KEY` | `backend/config/settings.py` |
| CORS | Explicit origin allow-list | `backend/config/settings.py` |
| Containers | Non-root users in backend and frontend images | `docker/` |

All of the above are covered by tests in `tests/test_security_hardening.py`,
`tests/test_auth.py`, `tests/test_rbac.py` and `tests/test_inference.py`.

## Dependency scanning

CI runs `pip-audit` on every push, and `npm audit` can be run locally in `frontend/`.

| Scope | Status |
|---|---|
| Backend (`requirements.txt`) | **0 known vulnerabilities** |
| Frontend production dependencies | **0 known vulnerabilities** |
| Frontend dev tooling | 3 moderate advisories, all in Tailwind CSS 3's PostCSS chain |

Getting the backend to zero took more than version bumps:

- **`python-jose` → `PyJWT`.** python-jose pins `pyasn1<0.5` and depends on `ecdsa`,
  which has an unfixed timing side-channel advisory. Neither could be resolved by
  upgrading, so the JWT layer was migrated (`backend/auth/jwt_handler.py`). The
  migration also tightened validation to require the `exp` and `sub` claims.
- **FastAPI 0.115 → 0.162**, which lifts the old `starlette<0.47` cap. Starlette is now
  pinned at 1.9.0 explicitly, so a resolver can never fall back to a vulnerable 0.x.
- **python-multipart 0.0.22 → 0.0.32.**

On the frontend, React Router 7 fixes an open-redirect advisory, and Vite 8 / Vitest 5
clear the esbuild dev-server and test-runner advisories.

**Remaining:** the 3 Tailwind 3 advisories affect only build-time CSS processing of the
project's own source; no user input reaches it. The fix is a Tailwind 4 migration
(CSS-first config, renamed utilities), which is tracked separately.

## Out of scope

TLS termination (handled by the ingress / load balancer), a secrets manager beyond
environment variables, field-level encryption of dataset content, and container image
scanning.
