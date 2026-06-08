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
    Triggered when a file is uploaded.
    Full implementation added in Sub-steps 7.2 and 7.3.
    """
    logger.info(
        "handle_file_uploaded received",
        extra={
            "event_type": event_data.get("event_type"),
            "file_id": event_data.get("file_id"),
            "workspace_id": event_data.get("workspace_id"),
        },
    )
    # TODO 7.2: extract text from file binary
    # TODO 7.3: fan-out to index_file_chunks + generate_file_metadata


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
