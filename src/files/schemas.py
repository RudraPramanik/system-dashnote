from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

EXTRACTED_TEXT_DETAIL_MAX = 8000


def clip_extracted_text(text: str | None, *, include: bool) -> str | None:
    """Return truncated extracted_text for detail responses; null for lists."""
    if not include or not text:
        return None
    return text[:EXTRACTED_TEXT_DETAIL_MAX]


class FileCreate(BaseModel):
    name: str
    mime_type: str
    size_bytes: int
    is_private: bool = True
    description: str | None = None


class FileUpdate(BaseModel):
    name: str | None = None
    is_private: bool | None = None
    description: str | None = None


class FileResponse(BaseModel):
    id: UUID
    workspace_id: int
    created_by: int
    name: str
    storage_key: str
    mime_type: str
    size_bytes: int
    is_private: bool
    description: str | None
    created_at: datetime
    updated_at: datetime
    download_url: str = ""
    summary: str | None = None
    tags: list[str] = Field(default_factory=list)
    extracted_text: str | None = None

    model_config = ConfigDict(from_attributes=True)


class FileListResponse(BaseModel):
    items: list[FileResponse]
    total: int
    skip: int
    limit: int
