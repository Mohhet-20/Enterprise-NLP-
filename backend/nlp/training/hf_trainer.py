"""
Fine-tuning a Hugging Face encoder for sequence classification.

`HFSequenceClassificationTrainer` is the concrete `BaseTrainer` used by
`scripts/train_sentiment.py`. It does the standard recipe — tokenize,
fine-tune with `transformers.Trainer`, evaluate on the held-out split —
and then writes three things next to the checkpoint so the run is
reproducible and auditable without re-running it:

  - `metrics.json`        final eval metrics + per-epoch history
  - `training_config.json` the exact hyperparameters / data sizes used
  - `README.md`           a short model card

Heavy imports (`torch`, `transformers`, `datasets`) are deferred to
`train()` so importing this module stays cheap for the API process.
"""

import json
import os
import random
import time
import uuid
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional

import numpy as np

from backend.core.exceptions import TrainingError
from backend.evaluation.metrics import compute_classification_metrics
from backend.nlp.training.base_trainer import BaseTrainer, TrainingConfig, TrainingResult


@dataclass
class HFTrainingConfig(TrainingConfig):
    text_column: str = "sentence"
    label_column: str = "label"
    train_split: str = "train"
    eval_split: str = "validation"
    max_train_samples: Optional[int] = None
    max_eval_samples: Optional[int] = None
    max_length: int = 128
    weight_decay: float = 0.01
    warmup_ratio: float = 0.06
    seed: int = 42


