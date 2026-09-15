"""Quality counters plus existing HTTP instrumentator metric names."""
from __future__ import annotations

from pathlib import Path

import pytest
from prometheus_client import REGISTRY, generate_latest

from observability.metrics import (
    inc_agent_interrupt,
    inc_empty_retrieval,
    inc_llm_fallback,
)

_REPO = Path(__file__).resolve().parents[2]


def test_quality_counters_have_stable_names() -> None:
    inc_empty_retrieval()
    inc_agent_interrupt()
    inc_llm_fallback()
    body = generate_latest(REGISTRY).decode("utf-8")
    assert "dashnote_ai_empty_retrieval_total" in body
    assert "dashnote_ai_agent_interrupt_total" in body
    assert "dashnote_ai_llm_fallback_total" in body
    assert "user_id" not in body.split("dashnote_ai_empty_retrieval_total")[1][:200]


def test_create_app_still_exposes_http_instrumentator_metrics() -> None:
    from main import create_app

    app = create_app()
    names = {route.path for route in app.routes}
    assert "/metrics" in names
    src = (_REPO / "src" / "main.py").read_text(encoding="utf-8")
    assert "dashnote" in src
    assert 'metric_subsystem="api"' in src
    assert 'endpoint="/metrics"' in src


@pytest.mark.asyncio
async def test_metrics_scrape_includes_http_and_quality_series() -> None:
    from httpx import ASGITransport, AsyncClient

    from main import create_app

    inc_empty_retrieval()
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/metrics")
    assert res.status_code == 200
    assert "dashnote_ai_empty_retrieval_total" in res.text
    assert "dashnote_api_http_requests_total" in res.text
