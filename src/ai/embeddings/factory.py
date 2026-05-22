"""
Embedding provider factory (process singleton).

This is the ONLY place where providers are instantiated.
All calling code uses get_embedding_provider() — never imports
a specific provider class directly.

FastAPI Depends wiring lives in route modules (not here) per AI import law.
"""
from __future__ import annotations

import asyncio
import logging

from ai.embeddings.base import BaseEmbeddingProvider

logger = logging.getLogger(__name__)

_provider_instance: BaseEmbeddingProvider | None = None
_provider_lock = asyncio.Lock()


async def get_embedding_provider() -> BaseEmbeddingProvider:
    """
    Singleton factory for the embedding provider.

    Returns the same provider instance for every call in this process.
    Thread-safe via asyncio.Lock — safe for concurrent async requests.
    Provider type is determined by EMBEDDING_MODEL in settings.

    Usage:
        provider = await get_embedding_provider()
    """
    global _provider_instance

    if _provider_instance is not None:
        return _provider_instance

    async with _provider_lock:
        if _provider_instance is not None:
            return _provider_instance

        from ai.embeddings.litellm_provider import LiteLLMEmbeddingProvider

        _provider_instance = LiteLLMEmbeddingProvider()
        logger.info(
            "Embedding provider initialised",
            extra={"model": _provider_instance.get_model_name()},
        )

    return _provider_instance


async def reset_embedding_provider() -> None:
    """Reset singleton — used in tests only."""
    global _provider_instance
    _provider_instance = None
