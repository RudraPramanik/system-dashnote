"""
Lazy Langfuse SDK client for DashNote observability.

Import law: stdlib, config, langfuse SDK only.
No FastAPI, SQLAlchemy, or domain modules.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from config import get_settings

if TYPE_CHECKING:
    from langfuse import Langfuse

logger = logging.getLogger(__name__)

_client: Langfuse | None = None
_initialized = False


def get_langfuse_client() -> Optional["Langfuse"]:
    """
    Return the process-wide Langfuse client, initializing lazily on first call.

    Never raises. Returns None when disabled or init fails.
    """
    global _client, _initialized

    if _initialized:
        return _client

    settings = get_settings()

    if not settings.langfuse_enabled:
        logger.warning(
            "Langfuse disabled: LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY "
            "are not both set"
        )
        _initialized = True
        return None

    try:
        from langfuse import Langfuse

        _client = Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST,
        )
        logger.info(
            "Langfuse client initialized",
            extra={"host": settings.LANGFUSE_HOST},
        )
    except Exception as exc:
        logger.warning(
            "Langfuse client init failed; tracing unavailable",
            extra={"error": str(exc), "host": settings.LANGFUSE_HOST},
        )
        _client = None

    _initialized = True
    return _client
