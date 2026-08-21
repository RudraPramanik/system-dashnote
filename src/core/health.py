
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Response, status
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from core.database.session import get_db
from core.redis.deps import get_redis

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


async def check_database(db: AsyncSession) -> None:
    await db.execute(text("SELECT 1"))


async def check_redis(redis: Redis) -> None:
    await redis.ping()


def _redis_expected() -> bool:
    return bool(settings.REDIS_ENABLED and settings.REDIS_URL)


async def _probe_qdrant() -> dict[str, Any]:
    """Soft Qdrant probe via REST (no ai.retrieval client — keeps hard /health isolated)."""
    url = (settings.QDRANT_URL or "").rstrip("/")
    if not url:
        return {"reachable": False, "configured": False, "detail": "QDRANT_URL not set"}

    headers: dict[str, str] = {}
    api_key = (settings.QDRANT_API_KEY or "").strip()
    if api_key and api_key != "...":
        headers["api-key"] = api_key

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{url}/collections", headers=headers)
        if resp.status_code < 400:
            return {"reachable": True, "configured": True, "http_status": resp.status_code}
        return {
            "reachable": False,
            "configured": True,
            "http_status": resp.status_code,
            "detail": resp.text[:200],
        }
    except Exception as exc:
        logger.warning("Qdrant soft health probe failed: %s", exc)
        return {"reachable": False, "configured": True, "detail": str(exc)[:200]}


async def _probe_llm() -> dict[str, Any]:
    """Soft LLM probe — never raises; never logs secrets."""
    if not settings.ai_enabled:
        return {"reachable": False, "configured": False}

    try:
        from shared.llm.fallback import resolve_llm_model

        model = await asyncio.wait_for(resolve_llm_model(timeout=12.0), timeout=14.0)
        if model:
            return {"reachable": True, "configured": True, "model": model}
        return {"reachable": False, "configured": True}
    except Exception as exc:
        logger.warning("LLM soft health probe failed: %s", str(exc)[:200])
        return {"reachable": False, "configured": True, "detail": str(exc)[:200]}


@router.get("/health")
async def deep_health(
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: Redis | None = Depends(get_redis),
) -> dict[str, Any]:
    """Hard readiness: Postgres + Redis only. Qdrant/LLM never affect this gate."""
    t0 = time.perf_counter()
    dependencies: dict[str, dict[str, Any]] = {"database": {"reachable": False}}

    try:
        await check_database(db)
        dependencies["database"]["reachable"] = True
    except Exception:
        dependencies["database"]["reachable"] = False

    if not _redis_expected():
        dependencies["redis"] = {"reachable": True, "configured": False}
    elif redis is None:
        dependencies["redis"] = {"reachable": False, "configured": True}
    else:
        dependencies["redis"] = {"reachable": False, "configured": True}
        try:
            await check_redis(redis)
            dependencies["redis"]["reachable"] = True
        except Exception:
            dependencies["redis"]["reachable"] = False

    latency_ms = round((time.perf_counter() - t0) * 1000, 3)
    ts = datetime.now(timezone.utc).isoformat()

    all_ok = all(d.get("reachable", False) for d in dependencies.values())
    if not all_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ok" if all_ok else "unavailable",
        "timestamp": ts,
        "latency_ms": latency_ms,
        "dependencies": dependencies,
    }


@router.get("/health/ai")
async def ai_health() -> dict[str, Any]:
    """Soft AI/Qdrant/LLM readiness. Never required by hard deploy smoke or GET /health."""
    t0 = time.perf_counter()
    ts = datetime.now(timezone.utc).isoformat()
    llm = await _probe_llm()

    if not settings.qdrant_enabled:
        llm_ok = bool(llm.get("reachable"))
        return {
            "status": "ok" if llm_ok else "degraded",
            "timestamp": ts,
            "latency_ms": round((time.perf_counter() - t0) * 1000, 3),
            "dependencies": {
                "qdrant": {"reachable": False, "configured": False},
                "llm": llm,
            },
        }

    qdrant = await _probe_qdrant()
    qdrant_ok = bool(qdrant.get("reachable"))
    llm_ok = bool(llm.get("reachable"))
    status_label = "ok" if qdrant_ok and llm_ok else "degraded"
    return {
        "status": status_label,
        "timestamp": ts,
        "latency_ms": round((time.perf_counter() - t0) * 1000, 3),
        "dependencies": {"qdrant": qdrant, "llm": llm},
    }
