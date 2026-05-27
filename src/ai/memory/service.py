"""
ThreadService — business logic layer for conversation threads.

Thin layer over ThreadRepository. Handles:
  - Thread creation with automatic title generation
  - Loading history for context injection
  - Persisting messages after each response
  - Workspace isolation enforcement

IMPORT LAW: ai_memory.repository, config, stdlib only.
No SQLAlchemy imports. No FastAPI. No RequestContext.
AsyncSession passed per method — never stored.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ai_memory.repository import ThreadRepository
from config import get_settings

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from ai_memory.models import AIThread, AIMessage

logger = logging.getLogger(__name__)

# Module-level singleton repository
_repo = ThreadRepository()


class ThreadService:
    """
    Business logic for conversation thread management.

    All methods accept AsyncSession as first parameter — never stored.
    workspace_id is enforced on every operation via ThreadRepository.

    LangGraph note (Slice 6):
        This service manages the PRODUCT layer (what users see).
        LangGraph's AsyncPostgresSaver manages the EXECUTION layer.
        They are linked only by thread_id string — no FK or direct coupling.
    """

    async def get_or_create_thread(
        self,
        db: "AsyncSession",
        *,
        thread_id: str | None,
        workspace_id: str,
        user_id: str,
    ) -> "AIThread":
        """
        Return existing thread or create a new one.

        If thread_id is provided: verify it belongs to workspace_id.
        If thread_id is None: create a new thread.
        Security: thread from wrong workspace raises ValueError.
        """
        if thread_id:
            thread = await _repo.get_thread(
                db,
                thread_id=thread_id,
                workspace_id=workspace_id,
            )
            if thread is None:
                raise ValueError(
                    f"Thread {thread_id} not found or does not belong to workspace {workspace_id}. "
                    "Cross-workspace thread access is not permitted."
                )
            return thread

        # Create new thread
        return await _repo.create_thread(
            db,
            workspace_id=workspace_id,
            user_id=user_id,
        )

    async def load_history_as_messages(
        self,
        db: "AsyncSession",
        *,
        thread_id: str,
        workspace_id: str,
    ) -> list[dict]:
        """
        Load recent messages formatted for LiteLLM messages array.

        Returns list of {"role": str, "content": str} dicts,
        ordered oldest first — correct order for LLM context.
        Workspace isolation enforced via ThreadRepository.
        """
        settings = get_settings()
        messages = await _repo.get_recent_messages(
            db,
            thread_id=thread_id,
            workspace_id=workspace_id,
            limit=settings.AI_THREAD_MESSAGE_LIMIT,
        )
        return [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

    async def persist_turn(
        self,
        db: "AsyncSession",
        *,
        thread_id: str,
        user_question: str,
        assistant_answer: str,
        citations: list[dict],
        token_count: int | None = None,
    ) -> None:
        """
        Save both the user message and assistant response to the thread.

        Called AFTER the LLM response is complete (or stream finishes).
        Never called before — partial responses are not persisted.
        """
        await _repo.save_message(
            db,
            thread_id=thread_id,
            role="user",
            content=user_question,
        )
        await _repo.save_message(
            db,
            thread_id=thread_id,
            role="assistant",
            content=assistant_answer,
            citations=citations,
            token_count=token_count,
        )
        logger.debug(
            "Conversation turn persisted",
            extra={"thread_id": thread_id},
        )
