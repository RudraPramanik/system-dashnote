# DashNoteSystem Low-Level Design (LLD)

## 1) Objective and scope
This document defines the implementation-level design for the current backend in `g:\projects\dashnotesystem`, aligned with code that exists today.

In scope:
- Auth + JWT context propagation
- Multi-tenant data access model
- RBAC + domain permissions
- Object storage abstraction (local / S3-compatible backends) and the `files` module
- Implemented modules: `auth`, `workspaces`, `membership`, `notes`, `notebooks`, `files`
- Extension contract for upcoming modules (such as `ai_gateway`)

Out of scope:
- Frontend design
- Infrastructure provisioning
- Non-implemented runtime components

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
- CORS middleware
- module routers
- global exception handler

Registered routers:
- `/auth`
- `/files`
- `/notebooks`
- `/notes`
- `/workspaces`
- `/workspaces/members`

System endpoints:
- `GET /health`
- `GET /`

### 3.2 Request flow (protected endpoint)
1. Client sends `Authorization: Bearer <token>`.
2. `oauth2_scheme` extracts the token.
3. `get_current_context` validates JWT and builds `RequestContext`.
4. Router instantiates repository with `ctx.workspace_id` where tenant-scoped.
5. Permission checks run (`require_roles` and/or domain helper).
6. Repository executes async SQLAlchemy query.
7. Router returns Pydantic schema.

## 4) Module-level low-level design

### 4.1 `auth` module
Responsibilities:
- user registration
- credential validation
- token issuance

Primary flow:
- `POST /auth/register`
  - creates `users`, `workspaces`, `workspace_users`
  - issues access + refresh JWTs with `sub`, `wid`, `role`
- `POST /auth/login`
  - validates credentials
  - selects first membership as default workspace
  - issues access + refresh JWTs

Notes:
- refresh tokens are generated but refresh endpoint is not implemented yet.

### 4.2 `core.security` module
Responsibilities:
- auth context extraction from token
- generic role gating

Components:
- `get_current_context`: JWT decode -> `RequestContext`
- `require_roles(*roles)`: dependency factory for 403 enforcement

Failure behavior:
- invalid/missing claims/token -> `401 Invalid or expired token`
- insufficient role -> `403 Insufficient permissions`

### 4.3 `workspaces` module
Responsibilities:
- retrieve current workspace
- rename workspace

Endpoints:
- `GET /workspaces/me`: authenticated user
- `PATCH /workspaces/me`: owner/admin only

Design note:
- workspace identity is always taken from JWT `wid` through context.

### 4.4 `membership` module
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

### 4.5 `notes` module
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

### 4.6 `notebooks` module
Responsibilities:
- list notebooks in workspace
- create notebook (owner/admin only)

Tenant handling:
- repository extends `TenantRepository`
- all operations scoped by workspace

### 4.7 `files` module
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

### 4.8 `ai_gateway` module (current state)
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
- `main.py`: app composition and module registration
- `core/database/session.py`: async engine/session factory + DI dependency
- `core/storage/client.py`: storage backend factory (`get_storage`) used by file write/read/delete paths
- `core/storage/utils.py`: MIME and upload validation helpers
- `core/security/dependency.py`: token decode to context
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
- Fallback global exception handler returns generic 500 body.

## 8) Testing strategy alignment
Current tests validate:
- permissions and tenant repository behavior
- notebooks API
- notes RBAC API
- auth security logic
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
