# Deployment Guide

## Container

```bash
docker compose -f docker/docker-compose.yml up --build
```

Builds `docker/Dockerfile` and serves the API on port 8000.

## Environment

Set these via real environment variables (not `.env`) in any deployed
environment:

- `ENVIRONMENT=production` — activates `ProductionSettings`, which requires
  `SECRET_KEY` to be explicitly set (the app refuses to start otherwise).
- `SECRET_KEY` — a securely generated random string, injected via your
  platform's secrets manager, never committed to source.
- `DATABASE_URL` — a production database connection string (Postgres
  recommended over the SQLite dev default).
- `ALLOWED_ORIGINS` — your real frontend origin(s).

## Statelessness

The API holds no in-memory session state and opens/closes a DB session per
request (`backend/database/session.py`), so it can be scaled horizontally
behind a load balancer without sticky sessions.

## Not yet included

Kubernetes manifests, Terraform/IaC, and CI/CD pipeline definitions are
intentionally out of scope for the architecture-skeleton stage — see
`deployment/README.md`.
