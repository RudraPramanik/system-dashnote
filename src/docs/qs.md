# DashNoteSystem — architecture & development Q&A

Short answers tied to how this repository is built today. For deeper flow diagrams and module contracts, see `system.md` and `lld.md`.

---

### Why centralize JWT handling in `core/security/dependency.py` instead of decoding in each router?

So every protected route shares one claim contract (`sub`, `wid`, `role`, `typ`, `jti`) and one revocation path (access blacklist via `get_token_store()`). Routers stay thin and cannot drift to different validation rules or forget blacklist checks.

---

### Why does `TenantRepository` take `workspace_id` in the constructor rather than passing it on every method?

Tenant scope becomes a type-level and construction-time guarantee: once built, the repository cannot accidentally query another workspace without constructing a new instance. That matches how routers derive `workspace_id` exclusively from `RequestContext` (JWT `wid`), which keeps cross-tenant mistakes harder to introduce than a per-call integer parameter.

---

### Why a `StorageBackend` protocol and `get_storage()` factory instead of calling boto3 or the filesystem directly from routers?

Upload, download, delete, and presigned URLs differ across local disk, MinIO, and R2, but the `files` module should not care which backend is active. A single protocol keeps routers and services stable while `STORAGE_BACKEND` and related settings choose the implementation at runtime, which is easier to test with mocks and to change per environment.

---

### Why is Redis optional (`REDIS_URL` / `REDIS_ENABLED`) if features like refresh rotation and cache-aside assume it?

The app is designed to boot and serve core CRUD paths without Redis: token store and cache helpers degrade to no-op or “always miss” behavior so local setups and tests do not require another service. When Redis is configured, you get refresh tracking, logout blacklist, read-through cache, and application rate limits.

---

### Why does application rate limiting skip enforcement when Redis is unavailable (“fail open”) instead of rejecting every request?

Blocking all traffic when Redis is down would make outages worse than abuse risk for many small deployments and for pytest runs that do not start Redis. The trade-off is documented: limits apply only when `get_redis_connection()` returns a client; Nginx edge `limit_req` still applies when you use the Compose Nginx path on port 80.

---

### Why fixed-window counters (`INCR` + `EXPIRE` with a time bucket in the key) for app rate limits instead of a sliding window?

Fixed windows need only a few Redis commands per request, are easy to reason about, and align with common “N requests per minute” product language. Sliding-window precision usually costs more Redis round-trips or Lua. Here the key includes a window index so resets do not require scanning keys.

---

### Why both Nginx `limit_req` and FastAPI/Redis limits?

They solve different problems: Nginx caps raw connection/request rate per IP before Python runs, which protects CPU and connection pools from floods. The app layer can key by authenticated `user_id` when a bearer token is present (via the same decode path as `get_current_context`) or by client IP for anonymous routes, so limits follow identity rather than only the edge IP (which matters behind shared NATs).

---

### Why generation counters (`INCR` on `app:cache:gen:{domain}:{workspace_id}`) for cache invalidation instead of publishing events or deleting keys by pattern?

Redis `SCAN` or wildcard deletes are slow and risky at scale. Bumping a small integer invalidates every list/detail key that embeds the current generation in its name, without listing keys. Pub/sub would require subscribers and still leave stale entries if a message is missed; generations plus TTL give a simple correctness story: miss after bump, bounded staleness if a bump fails.

---

### Why does the notes list cache use a `staff` vs `u{user_id}` key variant?

Owner and admin see a different effective list than a member (RBAC and visibility rules differ). Encoding the viewer role class in the key prevents serving a staff-shaped list to a member or mixing member-specific visible sets across users within the same workspace.

---

### Why `get_optional_current_context` for rate limiting instead of requiring `get_current_context` on every route?

Public routes (`POST /auth/login`, `POST /auth/register`, `GET /health`) have no access token. Optional bearer decoding reuses `_context_from_access_token` when a token exists so authenticated traffic is keyed by user, while anonymous traffic falls back to IP after `ProxyHeadersMiddleware`.

---

### Why `expire_on_commit=False` on the async sessionmaker?

After `commit()`, ORM instances attached to the session remain usable for building response DTOs without immediate refresh or re-query in many router paths. The trade-off is remembering that data can be slightly stale relative to the database until you explicitly refresh or load again, which matches typical FastAPI “commit then return” flows in this codebase.

---

### How does a request’s database session relate to concurrency between users?

Each request gets its own `AsyncSession` from `get_session()` (generator dependency). Sessions are not shared across concurrent requests, so transactions from different users do not interleave in the same session object. Throughput still depends on the async engine pool size and how long handlers hold the session open; keeping routers thin and avoiding unnecessary work before commit reduces contention on pool checkout.

---

### Why keep permission helpers (for example `notes/permissions.py`, `files/permissions.py`) separate from `require_roles`?

`require_roles` answers “is this role allowed on this route?” Entity-level rules depend on `created_by`, `is_private`, and note–file visibility. Splitting coarse route RBAC from per-resource checks keeps repositories focused on SQL and routers on orchestration, and tests can target permission logic without spinning up full HTTP stacks where not needed.

---

### Why does `docker-compose.yml` expose both Nginx on port 80 and the API on port 8000?

Port 80 matches the production-style path: edge rate limit, proxy headers, and a single public entry. Port 8000 is a developer convenience for hitting Uvicorn directly (Swagger UI, quick curls) without reproxying; application rate limits still run when Redis is configured, but Nginx’s `limit_req` does not apply on that path.

---

### When adding a new tenant-scoped module, what is the minimum contract to stay consistent with the rest of the repo?

Add `workspace_id` on the model (typically via `WorkspaceTenantMixin`), scope queries with `tenant_filter` (or a `TenantRepository` subclass that always applies it), resolve `RequestContext` from JWT in the router, and use domain permission helpers if rules go beyond role names. Register the router in `main.py` and extend tests for tenant isolation and RBAC the way existing `notes` and `files` tests do.
