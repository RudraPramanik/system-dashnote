"""
AI test routes — mounted at /ai (e.g. POST /ai/test-search).

workspace_id is always taken from RequestContext, never from the request body.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from ai.embeddings.factory import get_embedding_provider
from ai.retrieval.collection import ensure_notes_collection
from ai.retrieval.workspace_search import WorkspaceVectorSearch
from ai_search.schemas import TestSearchRequest, TestSearchResponse
from config import get_settings
from core.security.context import RequestContext
from core.security.dependency import get_current_context

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/test-search", response_model=TestSearchResponse)
async def test_search(
    body: TestSearchRequest,
    ctx: RequestContext = Depends(get_current_context),
) -> TestSearchResponse:
    """
    Semantic search over indexed note chunks for the caller's workspace.
    Dev/diagnostic endpoint — requires ai_enabled and Qdrant.
    """
    settings = get_settings()
    if not settings.ai_enabled:
        raise HTTPException(status_code=503, detail="AI features are disabled")
    if not settings.qdrant_enabled:
        raise HTTPException(status_code=503, detail="Vector store is not configured")

    await ensure_notes_collection()
    provider = await get_embedding_provider()
    vectors = await provider.embed_texts([body.query_text.strip()])
    if not vectors:
        raise HTTPException(status_code=502, detail="Embedding provider returned no vector")

    workspace_id = str(ctx.workspace_id)
    search = WorkspaceVectorSearch(workspace_id)
    results = await search.search_similar(
        vectors[0],
        limit=body.limit,
        user_id=str(ctx.user_id),
        role=ctx.role,
    )

    logger.info(
        "test_search complete",
        extra={
            "workspace_id": workspace_id,
            "user_id": ctx.user_id,
            "hits": len(results),
            "limit": body.limit,
        },
    )
    return TestSearchResponse(results=results)
