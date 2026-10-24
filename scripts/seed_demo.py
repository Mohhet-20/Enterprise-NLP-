"""
Populate a running instance with demo content through the public API:
evaluation runs (served model vs lexicon baseline, on the challenge set and
SST-2 validation), a registered + approved + deployed model, and an uploaded
dataset evaluated by the served model.

    uvicorn backend.main:app --port 8000
    python scripts/seed_demo.py

Uses the dev-seeded admin account by default.
"""

import argparse
import csv
import io

import httpx


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/api/v1")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default="ChangeMe123!")
    parser.add_argument("--dataset-rows", type=int, default=200)
    args = parser.parse_args()

    login = httpx.post(f"{args.base_url}/auth/login", json={"username": args.username, "password": args.password})
    login.raise_for_status()
    api = httpx.Client(
        base_url=args.base_url,
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
        timeout=600,
    )

    def post(path: str, **kwargs) -> dict:
        response = api.post(path, **kwargs)
        response.raise_for_status()
        return response.json()

    runs = {}
    for model in ("lexicon_baseline", "served"):
        for eval_set in ("challenge_set", "sst2_validation"):
            run = post("/evaluation/run", json={"task": "sentiment_analysis", "model": model, "eval_set": eval_set})
            runs[(model, eval_set)] = run
            print(f"eval  {run['model_name']:<22} {eval_set:<16} acc={run['accuracy']:.4f} ece={run.get('ece')}")

    served = runs[("served", "sst2_validation")]
    entry = post(
        "/models",
        json={
            "name": served["model_name"],
            "task": "sentiment_analysis",
            "architecture": "distilbert",
            "version": "1.0.0",
            "model_name_or_path": served["model_name"],
            "evaluation_run_id": served["run_id"],
            "notes": f"SST-2 validation accuracy {served['accuracy']:.2%}.",
        },
    )
    post(f"/models/{entry['id']}/approve")
    post(f"/models/{entry['id']}/promote", json={"stage": "production"})
    post(f"/models/{entry['id']}/deploy")
    post(f"/models/{entry['id']}/set-champion")
    print(f"model {entry['name']} registered -> approved -> production -> deployed -> champion")

    from datasets import load_dataset

    split = load_dataset("stanfordnlp/sst2", split="validation").shuffle(seed=7).select(range(args.dataset_rows))
    names = split.features["label"].names
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["text", "label"])
    for row in split:
        writer.writerow([row["sentence"].strip(), names[row["label"]].upper()])

    dataset = post(
        "/datasets",
        json={
            "name": "movie-reviews-sample",
            "task": "sentiment_analysis",
            "description": f"{args.dataset_rows} sentences sampled from SST-2 validation",
            "label_set": ["NEGATIVE", "POSITIVE"],
        },
    )
    post(f"/datasets/{dataset['id']}/upload", files={"file": ("movie_reviews.csv", buffer.getvalue(), "text/csv")})
    run = post("/evaluation/run", json={"task": "sentiment_analysis", "dataset_id": dataset["id"]})
    print(f"data  {dataset['name']} ({args.dataset_rows} rows) acc={run['accuracy']:.4f}")


if __name__ == "__main__":
    main()
