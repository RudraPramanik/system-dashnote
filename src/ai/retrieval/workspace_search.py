"""
Workspace-scoped Qdrant access.

workspace_id is bound at construction (from RequestContext in HTTP,
from IndexingRequest in the worker). Every query includes a mandatory
workspace_id filter — never accept workspace_id from user input on search.
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
from ai.retrieval.collection import ensure_notes_collection
from ai.retrieval.errors import VectorStoreError
from config import get_settings
from shared.schemas.note import NoteChunk
from shared.schemas.retrieval import RetrievalResult

logger = logging.getLogger(__name__)


def _workspace_must_filter(workspace_id: str) -> Filter:
    return Filter(
        must=[
            FieldCondition(
                key="workspace_id",
                match=MatchValue(value=workspace_id),
            )
        ]
    )


def _rbac_filter(workspace_id: str, user_id: str, role: str) -> Filter:
    """Tenant filter plus note visibility for members."""
    if role in ("owner", "admin"):
        return _workspace_must_filter(workspace_id)
    return Filter(
        must=[
            FieldCondition(
                key="workspace_id",
                match=MatchValue(value=workspace_id),
            ),
            Filter(
                should=[
                    FieldCondition(
                        key="is_private",
                        match=MatchValue(value=False),
                    ),
                    FieldCondition(
                        key="created_by",
                        match=MatchValue(value=user_id),
                    ),
                ],
                min_should=1,
            ),
        ]
    )


class WorkspaceVectorSearch:
    """
    All Qdrant reads/writes for one workspace.

    Construct with workspace_id from trusted server context only.
    """

    def __init__(
        self,
        workspace_id: str,
        *,
        client: AsyncQdrantClient | None = None,
    ) -> None:
        if not str(workspace_id).strip():
            raise ValueError("workspace_id is required for WorkspaceVectorSearch")
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
            payload: dict[str, Any] = {
                "workspace_id": self._workspace_id,
                "note_id": chunk.note_id,
                "chunk_id": chunk.chunk_id,
                "chunk_index": chunk.chunk_index,
                "chunk_text": chunk.chunk_text,
                "created_by": chunk.created_by,
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

    async def search_similar(
        self,
        query_vector: list[float],
        *,
        limit: int = 5,
        user_id: str,
        role: str,
    ) -> list[RetrievalResult]:
        """Vector search scoped to workspace_id with RBAC payload filters."""
        settings = get_settings()
        await ensure_notes_collection()
        client = await self._client_or_get()

        query_filter = _rbac_filter(self._workspace_id, user_id, role)

        try:
            response = await client.query_points(
                collection_name=settings.QDRANT_NOTES_COLLECTION,
                query=query_vector,
                query_filter=query_filter,
                limit=limit,
                with_payload=True,
            )
            hits = response.points
        except Exception as e:
            raise VectorStoreError(
                f"Qdrant search failed: {e}", retryable=True
            ) from e

        results: list[RetrievalResult] = []
        for hit in hits:
            payload = hit.payload or {}
            if str(payload.get("workspace_id")) != self._workspace_id:
                logger.warning(
                    "Skipping hit with mismatched workspace_id",
                    extra={
                        "expected": self._workspace_id,
                        "got": payload.get("workspace_id"),
                    },
                )
                continue

            chunk = NoteChunk(
                chunk_id=str(payload.get("chunk_id", hit.id)),
                note_id=str(payload.get("note_id", "")),
                workspace_id=self._workspace_id,
                text=str(payload.get("chunk_text", "")),
                index=int(payload.get("chunk_index", 0)),
            )
            meta = {
                k: v
                for k, v in payload.items()
                if k
                not in (
                    "chunk_text",
                    "chunk_id",
                    "note_id",
                    "workspace_id",
                    "chunk_index",
                )
            }
            results.append(
                RetrievalResult(
                    score=float(hit.score or 0.0),
                    content_chunk=chunk,
                    metadata=meta,
                )
            )

        return results


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
        search = WorkspaceVectorSearch("validate-ws-001")
        await search.delete_note_vectors("validate-note-001")
        print("PASS: WorkspaceVectorSearch collection + delete OK")

    asyncio.run(_validate())
