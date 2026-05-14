redis--1:Here is what was implemented.

Redis configuration and architecture
Shared client (src/core/redis/client.py): get_async_redis() builds a single decode_responses async Redis client when REDIS_ENABLED and REDIS_URL are set. reset_async_redis_client() clears it and resets the JWT token store singleton (used from tests/conftest.py after each test).

Token store (src/core/redis/redis.py): RedisTokenStore now takes that shared client instead of opening its own pool from the URL.

Cache-aside + tenant scope (src/core/redis/cache.py): WorkspaceRedisCache builds keys under app:cache:w:{workspace_id}:…, uses a staff vs u{user_id} segment for note lists (so member views cannot cross users), and uses read_generation / bump_generation (app:cache:gen:{domain}:{workspace_id} with INCR) so invalidation does not need SCAN.

“Invisible” / composed DI (src/core/redis/deps.py): get_workspace_cache = Depends(get_current_context) + Depends(get_redis_connection) so routers only add one extra parameter; when Redis is off, redis=None and the helper is a no-op (always miss, bumps ignored).

Routers: notes/router.py caches GET /notes, GET /notes/{note_id} and bumps notes generation on create/update/delete. notebooks/router.py caches GET /notebooks/ and bumps notebooks on create.

Permissions (src/notes/permissions.py): can_view_note_fields() centralizes visibility for both ORM notes and cached dicts before returning a cached GET /notes/{id}.

Settings (src/config.py): CACHE_TTL_SECONDS (default 60) for SETEX on cached JSON.

Tests: tests/core/test_workspace_redis_cache.py (aside hit, generation bump, disabled Redis, key isolation). pytest (with requirements/base.txt installed): 7 passed including notes, notebooks, and auth token tests.

Docs: src/docs/system.md (Redis section + Compose blurb), src/docs/lld.md (request flow, new §4.2 core.redis, renumbered modules, matrix, testing line), and a short auth.md pointer to the shared client.

core/redis/__init__.py no longer imports deps so from core.redis.cache import … in tests does not pull FastAPI/jose during collection.

Configure in .env: REDIS_URL=redis://... (Compose already sets REDIS_URL for the API). Optional: CACHE_TTL_SECONDS. With Redis off or URL unset, behavior matches the previous non-cached API paths