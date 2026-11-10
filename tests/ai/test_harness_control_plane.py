"""9H.5.3 harness control plane. No live model key."""
from __future__ import annotations

import inspect
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from ai.harness.control_plane import (
    LLM_UNAVAILABLE_MESSAGE,
    LLMUnavailableError,
    gate_ai_request_budget,
    is_provider_unavailable,
    provider_unavailable_message,
)
from ai_routes import agent as agent_routes
from ai_routes import chat as chat_routes
from ai_routes.chat import ChatRequest, chat, chat_stream
from core.security.context import RequestContext
from tests.ai.test_harness_budget_refusal import StubRedis


def _ctx() -> RequestContext:
    return RequestContext(user_id=1, workspace_id=2, role="owner")


def test_chat_and_agent_routes_do_not_call_budget_check_directly() -> None:
    chat_src = inspect.getsource(chat_routes)
    agent_src = inspect.getsource(agent_routes)
    assert "consume_ai_request_budget" not in chat_src
    assert "consume_ai_request_budget" not in agent_src
    assert "from ai.harness.budget_check" not in chat_src
    assert "from ai.harness.budget_check" not in agent_src
    assert "gate_ai_request_budget" in chat_src
    assert "bind_agent_harness" in agent_src
    assert "ai.harness.control_plane" in chat_src
    assert "ai.harness.control_plane" in agent_src


def test_reject_skips_budget_redis_bind() -> None:
    source = inspect.getsource(agent_routes.agent_reject)
    assert "with_budget_redis=False" in source
    assert "consume_ai_request_budget" not in source
    assert "gate_ai_request_budget" not in source


@pytest.mark.asyncio
async def test_over_budget_still_429_via_control_plane(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from config import settings

    monkeypatch.setattr(settings, "AI_USER_REQUESTS_PER_MINUTE", 1)
    monkeypatch.setattr(settings, "AI_WORKSPACE_REQUESTS_PER_DAY", 1)
    rag = AsyncMock()
    with pytest.raises(HTTPException) as caught:
        await chat(
            ChatRequest(message="hello"),
            _ctx(),
            rag,
            AsyncMock(),
            StubRedis(start=1),
        )
    assert caught.value.status_code == 429
    rag.answer.assert_not_called()


@pytest.mark.asyncio
async def test_over_budget_stream_emits_budget_exceeded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from config import settings

    monkeypatch.setattr(settings, "AI_USER_REQUESTS_PER_MINUTE", 1)
    monkeypatch.setattr(settings, "AI_WORKSPACE_REQUESTS_PER_DAY", 1)
    rag = AsyncMock()
    response = await chat_stream(
        ChatRequest(message="hello"),
        _ctx(),
        rag,
        AsyncMock(),
        StubRedis(start=1),
    )
    frames: list[str] = []
    async for part in response.body_iterator:
        frames.append(part.decode() if isinstance(part, bytes) else part)
    body = "".join(frames)
    assert '"code": "budget_exceeded"' in body
    rag.stream_answer.assert_not_called()


@pytest.mark.asyncio
async def test_provider_exhaustion_still_503_via_control_plane() -> None:
    rag = AsyncMock()
    rag.answer = AsyncMock(side_effect=LLMUnavailableError())
    with pytest.raises(HTTPException) as caught:
        await chat(
            ChatRequest(message="hello"),
            _ctx(),
            rag,
            AsyncMock(),
            None,
        )
    assert caught.value.status_code == 503
    assert caught.value.detail == LLM_UNAVAILABLE_MESSAGE


def test_provider_unavailable_helpers() -> None:
    exc = LLMUnavailableError()
    assert is_provider_unavailable(exc) is True
    assert provider_unavailable_message(exc) == LLM_UNAVAILABLE_MESSAGE
    assert is_provider_unavailable(ValueError("nope")) is False


@pytest.mark.asyncio
async def test_gate_delegates_to_budget_check() -> None:
    decision = await gate_ai_request_budget(StubRedis(start=0), "user-1", "ws-1")
    assert decision.outcome == "allowed"
