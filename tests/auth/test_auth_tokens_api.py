from unittest.mock import AsyncMock

from jose import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import auth.router as auth_router_module
import auth.service as auth_service_module
import core.security.dependency as security_dependency_module
from auth.email import send_password_reset_email
from auth.models import User, WorkspaceUser
from auth.router import FORGOT_PASSWORD_MESSAGE
from config import settings
from core.database.base import Base
from core.database.session import get_session
from core.redis.deps import get_redis_connection
from main import create_app
from workspaces.models import Workspace


class FakeTokenStore:
    def __init__(self):
        self.refresh_tokens: set[tuple[int, str]] = set()
        self.blacklisted_access_jtis: set[str] = set()
        self.reset_tokens: dict[str, int] = {}
        self.reset_by_user: dict[int, str] = {}

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

    async def revoke_all_refresh_tokens(self, *, user_id: int) -> None:
        self.refresh_tokens = {pair for pair in self.refresh_tokens if pair[0] != user_id}

    async def store_password_reset_token(
        self, *, user_id: int, digest: str, ttl_seconds: int
    ) -> bool:
        old = self.reset_by_user.get(user_id)
        if old is not None:
            self.reset_tokens.pop(old, None)
        self.reset_tokens[digest] = user_id
        self.reset_by_user[user_id] = digest
        return True

    async def consume_password_reset_token(self, *, digest: str) -> int | None:
        user_id = self.reset_tokens.pop(digest, None)
        if user_id is None:
            return None
        if self.reset_by_user.get(user_id) == digest:
            del self.reset_by_user[user_id]
        return user_id


class RefusingResetStore(FakeTokenStore):
    async def store_password_reset_token(
        self, *, user_id: int, digest: str, ttl_seconds: int
    ) -> bool:
        return False


def _bind_token_store(fake_store: FakeTokenStore) -> None:
    auth_router_module.get_token_store = lambda: fake_store
    auth_service_module.get_token_store = lambda: fake_store
    security_dependency_module.get_token_store = lambda: fake_store


async def _auth_client(fake_store: FakeTokenStore):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                sync_conn,
                tables=[
                    User.__table__,
                    Workspace.__table__,
                    WorkspaceUser.__table__,
                ],
            )
        )

    async def override_get_session() -> AsyncSession:
        async with session_maker() as session:
            yield session

    async def _no_redis() -> None:
        return None

    app = create_app()
    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_redis_connection] = _no_redis
    _bind_token_store(fake_store)
    transport = ASGITransport(app=app)
    return engine, AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_refresh_rotation_and_access_blacklist_on_logout() -> None:
    fake_store = FakeTokenStore()
    engine, client = await _auth_client(fake_store)
    async with client:
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
    await engine.dispose()


@pytest.mark.asyncio
async def test_change_password_success_and_revokes_other_refresh() -> None:
    fake_store = FakeTokenStore()
    engine, client = await _auth_client(fake_store)
    async with client:
        register_resp = await client.post(
            "/auth/register",
            json={
                "email": "owner@example.com",
                "password": "Password123!",
                "workspace_name": "ws-1",
            },
        )
        assert register_resp.status_code == 200
        first = register_resp.json()
        first_refresh = first["refresh_token"]

        login_resp = await client.post(
            "/auth/login",
            json={"email": "owner@example.com", "password": "Password123!"},
        )
        assert login_resp.status_code == 200
        second = login_resp.json()

        change_resp = await client.post(
            "/auth/change-password",
            headers={"Authorization": f"Bearer {second['access_token']}"},
            json={
                "current_password": "Password123!",
                "new_password": "Newpass123!",
            },
        )
        assert change_resp.status_code == 200
        changed = change_resp.json()
        assert "access_token" in changed and "refresh_token" in changed

        old_refresh = await client.post(
            "/auth/refresh",
            json={"refresh_token": first_refresh},
        )
        assert old_refresh.status_code == 401

        stale_login = await client.post(
            "/auth/login",
            json={"email": "owner@example.com", "password": "Password123!"},
        )
        assert stale_login.status_code == 401

        new_login = await client.post(
            "/auth/login",
            json={"email": "owner@example.com", "password": "Newpass123!"},
        )
        assert new_login.status_code == 200
        claims = jwt.decode(
            new_login.json()["access_token"],
            settings.JWT_SECRET,
            algorithms=["HS256"],
        )
        assert claims["sub"]
        assert claims["wid"]
        assert claims["role"] == "owner"
    await engine.dispose()


@pytest.mark.asyncio
async def test_change_password_wrong_current_keeps_refresh() -> None:
    fake_store = FakeTokenStore()
    engine, client = await _auth_client(fake_store)
    async with client:
        register_resp = await client.post(
            "/auth/register",
            json={
                "email": "owner@example.com",
                "password": "Password123!",
                "workspace_name": "ws-1",
            },
        )
        tokens = register_resp.json()
        refresh_before = set(fake_store.refresh_tokens)

        change_resp = await client.post(
            "/auth/change-password",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            json={
                "current_password": "wrong-pass",
                "new_password": "Newpass123!",
            },
        )
        assert change_resp.status_code == 401
        assert change_resp.json()["detail"] == "Invalid credentials"
        assert fake_store.refresh_tokens == refresh_before

        still_login = await client.post(
            "/auth/login",
            json={"email": "owner@example.com", "password": "Password123!"},
        )
        assert still_login.status_code == 200
    await engine.dispose()


