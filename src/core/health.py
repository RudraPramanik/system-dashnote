"""
Deep health checks: minimal round-trips (SELECT 1, Redis PING) for orchestration probes.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Response, status
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from core.database.session import get_db
from core.redis.deps import get_redis

router = APIRouter(tags=["health"])


async def check_database(db: AsyncSession) -> None:
    await db.execute(text("SELECT 1"))


async def check_redis(redis: Redis) -> None:
    await redis.ping()


def _redis_expected() -> bool:
    return bool(settings.REDIS_ENABLED and settings.REDIS_URL)


@router.get("/health")
async def deep_health(
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: Redis | None = Depends(get_redis),
) -> dict[str, Any]:
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
