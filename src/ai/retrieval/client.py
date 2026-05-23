"""
Async Qdrant client singleton.

Only ai.retrieval.* modules may call get_async_qdrant_client().
Routers and worker tasks must use WorkspaceVectorSearch / NoteVectorIndexer.
"""
from __future__ import annotations

import asyncio
import logging

from qdrant_client import AsyncQdrantClient

from config import get_settings

logger = logging.getLogger(__name__)

_client: AsyncQdrantClient | None = None
_lock = asyncio.Lock()


async def get_async_qdrant_client() -> AsyncQdrantClient:
    """Return a process-wide AsyncQdrantClient (lazy, thread-safe init)."""
    global _client
    if _client is not None:
        return _client

    async with _lock:
        if _client is not None:
            return _client

        settings = get_settings()
        if not settings.qdrant_enabled:
            raise RuntimeError("QDRANT_URL is not configured")

        kwargs: dict = {
            "url": settings.QDRANT_URL,
            "timeout": settings.QDRANT_TIMEOUT,
            "check_compatibility": False,
        }
        api_key = (settings.QDRANT_API_KEY or "").strip()
        if api_key and api_key != "...":
            kwargs["api_key"] = api_key

        _client = AsyncQdrantClient(**kwargs)
        logger.info(
            "Qdrant client initialised",
            extra={"url": settings.QDRANT_URL},
        )
        return _client


async def close_async_qdrant_client() -> None:
    """Close the singleton client (worker/API shutdown)."""
    global _client
    if _client is not None:
        await _client.close()
        _client = None


def reset_qdrant_client_for_tests() -> None:
    """Clear singleton without closing (unit tests)."""
    global _client
    _client = None
