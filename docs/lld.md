# DashNoteSystem Low-Level Design (LLD)

## 1) Objective and scope
This document defines the implementation-level design for the current backend in `g:\projects\dashnotesystem`, aligned with code that exists today.

In scope:
- Auth + JWT context propagation
- Multi-tenant data access model
- RBAC + domain permissions
- Object storage abstraction (local / S3-compatible backends) and the `files` module
- Implemented modules: `auth`, `workspaces`, `membership`, `notes`, `notebooks`, `files`
- Edge reverse proxy and dual-layer rate limiting (Nginx + Redis-backed FastAPI limits) as implemented in-repo
- Extension contract for upcoming modules (such as `ai_gateway`)

Out of scope:
- Frontend design
- Cloud-specific provisioning beyond the provided `docker-compose.yml`, `Dockerfile.api`, and `nginx/default.conf`
- Non-implemented runtime components (e.g. `Dockerfile.worker` / ARQ worker process until wired in Compose)

## 2) Design principles used

### 2.1 API layer stays thin
Routers only orchestrate:
- input schema validation
- dependency injection (DB, auth context)
- calling service/repository/permission helpers
- mapping models to response schemas

Business logic is kept in services/permission helpers/repositories.

### 2.2 Security and tenant context are explicit
Every protected request derives a single `RequestContext` from JWT:
- `user_id` (`sub`)
- `workspace_id` (`wid`)
- `role`

No protected module should decode JWT by itself.

### 2.3 Tenant safety by construction
Tenant-aware repositories inherit from `TenantRepository(session, workspace_id)` and enforce workspace scoping via `tenant_filter(...)`.

### 2.4 RBAC is layered
- Coarse route-level role checks: `require_roles(...)`
- Fine-grained entity checks: domain permission helpers (example: `notes/permissions.py`)

### 2.5 Backward-compatible tenancy naming
`tenant_filter` supports both `workspace_id` and `tenant_id`, allowing gradual model migration while preserving query safety.

### 2.6 Binary assets use storage backends, not SQL blobs
File bytes live in a `StorageBackend` implementation (`core/storage/client.py`: local disk, MinIO, or R2). SQL stores metadata, `storage_key`, and tenant/RBAC columns so repositories can enforce `workspace_id` the same way as notes.

## 3) Runtime architecture

### 3.1 Entry point and composition
`src/main.py` creates the FastAPI app and registers:
- `ProxyHeadersMiddleware` (Uvicorn) so `request.client` reflects the proxied client when `X-Forwarded-For` is trusted.
- CORS middleware
- **Global application rate limit** dependency (`enforce_global_rate_limit`): Redis fixed-window counter per `user_id` (from JWT when present) or client IP; skipped when Redis is unavailable.
- module routers
- global exception handler

Registered routers:
- `core.health` → `GET /health` (deep probe: `SELECT 1`, Redis `PING` when Redis is configured; **503** if a required dependency fails)
- `/auth`
- `/files`
- `/notebooks`
- `/notes`
- `/workspaces`
- `/workspaces/members`

### 3.2 Request flow (protected endpoint)
1. When behind Nginx, the edge sets `X-Forwarded-For` / `X-Real-IP`; `ProxyHeadersMiddleware` adjusts ASGI `client` so downstream code (including rate limiting) sees the original host.
2. Global rate limit dependency runs (Redis `INCR` on a fixed-window key before route handlers).
3. Client sends `Authorization: Bearer <token>`.
4. `oauth2_scheme` extracts the token.
5. `get_current_context` validates JWT and builds `RequestContext` (including optional Redis access-token blacklist check via `get_token_store()`).
6. Optional: routers that support read caching also resolve `WorkspaceRedisCache` via `get_workspace_cache` (nested `Depends(get_current_context)` + shared Redis client from `get_async_redis()`).
7. Router instantiates repository with `ctx.workspace_id` where tenant-scoped.
8. Permission checks run (`require_roles` and/or domain helper).
9. Repository executes async SQLAlchemy query (on cache miss for cached routes).
10. Router returns Pydantic schema.

### 3.3 Deployable units (modular monolith layout)
The repository separates **HTTP**, **AI orchestration**, **background work**, and **shared contracts** into top-level packages. Only a subset is copied into each container image.