@pytest.mark.asyncio
async def test_forgot_unknown_and_known_email_same_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    send = AsyncMock()
    monkeypatch.setattr("auth.router.send_password_reset_email", send)
    fake_store = FakeTokenStore()
    engine, client = await _auth_client(fake_store)
    async with client:
        unknown = await client.post(
            "/auth/forgot-password",
            json={"email": "nobody@example.com"},
        )
        assert unknown.status_code == 200
        assert unknown.json() == {"message": FORGOT_PASSWORD_MESSAGE}
        assert send.await_count == 0

        register_resp = await client.post(
            "/auth/register",
            json={
                "email": "owner@example.com",
                "password": "Password123!",
                "workspace_name": "ws-1",
            },
        )
        assert register_resp.status_code == 200

        known = await client.post(
            "/auth/forgot-password",
            json={"email": "owner@example.com"},
        )
        assert known.status_code == 200
        assert known.json() == {"message": FORGOT_PASSWORD_MESSAGE}
        assert send.await_count == 1
        kwargs = send.await_args.kwargs
        assert kwargs["to_email"] == "owner@example.com"
        assert kwargs["raw_token"]
    await engine.dispose()


@pytest.mark.asyncio
async def test_reset_happy_path_then_login(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "auth.service.secrets.token_urlsafe", lambda n=32: "fixed-reset-token"
    )
    send = AsyncMock()
    monkeypatch.setattr("auth.router.send_password_reset_email", send)
    fake_store = FakeTokenStore()
    engine, client = await _auth_client(fake_store)
    async with client:
        await client.post(
            "/auth/register",
            json={
                "email": "owner@example.com",
                "password": "Password123!",
                "workspace_name": "ws-1",
            },
        )
        forgot = await client.post(
            "/auth/forgot-password",
            json={"email": "owner@example.com"},
        )
        assert forgot.status_code == 200

        reset = await client.post(
            "/auth/reset-password",
            json={"token": "fixed-reset-token", "new_password": "Resetpass1"},
        )
        assert reset.status_code == 204

        reuse = await client.post(
            "/auth/reset-password",
            json={"token": "fixed-reset-token", "new_password": "Resetpass2"},
        )
        assert reuse.status_code == 400

        old_login = await client.post(
            "/auth/login",
            json={"email": "owner@example.com", "password": "Password123!"},
        )
        assert old_login.status_code == 401

        new_login = await client.post(
            "/auth/login",
            json={"email": "owner@example.com", "password": "Resetpass1"},
        )
        assert new_login.status_code == 200
    await engine.dispose()


@pytest.mark.asyncio
async def test_reset_unknown_token_fails() -> None:
    fake_store = FakeTokenStore()
    engine, client = await _auth_client(fake_store)
    async with client:
        await client.post(
            "/auth/register",
            json={
                "email": "owner@example.com",
                "password": "Password123!",
                "workspace_name": "ws-1",
            },
        )
        reset = await client.post(
            "/auth/reset-password",
            json={"token": "not-a-real-token", "new_password": "Resetpass1"},
        )
        assert reset.status_code == 400
        still = await client.post(
            "/auth/login",
            json={"email": "owner@example.com", "password": "Password123!"},
        )
        assert still.status_code == 200
    await engine.dispose()


@pytest.mark.asyncio
async def test_forgot_empty_resend_and_store_fallback_still_200(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("auth.email.settings.RESEND_API_KEY", "")
    fake_store = FakeTokenStore()
    engine, client = await _auth_client(fake_store)
    async with client:
        await client.post(
            "/auth/register",
            json={
                "email": "owner@example.com",
                "password": "Password123!",
                "workspace_name": "ws-1",
            },
        )
        resp = await client.post(
            "/auth/forgot-password",
            json={"email": "owner@example.com"},
        )
        assert resp.status_code == 200
        assert resp.json() == {"message": FORGOT_PASSWORD_MESSAGE}
    await engine.dispose()

    await send_password_reset_email(
        to_email="owner@example.com", raw_token="should-not-log"
    )

    refuse = RefusingResetStore()
    engine, client = await _auth_client(refuse)
    async with client:
        await client.post(
            "/auth/register",
            json={
                "email": "fallback@example.com",
                "password": "Password123!",
                "workspace_name": "ws-1",
            },
        )
        resp = await client.post(
            "/auth/forgot-password",
            json={"email": "fallback@example.com"},
        )
        assert resp.status_code == 200
        assert resp.json() == {"message": FORGOT_PASSWORD_MESSAGE}
    await engine.dispose()

