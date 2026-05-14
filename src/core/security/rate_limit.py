"""
Application-level fixed-window rate limiting backed by Redis.

Keys extend `rate_limit:{scope}:{identity}` with a window bucket suffix so counts
reset on fixed boundaries without SCAN.
"""

from __future__ import annotations

import time
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from redis.asyncio import Redis

from core.redis.deps import get_redis_connection
from core.security.context import RequestContext
from core.security.dependency import get_optional_current_context


def _client_host(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def build_rate_limit_identity(ctx: RequestContext | None, request: Request) -> str:
    """
    Redis identity segment: authenticated requests use `user_id`; otherwise client IP.

    Shaped to fit `rate_limit:{scope}:{user_id|ip}:...` (window suffix added by `RateLimiter`).
    """

    if ctx is not None:
        return str(ctx.user_id)
    return _client_host(request)


class RateLimiter:
    """Fixed-window counter per scope + identity using Redis INCR + TTL."""

    def __init__(self, *, scope: str, limit: int, window_seconds: int) -> None:
        self.scope = scope
        self.limit = limit
        self.window_seconds = window_seconds

    def _window_index(self) -> int:
        return int(time.time()) // self.window_seconds

    def _redis_key(self, identity: str) -> str:
        return f"rate_limit:{self.scope}:{identity}:{self._window_index()}"

    async def check(
        self,
        redis: Redis | None,
        request: Request,
        ctx: RequestContext | None,
    ) -> None:
        if redis is None:
            return

        identity = build_rate_limit_identity(ctx, request)
        key = self._redis_key(identity)
        current = await redis.incr(key)
        if current == 1:
            await redis.expire(key, self.window_seconds * 2)

        if current > self.limit:
            ttl = await redis.ttl(key)
            retry_after = (
                max(1, ttl) if ttl is not None and ttl > 0 else self.window_seconds
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={"Retry-After": str(retry_after)},
            )


_global_limiter = RateLimiter(scope="global", limit=100, window_seconds=60)
_auth_login_limiter = RateLimiter(scope="auth_login", limit=5, window_seconds=60)


async def enforce_global_rate_limit(
    request: Request,
    ctx: Annotated[RequestContext | None, Depends(get_optional_current_context)],
    redis: Annotated[Redis | None, Depends(get_redis_connection)],
) -> None:
    await _global_limiter.check(redis, request, ctx)


async def enforce_auth_login_rate_limit(
    request: Request,
    ctx: Annotated[RequestContext | None, Depends(get_optional_current_context)],
    redis: Annotated[Redis | None, Depends(get_redis_connection)],
) -> None:
    await _auth_login_limiter.check(redis, request, ctx)
