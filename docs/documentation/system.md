## DashNoteSystem backend (system workflow & routing)

**Frontend / Next.js integration:** see [frontendguide.md](./frontendguide.md).

### Overview

Multi-tenant **Notes backend**: **FastAPI + async SQLAlchemy**. JWT auth builds workspace-aware **`RequestContext`**:

- `user_id` (JWT `sub`)
- `workspace_id` (JWT `wid`)
- `role` (JWT `role`)

All tenant-scoped data flows through repositories filtered by `workspace_id`. JWT details: [auth.md](./auth.md).

### Entry point: `src/main.py`

Registers routers and global dependencies:

| Router | Prefix | Notes |
|--------|--------|-------|
| `core.health` | `/health`, `/health/ai` | Hard: DB + Redis; soft AI: Qdrant + LLM |
| `auth/router.py` | `/auth` | Register, login, refresh, logout |
| `files/router.py` | `/files` | Upload, download, metadata; emits `FileUploadedEvent` → worker extracts `extracted_text` |
| `notebooks/router.py` | `/notebooks` | |
| `notes/router.py` | `/notes` | Enqueues embed jobs + emits `NoteCreatedEvent` when `ai_enabled` |
| `workspaces/router.py` | `/workspaces` | |
| `membership/router.py` | `/workspaces/members` | |
| `integrations/router.py` | `/integrations` | Inbound email (API key); WhatsApp webhook + JWT link; see [inbound-channels.md](../inbound-channels.md) |
| `ai_gateway/search.py` | `/ai` | **Live** diagnostic: `GET /ai/test-search?q=&limit=` |
| `ai_routes/chat.py` | `/ai` | `POST /ai/chat`, `POST /ai/chat/stream` |
| `ai_routes/threads.py` | `/ai` | Thread list, messages, delete |
| `ai_routes/agent.py` | `/ai` | `POST /ai/agent`, `/ai/agent/stream`, `/ai/agent/resume`, `/ai/agent/reject` (HITL) |

**Not mounted:** `ai_search/router.py` (`POST /ai/test-search`) — present in tree but **not** the live contract. Use `GET /ai/test-search` via `ai_gateway/search.py`.

**No HTTP prefix:** `pages/` — ORM (`Page`, `PageVersion`) used by notebooks / worker model imports only.

**Middleware:** `CORSMiddleware` (`settings.CORS_ORIGINS`); `ProxyHeadersMiddleware` (trusted `*`) for `X-Forwarded-For`; global `enforce_global_rate_limit` when Redis configured.

**Lifespan:** `setup_logging()` → `configure_litellm_env` + `resolve_llm_model` (non-fatal) → ARQ pool → Qdrant collection bootstrap (non-fatal) → LangGraph checkpointer init (non-fatal).

**Soft dependency boot (7P.3):** When `settings.qdrant_enabled`, `main.py` and `worker/main.py` call `ensure_notes_collection()` / `ensure_files_collection()` inside try/except. Failure logs `ERROR` and startup continues — `/health`, `/notes`, `/files` still work; `/ai/*` and indexing degrade until Qdrant is reachable. Redis and Postgres remain hard deps (`GET /health` gate).

**Event bus (Slice 7):** `shared/events/bus.py` — `emit_event()` maps domain events to ARQ automation tasks. Never raises; failures logged only. Routers call `emit_event` after successful DB commit alongside existing Slice 1 embed enqueue.

**Metrics:** `GET /metrics` — Prometheus via `prometheus-fastapi-instrumentator` (`dashnote_api_*`); scraped by Compose `prometheus`, not Nginx.

**Health:**

| Route | Gate | Status labels | Probes |
|-------|------|---------------|--------|
| `GET /health` | **Hard** (deploy/smoke) | `ok` / `unavailable` (**503**) | Postgres `SELECT 1` + Redis `PING` when configured |
| `GET /health/ai` | **Soft** (never hard gate) | `ok` / `degraded` | Qdrant (when enabled) + LLM candidate resolve |

Returns `timestamp`, `latency_ms`, `dependencies`. Qdrant/LLM never fail hard `/health`.

### Rate limiting (Nginx + FastAPI)

