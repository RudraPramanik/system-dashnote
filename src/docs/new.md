## DashNoteSystem Auth + Multi-Tenant Documentation

This document explains **how authentication and tenancy work end-to-end** in this backend, in a way a fresher developer can follow, rebuild, and extend.

If you understand this file, you can:
- implement new protected APIs
- safely add new tenant-scoped entities
- modify role rules without breaking existing behavior

---

## 1) Big Picture (How requests are protected)

The backend is a FastAPI app where:
- users authenticate via `/auth/register` or `/auth/login`
- auth returns JWT tokens (access + refresh)
- every protected route decodes the access token into a `RequestContext`
- repositories use `workspace_id` from context to isolate data per tenant

Core wiring:
- App entry and router registration: `src/main.py`
- Token issuance: `src/auth/router.py`
- Token decode -> request context: `src/core/security/dependency.py`
- Role guard dependency: `src/core/security/permissions.py`

---

## 2) Authentication Flow (Step by step)

### 2.1 Register flow (`POST /auth/register`)

Primary endpoint:
- `src/auth/router.py` -> `register(...)`

What happens internally:
1. Router receives `RegisterRequest` (`email`, `password`, `workspace_name`). 
2. Router calls `register_user(...)` in `src/auth/service.py`.
3. Service creates:
   - `User` row (`src/auth/models.py`)
   - `Workspace` row (`src/workspaces/models.py`)
   - `WorkspaceUser` membership row with role `owner` (`src/auth/models.py`)
4. Router generates JWT payload:
   - `sub`: user id
   - `wid`: workspace id
   - `role`: membership role
5. Router returns `TokenResponse` with:
   - `create_access_token(...)`
   - `create_refresh_token(...)`

Functions responsible:
- `src/auth/router.py` -> `register`
- `src/auth/service.py` -> `register_user`
- `src/auth/security.py` -> `create_access_token`, `create_refresh_token`

### 2.2 Login flow (`POST /auth/login`)

Primary endpoint:
- `src/auth/router.py` -> `login(...)`

What happens:
1. Router receives `LoginRequest` (`email`, `password`).
2. Router calls `authenticate_user(...)`.
3. Service loads user + memberships and verifies password.
4. Router picks the first membership as default workspace.
5. Router returns new access/refresh JWT with `sub`, `wid`, `role`.

Functions responsible:
- `src/auth/router.py` -> `login`
- `src/auth/service.py` -> `authenticate_user`
- `src/auth/security.py` -> `verify_password`, `create_access_token`, `create_refresh_token`

Note:
- default workspace selection is currently `user.workspaces[0]`. If user can belong to multiple workspaces, add explicit workspace selection later.

### 2.3 Password security

File:
- `src/auth/security.py`

Key behavior:
- Password hashing: `hash_password(password)`
- Password verification: `verify_password(password, hashed)`
- Uses `passlib` `CryptContext` with:
  - `bcrypt` (preferred for new hashes)
  - `pbkdf2_sha256` (legacy verify support)
- Enforces bcrypt limit:
  - `_password_too_long(...)` rejects passwords over 72 bytes during hash

This protects from bcrypt truncation surprises.

---

## 3) JWT Design and Context Injection

### 3.1 JWT claim contract

Claims used across app:
- `sub`: user id
- `wid`: workspace id (tenant id)
- `role`: role in current workspace
- `exp`: expiry

If you rename these claims, update both:
- token creation in `src/auth/router.py`
- token decoding in `src/core/security/dependency.py`

### 3.2 Decode token into request context

Files:
- `src/auth/dependency.py` -> `oauth2_scheme`
- `src/core/security/dependency.py` -> `get_current_context(...)`
- `src/core/security/context.py` -> `RequestContext` dataclass

Flow:
1. `oauth2_scheme` extracts `Authorization: Bearer <token>`.
2. `get_current_context` decodes JWT with `settings.JWT_SECRET`.
3. It builds `RequestContext(user_id, workspace_id, role)`.
4. If token invalid/expired -> raises `401 Invalid or expired token`.

### 3.3 Use in routers

Common auth dependency:
- `ctx: RequestContext = Depends(get_current_context)`

