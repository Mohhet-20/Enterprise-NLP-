import pytest

from backend.core.constants import ModelArchitecture, NLPTask
from backend.core.exceptions import ModelNotFoundError, ValidationError
from backend.nlp.inference.model_factory import ModelFactory
from backend.nlp.inference.models.bert_model import BertModel


def test_factory_returns_registered_architecture():
    factory = ModelFactory()
    model = factory.get_model(ModelArchitecture.BERT, "bert-base-uncased")
    assert isinstance(model, BertModel)


def test_factory_caches_instances_by_key():
    factory = ModelFactory()
    first = factory.get_model(ModelArchitecture.BERT, "bert-base-uncased")
    second = factory.get_model(ModelArchitecture.BERT, "bert-base-uncased")
    assert first is second


def test_factory_raises_for_unregistered_architecture(monkeypatch):
    import backend.nlp.inference.model_factory as mf

    monkeypatch.delitem(mf._ARCHITECTURE_REGISTRY, ModelArchitecture.ROBERTA)
    with pytest.raises(ModelNotFoundError):
        ModelFactory().get_model(ModelArchitecture.ROBERTA, "roberta-base")


def test_plugin_registry_has_sentiment_analysis_registered():
    import backend.plugins  # noqa: F401  triggers registration
    from backend.plugins.plugin_registry import get_task_plugin

    plugin = get_task_plugin(NLPTask.SENTIMENT_ANALYSIS)
    assert plugin.default_architecture == ModelArchitecture.DISTILBERT


def test_plugin_registry_raises_for_unregistered_task():
    from backend.plugins import plugin_registry
    from backend.plugins.plugin_registry import get_task_plugin

    saved = plugin_registry._TASK_PLUGINS.pop(NLPTask.ZERO_SHOT_CLASSIFICATION)
    try:
        with pytest.raises(ValidationError):
            get_task_plugin(NLPTask.ZERO_SHOT_CLASSIFICATION)
    finally:
        plugin_registry._TASK_PLUGINS[NLPTask.ZERO_SHOT_CLASSIFICATION] = saved
