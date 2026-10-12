"""
Adapter pattern: wraps the third-party `transformers` tokenizer API behind
a small platform-owned interface. If the platform ever needed to support a
tokenization backend that isn't `transformers` (e.g. a custom BPE service),
only this file would need to change.
"""

from typing import Any, Dict, Protocol

from backend.core.exceptions import ModelLoadError


class Tokenizer(Protocol):
    def encode(self, text: str) -> Dict[str, Any]: ...


class HuggingFaceTokenizerAdapter:
    """Adapts `transformers.AutoTokenizer` to the platform's `Tokenizer` protocol."""

    def __init__(self, model_name: str, max_length: int = 512) -> None:
        self._model_name = model_name
        self._max_length = max_length
        self._tokenizer = None

    def _ensure_loaded(self) -> None:
        if self._tokenizer is not None:
            return
        try:
            from transformers import AutoTokenizer

            self._tokenizer = AutoTokenizer.from_pretrained(self._model_name)
        except ImportError as exc:
            raise ModelLoadError(
                "The 'transformers' package is required for tokenization."
            ) from exc

    def encode(self, text: str) -> Dict[str, Any]:
        self._ensure_loaded()
        return self._tokenizer(
            text, truncation=True, max_length=self._max_length, return_tensors="pt"
        )


def get_tokenizer(model_name: str, max_length: int = 512) -> HuggingFaceTokenizerAdapter:
    return HuggingFaceTokenizerAdapter(model_name, max_length)
