"""
Plugin registry: the extensibility mechanism referenced throughout the
platform spec ("adding a new NLP task should require minimal code changes").

A plugin bundles everything a new task needs (its model architecture
default, evaluator, optional explainer) and registers itself here at import
time. `backend/main.py` imports `backend/plugins/__init__.py` once at
startup, which is expected to import every plugin module — after that, the
core platform (API, services) can look up capabilities by task name without
an if/elif chain anywhere.
"""

import os
from dataclasses import dataclass
from typing import Dict, Optional, Type

from backend.core.constants import ModelArchitecture, NLPTask
from backend.core.exceptions import ValidationError
from backend.evaluation.base_evaluator import BaseEvaluator
from backend.explainability.base_explainer import BaseExplainer


@dataclass
class TaskPlugin:
    task: NLPTask
    default_architecture: ModelArchitecture
    default_model_name: str
    evaluator: Optional[Type[BaseEvaluator]] = None
    explainer: Optional[Type[BaseExplainer]] = None
    description: str = ""


_TASK_PLUGINS: Dict[NLPTask, TaskPlugin] = {}
# Plugins this build knows but this instance does not serve (Settings.served_tasks), for GET /tasks.
_NOT_SERVED: Dict[NLPTask, TaskPlugin] = {}


def _served(task: NLPTask) -> bool:
    from backend.config.settings import get_settings

    wanted = {t.strip() for t in get_settings().served_tasks.split(",") if t.strip()}
    return not wanted or task.value in wanted


def register_task_plugin(plugin: TaskPlugin) -> None:
    if _served(plugin.task):
        _TASK_PLUGINS[plugin.task] = plugin
    else:
        _NOT_SERVED[plugin.task] = plugin


def get_task_plugin(task: NLPTask) -> TaskPlugin:
    plugin = _TASK_PLUGINS.get(task)
    if plugin is None:
        raise ValidationError(f"No plugin registered for task '{task.value}'.")
    return plugin


def list_supported_tasks() -> list[NLPTask]:
    return list(_TASK_PLUGINS.keys())


def list_not_served_tasks() -> list[TaskPlugin]:
    return list(_NOT_SERVED.values())


def display_model_name(model_name: str) -> str:
    """Public name for a model. Local checkpoints are absolute paths on the
    server; expose only the directory name so filesystem layout never leaks
    into API responses."""
    if os.path.isabs(model_name):
        return os.path.basename(os.path.normpath(model_name))
    return model_name
