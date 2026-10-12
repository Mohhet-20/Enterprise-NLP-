"""
Structured logging configuration.

Every log line is emitted as JSON with a consistent schema so it can be
shipped to any log aggregator (ELK, Datadog, CloudWatch, etc.) without a
custom parser. Falls back to human-readable formatting in development.
"""

import json
import logging
import logging.config
import sys
from datetime import datetime, timezone
from typing import Any, Dict

from backend.config.settings import get_settings


class JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Structured "extra" fields (e.g. request_id, user_id, model_name)
        reserved = set(vars(logging.LogRecord("", 0, "", 0, "", None, None)).keys())
        for key, value in vars(record).items():
            if key not in reserved and key not in payload:
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def configure_logging() -> None:
    """Call once at application startup."""
    settings = get_settings()

    formatter_name = "json" if settings.log_json else "plain"

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {"()": JSONFormatter},
                "plain": {
                    "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "stream": sys.stdout,
                    "formatter": formatter_name,
                },
            },
            "root": {
                "handlers": ["console"],
                "level": settings.log_level,
            },
            "loggers": {
                # Categories called out explicitly in the platform spec —
                # each can be tuned independently (e.g. silence "sqlalchemy"
                # noise while keeping "audit" verbose).
                "api": {"level": settings.log_level, "propagate": True},
                "inference": {"level": settings.log_level, "propagate": True},
                "training": {"level": settings.log_level, "propagate": True},
                "auth": {"level": settings.log_level, "propagate": True},
                "experiments": {"level": settings.log_level, "propagate": True},
                "audit": {"level": "INFO", "propagate": True},
                "performance": {"level": settings.log_level, "propagate": True},
            },
        }
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
