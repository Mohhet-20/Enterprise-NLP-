# Inference benchmark: FP32 vs dynamic INT8

Model `distilbert-sst2` · Intel Core Ultra 9 185H laptop · 16 threads · torch 2.14.1+cpu · median of 5 alternating rounds; tokenisation excluded

| Variant | Size (MB) | p50 latency, batch 1 (ms) | p95 latency, batch 1 (ms) | Throughput, batch 32 (texts/s, min–max) | SST-2 val accuracy |
|---|---|---|---|---|---|
| fp32 | 267.9 | 18.54 | 24.7 | 41.7 (40.0–96.7) | 90.37% |
| int8-dynamic | 138.7 | 23.68 | 41.72 | 122.6 (100.5–240.5) | 88.99% |

INT8 is 1.9× smaller, 1.28× slower at batch 1, has 2.94× higher batch-32 throughput, and loses 1.38 accuracy points.

Reproduce: `python scripts/benchmark_inference.py`
