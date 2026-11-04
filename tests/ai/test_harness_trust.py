"""9H.1 trusted-tenant bind: HarnessContext wins; invented workspace never reaches services."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai.harness.context import (
    MISSING_HARNESS_MESSAGE,
    HarnessContext,
    harness_context_var,
)
from ai.tools import note_tools
from ai.tools.schemas import (
    CreateNoteArgs,
    SearchNotesArgs,
    SummarizeWorkspaceArgs,
    UpdateNoteArgs,
)


def test_tool_schemas_omit_tenant_fields():
    for model in (
        SearchNotesArgs,
        CreateNoteArgs,
        UpdateNoteArgs,
        SummarizeWorkspaceArgs,
    ):
        fields = set(model.model_fields)
        assert "workspace_id" not in fields
        assert "user_id" not in fields
        assert "role" not in fields


@pytest.mark.asyncio
async def test_search_uses_harness_workspace_not_foreign():
    """Foreign workspace cannot be selected — schemas omit it; service gets session only."""
    session = HarnessContext(
        workspace_id="ws-session",
        user_id="user-1",
        role="owner",
    )
    token = harness_context_var.set(session)
    captured: dict = {}

    async def _fake_answer(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(answer="ok")

    fake_rag = MagicMock()
    fake_rag.answer = AsyncMock(side_effect=_fake_answer)

    try:
        with patch("ai.services.rag_service.get_rag_service", return_value=fake_rag):
            # Extra kwargs would be what a model invents; pydantic schema strips them
            # before StructuredTool call. Direct coroutine only accepts question.
            result = await note_tools._search_notes(question="alpha")
        assert result == "ok"
        assert captured["workspace_id"] == "ws-session"
        assert captured["user_id"] == "user-1"
        assert captured["role"] == "owner"
        assert captured["workspace_id"] != "ws-foreign"
    finally:
        harness_context_var.reset(token)


@pytest.mark.asyncio
async def test_search_denies_without_harness_context():
    token = harness_context_var.set(None)
    fake_rag = MagicMock()
    fake_rag.answer = AsyncMock()
    try:
        with patch("ai.services.rag_service.get_rag_service", return_value=fake_rag):
            result = await note_tools._search_notes(question="alpha")
        assert result == MISSING_HARNESS_MESSAGE
        fake_rag.answer.assert_not_called()
    finally:
        harness_context_var.reset(token)


@pytest.mark.asyncio
async def test_create_approval_args_use_harness_tenant():
    """HITL approval payload tenant fields are server-authored from HarnessContext."""
    session = HarnessContext(
        workspace_id="ws-session",
        user_id="user-1",
        role="member",
    )
    token = harness_context_var.set(session)

    class _Interrupt(Exception):
        def __init__(self, value):
            self.value = value

    def _fake_interrupt(payload):
        raise _Interrupt(payload)

    try:
        with (
            patch(
                "ai.memory.checkpointer.get_graph_checkpointer",
                return_value=object(),
            ),
            patch("langgraph.types.interrupt", side_effect=_fake_interrupt),
        ):
            with pytest.raises(_Interrupt) as raised:
                await note_tools._create_note(title="T", content="Body")
        payload = raised.value.value
        assert payload["tool"] == "create_note"
        args = payload["args"]
        assert args["workspace_id"] == "ws-session"
        assert args["user_id"] == "user-1"
        assert args["role"] == "member"
        assert args["title"] == "T"
        assert args["content"] == "Body"
        assert args["workspace_id"] != "ws-foreign"
    finally:
        harness_context_var.reset(token)


def test_search_notes_args_rejects_invented_workspace_as_schema_field():
    """Model-invented workspace_id is not a declared tool argument (9H.1.4 theme)."""
    parsed = SearchNotesArgs.model_validate(
        {"question": "q", "workspace_id": "ws-foreign"}
    )
    assert parsed.question == "q"
    assert not hasattr(parsed, "workspace_id") or "workspace_id" not in parsed.model_fields
    dumped = parsed.model_dump()
    assert "workspace_id" not in dumped
