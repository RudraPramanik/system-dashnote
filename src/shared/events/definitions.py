from datetime import datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class EventType(str, Enum):
    NOTE_CREATED = "note.created"
    NOTE_UPDATED = "note.updated"
    NOTE_DELETED = "note.deleted"
    FILE_UPLOADED = "file.uploaded"
    FILE_DELETED = "file.deleted"


class BaseEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: EventType
    workspace_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class NoteCreatedEvent(BaseEvent):
    model_config = ConfigDict(frozen=True)

    event_type: EventType = EventType.NOTE_CREATED


class NoteUpdatedEvent(BaseEvent):
    model_config = ConfigDict(frozen=True)

    event_type: EventType = EventType.NOTE_UPDATED


class NoteDeletedEvent(BaseEvent):
    model_config = ConfigDict(frozen=True)

    event_type: EventType = EventType.NOTE_DELETED


class FileUploadedEvent(BaseEvent):
    model_config = ConfigDict(frozen=True)

    event_type: EventType = EventType.FILE_UPLOADED


class FileDeletedEvent(BaseEvent):
    model_config = ConfigDict(frozen=True)

    event_type: EventType = EventType.FILE_DELETED
