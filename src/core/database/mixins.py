from datetime import datetime
from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class TenantMixin:
    tenant_id: Mapped[int] = mapped_column(index=True)


class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class WorkspaceTenantMixin:
    """
    Workspace-scoped tenant mixin for multi-tenant entities.

    For this project we use integer workspace IDs (see `workspaces.models.Workspace`),
    so `workspace_id` is an `int`, not a UUID.
    """

    workspace_id: Mapped[int] = mapped_column(index=True)