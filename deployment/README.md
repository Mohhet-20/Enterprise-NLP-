# Deployment

Placeholder for future deployment configs (Kubernetes manifests, Terraform,
cloud-provider-specific IaC, CI/CD pipeline definitions).

Not implemented in the architecture-skeleton stage — the app is
containerized (see `../docker/`) and stateless by design (no in-memory
session state, DB access via short-lived per-request sessions), so it's
ready to run behind a load balancer / orchestrator once those configs are
added.
