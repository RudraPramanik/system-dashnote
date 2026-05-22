"""
Redis embedding cache for DashNoteSystem.

Cache key format: embed:v1:{sha256(chunk_text)}

Why sha256(chunk_text)?
- Same text always produces the same cache key
- Provider-agnostic: same text, same vector regardless of call count
- Changing EMBEDDING_MODEL invalidates naturally (different vectors)
- No note_id in key: same text in different notes shares the cache

Cache hit = skip provider API call entirely = zero cost for repeated text.
Primary use case: note updates that change only a few chunks.

IMPORT LAW: stdlib, redis.asyncio, config.get_settings, ai.embeddings.base
"""
from __future__ import annotations

import hashlib
import json
import logging
from typing import TYPE_CHECKING

from ai.embeddings.base import EmbeddingVector
from config import get_settings

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)

_CACHE_KEY_PREFIX = "embed:v1"


def _make_cache_key(chunk_text: str) -> str:
    """
    Deterministic cache key from chunk text content.
    sha256 of the text → consistent key for identical content.
    """
    text_hash = hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()
    return f"{_CACHE_KEY_PREFIX}:{text_hash}"


async def get_cached_vector(
    chunk_text: str,
    redis: "Redis",
) -> EmbeddingVector | None:
    """
    Retrieve a cached embedding vector for this chunk text.
    Returns None on cache miss or if caching is disabled.
    """
    settings = get_settings()

    if not settings.EMBEDDING_CACHE_ENABLED:
        return None

    try:
        key = _make_cache_key(chunk_text)
        cached = await redis.get(key)
        if cached:
            logger.debug("Embedding cache hit", extra={"key": key[:20]})
            return json.loads(cached)
    except Exception as e:
        logger.warning("Embedding cache read failed: %s", e)

    return None


async def cache_vector(
    chunk_text: str,
    vector: EmbeddingVector,
    redis: "Redis",
) -> None:
    """
    Store an embedding vector in Redis cache.
    TTL from settings.EMBEDDING_CACHE_TTL (default 24h).
    Failures are logged but never propagate — cache is non-critical.
    """
    settings = get_settings()

    if not settings.EMBEDDING_CACHE_ENABLED:
        return

    try:
        key = _make_cache_key(chunk_text)
        await redis.setex(
            key,
            settings.EMBEDDING_CACHE_TTL,
            json.dumps(vector),
        )
        logger.debug("Embedding cached", extra={"key": key[:20]})
    except Exception as e:
        logger.warning("Embedding cache write failed: %s", e)
