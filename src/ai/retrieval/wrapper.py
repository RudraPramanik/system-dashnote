"""
Tenant-safe Qdrant search wrapper for DashNoteSystem.

WorkspaceVectorSearch is the ONLY interface to Qdrant search in this project.
Raw AsyncQdrantClient.query_points() is NEVER called from routers or services directly.

Why?
The wrapper guarantees workspace_id is always injected from RequestContext.
A developer cannot accidentally perform a cross-tenant search — it is
architecturally impossible without bypassing this class.

IMPORT LAW: Only qdrant_client, ai.retrieval.*, ai.embeddings.*, config, stdlib.
No FastAPI. No SQLAlchemy. No domain repositories.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from qdrant_client.http.models import ScoredPoint

from ai.embeddings.factory import get_embedding_provider
from ai.retrieval.client import get_async_qdrant_client
from ai.retrieval.collection import ensure_notes_collection
from ai.retrieval.filters import build_rbac_filter
from config import get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SearchResult:
    """A single result from vector search — safe to return to any layer."""

    chunk_id: str
    note_id: str
    workspace_id: str
    created_by: str
    visibility: str
    chunk_text: str
    title: str
    chunk_index: int
    score: float


class WorkspaceVectorSearch:
    """
    Tenant-safe semantic search over the notes_chunks collection.

    Instantiate once and reuse — stateless between calls.
    All search calls require workspace_id, user_id, and role
    which are always sourced from RequestContext (JWT claims).

    Usage:
        searcher = WorkspaceVectorSearch()
        results = await searcher.search(
            query_text="project deadline",
            workspace_id=str(ctx.workspace_id),
            user_id=str(ctx.user_id),
            role=ctx.role,
            limit=5,
        )
    """

    async def search(
        self,
        *,
        query_text: str,
        workspace_id: str,
        user_id: str,
        role: str,
        limit: int = 10,
        score_threshold: float = 0.3,
    ) -> list[SearchResult]:
        """
        Perform hybrid-ready semantic search with RBAC enforcement.

        Args:
            query_text:      The user's search question.
            workspace_id:    From RequestContext — never user-supplied.
            user_id:         From RequestContext — never user-supplied.
            role:            From RequestContext — "owner", "admin", "member".
            limit:           Max results to return (1–50).
            score_threshold: Minimum cosine similarity to include (0–1).

        Returns:
            List of SearchResult ordered by relevance score descending.
            All results are guaranteed to belong to workspace_id.
        """
        settings = get_settings()

        provider = await get_embedding_provider()
        query_vector = await provider.embed_single(query_text)

        rbac_filter = build_rbac_filter(
            workspace_id=workspace_id,
            user_id=user_id,
            role=role,
        )

        await ensure_notes_collection()
        client = await get_async_qdrant_client()
        response = await client.query_points(
            collection_name=settings.QDRANT_NOTES_COLLECTION,
            query=query_vector,
            query_filter=rbac_filter,
            limit=limit,
            score_threshold=score_threshold,
            with_payload=True,
        )
        raw_results: list[ScoredPoint] = response.points

        logger.debug(
            "Vector search complete",
            extra={
                "workspace_id": workspace_id,
                "role": role,
                "query_length": len(query_text),
                "results_count": len(raw_results),
            },
        )

        results: list[SearchResult] = []
        for point in raw_results:
            p = point.payload or {}
            chunk_text = str(p.get("text") or p.get("chunk_text") or "")
            results.append(
                SearchResult(
                    chunk_id=str(point.id),
                    note_id=str(p.get("note_id", "")),
                    workspace_id=str(p.get("workspace_id", "")),
                    created_by=str(p.get("created_by", "")),
                    visibility=str(
                        p.get("visibility")
                        or ("private" if p.get("is_private") else "public")
                    ),
                    chunk_text=chunk_text,
                    title=str(p.get("title", "")),
                    chunk_index=int(p.get("chunk_index", 0)),
                    score=round(float(point.score or 0.0), 4),
                )
            )

        return results


_searcher: WorkspaceVectorSearch | None = None


def get_workspace_vector_search() -> WorkspaceVectorSearch:
    """Return the process-wide WorkspaceVectorSearch singleton."""
    global _searcher
    if _searcher is None:
        _searcher = WorkspaceVectorSearch()
    return _searcher
