"""
Redis-backed dependencies.

`get_workspace_cache` composes `RequestContext` with the shared async Redis client so routers
can opt in to tenant-scoped cache-aside without changing global security wiring.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis

from config import settings
from core.redis.cache import WorkspaceRedisCache
from core.redis.client import get_async_redis
from core.security.context import RequestContext
from core.security.dependency import get_current_context


async def get_redis_connection() -> Redis | None:
    return get_async_redis()


get_redis = get_redis_connection


async def get_workspace_cache(
    ctx: Annotated[RequestContext, Depends(get_current_context)],
    redis: Annotated[Redis | None, Depends(get_redis_connection)],
) -> WorkspaceRedisCache:
    return WorkspaceRedisCache(
        ctx=ctx,
        redis=redis,
        default_ttl_seconds=settings.CACHE_TTL_SECONDS,
    )