class HFSequenceClassificationTrainer(BaseTrainer):
    config: HFTrainingConfig

    def __init__(self, config: HFTrainingConfig) -> None:
        super().__init__(config)
        self._trainer = None
        self._eval_dataset = None
        self._label_names: List[str] = []

    def _load_splits(self):
        from datasets import load_dataset

        cfg = self.config
        raw = load_dataset(cfg.dataset_name)
        train = raw[cfg.train_split].shuffle(seed=cfg.seed)
        evaluation = raw[cfg.eval_split]
        if cfg.max_train_samples:
            train = train.select(range(min(cfg.max_train_samples, len(train))))
        if cfg.max_eval_samples:
            evaluation = evaluation.select(range(min(cfg.max_eval_samples, len(evaluation))))

        label_feature = train.features[cfg.label_column]
        self._label_names = [name.upper() for name in label_feature.names]
        return train, evaluation

    def train(self) -> TrainingResult:
        try:
            import torch
            from transformers import (
                AutoModelForSequenceClassification,
                AutoTokenizer,
                DataCollatorWithPadding,
                Trainer,
                TrainingArguments,
            )
        except ImportError as exc:
            raise TrainingError(
                "Training needs the ML extras: pip install -r requirements-ml.txt"
            ) from exc

        cfg = self.config
        random.seed(cfg.seed)
        np.random.seed(cfg.seed)
        torch.manual_seed(cfg.seed)

        train_ds, eval_ds = self._load_splits()
        tokenizer = AutoTokenizer.from_pretrained(cfg.model_name)

        def tokenize(batch):
            return tokenizer(batch[cfg.text_column], truncation=True, max_length=cfg.max_length)

        train_tok = train_ds.map(tokenize, batched=True)
        eval_tok = eval_ds.map(tokenize, batched=True)
        self._eval_dataset = eval_ds

        id2label = dict(enumerate(self._label_names))
        model = AutoModelForSequenceClassification.from_pretrained(
            cfg.model_name,
            num_labels=len(self._label_names),
            id2label=id2label,
            label2id={v: k for k, v in id2label.items()},
        )

        def compute_metrics(eval_pred):
            logits, labels = eval_pred
            preds = logits.argmax(axis=-1)
            return {"accuracy": float((preds == labels).mean())}

        args = TrainingArguments(
            output_dir=os.path.join(cfg.output_dir, "_checkpoints"),
            num_train_epochs=cfg.num_epochs,
            learning_rate=cfg.learning_rate,
            per_device_train_batch_size=cfg.batch_size,
            per_device_eval_batch_size=cfg.batch_size * 2,
            weight_decay=cfg.weight_decay,
            warmup_ratio=cfg.warmup_ratio,
            eval_strategy="epoch",
            save_strategy="no",
            logging_steps=25,
            report_to=[],
            seed=cfg.seed,
            use_cpu=not torch.cuda.is_available(),
        )
        self._trainer = Trainer(
            model=model,
            args=args,
            train_dataset=train_tok.remove_columns([c for c in train_tok.column_names if c not in ("input_ids", "attention_mask", cfg.label_column)]),
            eval_dataset=eval_tok.remove_columns([c for c in eval_tok.column_names if c not in ("input_ids", "attention_mask", cfg.label_column)]),
            tokenizer=tokenizer,
            data_collator=DataCollatorWithPadding(tokenizer),
            compute_metrics=compute_metrics,
        )

        started = time.time()
        train_output = self._trainer.train()
        train_seconds = time.time() - started

        final_metrics = self.evaluate()
        final_metrics["train_runtime_seconds"] = round(train_seconds, 1)
        final_metrics["train_loss"] = round(float(train_output.training_loss), 4)

        os.makedirs(cfg.output_dir, exist_ok=True)
        self._trainer.save_model(cfg.output_dir)
        tokenizer.save_pretrained(cfg.output_dir)

        history = [
            {k: v for k, v in entry.items() if k in ("epoch", "eval_loss", "eval_accuracy", "loss")}
            for entry in self._trainer.state.log_history
        ]
        experiment_id = str(uuid.uuid4())
        self._write_run_files(experiment_id, final_metrics, history, len(train_ds), len(eval_ds))

        return TrainingResult(
            final_metrics=final_metrics,
            checkpoint_path=cfg.output_dir,
            experiment_id=experiment_id,
        )

    def evaluate(self) -> Dict[str, float]:
        if self._trainer is None or self._eval_dataset is None:
            raise TrainingError("evaluate() called before train().")

        output = self._trainer.predict(self._trainer.eval_dataset)
        logits = output.predictions
        probs = _softmax(logits)
        pred_ids = probs.argmax(axis=-1)

        y_true = [self._label_names[i] for i in output.label_ids]
        y_pred = [self._label_names[i] for i in pred_ids]
        confidences = probs.max(axis=-1).tolist()

        metrics = compute_classification_metrics(y_true, y_pred, confidences, labels=self._label_names)
        return {
            "accuracy": metrics.accuracy,
            "macro_f1": metrics.macro_f1,
            "weighted_f1": metrics.weighted_f1,
            "roc_auc": metrics.roc_auc,
            "eval_samples": len(y_true),
            "confusion_matrix": metrics.confusion_matrix,
            "labels": metrics.labels,
        }

    def _write_run_files(
        self, experiment_id: str, metrics: Dict, history: List[Dict], n_train: int, n_eval: int
    ) -> None:
        cfg = self.config
        with open(os.path.join(cfg.output_dir, "metrics.json"), "w") as f:
            json.dump({"experiment_id": experiment_id, **metrics, "history": history}, f, indent=2)
        with open(os.path.join(cfg.output_dir, "training_config.json"), "w") as f:
            json.dump({**asdict(cfg), "train_samples_used": n_train, "eval_samples_used": n_eval}, f, indent=2)
        with open(os.path.join(cfg.output_dir, "README.md"), "w") as f:
            f.write(_model_card(cfg, metrics, n_train, n_eval))


def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - logits.max(axis=-1, keepdims=True)
    exp = np.exp(shifted)
    return exp / exp.sum(axis=-1, keepdims=True)


def _model_card(cfg: HFTrainingConfig, metrics: Dict, n_train: int, n_eval: int) -> str:
    return f"""# {os.path.basename(os.path.normpath(cfg.output_dir))}

Fine-tuned `{cfg.model_name}` on `{cfg.dataset_name}` for binary sentiment classification.

| | |
|---|---|
| Train examples | {n_train:,} |
| Eval examples ({cfg.eval_split}) | {n_eval:,} |
| Epochs | {cfg.num_epochs} |
| Learning rate | {cfg.learning_rate} |
| Batch size | {cfg.batch_size} |
| Max sequence length | {cfg.max_length} |
| Seed | {cfg.seed} |

## Results on `{cfg.eval_split}`

| Metric | Value |
|---|---|
| Accuracy | {metrics['accuracy']:.4f} |
| Macro F1 | {metrics['macro_f1']:.4f} |
| ROC AUC | {metrics['roc_auc']} |
| Train time (s) | {metrics['train_runtime_seconds']} |

Produced by `scripts/train_sentiment.py`.
"""
