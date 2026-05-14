## DashNoteSystem backend (system workflow & routing)

### Overview
This project is a **multi-tenant Notes backend** built with **FastAPI + async SQLAlchemy**. Authentication is handled by the `auth` service (JWT), and every other service uses the JWT to build a **workspace-aware** `RequestContext`:

- `user_id` (from JWT `sub`)
- `workspace_id` (from JWT `wid`)
- `role` (from JWT `role`)

All tenant-scoped data access is performed through repositories that filter by `workspace_id`.

### Entry point: `src/main.py`
`src/main.py` creates the FastAPI app and registers routers:

- `src/auth/router.py` (prefix: `/auth`)
- `src/notebooks/router.py` (prefix: `/notebooks`)
- `src/notes/router.py` (prefix: `/notes`)
- `src/files/router.py` (mounted at `/files` via `src/main.py`)
- `src/workspaces/router.py` (prefix: `/workspaces`)
- `src/membership/router.py` (prefix: `/workspaces/members`)

It also mounts **`core.health`** for orchestration:

- `GET /health` — deep probe: async `SELECT 1` on PostgreSQL and Redis `PING` when Redis is configured (`REDIS_ENABLED` and `REDIS_URL`). Returns **200** when all required dependencies respond, **503** otherwise, with `timestamp`, `latency_ms`, and a `dependencies` map (`database`, and `redis` when applicable).

### Request lifecycle (workflow)
Most endpoints follow the same flow:

1. **Client authenticates** using `POST /auth/login` and obtains an `access_token`.
2. Client calls any protected route with:
   - header: `Authorization: Bearer <access_token>`
3. Router dependency `core.security.dependency.get_current_context` decodes the JWT and returns `core.security.context.RequestContext`.
4. Router uses:
   - `ctx.workspace_id` to scope repository queries
   - `ctx.user_id` to enforce ownership rules (when needed)
   - `ctx.role` to enforce RBAC (via `core.security.permissions.require_roles(...)` or per-entity permission helpers)
5. Repository executes an **async SQLAlchemy** query and returns DB models.
6. Router maps models to response schemas (Pydantic).

### Auth-to-context injection (how it works everywhere)
The shared injection mechanism is:

- `core/security/dependency.py` provides `get_current_context(ctx=Depends(oauth2_scheme))`
- `auth/dependency.py` defines `oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")`

Routers typically add:

- `ctx: RequestContext = Depends(get_current_context)`
- OR role-gated: `ctx: RequestContext = Depends(require_roles("owner", "admin"))`

### Dependency map (which files depend on what)

#### App wiring
- `src/main.py`
  - depends on `config.settings`
  - registers `core.health` (`GET /health`) before feature routers
  - depends on each module’s `router` (`auth/router.py`, `notes/router.py`, etc.)

#### Health / readiness
- `core/health.py`
  - `check_database(db)` runs `SELECT 1` via SQLAlchemy
  - `check_redis(redis)` runs `PING` when Redis is required
  - `GET /health` uses `Depends(get_db)` and `Depends(get_redis)` (`core/redis/deps.py`)
- `core/database/session.py`
  - depends on `config.settings.DATABASE_URL`
  - provides `get_session()` used by routers via `Depends(get_session)`

- `core/database/utils.py`
  - provides `tenant_filter(model, workspace_id)`
  - used by tenant-scoped repositories (e.g. `notes/repository.py`, `notebooks/repository.py`)

- `core/database/mixins.py`
  - provides `TimestampMixin`, `WorkspaceTenantMixin`, etc.

#### Tenant scoping and RBAC
- `core/security/context.py`
  - defines `RequestContext(user_id, workspace_id, role)`

- `core/security/dependency.py`
  - decodes JWT and builds `RequestContext`

- `core/security/permissions.py`
  - provides `require_roles(*allowed_roles)` dependency factory

#### Module specifics
- `src/auth/*`
  - issues JWTs in `auth/router.py`
  - stores/validates users and memberships in `auth/models.py` and `auth/service.py`

- `src/workspaces/*`
  - reads/updates `workspaces.models.Workspace` using `RequestContext.workspace_id`

- `src/membership/*`
  - uses existing `auth.models.WorkspaceUser` table (`workspace_users`) to list/invite/update/remove members

- `src/files/*`
  - tenant-scoped file metadata, upload/download orchestration, and permissions; details in **Storage system** below.

- `src/notes/*`
  - note ownership + visibility rules live in `notes/permissions.py`
  - note persistence lives in `notes/repository.py`

