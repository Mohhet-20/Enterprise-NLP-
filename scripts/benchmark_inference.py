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


def encode_batches(tokenizer, texts, batch_size, n_batches):
    """Tokenise up front so timings measure the model, not the tokenizer."""
    return [
        tokenizer(texts[i * batch_size : (i + 1) * batch_size], return_tensors="pt", padding=True, truncation=True, max_length=128)
        for i in range(n_batches)
    ]


def time_batches(model, batches) -> list[float]:
    with torch.inference_mode():
        model(**batches[0])  # warm-up
        timings = []
        for enc in batches:
            start = time.perf_counter()
            model(**enc)
            timings.append((time.perf_counter() - start) * 1000)
    return timings


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
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--cpu-label", default=None, help="human-readable CPU name for the report")
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

    singles = encode_batches(tokenizer, sentences, 1, 100)
    batches32 = encode_batches(tokenizer, sentences, 32, 10)
    variants = {"fp32": fp32, "int8-dynamic": int8}

    # Alternate variants across rounds so thermal / turbo drift on a laptop
    # hits both equally; report the median round.
    per_round = {name: {"p50": [], "p95": [], "tput": []} for name in variants}
    for _ in range(args.rounds):
        for name, model in variants.items():
            t1 = sorted(time_batches(model, singles))
            t32 = time_batches(model, batches32)
            per_round[name]["p50"].append(statistics.median(t1))
            per_round[name]["p95"].append(t1[int(0.95 * (len(t1) - 1))])
            per_round[name]["tput"].append(32 * len(t32) / (sum(t32) / 1000))

    rows = []
    for name, model in variants.items():
        r = per_round[name]
        rows.append(
            {
                "variant": name,
                "size_mb": round(model_size_mb(model), 1),
                "p50_ms_batch1": round(statistics.median(r["p50"]), 2),
                "p95_ms_batch1": round(statistics.median(r["p95"]), 2),
                "throughput_batch32": round(statistics.median(r["tput"]), 1),
                "throughput_batch32_range": [round(min(r["tput"]), 1), round(max(r["tput"]), 1)],
                "sst2_val_accuracy": round(accuracy(model, tokenizer, sentences, gold), 4),
            }
        )
        print(rows[-1], flush=True)

    env = {
        "model": os.path.basename(os.path.normpath(args.model)),
        "cpu": args.cpu_label or platform.processor() or platform.machine(),
        "threads": args.threads,
        "rounds": args.rounds,
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
        f"Model `{env['model']}` · {env['cpu']} · {env['threads']} threads · torch {env['torch']} · "
        f"median of {env['rounds']} alternating rounds; tokenisation excluded",
        "",
        "| Variant | Size (MB) | p50 latency, batch 1 (ms) | p95 latency, batch 1 (ms) | Throughput, batch 32 (texts/s, min–max) | SST-2 val accuracy |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['variant']} | {r['size_mb']} | {r['p50_ms_batch1']} | {r['p95_ms_batch1']} | "
            f"{r['throughput_batch32']} ({r['throughput_batch32_range'][0]}–{r['throughput_batch32_range'][1]}) | "
            f"{r['sst2_val_accuracy']:.2%} |"
        )
    def ratio(new: float, old: float, better: str, worse: str) -> str:
        return f"{new / old:.2f}× {better}" if new >= old else f"{old / new:.2f}× {worse}"

    acc_delta = (base["sst2_val_accuracy"] - quant["sst2_val_accuracy"]) * 100
    lines += [
        "",
        f"INT8 is {base['size_mb'] / quant['size_mb']:.1f}× smaller, "
        f"{ratio(base['p50_ms_batch1'], quant['p50_ms_batch1'], 'faster', 'slower')} at batch 1, "
        f"has {ratio(quant['throughput_batch32'], base['throughput_batch32'], 'higher', 'lower')} batch-32 throughput, "
        f"and {'loses' if acc_delta >= 0 else 'gains'} {abs(acc_delta):.2f} accuracy points.",
        "",
        "Reproduce: `python scripts/benchmark_inference.py`",
    ]
    with open(os.path.join(args.out_dir, "results.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
