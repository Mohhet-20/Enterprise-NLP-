"""Dataset abstraction: versioned, with explicit train/val/test splits and
metadata. Concrete datasets (loaded from CSV, a DB table, HF datasets hub,
etc.) implement `load()`; everything else in the platform depends only on
this interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DatasetMetadata:
    name: str
    version: str
    task: str
    label_names: List[str]
    num_train: int = 0
    num_validation: int = 0
    num_test: int = 0
    extra: Dict[str, Any] = field(default_factory=dict)


class BaseDataset(ABC):
    def __init__(self, name: str, version: str = "v1") -> None:
        self.name = name
        self.version = version

    @abstractmethod
    def load(self) -> None:
        """Populate train/validation/test splits and metadata."""
        raise NotImplementedError

    @abstractmethod
    def validate(self) -> List[str]:
        """Return a list of validation warnings/errors (empty = clean)."""
        raise NotImplementedError

    @property
    @abstractmethod
    def metadata(self) -> Optional[DatasetMetadata]:
        raise NotImplementedError
