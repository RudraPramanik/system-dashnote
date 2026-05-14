"""Unit tests for `core.security.rate_limit.RateLimiter` (fixed window + Redis)."""

from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException, Request
from starlette.datastructures import Headers

from core.security.context import RequestContext
from core.security.rate_limit import RateLimiter, build_rate_limit_identity


def _request_with_client(host: str) -> Request:
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "path": "/",
        "raw_path": b"/",
        "root_path": "",
        "scheme": "http",
        "query_string": b"",
        "headers": Headers({}).raw,
        "client": (host, 12345),
        "server": ("testserver", 80),
        "state": {},
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_rate_limiter_allows_within_limit() -> None:
    redis = AsyncMock()
    redis.incr = AsyncMock(return_value=1)
    redis.expire = AsyncMock(return_value=True)
    lim = RateLimiter(scope="t", limit=5, window_seconds=60)
    req = _request_with_client("203.0.113.7")
    await lim.check(redis, req, None)
    redis.incr.assert_awaited_once()
    redis.expire.assert_awaited_once()


@pytest.mark.asyncio
async def test_rate_limiter_raises_429_with_retry_after() -> None:
    redis = AsyncMock()
    redis.incr = AsyncMock(return_value=6)
    redis.expire = AsyncMock(return_value=True)
    redis.ttl = AsyncMock(return_value=31)
    lim = RateLimiter(scope="t", limit=5, window_seconds=60)
    req = _request_with_client("203.0.113.7")
    with pytest.raises(HTTPException) as exc_info:
        await lim.check(redis, req, None)
    assert exc_info.value.status_code == 429
    assert exc_info.value.headers is not None
    assert exc_info.value.headers.get("Retry-After") == "31"


@pytest.mark.asyncio
async def test_rate_limiter_skips_when_redis_disabled() -> None:
    lim = RateLimiter(scope="t", limit=1, window_seconds=60)
    req = _request_with_client("127.0.0.1")
    await lim.check(None, req, None)


def test_build_rate_limit_identity_prefers_user_id() -> None:
    req = _request_with_client("127.0.0.1")
    ctx = RequestContext(user_id=42, workspace_id=9, role="member")
    assert build_rate_limit_identity(ctx, req) == "42"


def test_build_rate_limit_identity_falls_back_to_ip() -> None:
    req = _request_with_client("198.51.100.2")
    assert build_rate_limit_identity(None, req) == "198.51.100.2"
