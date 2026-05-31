"""
NoteService — thin service layer over notes/repository.py.

Exists so LangGraph agent tools can create and update notes
without importing SQLAlchemy or domain repositories directly.

This service accepts AsyncSession per method — never stored.
It accepts plain strings for IDs — converts to int internally.

CRITICAL: Read src/notes/repository.py to match method signatures exactly.
This file adapts the existing repository to an agent-callable interface.

IMPORT LAW: notes.repository, core.database.session, stdlib, pydantic only.
No FastAPI. No RequestContext. AsyncSession injected per method.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from notes.repository import NoteRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class NoteService:
    """
    Agent-callable note operations.

    All methods accept AsyncSession as first parameter and plain
    string IDs — never SQLAlchemy models or RequestContext objects.

    LangGraph tools call this service. Tools never call the repository directly.
    This enforces the tool → service → repository chain.

    NoteRepository is tenant-scoped: instantiated per call with session + workspace_id.
    """

    async def create_note(
        self,
        db: "AsyncSession",
        *,
        title: str,
        content: str,
        workspace_id: str,
        created_by: str,
        is_private: bool = False,
    ) -> dict:
        """
        Create a new note.
        Returns dict with note_id and title for tool confirmation.
        """
        # IMPORTANT: Verify this matches your notes/repository.py signature
        # Adjust the method call if needed before running
        try:
            repo = NoteRepository(db, workspace_id=int(workspace_id))
            note = await repo.create(
                created_by=int(created_by),
                title=title,
                content=content,
                is_private=is_private,
            )
            logger.info(
                "Note created via agent tool",
                extra={"note_id": str(note.id), "workspace_id": workspace_id},
            )
            return {"note_id": str(note.id), "title": note.title}
        except Exception as e:
            logger.error(
                "NoteService.create_note failed",
                extra={"error": str(e), "workspace_id": workspace_id},
            )
            raise

    async def update_note(
        self,
        db: "AsyncSession",
        *,
        note_id: str,
        content: str,
        workspace_id: str,
        updated_by: str,
    ) -> dict:
        """
        Update note content.
        workspace_id enforced — cannot update notes from other workspaces.
        """
        # IMPORTANT: Verify this matches your notes/repository.py signature
        # Adjust the method call if needed before running
        try:
            repo = NoteRepository(db, workspace_id=int(workspace_id))
            note = await repo.get(note_id=int(note_id))
            if note is None:
                raise ValueError(
                    f"Note {note_id} not found in workspace {workspace_id}"
                )
            note.content = content
            note = await repo.save(note)
            logger.info(
                "Note updated via agent tool",
                extra={
                    "note_id": str(note.id),
                    "workspace_id": workspace_id,
                    "updated_by": updated_by,
                },
            )
            return {"note_id": str(note.id), "title": note.title}
        except Exception as e:
            logger.error(
                "NoteService.update_note failed",
                extra={"note_id": note_id, "error": str(e)},
            )
            raise
