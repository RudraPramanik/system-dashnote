"""
Workspace-scoped Qdrant indexing (upsert/delete).

workspace_id is bound at construction (from RequestContext in HTTP,
from IndexingRequest in the worker). Vector search uses ai.retrieval.wrapper.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    FilterSelector,
)

from ai.embeddings.base import EmbeddedChunk
from ai.retrieval.client import get_async_qdrant_client
from ai.retrieval.collection import ensure_files_collection, ensure_notes_collection
from ai.retrieval.errors import VectorStoreError
from config import get_settings

logger = logging.getLogger(__name__)


class WorkspaceVectorIndex:
    """
    Qdrant upsert/delete for one workspace (indexing only — not search).

    Construct with workspace_id from trusted server context only.
    Vector search must use ai.retrieval.wrapper.WorkspaceVectorSearch.
    """

    def __init__(
        self,
        workspace_id: str,
        *,
        client: AsyncQdrantClient | None = None,
    ) -> None:
        if not str(workspace_id).strip():
            raise ValueError("workspace_id is required for WorkspaceVectorIndex")
        self._workspace_id = str(workspace_id)
        self._client = client

    async def _client_or_get(self) -> AsyncQdrantClient:
        if self._client is not None:
            return self._client
        return await get_async_qdrant_client()

    @property
    def workspace_id(self) -> str:
        return self._workspace_id

    async def upsert_chunks(self, chunks: list[EmbeddedChunk]) -> int:
        """Replace vectors for chunks; caller should delete stale note points first."""
        if not chunks:
            return 0

        for chunk in chunks:
            if str(chunk.workspace_id) != self._workspace_id:
                raise ValueError(
                    f"chunk workspace_id {chunk.workspace_id!r} does not match "
                    f"search scope {self._workspace_id!r}"
                )

        settings = get_settings()
        await ensure_notes_collection()
        client = await self._client_or_get()

        points: list[PointStruct] = []
        for chunk in chunks:
            point_id = str(uuid.UUID(chunk.chunk_id))
            visibility = "private" if chunk.is_private else "public"
            title = str((chunk.metadata or {}).get("title", ""))
            payload: dict[str, Any] = {
                "workspace_id": self._workspace_id,
                "note_id": chunk.note_id,
                "chunk_id": chunk.chunk_id,
                "chunk_index": chunk.chunk_index,
                "chunk_text": chunk.chunk_text,
                "text": chunk.chunk_text,
                "title": title,
                "created_by": chunk.created_by,
                "visibility": visibility,
                "is_private": chunk.is_private,
                "token_count": chunk.token_count,
                **(chunk.metadata or {}),
            }
            points.append(
                PointStruct(
                    id=point_id,
                    vector=chunk.vector,
                    payload=payload,
                )
            )

        try:
            await client.upsert(
                collection_name=settings.QDRANT_NOTES_COLLECTION,
                points=points,
                wait=True,
            )
        except Exception as e:
            raise VectorStoreError(
                f"Qdrant upsert failed: {e}", retryable=True
            ) from e

        logger.info(
            "Qdrant upsert complete",
            extra={
                "workspace_id": self._workspace_id,
                "points": len(points),
                "collection": settings.QDRANT_NOTES_COLLECTION,
            },
        )
        return len(points)

    async def delete_note_vectors(self, note_id: str) -> None:
        """Remove all chunk points for a note within this workspace."""
        settings = get_settings()
        await ensure_notes_collection()
        client = await self._client_or_get()

        note_filter = Filter(
            must=[
                FieldCondition(
                    key="workspace_id",
                    match=MatchValue(value=self._workspace_id),
                ),
                FieldCondition(
                    key="note_id",
                    match=MatchValue(value=note_id),
                ),
            ]
        )

        try:
            await client.delete(
                collection_name=settings.QDRANT_NOTES_COLLECTION,
                points_selector=FilterSelector(filter=note_filter),
                wait=True,
            )
        except Exception as e:
            raise VectorStoreError(
                f"Qdrant delete failed: {e}", retryable=True
            ) from e

        logger.info(
            "Qdrant note vectors deleted",
            extra={
                "workspace_id": self._workspace_id,
                "note_id": note_id,
            },
        )


class WorkspaceFileVectorIndex:
    """
    Qdrant upsert/delete for file chunks in one workspace (indexing only).

    EmbeddedChunk.note_id carries file_id when indexing files (Slice 7).
    """

    def __init__(
        self,
        workspace_id: str,
        *,
        client: AsyncQdrantClient | None = None,
    ) -> None:
        if not str(workspace_id).strip():
            raise ValueError("workspace_id is required for WorkspaceFileVectorIndex")
        self._workspace_id = str(workspace_id)
        self._client = client

    async def _client_or_get(self) -> AsyncQdrantClient:
        if self._client is not None:
            return self._client
        return await get_async_qdrant_client()

    @property
    def workspace_id(self) -> str:
        return self._workspace_id

    async def upsert_chunks(self, chunks: list[EmbeddedChunk]) -> int:
        """Replace vectors for file chunks; caller should delete stale file points first."""
        if not chunks:
            return 0

        for chunk in chunks:
            if str(chunk.workspace_id) != self._workspace_id:
                raise ValueError(
                    f"chunk workspace_id {chunk.workspace_id!r} does not match "
                    f"search scope {self._workspace_id!r}"
                )

        settings = get_settings()
        await ensure_files_collection()
        client = await self._client_or_get()

        points: list[PointStruct] = []
        for chunk in chunks:
            point_id = str(uuid.UUID(chunk.chunk_id))
            visibility = "private" if chunk.is_private else "public"
            title = str((chunk.metadata or {}).get("title", ""))
            payload: dict[str, Any] = {
                "workspace_id": self._workspace_id,
                "file_id": chunk.note_id,
                "chunk_id": chunk.chunk_id,
                "chunk_index": chunk.chunk_index,
                "chunk_text": chunk.chunk_text,
                "text": chunk.chunk_text,
                "title": title,
                "created_by": chunk.created_by,
                "visibility": visibility,
                "is_private": chunk.is_private,
                "token_count": chunk.token_count,
                **(chunk.metadata or {}),
            }
            points.append(
                PointStruct(
                    id=point_id,
                    vector=chunk.vector,
                    payload=payload,
                )
            )

        try:
            await client.upsert(
                collection_name=settings.QDRANT_FILES_COLLECTION,
                points=points,
                wait=True,
            )
        except Exception as e:
            raise VectorStoreError(
                f"Qdrant upsert failed: {e}", retryable=True
            ) from e

        logger.info(
            "Qdrant file upsert complete",
            extra={
                "workspace_id": self._workspace_id,
                "points": len(points),
                "collection": settings.QDRANT_FILES_COLLECTION,
            },
        )
        return len(points)

    async def delete_file_vectors(self, file_id: str) -> None:
        """Remove all chunk points for a file within this workspace."""
        settings = get_settings()
        await ensure_files_collection()
        client = await self._client_or_get()

        file_filter = Filter(
            must=[
                FieldCondition(
                    key="workspace_id",
                    match=MatchValue(value=self._workspace_id),
                ),
                FieldCondition(
                    key="file_id",
                    match=MatchValue(value=file_id),
                ),
            ]
        )

        try:
            await client.delete(
                collection_name=settings.QDRANT_FILES_COLLECTION,
                points_selector=FilterSelector(filter=file_filter),
                wait=True,
            )
        except Exception as e:
            raise VectorStoreError(
                f"Qdrant delete failed: {e}", retryable=True
            ) from e

        logger.info(
            "Qdrant file vectors deleted",
            extra={
                "workspace_id": self._workspace_id,
                "file_id": file_id,
            },
        )


if __name__ == "__main__":
    import asyncio
    import os
    import sys

    _src = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    _root = os.path.dirname(_src)
    if _src not in sys.path:
        sys.path.insert(0, _src)
    os.chdir(_root)

    async def _validate() -> None:
        from config import get_settings as gs

        if not gs().qdrant_enabled:
            print("SKIP: QDRANT_URL not set")
            return

        await ensure_notes_collection()
        index = WorkspaceVectorIndex("validate-ws-001")
        await index.delete_note_vectors("validate-note-001")
        print("PASS: WorkspaceVectorIndex collection + delete OK")

    asyncio.run(_validate())
