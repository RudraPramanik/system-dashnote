"""
NoteService — thin service layer over notes/repository.py.

Exists so LangGraph agent tools can create and update notes
without importing SQLAlchemy or domain repositories directly.

This service accepts AsyncSession per method — never stored.
It accepts plain strings for IDs — converts to int internally.

Update authorization uses notes.permissions.can_manage_note (same rules as
PATCH /notes). Tools pass role as a string; this module builds RequestContext.
Unknown roles are rejected before can_manage_note.

IMPORT LAW: notes.repository, notes.permissions, core.security.context, stdlib.
No FastAPI. AsyncSession injected per method.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from core.security.context import RequestContext
from notes.permissions import can_manage_note
from notes.repository import NoteRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

ALLOWED_NOTE_ROLES = frozenset({"owner", "admin", "member"})


class NoteNotFoundError(Exception):
    """Note is not in the session workspace."""


class NoteAccessDeniedError(Exception):
    """Caller role cannot manage this note."""


@dataclass(frozen=True)
class NoteUpdateDecision:
    """Pre-write outcome for an agent update. ``outcome`` is allowed|forbidden|not_found."""

    outcome: str


class NoteService:
    """
    Agent-callable note operations.

    All methods accept AsyncSession as first parameter and plain
    string IDs — never SQLAlchemy models or RequestContext objects.

    LangGraph tools call this service. Tools never call the repository directly.
    This enforces the tool → service → repository chain.

    NoteRepository is tenant-scoped: instantiated per call with session + workspace_id.
    """

    async def decide_update(
        self,
        db: "AsyncSession",
        *,
        note_id: str,
        workspace_id: str,
        user_id: str,
        role: str,
    ) -> NoteUpdateDecision:
        """
        Workspace-scoped manage check. Does not write.

        Unknown roles are forbidden before can_manage_note, which would
        otherwise treat them like a member who owns the note.
        """
        if role not in ALLOWED_NOTE_ROLES:
            return NoteUpdateDecision("forbidden")

        repo = NoteRepository(db, workspace_id=int(workspace_id))
        note = await repo.get(note_id=int(note_id))
        if note is None:
            return NoteUpdateDecision("not_found")

        ctx = RequestContext(
            user_id=int(user_id),
            workspace_id=int(workspace_id),
            role=role,
        )
        if not can_manage_note(ctx, note):
            return NoteUpdateDecision("forbidden")
        return NoteUpdateDecision("allowed")

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
        role: str,
    ) -> dict:
        """
        Update note content after a fresh manage check.
        workspace_id enforced — cannot update notes from other workspaces.
        """
        decision = await self.decide_update(
            db,
            note_id=note_id,
            workspace_id=workspace_id,
            user_id=updated_by,
            role=role,
        )
        if decision.outcome == "not_found":
            raise NoteNotFoundError("Note not found")
        if decision.outcome != "allowed":
            raise NoteAccessDeniedError("Note update denied")

        try:
            repo = NoteRepository(db, workspace_id=int(workspace_id))
            note = await repo.get(note_id=int(note_id))
            if note is None:
                raise NoteNotFoundError("Note not found")
            ctx = RequestContext(
                user_id=int(updated_by),
                workspace_id=int(workspace_id),
                role=role,
            )
            if role not in ALLOWED_NOTE_ROLES or not can_manage_note(ctx, note):
                raise NoteAccessDeniedError("Note update denied")
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