Role-protected dependency:
- `ctx: RequestContext = Depends(require_roles("owner", "admin"))`

Role guard implementation:
- `src/core/security/permissions.py` -> `require_roles(*allowed_roles)`

---

## 4) Multi-Tenant Model (How data isolation works)

This app is workspace-based multi-tenancy.

Tenant identity source:
- JWT claim `wid` -> `RequestContext.workspace_id`

### 4.1 Tenant data model

Core tables:
- `users` (`src/auth/models.py` -> `User`)
- `workspaces` (`src/workspaces/models.py` -> `Workspace`)
- `workspace_users` (`src/auth/models.py` -> `WorkspaceUser`)

Membership table connects users to workspaces:
- `WorkspaceUser.user_id`
- `WorkspaceUser.tenant_id` (references workspace id)
- `WorkspaceUser.role`

Initial schema migration:
- `alembic/versions/52bc7b7d864f_initial_workspace_and_auth_models.py`

### 4.2 Tenant columns on domain models

Preferred tenant column:
- `workspace_id` (see `WorkspaceTenantMixin`)

File:
- `src/core/database/mixins.py` -> `WorkspaceTenantMixin`

Examples using it:
- `src/notes/models.py` -> `Note(Base, WorkspaceTenantMixin, ...)`
- `src/notebooks/models.py` -> `Notebook(Base, WorkspaceTenantMixin, ...)`

### 4.3 Tenant-aware repository base

File:
- `src/core/database/repository.py` -> `TenantRepository`

Purpose:
- stores `self.workspace_id` once in repository constructor
- avoids passing free-form workspace id in every method

### 4.4 Standard tenant filter helper

File:
- `src/core/database/utils.py` -> `tenant_filter(model, workspace_id)`

Behavior:
- filters by `model.workspace_id` if available
- fallback to `model.tenant_id` for legacy models
- raises `AttributeError` if model has neither

This is the common way to avoid accidental cross-tenant queries.

---

## 5) Where Tenant Isolation Is Enforced (real code paths)

### 5.1 Notes module

Files and responsibilities:
- `src/notes/router.py`
  - injects `RequestContext`
  - creates `NoteRepository(db, workspace_id=ctx.workspace_id)`
  - applies permission checks
- `src/notes/repository.py`
  - all read/write queries include `tenant_filter(Note, self.workspace_id)`
  - `create(...)` writes `workspace_id=self.workspace_id`
- `src/notes/permissions.py`
  - `can_view_note(ctx, note)`
  - `can_manage_note(ctx, note)`

Rule summary:
- owner/admin -> manage all notes in workspace
- member -> manage only own notes
- member visibility -> public notes + own private notes

### 5.2 Notebooks module

Files and responsibilities:
- `src/notebooks/router.py`
  - list: any authenticated user in workspace
  - create: only owner/admin via `require_roles`
- `src/notebooks/repository.py`
  - list uses `tenant_filter(Notebook, self.workspace_id)`
  - create sets `workspace_id=self.workspace_id`

### 5.3 Membership module

Files and responsibilities:
- `src/membership/router.py`
  - workspace member listing/invite/role-change/remove endpoints
  - enforces role guards via `require_roles`
- `src/membership/service.py`
  - business rules for who can invite/change/remove
- `src/membership/repository.py`
  - all membership operations scoped by `WorkspaceUser.tenant_id == self.workspace_id`

Important role rules from service:
- admin cannot invite another admin
- only owner can change member roles
- admin cannot remove admin/owner
- user cannot remove self

### 5.4 Workspace profile module

Files:
- `src/workspaces/router.py`
- `src/workspaces/repository.py`

Tenant behavior:
- `GET /workspaces/me` uses `ctx.workspace_id` only
- `PATCH /workspaces/me` requires owner/admin and updates only current workspace

---

## 6) Rebuild This From Scratch (Implementation checklist)

If you had to rebuild auth + tenancy in a new service, follow this order:

1. Create core entities:
   - `User`, `Workspace`, `WorkspaceUser` models and migration
2. Implement auth security:
   - password hash/verify
   - JWT access + refresh creators
3. Build auth service:
   - `register_user`, `authenticate_user`
4. Build auth router:
   - `/auth/register`, `/auth/login`
