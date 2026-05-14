from __future__ import annotations

from redis.asyncio import Redis

from core.redis.client import get_async_redis


class BaseTokenStore:
    async def is_access_token_blacklisted(self, *, jti: str) -> bool:
        return False

    async def blacklist_access_token(self, *, jti: str, ttl_seconds: int) -> None:
        return None

    async def store_refresh_token(self, *, user_id: int, jti: str, ttl_seconds: int) -> None:
        return None

    async def is_refresh_token_active(self, *, user_id: int, jti: str) -> bool:
        return True

    async def revoke_refresh_token(self, *, user_id: int, jti: str) -> None:
        return None


class RedisTokenStore(BaseTokenStore):
    def __init__(self, client: Redis):
        self.client = client

    @staticmethod
    def _access_key(jti: str) -> str:
        return f"auth:access:blacklist:{jti}"

    @staticmethod
    def _refresh_key(user_id: int, jti: str) -> str:
        return f"auth:refresh:{user_id}:{jti}"

    async def is_access_token_blacklisted(self, *, jti: str) -> bool:
        return bool(await self.client.exists(self._access_key(jti)))

    async def blacklist_access_token(self, *, jti: str, ttl_seconds: int) -> None:
        await self.client.setex(self._access_key(jti), max(1, ttl_seconds), "1")

    async def store_refresh_token(self, *, user_id: int, jti: str, ttl_seconds: int) -> None:
        await self.client.setex(self._refresh_key(user_id, jti), max(1, ttl_seconds), "1")

    async def is_refresh_token_active(self, *, user_id: int, jti: str) -> bool:
        return bool(await self.client.exists(self._refresh_key(user_id, jti)))

    async def revoke_refresh_token(self, *, user_id: int, jti: str) -> None:
        await self.client.delete(self._refresh_key(user_id, jti))


_token_store: BaseTokenStore | None = None


def reset_token_store_singleton() -> None:
    global _token_store
    _token_store = None


def get_token_store() -> BaseTokenStore:
    global _token_store
    if _token_store is not None:
        return _token_store

    client = get_async_redis()
    if client is not None:
        _token_store = RedisTokenStore(client)
    else:
        _token_store = BaseTokenStore()
    return _token_store