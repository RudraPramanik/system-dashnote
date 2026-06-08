"""
Automation worker tasks for DashNoteSystem.

Task progression:
  handle_file_uploaded  → extract text → index vectors → generate metadata
  handle_note_created   → auto-tag note

Fan-out pattern:
  Each task does ONE job and enqueues the next task on success.
  This ensures retries are isolated — extract failure ≠ index failure.

Slice 7.1: stubs — log event receipt, no business logic yet
Slice 7.2: handle_file_uploaded gets extraction + DB persistence
Slice 7.3: fan-out to indexing + metadata generation + note tagging
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def handle_file_uploaded(ctx: dict, *, event_data: dict) -> None:
    """
    Step 1 of file automation: extract text from uploaded file binary.

    Flow:
      1. Parse event_data to get file_id, workspace_id, mime_type
      2. Load file metadata from DB to get storage path
      3. Download file binary from storage backend
      4. Extract text using FileParsingEngine
      5. Persist extracted_text to files table
      6. Enqueue fan-out tasks (added in Sub-step 7.3)
    """
    import uuid
    import asyncio
    import functools

    from shared.utils.parsers import FileParsingEngine
    from core.storage.client import get_storage
    from core.database.session import AsyncSessionLocal
    import sqlalchemy as sa

    # Parse event — model_dump(mode="json") flattens payload fields to top level (7.0)
    try:
        file_id = event_data.get("file_id")
        workspace_id = event_data.get("workspace_id")
        mime_type = event_data.get("mime_type", "text/plain")

        if not file_id or not workspace_id:
            logger.error(
                "handle_file_uploaded: missing file_id or workspace_id",
                extra={"event_data_keys": list(event_data.keys())},
            )
            return
    except Exception as e:
        logger.error("handle_file_uploaded: event_data parse failed", extra={"error": str(e)})
        return

    # Step 1: Load file record to get storage_key
    file_record = None
    async with AsyncSessionLocal() as db:
        try:
            from files.models import File
            result = await db.execute(
                sa.select(File).where(
                    File.id == uuid.UUID(file_id),
                    File.workspace_id == int(workspace_id),
                )
            )
            file_record = result.scalar_one_or_none()
        except Exception as e:
            logger.error(
                "handle_file_uploaded: DB lookup failed",
                extra={"file_id": file_id, "error": str(e)},
            )
            return

    if file_record is None:
        logger.warning(
            "handle_file_uploaded: file not found",
            extra={"file_id": file_id, "workspace_id": workspace_id},
        )
        return

    # Step 2: Download file binary from storage
    try:
        storage = get_storage()
        file_bytes = await storage.download(file_record.storage_key)
    except Exception as e:
        logger.error(
            "handle_file_uploaded: storage download failed",
            extra={"file_id": file_id, "error": str(e)},
        )
        return

    # Step 3: Extract text (CPU-bound — run in executor)
    try:
        loop = asyncio.get_event_loop()
        extracted_text = await loop.run_in_executor(
            None,
            functools.partial(
                FileParsingEngine.extract_text,
                file_bytes,
                file_record.mime_type,
            ),
        )
    except Exception as e:
        logger.error(
            "handle_file_uploaded: text extraction failed",
            extra={"file_id": file_id, "mime_type": file_record.mime_type, "error": str(e)},
        )
        extracted_text = ""   # non-fatal — continue without text

    # Step 4: Persist extracted_text to DB
    async with AsyncSessionLocal() as db:
        try:
            from files.models import File
            await db.execute(
                sa.update(File)
                .where(
                    File.id == uuid.UUID(file_id),
                    File.workspace_id == int(workspace_id),
                )
                .values(extracted_text=extracted_text)
            )
            await db.commit()
            logger.info(
                "handle_file_uploaded: extracted_text saved",
                extra={
                    "file_id": file_id,
                    "chars_extracted": len(extracted_text),
                    "mime_type": mime_type,
                },
            )
        except Exception as e:
            logger.error(
                "handle_file_uploaded: DB update failed",
                extra={"file_id": file_id, "error": str(e)},
            )
            return

    # Step 5: Fan-out to indexing + metadata (added in Sub-step 7.3)
    # TODO 7.3: enqueue index_file_chunks + generate_file_metadata


async def handle_note_created(ctx: dict, *, event_data: dict) -> None:
    """
    Triggered when a note is created.
    Full implementation added in Sub-step 7.3.
    """
    logger.info(
        "handle_note_created received",
        extra={
            "event_type": event_data.get("event_type"),
            "note_id": event_data.get("note_id"),
            "workspace_id": event_data.get("workspace_id"),
        },
    )
    # TODO 7.3: auto-tag note


async def handle_note_updated(ctx: dict, *, event_data: dict) -> None:
    """Triggered when note content changes. Stub for future use."""
    logger.info("handle_note_updated received", extra={"event_data": event_data})


async def handle_file_deleted(ctx: dict, *, event_data: dict) -> None:
    """Triggered when a file is deleted. Stub for Qdrant vector cleanup."""
    logger.info("handle_file_deleted received", extra={"event_data": event_data})
    # TODO: delete file vectors from QDRANT_FILES_COLLECTION
