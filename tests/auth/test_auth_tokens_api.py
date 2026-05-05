from jose import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import auth.router as auth_router_module
import core.security.dependency as security_dependency_module
from config import settings
from core.database.base import Base
from core.database.session import get_session
from main import create_app


class FakeTokenStore:
    def __init__(self):
        self.refresh_tokens: set[tuple[int, str]] = set()
        self.blacklisted_access_jtis: set[str] = set()

    async def is_access_token_blacklisted(self, *, jti: str) -> bool:
        return jti in self.blacklisted_access_jtis

    async def blacklist_access_token(self, *, jti: str, ttl_seconds: int) -> None:
        self.blacklisted_access_jtis.add(jti)

    async def store_refresh_token(self, *, user_id: int, jti: str, ttl_seconds: int) -> None:
        self.refresh_tokens.add((user_id, jti))

    async def is_refresh_token_active(self, *, user_id: int, jti: str) -> bool:
        return (user_id, jti) in self.refresh_tokens

    async def revoke_refresh_token(self, *, user_id: int, jti: str) -> None:
        self.refresh_tokens.discard((user_id, jti))


@pytest.mark.asyncio
async def test_refresh_rotation_and_access_blacklist_on_logout() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_session() -> AsyncSession:
        async with session_maker() as session:
            yield session

    fake_store = FakeTokenStore()
    app = create_app()
    app.dependency_overrides[get_session] = override_get_session

    # Patch token-store provider in both modules that consume it.
    auth_router_module.get_token_store = lambda: fake_store
    security_dependency_module.get_token_store = lambda: fake_store

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        register_resp = await client.post(
            "/auth/register",
            json={
                "email": "owner@example.com",
                "password": "Password123!",
                "workspace_name": "ws-1",
            },
        )
        assert register_resp.status_code == 200
        tokens = register_resp.json()
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]

        refresh_payload = jwt.decode(
            refresh_token,
            settings.JWT_REFRESH_SECRET,
            algorithms=["HS256"],
        )
        user_id = int(refresh_payload["sub"])
        old_refresh_jti = str(refresh_payload["jti"])
        assert (user_id, old_refresh_jti) in fake_store.refresh_tokens

        refresh_resp = await client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_resp.status_code == 200
        refreshed = refresh_resp.json()
        new_refresh_token = refreshed["refresh_token"]
        new_refresh_payload = jwt.decode(
            new_refresh_token,
            settings.JWT_REFRESH_SECRET,
            algorithms=["HS256"],
        )
        new_refresh_jti = str(new_refresh_payload["jti"])
        assert (user_id, old_refresh_jti) not in fake_store.refresh_tokens
        assert (user_id, new_refresh_jti) in fake_store.refresh_tokens

        logout_resp = await client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"refresh_token": new_refresh_token},
        )
        assert logout_resp.status_code == 204

        access_payload = jwt.decode(
            access_token,
            settings.JWT_SECRET,
            algorithms=["HS256"],
        )
        assert str(access_payload["jti"]) in fake_store.blacklisted_access_jtis
        assert (user_id, new_refresh_jti) not in fake_store.refresh_tokens

        denied_after_logout = await client.get(
            "/workspaces/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert denied_after_logout.status_code == 401
        assert denied_after_logout.json()["detail"] == "Token has been revoked"
