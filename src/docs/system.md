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

It also exposes:

- `GET /health`
- `GET /` (base)

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
  - depends on each module’s `router` (`auth/router.py`, `notes/router.py`, etc.)

#### Database access
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
  - uploads use MIME sniffing (`core/storage/utils.py`: `detect_mime_type`, `validate_file`, size/extension checks), storage abstraction (`core/storage/client.py`: Local / MinIO / `R2`), and persistence in `files/models.py` scoped by `workspace_id`.
  - list/read/download visibility mirrors notes-style RBAC: `files/permissions.py` (`owner`/`admin` see all workspace files; `member` sees non-private files or files they created).
  - note ↔ file links use the shared association table `note_attachments` in `core/database/associations.py` only (no direct imports between `notes/` and `files/` packages beyond this table).
  - API routes live in `files/router.py` (`POST /files/upload`, `GET /files`, `GET /files/{file_id}`, download stream, patch/delete, attach to note, admin list).

- `src/notes/*`
  - note ownership + visibility rules live in `notes/permissions.py`
  - note persistence lives in `notes/repository.py`

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

### Production-grade notes / operational concerns
Recommended operational practices:

- Treat `core/security/dependency.py` as the **single source of truth** for JWT claim names (`sub`, `wid`, `role`).
- Keep permission logic out of routers:
  - routers should call dedicated helpers like `notes/permissions.py`.
- When adding new tenant-scoped entities:
  - include a `workspace_id` column (use `WorkspaceTenantMixin`)
  - always scope queries via repository + `tenant_filter`.

### Where to extend next
If you add new note-like resources or collaboration features:

- create a new module under `src/<module_name>/`
- implement:
  - `models.py`, `schemas.py`, `repository.py`, `router.py`
  - permission helper(s) if RBAC is non-trivial
- inject auth as described in `src/docs/auth.md`.

### Automated tests (files / storage)
Integration-style unit tests live under `tests/files/` and use **pytest** + **pytest-asyncio**. They **mock** storage (`aioboto3`, `pathlib.Path`, etc.) and **never** connect to a real database or object storage.

- Configure env for `Settings` in `tests/conftest.py` (database URL and JWT secret placeholders).
- On hosts without **libmagic** (common on Windows), `tests/conftest.py` installs a tiny **`magic` stub** so `core.storage.utils` imports cleanly; Docker images install **`libmagic1`** for production MIME sniffing.

Run from the repository root:

```powershell
python -m pytest tests/files -q
```

Project metadata: `pytest.ini` sets `pythonpath = src` and `asyncio_mode = auto`.

### Smoke: file upload (live API)
With the stack up (`docker compose up -d --build`) and `GET /health` returning `{"status":"ok"}`, you can confirm `files/router.py` end-to-end: **register** (returns JWT), then **`POST /files/upload`** as `multipart/form-data` with part `file` (e.g. `requirement.txt` containing plain text), plus form fields `is_private` and optional `description`. The file must use an allowed extension that matches sniffed MIME (e.g. `.txt` for `text/plain`). Example using **httpx** from the repo root (requires `httpx` installed):

```powershell
python -c "import uuid, httpx; b='http://127.0.0.1:8000'; e=f'test_{uuid.uuid4().hex[:8]}@example.com'; t=httpx.post(f'{b}/auth/register', json={'email':e,'password':'Test123!','workspace_name':'ws'}, timeout=30).json()['access_token']; r=httpx.post(f'{b}/files/upload', headers={'Authorization':f'Bearer {t}'}, files={'file':('requirement.txt',b'req line\n','text/plain')}, data={'is_private':'false','description':'smoke'}, timeout=30); print(r.status_code, r.json())"
```

A successful run returns **200** and a JSON body with `id`, `name`, `mime_type`, `size_bytes`, and `download_url` (relative `/files/{id}/download` when presigned URLs are not used).

### Docker / Compose runbook (API + DB + Redis + migration)
This repo now supports a compose flow where DB and Redis start first, then a one-shot migration service runs `alembic upgrade head`, then API starts.

#### One-time prerequisites
- Docker Desktop running
- Port `8000` and `5432` available

#### Start everything
From repo root:

```powershell
docker compose up -d --build
```

What this does:
- builds the API image from `Dockerfile` (installs **`libmagic1`** for `python-magic` / upload MIME detection)
- starts `db` (`postgres:16-alpine`)
- starts `redis` (`redis:7-alpine`)
- waits for DB healthcheck
- runs `migrate` service once
- starts `api` only after migration succeeds

#### Verify state
```powershell
docker compose ps
curl.exe -sS --max-time 10 http://127.0.0.1:8000/health
docker compose logs --tail 50 api
docker compose logs --tail 50 migrate
```

Expected health response:
- `{"status":"ok"}`

#### Stop services
```powershell
docker compose down
```

#### Reset everything including database volume
```powershell
docker compose down -v
```

#### Re-run migrations manually (if needed)
```powershell
docker compose run --rm migrate
```

