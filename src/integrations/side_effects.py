"""Mirror note/file HTTP side effects (embed enqueue + domain events)."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from starlette.requests import Request

from config import get_settings
from notes.models import Note
from shared.contracts.indexing import IndexingOperation, IndexingRequest

logger = logging.getLogger(__name__)


async def emit_note_created_side_effects(
    request: Request,
    *,
    note: Note,
    workspace_id: int,
    user_id: int,
    content: str,
) -> None:
    settings = get_settings()
    if not settings.ai_enabled:
        return
    arq_pool = getattr(request.app.state, "arq_pool", None)
    try:
        if arq_pool is not None:
            await arq_pool.enqueue_job(
                "embed_note_task",
                request_dict=IndexingRequest(
                    operation=IndexingOperation.UPSERT,
                    note_id=str(note.id),
                    workspace_id=str(workspace_id),
                    created_by=str(user_id),
                    is_private=note.is_private,
                    title=note.title,
                    content=content,
                ).model_dump(),
            )
    except Exception:
        logger.warning(
            "Failed to enqueue embedding job for inbound note",
            extra={"note_id": str(note.id)},
        )

    try:
        from shared.events.bus import emit_event
        from shared.events.definitions import NoteCreatedEvent

        await emit_event(
            NoteCreatedEvent(
                workspace_id=str(workspace_id),
                note_id=str(note.id),
                created_by=str(user_id),
                is_private=note.is_private,
                title=note.title,
                content=content,
            ),
            arq_pool,
        )
    except Exception:
        logger.warning(
            "NoteCreatedEvent emission failed for inbound note",
            extra={"note_id": str(note.id)},
        )


async def emit_file_uploaded_side_effects(
    request: Request,
    *,
    workspace_id: int,
    file_id: UUID,
    uploaded_by: int,
    file_name: str,
    mime_type: str,
    size_bytes: int,
    is_private: bool,
) -> None:
    settings = get_settings()
    if not settings.ai_enabled:
        return
    arq_pool = getattr(request.app.state, "arq_pool", None)
    try:
        from shared.events.bus import emit_event
        from shared.events.definitions import FileUploadedEvent

        await emit_event(
            FileUploadedEvent(
                workspace_id=str(workspace_id),
                file_id=str(file_id),
                uploaded_by=str(uploaded_by),
                file_name=file_name,
                mime_type=mime_type,
                size_bytes=size_bytes,
                is_private=is_private,
            ),
            arq_pool,
        )
    except Exception:
        logger.warning(
            "FileUploadedEvent emission failed for inbound file",
            extra={"file_id": str(file_id)},
        )