| Package / path | API image (`Dockerfile.api`) | Worker image (planned) | Notes |
|----------------|------------------------------|-------------------------|--------|
| `src/` | yes | via shared deps / config only | FastAPI routers, DB, storage clients, `src/config.py` |
| `ai/` | yes | yes (planned) | Orchestration helpers for embeddings/indexing — no FastAPI imports in `ai/` |
| `shared/` | yes | yes (planned) | Pydantic contracts and events; stdlib + pydantic only |
| `worker/` | no | yes (planned) | ARQ jobs: parse, chunk, embed, index; may import `ai/`, `shared/`, `src/config/` only |

**API container build (`Dockerfile.api`)**
- Dependencies: `pip install -r requirements.api.txt` (see file header — excludes torch, transformers, `pypdf`, `python-docx`, `unstructured`, full `langchain` meta-package).
- Files copied: `src/`, `ai/`, `shared/` only (no `worker/`, no wildcard `COPY . .`).
- Runtime: `PYTHONPATH=/app/src:/app/ai:/app/shared`; process runs as non-root `appuser`.
- Entry: `uvicorn src.main:app` on port **8000** (single worker in the default image CMD).

**Worker container (planned)**
- Will install `requirements.worker.txt` (`-r requirements.api.txt` plus document parsers and `langchain-text-splitters` only).
- Hosted embedding APIs only — no local model weights; sized for ~8GB RAM dev machines.

**Migrations**
- Compose `migrate` service may continue to use the legacy root `Dockerfile` until a dedicated migrate image is introduced; it is not part of the lean API runtime image.

## 4) Module-level low-level design

### 4.1 `auth` module
Responsibilities:
- user registration
- credential validation
- token issuance, refresh rotation, and logout (access blacklist + optional refresh revocation)

Primary flow:
- `POST /auth/register`
  - creates `users`, `workspaces`, `workspace_users`
  - issues access + refresh JWTs with `sub`, `wid`, `role`, `jti`, `typ`
  - when Redis is enabled, stores the refresh token `jti` in Redis for rotation checks
- `POST /auth/login`
  - validates credentials
  - selects first membership as default workspace
  - issues access + refresh JWTs (same Redis refresh tracking when enabled)
  - additionally guarded by **`enforce_auth_login_rate_limit`** (5/min per identity in Redis when configured)
- `POST /auth/refresh`
  - validates refresh JWT; requires active refresh `jti` in Redis when enabled; rotates refresh token
- `POST /auth/logout`
  - blacklists access token `jti` until expiry when Redis is enabled; optionally revokes refresh `jti`

Operational state is delegated to `core/redis/redis.py` (`get_token_store`) using the shared async client from `core/redis/client.py` when `REDIS_URL` is configured (details in `src/docs/auth.md`).

### 4.2 `core.redis` — shared client + tenant cache-aside
Components:
- `core/redis/client.py`: lazy singleton `get_async_redis()`; `reset_async_redis_client()` clears the client and resets the token-store singleton (tests).
- `core/redis/redis.py`: `RedisTokenStore` / `BaseTokenStore` for JWT blacklist + refresh tracking.
- `core/redis/cache.py`: `WorkspaceRedisCache` — tenant-scoped key layout (`workspace_id` prefix), generation counters per domain (`notes`, `notebooks`), JSON cache-aside helpers.
- `core/redis/deps.py`: `get_redis_connection`, `get_workspace_cache` — FastAPI dependencies composing `RequestContext` with Redis (no-op cache when Redis is disabled).

Consumers (read caching):
- `notes/router.py`: `GET /notes` (list), `GET /notes/{id}` (detail after permission); all note mutations `INCR` the workspace notes generation.
- `notebooks/router.py`: `GET /notebooks/`; `POST /notebooks/` bumps workspace notebooks generation.

### 4.3 `core.security` module
Responsibilities:
- auth context extraction from token
- generic role gating
- optional access-token decode for non-auth-gated flows (rate limit identity)

