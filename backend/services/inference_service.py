"""
Inference service: the orchestration layer between the API and the NLP
subsystem. Endpoints call this; this calls ModelFactory + plugin registry.
Nothing about HTTP (status codes, request parsing) lives here — that stays
in the API layer, and nothing about model internals leaks out of it either.
"""

import time
from typing import List

from backend.config.settings import get_settings
from backend.core.constants import NLPTask
from backend.core.exceptions import ValidationError
from backend.monitoring.metrics import metrics_registry
from backend.nlp.inference.base_model import BaseNLPModel, Prediction
from backend.nlp.inference.model_factory import model_factory
from backend.plugins.plugin_registry import display_model_name, get_task_plugin
from backend.schemas.inference import (
    BatchInferenceItem,
    BatchInferenceRequest,
    BatchInferenceResponse,
    EmbedRequest,
    EmbedResponse,
    ExplainRequest,
    ExplainResponse,
    InferenceRequest,
    InferenceResponse,
    InferenceResult,
    TokenAttributionSchema,
)
from backend.services.base_service import BaseService
from backend.utils.validators import require_non_empty_text


def _to_results(predictions: List[Prediction]) -> List[InferenceResult]:
    return [InferenceResult(label=p.label, score=p.score, raw_scores=p.raw_scores) for p in predictions]


class InferenceService(BaseService):
    def _resolve(self, task: NLPTask, model_name: str | None) -> tuple[BaseNLPModel, str]:
        plugin = get_task_plugin(task)
        resolved_name = model_name or plugin.default_model_name
        model = model_factory.get_model(plugin.default_architecture, resolved_name, task=task)
        return model, display_model_name(resolved_name)

    def _timed(self, task: NLPTask, model_name: str, fn):
        start = time.perf_counter()
        success = True
        try:
            return fn(), (time.perf_counter() - start) * 1000
        except Exception:
            success = False
            raise
        finally:
            metrics_registry.record_inference(
                task=task.value,
                model_name=model_name,
                latency_ms=(time.perf_counter() - start) * 1000,
                success=success,
            )

    def run_inference(self, request: InferenceRequest) -> InferenceResponse:
        require_non_empty_text(request.text)
        model, model_name = self._resolve(request.task, request.model_name)

        predictions, latency_ms = self._timed(
            request.task,
            model_name,
            lambda: model.predict(
                request.text,
                request.task,
                candidate_labels=request.candidate_labels,
                multi_label=request.multi_label,
                text_pair=request.text_pair,
            ),
        )
        return InferenceResponse(
            task=request.task,
            model_name=model_name,
            results=_to_results(predictions),
            latency_ms=round(latency_ms, 2),
        )

    def run_batch(self, request: BatchInferenceRequest) -> BatchInferenceResponse:
        max_texts = get_settings().max_batch_texts
        if len(request.texts) > max_texts:
            raise ValidationError(f"A batch may contain at most {max_texts} texts.")
        for text in request.texts:
            require_non_empty_text(text)
        if request.task == NLPTask.SEMANTIC_SIMILARITY:
            raise ValidationError("Semantic similarity compares a pair; use /predict with text_pair.")

        model, model_name = self._resolve(request.task, request.model_name)
        batch_size = get_settings().inference_batch_size

        def run() -> List[List[Prediction]]:
            out: List[List[Prediction]] = []
            for i in range(0, len(request.texts), batch_size):
                out.extend(
                    model.predict_batch(
                        request.texts[i : i + batch_size],
                        request.task,
                        candidate_labels=request.candidate_labels,
                        multi_label=request.multi_label,
                    )
                )
            return out

        batches, latency_ms = self._timed(request.task, model_name, run)
        return BatchInferenceResponse(
            task=request.task,
            model_name=model_name,
            items=[BatchInferenceItem(text=t, results=_to_results(p)) for t, p in zip(request.texts, batches)],
            latency_ms=round(latency_ms, 2),
            throughput_texts_per_second=round(len(request.texts) / max(latency_ms / 1000, 1e-9), 2),
        )

    def explain(self, request: ExplainRequest) -> ExplainResponse:
        require_non_empty_text(request.text)
        plugin = get_task_plugin(request.task)
        if plugin.explainer is None:
            raise ValidationError(f"No explainer is registered for task '{request.task.value}'.")

        model, model_name = self._resolve(request.task, None)
        start = time.perf_counter()
        target = request.target_label or model.predict(request.text, request.task)[0].label
        explanation = plugin.explainer(model, n_steps=request.n_steps).explain_full(request.text, target)
        latency_ms = (time.perf_counter() - start) * 1000

        return ExplainResponse(
            task=request.task,
            model_name=model_name,
            method="integrated_gradients",
            label=explanation.label,
            target_score=explanation.target_score,
            baseline_score=explanation.baseline_score,
            convergence_delta=explanation.convergence_delta,
            attributions=[TokenAttributionSchema(**a.__dict__) for a in explanation.attributions],
            latency_ms=round(latency_ms, 2),
        )

    def embed(self, request: EmbedRequest) -> EmbedResponse:
        max_texts = get_settings().max_batch_texts
        if len(request.texts) > max_texts:
            raise ValidationError(f"At most {max_texts} texts can be embedded per request.")
        for text in request.texts:
            require_non_empty_text(text)
        model, model_name = self._resolve(NLPTask.TEXT_EMBEDDINGS, None)
        vectors, _ = self._timed(NLPTask.TEXT_EMBEDDINGS, model_name, lambda: model.embed(request.texts))
        return EmbedResponse(model_name=model_name, dimension=len(vectors[0]), embeddings=vectors)


inference_service = InferenceService()