#### Redis (shared client, auth state, and cache-aside)
Redis is optional at runtime (`REDIS_ENABLED`, `REDIS_URL` in `config.settings`). When configured, the process uses **one shared async Redis client** (`core/redis/client.py`: `get_async_redis`) for:
- **JWT operational state** (refresh-token presence, access-token logout blacklist) via `get_token_store()` / `core/redis/redis.py` (see `src/docs/auth.md`).
- **Application reads** using **cache-aside** in selected routers (`GET /notes`, `GET /notes/{id}`, `GET /notebooks/`).

Tenant safety for cached reads:
- Keys are always prefixed with `workspace_id` from `RequestContext` (JWT `wid`), plus a **list variant** for notes (`staff` for owner/admin vs `u{user_id}` for members) so member-visible subsets cannot leak across users.
- **Invalidation** does not scan keys: each workspace keeps monotonic **generation counters** (`INCR` on `app:cache:gen:notes:{wid}` and `app:cache:gen:notebooks:{wid}`). Any note write bumps the notes generation; notebook create bumps the notebooks generation, so stale list/detail entries age out immediately when Redis is enabled.

FastAPI wiring (no change to how JWT context is produced):
- `core/redis/deps.py` exposes `get_redis_connection` (alias `get_redis`), and `get_workspace_cache`. Routers that need caching add `cache: WorkspaceRedisCache = Depends(get_workspace_cache)` alongside existing `get_current_context` / `get_session` dependencies. FastAPI deduplicates nested `Depends(get_current_context)` per request.
- **TTL**: cached JSON entries use `settings.CACHE_TTL_SECONDS` (default 60) as the Redis `SETEX` lifetime; generations provide correctness, TTL bounds recovery if a bump is missed.

When Redis is disabled, `WorkspaceRedisCache` receives `redis=None`: every read is a cache miss and mutations still succeed (no-op bump), preserving existing API behavior without Redis.

### Tenancy model (current implementation)
Multi-tenancy is implemented using:

- JWT claim `wid` -> `RequestContext.workspace_id`
- DB columns:
  - tenant-aware entities include `workspace_id` (via `WorkspaceTenantMixin`)

Tenant filtering is standardized through:

- `core/database/utils.tenant_filter(...)`

### RBAC rules (current implementation)
Roles come from `RequestContext.role` which is populated from JWT.

Common meaning:

- `owner`: workspace creator / highest privileges
- `admin`: admin privileges for the workspace
- `member`: standard member privileges

General enforcement patterns:

- Router-level role enforcement: `core.security.permissions.require_roles(...)`
- Entity-specific permission logic: `src/notes/permissions.py`

Notes RBAC/visibility (important):

- `owner/admin`: can CRUD any note in the workspace
- `member`:
  - can CRUD only their own notes
  - can view:
    - all public notes (`is_private = false`)
    - their own private notes (`created_by == ctx.user_id`)

### Storage system (current implementation)
Binary objects are stored **outside PostgreSQL** behind a small backend abstraction; the database holds **metadata**, **`workspace_id`**, and fields used for RBAC—same tenancy story as notes and notebooks.

**Backend selection**
- `core/storage/client.py`: `get_storage()` reads `config.settings.STORAGE_BACKEND` (`local`, `minio`, or `r2`) and returns a `StorageBackend` (`upload`, `download`, `delete`, `presigned_url`).
- **Local** (`LocalStorageBackend`): files under `LOCAL_STORAGE_PATH`; `presigned_url` returns `None` so clients typically use the app’s download route.
- **MinIO / R2** (`MinIOStorageBackend`, `R2StorageBackend`): S3-compatible endpoints via `aioboto3` / `boto3`; `presigned_url` may be used for direct client downloads depending on router/service behavior.

**Upload validation**
- `core/storage/utils.py`: MIME sniffing (`detect_mime_type`), `validate_file`, allowed extensions, and size limits so uploads stay consistent with detected type.

**Tenancy**
- `files.models.File` uses `WorkspaceTenantMixin`; repositories scope queries with `workspace_id` like other tenant modules (`tenant_filter` pattern).

**RBAC and visibility**
- `files/permissions.py`: `owner` and `admin` see all files in the workspace; `member` sees non-private files and any file they created (`created_by` matches `ctx.user_id`).

**Note ↔ file association**
- `core/database/associations.py` defines `note_attachments` only; `notes/` and `files/` do not import each other’s packages beyond this shared table.

**HTTP surface**
- `files/router.py` is mounted in `main.py` at prefix `/files` (upload, list, get, streamed download, patch, delete, attach to note, admin-oriented listing as implemented in code).

