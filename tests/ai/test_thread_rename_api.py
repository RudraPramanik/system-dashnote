"""API tests for PATCH /ai/threads/{id} rename."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from core.database.session import get_session
from core.security.context import RequestContext
from core.security.dependency import get_current_context
from main import create_app


@pytest.mark.asyncio
async def test_rename_thread_ok():
    app = create_app()

    async def _ctx() -> RequestContext:
        return RequestContext(user_id=1, workspace_id=9, role="owner")

    async def _db():
        yield AsyncMock()

    app.dependency_overrides[get_current_context] = _ctx
    app.dependency_overrides[get_session] = _db

    thread = MagicMock()
    thread.id = "11111111-1111-1111-1111-111111111111"
    thread.workspace_id = 9
    thread.created_by = 1
    thread.title = "Renamed"
    thread.is_active = True
    from datetime import datetime, timezone

    thread.created_at = datetime.now(timezone.utc)
    thread.updated_at = datetime.now(timezone.utc)

    with (
        patch(
            "ai_routes.threads._repo.get_thread",
            new_callable=AsyncMock,
            side_effect=[thread, thread],
        ),
        patch(
            "ai.memory.service.ThreadService.rename_thread",
            new_callable=AsyncMock,
            return_value=True,
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.patch(
                f"/ai/threads/{thread.id}",
                json={"title": "Renamed"},
            )

    assert res.status_code == 200
    assert res.json()["title"] == "Renamed"
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_rename_thread_cross_workspace_404():
    app = create_app()

    async def _ctx() -> RequestContext:
        return RequestContext(user_id=1, workspace_id=9, role="owner")

    async def _db():
        yield AsyncMock()

    app.dependency_overrides[get_current_context] = _ctx
    app.dependency_overrides[get_session] = _db

    with patch(
        "ai_routes.threads._repo.get_thread",
        new_callable=AsyncMock,
        return_value=None,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.patch(
                "/ai/threads/11111111-1111-1111-1111-111111111111",
                json={"title": "Nope"},
            )

    assert res.status_code == 404
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_rename_thread_rejects_whitespace_title():
    app = create_app()

    async def _ctx() -> RequestContext:
        return RequestContext(user_id=1, workspace_id=9, role="owner")

    async def _db():
        yield AsyncMock()

    app.dependency_overrides[get_current_context] = _ctx
    app.dependency_overrides[get_session] = _db

    thread = MagicMock()
    with patch(
        "ai_routes.threads._repo.get_thread",
        new_callable=AsyncMock,
        return_value=thread,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.patch(
                "/ai/threads/11111111-1111-1111-1111-111111111111",
                json={"title": "   "},
            )

    # pydantic min_length=1 may pass spaces; route strips and returns 422
    assert res.status_code in (422, 422)
    app.dependency_overrides.clear()