**Layer 1 — Nginx** (`nginx/default.conf`): host **80** → `api:8000`; `limit_req` 10r/s burst 20; dedicated `location /ai/` with `proxy_buffering off` and 180s read/send timeouts; sets `X-Real-IP`, `X-Forwarded-For`, `X-Forwarded-Proto`, `X-Request-ID`.

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
| Redis | `core/redis/client.py`, `deps.py` — shared client; JWT state ([auth.md](./auth.md)); cache-aside on notes/notebooks reads |
| Storage | `core/storage/client.py`, `utils.py` — see **Storage system** below |
| Integrations | `integrations/` — inbound email + WhatsApp; details [inbound-channels.md](../inbound-channels.md) |
| Pages (ORM) | `pages/models.py` — no router |
| Shared utils | `shared/utils/parsers.py` — `FileParsingEngine` (file text extraction; no FastAPI/DB) |

**Redis cache-aside:** keys prefixed with JWT `workspace_id`; notes list variant (`staff` vs `u{user_id}`). Invalidation via generation counters (`app:cache:gen:notes:{wid}`), not key scans. TTL `CACHE_TTL_SECONDS` (default 60). Disabled Redis → cache miss, API unchanged.

### Tenancy & RBAC

- JWT `wid` → `RequestContext.workspace_id`; entities use `workspace_id` column
- Roles: `owner`, `admin`, `member`
- Router: `require_roles(...)`; entity logic: `notes/permissions.py`, `files/permissions.py`

**Notes:** owner/admin CRUD any note; member CRUD own notes, view all public + own private.

**Files:** owner/admin see all; member sees non-private + own (`created_by`).

**Integrations:** WhatsApp link start/confirm/unlink use JWT `RequestContext`. Inbound email uses `X-Inbound-Api-Key` (+ optional HMAC), not user Bearer. WhatsApp webhook uses Meta signature verification.

### Storage system (current implementation)

Bytes in object storage; metadata in PostgreSQL (`files` table: `storage_key`, `mime_type`, `extracted_text`, `summary`, `tags`).

- `get_storage()` — `STORAGE_BACKEND`: `local`, `minio`, or `r2`
- Local: `LOCAL_STORAGE_PATH` (default `storage`); no presigned URL → app download route
- **Compose local dev:** `api` + `worker` share volume `local_storage:/app/storage` so worker can read uploaded bytes
- MinIO/R2: S3-compatible via `aioboto3`/`boto3` (no shared volume needed)
- Upload validation: `core/storage/utils.py` (MIME sniff, size, extensions)
- Note attachments: `core/database/associations.py` (`note_attachments` only — no cross-package imports)

### AI features

All AI module layout, RBAC filters, HTTP contracts, and agent laws: **[ai.md](./ai.md)**. Import/modification laws: **[rules.md](./rules.md)**.

Surface summary: embeddings → Qdrant (`notes_chunks`, `files_chunks`); file upload → text extraction → `extracted_text` (7.2) → fan-out indexing + metadata (7.3); note create → auto-tagging (7.3); destructive AI automation gated by `AutomationDecisionEngine` (7.4); shared LLM retry/structured/fallback layer (7.5+); RAG at `/ai/chat*`; threads at `/ai/threads*`; LangGraph agent at `/ai/agent*` with HITL resume/reject. Fast RAG and agent paths coexist. Soft readiness: `GET /health/ai`.

**Shared LLM layer (7.5+):** `shared/llm/` — `acompletion_structured` for automation + governance; `acompletion_with_retry` / `acompletion_with_fallback` for chat/agent (wall-clock candidate walk). Transient LLM failures in worker tasks re-raise for ARQ retry; agent maps exhaustion to **503**.

**Automation governance (7.4):** `worker/automation/decision.py` evaluates ambiguous/destructive AI-initiated actions only. Additive tasks (`generate_note_tags`, `generate_file_metadata`, `index_file_chunks`) skip governance. Blocked actions log `[AUTOMATION_GOVERNANCE_BLOCK]` for monitoring.

### Observability

JSON logs (`observability/logging.py`), Langfuse RAG traces (`observability/tracing.py`), Prometheus `/metrics`, Compose `prometheus` (:9090). Grafana is **not** a default local Compose service; use Grafana Cloud / leftover `monitoring/grafana/` provisioning when needed.

**Details:** [observe.md](./observe.md) (agent) · [observability.md](../observability.md) (human runbook)

### Operational practices

