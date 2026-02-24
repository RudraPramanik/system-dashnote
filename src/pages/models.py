from sqlalchemy import ForeignKey, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.base import Base
from core.database.mixins import TimestampMixin, WorkspaceTenantMixin


class Page(Base, WorkspaceTenantMixin, TimestampMixin):
    __tablename__ = "pages"

    id: Mapped[int] = mapped_column(primary_key=True)
    notebook_id: Mapped[int] = mapped_column(
        ForeignKey("notebooks.id", ondelete="CASCADE"),
        nullable=False,
    )

    notebook = relationship("Notebook", back_populates="pages")
    versions = relationship(
        "PageVersion",
        back_populates="page",
        cascade="all, delete-orphan",
    )


class PageVersion(Base, TimestampMixin):
    __tablename__ = "page_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    page_id: Mapped[int] = mapped_column(
        ForeignKey("pages.id", ondelete="CASCADE"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)

    page = relationship("Page", back_populates="versions")

