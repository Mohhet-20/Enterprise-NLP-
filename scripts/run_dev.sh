#!/usr/bin/env bash
# Convenience script for local development.
set -euo pipefail

if [ ! -f .env ]; then
  echo "No .env found — copying .env.example"
  cp .env.example .env
fi

export ENVIRONMENT="${ENVIRONMENT:-development}"
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
