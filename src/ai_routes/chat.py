"""
AI chat routes for DashNoteSystem.

POST /ai/chat — RAG-powered workspace assistant.

Security model:
  RequestContext is validated by get_current_context (JWT decode).
  workspace_id and user_id are FROZEN to plain strings before any
  service call. ctx is never passed into ai.services.*.

  This pattern is required because:
  1. Security: prevents ctx mutation inside service layer
  2. LangGraph compatibility: RagService.answer() will be called by
     agent tools in Slice 6 — tools pass plain strings, not ctx objects

Slice roadmap for this file:
  Slice 3: POST /ai/chat — basic RAG, no memory, no streaming (current)
  Slice 4: POST /ai/chat/stream — SSE streaming responses
  Slice 5: thread_id added to request/response schemas
  Slice 6: agent routing added alongside direct RAG path
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from core.security.dependency import get_current_context
from core.security.context import RequestContext
from ai.services.rag_service import ChatResult, Citation, get_rag_service, RagService

router = APIRouter(prefix="/ai", tags=["ai-chat"])


# ── Request / response schemas ───────────────────────────────────────────────

class ChatRequest(BaseModel):
    """Input payload for /ai/chat."""
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The user's question about their notes.",
    )


class ChatResponse(BaseModel):
    """
    Response from /ai/chat.

    answer:     Markdown-formatted answer grounded in workspace notes.
    citations:  Source notes used to formulate the answer.

    Slice 5 note: thread_id field will be added here when memory is implemented.
    """
    answer: str
    citations: list[Citation]
    chunks_retrieved: int
    chunks_used: int
    latency_ms: float


# ── Route ────────────────────────────────────────────────────────────────────

@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Ask a question about your workspace notes",
    description=(
        "RAG-powered AI chat. Answers are grounded in your workspace notes. "
        "All responses include citations referencing the source notes used."
    ),
)
async def chat(
    body: ChatRequest,
    ctx: RequestContext = Depends(get_current_context),
    rag: RagService = Depends(get_rag_service),
) -> ChatResponse:
    """
    Answer a workspace question using retrieval-augmented generation.

    Security:
        ctx.workspace_id is sourced from JWT (wid claim) — never from request body.
        Frozen to plain string before service call to prevent HTTP coupling.

    LangGraph compatibility:
        rag.answer() accepts plain strings — identical signature used by
        agent tools in Slice 6. No adapter needed when wiring to LangGraph.
    """
    # Freeze context to plain strings before calling service
    # This is the ONLY place RequestContext is used in the AI chat path
    workspace_id = str(ctx.workspace_id)   # from JWT wid claim
    user_id = str(ctx.user_id)             # from JWT sub claim
    role = ctx.role                         # "owner" | "admin" | "member"

    result: ChatResult = await rag.answer(
        question=body.message,
        workspace_id=workspace_id,
        user_id=user_id,
        role=role,
    )

    return ChatResponse(
        answer=result.answer,
        citations=result.citations,
        chunks_retrieved=result.chunks_retrieved,
        chunks_used=result.chunks_used,
        latency_ms=result.latency_ms,
    )
