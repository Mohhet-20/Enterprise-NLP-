"""Build the hosted public demo's showcase (run once, at image build time, by deploy/demo/Dockerfile).

Drives the real API in-process, as an administrator created for the build only (random password, locked again by
scripts/demo_start.py), and leaves under NLP_DEMO_ROOT (default /tmp/nlp-demo):

* ``nlp_platform.db`` and ``evaluation_runs/`` - evaluations of the fine-tuned DistilBERT and the lexicon baseline on
  the 48-sentence challenge set and the 872-sentence SST-2 validation split; the model registered and taken through
  approval -> production -> deployed -> champion; and a 200-sentence dataset uploaded and evaluated.

Expects the serving environment the image sets (SENTIMENT_CHECKPOINT_DIR, SST2_VALIDATION_FILE, SERVED_TASKS, ...).
"""

import csv
import io
import json
import os
import random
import secrets
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO_ROOT = Path(os.environ.get("NLP_DEMO_ROOT", "/tmp/nlp-demo"))
DATASET_ROWS = 200


def main() -> int:
    if DEMO_ROOT.exists():
        shutil.rmtree(DEMO_ROOT)
    (DEMO_ROOT / "evaluation_runs").mkdir(parents=True)
    os.environ.update({
        "ENVIRONMENT": "production",
        "SECRET_KEY": secrets.token_urlsafe(48),  # build-only; tokens issued here are never used again
        "DATABASE_URL": f"sqlite:///{(DEMO_ROOT / 'nlp_platform.db').as_posix()}",
        "EVALUATION_RUNS_DIR": str(DEMO_ROOT / "evaluation_runs"),
        "EXPERIMENTS_DIR": str(DEMO_ROOT / "experiments"),
        "RATE_LIMIT_REQUESTS_PER_MINUTE": "100000",
        "LOG_LEVEL": "WARNING",
    })
    sys.path.insert(0, str(ROOT))
    os.chdir(ROOT)

    from fastapi.testclient import TestClient

    from backend.auth.password import hash_password
    from backend.core.constants import UserRole
    from backend.database.session import SessionLocal, init_db
    from backend.main import app
    from backend.models.user import User
    from backend.repositories.user_repository import UserRepository
    from backend.services.auth_service import auth_service

    init_db()
    db = SessionLocal()
    try:
        builder = UserRepository(db).create(User(username="showcase-builder", email="builder@showcase.invalid",
                                                 hashed_password=hash_password(secrets.token_urlsafe(32)),
                                                 role=UserRole.ADMIN.value))
        token = auth_service.issue_tokens(db, builder).access_token
    finally:
        db.close()

    with TestClient(app) as c:
        c.headers["Authorization"] = f"Bearer {token}"

        def post(path: str, **kwargs) -> dict:
            res = c.post(f"/api/v1{path}", **kwargs)
            if res.status_code >= 300:
                raise SystemExit(f"[demo-build] POST {path} -> {res.status_code}: {res.text[:400]}")
            return res.json()

        runs = {}
        for model in ("lexicon_baseline", "served"):
            for eval_set in ("challenge_set", "sst2_validation"):
                run = post("/evaluation/run", json={"task": "sentiment_analysis", "model": model, "eval_set": eval_set})
                runs[(model, eval_set)] = run
                print(f"[demo-build] eval {run['model_name']:<22} {eval_set:<16} acc={run['accuracy']:.4f}", flush=True)

        served = runs[("served", "sst2_validation")]
        entry = post("/models", json={
            "name": served["model_name"], "task": "sentiment_analysis", "architecture": "distilbert",
            "version": "1.0.0", "model_name_or_path": served["model_name"], "evaluation_run_id": served["run_id"],
            "notes": f"Fine-tuned on SST-2 in this repository. SST-2 validation accuracy {served['accuracy']:.2%}.",
        })
        for step, body in (("approve", None), ("promote", {"stage": "production"}), ("deploy", None), ("set-champion", None)):
            post(f"/models/{entry['id']}/{step}", json=body)
        print(f"[demo-build] model {entry['name']} -> approved, production, deployed, champion", flush=True)

        # Also loads MiniLM into MODEL_CACHE_DIR, so the server never downloads at runtime (it runs offline).
        sim = post("/predict", json={"task": "semantic_similarity", "text": "The battery lasts all day.",
                                     "text_pair": "It holds a charge from morning to night."})
        print(f"[demo-build] similarity warm-up: {sim['results'][0]['score']:.3f}", flush=True)

        rows = json.loads(Path(os.environ["SST2_VALIDATION_FILE"]).read_text(encoding="utf-8"))
        sample = random.Random(7).sample(rows, DATASET_ROWS)
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["text", "label"])
        for row in sample:
            writer.writerow([row["sentence"].strip(), row["label"].upper()])
        dataset = post("/datasets", json={
            "name": "movie-reviews-sample", "task": "sentiment_analysis",
            "description": f"{DATASET_ROWS} sentences sampled from SST-2 validation", "label_set": ["NEGATIVE", "POSITIVE"],
        })
        post(f"/datasets/{dataset['id']}/upload", files={"file": ("movie_reviews.csv", buffer.getvalue(), "text/csv")})
        run = post("/evaluation/run", json={"task": "sentiment_analysis", "dataset_id": dataset["id"]})
        print(f"[demo-build] dataset {dataset['name']} ({DATASET_ROWS} rows) acc={run['accuracy']:.4f}", flush=True)

    print(f"[demo-build] showcase ready in {DEMO_ROOT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
