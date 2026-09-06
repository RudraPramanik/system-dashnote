"""Orchestrate inbound note + attachment creation."""

from __future__ import annotations

import base64
import logging
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from core.storage.client import get_storage
from core.storage.utils import (
    detect_mime_type,
    generate_storage_key,
    safe_filename,
    validate_file,
)
from files import repository as files_repo
from files.schemas import FileCreate
from integrations.enrich import dump_title, enrich_title_and_tags
from integrations.idempotency import get_existing_ingest, record_ingest
from integrations.identity import ResolvedIdentity
from integrations.schemas import (
    AttachmentResult,
    EmailInboundRequest,
    InboundAttachmentIn,
    InboundIngestResponse,
)
from integrations.side_effects import (
    emit_file_uploaded_side_effects,
    emit_note_created_side_effects,
)
from notes.repository import NoteRepository

logger = logging.getLogger(__name__)

CHANNEL_EMAIL = "email"
CHANNEL_WHATSAPP = "whatsapp"


async def ingest_text_message(
    request: Request,
    db: AsyncSession,
    *,
    channel: str,
    provider_message_id: str,
    identity: ResolvedIdentity,
    subject: str | None,
    body: str,
    attachments: list[InboundAttachmentIn] | None = None,
) -> InboundIngestResponse:
    existing = await get_existing_ingest(
        db,
        channel=channel,
        provider_message_id=provider_message_id,
    )
    if existing is not None:
        repo = NoteRepository(db, workspace_id=existing.workspace_id)
        note = await repo.get(note_id=existing.note_id)
        title = note.title if note is not None else "Inbound note"
        return InboundIngestResponse(
            note_id=existing.note_id,
            workspace_id=existing.workspace_id,
            user_id=existing.user_id,
            title=title,
            duplicate=True,
            attachments=[],
            agentic=False,
        )

    title = dump_title(subject, body)
    content = body or ""
    tags: list[str] = []
    agentic_used = False

    enriched = await enrich_title_and_tags(
        subject=subject,
        body=content,
        workspace_id=identity.workspace_id,
    )
    if enriched is not None:
        title, tags = enriched
        agentic_used = True

    repo = NoteRepository(db, workspace_id=identity.workspace_id)
    note = await repo.create(
        created_by=identity.user_id,
        title=title,
        content=content,
        is_private=False,
    )
    if tags:
        note.tags = tags
        note = await repo.save(note)

    await emit_note_created_side_effects(
        request,
        note=note,
        workspace_id=identity.workspace_id,
        user_id=identity.user_id,
        content=content,
    )

    attachment_results = await _store_attachments(
        request,
        db,
        identity=identity,
        note_id=note.id,
        attachments=attachments or [],
    )

    await record_ingest(
        db,
        channel=channel,
        provider_message_id=provider_message_id,
        note_id=note.id,
        workspace_id=identity.workspace_id,
        user_id=identity.user_id,
    )

    return InboundIngestResponse(
        note_id=note.id,
        workspace_id=identity.workspace_id,
        user_id=identity.user_id,
        title=note.title,
        duplicate=False,
        attachments=attachment_results,
        agentic=agentic_used,
    )


async def ingest_email(
    request: Request,
    db: AsyncSession,
    payload: EmailInboundRequest,
    identity: ResolvedIdentity,
) -> InboundIngestResponse:
    return await ingest_text_message(
        request,
        db,
        channel=CHANNEL_EMAIL,
        provider_message_id=payload.message_id,
        identity=identity,
        subject=payload.subject,
        body=payload.body,
        attachments=payload.attachments,
    )


async def _store_attachments(
    request: Request,
    db: AsyncSession,
    *,
    identity: ResolvedIdentity,
    note_id: int,
    attachments: list[InboundAttachmentIn],
) -> list[AttachmentResult]:
    results: list[AttachmentResult] = []
    if not attachments:
        return results

    storage = get_storage()
    for att in attachments:
        try:
            raw = base64.b64decode(att.content_base64, validate=False)
        except Exception:
            results.append(
                AttachmentResult(
                    filename=att.filename,
                    status="rejected",
                    reason="Invalid base64 content.",
                )
            )
            continue

        try:
            detected = detect_mime_type(raw) if raw else (att.content_type or "")
            validate_file(att.filename or "upload.bin", len(raw), detected)
            safe_name = safe_filename(att.filename or "upload.bin")
            key = generate_storage_key(str(identity.workspace_id), safe_name)
            await storage.upload(key, raw, detected)
            record = await files_repo.create(
                db,
                identity.workspace_id,
                identity.user_id,
                FileCreate(
                    name=safe_name,
                    mime_type=detected,
                    size_bytes=len(raw),
                    is_private=False,
                    description="Inbound attachment",
                ),
                storage_key=key,
            )
            await files_repo.link_to_note(
                db,
                identity.workspace_id,
                note_id,
                record.id,
            )
            await emit_file_uploaded_side_effects(
                request,
                workspace_id=identity.workspace_id,
                file_id=record.id,
                uploaded_by=identity.user_id,
                file_name=record.name,
                mime_type=record.mime_type,
                size_bytes=record.size_bytes,
                is_private=record.is_private,
            )
            results.append(
                AttachmentResult(
                    filename=safe_name,
                    status="attached",
                    file_id=record.id,
                )
            )
        except HTTPException as e:
            results.append(
                AttachmentResult(
                    filename=att.filename,
                    status="rejected",
                    reason=str(e.detail),
                )
            )
        except Exception as e:
            logger.warning(
                "Inbound attachment failed",
                extra={"filename": att.filename, "error": str(e)[:240]},
            )
            results.append(
                AttachmentResult(
                    filename=att.filename,
                    status="rejected",
                    reason="Attachment processing failed.",
                )
            )
    return results
