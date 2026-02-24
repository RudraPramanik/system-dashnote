import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select

from core.database.base import Base
from notebooks.models import Notebook
from pages.models import Page, PageVersion
from pages.versioning import create_page_version


@pytest.mark.asyncio
async def test_create_page_version_increments_versions() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        # Create a workspace-scoped notebook and page
        notebook = Notebook(name="Demo", workspace_id=1)
        page = Page(notebook=notebook, notebook_id=0, workspace_id=1)  # notebook_id will be set after flush

        session.add_all([notebook, page])
        await session.flush()

        # fix notebook_id now that notebook has an id
        page.notebook_id = notebook.id
        await session.flush()

        v1 = await create_page_version(session, page.id, "first")
        v2 = await create_page_version(session, page.id, "second")

        assert v1.version == 1
        assert v1.content == "first"
        assert v2.version == 2
        assert v2.content == "second"

        result = await session.execute(
            select(PageVersion).where(PageVersion.page_id == page.id).order_by(PageVersion.version)
        )
        versions = result.scalars().all()
        assert [v.version for v in versions] == [1, 2]

