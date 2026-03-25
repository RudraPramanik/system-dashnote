## API routes map + how to test

### Base URLs
When running locally, Uvicorn will expose:

- API routes under `/`
- Swagger docs at `/docs` (when `settings.DEBUG = True`)

Auth uses:

- `Authorization: Bearer <access_token>` header

### Route map (which service carries which routes)
All routers are registered in `src/main.py`.

#### Auth service (`src/auth/router.py`, prefix: `/auth`)
- `POST /auth/register`
  - Body: `{"email": "...", "password": "...", "workspace_name": "..."}`
  - Response: `access_token`, `refresh_token`

- `POST /auth/login`
  - Body: `{"email": "...", "password": "..."}`
  - Response: `access_token`, `refresh_token`

#### Notes service (`src/notes/router.py`, prefix: `/notes`)
- `GET /notes/`
  - Returns notes visible to the caller within `ctx.workspace_id`
  - RBAC/visibility:
    - `owner/admin`: all notes in workspace
    - `member`: public notes + own private notes

- `POST /notes/`
  - Body: `{"title": "...", "content": "...", "is_private": true|false}`
  - Caller becomes `created_by`

- `GET /notes/{note_id}`
  - Visibility enforced by `src/notes/permissions.py`

- `PATCH /notes/{note_id}`
  - RBAC enforced by `src/notes/permissions.py`
  - `member` can only update their own notes

- `DELETE /notes/{note_id}`
  - RBAC enforced by `src/notes/permissions.py`

#### Workspaces service (`src/workspaces/router.py`, prefix: `/workspaces`)
- `GET /workspaces/me`
  - Uses `ctx.workspace_id` from JWT

- `PATCH /workspaces/me`
  - Role gated by `require_roles("owner", "admin")`
  - Updates workspace name

#### Membership service (`src/membership/router.py`, prefix: `/workspaces/members`)
- `GET /workspaces/members/`
  - Lists members in the caller’s `ctx.workspace_id`

- `POST /workspaces/members/`
  - Role gated by `require_roles("owner", "admin")`
  - Body: `{"email": "...", "role": "member"|"admin"}`
  - Invites/creates membership in `workspace_users`

- `PATCH /workspaces/members/{user_id}`
  - Role gated by `require_roles("owner")`
  - Body: `{"role": "member"|"admin"}`

- `DELETE /workspaces/members/{user_id}`
  - Role gated by `require_roles("owner", "admin")`

#### Notebooks service (`src/notebooks/router.py`, prefix: `/notebooks`)
Existing endpoints:

- `GET /notebooks/`
- `POST /notebooks/` (role gated by `require_roles("owner", "admin")`)

#### System endpoints (`src/main.py`)
- `GET /health`
- `GET /` (base)

### How to test routes manually (Swagger)
1. Start the server (example):
   - `.\.venv\Scripts\python -m uvicorn src.main:app --reload`
2. Open `http://127.0.0.1:8000/docs`
3. Use “Authorize” in Swagger to set:
   - `Bearer <access_token>`
4. Call endpoints and verify RBAC behavior for notes and membership.

### How to test routes with `curl` (recommended minimal flow)
1. Get a token:
   - `POST /auth/register` or `/auth/login`
2. Use the returned `access_token`:
   - `Authorization: Bearer <token>`

Example (conceptual):

```bash
curl -X POST http://127.0.0.1:8000/auth/login ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"you@example.com\",\"password\":\"your_password\"}"
```

Then:

```bash
curl -X POST http://127.0.0.1:8000/notes/ ^
  -H "Authorization: Bearer <access_token>" ^
  -H "Content-Type: application/json" ^
  -d "{\"title\":\"t1\",\"content\":\"c1\",\"is_private\":false}"
```

### How to test routes via automated tests (pytest)
This repo includes API tests, including RBAC coverage for notes:

- `tests/notes/test_notes_rbac_api.py`

Run all tests:

```bash
$env:PYTHONPATH='src'
.\.venv\Scripts\python -m pytest -q
```

Notes on how tests work:
- Tests override two dependencies:
  - `core.database.session.get_session` (uses an in-memory DB)
  - `core.security.dependency.get_current_context` (sets `RequestContext` for different roles)

### Quick verification checklist (RBAC)
- `member` can:
  - create notes
  - update/delete their own notes
  - view public notes + own private notes
- `member` cannot:
  - update/delete other users’ private notes (or admin/owner notes)
- `owner/admin` can:
  - CRUD any note in the workspace

### Protected routes: verify JWT → `RequestContext` injection

The protected routes rely on these dependencies:

- `auth/dependency.py` (extracts `Authorization: Bearer ...`)
- `core/security/dependency.py` (`get_current_context` decodes JWT claims into `RequestContext(user_id, workspace_id, role)`)
- Domain RBAC helpers:
  - `notes/permissions.py` for note visibility + edit rules
  - `core/security/permissions.py` for coarse role gating (e.g. workspace rename, notebook create)

Sanity checks you should run (especially for notes):

1. Call a protected endpoint without auth
   - Example: `GET /notes/`
   - Expected: `401 Invalid or expired token`

2. Call the same endpoint with a valid token
   - Expected: `200` (and correct workspace-scoped results)

3. Validate role enforcement
   - `member` can view public notes + their own private notes
   - `member` cannot edit/delete an `owner/admin` note

> Manual member testing note: `/auth/login` chooses a “default” workspace based on the user’s memberships. If a user belongs to multiple workspaces, you may need a workspace-scoped token (JWT `wid` + `role`) to test member permissions reliably.

### Supabase integration test (recommended)

This repo includes a Supabase-backed smoke test that:

- runs through `POST /auth/register` for 2 users
- verifies a protected route returns `401` without auth
- creates notes as `owner`
- invites another user via `POST /workspaces/members/`
- issues a member-scoped JWT for the invited user in the owner workspace
- verifies:
  - note visibility (public vs private)
  - edit denial (`403`) for member on owner private notes
  - delete allowed for owner
- also checks role gating for:
  - `PATCH /workspaces/me` (403 for member)
  - `POST /notebooks/` (403 for member)

Run it from repo root:

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python tests\supabase_smoke_test.py
```

Expected output ends with:

- `Supabase smoke test: OK`

### Supabase DB migration (run before integration tests)

If you changed any models/services:

1. Generate a migration (only if needed)
   - `.\.venv\Scripts\python -m alembic revision --autogenerate -m "your message"`

2. Apply to Supabase
   - `.\.venv\Scripts\python -m alembic upgrade head`

Then re-run the Supabase smoke test above.

