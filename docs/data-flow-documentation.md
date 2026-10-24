# Data Flow: A Prediction Request

```
Client
  │  POST /api/v1/predict  {task, text, model_name?, candidate_labels?, text_pair?}
  ▼
RequestContextMiddleware        (assigns request_id, times the request, logs completion)
  ▼
api/v1/endpoints/inference.py   (parses InferenceRequest, resolves current_user via JWT)
  │  require_permission(role, "model:infer")
  ▼
services/inference_service.py   (InferenceService.run_inference)
  │  1. get_task_plugin(task)              -> default architecture + model name
  │  2. model_factory.get_model(...)        -> cached BaseNLPModel instance (Strategy);
  │                                            LRU-unloads the oldest model past the cap
  │  3. model.predict(text, task, ...)      -> lazy-loads weights on first call (with retry),
  │                                            one forward pass under inference_mode
  │  4. metrics_registry.record_inference    -> updates in-process monitoring
  ▼
schemas/inference.py             (serializes InferenceResponse)
  ▼
Client receives JSON response + X-Request-ID header
```

## Error path

If any step raises a `PlatformError` subclass (e.g. `ModelNotFoundError`,
`ValidationError`), it propagates unmodified up to
`core/exception_handlers.py`, which converts it into the standard error
JSON shape (`docs/api-documentation.md` → "Error format") and logs it with
the same `request_id` — nothing downstream needs its own try/except for
this to work correctly.

## Training data flow

```
HF dataset (stanfordnlp/sst2)            scripts/train_sentiment.py
   │  seeded shuffle, optional subsample
   ▼
tokenize (truncate to max_length)  ──►  DataCollatorWithPadding (dynamic padding)
   ▼
transformers.Trainer  (AdamW, linear warm-up/decay, per-epoch eval)
   ▼
HFSequenceClassificationTrainer.evaluate()  ──►  evaluation/metrics.py (same code as the API)
   ▼
artifacts/models/distilbert-sst2/
   ├─ model + tokenizer
   ├─ metrics.json            accuracy, macro-F1, ROC-AUC, confusion matrix, loss history
   ├─ training_config.json    every hyperparameter + data sizes
   └─ README.md               model card
   ▼
plugins/__init__.py serves it for sentiment_analysis on next start
```
