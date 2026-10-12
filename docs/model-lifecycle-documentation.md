# Model Lifecycle

```
1. Registered      A TaskPlugin declares a default (architecture, model_name)
                    in backend/plugins/__init__.py.

2. Requested        A client calls POST /predict with a task (and optionally
                    an explicit model_name override).

3. Resolved          model_factory.get_model(architecture, model_name) checks
                    its in-memory cache for an existing instance.

4. Loaded (lazy)     On first use, BaseNLPModel.load() pulls tokenizer +
                    weights (currently via `transformers.AutoModel*`,
                    swappable per architecture). Cached in-process after
                    that — no reload per request.

5. Inference         BaseNLPModel.predict() runs, wrapped in a Timer and
                    recorded to MetricsRegistry (count, latency, error rate
                    per task:model_name).

6. Evaluated          (training/eval pipeline, not the request path) —
                    BaseEvaluator computes metrics against a held-out split,
                    logged via ExperimentTracker.

7. Compared           ExperimentTracker.compare(...) pulls the same metric
                    across multiple experiment_ids for side-by-side review.

8. Explained (opt.)   BaseExplainer.explain() attributes the prediction to
                    input tokens, for human review workflows.

9. Retired            Not yet implemented: a future `ModelRegistry` version
                    field + `deprecated_at` timestamp would let old model
                    versions be phased out without breaking in-flight
                    requests. Flagged here so the schema addition is
                    anticipated rather than a later migration surprise.
```

This lifecycle deliberately keeps "load" separate from "predict" and both
separate from "train"/"evaluate" so that swapping in a real training loop
later doesn't touch the inference path at all.
