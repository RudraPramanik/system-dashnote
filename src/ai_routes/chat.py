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

import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.session import get_session
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
    thread_id: str | None = Field(
        default=None,
        description="Optional conversation thread UUID. Omit to start a new thread.",
    )


class ChatResponse(BaseModel):
    """
    Response from /ai/chat.

    answer:     Markdown-formatted answer grounded in workspace notes.
    citations:  Source notes used to formulate the answer.

    thread_id: conversation thread UUID (new or continued).
    """
    answer: str
    citations: list[Citation]
    chunks_retrieved: int
    chunks_used: int
    latency_ms: float
    thread_id: str | None = None


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
    db: AsyncSession = Depends(get_session),
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
        thread_id=body.thread_id,
        db=db,
    )

    return ChatResponse(
        answer=result.answer,
        citations=result.citations,
        chunks_retrieved=result.chunks_retrieved,
        chunks_used=result.chunks_used,
        latency_ms=result.latency_ms,
        thread_id=result.thread_id,
    )


@router.post(
    "/chat/stream",
    summary="Stream a workspace question answer (SSE)",
    description=(
        "Server-Sent Events streaming version of /ai/chat. "
        "Yields token chunks progressively, then a final metadata event "
        "with citations. Use /ai/chat for non-streaming clients."
    ),
    response_class=StreamingResponse,
)
async def chat_stream(
    body: ChatRequest,
    ctx: RequestContext = Depends(get_current_context),
    rag: RagService = Depends(get_rag_service),
    db: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    """
    Stream a RAG answer using Server-Sent Events.

    Event format:
        data: {"type": "token", "content": "..."}\n\n
        data: {"type": "token", "content": "..."}\n\n
        ... (one event per token)
        data: {"type": "metadata", "citations": [...], "latency_ms": N}\n\n
        data: [DONE]\n\n

    Security:
        ctx.workspace_id sourced from JWT — never from request body.
        Frozen to plain string BEFORE generator opens — ctx never
        referenced inside generate() to prevent mid-stream access issues.

    Nginx note:
        X-Accel-Buffering: no disables Nginx proxy buffering.
        Cache-Control: no-cache prevents intermediate caching.
        Both headers are required for tokens to stream progressively.

    LangGraph note:
        rag.stream_answer() is also callable from agent tools in Slice 6.
        The HTTP wrapper here does not affect the service signature.
    """
    # ── Step 1: Freeze security context BEFORE generator opens ──────────────
    # ctx must never be referenced inside generate().
    # Plain string primitives are safe to use inside async generators.
    workspace_id = str(ctx.workspace_id)   # from JWT wid claim
    user_id = str(ctx.user_id)             # from JWT sub claim
    role = ctx.role                         # "owner" | "admin" | "member"
    thread_id = body.thread_id

    # ── Step 2: Resolve service singleton BEFORE generator opens ────────────
    # get_rag_service() is already called via Depends(get_rag_service) above.
    # rag is captured by closure — no instantiation inside generate().

    async def generate():
        """
        SSE generator — yields data: {...}\\n\\n frames.

        Security: only frozen primitives (workspace_id, user_id, role) used.
        ctx is never referenced here. rag singleton captured by closure.
        """
        try:
            async for event in rag.stream_answer(
                question=body.message,
                workspace_id=workspace_id,
                user_id=user_id,
                role=role,
                thread_id=thread_id,
                db=db,
            ):
                # Serialize StreamToken or StreamMetadata to JSON
                yield f"data: {event.model_dump_json()}\n\n"

        except Exception:
            # Yield an error event so the client knows the stream failed
            # Never silently drop errors mid-stream
            error_payload = json.dumps({
                "type": "error",
                "message": "Stream encountered an error. Please try again.",
            })
            yield f"data: {error_payload}\n\n"

        finally:
            # Always emit [DONE] — lets client close the EventSource connection
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",           # prevent intermediate caching
            "X-Accel-Buffering": "no",             # disable Nginx proxy buffering
            "Connection": "keep-alive",
            "Transfer-Encoding": "chunked",
        },
    )
