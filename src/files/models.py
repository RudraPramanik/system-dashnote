from uuid import uuid4

from sqlalchemy import Boolean, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.associations import note_attachments
from core.database.base import Base
from core.database.mixins import TimestampMixin, WorkspaceTenantMixin


class File(Base, WorkspaceTenantMixin, TimestampMixin):
    __tablename__ = "files"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    is_private: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    notes = relationship(
        "Note",
        secondary=note_attachments,
        back_populates="attachments",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_files_workspace_created_by", "workspace_id", "created_by"),
        Index("ix_files_workspace_private", "workspace_id", "is_private"),
    )
