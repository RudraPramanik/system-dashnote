"""
POST /ai/feedback — attach user quality signal to a Langfuse trace.

Workspace identity comes from JWT wid only. Existing chat/agent clients
never need this route.
"""
from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from ai_memory.repository import ThreadRepository
from core.database.session import get_session
from core.security.context import RequestContext
from core.security.dependency import get_current_context
from observability.tracing import lookup_thread_trace, score_by_trace_id

router = APIRouter(prefix="/ai", tags=["ai-feedback"])
_repo = ThreadRepository()


class FeedbackRequest(BaseModel):
    thread_id: str = Field(..., min_length=1)
    thumbs: Literal["up", "down"] | None = None
    score: int | None = Field(default=None, ge=1, le=5)
    trace_id: str | None = None

    @model_validator(mode="after")
    def _require_signal(self) -> FeedbackRequest:
        if self.thumbs is None and self.score is None:
            raise ValueError("Provide thumbs (up|down) or score (1-5)")
        return self


class FeedbackResponse(BaseModel):
    status: Literal["ok"] = "ok"
    tracing: Literal["recorded", "unavailable"]


def _score_value(body: FeedbackRequest) -> float | int:
    if body.score is not None:
        return body.score
    return 1 if body.thumbs == "up" else 0


def _score_comment(body: FeedbackRequest) -> str:
    if body.thumbs is not None:
        return f"user_feedback thumbs={body.thumbs}"
    return f"user_feedback score={body.score}"


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    body: FeedbackRequest,
    ctx: RequestContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_session),
) -> FeedbackResponse:
    workspace_id = str(ctx.workspace_id)
    try:
        UUID(body.thread_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found",
        ) from exc

    thread = await _repo.get_thread(
        db,
        thread_id=body.thread_id,
        workspace_id=workspace_id,
    )
    if thread is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found",
        )

    trace_id = (body.trace_id or "").strip() or lookup_thread_trace(
        workspace_id, body.thread_id
    )
    if not trace_id:
        return FeedbackResponse(tracing="unavailable")

    recorded = score_by_trace_id(
        trace_id,
        name="user_feedback",
        value=_score_value(body),
        comment=_score_comment(body),
    )
    return FeedbackResponse(tracing="recorded" if recorded else "unavailable")
