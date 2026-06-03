"""
Structured JSON logging for the DashNote API process.

Import law: stdlib only (logging, json, datetime).
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

# Optional context fields callers may pass via logging extra={...}
_CONTEXT_KEYS = frozenset(
    {
        "request_id",
        "workspace_id",
        "user_id",
        "route",
        "latency_ms",
    }
)


class JsonFormatter(logging.Formatter):
    """Emit one JSON object per log line for ingestion by Loki/ELK/CloudWatch."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for key in _CONTEXT_KEYS:
            if key not in record.__dict__:
                continue
            value = record.__dict__[key]
            if value is not None:
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


_CONFIGURED = False


def _apply_json_handlers() -> None:
    formatter = JsonFormatter()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)

    # Route uvicorn loggers through the root JSON handler (consistent format).
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uv_logger = logging.getLogger(logger_name)
        uv_logger.handlers.clear()
        uv_logger.propagate = True
        uv_logger.setLevel(logging.INFO)


def setup_logging() -> None:
    """
    Configure process-wide JSON logging. Idempotent and never raises.

    Intended to be called once at API startup (main.py lifespan only).
    On failure, falls back to logging.basicConfig so the process still starts.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    try:
        _apply_json_handlers()
    except Exception:
        logging.basicConfig(
            level=logging.INFO,
            stream=sys.stdout,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )
    finally:
        _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a named logger; use extra={} for optional context fields."""
    return logging.getLogger(name)