5. Build token dependency:
   - `oauth2_scheme`
   - `get_current_context`
   - `RequestContext`
6. Build role dependency:
   - `require_roles(...)`
7. Build tenant repository base + helper:
   - `TenantRepository`
   - `tenant_filter(...)`
8. For each domain module:
   - add `workspace_id` to models (via mixin)
   - create repository scoped by `workspace_id`
   - inject `RequestContext` in router
   - add module-specific permission helper when needed

---

## 7) How To Safely Extend This Project

### 7.1 Add a new tenant-scoped resource (example: Tasks)

Create:
- `src/tasks/models.py` (include `WorkspaceTenantMixin`)
- `src/tasks/repository.py` (inherit `TenantRepository`)
- `src/tasks/router.py` (inject `RequestContext`)
- `src/tasks/permissions.py` (if non-trivial RBAC)

In repository:
- every query includes `tenant_filter(Task, self.workspace_id)`
- every create sets `workspace_id=self.workspace_id`

### 7.2 Add workspace switching

Current limitation:
- login chooses first membership only.

Suggested extension:
- add endpoint like `POST /auth/switch-workspace`
- validate user membership in requested workspace
- issue new access token with updated `wid` and `role`

Files to update:
- `src/auth/router.py`
- optionally `src/auth/service.py`

### 7.3 Add refresh-token endpoint

Refresh tokens exist but refresh endpoint is not implemented.

Suggested:
- `POST /auth/refresh`
- decode refresh token with `settings.JWT_REFRESH_SECRET`
- re-issue access token (and optionally rotate refresh token)

Files to update:
- `src/auth/router.py`
- maybe helper in `src/auth/security.py`

### 7.4 Standardize tenant naming (`tenant_id` vs `workspace_id`)

Current state:
- some places still use `tenant_id` (especially membership model/table)
- most domain entities use `workspace_id`

Safe strategy:
- continue using `tenant_filter(...)` while migrating
- gradually rename legacy fields only with migration + full test coverage

---

## 8) Testing references (learn behavior quickly)

Useful tests:
- `tests/auth/test_security.py`
  - verifies password hashing, max bcrypt input handling, token generation
- `tests/core/test_tenant_repository.py`
  - verifies `TenantRepository` stores workspace id correctly
  - verifies `tenant_filter(...)` targets `workspace_id`
- `tests/notes/test_notes_rbac_api.py`
  - validates role-based note visibility and CRUD permissions

For freshers, reading these tests after this document is the fastest way to understand expected behavior.

---

## 9) Quick file/function index

### Authentication
- `src/auth/router.py`
  - `register`, `login`
- `src/auth/service.py`
  - `register_user`, `authenticate_user`
- `src/auth/security.py`
  - `_password_too_long`, `hash_password`, `verify_password`
  - `create_access_token`, `create_refresh_token`
- `src/auth/dependency.py`
  - `oauth2_scheme`

### Security context & role checks
- `src/core/security/dependency.py`
  - `get_current_context`
- `src/core/security/context.py`
  - `RequestContext`
- `src/core/security/permissions.py`
  - `require_roles`

### Multi-tenant base
- `src/core/database/mixins.py`
  - `WorkspaceTenantMixin` (preferred), `TenantMixin` (legacy)
- `src/core/database/repository.py`
  - `TenantRepository`
- `src/core/database/utils.py`
  - `tenant_filter`

### Tenant-aware modules
- Notes:
  - `src/notes/router.py`
  - `src/notes/repository.py`
  - `src/notes/permissions.py`
- Notebooks:
  - `src/notebooks/router.py`
  - `src/notebooks/repository.py`
- Membership:
  - `src/membership/router.py`
  - `src/membership/service.py`
  - `src/membership/repository.py`
- Workspaces:
  - `src/workspaces/router.py`
  - `src/workspaces/repository.py`

---

## 10) Common mistakes to avoid

- Forgetting tenant filter in repository query.
- Trusting client-provided workspace id instead of token-derived `ctx.workspace_id`.
- Putting RBAC logic directly in routers instead of permission/service helpers.
- Changing JWT claim names without updating decode dependency.
- Adding new model without workspace/tenant column.

If you avoid these, you can scale this architecture with much lower risk.
