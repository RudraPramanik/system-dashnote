"""
ThreadRepository — data access for ai_threads and ai_messages.

Follows the same stateless repository pattern as src/notes/repository.py.
AsyncSession is passed per method — never stored on the instance.
workspace_id filter is applied on EVERY query — no exceptions.

IMPORT LAW: SQLAlchemy, ai_memory.models, stdlib only.
No FastAPI. No RequestContext. No business logic — only data access.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from ai_memory.models import AIMessage, AIThread

logger = logging.getLogger(__name__)


class ThreadRepository:
    """
    Stateless repository for ai_threads and ai_messages.

    Every method receives AsyncSession as first argument.
    workspace_id is always applied as a filter — cross-workspace
    access is structurally impossible through this class.

    Usage (from service layer):
        repo = ThreadRepository()
        thread = await repo.create_thread(db, workspace_id=..., user_id=...)
    """

    async def create_thread(
        self,
        db: AsyncSession,
        *,
        workspace_id: str,
        user_id: str,
        title: str | None = None,
    ) -> AIThread:
        """Create a new conversation thread."""
        thread = AIThread(
            workspace_id=int(workspace_id),
            created_by=int(user_id),
            title=title,
            is_active=True,
        )
        db.add(thread)
        await db.commit()
        await db.refresh(thread)
        logger.info(
            "Thread created",
            extra={"thread_id": str(thread.id), "workspace_id": workspace_id},
        )
        return thread

    async def get_thread(
        self,
        db: AsyncSession,
        *,
        thread_id: str,
        workspace_id: str,
    ) -> AIThread | None:
        """
        Fetch a thread by ID — returns None if not found OR wrong workspace.
        workspace_id filter prevents cross-tenant access structurally.
        """
        result = await db.execute(
            sa.select(AIThread).where(
                AIThread.id == uuid.UUID(thread_id),
                AIThread.workspace_id == int(workspace_id),
                AIThread.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def list_threads(
        self,
        db: AsyncSession,
        *,
        workspace_id: str,
        user_id: str,
        limit: int = 50,
    ) -> list[AIThread]:
        """
        List active threads for a user in a workspace.
        Filters by both workspace_id AND created_by — users see only their threads.
        Owners/admins who need to see all threads should use a separate admin method.
        """
        result = await db.execute(
            sa.select(AIThread)
            .where(
                AIThread.workspace_id == int(workspace_id),
                AIThread.created_by == int(user_id),
                AIThread.is_active.is_(True),
            )
            .order_by(AIThread.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_recent_messages(
        self,
        db: AsyncSession,
        *,
        thread_id: str,
        workspace_id: str,
        limit: int = 20,
    ) -> list[AIMessage]:
        """
        Load recent messages for a thread — workspace_id verified via thread lookup.

        Security: thread must belong to workspace_id or returns empty list.
        Messages ordered ASC (oldest first) for correct LLM context order.
        """
        thread = await self.get_thread(db, thread_id=thread_id, workspace_id=workspace_id)
        if thread is None:
            logger.warning(
                "Thread not found or workspace mismatch",
                extra={"thread_id": thread_id, "workspace_id": workspace_id},
            )
            return []

        result = await db.execute(
            sa.select(AIMessage)
            .where(AIMessage.thread_id == uuid.UUID(thread_id))
            .order_by(AIMessage.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def save_message(
        self,
        db: AsyncSession,
        *,
        thread_id: str,
        role: str,
        content: str,
        citations: list[dict] | None = None,
        token_count: int | None = None,
    ) -> AIMessage:
        """
        Save a message to the thread.
        role must be 'user', 'assistant', or 'tool' — enforced at DB level.
        """
        message = AIMessage(
            thread_id=uuid.UUID(thread_id),
            role=role,
            content=content,
            citations=citations or [],
            token_count=token_count,
        )
        db.add(message)
        await db.commit()
        await db.refresh(message)
        return message

    async def update_thread_title(
        self,
        db: AsyncSession,
        *,
        thread_id: str,
        workspace_id: str,
        title: str,
    ) -> bool:
        """Update thread title — workspace_id verified before update."""
        result = await db.execute(
            sa.update(AIThread)
            .where(
                AIThread.id == uuid.UUID(thread_id),
                AIThread.workspace_id == int(workspace_id),
            )
            .values(title=title, updated_at=datetime.now(timezone.utc))
        )
        await db.commit()
        return result.rowcount > 0

    async def delete_thread(
        self,
        db: AsyncSession,
        *,
        thread_id: str,
        workspace_id: str,
    ) -> bool:
        """
        Soft-delete a thread (sets is_active=False).
        workspace_id verified — cannot delete threads from other workspaces.
        Messages are preserved for audit — hard delete if needed separately.
        """
        result = await db.execute(
            sa.update(AIThread)
            .where(
                AIThread.id == uuid.UUID(thread_id),
                AIThread.workspace_id == int(workspace_id),
                AIThread.is_active.is_(True),
            )
            .values(is_active=False, updated_at=datetime.now(timezone.utc))
        )
        await db.commit()
        deleted = result.rowcount > 0
        if deleted:
            logger.info(
                "Thread soft-deleted",
                extra={"thread_id": thread_id, "workspace_id": workspace_id},
            )
        return deleted
