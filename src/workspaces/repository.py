from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from workspaces.models import Workspace


class WorkspaceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, *, workspace_id: int) -> Workspace | None:
        stmt = select(Workspace).where(Workspace.id == workspace_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def save(self, workspace: Workspace) -> Workspace:
        self.session.add(workspace)
        await self.session.commit()
        await self.session.refresh(workspace)
        return workspace

