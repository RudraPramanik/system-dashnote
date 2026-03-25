## Authentication & Authorization (JWT) — `src/auth` + injection workflow

### What this system authenticates
Authentication is handled by the `auth` module, and returns JWTs used by all other services to enforce workspace-scoped access control.

The JWT is expected to carry the following claims:

- `sub`: user id
- `wid`: workspace id (tenant id)
- `role`: user role within that workspace (`owner | admin | member`)

### Token issuance
Endpoints:

- `POST /auth/register`
  - Creates:
    - a `users` row (`auth/models.py`)
    - a `workspaces` row (`workspaces/models.py`)
    - a `workspace_users` membership row (`auth/models.py`)
  - Issues JWTs embedding:
    - `sub=user.id`
    - `wid=workspace.id`
    - `role=membership.role`

- `POST /auth/login`
  - Validates credentials against stored `password_hash`
  - Picks the user’s first membership as the default workspace
  - Issues JWTs embedding:
    - `sub=user.id`
    - `wid=membership.tenant_id`
    - `role=membership.role`

JWT creation is done in:

- `src/auth/security.py`
  - `create_access_token(data, expires_minutes=15)`
  - `create_refresh_token(data, expires_days=30)` (not used elsewhere yet)

### Token validation → building the `RequestContext`
Every protected route should add a dependency that decodes the access token.

Key files:

- `src/auth/dependency.py`
  - `oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")`
  - This defines the “Bearer token” extraction behavior for FastAPI.

- `src/core/security/dependency.py`
  - `get_current_context(token=Depends(oauth2_scheme)) -> RequestContext`
  - Decodes the JWT using `settings.JWT_SECRET`
  - Builds:
    - `core.security.context.RequestContext(user_id, workspace_id, role)`

If decoding fails, the dependency raises:

- `401 Invalid or expired token`

### How to inject auth into other services (the standard pattern)
In any router function, add one of these:

1. Require authentication (no role restriction)

   - `ctx: RequestContext = Depends(get_current_context)`

2. Require authentication + specific roles

   - `ctx: RequestContext = Depends(require_roles("owner", "admin"))`

Where:

- `get_current_context` comes from `src/core/security/dependency.py`
- `require_roles(...)` comes from `src/core/security/permissions.py`

Then use:

- `ctx.workspace_id` to scope all tenant queries (repositories must filter by workspace)
- `ctx.user_id` when ownership matters (e.g. “only edit your own notes”)
- `ctx.role` for RBAC checks

### Example: wiring `RequestContext` in a new router
Use the same approach as existing routes like `src/notes/router.py` and `src/notebooks/router.py`:

- add `ctx = Depends(get_current_context)` (or `require_roles(...)`)
- construct the repository with `workspace_id=ctx.workspace_id`
- call permission helpers when entity ownership matters

### How to update / evolve the auth workflow
You’ll typically change one of these areas:

1. JWT claim shape (breaking change)
   - If you rename claim keys or change types, update:
     - `src/auth/router.py` (what claims are issued)
     - `src/core/security/dependency.py` (what claims are read)

2. Role vocabulary / permissions logic
   - Roles are currently treated as strings:
     - `owner`, `admin`, `member`
   - Update `src/core/security/permissions.py` only if role gating behavior changes.
   - Entity-specific RBAC should live in the domain module (e.g. `src/notes/permissions.py`).

3. Multi-workspace selection
   - Currently, `POST /auth/login` picks the user’s “first membership”.
   - If you add a “switch workspace” endpoint:
     - update auth login to use a requested membership, or add a dedicated claims re-issue endpoint.

4. Refresh token usage
   - Refresh tokens are created but there is no refresh endpoint wired in this repo.
   - Add:
     - `POST /auth/refresh`
   - Then decide where to re-issue access tokens with the correct `sub/wid/role` claims.

### Operational best practices
- Always enforce workspace scoping in repositories and/or via `tenant_filter` helpers.
- Keep JWT decoding as a single dependency (avoid custom JWT decoding per route).
- Keep ownership and visibility logic out of routers; use domain permission helpers.

