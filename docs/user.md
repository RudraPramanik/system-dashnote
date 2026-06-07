# DashNoteSystem — Insomnia API Testing Guide

Hands-on guide for testing the DashNoteSystem API in [Insomnia](https://insomnia.rest/). Covers auth, notes, files, workspaces, and AI endpoints.

**Related docs:** [system.md](documentation/system.md) · [ai.md](documentation/ai.md)

---

## 1. Before you start

### Start the stack

```powershell
docker compose up -d --build
curl.exe -sS http://127.0.0.1/health
```

Use **`http://127.0.0.1`** (port 80, through Nginx). Direct API on `:8000` skips the proxy path.

### AI prerequisites

AI routes need these in `.env`:

| Variable | Purpose |
|----------|---------|
| `GEMINI_API_KEY` or `OPENAI_API_KEY` | Enables `ai_enabled` |
| `QDRANT_URL` | Enables vector search (`qdrant_enabled`) |
| `REDIS_URL` | ARQ worker queues embed jobs |

After creating or updating a note, the **worker** indexes embeddings (usually a few seconds). Wait before calling `GET /ai/test-search` or chat.

### Roles (from JWT)

| Role | Notes | Files | Members | Notebooks |
|------|-------|-------|---------|-----------|
| `owner` | Full CRUD | Full | Invite, remove, change roles | Create |
| `admin` | Full CRUD | Full | Invite, remove | Create |
| `member` | Own notes + view public | Own + non-private | List only | List only |

Register creates the first user as **`owner`** of a new workspace.

---

## 2. Insomnia setup

### Environment

Create an environment (e.g. **Local**) with:

| Variable | Example | Notes |
|----------|---------|-------|
| `base_url` | `http://127.0.0.1` | No trailing slash |
| `access_token` | *(empty)* | Set after login/register |
| `refresh_token` | *(empty)* | Set after login/register |
| `note_id` | *(empty)* | Copy from create-note response |
| `file_id` | *(empty)* | Copy from upload response |
| `thread_id` | *(empty)* | Copy from chat/agent response |

Use `{{ base_url }}` in request URLs, e.g. `{{ base_url }}/auth/login`.

### Auth on protected routes

For any route except `/health`, `/auth/register`, `/auth/login`, `/auth/refresh`:

- **Auth type:** Bearer Token  
- **Token:** `{{ access_token }}`

Or add header manually:

```
Authorization: Bearer {{ access_token }}
```

### Auto-save tokens (optional)

On **Register** and **Login** requests, open the **Scripts** tab → **After-response**:

```javascript
const body = JSON.parse(insomnia.response.getBody());
if (body.access_token) insomnia.environment.set('access_token', body.access_token);
if (body.refresh_token) insomnia.environment.set('refresh_token', body.refresh_token);
```

### Suggested folder layout

```
DashNoteSystem/
├── 00 — Health
├── 01 — Auth
├── 02 — Workspace & Members
├── 03 — Notebooks
├── 04 — Notes
├── 05 — Files
└── 06 — AI
```

### OpenAPI import (DEBUG only)

When `DEBUG=true`, import `{{ base_url }}/openapi.json` into Insomnia for auto-generated requests. This guide stays the source of truth for test order and expected behavior.

---

## 3. Recommended test flow

Run requests in this order for a full smoke test.

```
1. GET  /health
2. POST /auth/register          → save tokens
3. GET  /workspaces/me
4. POST /notebooks/             → owner/admin only
5. POST /notes/                 → save note_id
6. POST /files/upload           → save file_id (multipart)
7. POST /files/{file_id}/attach/{note_id}
8. GET  /ai/test-search?q=...   → wait ~5–10s after step 5
9. POST /ai/chat
10. POST /ai/chat               → same thread_id from step 9
11. GET  /ai/threads
12. GET  /ai/threads/{thread_id}/messages
13. POST /ai/agent
14. POST /auth/logout
```

---

## 4. Endpoints reference

### 00 — Health

#### `GET /health`

No auth.

**Expect:** `200` when DB (+ Redis if configured) are up; `503` if degraded.

```json
{
  "status": "ok",
  "timestamp": "2026-06-07T12:00:00+00:00",
  "latency_ms": 2.5,
  "dependencies": {
    "database": { "reachable": true },
    "redis": { "reachable": true, "configured": true }
  }
}
```

---

### 01 — Auth

All bodies: **JSON** (`Content-Type: application/json`).

#### `POST /auth/register`

Creates user + workspace. Caller becomes **owner**.

```json
{
  "email": "tester@example.com",
  "password": "SecurePass123!",
  "workspace_name": "My Test Workspace"
}
```

**Expect:** `200`

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

**Errors:** `400` — email taken or validation failure.

---

#### `POST /auth/login`

Rate-limited: **5 requests/min** per IP.

```json
{
  "email": "tester@example.com",
  "password": "SecurePass123!"
}
```

**Expect:** `200` — same shape as register.  
**Errors:** `401` invalid credentials; `429` rate limit (+ `Retry-After` header).

---

#### `POST /auth/refresh`

```json
{
  "refresh_token": "{{ refresh_token }}"
}
```

**Expect:** `200` — new `access_token` and `refresh_token` (old refresh is revoked).  
**Errors:** `401` invalid or revoked refresh.

---

#### `POST /auth/logout`

**Auth:** Bearer `{{ access_token }}`

```json
{
  "refresh_token": "{{ refresh_token }}"
}
```

Body is optional; include `refresh_token` to revoke both tokens.

**Expect:** `204` No Content.

---

### 02 — Workspace & Members

#### `GET /workspaces/me`

**Auth:** Bearer

**Expect:** `200`

```json
{
  "id": 1,
  "name": "My Test Workspace"
}
```

---

#### `PATCH /workspaces/me`

**Auth:** Bearer · **Roles:** `owner`, `admin`

```json
{
  "name": "Renamed Workspace"
}
```

**Expect:** `200` — updated workspace.  
**Errors:** `403` if `member`.

---

#### `GET /workspaces/members/`

**Auth:** Bearer

**Expect:** `200`

```json
[
  {
    "user_id": 1,
    "email": "tester@example.com",
    "role": "owner"
  }
]
```

---

#### `POST /workspaces/members/`

**Auth:** Bearer · **Roles:** `owner`, `admin`

Invite an **existing** user (they must register first).

```json
{
  "email": "member@example.com",
  "role": "member"
}
```

`role`: `"member"` or `"admin"`.

**Expect:** `200` — `MemberRead`.  
**Errors:** `400` if user not found or already a member.

---

#### `PATCH /workspaces/members/{user_id}`

**Auth:** Bearer · **Roles:** `owner` only

```json
{
  "role": "admin"
}
```

**Expect:** `200`.

---

#### `DELETE /workspaces/members/{user_id}`

**Auth:** Bearer · **Roles:** `owner`, `admin`

**Expect:** `204`.

---

### 03 — Notebooks

#### `GET /notebooks/`

**Auth:** Bearer

**Expect:** `200` — array of `{ "id", "name" }`.

---

#### `POST /notebooks/`

**Auth:** Bearer · **Roles:** `owner`, `admin`

```json
{
  "name": "Project Alpha"
}
```

**Expect:** `200`.  
**Errors:** `403` if `member`.

---

### 04 — Notes

#### `GET /notes/`

**Auth:** Bearer

**Expect:** `200` — array of notes visible to your role.

```json
[
  {
    "id": 1,
    "title": "Meeting notes",
    "content": "Discussed Q3 roadmap...",
    "is_private": false,
    "created_by": 1
  }
]
```

---

#### `POST /notes/`

**Auth:** Bearer

```json
{
  "title": "Meeting notes",
  "content": "Discussed Q3 roadmap and budget allocation for engineering.",
  "is_private": false
}
```

**Expect:** `200` — save `id` as `{{ note_id }}`.

When AI is enabled, this enqueues an embed job. Wait a few seconds before search/chat.

---

#### `GET /notes/{note_id}`

**Auth:** Bearer

**Expect:** `200` single note; `404` not found; `403` no permission (private note owned by someone else).

---

#### `PATCH /notes/{note_id}`

**Auth:** Bearer · must own note (or be owner/admin)

```json
{
  "title": "Updated title",
  "content": "Updated content with more detail.",
  "is_private": true
}
```

All fields optional — send only what you change.

**Expect:** `200`. Re-indexes vectors when AI enabled.

---

#### `DELETE /notes/{note_id}`

**Auth:** Bearer

**Expect:** `204`. Removes vectors when AI enabled.

---

### 05 — Files

#### `POST /files/upload`

**Auth:** Bearer  
**Body:** **Multipart Form** (not JSON)

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `file` | File | Yes | — |
| `is_private` | Text (`true`/`false`) | No | `true` |
| `description` | Text | No | `""` |

**Allowed:** PDF, Word, Excel, PowerPoint, `.txt`, `.csv` — max **1 MB**.

In Insomnia: Body → **Multipart Form** → add `file` as File, `is_private` as Text `false`.

**Expect:** `200`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "workspace_id": 1,
  "created_by": 1,
  "name": "report.pdf",
  "mime_type": "application/pdf",
  "size_bytes": 12345,
  "is_private": false,
  "download_url": "/files/550e8400-e29b-41d4-a716-446655440000/download",
  "created_at": "...",
  "updated_at": "..."
}
```

Save `id` as `{{ file_id }}`.

---

#### `GET /files/`

**Auth:** Bearer

**Query params:** `skip` (default 0), `limit` (default 20)

**Expect:** `200` — `{ "items", "total", "skip", "limit" }`.

---

#### `GET /files/admin/all`

**Auth:** Bearer · **Roles:** `owner`, `admin`

Same query params as list. Returns all workspace files.

---

#### `GET /files/{file_id}`

**Auth:** Bearer

**Expect:** `200` metadata + `download_url`.

---

#### `GET /files/{file_id}/download`

**Auth:** Bearer

**Expect:** `200` — raw file bytes (attachment). In Insomnia, use **Send and Download**.

---

#### `PATCH /files/{file_id}`

**Auth:** Bearer · must own file (or owner/admin)

```json
{
  "name": "renamed.pdf",
  "is_private": true,
  "description": "Q3 report"
}
```

**Expect:** `200`.

---

#### `DELETE /files/{file_id}`

**Auth:** Bearer

**Expect:** `204`.

---

#### `POST /files/{file_id}/attach/{note_id}`

**Auth:** Bearer · must manage both file and note

**Expect:** `200` — `{ "attached": true }`.

---

### 06 — AI

All AI routes require **Bearer** auth. `workspace_id` always comes from the JWT — never send it in query or body.

#### `GET /ai/test-search`

Semantic search validation (engineering / QA).

**Query params:**

| Param | Rule | Default |
|-------|------|---------|
| `q` | 1–500 chars | required |
| `limit` | 1–20 | `5` |

Example: `{{ base_url }}/ai/test-search?q=roadmap&limit=5`

**Expect:** `200` — array of chunks with scores.

```json
[
  {
    "chunk_id": "abc-123",
    "note_id": "1",
    "title": "Meeting notes",
    "chunk_text": "Discussed Q3 roadmap...",
    "score": 0.72,
    "visibility": "public",
    "chunk_index": 0,
    "workspace_id": "1"
  }
]
```

**Quality check:** relevant matches usually have `score` > **0.4**.

**Errors:** `503` — AI disabled or Qdrant not configured; `401` — no/invalid token.

---

#### `POST /ai/chat`

Fast RAG — single-shot Q&A grounded in your notes.

```json
{
  "message": "What did we discuss about the Q3 roadmap?",
  "thread_id": null
}
```

Omit `thread_id` or set `null` for a new conversation. Reuse `thread_id` from the response to continue.

**Expect:** `200`

```json
{
  "answer": "Based on your notes...",
  "citations": [
    {
      "note_id": "1",
      "chunk_id": "abc-123",
      "title": "Meeting notes",
      "relevance_score": 0.72
    }
  ],
  "chunks_retrieved": 5,
  "chunks_used": 3,
  "latency_ms": 1250.5,
  "thread_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
}
```

Save `thread_id` as `{{ thread_id }}`.

**Errors:** `400` — bad `thread_id` (wrong workspace); `401` — auth.

---

#### `POST /ai/chat/stream`

Same body as `/ai/chat`. Response is **Server-Sent Events** (`text/event-stream`).

**Insomnia:** Response shows raw SSE lines. Look for:

```
data: {"type":"token","content":"Based"}
data: {"type":"token","content":" on"}
data: {"type":"metadata","citations":[...],"latency_ms":1200,"thread_id":"..."}
data: [DONE]
```

Citations appear only in the final `metadata` event, not in token events.

---

#### `GET /ai/threads`

**Expect:** `200` — list of your conversation threads in the current workspace.

```json
[
  {
    "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "workspace_id": "1",
    "created_by": "1",
    "title": null,
    "is_active": true,
    "created_at": "2026-06-07T12:00:00",
    "updated_at": "2026-06-07T12:05:00"
  }
]
```

---

#### `GET /ai/threads/{thread_id}/messages`

**Expect:** `200` — up to 50 messages; `404` if thread not in your workspace.

```json
[
  {
    "id": "...",
    "thread_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "role": "user",
    "content": "What did we discuss?",
    "citations": [],
    "token_count": null,
    "created_at": "..."
  },
  {
    "id": "...",
    "role": "assistant",
    "content": "Based on your notes...",
    "citations": [{ "note_id": "1", "chunk_id": "...", "title": "...", "relevance_score": 0.7 }],
    "token_count": 150,
    "created_at": "..."
  }
]
```

---

#### `DELETE /ai/threads/{thread_id}`

Soft-deletes the thread (`is_active=false`).

**Expect:** `204`; `404` if not found.

---

#### `POST /ai/agent`

LangGraph agent with tools (search, create/update notes, summarize workspace). Slower than chat; can mutate notes.

```json
{
  "message": "Create a note summarizing our Q3 roadmap discussion",
  "thread_id": null
}
```

**Expect:** `200`

```json
{
  "answer": "I've created a note titled...",
  "thread_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "steps_taken": 3,
  "tool_calls_made": 2
}
```

**Errors:** `503` — checkpointer/graph unavailable; `500` — agent error (try `/ai/chat` as fallback).

---

#### `POST /ai/agent/stream`

Same body as `/ai/agent`. SSE events:

| `type` | Meaning |
|--------|---------|
| `token` | LLM text chunk |
| `tool_start` | Tool invoked (`tool`, `args`) |
| `tool_end` | Tool result (truncated to 200 chars) |
| `done` | Finished (`thread_id`, `steps_taken`) |
| `error` | Failure message |

Ends with `data: [DONE]`.

---

## 5. Multi-user RBAC spot checks

Use two Insomnia environments or two users:

1. **Owner** registers → creates a **public** note and a **private** note.
2. **Member** registers separately (new workspace) OR owner invites member (same workspace).
3. As **member** in shared workspace:
   - `GET /notes/` — sees public notes + own notes only.
   - `GET /notes/{private_owner_note_id}` — expect `403`.
   - `GET /ai/test-search?q=...` — private owner notes must not appear in results.
4. As **owner** — sees all notes and all search results in workspace.

---

## 6. Status codes cheat sheet

| Code | When |
|------|------|
| `200` | Success (JSON body) |
| `204` | Success (no body) — delete, logout |
| `400` | Validation / bad input / bad thread_id |
| `401` | Missing or invalid token |
| `403` | Authenticated but wrong role or note/file permission |
| `404` | Resource not found (or hidden for security on threads) |
| `413` | File too large (> 1 MB) |
| `415` | Unsupported file type |
| `429` | Rate limit (global 100/min; login 5/min) |
| `503` | Health degraded, AI disabled, or Qdrant unavailable |
| `500` | Server error |

Global rate limit: **100 requests/min** per user (JWT) or IP when Redis is configured.

---

## 7. Troubleshooting

| Problem | Fix |
|---------|-----|
| `502` on `/health` | `docker compose restart nginx` after API container recreate |
| `503` on `/ai/test-search` | Set `GEMINI_API_KEY` or `OPENAI_API_KEY` and `QDRANT_URL`; restart `api` + `worker` |
| Empty search results | Wait for worker after note create; use words that appear in note content; check `docker compose logs worker` |
| `401` after logout | Login again; access token was blacklisted |
| Chat returns generic answer, no citations | No indexed notes match query; create notes with relevant content first |
| File upload `415` | Use allowed types (PDF, Office, txt, csv); extension must match content |
| SSE shows one big blob | Normal in Insomnia; tokens are still separated by `data:` lines. Use curl or a browser EventSource for live streaming |
| `429` on login | Wait for `Retry-After` seconds; use register once, then reuse token |

### Quick worker check

```powershell
docker compose logs worker --tail 30
```

Look for `embed_note_task` completing without errors after `POST /notes/`.

---

## 8. Copy-paste curl equivalents

Useful when Insomnia behaves differently from the real proxy path.

```powershell
# Health
curl.exe -sS http://127.0.0.1/health

# Register
curl.exe -sS -X POST http://127.0.0.1/auth/register `
  -H "Content-Type: application/json" `
  -d '{"email":"test@example.com","password":"Pass123!","workspace_name":"Test WS"}'

# Chat (replace TOKEN)
curl.exe -sS -X POST http://127.0.0.1/ai/chat `
  -H "Authorization: Bearer TOKEN" `
  -H "Content-Type: application/json" `
  -d '{"message":"Summarize my notes"}'
```

---

*Last updated for DashNoteSystem slices 1–6 (embeddings, RAG chat, threads, LangGraph agent).*
