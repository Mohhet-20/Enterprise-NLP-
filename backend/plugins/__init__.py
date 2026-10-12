"""
Import every plugin module here so `backend/main.py` can register all task
plugins with a single `import backend.plugins` at startup.

Adding a new NLP task = adding one registration call to this file (or, for
larger plugins, a new module imported from here) — no other core file
changes.
"""

from backend.core.constants import ModelArchitecture, NLPTask
from backend.evaluation.base_evaluator import ClassificationEvaluator
from backend.plugins.plugin_registry import TaskPlugin, register_task_plugin

register_task_plugin(
    TaskPlugin(
        task=NLPTask.SENTIMENT_ANALYSIS,
        default_architecture=ModelArchitecture.DISTILBERT,
        default_model_name="distilbert-base-uncased-finetuned-sst-2-english",
        evaluator=ClassificationEvaluator,
    )
)

register_task_plugin(
    TaskPlugin(
        task=NLPTask.TOXICITY_DETECTION,
        default_architecture=ModelArchitecture.BERT,
        default_model_name="unitary/toxic-bert",
        evaluator=ClassificationEvaluator,
    )
)

# Additional tasks (emotion detection, topic classification, hate speech,
# fake news, language detection, intent classification, multi-label,
# zero-shot, semantic similarity, embeddings) register the same way in a
# follow-up build — each is one `register_task_plugin(...)` call.
