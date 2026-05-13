import os
import re
from pathlib import Path
from uuid import uuid4

import magic
from fastapi import HTTPException, status


ALLOWED_MIME_TYPES = frozenset(
    {
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "text/plain",
        "text/csv",
    }
)

MIME_EXTENSION_MAP: dict[str, set[str]] = {
    "application/pdf": {".pdf"},
    "application/msword": {".doc"},
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {".docx"},
    "application/vnd.ms-excel": {".xls"},
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {".xlsx"},
    "application/vnd.ms-powerpoint": {".ppt"},
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": {".pptx"},
    "text/plain": {".txt"},
    "text/csv": {".csv"},
}


def validate_file(filename: str, size: int, mime_type: str) -> None:
    if size > 1_048_576:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds maximum allowed size.",
        )

    if mime_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported MIME type.",
        )

    file_ext = Path(filename).suffix.lower()
    if file_ext not in MIME_EXTENSION_MAP[mime_type]:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="File extension does not match MIME type.",
        )


def detect_mime_type(data: bytes) -> str:
    return magic.from_buffer(data, mime=True)


def generate_storage_key(workspace_id: str, filename: str) -> str:
    return f"{workspace_id}/{uuid4().hex}/{filename}"


def safe_filename(filename: str) -> str:
    basename = os.path.basename(filename).replace(" ", "_")
    return re.sub(r"[^a-zA-Z0-9._-]", "", basename)
