from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


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

    model_config = ConfigDict(from_attributes=True)


class FileListResponse(BaseModel):
    items: list[FileResponse]
    total: int
    skip: int
    limit: int
