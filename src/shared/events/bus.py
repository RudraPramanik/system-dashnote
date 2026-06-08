"""
Event bus dispatcher for DashNoteSystem.

emit_event() converts domain events into ARQ background jobs.
This module does NOT define event schemas — those live in
shared/events/definitions.py.

Task routing:
  FileUploadedEvent → handle_file_uploaded (worker/automation/tasks.py)
  NoteCreatedEvent  → handle_note_created  (worker/automation/tasks.py)

Failure handling:
  Redis unavailable → log error, return None
  Unknown event type → log warning, return None
  Never raise — never block the HTTP request lifecycle

IMPORT LAW: shared.events.definitions, stdlib, logging only.
No FastAPI. No SQLAlchemy. No AI imports.
"""
from __future__ import annotations

import logging
from typing import Any

from shared.events.definitions import BaseEvent, EventType

logger = logging.getLogger(__name__)

# Maps event type string to ARQ task function name
_TASK_MAP: dict[str, str] = {
    EventType.FILE_UPLOADED.value: "handle_file_uploaded",
    EventType.NOTE_CREATED.value: "handle_note_created",
    EventType.NOTE_UPDATED.value: "handle_note_updated",
    EventType.FILE_DELETED.value: "handle_file_deleted",
}


async def emit_event(
    event: BaseEvent,
    arq_pool: Any,
) -> bool:
    """
    Dispatch a domain event to the ARQ background worker queue.

    Args:
        event:    A frozen Pydantic BaseEvent subclass from shared/events/definitions.py
        arq_pool: app.state.arq_pool — the ARQ connection pool from lifespan

    Returns:
        True if enqueued successfully, False otherwise.
        Never raises — failure is logged and swallowed.

    Security:
        event.workspace_id comes from RequestContext (JWT) — already validated
        before reaching this function. No re-validation needed here.
    """
    if arq_pool is None:
        logger.warning(
            "emit_event called with no arq_pool — event dropped",
            extra={"event_type": event.event_type.value},
        )
        return False

    task_name = _TASK_MAP.get(event.event_type.value)
    if task_name is None:
        logger.warning(
            "No task registered for event type",
            extra={"event_type": event.event_type.value},
        )
        return False

    try:
        await arq_pool.enqueue_job(
            task_name,
            event_data=event.model_dump(mode="json"),
        )
        logger.info(
            "Event emitted",
            extra={
                "event_type": event.event_type.value,
                "event_id": event.event_id,
                "workspace_id": event.workspace_id,
                "task": task_name,
            },
        )
        return True
    except Exception as e:
        logger.error(
            "emit_event failed — event dropped, HTTP response unaffected",
            extra={
                "event_type": event.event_type.value,
                "error": str(e),
            },
        )
        return False
