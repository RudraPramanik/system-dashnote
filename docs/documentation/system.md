## DashNoteSystem backend (system workflow & routing)

### Overview

Multi-tenant **Notes backend**: **FastAPI + async SQLAlchemy**. JWT auth builds workspace-aware **`RequestContext`**:

- `user_id` (JWT `sub`)
- `workspace_id` (JWT `wid`)
- `role` (JWT `role`)

All tenant-scoped data flows through repositories filtered by `workspace_id`. JWT details: `src/docs/auth.md`.

### Entry point: `src/main.py`

Registers routers and global dependencies:

| Router | Prefix | Notes |
|--------|--------|-------|
| `core.health` | `/health` | DB + Redis probe |
| `auth/router.py` | `/auth` | Register, login, tokens |
| `files/router.py` | `/files` | Upload, download, metadata; emits `FileUploadedEvent` → worker extracts `extracted_text` |
| `notebooks/router.py` | `/notebooks` | |
| `notes/router.py` | `/notes` | Enqueues embed jobs + emits `NoteCreatedEvent` when `ai_enabled` |
| `workspaces/router.py` | `/workspaces` | |
| `membership/router.py` | `/workspaces/members` | |
| `ai_gateway/search.py` | `/ai` | `GET /ai/test-search` |
| `ai_routes/chat.py` | `/ai` | `POST /ai/chat`, `POST /ai/chat/stream` |
| `ai_routes/threads.py` | `/ai` | Thread list, messages, delete |
| `ai_routes/agent.py` | `/ai` | `POST /ai/agent`, `POST /ai/agent/stream` |

**Middleware:** `ProxyHeadersMiddleware` (trusted `*`) for `X-Forwarded-For`; global `enforce_global_rate_limit` when Redis configured.

**Lifespan:** `setup_logging()` → ARQ pool (`app.state.arq_pool`) → Qdrant collection bootstrap → LangGraph checkpointer init (non-fatal on failure).

**Event bus (Slice 7):** `shared/events/bus.py` — `emit_event()` maps domain events to ARQ automation tasks. Never raises; failures logged only. Routers call `emit_event` after successful DB commit alongside existing Slice 1 embed enqueue.

**Metrics:** `GET /metrics` — Prometheus via `prometheus-fastapi-instrumentator` (`dashnote_api_*`); scraped by Compose `prometheus`, not Nginx.

**Health:** `GET /health` — `SELECT 1` + Redis `PING` when configured. **200** ok / **503** degraded; returns `timestamp`, `latency_ms`, `dependencies`.

### Rate limiting (Nginx + FastAPI)

**Layer 1 — Nginx** (`nginx/default.conf`): host **80** → `api:8000`; `limit_req` 10r/s burst 20; sets `X-Real-IP`, `X-Forwarded-For`, `X-Forwarded-Proto`, `X-Request-ID`.

**Layer 2 — FastAPI** (`core/security/rate_limit.py`): Redis fixed-window counters; keyed by `user_id` (valid JWT) or client IP. Global **100/min**; `POST /auth/login` **5/min**. **429** + `Retry-After`. Fail-open when Redis unset.

### Request lifecycle

1. `POST /auth/login` → `access_token`
2. Protected routes: `Authorization: Bearer <token>`
3. `get_current_context` → `RequestContext`
4. Router scopes by `ctx.workspace_id`, ownership by `ctx.user_id`, RBAC by `ctx.role` (`require_roles` or entity helpers)
5. Repository → async SQLAlchemy
6. Router → Pydantic response

Injection: `core/security/dependency.py` + `auth/dependency.py` (`oauth2_scheme`). Role-gated: `Depends(require_roles("owner", "admin"))`.

### Core modules (summary)

| Area | Key paths |
|------|-----------|
| DB session | `core/database/session.py` — `get_session()` (API); `AsyncSessionLocal` (worker) |
| Tenant filter | `core/database/utils.py` — `tenant_filter()`; `WorkspaceTenantMixin` in `mixins.py` |
| Security | `core/security/context.py`, `dependency.py`, `permissions.py`, `rate_limit.py` |
| Redis | `core/redis/client.py`, `deps.py` — shared client; JWT state (`auth.md`); cache-aside on notes/notebooks reads |
| Storage | `core/storage/client.py`, `utils.py` — see **Storage system** below |
| Shared utils | `shared/utils/parsers.py` — `FileParsingEngine` (file text extraction; no FastAPI/DB) |

**Redis cache-aside:** keys prefixed with JWT `workspace_id`; notes list variant (`staff` vs `u{user_id}`). Invalidation via generation counters (`app:cache:gen:notes:{wid}`), not key scans. TTL `CACHE_TTL_SECONDS` (default 60). Disabled Redis → cache miss, API unchanged.

### Tenancy & RBAC

- JWT `wid` → `RequestContext.workspace_id`; entities use `workspace_id` column
- Roles: `owner`, `admin`, `member`
- Router: `require_roles(...)`; entity logic: `notes/permissions.py`, `files/permissions.py`

**Notes:** owner/admin CRUD any note; member CRUD own notes, view all public + own private.

