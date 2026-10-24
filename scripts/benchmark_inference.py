"""
Latency / throughput / accuracy benchmark: FP32 vs dynamic INT8 quantization.

    python scripts/benchmark_inference.py                     # local fine-tuned model if present
    python scripts/benchmark_inference.py --model distilbert/distilbert-base-uncased-finetuned-sst-2-english

Dynamic quantization (torch.ao.quantization.quantize_dynamic) converts every
nn.Linear's weights to int8 ahead of time and quantizes activations on the
fly — no calibration data, no retraining. It's the cheapest CPU speed-up
for transformer encoders, so the question worth measuring is what it costs
in accuracy. Accuracy is measured on the full SST-2 validation split.

Writes benchmarks/results.json and benchmarks/results.md.
"""

import argparse
import json
import os
import platform
import statistics
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch  # noqa: E402
from transformers import AutoModelForSequenceClassification, AutoTokenizer  # noqa: E402

LOCAL_CHECKPOINT = "artifacts/models/distilbert-sst2"
PUBLIC_CHECKPOINT = "distilbert/distilbert-base-uncased-finetuned-sst-2-english"


def model_size_mb(model) -> float:
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "m.pt")
        torch.save(model.state_dict(), path)
        return os.path.getsize(path) / 1e6


def latency_ms(model, tokenizer, texts, batch_size, warmup=5, iters=50):
    batches = [texts[i : i + batch_size] for i in range(0, len(texts), batch_size)]
    timings = []
    with torch.inference_mode():
        for i in range(warmup + iters):
            batch = batches[i % len(batches)]
            enc = tokenizer(batch, return_tensors="pt", padding=True, truncation=True, max_length=128)
            start = time.perf_counter()
            model(**enc)
            if i >= warmup:
                timings.append((time.perf_counter() - start) * 1000)
    timings.sort()
    p50 = statistics.median(timings)
    p95 = timings[int(0.95 * (len(timings) - 1))]
    return p50, p95, batch_size / (p50 / 1000)


def accuracy(model, tokenizer, sentences, labels, batch_size=64):
    correct = 0
    label_names = [model.config.id2label[i].upper() for i in range(model.config.num_labels)]
    with torch.inference_mode():
        for i in range(0, len(sentences), batch_size):
            enc = tokenizer(sentences[i : i + batch_size], return_tensors="pt", padding=True, truncation=True, max_length=128)
            preds = model(**enc).logits.argmax(-1).tolist()
            correct += sum(label_names[p] == gold for p, gold in zip(preds, labels[i : i + batch_size]))
    return correct / len(sentences)


def main() -> None:
    parser = argparse.ArgumentParser()
    default = LOCAL_CHECKPOINT if os.path.isfile(os.path.join(LOCAL_CHECKPOINT, "config.json")) else PUBLIC_CHECKPOINT
    parser.add_argument("--model", default=default)
    parser.add_argument("--threads", type=int, default=torch.get_num_threads())
    parser.add_argument("--out-dir", default="benchmarks")
    args = parser.parse_args()
    torch.set_num_threads(args.threads)

    from datasets import load_dataset

    val = load_dataset("stanfordnlp/sst2", split="validation")
    names = val.features["label"].names
    sentences = list(val["sentence"])
    gold = [names[label].upper() for label in val["label"]]

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    fp32 = AutoModelForSequenceClassification.from_pretrained(args.model).eval()
    int8 = torch.ao.quantization.quantize_dynamic(
        AutoModelForSequenceClassification.from_pretrained(args.model).eval(), {torch.nn.Linear}, dtype=torch.qint8
    )

    rows = []
    for name, model in (("fp32", fp32), ("int8-dynamic", int8)):
        b1 = latency_ms(model, tokenizer, sentences, batch_size=1)
        b32 = latency_ms(model, tokenizer, sentences, batch_size=32, iters=20)
        rows.append(
            {
                "variant": name,
                "size_mb": round(model_size_mb(model), 1),
                "p50_ms_batch1": round(b1[0], 2),
                "p95_ms_batch1": round(b1[1], 2),
                "throughput_batch32": round(b32[2], 1),
                "sst2_val_accuracy": round(accuracy(model, tokenizer, sentences, gold), 4),
            }
        )
        print(rows[-1], flush=True)

    env = {
        "model": os.path.basename(os.path.normpath(args.model)),
        "cpu": platform.processor() or platform.machine(),
        "threads": args.threads,
        "torch": torch.__version__,
        "python": platform.python_version(),
    }
    os.makedirs(args.out_dir, exist_ok=True)
    with open(os.path.join(args.out_dir, "results.json"), "w") as f:
        json.dump({"environment": env, "results": rows}, f, indent=2)

    base, quant = rows
    lines = [
        "# Inference benchmark: FP32 vs dynamic INT8",
        "",
        f"Model `{env['model']}` · {env['cpu']} · {env['threads']} threads · torch {env['torch']}",
        "",
        "| Variant | Size (MB) | p50 latency, batch 1 (ms) | p95 latency, batch 1 (ms) | Throughput, batch 32 (texts/s) | SST-2 val accuracy |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['variant']} | {r['size_mb']} | {r['p50_ms_batch1']} | {r['p95_ms_batch1']} | "
            f"{r['throughput_batch32']} | {r['sst2_val_accuracy']:.2%} |"
        )
    lines += [
        "",
        f"INT8 is **{base['size_mb'] / quant['size_mb']:.1f}× smaller**, "
        f"**{base['p50_ms_batch1'] / quant['p50_ms_batch1']:.2f}× faster** at batch 1 and "
        f"**{quant['throughput_batch32'] / base['throughput_batch32']:.2f}×** the batch-32 throughput, for a "
        f"**{(base['sst2_val_accuracy'] - quant['sst2_val_accuracy']) * 100:+.2f} pt** accuracy change "
        f"(positive = accuracy lost).",
        "",
        "Reproduce: `python scripts/benchmark_inference.py`",
    ]
    with open(os.path.join(args.out_dir, "results.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
