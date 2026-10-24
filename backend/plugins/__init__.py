"""
Import every plugin module here so `backend/main.py` can register all task
plugins with a single `import backend.plugins` at startup.

Adding a new NLP task = one `register_task_plugin(...)` call below plus a
value in `NLPTask` — no other core file changes.

Every checkpoint below is a public Hugging Face model with a permissive
license; see docs/model-cards.md for sources, training data, and known
limitations of each one.
"""

import os

from backend.config.settings import get_settings
from backend.core.constants import ModelArchitecture, NLPTask
from backend.evaluation.base_evaluator import ClassificationEvaluator
from backend.explainability.integrated_gradients import IntegratedGradientsExplainer
from backend.plugins.plugin_registry import TaskPlugin, register_task_plugin

PUBLIC_SENTIMENT_CHECKPOINT = "distilbert/distilbert-base-uncased-finetuned-sst-2-english"


def _sentiment_model_name() -> str:
    """Prefer our own fine-tuned checkpoint when it has been trained locally."""
    local_dir = get_settings().sentiment_checkpoint_dir
    if os.path.isfile(os.path.join(local_dir, "config.json")):
        return os.path.abspath(local_dir)
    return PUBLIC_SENTIMENT_CHECKPOINT


register_task_plugin(
    TaskPlugin(
        task=NLPTask.SENTIMENT_ANALYSIS,
        default_architecture=ModelArchitecture.DISTILBERT,
        default_model_name=_sentiment_model_name(),
        evaluator=ClassificationEvaluator,
        explainer=IntegratedGradientsExplainer,
        description="Binary positive/negative sentiment (DistilBERT fine-tuned on SST-2).",
    )
)

register_task_plugin(
    TaskPlugin(
        task=NLPTask.EMOTION_DETECTION,
        default_architecture=ModelArchitecture.ROBERTA,
        default_model_name="j-hartmann/emotion-english-distilroberta-base",
        evaluator=ClassificationEvaluator,
        explainer=IntegratedGradientsExplainer,
        description="Ekman's 6 basic emotions + neutral.",
    )
)

register_task_plugin(
    TaskPlugin(
        task=NLPTask.TOXICITY_DETECTION,
        default_architecture=ModelArchitecture.BERT,
        default_model_name="unitary/toxic-bert",
        evaluator=ClassificationEvaluator,
        explainer=IntegratedGradientsExplainer,
        description="Multi-label toxicity (Jigsaw): toxic, severe_toxic, obscene, threat, insult, identity_hate.",
    )
)

register_task_plugin(
    TaskPlugin(
        task=NLPTask.TOPIC_CLASSIFICATION,
        default_architecture=ModelArchitecture.ROBERTA,
        default_model_name="cardiffnlp/tweet-topic-21-multi",
        evaluator=ClassificationEvaluator,
        description="Multi-label topic classification over 19 topics (TweetTopic).",
    )
)

register_task_plugin(
    TaskPlugin(
        task=NLPTask.LANGUAGE_DETECTION,
        default_architecture=ModelArchitecture.XLM_ROBERTA,
        default_model_name="papluca/xlm-roberta-base-language-detection",
        evaluator=ClassificationEvaluator,
        description="Identifies 20 languages (XLM-RoBERTa).",
    )
)

register_task_plugin(
    TaskPlugin(
        task=NLPTask.ZERO_SHOT_CLASSIFICATION,
        default_architecture=ModelArchitecture.DEBERTA,
        default_model_name="MoritzLaurer/deberta-v3-xsmall-zeroshot-v1.1-all-33",
        description="Classify into any labels you supply at request time (NLI-based).",
    )
)

register_task_plugin(
    TaskPlugin(
        task=NLPTask.SEMANTIC_SIMILARITY,
        default_architecture=ModelArchitecture.SENTENCE_TRANSFORMER,
        default_model_name="sentence-transformers/all-MiniLM-L6-v2",
        description="Cosine similarity between two texts (MiniLM sentence embeddings).",
    )
)

register_task_plugin(
    TaskPlugin(
        task=NLPTask.TEXT_EMBEDDINGS,
        default_architecture=ModelArchitecture.SENTENCE_TRANSFORMER,
        default_model_name="sentence-transformers/all-MiniLM-L6-v2",
        description="384-dimensional normalised sentence embeddings.",
    )
)
