from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.base import Base
from core.database.mixins import TimestampMixin, WorkspaceTenantMixin

# Ensure Page model is imported so the "Page" relationship can be resolved
from pages import models as page_models  # noqa: F401


class Notebook(Base, WorkspaceTenantMixin, TimestampMixin):
    __tablename__ = "notebooks"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    pages = relationship(
        "Page",
        back_populates="notebook",
        cascade="all, delete-orphan",
    )

