import pytest

from core.redis.cache import WorkspaceRedisCache
from core.security.context import RequestContext


class _FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def setex(self, key: str, ttl: int, value: str) -> None:
        self.store[key] = value

    async def incr(self, key: str) -> int:
        cur = int(self.store.get(key, "0"))
        nxt = cur + 1
        self.store[key] = str(nxt)
        return nxt


@pytest.mark.asyncio
async def test_cache_aside_second_hit_skips_loader() -> None:
    ctx = RequestContext(user_id=1, workspace_id=10, role="owner")
    fake = _FakeRedis()
    cache = WorkspaceRedisCache(ctx=ctx, redis=fake, default_ttl_seconds=30)
    gen = await cache.read_generation("notes")
    key = cache.key_notes_list(gen)
    calls = {"n": 0}

    async def loader() -> list[dict]:
        calls["n"] += 1
        return [
            {
                "id": 1,
                "title": "a",
                "content": "c",
                "is_private": False,
                "created_by": 1,
            }
        ]

    first = await cache.aside_json(key, loader)
    second = await cache.aside_json(key, loader)
    assert calls["n"] == 1
    assert first == second


@pytest.mark.asyncio
async def test_generation_bump_changes_list_key() -> None:
    ctx = RequestContext(user_id=2, workspace_id=7, role="member")
    fake = _FakeRedis()
    cache = WorkspaceRedisCache(ctx=ctx, redis=fake, default_ttl_seconds=30)
    gen0 = await cache.read_generation("notes")
    key0 = cache.key_notes_list(gen0)
    calls = {"n": 0}

    async def loader() -> list[dict]:
        calls["n"] += 1
        return []

    await cache.aside_json(key0, loader)
    assert calls["n"] == 1

    await cache.bump_generation("notes")
    gen1 = await cache.read_generation("notes")
    assert gen1 != gen0
    key1 = cache.key_notes_list(gen1)
    assert key0 != key1

    await cache.aside_json(key1, loader)
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_disabled_redis_does_not_cache() -> None:
    ctx = RequestContext(user_id=1, workspace_id=1, role="owner")
    cache = WorkspaceRedisCache(ctx=ctx, redis=None, default_ttl_seconds=30)
    key = cache.key_notes_list("0")
    calls = {"n": 0}

    async def loader() -> list[str]:
        calls["n"] += 1
        return ["x"]

    await cache.aside_json(key, loader)
    await cache.aside_json(key, loader)
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_staff_and_member_list_keys_differ() -> None:
    owner_ctx = RequestContext(user_id=1, workspace_id=3, role="owner")
    member_ctx = RequestContext(user_id=9, workspace_id=3, role="member")
    fake = _FakeRedis()
    c_owner = WorkspaceRedisCache(ctx=owner_ctx, redis=fake, default_ttl_seconds=10)
    c_member = WorkspaceRedisCache(ctx=member_ctx, redis=fake, default_ttl_seconds=10)
    assert c_owner.key_notes_list("0") != c_member.key_notes_list("0")
