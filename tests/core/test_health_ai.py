"""Hard /health must not depend on LLM; /health/ai reports llm softly."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import Response

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from core.health import ai_health, deep_health


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
    ):
        settings.qdrant_enabled = True
        payload = await ai_health()

    assert payload["status"] == "degraded"
    assert payload["dependencies"]["llm"]["reachable"] is False
    assert payload["dependencies"]["qdrant"]["reachable"] is True
