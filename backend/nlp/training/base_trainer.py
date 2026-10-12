"""
Training subsystem interface.

Deliberately minimal at the skeleton stage: defines the contract
(configure -> train -> evaluate -> save) that a real Hugging Face
`Trainer`-based implementation will fulfill in a follow-up build, without
committing the architecture to a specific training framework yet.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict


@dataclass
class TrainingConfig:
    model_name: str
    dataset_name: str
    num_epochs: int = 3
    learning_rate: float = 2e-5
    batch_size: int = 16
    output_dir: str = "./training_output"


@dataclass
class TrainingResult:
    final_metrics: Dict[str, float]
    checkpoint_path: str
    experiment_id: str


class BaseTrainer(ABC):
    def __init__(self, config: TrainingConfig) -> None:
        self.config = config

    @abstractmethod
    def train(self) -> TrainingResult:
        raise NotImplementedError

    @abstractmethod
    def evaluate(self) -> Dict[str, float]:
        raise NotImplementedError
