"""
Inference service: the orchestration layer between the API and the NLP
subsystem. Endpoints call this; this calls ModelFactory + plugin registry.
Nothing about HTTP (status codes, request parsing) lives here — that stays
in the API layer, and nothing about model internals leaks out of it either.
"""

import time
from typing import List

from backend.monitoring.metrics import metrics_registry
from backend.nlp.inference.model_factory import model_factory
from backend.plugins.plugin_registry import get_task_plugin
from backend.schemas.inference import InferenceRequest, InferenceResponse, InferenceResult
from backend.services.base_service import BaseService
from backend.utils.validators import require_non_empty_text


class InferenceService(BaseService):
    def run_inference(self, request: InferenceRequest) -> InferenceResponse:
        require_non_empty_text(request.text)

        plugin = get_task_plugin(request.task)
        model_name = request.model_name or plugin.default_model_name
        architecture = plugin.default_architecture

        model = model_factory.get_model(architecture, model_name)

        start = time.perf_counter()
        success = True
        try:
            predictions = model.predict(request.text, request.task)
        except Exception:
            success = False
            raise
        finally:
            latency_ms = (time.perf_counter() - start) * 1000
            metrics_registry.record_inference(
                task=request.task.value,
                model_name=model_name,
                latency_ms=latency_ms,
                success=success,
            )

        results: List[InferenceResult] = [
            InferenceResult(label=p.label, score=p.score, raw_scores=p.raw_scores)
            for p in predictions
        ]

        return InferenceResponse(
            task=request.task,
            model_name=model_name,
            results=results,
            latency_ms=round(latency_ms, 2),
        )


inference_service = InferenceService()
