# Model Lifecycle

## Serving path

```
1. Registered   A TaskPlugin declares the task's default (architecture, checkpoint),
                evaluator and explainer — backend/plugins/__init__.py.

2. Requested    POST /predict (or /predict/batch, /explain) names a task and
                optionally a model_name override.

3. Resolved     model_factory.get_model(architecture, name, task) returns a cached
                strategy instance; zero-shot is routed to the NLI strategy.

4. Loaded       First use pulls tokenizer + weights into memory (from
                MODEL_CACHE_DIR, or a local checkpoint directory). If more than
                MAX_LOADED_MODELS now hold weights, the least recently used one is
                unloaded and will reload on its next request.

5. Inference    One padded forward pass under torch.inference_mode(); latency and
                errors recorded per task:model in the MetricsRegistry.

6. Explained    /explain runs Integrated Gradients against the same loaded weights.
```

## Promotion path (Model Registry)

```
train ─► evaluate ─► register ─► approve ─► promote ─► deploy ─► champion
  │          │          │           │          │          │
  │          │          │           │          │          └ previous deployment for the
  │          │          │           │          │            task is rolled back automatically
  │          │          │           │          └ production only once approved
  │          │          │           └ Reviewer/Admin only (separation of duties)
  │          │          └ POST /models, linked to an evaluation_run_id
  │          └ POST /evaluation/run — served model vs baseline, same data
  └ scripts/train_sentiment.py → checkpoint + metrics.json + model card
```

Load, predict, train and evaluate are deliberately separate steps, so changing the
training recipe never touches the inference path, and a model can be re-evaluated on
new data without retraining.
