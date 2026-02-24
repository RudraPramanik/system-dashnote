import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from core.database.base import Base
from core.security.context import RequestContext
from core.security.dependency import get_current_context
from core.database.session import get_session
from notebooks.models import Notebook
from main import create_app


@pytest.mark.asyncio
async def test_notebooks_list_and_create_scoped_to_workspace() -> None:
    # Use an in-memory SQLite DB for this API test
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_session() -> AsyncSession:
        async with async_session() as session:
            yield session

    async def override_get_current_context() -> RequestContext:
        # Pretend we are an owner in workspace 1
        return RequestContext(user_id=1, workspace_id=1, role="owner")

    app = create_app()
    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_current_context] = override_get_current_context

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Initially, there should be no notebooks
        resp = await client.get("/notebooks/")
        assert resp.status_code == 200
        assert resp.json() == []

        # Create a notebook in workspace 1
        resp_create = await client.post("/notebooks/", json={"name": "Workspace 1 Notebook"})
        assert resp_create.status_code == 200
        created = resp_create.json()
        assert created["name"] == "Workspace 1 Notebook"

        # Insert a notebook for a different workspace (2) directly via the session
        async with async_session() as session:
            other = Notebook(name="Other Workspace", workspace_id=2)
            session.add(other)
            await session.commit()

        # Listing notebooks via the API should still only return workspace 1 notebooks
        resp_list = await client.get("/notebooks/")
        assert resp_list.status_code == 200
        notebooks = resp_list.json()
        assert len(notebooks) == 1
        assert notebooks[0]["name"] == "Workspace 1 Notebook"

