"""
Exposes which NLP tasks are actually registered (via the plugin registry),
so clients (the frontend, API consumers) never have to hardcode the task
list separately from the backend's real capabilities.
"""

from fastapi import APIRouter

from backend.plugins.plugin_registry import get_task_plugin, list_supported_tasks

router = APIRouter()


@router.get("/tasks")
def list_tasks() -> dict:
    tasks = list_supported_tasks()
    return {
        "tasks": [
            {
                "task": task.value,
                "default_model": get_task_plugin(task).default_model_name,
            }
            for task in tasks
        ]
    }