Components:
- `_context_from_access_token` / `get_current_context`: JWT decode -> `RequestContext`
- `get_optional_current_context`: same validation when a bearer token is supplied; otherwise `None` (used by rate limiting without forcing login on public routes)
- `require_roles(*roles)`: dependency factory for 403 enforcement

Failure behavior:
- invalid/missing claims/token -> `401 Invalid or expired token` (strict `get_current_context` path only)
- insufficient role -> `403 Insufficient permissions`

### 4.3a `core.security.rate_limit` — application fixed-window limits
Responsibilities:
- enforce Redis-backed fixed-window quotas per logical **scope** and **identity**
- emit **429** with **`Retry-After`** when a window is exceeded

Components:
- `RateLimiter(scope, limit, window_seconds)`: builds keys `rate_limit:{scope}:{user_id|ip}:{window_index}`, uses `INCR` + `EXPIRE`
- `enforce_global_rate_limit`: FastAPI dependency (wired on the app in `main.py`) — default **100/min** (`scope=global`)
- `enforce_auth_login_rate_limit`: route-level dependency on `POST /auth/login` — **5/min** (`scope=auth_login`)

Identity rules:
- If `get_optional_current_context` returns a `RequestContext`, the identity segment is `str(user_id)` (same JWT semantics as `get_current_context`).
- Otherwise the identity segment is the client IP string from `Request.client` (after `ProxyHeadersMiddleware`).

Operational notes:
- When `get_redis_connection` yields `None`, checks are skipped (no Redis URL / disabled Redis) so unit tests and minimal dev setups keep working.

### 4.4 `workspaces` module
Responsibilities:
- retrieve current workspace
- rename workspace

Endpoints:
- `GET /workspaces/me`: authenticated user
- `PATCH /workspaces/me`: owner/admin only

Design note:
- workspace identity is always taken from JWT `wid` through context.

### 4.5 `membership` module
Responsibilities:
- list members
- invite member
- update member role
- remove member

Key rules in service layer:
- valid roles: `owner`, `admin`, `member`
- cannot invite `owner`
- admin cannot invite admin
- only owner can change roles
- admin cannot remove owner/admin
- user cannot remove self

Storage model:
- joins `workspace_users` with `users` for member listing.

### 4.6 `notes` module
Responsibilities:
- CRUD notes within workspace
- visibility and ownership checks

Data model highlights:
- tenant key (`workspace_id` via mixin)
- `created_by`
- `is_private`

Permission rules:
- owner/admin: full access
- member:
  - manage only own notes
  - view public notes + own private notes

Repository guarantees:
- all note queries include tenant scope
- member listing query applies visibility filter in SQL

Read performance:
- `GET /notes` and `GET /notes/{id}` use Redis cache-aside when configured (`WorkspaceRedisCache` from `core/redis/deps.py`); keys include `workspace_id`, viewer variant, and a workspace generation counter bumped on any note mutation.

### 4.7 `notebooks` module
Responsibilities:
- list notebooks in workspace
- create notebook (owner/admin only)

Tenant handling:
- repository extends `TenantRepository`
- all operations scoped by workspace

Read performance:
- `GET /notebooks/` uses the same tenant-scoped cache-aside pattern; notebook create bumps the workspace notebooks generation.

### 4.8 `files` module
Responsibilities:
- upload and persist file metadata in the active workspace
- list, read metadata, stream download, update, delete
- attach files to notes via the shared association table only

Storage layer:
- `get_storage()` returns a `StorageBackend` selected by `STORAGE_BACKEND` (`local`, `minio`, `r2`).
- Upload path validates MIME and policy in `core/storage/utils.py` before writing bytes through the backend.

Tenancy and data:
- `File` model uses `WorkspaceTenantMixin`; `storage_key` is unique and maps to the object key in the backend.

RBAC:
- `files/permissions.py` mirrors the notes visibility pattern: owner/admin see all workspace files; members see public files plus files they created.

Integration boundary:
- Note-to-file links use `note_attachments` in `core/database/associations.py` so `notes/` and `files/` stay loosely coupled.

### 4.9 `ai_gateway` module (current state)
Current code status:
- `src/ai_gateway/router.py` and `src/ai_gateway/schemas.py` are placeholders (empty).