**Files:** owner/admin see all; member sees non-private + own (`created_by`).

### Storage system (current implementation)

Bytes in object storage; metadata in PostgreSQL (`files` table: `storage_key`, `mime_type`, `extracted_text`, `summary`, `tags`).

- `get_storage()` — `STORAGE_BACKEND`: `local`, `minio`, or `r2`
- Local: `LOCAL_STORAGE_PATH` (default `storage`); no presigned URL → app download route
- **Compose local dev:** `api` + `worker` share volume `local_storage:/app/storage` so worker can read uploaded bytes
- MinIO/R2: S3-compatible via `aioboto3`/`boto3` (no shared volume needed)
- Upload validation: `core/storage/utils.py` (MIME sniff, size, extensions)
- Note attachments: `core/database/associations.py` (`note_attachments` only — no cross-package imports)

### AI features

All AI module layout, RBAC filters, HTTP contracts, and agent laws: **`src/docs/ai.md`**. Import/modification laws: **`src/docs/rules.md`**.

Surface summary: embeddings → Qdrant (`notes_chunks`, `files_chunks`); file upload → text extraction → `extracted_text` (7.2) → fan-out indexing + metadata (7.3); note create → auto-tagging (7.3); destructive AI automation gated by `AutomationDecisionEngine` (7.4); shared LLM retry/structured layer (7.5); RAG at `/ai/chat*`; threads at `/ai/threads*`; LangGraph agent at `/ai/agent*`. Fast RAG and agent paths coexist.

**Shared LLM layer (7.5):** `shared/llm/` — `acompletion_structured` for automation tasks + governance; `acompletion_with_retry` for agent `call_model`. Transient LLM failures in worker tasks re-raise for ARQ retry; agent maps exhausted retries to **503**.

**Automation governance (7.4):** `worker/automation/decision.py` evaluates ambiguous/destructive AI-initiated actions only. Additive tasks (`generate_note_tags`, `generate_file_metadata`, `index_file_chunks`) skip governance. Blocked actions log `[AUTOMATION_GOVERNANCE_BLOCK]` for monitoring.

### Observability

JSON logs (`observability/logging.py`), Langfuse RAG traces (`observability/tracing.py`), Prometheus `/metrics`, Compose `prometheus` (:9090) + `grafana` (:3001, folder **DashNote**).

**Details:** `src/docs/observe.md` (agent) · `docs/observability.md` (human runbook)

### Operational practices

- JWT claim names (`sub`, `wid`, `role`): single source in `core/security/dependency.py`
- Permission logic in dedicated helpers, not routers
- New tenant entities: `workspace_id` + repository + `tenant_filter`
- File features: bytes in storage, metadata in SQL

### Extending the codebase

New module under `src/<name>/`: `models.py`, `schemas.py`, `repository.py`, `router.py`, permission helper if needed. Auth injection: `src/docs/auth.md`.

### Testing

```powershell
python -m pytest tests/files -q          # files module (mocked storage)
python -m pytest tests/shared/test_parsers.py tests/shared/test_llm_structured.py -q
python -m pytest tests/worker/test_automation_decision.py tests/worker/test_automation_llm_tasks.py -q
python -m pytest tests/ai/test_agent_retry.py -q
python -m pytest tests/core/test_rate_limit.py -q
```

`pytest.ini`: `pythonpath = src`, `asyncio_mode = auto`. Windows dev: conftest stubs `magic` if libmagic missing; Docker uses `libmagic1`.

### Docker Compose

```powershell
docker compose up -d --build    # start
docker compose ps
curl.exe -sS http://127.0.0.1/health
docker compose down             # stop
docker compose down -v          # reset volumes
docker compose run --rm migrate # migrations only
```

**Services:** `nginx` (:80), `api` (:8000 direct), `db` (postgres:16), `redis` (:6379), `worker` (ARQ embed + automation jobs), `qdrant` (:6333), `prometheus` (:9090), `grafana` (:3001), `migrate` (one-shot Alembic).

**Local dev overrides (Compose):** `api` and `worker` get explicit `DATABASE_URL` (local Postgres, not `.env` remote). Both mount `local_storage` for `STORAGE_BACKEND=local`. Worker imports all ORM models at startup (same pattern as `alembic/env.py`).

Prefer **`http://127.0.0.1/`** (port 80) for full Nginx proxy path. After recreating `api`, restart `nginx` if `/health` returns 502.

**File upload smoke test:** register → `POST /files/upload` multipart (`file`, `is_private`, optional `description`). Expect **200** with `id`, `mime_type`, `download_url`. After ~45s, worker should populate `extracted_text`, `summary`, `tags` in DB and index vectors to `files_chunks`.

**Note create smoke test:** `POST /notes/` → after ~45s worker should log `generate_note_tags complete` and populate `notes.tags` in DB.

**Agent smoke test:** `POST /ai/agent` with Bearer token → expect **200** with tool calls, or **503** when LLM quota exhausted (never silent empty response). Full E2E: `python scripts/e2e_agent_test.py`.
