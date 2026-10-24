"""
End-to-end checks against the real Hugging Face checkpoints each plugin
serves. Slow (downloads ~2.5GB on first run) and network-dependent, so
they're opt-in:

    pytest -m integration

Assertions are about behaviour a real model must get right on unambiguous
inputs — not exact scores, which shift between checkpoint revisions.
"""

import pytest

from backend.core.constants import NLPTask
from backend.nlp.inference.model_factory import ModelFactory
from backend.plugins.plugin_registry import get_task_plugin

pytestmark = pytest.mark.integration

_factory = ModelFactory(max_loaded_models=2)


def _model(task: NLPTask):
    import backend.plugins  # noqa: F401

    plugin = get_task_plugin(task)
    return _factory.get_model(plugin.default_architecture, plugin.default_model_name, task=task)


def _top(task: NLPTask, text: str, **kwargs) -> str:
    return _model(task).predict(text, task, **kwargs)[0].label


@pytest.mark.parametrize(
    "text,expected",
    [
        ("An absolute masterpiece, I was moved to tears.", "POSITIVE"),
        ("A tedious, joyless slog that wastes a fine cast.", "NEGATIVE"),
        ("I didn't think it was going to be good, but it was wonderful.", "POSITIVE"),
    ],
)
def test_sentiment(text, expected):
    assert _top(NLPTask.SENTIMENT_ANALYSIS, text) == expected


@pytest.mark.parametrize(
    "text,expected",
    [("I can't stop smiling, best day ever!", "joy"), ("I'm terrified of what happens next.", "fear")],
)
def test_emotion(text, expected):
    assert _top(NLPTask.EMOTION_DETECTION, text) == expected


def test_toxicity_flags_insult_and_passes_benign_text():
    model = _model(NLPTask.TOXICITY_DETECTION)
    insult = model.predict("You are a pathetic idiot.", NLPTask.TOXICITY_DETECTION)
    benign = model.predict("Thanks for the thoughtful review.", NLPTask.TOXICITY_DETECTION)
    assert "toxic" in {p.label for p in insult}
    assert benign[0].raw_scores["toxic"] < 0.1


@pytest.mark.parametrize(
    "text,expected",
    [("Où se trouve la gare, s'il vous plaît ?", "fr"), ("Ich habe heute keine Zeit.", "de"), ("今日はいい天気ですね。", "ja")],
)
def test_language_detection(text, expected):
    assert _top(NLPTask.LANGUAGE_DETECTION, text) == expected


def test_topic_is_multi_label():
    preds = _model(NLPTask.TOPIC_CLASSIFICATION).predict(
        "The championship final drew a record TV audience.", NLPTask.TOPIC_CLASSIFICATION
    )
    assert "sports" in {p.label for p in preds}


def test_zero_shot_uses_request_time_labels():
    label = _top(
        NLPTask.ZERO_SHOT_CLASSIFICATION,
        "The central bank raised interest rates by half a point.",
        candidate_labels=["economy", "sports", "cooking"],
    )
    assert label == "economy"


def test_semantic_similarity_tracks_meaning_not_word_overlap():
    model = _model(NLPTask.SEMANTIC_SIMILARITY)
    paraphrase = model.similarity("The battery lasts all day.", "It holds a charge from morning to night.")
    overlap_only = model.similarity("The battery lasts all day.", "The day the battery factory closed.")
    assert paraphrase > overlap_only


def test_dense_index_finds_paraphrase_with_no_shared_words():
    from backend.services.embedding_service import EmbeddingIndexService

    service = EmbeddingIndexService(encoder="dense")
    service.build_index(
        "ds",
        ["r1", "r2", "r3"],
        ["Delivery was weeks late.", "It holds a charge from morning to night.", "The screen cracked."],
        [None, None, None],
    )
    assert service.search("ds", "great battery life", top_k=1)[0].record_id == "r2"


def test_integrated_gradients_highlights_the_sentiment_word():
    from backend.explainability.integrated_gradients import IntegratedGradientsExplainer

    model = _model(NLPTask.SENTIMENT_ANALYSIS)
    explanation = IntegratedGradientsExplainer(model, n_steps=50).explain_full(
        "The plot was dull and the acting was terrible.", "NEGATIVE"
    )
    top_word = max(explanation.attributions, key=lambda a: a.importance).token
    assert top_word in {"terrible", "dull"}
    gap = explanation.target_score - explanation.baseline_score
    assert abs(explanation.convergence_delta) < 0.1 * max(abs(gap), 1e-6) + 0.02
