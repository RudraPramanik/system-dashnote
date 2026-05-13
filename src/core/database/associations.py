from sqlalchemy import Column, ForeignKey, Integer, Table
from sqlalchemy.dialects.postgresql import UUID

from core.database.base import Base


note_attachments = Table(
    "note_attachments",
    Base.metadata,
    Column(
        "note_id",
        Integer,
        ForeignKey("notes.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "file_id",
        UUID(as_uuid=True),
        ForeignKey("files.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("workspace_id", Integer, nullable=False),
)
