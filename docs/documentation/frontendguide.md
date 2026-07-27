# DashNoteSystem — Frontend Developer Guide

Build a **Next.js** (App Router) client against the DashNoteSystem FastAPI backend. This guide is for humans and AI agents: product map, auth, domain APIs, AI streaming contracts, errors/CORS, and the B-gate checklist.

**This repo is API-only.** The frontend lives in a sibling repo or a future `frontend/` folder. Do not invent backend routes — verify schemas against OpenAPI.

**Related docs**

| Doc | Use when |
|-----|----------|
| [system.md](./system.md) | Routing, request lifecycle, modules |
| [auth.md](./auth.md) | JWT claims, refresh/blacklist, `RequestContext` |
| [ai.md](./ai.md) | AI laws, RAG vs agent, settings |
| [blueprint/goal.md](./blueprint/goal.md) §B | Frontend ship checklist |
| OpenAPI `/docs` | **Normative** request/response field lists |

**Local API base (typical):** `http://127.0.0.1` (Nginx → API) or `http://127.0.0.1:8000` if calling the API container directly.  
**OpenAPI:** `{API_BASE}/docs`

---

## Table of contents

1. [Product overview](#1-product-overview)
2. [Frontend laws](#2-frontend-laws)
3. [Auth & tenancy](#3-auth--tenancy)
4. [Domain API map](#4-domain-api-map)
5. [AI: chat, agent, threads](#5-ai-chat-agent-threads)
6. [Operational UX](#6-operational-ux)
7. [B-gate checklist & demo path](#7-b-gate-checklist--demo-path)
8. [Suggested Next.js layout](#8-suggested-nextjs-layout)

---

## 1. Product overview

DashNoteSystem is a **multi-tenant notes product**:

- Users register into a **workspace** (tenant).
- They create **notes** / **notebooks**, upload **files**, and ask AI about workspace content.
- **Fast RAG chat** answers with citations; a separate **LangGraph agent** can search and create/update notes via tools.
- Background workers embed notes/files for search — UI may see a short **indexing lag**.

```
Next.js (browser) ──Bearer JWT──► Nginx (optional) ──► FastAPI
                                      │
                                      ├── PostgreSQL (metadata)
                                      ├── Redis (tokens, cache, rate limits)
                                      ├── Object storage (file bytes)
                                      └── Worker → Qdrant / LLM (async)
```

| UI area | Primary APIs |
|---------|----------------|
| Auth screens | `/auth/*` |
| Workspace / members | `/workspaces/*`, `/workspaces/members` |
| Notes / notebooks | `/notes`, `/notebooks` |
| Files | `/files` |
| RAG chat | `/ai/chat`, `/ai/chat/stream` |
| Threads sidebar | `/ai/threads*` |
| Agent demo | `/ai/agent`, `/ai/agent/stream` |

---

## 2. Frontend laws

Enforce these in every client integration:

| Law | Rule |
|-----|------|
| OpenAPI wins | Exact JSON fields: use `{API_BASE}/docs`. This guide owns **UX contracts** (SSE, tenancy, errors). |
| Tenancy from JWT | `workspace_id` / `role` come from token claims `wid` / `role`. **Never** send a client-chosen workspace id to override tenancy on notes/files/AI. |
| Bearer on protected routes | `Authorization: Bearer <access_token>` |
| Chat ≠ Agent | Keep `/ai/chat*` and `/ai/agent*` as **two UI modes**. Do not replace one with the other. |
| Citations | Stream **tokens** from `type: "token"`. Render **citations only** from the final `type: "metadata"` event — never parse citations out of token text. |
| Errors visible | Surface `429` (rate limit), `503` (LLM/AI down), and SSE `type: "error"` to the user. |

---

## 3. Auth & tenancy

### 3.1 Token lifecycle

All auth bodies are **JSON** (not OAuth2 form `username`/`password`).

| Method | Path | Auth | Body (summary) | Success |
|--------|------|------|----------------|---------|
| `POST` | `/auth/register` | none | `{ email, password, workspace_name }` | `TokenResponse` |
| `POST` | `/auth/login` | none | `{ email, password }` | `TokenResponse` (stricter rate limit) |
| `POST` | `/auth/refresh` | none | `{ refresh_token }` | new `TokenResponse` (refresh rotated) |
| `POST` | `/auth/logout` | Bearer access | optional `{ refresh_token }` | `204` |

`TokenResponse`:

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer"
}
```

**JWT claims (access):** `sub` (user id), `wid` (workspace id), `role` (`owner` | `admin` | `member`), `jti`, `typ: "access"`, `exp`.

Login picks the user’s **first membership** as default workspace. Register creates user + workspace + membership in one call.

### 3.2 Calling protected APIs

```ts
const res = await fetch(`${API_BASE}/notes`, {
  headers: {
    Authorization: `Bearer ${accessToken}`,
    Accept: "application/json",
  },
});
```

On `401`, try `POST /auth/refresh` with the stored refresh token; on failure, send the user to login. On logout, call `POST /auth/logout` with the access Bearer (and refresh in body when available).

### 3.3 Next.js token storage (guidance)

| Approach | Notes |
|----------|--------|
| Memory + refresh in httpOnly cookie via Route Handler BFF | Stronger XSS posture; more setup |
| `localStorage` / session for tokens | Simple demos; XSS can steal tokens — acceptable only for local/portfolio demos if you accept the risk |

Do **not** put long-lived secrets in `NEXT_PUBLIC_*`. Use `NEXT_PUBLIC_API_BASE_URL` for the API origin only.

### 3.4 RBAC — what the UI should allow

Roles: `owner`, `admin`, `member`. Decode `role` from the access JWT (or a `/workspaces/me` response) for UI affordances. **Server still enforces** — UI hide/disable is UX only.

**Notes**

| Role | Can |
|------|-----|
| `owner` / `admin` | CRUD any note in the workspace |
| `member` | CRUD **own** notes; view all **public** notes + own private |

**Files**

| Role | Can |
|------|-----|
| `owner` / `admin` | See/manage all files; admin list at `GET /files/admin/all` |
| `member` | See non-private + own files (`created_by`); mutate per permission helpers |

---

## 4. Domain API map

Field-level schemas: **OpenAPI**. Below is the UI → route map.

### 4.1 Notes — `/notes`

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/notes/` | List notes (workspace-scoped, RBAC-filtered) |
| `POST` | `/notes/` | Create note `{ title, content, is_private? }` |
| `GET` | `/notes/{note_id}` | Read one |
| `PATCH` | `/notes/{note_id}` | Update fields |
| `DELETE` | `/notes/{note_id}` | Delete (`204`) |

After create/update, the API may enqueue embedding. Treat new notes as **indexing** until RAG finds them (see §6).

### 4.2 Notebooks — `/notebooks`

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/notebooks/` | List |
| `POST` | `/notebooks/` | Create |

### 4.3 Files — `/files`

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/files/upload` | Multipart upload: `file` + form `is_private` (default true), `description` |
| `GET` | `/files/` | List (paginated `items` + `total`) |
| `GET` | `/files/admin/all` | Admin/owner broader list |
| `GET` | `/files/{file_id}` | Metadata (+ `download_url`) |
| `GET` | `/files/{file_id}/download` | Download bytes when no presigned URL |
| `PATCH` | `/files/{file_id}` | Update name / privacy / description |
| `DELETE` | `/files/{file_id}` | Delete |
| `POST` | `/files/{file_id}/attach/{note_id}` | Attach file to note |

Upload example:

```ts
const form = new FormData();
form.append("file", file);
form.append("is_private", "true");
form.append("description", "");

await fetch(`${API_BASE}/files/upload`, {
  method: "POST",
  headers: { Authorization: `Bearer ${accessToken}` },
  // Do not set Content-Type — browser sets multipart boundary
  body: form,
});
```

After upload, workers may extract text and run automation (~tens of seconds). Poll `GET /files/{id}` or refresh the list for updated metadata.

### 4.4 Workspaces & members

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/workspaces/me` | Current workspace |
| `PATCH` | `/workspaces/me` | Update workspace |
| `GET` | `/workspaces/members/` | List members |
| `POST` | `/workspaces/members/` | Add member (role-gated) |
| `PATCH` | `/workspaces/members/{user_id}` | Change role |
| `DELETE` | `/workspaces/members/{user_id}` | Remove member |

### 4.5 Health (optional UI)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | API + DB + Redis; `200` / `503` |

---

## 5. AI: chat, agent, threads

Both **chat** and **agent** MUST remain available as separate modes (tabs/pages).

| Mode | Endpoints | Use for |
|------|-----------|---------|
| Fast RAG | `POST /ai/chat`, `POST /ai/chat/stream` | Quick grounded Q&A + citations |
| Agent | `POST /ai/agent`, `POST /ai/agent/stream` | Multi-step tools (search, create/update notes) |
| Threads | `GET /ai/threads`, `GET /ai/threads/{id}/messages`, `DELETE /ai/threads/{id}` | History sidebar |
| Dev search | `POST /ai/test-search` | Diagnostic retrieval (`{ query_text, limit? }`) — not primary product UI |

All AI routes require Bearer. `workspace_id` / `user_id` / `role` are taken from JWT only.

### 5.1 Chat request / response

**Body** (`ChatRequest`):

```json
{ "message": "What did we decide about pricing?", "thread_id": null }
```

- `message`: 1–2000 chars  
- `thread_id`: optional UUID string to continue a conversation  

**Non-stream** `POST /ai/chat` → `{ answer, citations[], chunks_retrieved, chunks_used, latency_ms, thread_id }`.

**Citation shape** (typical): `{ note_id, chunk_id, title, relevance_score }`.

### 5.2 Chat SSE — `/ai/chat/stream`

Content-Type: `text/event-stream`. Events:

| Event | Shape | UI action |
|-------|--------|-----------|
| token | `{ "type": "token", "content": "..." }` | Append to answer (skip empty) |
| metadata | `{ "type": "metadata", "citations": [...], "chunks_retrieved", "chunks_used", "latency_ms", "thread_id"? }` | Render sources **here only** |
| error | `{ "type": "error", "message": "...", "status_code"? }` | Show error |
| done | literal `data: [DONE]` | Close reader |

**Law:** Never scrape citations from the token text stream.

```ts
async function streamChat(apiBase: string, token: string, message: string, threadId?: string) {
  const response = await fetch(`${apiBase}/ai/chat/stream`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify({ message, thread_id: threadId ?? null }),
  });

  if (!response.ok || !response.body) {
    throw new Error(`Chat stream failed: ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const data = line.slice(6).trim();
      if (data === "[DONE]") return;
      const event = JSON.parse(data);
      if (event.type === "token" && event.content) {
        // appendToAnswer(event.content)
      } else if (event.type === "metadata") {
        // renderCitations(event.citations); persist event.thread_id
      } else if (event.type === "error") {
        // showError(event.message)
      }
    }
  }
}
```

Prefer `fetch` + `ReadableStream` over `EventSource` because this is a **POST** with a JSON body and Bearer header.

### 5.3 Threads

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/ai/threads` | List current user’s active threads in JWT workspace |
| `GET` | `/ai/threads/{thread_id}/messages` | Load messages (up to ~50 recent) |
| `DELETE` | `/ai/threads/{thread_id}` | Soft-delete (`204`); wrong workspace → `404` |

Pass returned `thread_id` back into chat/agent requests to continue. Message objects include `role`, `content`, `citations`.

### 5.4 Agent — `/ai/agent` & `/ai/agent/stream`

**Body:** `{ "message": "...", "thread_id": null }` (same length rules as chat).

**Non-stream** response: `{ answer, thread_id, steps_taken, tool_calls_made }`.

**SSE events:**

| type | Fields | UI |
|------|--------|-----|
| `token` | `content` | Stream assistant text |
| `tool_start` | `tool`, `args` | Show “Running {tool}…” |
| `tool_end` | `tool`, `result` (truncated) | Show tool finished |
| `done` | `thread_id`, `steps_taken` | Finalize |
| `error` | `message` | User-visible error; suggest falling back to chat |
| `[DONE]` | literal | Close stream |

Agent may create/update notes via tools — refresh the notes list after `done` when tools ran. Agent failures often return **503** (`LLM temporarily unavailable`) on the non-stream route.

### 5.5 Chat vs agent UX

- Default product chat → **RAG stream** (citations).
- “Agent” / “Assistant with tools” → **agent stream** (tool timeline + answer).
- Do not hide chat because agent exists.

---

## 6. Operational UX

### 6.1 Indexing lag

After **note create/update** or **file upload**, embedding/automation runs in the worker. RAG/search may miss new content for a short window (often ~30–60s for files/metadata demos).

**UI:** Show an “Indexing…” state on new notes/files; delay or retry RAG; avoid claiming “AI is broken” when vectors are still catching up.

### 6.2 Rate limits (`429`)

- Global API rate limit (per user or IP when Redis is on).
- Stricter limit on `POST /auth/login`.

On `429`, read `Retry-After` when present and show a clear wait message. Do not spin silent retries without backoff.

### 6.3 AI / LLM unavailable (`503`)

AI routes may return `503` when AI is disabled, Qdrant is unset, or the LLM is down. Agent may suggest trying `/ai/chat`. Show a calm, user-visible message (“AI temporarily unavailable — try again shortly”).

Core CRUD (`/notes`, `/files`, `/health` with DB+Redis) can still work when AI is degraded.

### 6.4 CORS & API base URL

```env
# Next.js
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1
```

Backend (production example):

```env
CORS_ORIGINS=["http://localhost:3000","https://app.yourdomain.com"]
```

Local Compose often allows `CORS_ORIGINS=["*"]`. Production **must** list the real frontend origin — otherwise the browser blocks calls even if the API is healthy.

Checklist:

1. Frontend origin matches an entry in `CORS_ORIGINS`.
2. Requests use HTTPS in prod (both app and API).
3. Preflight succeeds for `Authorization` + `Content-Type`.

### 6.5 Streaming through proxies

Chat/agent stream responses set `Cache-Control: no-cache` and `X-Accel-Buffering: no`. If tokens arrive in one burst, check proxy buffering — not only the React state updates.

---

## 7. B-gate checklist & demo path

Aligned with [goal.md](./blueprint/goal.md) §B.

| # | Task | Done when |
|---|------|-----------|
| B1 | Auth: register, login, Bearer on API calls | No CORS errors vs target API |
| B2 | Notes CRUD + file upload UI | Upload → wait → metadata visible |
| B3 | Chat UI: SSE + citations from `metadata` | Grounded answer with sources |
| B4 | Threads sidebar + history | Continue prior conversation |
| B5 | Agent view: `tool_start` / `tool_end` | Multi-step demo works |
| B6 | Error UX: 503 LLM, 429 rate limit | User-visible messages |
| B7 | Frontend deployed with TLS | `https://app.<domain>` |

**Demo path (record this):**

1. Register  
2. Create a note  
3. Upload a file  
4. Ask a RAG question → show citation from `metadata`  
5. Agent creates/updates a note (tool events visible)

---

## 8. Suggested Next.js layout

Optional structure (not required):

```
app/
  (auth)/login/page.tsx
  (auth)/register/page.tsx
  (app)/notes/page.tsx
  (app)/files/page.tsx
  (app)/chat/page.tsx      # RAG stream
  (app)/agent/page.tsx     # tool stream
lib/
  api.ts                   # fetch wrapper + refresh
  sse.ts                   # shared SSE line parser
  auth.ts                  # token get/set
```

Keep chat and agent as separate routes or clearly labeled tabs.

---

## Quick reference — method/path corrections vs older docs

Some older backend docs mention `GET /ai/test-search`. The live router is:

- **`POST /ai/test-search`** with body `{ "query_text": "...", "limit": 5 }`

When in doubt, trust **`/docs`** and `src/*/router.py` over narrative docs.
