# Deployment Guide

## Docker Compose

```bash
docker compose -f docker/docker-compose.yml --profile prod up --build            # SQLite
docker compose -f docker/docker-compose.yml --profile prod --profile prod-postgres up --build
```

The backend image installs CPU-only PyTorch and the model-serving extras. Weights
download on first use into the `model_cache` volume, so only the first request per model
is slow. To serve your own fine-tuned sentiment model, train it
(`python scripts/train_sentiment.py`); compose mounts `artifacts/models/` read-only.

## Single-container hosts (Render, Railway, Cloud Run, HF Spaces)

Point the platform at `docker/Dockerfile`. The container listens on `$PORT` (default
8000) and runs one worker. Give it **at least 2GB of RAM**, or set
`MAX_LOADED_MODELS=2`. Each loaded transformer takes 0.3–1.1GB.

## Kubernetes

Manifests are in `deployment/k8s/` (namespace, ConfigMap, Secret, backend Deployment +
Service + PVC, frontend, Redis, Ingress):

```bash
kubectl apply -f deployment/k8s/
```

Backend pods request 3Gi and are limited to 5Gi, sized for four resident models. Lower
`MAX_LOADED_MODELS` in the ConfigMap before lowering the limits. The backend PVC is
`ReadWriteOnce`, which suits one replica on SQLite; run multiple replicas only with
Postgres.

## Environment

| Variable | Purpose |
|---|---|
| `ENVIRONMENT=production` | Activates `ProductionSettings`; the app refuses to start without an explicit `SECRET_KEY` |
| `SECRET_KEY` | JWT signing key, injected from a secrets manager |
| `DATABASE_URL` | e.g. `postgresql://user:pass@host/db` |
| `REDIS_URL` | Cache and rate-limit store; falls back to in-memory if unreachable |
| `ALLOWED_ORIGINS` | JSON list of frontend origins |
| `MODEL_CACHE_DIR` | Where Hugging Face weights are cached |
| `MAX_LOADED_MODELS` | LRU cap on models held in memory (default 4) |
| `EMBEDDING_ENCODER` | `dense` (MiniLM) or `tfidf` for the dataset vector index |
| `WEB_CONCURRENCY` | uvicorn workers. Each worker loads its own copy of every model, so prefer more replicas over more workers |

## Scaling notes

The API holds no session state and opens one DB session per request, so it scales
horizontally behind a load balancer without sticky sessions. Model memory is per
process, so scale with replicas. Dataset vector indices are in-memory per process:
with several replicas, call `/embeddings/build` through each one, or move the index
to pgvector.
