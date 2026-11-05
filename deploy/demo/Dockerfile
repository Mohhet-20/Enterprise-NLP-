# syntax=docker/dockerfile:1
# Hosted public demo (render.yaml), sized for a 512 MB free instance. Build context: the repository root.
#
# Serves the fine-tuned DistilBERT sentiment model (with Integrated Gradients explanations) and MiniLM semantic
# similarity / embeddings; the other five tasks are listed by GET /tasks as not served here (they need ~2-3 GB).
# Everything heavy happens at build time: the fine-tuned model is downloaded from the GitHub release and verified,
# MiniLM is cached, SST-2 validation is exported to JSON, and scripts/demo_build.py runs the evaluations and the
# model-registry lifecycle through the API. scripts/demo_start.py copies that showcase fresh on every start.
# For a full deployment use docker/Dockerfile.

FROM python:3.11-slim AS deps
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
COPY requirements.txt /tmp/requirements.txt
# CPU-only torch; transformers/sentence-transformers at the versions in requirements-ml.txt. No `datasets` or
# `accelerate` at runtime (the SST-2 split is read from a JSON export).
RUN pip install --user torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu \
    && pip install --user -r /tmp/requirements.txt transformers==4.46.3 sentence-transformers==3.3.1

FROM deps AS showcase
RUN pip install --user datasets==3.1.0
WORKDIR /app
COPY backend ./backend
COPY scripts/fetch_model.py scripts/export_sst2.py scripts/demo_build.py ./scripts/
ARG MODEL_URL=https://github.com/Mohhet-20/Enterprise-NLP-/releases/download/v1.1.0/distilbert-sst2.zip
ARG MODEL_SHA256=9610ca7bdb568c055d7293505e2916118f05880349260ac72e7533d40d3ae756
RUN python scripts/fetch_model.py "$MODEL_URL" "$MODEL_SHA256" /app/models/distilbert-sst2 \
    && python scripts/export_sst2.py /app/data/sst2_validation.json
ENV SENTIMENT_CHECKPOINT_DIR=/app/models/distilbert-sst2 MODEL_CACHE_DIR=/app/model-cache \
    SST2_VALIDATION_FILE=/app/data/sst2_validation.json \
    SERVED_TASKS=sentiment_analysis,semantic_similarity,text_embeddings EMBEDDING_ENCODER=dense \
    OMP_NUM_THREADS=1 TOKENIZERS_PARALLELISM=false PYTHONUNBUFFERED=1
RUN python scripts/demo_build.py && mkdir -p /app/showcase && cp -a /tmp/nlp-demo/. /app/showcase/

FROM python:3.11-slim AS runtime
RUN groupadd --gid 1000 appuser && useradd --uid 1000 --gid appuser --create-home appuser
WORKDIR /app
COPY --from=deps /root/.local /home/appuser/.local
COPY backend ./backend
COPY scripts/demo_start.py ./scripts/
COPY --from=showcase /app/models ./models
COPY --from=showcase /app/model-cache ./model-cache
COPY --from=showcase /app/data ./data
COPY --from=showcase /app/showcase ./showcase
ENV PATH=/home/appuser/.local/bin:$PATH PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    SENTIMENT_CHECKPOINT_DIR=/app/models/distilbert-sst2 MODEL_CACHE_DIR=/app/model-cache \
    SST2_VALIDATION_FILE=/app/data/sst2_validation.json \
    SERVED_TASKS=sentiment_analysis,semantic_similarity,text_embeddings EMBEDDING_ENCODER=dense \
    MAX_LOADED_MODELS=2 PRELOAD_MODELS=true MAX_SEQUENCE_LENGTH=128 EVAL_BATCH_SIZE=8 \
    EXPLAIN_BATCH_SIZE=4 MAX_EXPLAIN_STEPS=16 MAX_SERVED_EVAL_EXAMPLES=100 \
    HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 TOKENIZERS_PARALLELISM=false \
    MALLOC_ARENA_MAX=2 NLP_SHOWCASE_DIR=/app/showcase NLP_DEMO_ROOT=/tmp/nlp-demo
USER appuser
EXPOSE 8000
CMD ["python", "scripts/demo_start.py"]
