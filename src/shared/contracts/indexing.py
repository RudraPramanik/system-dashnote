"""
Contracts for note indexing operations.
API enqueues IndexingRequest. Worker processes it.
This module imports NOTHING from src/ai/, src/worker/, or domain modules.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


class IndexingOperation(str, Enum):
    UPSERT = "upsert"
    DELETE = "delete"


class IndexingRequest(BaseModel):
    """Enqueued by API after note create/update. Worker processes this."""

    model_config = ConfigDict(frozen=True)

    request_id: str = Field(default_factory=lambda: str(uuid4()))
    operation: IndexingOperation
    note_id: str
    workspace_id: str
    created_by: str
    is_private: bool
    title: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @model_validator(mode="after")
    def content_required_for_upsert(self) -> "IndexingRequest":
        if self.operation == IndexingOperation.UPSERT and not self.content.strip():
            raise ValueError("content must not be empty for upsert operation")
        return self


class DeletionRequest(BaseModel):
    """Enqueued by API after note delete. Worker removes vectors."""

    model_config = ConfigDict(frozen=True)

    request_id: str = Field(default_factory=lambda: str(uuid4()))
    note_id: str
    workspace_id: str
    deleted_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class IndexingResult(BaseModel):
    """Returned by worker after indexing completes."""

    model_config = ConfigDict(frozen=True)

    request_id: str
    note_id: str
    workspace_id: str
    success: bool
    chunks_indexed: int = 0
    error: str | None = None
    latency_ms: float = 0.0
    completed_at: datetime = Field(default_factory=datetime.utcnow)