### Production-grade notes / operational concerns
Recommended operational practices:

- Treat `core/security/dependency.py` as the **single source of truth** for JWT claim names (`sub`, `wid`, `role`).
- Keep permission logic out of routers:
  - routers should call dedicated helpers (for example `notes/permissions.py`, `files/permissions.py`).
- When adding new tenant-scoped entities:
  - include a `workspace_id` column (use `WorkspaceTenantMixin`)
  - always scope queries via repository + `tenant_filter`.
- For file-like features, keep bytes in object storage and metadata in SQL; extend `StorageBackend` or settings rather than embedding secrets in code.

### Where to extend next
If you add new note-like resources or collaboration features:

- create a new module under `src/<module_name>/`
- implement:
  - `models.py`, `schemas.py`, `repository.py`, `router.py`
  - permission helper(s) if RBAC is non-trivial
- inject auth as described in `src/docs/auth.md`.

### Automated testing (files module)
Tests under `tests/files/` exercise the files flow with **pytest** and **pytest-asyncio**. Storage and IO boundaries (`aioboto3`, `pathlib.Path`, and related calls) are **mocked** so the suite does not require a live PostgreSQL instance or real object storage.

**Fixtures and environment**
- `tests/conftest.py` wires `Settings` (database URL and JWT secret placeholders) for imports and dependencies used by file tests.
- On hosts without **libmagic** (typical on Windows), conftest provides a minimal **`magic` import stub** so `core.storage.utils` loads; production Docker images install **`libmagic1`** for real MIME detection.

**Command** (repository root):

```powershell
python -m pytest tests/files -q
```

**Pytest configuration**
- `pytest.ini`: `pythonpath = src`, `asyncio_mode = auto`.

### Smoke testing (file upload, live API)
Use this after the stack is healthy (`docker compose up -d --build`, then `GET /health` → HTTP **200** with `"status":"ok"` and dependency details) to validate `files/router.py` end-to-end.

**Steps**
1. `POST /auth/register` (or login) to obtain `access_token`.
2. `POST /files/upload` as `multipart/form-data` with file part name `file`, form fields `is_private` and optional `description`.
3. Use an allowed extension consistent with sniffed MIME (example: `.txt` with `text/plain` body).

**Example** (repo root; requires `httpx`):

```powershell
python -c "import uuid, httpx; b='http://127.0.0.1:8000'; e=f'test_{uuid.uuid4().hex[:8]}@exame.com'; t=httpx.post(f'{b}/auth/register', json={'email':e,'password':'Test123!','workspace_name':'ws'}, timeout=30).json()['access_token']; r=httpx.post(f'{b}/files/upload', headers={'Authorization':f'Bearer {t}'}, files={'file':('requirement.txt',b'req line\n','text/plain')}, data={'is_private':'false','description':'smoke'}, timeout=30); print(r.status_code, r.json())"
```

**Expected success**
- HTTP **200** and JSON including `id`, `name`, `mime_type`, `size_bytes`, and `download_url` (often a relative `/files/{id}/download` when the backend does not return a presigned URL).

### Docker Compose (API, database, Redis, migrations)
Compose starts PostgreSQL and Redis, runs **`alembic upgrade head`** once via a **`migrate`** service after the database is healthy, then starts the **API** so migrations always precede traffic.

#### Prerequisites
- Docker Desktop running
- Host ports **8000** and **5432** free (or change mappings in compose)

#### Start the stack
From the repository root:

```powershell
docker compose up -d --build
```

**Services**
- **api**: built from `Dockerfile`, including **`libmagic1`** for `python-magic` during upload validation.
- **db**: `postgres:16-alpine` with healthcheck.
- **redis**: `redis:7-alpine` (JWT token state when the API is given `REDIS_URL`, plus optional cache-aside for read-heavy routes documented above).
- **migrate**: one-shot job; exits after `alembic upgrade head` succeeds.

#### Verify
```powershell
docker compose ps
curl.exe -sS --max-time 10 http://127.0.0.1:8000/health
docker compose logs --tail 50 api
docker compose logs --tail 50 migrate
```

**Health check**: expect HTTP **200** and JSON including `status`, `timestamp`, `latency_ms`, and `dependencies` (each dependency reports `reachable`; Redis may include `configured: false` when Redis is not enabled in settings).

#### Stop
```powershell
docker compose down
```

#### Reset including volumes
```powershell
docker compose down -v
```

#### Re-run migrations only
```powershell
docker compose run --rm migrate
```

