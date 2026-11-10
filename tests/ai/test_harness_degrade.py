"""9H.5.1 degrade matrix. No live model key."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from ai.harness.context import HarnessContext, harness_context_var
from ai.tools import note_tools
from ai_routes.chat import ChatRequest, chat
from core.security.context import RequestContext
from shared.llm.fallback import LLM_UNAVAILABLE_MESSAGE, LLMUnavailableError


def _ctx() -> RequestContext:
    return RequestContext(user_id=1, workspace_id=2, role="owner")


@pytest.mark.asyncio
async def test_chat_provider_exhaustion_is_503() -> None:
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
    assert LLM_UNAVAILABLE_MESSAGE in str(caught.value.detail)
    assert caught.value.detail != ""
    # Not an empty successful ChatResponse body
    assert not hasattr(caught.value, "answer")


@pytest.mark.asyncio
async def test_checkpointer_down_blocks_mutations_allows_search() -> None:
    session = HarnessContext(
        workspace_id="ws-session",
        user_id="user-1",
        role="owner",
    )
    token = harness_context_var.set(session)

    fake_rag = MagicMock()
    fake_rag.answer = AsyncMock(
        return_value=SimpleNamespace(answer="search-ok"),
    )
    mock_svc = MagicMock()
    mock_svc.create_note = AsyncMock()
    mock_svc.update_note = AsyncMock()
    mock_svc.decide_update = AsyncMock()

    try:
        with (
            patch(
                "ai.memory.checkpointer.get_graph_checkpointer",
                side_effect=RuntimeError("no cp"),
            ),
            patch("notes.service.NoteService", return_value=mock_svc),
            patch("ai.services.rag_service.get_rag_service", return_value=fake_rag),
        ):
            create_result = await note_tools._create_note(
                title="t",
                content="c",
            )
            update_result = await note_tools._update_note(
                note_id="n1",
                content="c2",
            )
            search_result = await note_tools._search_notes(question="alpha")

        assert note_tools.is_checkpointer_blocked_tool_result(create_result) is True
        assert note_tools.is_checkpointer_blocked_tool_result(update_result) is True
        assert "checkpointer" in str(create_result).lower()
        assert "checkpointer" in str(update_result).lower()
        mock_svc.create_note.assert_not_called()
        mock_svc.update_note.assert_not_called()
        mock_svc.decide_update.assert_not_called()

        assert search_result == "search-ok"
        fake_rag.answer.assert_awaited()
        assert "checkpointer" not in str(search_result).lower()
    finally:
        harness_context_var.reset(token)
