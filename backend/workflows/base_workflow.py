"""Workflow subsystem: composes multiple steps (e.g. dataset validation ->
training -> evaluation -> human review -> deployment) into a single
trackable pipeline. Each step is a callable; the workflow just sequences
them and records outcomes — future workflow types (async/distributed via
Celery/Temporal) implement the same `run()` contract."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Dict, List


@dataclass
class WorkflowStepResult:
    step_name: str
    success: bool
    output: Any = None
    error: str = ""


class BaseWorkflow(ABC):
    def __init__(self, name: str) -> None:
        self.name = name
        self.steps: List[tuple[str, Callable[..., Any]]] = []

    def add_step(self, name: str, fn: Callable[..., Any]) -> "BaseWorkflow":
        self.steps.append((name, fn))
        return self

    @abstractmethod
    def run(self, context: Dict[str, Any]) -> List[WorkflowStepResult]:
        raise NotImplementedError


class SequentialWorkflow(BaseWorkflow):
    """Runs steps in order, stopping at the first failure."""

    def run(self, context: Dict[str, Any]) -> List[WorkflowStepResult]:
        results: List[WorkflowStepResult] = []
        for step_name, fn in self.steps:
            try:
                output = fn(context)
                results.append(WorkflowStepResult(step_name, True, output=output))
            except Exception as exc:  # noqa: BLE001
                results.append(WorkflowStepResult(step_name, False, error=str(exc)))
                break
        return results
