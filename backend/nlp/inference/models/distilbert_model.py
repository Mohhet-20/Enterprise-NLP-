"""
DistilBERT is architecturally a drop-in for BertModel's sequence-classification
API, so it reuses that implementation entirely. This is the "minimal code
to add a new model" case referenced in the platform spec — most
`transformers`-based encoder models will only need an entry in
`model_factory.py`, not a whole new class like this one.
"""

from backend.nlp.inference.models.bert_model import BertModel


class DistilBertModel(BertModel):
    """Distinct class name kept for explicitness in logs/registry, even
    though behavior is identical to BertModel."""
    pass
