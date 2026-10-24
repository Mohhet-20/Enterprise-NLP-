"""
Fine-tune DistilBERT on SST-2 and save a servable checkpoint.

    python scripts/train_sentiment.py                       # full SST-2 (67k), GPU recommended
    python scripts/train_sentiment.py --max-train-samples 20000 --epochs 2   # ~30 min on a laptop CPU

The checkpoint lands in `artifacts/models/distilbert-sst2/` by default.
The sentiment plugin serves it automatically once it exists (see
`backend/plugins/__init__.py`); evaluation runs can then compare it against
the lexicon baseline on the same data.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.nlp.training.hf_trainer import HFSequenceClassificationTrainer, HFTrainingConfig  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", default="distilbert/distilbert-base-uncased")
    parser.add_argument("--dataset", default="stanfordnlp/sst2")
    parser.add_argument("--output-dir", default="artifacts/models/distilbert-sst2")
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--lr", type=float, default=3e-5)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--max-length", type=int, default=64)
    parser.add_argument("--max-train-samples", type=int, default=None)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    config = HFTrainingConfig(
        model_name=args.model,
        dataset_name=args.dataset,
        output_dir=args.output_dir,
        num_epochs=args.epochs,
        learning_rate=args.lr,
        batch_size=args.batch_size,
        max_length=args.max_length,
        max_train_samples=args.max_train_samples,
        seed=args.seed,
    )
    result = HFSequenceClassificationTrainer(config).train()

    summary = {k: v for k, v in result.final_metrics.items() if k != "confusion_matrix"}
    print(json.dumps({"checkpoint": result.checkpoint_path, **summary}, indent=2))


if __name__ == "__main__":
    main()
