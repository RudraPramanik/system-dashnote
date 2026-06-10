"""Unit tests for automation LLM task error handling — mocked structured client."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import litellm
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from shared.llm.structured import StructuredLLMParseError
from worker.automation.tasks import NoteTagAnalysis, generate_note_tags


@pytest.mark.asyncio
async def test_generate_note_tags_reraises_rate_limit():
    with (
        patch("config.get_settings") as mock_settings,
        patch(
            "shared.llm.structured.acompletion_structured",
            new_callable=AsyncMock,
            side_effect=litellm.exceptions.RateLimitError(
                message="429",
                llm_provider="test",
                model="test",
            ),
        ),
    ):
        settings = MagicMock()
        settings.ai_enabled = True
        settings.LLM_STRUCTURED_MAX_TOKENS_TAGS = 256
        mock_settings.return_value = settings

        with pytest.raises(litellm.exceptions.RateLimitError):
            await generate_note_tags(
                {},
                note_id="1",
                workspace_id="1",
                content="Quantum entanglement notes.",
                title="Quantum Lab",
            )


@pytest.mark.asyncio
async def test_generate_note_tags_reraises_parse_error():
    with (
        patch("config.get_settings") as mock_settings,
        patch(
            "shared.llm.structured.acompletion_structured",
            new_callable=AsyncMock,
            side_effect=StructuredLLMParseError("parse fail"),
        ),
    ):
        settings = MagicMock()
        settings.ai_enabled = True
        settings.LLM_STRUCTURED_MAX_TOKENS_TAGS = 256
        mock_settings.return_value = settings

        with pytest.raises(StructuredLLMParseError):
            await generate_note_tags(
                {},
                note_id="1",
                workspace_id="1",
                content="Some content",
                title="Title",
            )


@pytest.mark.asyncio
async def test_generate_note_tags_returns_on_auth_error():
    with (
        patch("config.get_settings") as mock_settings,
        patch(
            "shared.llm.structured.acompletion_structured",
            new_callable=AsyncMock,
            side_effect=litellm.exceptions.AuthenticationError(
                message="401",
                llm_provider="test",
                model="test",
            ),
        ),
    ):
        settings = MagicMock()
        settings.ai_enabled = True
        settings.LLM_STRUCTURED_MAX_TOKENS_TAGS = 256
        mock_settings.return_value = settings

        # Should return without raising
        await generate_note_tags(
            {},
            note_id="1",
            workspace_id="1",
            content="Content",
            title="Title",
        )


@pytest.mark.asyncio
async def test_generate_note_tags_commits_on_success():
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.first.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.commit = AsyncMock()

    mock_session = MagicMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_db)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    with (
        patch("config.get_settings") as mock_settings,
        patch(
            "shared.llm.structured.acompletion_structured",
            new_callable=AsyncMock,
            return_value=NoteTagAnalysis(tags=["quantum", "lab"]),
        ),
        patch(
            "core.database.session.AsyncSessionLocal",
            return_value=mock_session,
        ),
    ):
        settings = MagicMock()
        settings.ai_enabled = True
        settings.LLM_STRUCTURED_MAX_TOKENS_TAGS = 256
        mock_settings.return_value = settings

        await generate_note_tags(
            {},
            note_id="1",
            workspace_id="1",
            content="Entanglement experiment notes.",
            title="Quantum Lab",
        )

    mock_db.commit.assert_awaited_once()
