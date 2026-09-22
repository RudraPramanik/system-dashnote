from __future__ import annotations

from redis.asyncio import Redis

from core.redis.client import get_async_redis


def _as_str(value: bytes | str | int) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


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

    async def revoke_all_refresh_tokens(self, *, user_id: int) -> None:
        return None

    async def store_password_reset_token(
        self, *, user_id: int, digest: str, ttl_seconds: int
    ) -> bool:
        return False

    async def consume_password_reset_token(self, *, digest: str) -> int | None:
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

    @staticmethod
    def _refresh_index_key(user_id: int) -> str:
        return f"auth:refresh:index:{user_id}"

    @staticmethod
    def _reset_key(digest: str) -> str:
        return f"auth:pwdreset:{digest}"

    @staticmethod
    def _reset_user_key(user_id: int) -> str:
        return f"auth:pwdreset:user:{user_id}"

    async def is_access_token_blacklisted(self, *, jti: str) -> bool:
        return bool(await self.client.exists(self._access_key(jti)))

    async def blacklist_access_token(self, *, jti: str, ttl_seconds: int) -> None:
        await self.client.setex(self._access_key(jti), max(1, ttl_seconds), "1")

    async def store_refresh_token(self, *, user_id: int, jti: str, ttl_seconds: int) -> None:
        ttl = max(1, ttl_seconds)
        index_key = self._refresh_index_key(user_id)
        await self.client.setex(self._refresh_key(user_id, jti), ttl, "1")
        await self.client.sadd(index_key, jti)
        remaining = await self.client.ttl(index_key)
        expire_for = ttl
        if isinstance(remaining, int) and remaining > expire_for:
            expire_for = remaining
        await self.client.expire(index_key, expire_for)

    async def is_refresh_token_active(self, *, user_id: int, jti: str) -> bool:
        return bool(await self.client.exists(self._refresh_key(user_id, jti)))

    async def revoke_refresh_token(self, *, user_id: int, jti: str) -> None:
        await self.client.delete(self._refresh_key(user_id, jti))
        await self.client.srem(self._refresh_index_key(user_id), jti)

    async def revoke_all_refresh_tokens(self, *, user_id: int) -> None:
        index_key = self._refresh_index_key(user_id)
        members = await self.client.smembers(index_key)
        for member in members:
            jti = _as_str(member)
            await self.client.delete(self._refresh_key(user_id, jti))
        await self.client.delete(index_key)

    async def store_password_reset_token(
        self, *, user_id: int, digest: str, ttl_seconds: int
    ) -> bool:
        ttl = max(1, ttl_seconds)
        user_key = self._reset_user_key(user_id)
        old = await self.client.get(user_key)
        if old:
            await self.client.delete(self._reset_key(_as_str(old)))
        await self.client.setex(self._reset_key(digest), ttl, str(user_id))
        await self.client.setex(user_key, ttl, digest)
        return True

    async def consume_password_reset_token(self, *, digest: str) -> int | None:
        raw = await self.client.get(self._reset_key(digest))
        if raw is None:
            return None
        user_id = int(_as_str(raw))
        await self.client.delete(self._reset_key(digest))
        pointer = await self.client.get(self._reset_user_key(user_id))
        if pointer is not None and _as_str(pointer) == digest:
            await self.client.delete(self._reset_user_key(user_id))
        return user_id


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
