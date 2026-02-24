from sqlalchemy.ext.asyncio import AsyncSession


class TenantRepository:
    """
    Base repository that is always scoped to a single workspace.

    Every tenant-aware repository should inherit from this and never accept
    a free-form workspace_id on individual methods.
    """

    def __init__(self, session: AsyncSession, workspace_id: int):
        self.session = session
        self.workspace_id = workspace_id

