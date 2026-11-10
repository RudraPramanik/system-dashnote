"""9H.4.2 AI budget refusal. No live model key."""
from __future__ import annotations

import inspect
import logging
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from prometheus_client import REGISTRY, generate_latest
from redis.exceptions import RedisError

from ai.harness.budget_check import (
    OUTCOME_ALLOWED,
    OUTCOME_DENIED,
    OUTCOME_FAIL_OPEN,
    BudgetDecision,
    BudgetDenied,
    budget_denied_from,
    budget_redis_var,
    consume_ai_request_budget,
)
from ai.workflows.workspace_assistant import call_model
from ai_routes.agent import agent_reject
from ai_routes.chat import ChatRequest, chat, chat_stream
from config import settings
from core.security.context import RequestContext


class StubRedis:
    def __init__(self, *, start: int = 0, error: Exception | None = None) -> None:
        self.start = start
        self.error = error
        self.keys: list[str] = []
        self.expires: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        if self.error is not None:
            raise self.error
        self.keys.append(key)
        return self.start + self.keys.count(key)

    async def expire(self, key: str, seconds: int) -> bool:
        if self.error is not None:
            raise self.error
        self.expires[key] = seconds
        return True

    async def ttl(self, key: str) -> int:
        if self.error is not None:
            raise self.error
        if key.startswith("ai_req:"):
            return 15
        if key.startswith("ai_day:"):
            return 90
        return -1


def _ctx() -> RequestContext:
    return RequestContext(user_id=1, workspace_id=2, role="owner")


def _outcome_count(outcome: str) -> float:
    value = REGISTRY.get_sample_value(
        "dashnote_ai_budget_outcome_total",
        {"outcome": outcome},
    )
    return float(value or 0.0)


def _budget_series_lines() -> list[str]:
    body = generate_latest(REGISTRY).decode("utf-8")
    return [
        line
        for line in body.splitlines()
        if line.startswith("dashnote_ai_budget_outcome_total{")
    ]


@pytest.fixture
def tiny_ceiling(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "AI_USER_REQUESTS_PER_MINUTE", 1)
    monkeypatch.setattr(settings, "AI_WORKSPACE_REQUESTS_PER_DAY", 1)


@pytest.mark.asyncio
async def test_chat_over_budget_is_429_and_skips_the_model(tiny_ceiling) -> None:
    rag = AsyncMock()
    redis = StubRedis(start=1)
    with pytest.raises(HTTPException) as caught:
        await chat(
            ChatRequest(message="hello"),
            _ctx(),
            rag,
            AsyncMock(),
            redis,
        )
    assert caught.value.status_code == 429
    assert caught.value.headers is not None
    assert caught.value.headers["Retry-After"] == "90"
    rag.answer.assert_not_called()


@pytest.mark.asyncio
async def test_chat_stream_emits_budget_exceeded_and_ends(tiny_ceiling) -> None:
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
    assert body.rstrip().endswith("data: [DONE]")
    rag.stream_answer.assert_not_called()


@pytest.mark.asyncio
async def test_allowed_completion_increments_request_keys_only(tiny_ceiling) -> None:
    redis = StubRedis(start=0)
    decision = await consume_ai_request_budget(redis, "user-1", "ws-1")
    assert decision.outcome == OUTCOME_ALLOWED
    assert any(key.startswith("ai_req:user-1:") for key in redis.keys)
    assert any(key.startswith("ai_day:ws-1:") for key in redis.keys)
    assert not any(key.startswith("ai_tok:") for key in redis.keys)
    minute = next(key for key in redis.keys if key.startswith("ai_req:"))
    day = next(key for key in redis.keys if key.startswith("ai_day:"))
    assert redis.expires[minute] == 120
    assert redis.expires[day] == 48 * 60 * 60


@pytest.mark.asyncio
async def test_blank_identity_denies_without_anonymous_key() -> None:
    redis = StubRedis()
    before = _outcome_count("denied")
    decision = await consume_ai_request_budget(redis, "  ", "ws-1")
    assert decision.outcome == OUTCOME_DENIED
    assert redis.keys == []
    rendered = " ".join(redis.keys)
    assert "anonymous" not in rendered
    assert _outcome_count("denied") == before + 1


@pytest.mark.asyncio
async def test_redis_error_fails_open_with_a_warning(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING)
    before = _outcome_count("fail_open")
    decision = await consume_ai_request_budget(
        StubRedis(error=RedisError("down")),
        "user-1",
        "ws-1",
    )
    assert decision.outcome == OUTCOME_FAIL_OPEN
    assert "fail open" in caplog.text
    assert _outcome_count("fail_open") == before + 1


@pytest.mark.asyncio
async def test_call_model_raises_before_the_provider(tiny_ceiling) -> None:
    token = budget_redis_var.set(StubRedis(start=5))
    before = _outcome_count("denied")
    try:
        with patch(
            "shared.llm.fallback.acompletion_with_fallback",
            new=AsyncMock(),
        ) as llm:
            with pytest.raises(BudgetDenied):
                await call_model(
                    {
                        "user_id": "user-1",
                        "workspace_id": "ws-1",
                        "role": "owner",
                        "messages": [],
                    }
                )
            llm.assert_not_called()
    finally:
        budget_redis_var.reset(token)
    assert _outcome_count("denied") == before + 1


@pytest.mark.asyncio
async def test_distinct_tenants_share_the_allowed_series(tiny_ceiling) -> None:
    before = _outcome_count("allowed")
    first = await consume_ai_request_budget(StubRedis(), "user-1", "ws-1")
    second = await consume_ai_request_budget(StubRedis(), "user-2", "ws-2")
    assert first.outcome == OUTCOME_ALLOWED
    assert second.outcome == OUTCOME_ALLOWED
    assert _outcome_count("allowed") == before + 2
    series = [line for line in _budget_series_lines() if 'outcome="allowed"' in line]
    assert len(series) == 1
    assert "user-1" not in series[0]
    assert "user-2" not in series[0]
    assert "ws-1" not in series[0]
    assert "ws-2" not in series[0]
    assert "role" not in series[0]


def test_reject_does_not_consume_a_request() -> None:
    source = inspect.getsource(agent_reject)
    assert "consume_ai_request_budget" not in source
    assert "budget_redis_var" not in source


def test_health_handlers_do_not_touch_ai_budget_keys() -> None:
    from core.health import ai_health, deep_health

    for handler in (deep_health, ai_health):
        source = inspect.getsource(handler)
        assert "consume_ai_request_budget" not in source
        assert "inc_ai_budget_outcome" not in source
        assert "ai_req" not in source
        assert "ai_day" not in source
        assert "ai_tok" not in source


def test_wrapped_budget_denial_is_visible() -> None:
    denied = BudgetDenied(BudgetDecision(outcome=OUTCOME_DENIED, retry_after=5))
    wrapped = RuntimeError("graph wrapped the node")
    wrapped.__cause__ = denied
    assert budget_denied_from(wrapped) is denied
    assert budget_denied_from(denied) is denied
