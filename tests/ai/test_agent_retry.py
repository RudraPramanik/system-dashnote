"""Unit tests for agent LLM retry error mapping."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import litellm
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from fastapi import HTTPException

from shared.llm.fallback import LLMUnavailableError
from ai_routes.agent import agent_chat


@pytest.mark.asyncio
async def test_agent_maps_rate_limit_to_503():
    ctx = MagicMock()
    ctx.workspace_id = 1
    ctx.user_id = 1
    ctx.role = "owner"

    body = MagicMock()
    body.message = "Search my notes for quantum"
    body.thread_id = None

    mock_graph = AsyncMock()
    mock_graph.ainvoke = AsyncMock(
        side_effect=litellm.exceptions.RateLimitError(
            message="429",
            llm_provider="test",
            model="test",
        )
    )

    with (
        patch("ai_routes.agent._resolve_thread_id", new_callable=AsyncMock, return_value="t1"),
        patch("ai_routes.agent.get_workspace_assistant", return_value=mock_graph),
        patch("ai_routes.agent.db_session_var"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await agent_chat(body=body, ctx=ctx, db=AsyncMock())

    assert exc_info.value.status_code == 503
    assert "LLM temporarily unavailable" in exc_info.value.detail


@pytest.mark.asyncio
async def test_agent_maps_llm_unavailable_to_503():
    ctx = MagicMock()
    ctx.workspace_id = 1
    ctx.user_id = 1
    ctx.role = "owner"

    body = MagicMock()
    body.message = "Search my notes"
    body.thread_id = None

    mock_graph = AsyncMock()
    mock_graph.ainvoke = AsyncMock(side_effect=LLMUnavailableError())

    with (
        patch("ai_routes.agent._resolve_thread_id", new_callable=AsyncMock, return_value="t1"),
        patch("ai_routes.agent.get_workspace_assistant", return_value=mock_graph),
        patch("ai_routes.agent.db_session_var"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await agent_chat(body=body, ctx=ctx, db=AsyncMock())

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "LLM temporarily unavailable; retry shortly"


@pytest.mark.asyncio
async def test_agent_stream_unavailable_copy():
    ctx = MagicMock()
    ctx.workspace_id = 1
    ctx.user_id = 1
    ctx.role = "owner"

    body = MagicMock()
    body.message = "Search my notes"
    body.thread_id = None

    async def _fail_events(*args, **kwargs):
        raise LLMUnavailableError()
        yield  # pragma: no cover — make this an async generator

    mock_graph = MagicMock()
    mock_graph.astream_events = _fail_events
    mock_graph.aget_state = AsyncMock()

    from ai_routes.agent import agent_chat_stream

    with (
        patch("ai_routes.agent._resolve_thread_id", new_callable=AsyncMock, return_value="t1"),
        patch("ai_routes.agent.get_workspace_assistant", return_value=mock_graph),
        patch("ai_routes.agent.db_session_var"),
    ):
        response = await agent_chat_stream(body=body, ctx=ctx, db=AsyncMock())
        chunks: list[str] = []
        async for chunk in response.body_iterator:
            if isinstance(chunk, bytes):
                chunks.append(chunk.decode())
            else:
                chunks.append(str(chunk))

    text = "".join(chunks)
    assert "LLM temporarily unavailable; retry shortly" in text
    assert '"type": "error"' in text or '"type":"error"' in text


@pytest.mark.asyncio
async def test_chat_stream_unavailable_copy():
    from ai_routes.chat import chat_stream

    ctx = MagicMock()
    ctx.workspace_id = 1
    ctx.user_id = 1
    ctx.role = "owner"

    body = MagicMock()
    body.message = "hi"
    body.thread_id = None

    async def _fail(*args, **kwargs):
        raise LLMUnavailableError()
        yield  # pragma: no cover

    rag = MagicMock()
    rag.stream_answer = _fail

    response = await chat_stream(body=body, ctx=ctx, rag=rag, db=AsyncMock())
    chunks: list[str] = []
    async for chunk in response.body_iterator:
        if isinstance(chunk, bytes):
            chunks.append(chunk.decode())
        else:
            chunks.append(str(chunk))

    text = "".join(chunks)
    assert "LLM temporarily unavailable; retry shortly" in text
    assert '"type": "error"' in text or '"type":"error"' in text
