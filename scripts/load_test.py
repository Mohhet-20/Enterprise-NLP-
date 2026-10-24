"""
Concurrent load test against a live uvicorn instance: latency percentiles
and throughput. Not part of pytest, because it needs a running server.

    uvicorn backend.main:app --host 127.0.0.1 --port 8000
    python scripts/load_test.py                                   # GET /health
    python scripts/load_test.py --predict --task sentiment_analysis --concurrency 8 --requests 200

`--predict` logs in first (default: the dev-seeded admin) and POSTs real
sentences to /predict. Start the server with a high
RATE_LIMIT_REQUESTS_PER_MINUTE for this, or the limiter (correctly) answers 429.
"""

import argparse
import itertools
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import httpx

SENTENCES = [
    "An absolute triumph of a film, moving and funny in equal measure.",
    "The pacing drags and the dialogue is painfully wooden.",
    "I didn't expect much, but it won me over by the end.",
    "Not the worst sequel, but nowhere near the original.",
    "Customer support resolved my issue in five minutes. Impressive.",
    "The battery died after two days and nobody answered my emails.",
]


def _login(base_url: str, username: str, password: str) -> str:
    response = httpx.post(f"{base_url}/api/v1/auth/login", json={"username": username, "password": password})
    response.raise_for_status()
    return response.json()["access_token"]


def run_load_test(
    base_url: str, concurrency: int, total_requests: int, path: str, token: Optional[str] = None, task: str = ""
) -> dict:
    latencies: list[float] = []
    statuses: list[int] = []
    texts = itertools.cycle(SENTENCES)
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    client = httpx.Client(base_url=base_url, timeout=60.0, headers=headers, limits=httpx.Limits(max_connections=concurrency))

    def worker(text: str) -> tuple[float, int]:
        start = time.perf_counter()
        if token:
            response = client.post(path, json={"task": task, "text": text})
        else:
            response = client.get(path)
        return (time.perf_counter() - start) * 1000, response.status_code

    if token:  # one warm-up call so the first-load cost isn't counted as latency
        worker(SENTENCES[0])

    method = "POST" if token else "GET"
    print(f"Load testing {method} {base_url}{path} — {total_requests} requests at concurrency {concurrency}")
    wall_start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [pool.submit(worker, next(texts)) for _ in range(total_requests)]
        for future in as_completed(futures):
            elapsed_ms, status = future.result()
            latencies.append(elapsed_ms)
            statuses.append(status)
    wall_elapsed = time.perf_counter() - wall_start
    client.close()

    latencies.sort()

    def percentile(p: float) -> float:
        return latencies[min(len(latencies) - 1, int(len(latencies) * p))]

    result = {
        "requests": total_requests,
        "concurrency": concurrency,
        "success_rate": sum(1 for s in statuses if s == 200) / total_requests,
        "throughput_rps": total_requests / wall_elapsed,
        "p50_ms": percentile(0.50),
        "p95_ms": percentile(0.95),
        "p99_ms": percentile(0.99),
    }
    print(f"Successful (200):    {result['success_rate']:.1%}")
    print(f"Throughput:          {result['throughput_rps']:.1f} req/s")
    print(f"Latency p50/p95/p99: {result['p50_ms']:.1f} / {result['p95_ms']:.1f} / {result['p99_ms']:.1f} ms")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--concurrency", type=int, default=20)
    parser.add_argument("--requests", type=int, default=200)
    parser.add_argument("--path", default=None)
    parser.add_argument("--predict", action="store_true", help="POST real sentences to /predict")
    parser.add_argument("--task", default="sentiment_analysis")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default="ChangeMe123!")
    args = parser.parse_args()

    if args.predict:
        token = _login(args.base_url, args.username, args.password)
        run_load_test(args.base_url, args.concurrency, args.requests, args.path or "/api/v1/predict", token, args.task)
    else:
        run_load_test(args.base_url, args.concurrency, args.requests, args.path or "/api/v1/health")
