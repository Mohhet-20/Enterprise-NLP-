"""Simple registry so datasets are discoverable by name without every
caller needing to know the concrete class. Mirrors the ModelFactory pattern
used in nlp/inference for consistency across the codebase."""

from typing import Dict, Type

from backend.core.exceptions import DatasetNotFoundError
from backend.datasets.base_dataset import BaseDataset

_REGISTRY: Dict[str, Type[BaseDataset]] = {}


def register_dataset(name: str):
    """Class decorator: `@register_dataset("imdb_sentiment")`."""

    def _decorator(cls: Type[BaseDataset]) -> Type[BaseDataset]:
        _REGISTRY[name] = cls
        return cls

    return _decorator


def get_dataset(name: str, **kwargs) -> BaseDataset:
    dataset_cls = _REGISTRY.get(name)
    if dataset_cls is None:
        raise DatasetNotFoundError(f"No dataset registered under name '{name}'.")
    return dataset_cls(name=name, **kwargs)


def list_registered_datasets() -> list[str]:
    return sorted(_REGISTRY.keys())
