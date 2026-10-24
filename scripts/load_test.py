"""
A real, if modest, load test: spins up real concurrent client connections
against a live uvicorn instance and measures actual latency percentiles
and throughput — not simulated or estimated numbers. Run manually (not
part of the pytest suite, which shouldn't depend on a running server):

    uvicorn backend.main:app --host 127.0.0.1 --port 8300 &
    python scripts/load_test.py --base-url http://127.0.0.1:8300 --concurrency 20 --requests 200
"""

import argparse
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx


def _timed_request(client: httpx.Client, method: str, path: str, **kwargs) -> tuple[float, int]:
    start = time.perf_counter()
    response = client.request(method, path, **kwargs)
    elapsed_ms = (time.perf_counter() - start) * 1000
    return elapsed_ms, response.status_code


def run_load_test(base_url: str, concurrency: int, total_requests: int, path: str = "/api/v1/health") -> None:
    latencies: list[float] = []
    statuses: list[int] = []

    def worker(_: int) -> tuple[float, int]:
        with httpx.Client(base_url=base_url, timeout=10.0) as client:
            return _timed_request(client, "GET", path)

    print(f"Load testing {base_url}{path} — {total_requests} requests at concurrency {concurrency}")
    wall_start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [pool.submit(worker, i) for i in range(total_requests)]
        for future in as_completed(futures):
            elapsed_ms, status = future.result()
            latencies.append(elapsed_ms)
            statuses.append(status)

    wall_elapsed = time.perf_counter() - wall_start
    latencies.sort()

    def percentile(p: float) -> float:
        idx = min(len(latencies) - 1, int(len(latencies) * p))
        return latencies[idx]

    success_count = sum(1 for s in statuses if s == 200)

    print()
    print(f"Total requests:      {total_requests}")
    print(f"Successful (200):    {success_count} ({100 * success_count / total_requests:.1f}%)")
    print(f"Wall time:           {wall_elapsed:.2f}s")
    print(f"Throughput:          {total_requests / wall_elapsed:.1f} req/s")
    print(f"Latency min:         {min(latencies):.1f}ms")
    print(f"Latency p50:         {percentile(0.50):.1f}ms")
    print(f"Latency p95:         {percentile(0.95):.1f}ms")
    print(f"Latency p99:         {percentile(0.99):.1f}ms")
    print(f"Latency max:         {max(latencies):.1f}ms")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--concurrency", type=int, default=20)
    parser.add_argument("--requests", type=int, default=200)
    parser.add_argument("--path", default="/api/v1/health")
    args = parser.parse_args()

    run_load_test(args.base_url, args.concurrency, args.requests, args.path)
