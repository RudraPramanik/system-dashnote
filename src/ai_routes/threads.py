"""
Thread management routes for DashNoteSystem AI conversations.

GET    /ai/threads                     — list user's threads
GET    /ai/threads/{thread_id}/messages — load messages for a thread
PATCH  /ai/threads/{thread_id}         — rename a thread
DELETE /ai/threads/{thread_id}         — soft-delete a thread

SECURITY: workspace_id always from RequestContext (JWT wid claim).
          Never from path params or query strings.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.security.dependency import get_current_context
from core.security.context import RequestContext
from core.database.session import get_session
from ai.memory.service import ThreadService
from ai_memory.repository import ThreadRepository

router = APIRouter(prefix="/ai", tags=["ai-threads"])
_repo = ThreadRepository()


# ── Response schemas ─────────────────────────────────────────────────────────

class ThreadResponse(BaseModel):
    id: str
    workspace_id: str
    created_by: str
    title: str | None
    is_active: bool
    created_at: str
    updated_at: str


class MessageResponse(BaseModel):
    id: str
    thread_id: str
    role: str
    content: str
    citations: list[dict]
    token_count: int | None
    created_at: str


class ThreadTitleUpdate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("/threads", response_model=list[ThreadResponse])
async def list_threads(
    ctx: RequestContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_session),
) -> list[ThreadResponse]:
    """
    List the authenticated user's active conversation threads.
    Scoped to workspace_id from JWT — never shows other workspaces.
    """
    workspace_id = str(ctx.workspace_id)
    user_id = str(ctx.user_id)

    threads = await _repo.list_threads(
        db,
        workspace_id=workspace_id,
        user_id=user_id,
    )
    return [
        ThreadResponse(
            id=str(t.id),
            workspace_id=str(t.workspace_id),
            created_by=str(t.created_by),
            title=t.title,
            is_active=t.is_active,
            created_at=t.created_at.isoformat(),
            updated_at=t.updated_at.isoformat(),
        )
        for t in threads
    ]


@router.get("/threads/{thread_id}/messages", response_model=list[MessageResponse])
async def get_thread_messages(
    thread_id: str,
    ctx: RequestContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_session),
) -> list[MessageResponse]:
    """
    Load messages for a thread.
    Security: thread must belong to ctx.workspace_id — verified in repository.
    Returns 404 if thread not found or belongs to different workspace.
    """
    workspace_id = str(ctx.workspace_id)

    messages = await _repo.get_recent_messages(
        db,
        thread_id=thread_id,
        workspace_id=workspace_id,
        limit=50,
    )

    if not messages:
        # Could be empty thread or wrong workspace — same 404 response
        # (don't reveal whether thread exists in another workspace)
        thread = await _repo.get_thread(db, thread_id=thread_id, workspace_id=workspace_id)
        if thread is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thread not found.",
            )

    return [
        MessageResponse(
            id=str(m.id),
            thread_id=str(m.thread_id),
            role=m.role,
            content=m.content,
            citations=m.citations or [],
            token_count=m.token_count,
            created_at=m.created_at.isoformat(),
        )
        for m in messages
    ]


@router.patch("/threads/{thread_id}", response_model=ThreadResponse)
async def rename_thread(
    thread_id: str,
    body: ThreadTitleUpdate,
    ctx: RequestContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_session),
) -> ThreadResponse:
    """
    Rename a conversation thread.
    Security: only the JWT workspace can update the thread.
    Empty/whitespace titles are rejected by schema + service.
    """
    workspace_id = str(ctx.workspace_id)
    title = body.title.strip()
    if not title:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Title must not be empty.",
        )

    thread = await _repo.get_thread(
        db, thread_id=thread_id, workspace_id=workspace_id
    )
    if thread is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found.",
        )

    ok = await ThreadService().rename_thread(
        db,
        thread_id=thread_id,
        workspace_id=workspace_id,
        title=title,
    )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found.",
        )

    refreshed = await _repo.get_thread(
        db, thread_id=thread_id, workspace_id=workspace_id
    )
    if refreshed is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found.",
        )

    return ThreadResponse(
        id=str(refreshed.id),
        workspace_id=str(refreshed.workspace_id),
        created_by=str(refreshed.created_by),
        title=refreshed.title,
        is_active=refreshed.is_active,
        created_at=refreshed.created_at.isoformat(),
        updated_at=refreshed.updated_at.isoformat(),
    )


@router.delete("/threads/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_thread(
    thread_id: str,
    ctx: RequestContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_session),
) -> None:
    """
    Soft-delete a conversation thread.
    Security: only the thread's workspace can delete it.
    Returns 404 if not found — same response for security (no enumeration).
    """
    workspace_id = str(ctx.workspace_id)

    deleted = await _repo.delete_thread(
        db,
        thread_id=thread_id,
        workspace_id=workspace_id,
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found.",
        )
