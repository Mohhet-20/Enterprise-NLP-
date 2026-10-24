# Deployment

- `k8s/` — Kubernetes manifests (namespace, ConfigMap, Secret, backend, frontend, Redis,
  Ingress). Apply with `kubectl apply -f deployment/k8s/`.
- `../docker/` — backend and frontend Dockerfiles, nginx config, and a Compose file with
  `dev`, `prod` and `prod-postgres` profiles.

See `../docs/deployment-guide.md` for sizing, environment variables and scaling notes.
