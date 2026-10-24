"""
Head-to-head sentiment evaluation: lexicon baseline vs the public SST-2
checkpoint vs our own fine-tuned checkpoint, on both the SST-2 validation
split and the 48-sentence challenge set.

    python scripts/evaluate_sentiment.py

Uses the same metrics code (backend/evaluation/metrics.py) as the API's
Evaluation Center. Writes reports/sentiment_results.{json,md}.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.constants import NLPTask  # noqa: E402
from backend.evaluation.baseline_classifier import baseline_sentiment_classifier  # noqa: E402
from backend.evaluation.error_analysis import EvalSampleResult, error_analyzer  # noqa: E402
from backend.evaluation.metrics import compute_classification_metrics  # noqa: E402
from backend.evaluation.sample_dataset import SENTIMENT_EVAL_SET  # noqa: E402
from backend.nlp.inference.models.distilbert_model import DistilBertModel  # noqa: E402
from backend.services.evaluation_service import _load_sst2_validation  # noqa: E402

LOCAL = "artifacts/models/distilbert-sst2"
PUBLIC = "distilbert/distilbert-base-uncased-finetuned-sst-2-english"


def score(predict_batch, examples):
    preds = predict_batch([e.text for e in examples])
    samples = [
        EvalSampleResult(e.text, e.true_label.upper(), label.upper(), conf) for e, (label, conf) in zip(examples, preds)
    ]
    m = compute_classification_metrics(
        [s.true_label for s in samples], [s.predicted_label for s in samples], [s.confidence for s in samples],
        labels=["NEGATIVE", "POSITIVE"],
    )
    slices = {ls.name: ls.accuracy for ls in error_analyzer.analyze(samples).length_slices}
    return {"accuracy": m.accuracy, "macro_f1": m.macro_f1, "roc_auc": m.roc_auc, "n": len(samples), "by_length": slices}


def transformer(name):
    model = DistilBertModel(name)

    def run(texts):
        out = []
        for i in range(0, len(texts), 64):
            out += [(p[0].label, p[0].score) for p in model.predict_batch(texts[i : i + 64], NLPTask.SENTIMENT_ANALYSIS)]
        return out

    return run


def main() -> None:
    systems = {"lexicon-baseline-v1": lambda ts: [(p.label, p.score) for p in map(baseline_sentiment_classifier.predict, ts)]}
    systems[PUBLIC] = transformer(PUBLIC)
    if os.path.isfile(os.path.join(LOCAL, "config.json")):
        systems["distilbert-sst2 (ours)"] = transformer(os.path.abspath(LOCAL))

    sets = {"sst2_validation": _load_sst2_validation(), "challenge_set": list(SENTIMENT_EVAL_SET)}
    results = {name: {set_name: score(fn, ex) for set_name, ex in sets.items()} for name, fn in systems.items()}

    os.makedirs("reports", exist_ok=True)
    with open("reports/sentiment_results.json", "w") as f:
        json.dump(results, f, indent=2)

    lines = [
        "# Sentiment results",
        "",
        "| System | SST-2 val accuracy | SST-2 val macro-F1 | Challenge set accuracy | Challenge set macro-F1 |",
        "|---|---|---|---|---|",
    ]
    for name, r in results.items():
        s, c = r["sst2_validation"], r["challenge_set"]
        lines.append(f"| {name} | {s['accuracy']:.2%} | {s['macro_f1']:.3f} | {c['accuracy']:.2%} | {c['macro_f1']:.3f} |")
    lines += ["", "Reproduce: `python scripts/evaluate_sentiment.py`"]
    with open("reports/sentiment_results.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
