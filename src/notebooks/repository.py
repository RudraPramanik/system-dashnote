from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.repository import TenantRepository
from core.database.utils import tenant_filter
from notebooks.models import Notebook


class NotebookRepository(TenantRepository):
    async def list(self) -> list[Notebook]:
        stmt = select(Notebook).where(
            tenant_filter(Notebook, self.workspace_id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create(self, *, name: str) -> Notebook:
        notebook = Notebook(
            name=name,
            workspace_id=self.workspace_id,
        )
        self.session.add(notebook)
        await self.session.commit()
        await self.session.refresh(notebook)
        return notebook

