# Data Flow: A Prediction Request

```
Client
  │  POST /api/v1/predict  {task, text, model_name?}
  ▼
RequestContextMiddleware        (assigns request_id, times the request, logs completion)
  ▼
api/v1/endpoints/inference.py   (parses InferenceRequest, resolves current_user via JWT)
  │  require_permission(role, "model:infer")
  ▼
services/inference_service.py   (InferenceService.run_inference)
  │  1. get_task_plugin(task)              -> default architecture + model name
  │  2. model_factory.get_model(...)        -> cached BaseNLPModel instance (Strategy)
  │  3. model.predict(text, task)           -> lazy-loads weights on first call
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

## Training data flow (interface only at this stage)

```
datasets/base_dataset.py  (load + validate)
   ▼
nlp/training/base_trainer.py  (BaseTrainer.train() -> TrainingResult)
   ▼
experiments/experiment_tracker.py  (ExperimentTracker.create + log_metrics)
   ▼
evaluation/base_evaluator.py  (BaseEvaluator.evaluate on held-out split)
   ▼
reporting/report_generator.py  (renders a report from tracked experiment data)
```
