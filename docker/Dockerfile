# syntax=docker/dockerfile:1
#
# Multi-stage build: the `builder` stage has the compiler toolchain needed
# to build native wheels (bcrypt, etc.); the `runtime` stage copies only
# the installed packages out of it, so the final image never carries a
# C compiler or apt package cache. Runs as a non-root user — a container
# escape in a root-owned process is a much worse day than one in a
# process that can't write outside its own home directory.

# --- Stage 1: build dependencies ---
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-ml.txt ./
# CPU-only torch: ~200MB wheel instead of ~2GB of CUDA libraries. For a GPU
# image, swap the index URL for the matching CUDA one.
RUN pip install --no-cache-dir --user torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu     && pip install --no-cache-dir --user -r requirements-ml.txt

# --- Stage 2: slim runtime image ---
FROM python:3.11-slim AS runtime

RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

WORKDIR /app

COPY --from=builder /root/.local /home/appuser/.local
COPY backend ./backend

ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ENVIRONMENT=production

# Mount a volume at /app/.model_cache to keep downloaded weights across
# restarts; a locally fine-tuned checkpoint can be mounted at
# /app/artifacts/models/distilbert-sst2.
RUN mkdir -p /app/.model_cache /app/artifacts && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Hits the real /health endpoint (backend/api/v1/endpoints/health.py) —
# not a fixed "container is running" check, an actual app-level check.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/v1/health').status == 200 else 1)"

# 2 workers by default — override via `docker run ... --workers N` or the
# compose command for a given environment's actual capacity.
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
