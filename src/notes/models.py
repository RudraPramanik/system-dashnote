from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.database.base import Base
from core.database.mixins import TimestampMixin, WorkspaceTenantMixin


class Note(Base, WorkspaceTenantMixin, TimestampMixin):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_by: Mapped[int] = mapped_column(index=True, nullable=False)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_private: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

