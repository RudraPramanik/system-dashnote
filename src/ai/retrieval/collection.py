"""
Ensure the notes_chunks collection exists with the configured vector dimension.
"""
from __future__ import annotations

import logging

from qdrant_client.models import Distance, VectorParams

from ai.retrieval.client import get_async_qdrant_client
from config import get_settings

logger = logging.getLogger(__name__)

_notes_collection_ready = False
_files_collection_ready = False


async def ensure_notes_collection() -> None:
    """
    Create notes_chunks collection if missing (idempotent per process).
    Vector size must match settings.EMBEDDING_DIMENSION (3072 for gemini-embedding-2).
    """
    global _notes_collection_ready
    if _notes_collection_ready:
        return

    settings = get_settings()
    if not settings.qdrant_enabled:
        logger.debug("Qdrant disabled — skipping collection ensure")
        return

    client = await get_async_qdrant_client()
    name = settings.QDRANT_NOTES_COLLECTION
    dim = settings.EMBEDDING_DIMENSION

    exists = await client.collection_exists(name)
    if not exists:
        await client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )
        logger.info(
            "Qdrant collection created",
            extra={"collection": name, "dimension": dim},
        )
    else:
        info = await client.get_collection(name)
        cfg = info.config.params.vectors
        size = cfg.size if hasattr(cfg, "size") else None
        if size is not None and size != dim:
            logger.warning(
                "Qdrant collection dimension mismatch",
                extra={
                    "collection": name,
                    "configured": dim,
                    "existing": size,
                },
            )

    _notes_collection_ready = True


async def ensure_files_collection() -> None:
    """
    Create files_chunks collection if missing (idempotent per process).
    Vector size must match settings.EMBEDDING_DIMENSION.
    """
    global _files_collection_ready
    if _files_collection_ready:
        return

    settings = get_settings()
    if not settings.qdrant_enabled:
        logger.debug("Qdrant disabled — skipping files collection ensure")
        return

    client = await get_async_qdrant_client()
    name = settings.QDRANT_FILES_COLLECTION
    dim = settings.EMBEDDING_DIMENSION

    exists = await client.collection_exists(name)
    if not exists:
        await client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )
        logger.info(
            "Qdrant collection created",
            extra={"collection": name, "dimension": dim},
        )
    else:
        info = await client.get_collection(name)
        cfg = info.config.params.vectors
        size = cfg.size if hasattr(cfg, "size") else None
        if size is not None and size != dim:
            logger.warning(
                "Qdrant collection dimension mismatch",
                extra={
                    "collection": name,
                    "configured": dim,
                    "existing": size,
                },
            )

    _files_collection_ready = True
