"""Hard /health must not depend on LLM; /health/ai reports llm softly."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import Response

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from core.health import _probe_llm, ai_health, deep_health


@pytest.mark.asyncio
async def test_hard_health_ok_when_llm_down():
    db = AsyncMock()
    db.execute = AsyncMock()
    redis = AsyncMock()
    redis.ping = AsyncMock()
    response = Response()

    with (
        patch("core.health._redis_expected", return_value=True),
        patch("core.health.check_database", new_callable=AsyncMock),
        patch("core.health.check_redis", new_callable=AsyncMock),
    ):
        payload = await deep_health(response=response, db=db, redis=redis)

    assert payload["status"] == "ok"
    assert "llm" not in payload["dependencies"]


@pytest.mark.asyncio
async def test_health_ai_includes_llm_and_stays_soft():
    with (
        patch("core.health.settings") as settings,
        patch(
            "core.health._probe_qdrant",
            new_callable=AsyncMock,
            return_value={"reachable": True, "configured": True},
        ),
        patch(
            "core.health._probe_llm",
            new_callable=AsyncMock,
            return_value={"reachable": False, "configured": True},
        ),
        patch(
            "core.health._probe_checkpointer",
            return_value={"reachable": True, "configured": True},
        ),
    ):
        settings.qdrant_enabled = True
        settings.langfuse_enabled = False
        settings.effective_langfuse_host = "https://cloud.langfuse.com"
        payload = await ai_health()

    assert payload["status"] == "degraded"
    assert payload["dependencies"]["llm"]["reachable"] is False
    assert payload["dependencies"]["langfuse"] == {"enabled": False, "host": ""}
    assert payload["dependencies"]["qdrant"]["reachable"] is True
    assert payload["dependencies"]["checkpointer"]["reachable"] is True


@pytest.mark.asyncio
async def test_health_ai_reports_checkpointer_soft():
    with (
        patch("core.health.settings") as settings,
        patch(
            "core.health._probe_qdrant",
            new_callable=AsyncMock,
            return_value={"reachable": True, "configured": True},
        ),
        patch(
            "core.health._probe_llm",
            new_callable=AsyncMock,
            return_value={"reachable": True, "configured": True, "model": "x"},
        ),
        patch(
            "core.health._probe_checkpointer",
            return_value={
                "reachable": False,
                "configured": True,
                "detail": "not initialized",
            },
        ),
    ):
        settings.qdrant_enabled = True
        payload = await ai_health()

    assert payload["status"] == "degraded"
    assert payload["dependencies"]["checkpointer"]["reachable"] is False
    assert payload["dependencies"]["llm"]["reachable"] is True


@pytest.mark.asyncio
async def test_health_ai_langfuse_enabled_does_not_change_status():
    with (
        patch("core.health.settings") as settings,
        patch(
            "core.health._probe_qdrant",
            new_callable=AsyncMock,
            return_value={"reachable": True, "configured": True},
        ),
        patch(
            "core.health._probe_llm",
            new_callable=AsyncMock,
            return_value={"reachable": True, "configured": True, "model": "x"},
        ),
        patch(
            "core.health._probe_checkpointer",
            return_value={"reachable": True, "configured": True},
        ),
    ):
        settings.qdrant_enabled = True
        settings.langfuse_enabled = True
        settings.effective_langfuse_host = "https://cloud.langfuse.com"
        payload = await ai_health()

    assert payload["status"] == "ok"
    langfuse = payload["dependencies"]["langfuse"]
    assert langfuse["enabled"] is True
    assert langfuse["host"] == "https://cloud.langfuse.com"
    assert "pk-lf" not in str(langfuse)
    assert "sk-lf" not in str(langfuse)


@pytest.mark.asyncio
async def test_hard_health_ignores_langfuse():
    db = AsyncMock()
    redis = AsyncMock()
    response = Response()
    with (
        patch("core.health._redis_expected", return_value=True),
        patch("core.health.check_database", new_callable=AsyncMock),
        patch("core.health.check_redis", new_callable=AsyncMock),
        patch("core.health.settings") as settings,
    ):
        settings.langfuse_enabled = False
        payload = await deep_health(response=response, db=db, redis=redis)

    assert payload["status"] == "ok"
    assert "langfuse" not in payload["dependencies"]


@pytest.mark.asyncio
async def test_probe_llm_splits_configured_and_cached_model():
    with (
        patch("core.health.settings") as settings,
        patch(
            "shared.llm.fallback.resolve_llm_model",
            new_callable=AsyncMock,
            return_value="nvidia_nim/openai/gpt-oss-20b",
        ),
        patch(
            "shared.llm.fallback.cached_llm_model",
            return_value="nvidia_nim/openai/gpt-oss-20b",
        ),
    ):
        settings.ai_enabled = True
        settings.LLM_MODEL = "gemini/gemini-2.5-flash"
        payload = await _probe_llm()

    assert payload["model"] == "nvidia_nim/openai/gpt-oss-20b"
    assert payload["configured_model"] == "gemini/gemini-2.5-flash"
    assert payload["cached_model"] == "nvidia_nim/openai/gpt-oss-20b"


@pytest.mark.asyncio
async def test_probe_llm_cached_model_null_when_unset():
    with (
        patch("core.health.settings") as settings,
        patch(
            "shared.llm.fallback.resolve_llm_model",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch("shared.llm.fallback.cached_llm_model", return_value=None),
    ):
        settings.ai_enabled = True
        settings.LLM_MODEL = "gemini/gemini-2.5-flash"
        payload = await _probe_llm()

    assert payload["reachable"] is False
    assert payload["configured_model"] == "gemini/gemini-2.5-flash"
    assert payload["cached_model"] is None
    assert "model" not in payload
