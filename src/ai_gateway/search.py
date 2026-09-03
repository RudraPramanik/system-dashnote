"""
Internal AI search routes — DashNoteSystem.

GET /ai/test-search — semantic search validation endpoint.

This route is for engineering validation of retrieval quality.
It returns raw search results including scores for tuning purposes.
Gate before removing or restricting:
  - Cosine similarity scores consistently > 0.4 for relevant queries
  - workspace_id in every result matches the authenticated user's workspace
  - Different workspace JWTs return completely separate result sets

SECURITY: workspace_id is sourced from RequestContext (JWT wid claim) only.
          It is NEVER read from query parameters.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from ai.retrieval.wrapper import SearchResult, get_workspace_vector_search
from config import get_settings
from core.security.context import RequestContext
from core.security.dependency import get_current_context

router = APIRouter(prefix="/ai", tags=["ai-internal"])


@router.get(
    "/test-search",
    response_model=list[dict],
    summary="Internal: validate semantic search quality",
    description=(
        "Engineering validation endpoint. "
        "Returns raw vector search results with scores. "
        "workspace_id is always from JWT — never from query params."
    ),
)
async def test_search(
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    limit: int = Query(default=5, ge=1, le=20, description="Max results"),
    ctx: RequestContext = Depends(get_current_context),
) -> list[dict]:
    """
    Run semantic search against notes_chunks and files_chunks.

    Security:
        workspace_id sourced from JWT (ctx.workspace_id) — not from query.
        RBAC filter applied: member sees own + public only.
        Owner/admin sees all notes in their workspace.

    Quality gate thresholds:
        score > 0.5 = strong semantic match
        score 0.3–0.5 = moderate match
        score < 0.3 = filtered out (score_threshold in wrapper)
    """
    settings = get_settings()
    if not settings.ai_enabled:
        raise HTTPException(status_code=503, detail="AI features are disabled")
    if not settings.qdrant_enabled:
        raise HTTPException(status_code=503, detail="Vector store is not configured")

    searcher = get_workspace_vector_search()

    results: list[SearchResult] = await searcher.search(
        query_text=q,
        workspace_id=str(ctx.workspace_id),
        user_id=str(ctx.user_id),
        role=ctx.role,
        limit=limit,
    )

    return [
        {
            "chunk_id": r.chunk_id,
            "note_id": r.note_id,
            "file_id": r.file_id,
            "source_type": r.source_type,
            "title": r.title,
            "chunk_text": r.chunk_text[:200],
            "score": r.score,
            "visibility": r.visibility,
            "chunk_index": r.chunk_index,
            "workspace_id": r.workspace_id,
        }
        for r in results
    ]
