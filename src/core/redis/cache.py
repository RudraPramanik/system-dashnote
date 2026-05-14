from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from redis.asyncio import Redis

from core.security.context import RequestContext

T = TypeVar("T")


class WorkspaceRedisCache:
    """
    Tenant-scoped cache-aside helper: every key is rooted at workspace_id from RequestContext.

    Invalidation uses a monotonic per-workspace generation counter (INCR) so list/detail
    keys do not require SCAN. When Redis is unavailable, reads always miss and writes are no-ops.
    """

    __slots__ = ("_ctx", "_redis", "_default_ttl")

    def __init__(
        self,
        *,
        ctx: RequestContext,
        redis: Redis | None,
        default_ttl_seconds: int,
    ) -> None:
        self._ctx = ctx
        self._redis = redis
        self._default_ttl = max(1, default_ttl_seconds)

    @property
    def enabled(self) -> bool:
        return self._redis is not None

    def notes_list_variant(self) -> str:
        if self._ctx.role in {"owner", "admin"}:
            return "staff"
        return f"u{self._ctx.user_id}"

    def key_notes_list(self, generation: str) -> str:
        return (
            f"app:cache:w:{self._ctx.workspace_id}:notes:list:{generation}:{self.notes_list_variant()}"
        )

    def key_note_detail(self, generation: str, note_id: int) -> str:
        return (
            f"app:cache:w:{self._ctx.workspace_id}:notes:one:{generation}:"
            f"u{self._ctx.user_id}:n{note_id}"
        )

    def key_notebooks_list(self, generation: str) -> str:
        return f"app:cache:w:{self._ctx.workspace_id}:notebooks:list:{generation}"

    def _gen_key(self, domain: str) -> str:
        return f"app:cache:gen:{domain}:{self._ctx.workspace_id}"

    async def read_generation(self, domain: str) -> str:
        if not self._redis:
            return "0"
        raw = await self._redis.get(self._gen_key(domain))
        return raw if raw is not None else "0"

    async def bump_generation(self, domain: str) -> None:
        if self._redis:
            await self._redis.incr(self._gen_key(domain))

    async def get_json(self, key: str) -> Any | None:
        if not self._redis:
            return None
        raw = await self._redis.get(key)
        if raw is None:
            return None
        return json.loads(raw)

    async def set_json(self, key: str, value: Any, *, ttl_seconds: int | None = None) -> None:
        if not self._redis:
            return
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        await self._redis.setex(key, max(1, ttl), json.dumps(value))

    async def aside_json(
        self,
        key: str,
        loader: Callable[[], Awaitable[T]],
        *,
        ttl_seconds: int | None = None,
    ) -> T:
        cached = await self.get_json(key)
        if cached is not None:
            return cached  # type: ignore[return-value]
        value = await loader()
        await self.set_json(key, value, ttl_seconds=ttl_seconds)
        return value
