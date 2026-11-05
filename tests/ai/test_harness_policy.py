"""9H.2 tool ACL and error envelopes. No live model key."""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai.harness.context import HarnessContext, harness_context_var
from ai.harness.errors import (
    CODE_FORBIDDEN,
    CODE_NOT_FOUND,
    CODE_UPSTREAM,
    _UPSTREAM_FALLBACK,
    tool_error,
)
from ai.tools import note_tools
from notes.service import (
    NoteAccessDeniedError,
    NoteService,
    NoteUpdateDecision,
)


def _envelope(raw: str) -> dict:
    body = json.loads(raw)
    assert body["ok"] is False
    assert "traceback" not in json.dumps(body).lower()
    return body


def _session(role: str, user_id: str = "7") -> HarnessContext:
    return HarnessContext(workspace_id="4", user_id=user_id, role=role)


class _NoteService:
    def __init__(self, decision: NoteUpdateDecision):
        self.decide_update = AsyncMock(return_value=decision)
        self.update_note = AsyncMock()
        self.create_note = AsyncMock()


def _bind(role: str, user_id: str = "7"):
    harness_token = harness_context_var.set(_session(role, user_id))
    db_token = note_tools.db_session_var.set(object())
    return harness_token, db_token


def _reset(tokens) -> None:
    harness_token, db_token = tokens
    harness_context_var.reset(harness_token)
    note_tools.db_session_var.reset(db_token)


@pytest.mark.asyncio
async def test_forbidden_update_does_not_commit():
    """Member update the notes API would reject: forbidden, no interrupt, no write."""
    tokens = _bind("member", user_id="7")
    svc = _NoteService(NoteUpdateDecision("forbidden"))
    interrupt = MagicMock(side_effect=AssertionError("HITL must not start"))
    try:
        with (
            patch(
                "ai.memory.checkpointer.get_graph_checkpointer",
                return_value=object(),
            ),
            patch("notes.service.NoteService", return_value=svc),
            patch("langgraph.types.interrupt", interrupt),
        ):
            result = await note_tools._update_note(note_id="15", content="hacked")
        body = _envelope(result)
        assert body["code"] == CODE_FORBIDDEN
        svc.update_note.assert_not_called()
        svc.create_note.assert_not_called()
        interrupt.assert_not_called()
    finally:
        _reset(tokens)


@pytest.mark.asyncio
async def test_owner_update_interrupts_without_commit():
    tokens = _bind("owner")
    svc = _NoteService(NoteUpdateDecision("allowed"))

    class _Interrupt(Exception):
        def __init__(self, value):
            self.value = value

    def _pause(payload):
        raise _Interrupt(payload)

    try:
        with (
            patch(
                "ai.memory.checkpointer.get_graph_checkpointer",
                return_value=object(),
            ),
            patch("notes.service.NoteService", return_value=svc),
            patch("langgraph.types.interrupt", side_effect=_pause),
        ):
            with pytest.raises(_Interrupt) as raised:
                await note_tools._update_note(note_id="15", content="edited")
        payload = raised.value.value
        assert payload["tool"] == "update_note"
        assert payload["args"]["role"] == "owner"
        assert payload["args"]["workspace_id"] == "4"
        svc.update_note.assert_not_called()
    finally:
        _reset(tokens)


@pytest.mark.asyncio
async def test_missing_note_is_not_found_without_interrupt():
    tokens = _bind("admin")
    svc = _NoteService(NoteUpdateDecision("not_found"))
    interrupt = MagicMock(side_effect=AssertionError("HITL must not start"))
    try:
        with (
            patch(
                "ai.memory.checkpointer.get_graph_checkpointer",
                return_value=object(),
            ),
            patch("notes.service.NoteService", return_value=svc),
            patch("langgraph.types.interrupt", interrupt),
        ):
            result = await note_tools._update_note(note_id="99", content="x")
        assert _envelope(result)["code"] == CODE_NOT_FOUND
        svc.update_note.assert_not_called()
        interrupt.assert_not_called()
    finally:
        _reset(tokens)


@pytest.mark.asyncio
async def test_unknown_role_does_not_call_rag_or_create():
    tokens = _bind("guest")
    fake_rag = MagicMock()
    fake_rag.answer = AsyncMock()
    create = AsyncMock()
    try:
        with (
            patch("ai.services.rag_service.get_rag_service", return_value=fake_rag),
            patch("notes.service.NoteService") as service_cls,
        ):
            service_cls.return_value.create_note = create
            search = await note_tools._search_notes(question="alpha")
            summary = await note_tools._summarize_workspace()
            created = await note_tools._create_note(title="T", content="Body")
        for raw in (search, summary, created):
            assert _envelope(raw)["code"] == CODE_FORBIDDEN
        fake_rag.answer.assert_not_called()
        create.assert_not_called()
    finally:
        _reset(tokens)


