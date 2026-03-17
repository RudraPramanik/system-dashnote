import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from core.database.base import Base
from core.security.context import RequestContext
from core.security.dependency import get_current_context
from core.database.session import get_session
from main import create_app


@pytest.mark.asyncio
async def test_notes_rbac_visibility_and_crud() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_session() -> AsyncSession:
        async with async_session() as session:
            yield session

    state = {"user_id": 1, "workspace_id": 1, "role": "owner"}

    async def override_get_current_context() -> RequestContext:
        return RequestContext(**state)  # type: ignore[arg-type]

    app = create_app()
    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_current_context] = override_get_current_context

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Owner creates a public and a private note
        resp_pub = await client.post(
            "/notes/",
            json={"title": "Public", "content": "pub", "is_private": False},
        )
        assert resp_pub.status_code == 200
        owner_public_id = resp_pub.json()["id"]

        resp_priv = await client.post(
            "/notes/",
            json={"title": "Private", "content": "priv", "is_private": True},
        )
        assert resp_priv.status_code == 200
        owner_private_id = resp_priv.json()["id"]

        # Member can only see public notes + their own private notes
        state.update({"user_id": 2, "role": "member"})
        resp_list_member = await client.get("/notes/")
        assert resp_list_member.status_code == 200
        ids = {n["id"] for n in resp_list_member.json()}
        assert owner_public_id in ids
        assert owner_private_id not in ids

        # Member cannot edit owner's note
        resp_edit_forbidden = await client.patch(
            f"/notes/{owner_public_id}",
            json={"title": "Hacked"},
        )
        assert resp_edit_forbidden.status_code == 403

        # Member can create and manage own note
        resp_member_create = await client.post(
            "/notes/",
            json={"title": "Mine", "content": "m", "is_private": True},
        )
        assert resp_member_create.status_code == 200
        member_note_id = resp_member_create.json()["id"]

        resp_member_edit = await client.patch(
            f"/notes/{member_note_id}",
            json={"content": "m2"},
        )
        assert resp_member_edit.status_code == 200
        assert resp_member_edit.json()["content"] == "m2"

        # Owner can manage any note (including member note)
        state.update({"user_id": 1, "role": "owner"})
        resp_owner_delete = await client.delete(f"/notes/{member_note_id}")
        assert resp_owner_delete.status_code == 204

