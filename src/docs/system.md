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

