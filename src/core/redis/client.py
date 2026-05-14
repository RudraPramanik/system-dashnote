from __future__ import annotations

from redis.asyncio import Redis

from config import settings

_shared_redis: Redis | None = None


def get_async_redis() -> Redis | None:
    """
    Lazily construct a single decode_responses async Redis client for the process.

    Returns None when Redis is disabled or REDIS_URL is unset (callers use no-op paths).
    """

    global _shared_redis
    if not (settings.REDIS_ENABLED and settings.REDIS_URL):
        return None
    if _shared_redis is None:
        _shared_redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _shared_redis


def reset_async_redis_client() -> None:
    """
    Drop the shared client reference (used by tests). Does not await close();
    the event loop teardown drops connections for typical pytest runs.
    """

    global _shared_redis
    _shared_redis = None
    # Token store holds the same pooled client when Redis auth is enabled; clear it too.
    from core.redis.redis import reset_token_store_singleton

    reset_token_store_singleton()
