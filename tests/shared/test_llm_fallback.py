"""Unit tests for LLM model-gone fallback — no live HTTP."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from shared.llm.fallback import (
    LLMUnavailableError,
    acompletion_with_fallback,
    is_model_gone,
    reset_fallback_state,
)


@pytest.fixture(autouse=True)
def _reset_fallback():
    reset_fallback_state()
    yield
    reset_fallback_state()


def test_is_model_gone_detects_410_text():
    assert is_model_gone(RuntimeError("Error code: 410 - end of life"))
    assert is_model_gone(RuntimeError("The model has reached its end of life"))
    assert not is_model_gone(RuntimeError("timeout"))


@pytest.mark.asyncio
async def test_fallback_skips_gone_primary():
    settings = MagicMock()
    settings.llm_model_candidates = ["gone-model", "live-model"]

    async def fake_retry(**kwargs):
        if kwargs["model"] == "gone-model":
            raise RuntimeError("Error code: 410 - no longer available")
        return {"ok": True}

    with (
        patch("shared.llm.fallback.get_settings", return_value=settings),
        patch(
            "shared.llm.fallback.acompletion_with_retry",
            new_callable=AsyncMock,
            side_effect=fake_retry,
        ),
    ):
        result = await acompletion_with_fallback(messages=[{"role": "user", "content": "hi"}])

    assert result == {"ok": True}


@pytest.mark.asyncio
async def test_all_candidates_gone_raises_unavailable():
    settings = MagicMock()
    settings.llm_model_candidates = ["a", "b"]

    with (
        patch("shared.llm.fallback.get_settings", return_value=settings),
        patch(
            "shared.llm.fallback.acompletion_with_retry",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Error code: 410 - gone"),
        ),
    ):
        with pytest.raises(LLMUnavailableError, match="LLM temporarily unavailable"):
            await acompletion_with_fallback(messages=[{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_stream_fallback_uses_litellm_acompletion():
    settings = MagicMock()
    settings.llm_model_candidates = ["gone-model", "live-model"]

    async def fake_complete(**kwargs):
        if kwargs["model"] == "gone-model":
            raise RuntimeError("Error code: 410 - end of life")
        return {"stream": True}

    with (
        patch("shared.llm.fallback.get_settings", return_value=settings),
        patch(
            "shared.llm.fallback.litellm.acompletion",
            new_callable=AsyncMock,
            side_effect=fake_complete,
        ),
    ):
        result = await acompletion_with_fallback(
            messages=[{"role": "user", "content": "hi"}],
            stream=True,
        )

    assert result == {"stream": True}


@pytest.mark.asyncio
async def test_fallback_skips_timed_out_primary():
    settings = MagicMock()
    settings.llm_model_candidates = ["slow-model", "live-model"]
    settings.AGENT_TOOL_TIMEOUT = 0.05

    async def fake_retry(**kwargs):
        if kwargs["model"] == "slow-model":
            await __import__("asyncio").sleep(1)
        return {"ok": True}

    with (
        patch("shared.llm.fallback.get_settings", return_value=settings),
        patch(
            "shared.llm.fallback.acompletion_with_retry",
            new_callable=AsyncMock,
            side_effect=fake_retry,
        ),
    ):
        result = await acompletion_with_fallback(
            messages=[{"role": "user", "content": "hi"}]
        )

    assert result == {"ok": True}


@pytest.mark.asyncio
async def test_all_candidates_timeout_raises_unavailable():
    settings = MagicMock()
    settings.llm_model_candidates = ["a", "b"]
    settings.AGENT_TOOL_TIMEOUT = 0.05

    async def fake_retry(**kwargs):
        await __import__("asyncio").sleep(1)
        return {"ok": True}

    with (
        patch("shared.llm.fallback.get_settings", return_value=settings),
        patch(
            "shared.llm.fallback.acompletion_with_retry",
            new_callable=AsyncMock,
            side_effect=fake_retry,
        ),
    ):
        with pytest.raises(LLMUnavailableError, match="LLM temporarily unavailable"):
            await acompletion_with_fallback(messages=[{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_nvidia_thinking_disabled_on_nim_candidate():
    settings = MagicMock()
    settings.llm_model_candidates = ["nvidia_nim/nvidia/nemotron-3.5-lightning-30b-a3b"]
    settings.AGENT_TOOL_TIMEOUT = 30

    captured: dict = {}

    async def fake_retry(**kwargs):
        captured.update(kwargs)
        return {"ok": True}

    with (
        patch("shared.llm.fallback.get_settings", return_value=settings),
        patch(
            "shared.llm.fallback.acompletion_with_retry",
            new_callable=AsyncMock,
            side_effect=fake_retry,
        ),
    ):
        await acompletion_with_fallback(messages=[{"role": "user", "content": "hi"}])

    extra = captured.get("extra_body") or {}
    assert extra.get("chat_template_kwargs", {}).get("enable_thinking") is False