@pytest.mark.asyncio
async def test_service_exception_is_upstream_without_stack_trace():
    tokens = _bind("member")
    svc = _NoteService(NoteUpdateDecision("allowed"))
    svc.decide_update.side_effect = RuntimeError("Traceback secret boom")
    try:
        with (
            patch(
                "ai.memory.checkpointer.get_graph_checkpointer",
                return_value=object(),
            ),
            patch("notes.service.NoteService", return_value=svc),
        ):
            result = await note_tools._update_note(note_id="15", content="x")
        body = _envelope(result)
        assert body["code"] == CODE_UPSTREAM
        assert "secret" not in result
        assert "Traceback" not in result
        svc.update_note.assert_not_called()
    finally:
        _reset(tokens)


@pytest.mark.asyncio
async def test_missing_harness_context_is_forbidden():
    harness_token = harness_context_var.set(None)
    fake_rag = MagicMock()
    fake_rag.answer = AsyncMock()
    try:
        with patch("ai.services.rag_service.get_rag_service", return_value=fake_rag):
            result = await note_tools._search_notes(question="alpha")
        assert _envelope(result)["code"] == CODE_FORBIDDEN
        fake_rag.answer.assert_not_called()
    finally:
        harness_context_var.reset(harness_token)


@pytest.mark.asyncio
async def test_user_reject_is_not_forbidden_and_does_not_commit():
    tokens = _bind("member")
    svc = _NoteService(NoteUpdateDecision("allowed"))
    try:
        with (
            patch(
                "ai.memory.checkpointer.get_graph_checkpointer",
                return_value=object(),
            ),
            patch("notes.service.NoteService", return_value=svc),
            patch(
                "langgraph.types.interrupt",
                return_value={"action": "reject"},
            ),
        ):
            result = await note_tools._update_note(note_id="15", content="x")
        assert result == "Note update rejected by user. No changes were saved."
        assert CODE_FORBIDDEN not in result
        svc.update_note.assert_not_called()
    finally:
        _reset(tokens)


@pytest.mark.asyncio
async def test_approved_update_success_stays_prose():
    tokens = _bind("owner")
    svc = _NoteService(NoteUpdateDecision("allowed"))
    svc.update_note.return_value = {"note_id": "15", "title": "T"}
    try:
        with (
            patch(
                "ai.memory.checkpointer.get_graph_checkpointer",
                return_value=object(),
            ),
            patch("notes.service.NoteService", return_value=svc),
            patch(
                "langgraph.types.interrupt",
                return_value={"action": "approve"},
            ),
        ):
            result = await note_tools._update_note(note_id="15", content="edited")
        assert result == "Note updated successfully. ID: 15"
        assert not result.startswith("{")
        svc.update_note.assert_awaited()
    finally:
        _reset(tokens)


def test_tool_error_uses_fixed_upstream_when_serialization_fails(monkeypatch):
    def _boom(*_args, **_kwargs):
        raise TypeError("cannot encode")

    monkeypatch.setattr("ai.harness.errors.json.dumps", _boom)
    assert tool_error("forbidden", "nope") == _UPSTREAM_FALLBACK


def test_reserved_codes_are_named_and_not_redis():
    import ai.harness.errors as errors

    assert "budget_exceeded" in errors.RESERVED_TOOL_ERROR_CODES
    assert "approval_required" in errors.RESERVED_TOOL_ERROR_CODES
    source = open(errors.__file__, encoding="utf-8").read().splitlines()
    imports = [
        line
        for line in source
        if line.startswith("import ") or line.startswith("from ")
    ]
    assert all("redis" not in line.lower() for line in imports)


@pytest.mark.asyncio
async def test_unknown_role_decision_does_not_load_note():
    svc = NoteService()
    with patch("notes.service.NoteRepository") as repo_cls:
        decision = await svc.decide_update(
            object(),
            note_id="15",
            workspace_id="4",
            user_id="7",
            role="guest",
        )
    assert decision.outcome == "forbidden"
    repo_cls.assert_not_called()


@pytest.mark.asyncio
async def test_member_cannot_manage_another_users_note():
    svc = NoteService()
    note = SimpleNamespace(created_by=2, id=15, title="T")
    repo = MagicMock()
    repo.get = AsyncMock(return_value=note)
    with patch("notes.service.NoteRepository", return_value=repo):
        decision = await svc.decide_update(
            object(),
            note_id="15",
            workspace_id="4",
            user_id="7",
            role="member",
        )
    assert decision.outcome == "forbidden"


@pytest.mark.asyncio
async def test_update_recheck_denies_before_save():
    svc = NoteService()
    note = SimpleNamespace(created_by=2, id=15, title="T")
    repo = MagicMock()
    repo.get = AsyncMock(return_value=note)
    repo.save = AsyncMock()
    with (
        patch.object(
            svc,
            "decide_update",
            AsyncMock(return_value=NoteUpdateDecision("allowed")),
        ),
        patch("notes.service.NoteRepository", return_value=repo),
    ):
        with pytest.raises(NoteAccessDeniedError):
            await svc.update_note(
                object(),
                note_id="15",
                content="edited",
                workspace_id="4",
                updated_by="7",
                role="member",
            )
    repo.save.assert_not_called()
