"""
Ensure notes_chunks / files_chunks collections exist with payload indexes.

Qdrant Cloud requires keyword indexes for filtered delete/search. Creating the
collection alone is not enough — missing workspace_id (etc.) indexes break
indexing and RAG.
"""
from __future__ import annotations

import logging
from typing import Iterable

from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import Distance, PayloadSchemaType, VectorParams

from ai.retrieval.client import get_async_qdrant_client
from config import get_settings

logger = logging.getLogger(__name__)

_notes_collection_ready = False
_files_collection_ready = False

# Fields used in Filter must=/should for delete + RBAC search.
_NOTES_PAYLOAD_INDEXES: tuple[str, ...] = (
    "workspace_id",
    "note_id",
    "created_by",
    "visibility",
)
_FILES_PAYLOAD_INDEXES: tuple[str, ...] = (
    "workspace_id",
    "file_id",
    "created_by",
    "visibility",
)


def _reset_collection_ready_flags_for_tests() -> None:
    """Test helper — do not call from production paths."""
    global _notes_collection_ready, _files_collection_ready
    _notes_collection_ready = False
    _files_collection_ready = False


async def _ensure_payload_indexes(
    client: object,
    *,
    collection_name: str,
    field_names: Iterable[str],
) -> None:
    """Create keyword payload indexes if missing (idempotent)."""
    info = await client.get_collection(collection_name)  # type: ignore[attr-defined]
    existing = set(getattr(info, "payload_schema", None) or {})

    for field_name in field_names:
        if field_name in existing:
            continue
        try:
            await client.create_payload_index(  # type: ignore[attr-defined]
                collection_name=collection_name,
                field_name=field_name,
                field_schema=PayloadSchemaType.KEYWORD,
            )
            logger.info(
                "Qdrant payload index created",
                extra={"collection": collection_name, "field": field_name},
            )
        except UnexpectedResponse as exc:
            # Concurrent ensure / already exists — safe to continue.
            detail = str(exc).lower()
            if "already" in detail or "exists" in detail:
                logger.debug(
                    "Qdrant payload index already present",
                    extra={"collection": collection_name, "field": field_name},
                )
                continue
            raise


async def ensure_notes_collection() -> None:
    """
    Create notes_chunks collection if missing (idempotent per process).
    Vector size must match settings.EMBEDDING_DIMENSION (3072 for gemini-embedding-2).
    Ensures keyword payload indexes required for filtered delete/search.
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

    await _ensure_payload_indexes(
        client,
        collection_name=name,
        field_names=_NOTES_PAYLOAD_INDEXES,
    )
    _notes_collection_ready = True


async def ensure_files_collection() -> None:
    """
    Create files_chunks collection if missing (idempotent per process).
    Vector size must match settings.EMBEDDING_DIMENSION.
    Ensures keyword payload indexes required for filtered delete/search.
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

    await _ensure_payload_indexes(
        client,
        collection_name=name,
        field_names=_FILES_PAYLOAD_INDEXES,
    )
    _files_collection_ready = True