LLD contract for implementation:
- must follow same router -> dependency -> service/repository layering
- must consume `RequestContext` for workspace-safe behavior
- avoid bypassing tenant and permission patterns used by other modules

## 5) Data model and persistence design

### 5.1 Core entities (implemented)
- `users`
- `workspaces`
- `workspace_users` (membership + role)
- `notes`
- `notebooks`
- `pages` (model exists and relates to notebooks)
- `files` (metadata + `storage_key`; binary content in configured `StorageBackend`)
- `note_attachments` (association between `notes` and `files`)

### 5.2 Shared mixins/patterns
- `TimestampMixin` for auditing fields
- `WorkspaceTenantMixin` for tenant key
- `tenant_filter(model, workspace_id)` for standardized predicate

### 5.3 Transaction pattern
Repositories currently perform:
- `session.add(...)`
- `session.commit()`
- optional `session.refresh(...)`

This keeps write semantics explicit and local to repository methods.

## 6) Dependency and responsibility matrix
- `main.py`: app composition, module registration, `ProxyHeadersMiddleware`, global rate limit dependency
- `nginx/default.conf` (Compose): edge `limit_req` per `$binary_remote_addr`, reverse proxy to `api:8000`, tracing/proxy headers
- `core/database/session.py`: async engine/session factory + DI dependency
- `core/redis/client.py`: shared async Redis client (`get_async_redis`) when `REDIS_URL` is set
- `core/redis/redis.py`: JWT refresh + access blacklist token store (`get_token_store`)
- `core/redis/cache.py`: tenant-scoped `WorkspaceRedisCache` (cache-aside JSON + generation bumps)
- `core/redis/deps.py`: `get_workspace_cache` / `get_redis_connection` for routers and rate limiting
- `core/storage/client.py`: storage backend factory (`get_storage`) used by file write/read/delete paths
- `core/storage/utils.py`: MIME and upload validation helpers
- `core/security/dependency.py`: token decode to context; optional decode for rate limit identity
- `core/security/rate_limit.py`: fixed-window Redis rate limits + FastAPI dependencies
- `core/security/permissions.py`: route-level RBAC
- `<module>/router.py`: HTTP orchestration
- `<module>/service.py`: domain/business rules (where present)
- `<module>/repository.py`: DB access + persistence
- `<module>/schemas.py`: request/response contracts
- `<module>/models.py`: ORM table mapping

## 7) Error handling strategy
- Domain validation and authorization use HTTP exceptions with explicit status codes:
  - 400: invalid role/state conflicts
  - 401: auth failure
  - 403: permission denied
  - 404: entity/membership not found
  - 429: application rate limit exceeded (`Retry-After` header)
- Fallback global exception handler returns generic 500 body.

## 8) Testing strategy alignment
Current tests validate:
- permissions and tenant repository behavior
- notebooks API
- notes RBAC API
- auth security logic and token rotation / blacklist flows
- `WorkspaceRedisCache` cache-aside and generation invalidation (`tests/core/test_workspace_redis_cache.py`)
- application rate limiter behavior (`tests/core/test_rate_limit.py`)
- page versioning behavior
- files module flows with mocked storage (`tests/files/`)
- Supabase smoke path for integrated flow

Recommended rule:
- each new module must add at least:
  - context/tenant-scope tests
  - role-based authorization tests
  - happy-path CRUD/service tests
- for modules that touch object storage: mock `StorageBackend` / IO boundaries so CI does not depend on MinIO, R2, or local disk layout

## 9) Extension blueprint for new modules
For any new bounded module under `src/<module>/`:
1. Create `models.py`, `schemas.py`, `repository.py`, `router.py`.
2. Add `service.py` if business rules are non-trivial.
3. Inject `RequestContext` in protected routes.
4. Scope tenant queries through repository + `tenant_filter`.
5. Use `require_roles` and domain permission helpers where needed.
6. Register router in `main.py`.
7. Add migration + tests.

If the module stores binary blobs, use `StorageBackend` (`core/storage/client.py`) for bytes and keep SQL rows tenant-scoped with metadata and `storage_key`, following the `files` module pattern.

This keeps all modules consistent with current architecture and minimizes security regression risk.
