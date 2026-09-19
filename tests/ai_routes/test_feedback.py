"""POST /ai/feedback authorization and soft tracing."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from core.database.session import get_session
from core.security.context import RequestContext
from core.security.dependency import get_current_context
from main import create_app

THREAD_ID = "11111111-1111-1111-1111-111111111111"


def _app_with_ctx(*, workspace_id: int = 9):
    app = create_app()

    async def _ctx() -> RequestContext:
        return RequestContext(user_id=1, workspace_id=workspace_id, role="owner")

    async def _db():
        yield AsyncMock()

    app.dependency_overrides[get_current_context] = _ctx
    app.dependency_overrides[get_session] = _db
    return app


def _thread(workspace_id: int = 9) -> MagicMock:
    thread = MagicMock()
    thread.id = THREAD_ID
    thread.workspace_id = workspace_id
    thread.created_by = 1
    thread.title = "t"
    thread.is_active = True
    thread.created_at = datetime.now(timezone.utc)
    thread.updated_at = datetime.now(timezone.utc)
    return thread


@pytest.mark.asyncio
async def test_feedback_foreign_thread_404() -> None:
    app = _app_with_ctx(workspace_id=9)
    with patch(
        "ai_routes.feedback._repo.get_thread",
        new_callable=AsyncMock,
        return_value=None,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post(
                "/ai/feedback",
                json={"thread_id": THREAD_ID, "thumbs": "down"},
            )
    assert res.status_code in (403, 404)
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_feedback_ok_when_langfuse_off() -> None:
    app = _app_with_ctx()
    with (
        patch(
            "ai_routes.feedback._repo.get_thread",
            new_callable=AsyncMock,
            return_value=_thread(),
        ),
        patch("ai_routes.feedback.lookup_thread_trace", return_value=None),
        patch("ai_routes.feedback.score_by_trace_id", return_value=False),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post(
                "/ai/feedback",
                json={"thread_id": THREAD_ID, "thumbs": "up"},
            )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["tracing"] == "unavailable"
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_feedback_accepts_numeric_score() -> None:
    app = _app_with_ctx()
    with (
        patch(
            "ai_routes.feedback._repo.get_thread",
            new_callable=AsyncMock,
            return_value=_thread(),
        ),
        patch("ai_routes.feedback.lookup_thread_trace", return_value=None),
        patch("ai_routes.feedback.score_by_trace_id", return_value=False),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post(
                "/ai/feedback",
                json={"thread_id": THREAD_ID, "score": 4},
            )
    assert res.status_code == 200
    assert res.json()["tracing"] == "unavailable"
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_chat_and_agent_schemas_do_not_require_feedback() -> None:
    from ai_routes.agent import AgentResponse, ApprovalRequiredResponse
    from ai_routes.chat import ChatResponse

    chat = ChatResponse(
        answer="ok",
        citations=[],
        chunks_retrieved=0,
        chunks_used=0,
        latency_ms=1.0,
    )
    dumped = chat.model_dump()
    for key in ("answer", "citations", "chunks_retrieved", "chunks_used", "latency_ms"):
        assert key in dumped
    assert "feedback" not in dumped

    agent = AgentResponse(
        answer="ok",
        thread_id=THREAD_ID,
        steps_taken=1,
        tool_calls_made=0,
    )
    agent_dump = agent.model_dump()
    for key in ("status", "answer", "thread_id", "steps_taken", "tool_calls_made"):
        assert key in agent_dump

    hitl = ApprovalRequiredResponse(
        tool="create_note",
        args={"title": "x"},
        thread_id=THREAD_ID,
        interrupt_id="iid",
    )
    hitl_dump = hitl.model_dump()
    for key in ("status", "type", "tool", "args", "thread_id", "interrupt_id"):
        assert key in hitl_dump
