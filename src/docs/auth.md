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
  - `create_refresh_token(data, expires_days=30)`

Token claims now include:
- `jti`: unique token id
- `typ`: `access` or `refresh`
- `exp`: expiry timestamp

### Redis-backed token state (refresh + logout)
To keep auth module changes minimal, token state is handled by a reusable core component:

- `src/core/redis/redis.py`
  - `store_refresh_token(user_id, jti, ttl_seconds)`
  - `is_refresh_token_active(user_id, jti)`
  - `revoke_refresh_token(user_id, jti)`
  - `blacklist_access_token(jti, ttl_seconds)`
  - `is_access_token_blacklisted(jti)`

Behavior:
- On `register/login`, issued refresh token `jti` is stored in Redis.
- On `refresh`, old refresh token must exist in Redis; then it is rotated (revoked and replaced).
- On `logout`, access token `jti` is blacklisted in Redis until its `exp`.
- On protected routes, access token is rejected if blacklisted.

Fallback behavior:
- If Redis is disabled or not configured (`REDIS_ENABLED=false` or missing `REDIS_URL`), auth still works in stateless mode.

### Token validation → building the `RequestContext`
Every protected route should add a dependency that decodes the access token.

Key files:

- `src/auth/dependency.py`
  - `oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")`
  - This defines the “Bearer token” extraction behavior for FastAPI.

- `src/core/security/dependency.py`
  - `get_current_context(token=Depends(oauth2_scheme)) -> RequestContext`
  - Decodes the JWT using `settings.JWT_SECRET`
  - Enforces `typ == "access"`
  - Checks Redis access-token blacklist by `jti`
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

4. Refresh + logout lifecycle
   - `POST /auth/refresh` verifies refresh token exists in Redis and rotates it.
   - `POST /auth/logout` blacklists current access token and optionally revokes a submitted refresh token.

### Auth API commands (quick test)
1. Login/register to get tokens.
2. Refresh:
   - `POST /auth/refresh`
   - body: `{"refresh_token":"<refresh>"}` 
3. Logout:
   - `POST /auth/logout`
   - header: `Authorization: Bearer <access_token>`
   - optional body: `{"refresh_token":"<refresh>"}` (revokes refresh immediately)

### Operational best practices
- Always enforce workspace scoping in repositories and/or via `tenant_filter` helpers.
- Keep JWT decoding as a single dependency (avoid custom JWT decoding per route).
- Keep ownership and visibility logic out of routers; use domain permission helpers.