- JWT claim names (`sub`, `wid`, `role`): single source in `core/security/dependency.py`
- Permission logic in dedicated helpers, not routers
- New tenant entities: `workspace_id` + repository + `tenant_filter`
- File features: bytes in storage, metadata in SQL

### Extending the codebase

New module under `src/<name>/`: `models.py`, `schemas.py`, `repository.py`, `router.py`, permission helper if needed. Auth injection: [auth.md](./auth.md).

### Testing

```powershell
python -m pytest tests/files -q          # files module (mocked storage)
python -m pytest tests/shared/test_parsers.py tests/shared/test_llm_structured.py -q
python -m pytest tests/worker/test_automation_decision.py tests/worker/test_automation_llm_tasks.py -q
python -m pytest tests/ai/test_agent_retry.py tests/ai/test_agent_hitl.py -q
python -m pytest tests/core/test_rate_limit.py -q
```

`pytest.ini`: `pythonpath = src`, `asyncio_mode = auto`. Windows dev: conftest stubs `magic` if libmagic missing; Docker uses `libmagic1`.

### Docker Compose

Two compose files — dev stack vs VPS profile. See `.env.production.example` for hosted URLs.

**Local (full stack)** — `docker-compose.yml`:

```powershell
docker compose up -d --build    # start
docker compose ps
curl.exe -sS http://127.0.0.1/health
curl.exe -sS http://127.0.0.1/health/ai
docker compose down             # stop
docker compose down -v          # reset volumes
docker compose run --rm migrate # migrations only
```

**Production (VPS — hosted db/redis/qdrant in `.env`)** — `docker-compose.prod.yml`:

```powershell
docker compose -f docker-compose.prod.yml run --rm migrate
docker compose -f docker-compose.prod.yml up -d
# Optional metrics → Grafana Cloud:
docker compose -f docker-compose.prod.yml --profile observability up -d
```

**Dev services:** `nginx` (:80), `api` (:8000 direct), `db` (postgres:16), `redis` (:6379), `worker` (ARQ embed + automation jobs), `qdrant` (:6333), `prometheus` (:9090), `migrate` (one-shot Alembic). **No** local Grafana container.

**Prod services:** `nginx` (:80), `api` (expose 8000 only — nginx fronts traffic), `worker`, `migrate` (run separately), optional `prometheus` (`--profile observability`). No local `db`, `redis`, or `qdrant` containers.

**Local dev overrides (Compose):** `api` and `worker` get explicit `DATABASE_URL` (local Postgres, not `.env` remote). Both mount `local_storage` for `STORAGE_BACKEND=local`. Worker imports all ORM models at startup (same pattern as `alembic/env.py`). Production compose uses `env_file: .env` only (plus `DEBUG=false`); no shared storage volume — use `STORAGE_BACKEND=r2`.

Prefer **`http://127.0.0.1/`** (port 80) for full Nginx proxy path. After recreating `api`, restart `nginx` if `/health` returns 502.

**File upload smoke test:** register → `POST /files/upload` multipart (`file`, `is_private`, optional `description`). Expect **200** with `id`, `mime_type`, `download_url`. After ~45s, worker should populate `extracted_text`, `summary`, `tags` in DB and index vectors to `files_chunks`.

**Note create smoke test:** `POST /notes/` → after ~45s worker should log `generate_note_tags complete` and populate `notes.tags` in DB.

**Agent smoke test:** `POST /ai/agent` with Bearer token → expect **200** with tool calls, or **503** when LLM quota exhausted (never silent empty response). Mutation tools may return `approval_required` → `POST /ai/agent/resume` or `/reject`. Full E2E: `python scripts/e2e_agent_test.py`.

### Dependency tiers & deploy profiles

| Tier | Services | Deploy gate |
|------|----------|-------------|
| **Hard** | Postgres, Redis | `/health` must return 200 |
| **Soft** | Qdrant, LLM providers | App boots; AI/automation degrades; probe via `/health/ai` |
| **Optional** | Langfuse, LangSmith, Grafana Cloud remote_write | Never block startup or CD |

**Dev (full stack):** `docker compose up` — includes `db`, `redis`, `qdrant`, `api`, `worker`, `nginx`, `prometheus` on the local machine.

**Prod (VPS / hosted services):** `docker compose -f docker-compose.prod.yml up` — `nginx`, `api`, `worker`, `migrate`, optional `prometheus` only; Postgres, Redis, and Qdrant come from `.env` (see `.env.production.example`).
