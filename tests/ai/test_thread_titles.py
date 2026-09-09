"""Unit tests for conversation auto-title helpers and ThreadService gates."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from ai.memory.titles import deterministic_thread_title, generate_thread_title
from ai.memory.service import ThreadService


def test_deterministic_title_truncates_and_normalizes():
    title = deterministic_thread_title("  hello   world  " + ("x" * 100))
    assert "  " not in title
    assert title.startswith("hello world")
    assert len(title) <= 80
    assert title.endswith("…")


def test_deterministic_title_empty_fallback():
    assert deterministic_thread_title("   ") == "New conversation"


@pytest.mark.asyncio
async def test_generate_title_falls_back_when_ai_disabled():
    with patch("ai.memory.titles.get_settings") as settings:
        settings.return_value.ai_enabled = False
        title = await generate_thread_title("Pricing decision for Q3")
    assert title == "Pricing decision for Q3"


@pytest.mark.asyncio
async def test_generate_title_falls_back_when_llm_fails():
    with (
        patch("ai.memory.titles.get_settings") as settings,
        patch(
            "shared.llm.fallback.acompletion_with_fallback",
            new_callable=AsyncMock,
            side_effect=RuntimeError("boom"),
        ),
    ):
        settings.return_value.ai_enabled = True
        title = await generate_thread_title("Help with invoices", "Sure, here is help")
    assert title == "Help with invoices"


@pytest.mark.asyncio
async def test_generate_title_uses_polished_llm_result():
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message.content = "Q3 invoice help"

    with (
        patch("ai.memory.titles.get_settings") as settings,
        patch(
            "shared.llm.fallback.acompletion_with_fallback",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ),
    ):
        settings.return_value.ai_enabled = True
        title = await generate_thread_title("Help with invoices", "Sure")
    assert title == "Q3 invoice help"


@pytest.mark.asyncio
async def test_set_title_for_new_thread_skips_when_not_created():
    svc = ThreadService()
    with patch("ai.memory.service._repo") as repo:
        repo.update_thread_title = AsyncMock(return_value=True)
        ok = await svc.set_title_for_new_thread(
            AsyncMock(),
            thread_id="t1",
            workspace_id="1",
            title="Hello",
            created_this_request=False,
        )
    assert ok is False
    repo.update_thread_title.assert_not_called()


@pytest.mark.asyncio
async def test_set_title_for_new_thread_writes_when_created():
    svc = ThreadService()
    with patch("ai.memory.service._repo") as repo:
        repo.update_thread_title = AsyncMock(return_value=True)
        ok = await svc.set_title_for_new_thread(
            AsyncMock(),
            thread_id="t1",
            workspace_id="1",
            title="Hello",
            created_this_request=True,
        )
    assert ok is True
    repo.update_thread_title.assert_awaited_once()


@pytest.mark.asyncio
async def test_rename_thread_rejects_blank():
    svc = ThreadService()
    with patch("ai.memory.service._repo") as repo:
        repo.update_thread_title = AsyncMock(return_value=True)
        ok = await svc.rename_thread(
            AsyncMock(),
            thread_id="t1",
            workspace_id="1",
            title="   ",
        )
    assert ok is False
    repo.update_thread_title.assert_not_called()


@pytest.mark.asyncio
async def test_maybe_auto_title_skips_existing_thread():
    from ai.services.rag_service import RagService

    svc = RagService()
    with patch("ai.memory.service.ThreadService.set_title_for_new_thread", new_callable=AsyncMock) as setter:
        title = await svc._maybe_auto_title(
            db=AsyncMock(),
            thread_id="t1",
            workspace_id="1",
            question="hi",
            answer="hello",
            created_this_request=False,
        )
    assert title is None
    setter.assert_not_called()
