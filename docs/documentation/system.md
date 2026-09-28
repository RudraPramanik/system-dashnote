## DashNoteSystem backend (system workflow & routing)

**Frontend / Next.js integration:** see [frontendguide.md](./frontendguide.md).

### Overview

Multi-tenant **Notes backend**: **FastAPI + async SQLAlchemy**. JWT auth builds workspace-aware **`RequestContext`**:

- `user_id` (JWT `sub`)
- `workspace_id` (JWT `wid`)
- `role` (JWT `role`)

All tenant-scoped data flows through repositories filtered by `workspace_id`. JWT details: [auth.md](./auth.md).

### Production platform (as of 2026-09-28)

Thin **AWS EC2** compute + hosted data plane. App code is unchanged between local Compose and prod; only env URLs and compose file differ.

```
Browser / FE
   │  HTTPS
   ▼
Cloudflare (DNS + browser TLS; SSL mode Full)
   │  HTTPS :443 → origin (self-signed OK for Full, not Full strict)
   ▼
EC2 t3.small (Terraform Level A: instance + SG)
   nginx :80/:443  →  api :8000 (unpublished)  +  ARQ worker  +  migrate oneshot
   │
   └── .env URLs only ──► Hosted Postgres · Redis (cache + ARQ) · Qdrant Cloud · R2
                          LLM via LiteLLM (NIM / Gemini today; Bedrock deferred)
```

| Surface | Status | Notes |
|---------|--------|-------|
| `https://api.aisystem.world` | **Live (A7)** | Health 200 + `smoke_prod.py` HARD GATE PASS |
| HTTP-on-IP first-boot | Proven (A4) | Operator evidence; not the stranger-facing demo URL |
| CD | **Green** | `workflow_dispatch` / tags `v*` → GHCR → SSH migrate/roll → smoke; **not** on every merge |
| Terraform Level A | **Live** | EC2 + SG (+ optional EIP) in `infra/`; remote state. Level B/C not started |
| Apex FE (`aisystem.world`) | **Not this VPS** | CORS already allows `https://aisystem.world`; host elsewhere |
| Bedrock | Deferred | Keep LangGraph; swap model provider via LiteLLM after FE path is honest |

| On VPS | Off VPS (hosted) |
|--------|------------------|
| `nginx`, `api`, `worker`, `migrate`; optional `prometheus` (`--profile observability`, off by default) | Postgres (Supabase pooler), Redis (Upstash cache + Redis Cloud ARQ), Qdrant Cloud, R2 |
| Secrets in VPS `.env` + GitHub deploy secrets | Never commit prod credentials |

**Ops sources of truth:** [devops-progress.md](../devops-progress.md) (phase / next) · [deployment/runbook.md](../deployment/runbook.md) (commands) · [deployment/edge-aisystem.md](../deployment/edge-aisystem.md) (Cloudflare edge) · [deployment/terraform-a.md](../deployment/terraform-a.md) (IaC) · [production.md](./production.md) (7P engineering) · [deployment/storage.md](../deployment/storage.md) (R2).

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
| `ai_routes/threads.py` | `/ai` | Thread list, messages, `PATCH /ai/threads/{thread_id}` rename, delete |
| `ai_routes/agent.py` | `/ai` | `POST /ai/agent`, `/ai/agent/stream`, `/ai/agent/resume`, `/ai/agent/reject` (HITL) |
| `ai_routes/feedback.py` | `/ai` | `POST /ai/feedback` — JWT `wid` only; thumbs or 1–5; chat/agent turns do **not** require it |

**Not mounted:** `ai_search/router.py` (`POST /ai/test-search`) — present in tree but **not** the live contract. Use `GET /ai/test-search` via `ai_gateway/search.py`.

**No HTTP prefix:** `pages/` — ORM (`Page`, `PageVersion`) used by notebooks / worker model imports only.

**Middleware:** `CORSMiddleware` (`settings.CORS_ORIGINS`); `ProxyHeadersMiddleware` (trusted `*`) for `X-Forwarded-For`; global `enforce_global_rate_limit` when Redis configured.

**Lifespan:** `setup_logging()` → `configure_litellm_env` + `resolve_llm_model` (non-fatal) → ARQ pool → Qdrant collection bootstrap (non-fatal) → LangGraph checkpointer init (non-fatal).

**Soft dependency boot (7P.3):** When `settings.qdrant_enabled`, `main.py` and `worker/main.py` call `ensure_notes_collection()` / `ensure_files_collection()` inside try/except. Failure logs `ERROR` and startup continues — `/health`, `/notes`, `/files` still work; `/ai/*` and indexing degrade until Qdrant is reachable. Redis and Postgres remain hard deps (`GET /health` gate).

**Event bus (Slice 7):** `shared/events/bus.py` — `emit_event()` maps domain events to ARQ automation tasks. Never raises; failures logged only. Routers call `emit_event` after successful DB commit alongside existing Slice 1 embed enqueue.

**Metrics:** `GET /metrics` — Prometheus via `prometheus-fastapi-instrumentator` (`dashnote_api_*` HTTP series) plus low-cardinality AI quality counters (`dashnote_ai_*`). Scraped by Compose `prometheus`, not Nginx. **Not** a production SLO and **not** the hard `/health` gate.

**Health:**

| Route | Gate | Status labels | Probes |
|-------|------|---------------|--------|
| `GET /health` | **Hard** (deploy/smoke) | `ok` / `unavailable` (**503**) | Postgres `SELECT 1` + Redis `PING` when configured |
| `GET /health/ai` | **Soft** (never hard gate) | `ok` / `degraded` | Qdrant (when enabled) + LLM candidate resolve |

Returns `timestamp`, `latency_ms`, `dependencies`. Qdrant/LLM never fail hard `/health`.

### Rate limiting (Nginx + FastAPI)

**Layer 1 — Nginx** (`nginx/default.conf`): proxies to `api:8000` (Docker DNS `resolve` so recreates do not stale-502). `limit_req` 10r/s burst 20; dedicated `location /ai/` with `proxy_buffering off` and 180s read/send timeouts; sets `X-Real-IP`, `X-Forwarded-For`, `X-Forwarded-Proto`, `X-Request-ID`.

- **Local / HTTP:** `listen 80`
- **Prod origin TLS:** also `listen 443 ssl` for `api.aisystem.world` — certs under `nginx/certs/` (gitignored). Cloudflare Full terminates browser TLS; origin self-signed is enough for Full, not Full strict. See [edge-aisystem.md](../deployment/edge-aisystem.md).

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

Surface summary: embeddings → Qdrant (`notes_chunks`, `files_chunks`); file upload → text extraction → `extracted_text` (7.2) → fan-out indexing + metadata (7.3); note create → auto-tagging (7.3); destructive AI automation gated by `AutomationDecisionEngine` (7.4); shared LLM retry/structured/fallback layer (7.5+); RAG at `/ai/chat*`; threads at `/ai/threads*`; LangGraph agent at `/ai/agent*` with HITL resume/reject; optional `POST /ai/feedback` (JWT `wid` only). Fast RAG and agent paths coexist. Soft readiness: `GET /health/ai`.

**Conversation auto-titles:** After the first successful chat or agent turn, threads get a one-shot title (`ai/memory/titles.py` — deterministic truncate + optional LLM polish). No historical backfill. Streaming clients may receive a `title` field on chat SSE `metadata` and agent `done` / `approval_required` events. Manual rename: `PATCH /ai/threads/{thread_id}`. Details: [ai.md](./ai.md). Smoke: [smoke-conversation-titles.md](./smoke-conversation-titles.md).

**Shared LLM layer (7.5+):** `shared/llm/` — `acompletion_structured` for automation + governance; `acompletion_with_retry` / `acompletion_with_fallback` for chat/agent (wall-clock candidate walk). Transient LLM failures in worker tasks re-raise for ARQ retry; agent maps exhaustion to **503**.

**Automation governance (7.4):** `worker/automation/decision.py` evaluates ambiguous/destructive AI-initiated actions only. Additive tasks (`generate_note_tags`, `generate_file_metadata`, `index_file_chunks`) skip governance. Blocked actions log `[AUTOMATION_GOVERNANCE_BLOCK]` for monitoring.

### Observability

JSON logs (`observability/logging.py`), Langfuse traces via `observability.tracing` (`rag.answer` / `agent.turn`), optional `POST /ai/feedback` (JWT `wid` thumbs or 1–5), Prometheus `/metrics` (`dashnote_api_*` + `dashnote_ai_*`), Compose `prometheus` (:9090). Grafana is **not** a default local Compose service; use Grafana Cloud / leftover `monitoring/grafana/` provisioning when needed.

**Eval program (L0–L3 implemented; not a production SLO):**

| Layer | What | Where |
|-------|------|--------|
| **L0** fixture contract | Marker / tenant / trajectory goldens | `evals/run_eval.py --mode fixture` — **PR CI** |
| **L1** live contract | Same goldens vs a real API | `evals/run_eval.py --mode live` — operator / nightly |
| **L2** answer quality | DeepEval **GEval** (correctness, completeness, style) on `rag_answers.jsonl` | `evals/run_quality.py` — laptop / pre-deploy. **Never** on `/ai/chat` or `/ai/agent`. Not PR CI. |
| **L3** serving observability | Langfuse traces, `POST /ai/feedback`, `dashnote_ai_*` | Request path has **no** judge. **Not** the hard `/health` gate. |

Later (not on this hub): thresholds/baseline, generator rewrites, agent answer goldens. Map: [evals/BLUEPRINT.md](../../evals/BLUEPRINT.md) · how to run: [evals/README.md](../../evals/README.md). Depth: [observe.md](./observe.md) (agent) · [observability.md](../observability.md) (human runbook).

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
python -m pytest tests/ai/test_thread_titles.py tests/ai/test_thread_rename_api.py -q
python -m pytest tests/ai_routes/test_feedback.py tests/observability/ -q
python -m pytest tests/core/test_rate_limit.py -q
```

Inbound email smoke (when integrations configured): `python scripts/smoke_inbound_email.py`. Conversation title UI smoke: [smoke-conversation-titles.md](./smoke-conversation-titles.md).

`pytest.ini`: `pythonpath = src`, `asyncio_mode = auto`. Windows dev: conftest stubs `magic` if libmagic missing; Docker uses `libmagic1`.

### Docker Compose & deploy

Two compose files — local full stack vs thin VPS. Hosted URL template: `.env.production.example`. Laws: [deploy-low.md](./deploy-low.md). Status / next: [devops-progress.md](../devops-progress.md).

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

**Production (VPS)** — `docker-compose.prod.yml` only on the box (never full local compose):

```powershell
# Prefer IMAGE=ghcr.io/<owner>/<repo>:<tag> pull on thin VPS (avoids on-box build)
docker compose -f docker-compose.prod.yml run --rm migrate
docker compose -f docker-compose.prod.yml up -d
# Optional metrics → Grafana Cloud remote_write:
docker compose -f docker-compose.prod.yml --profile observability up -d

# Production-live smoke (A7):
curl.exe -sS https://api.aisystem.world/health
$env:SMOKE_BASE_URL="https://api.aisystem.world"; python scripts/smoke_prod.py
```

| Profile | Services | Notes |
|---------|----------|-------|
| **Dev** | `nginx` (:80), `api` (:8000 direct), `db`, `redis`, `worker`, `qdrant`, `prometheus` (:9090), `migrate` | Compose overrides force local `DATABASE_URL` / Redis / Qdrant. `local_storage` volume for `STORAGE_BACKEND=local`. No Grafana container. |
| **Prod** | `nginx` (**:80 + :443**), `api` (expose 8000 only), `worker` (after api healthy), `migrate` (oneshot), optional `prometheus` | No `db` / `redis` / `qdrant` containers. `env_file: .env` + `DEBUG=false` only. `STORAGE_BACKEND=r2` (no shared volume). Set `IMAGE=` for GHCR pull; unset builds from local Dockerfile. |

**CD path (proven):** `.github/workflows/deploy.yml` — build/push GHCR → SSH (`/opt/dashnote`) migrate → compose up → health + `smoke_prod.py`. Triggers: `workflow_dispatch` or tag `v*` only. Secrets: `VPS_HOST` (SSH IP, not proxied hostname), `VPS_USER`, `VPS_SSH_KEY`, `SMOKE_BASE_URL=https://api.aisystem.world`. App secrets stay on the VPS `.env`.

**Infra (Level A):** `infra/` adopts existing EC2 + security group (22/80/443; **never** public 8000). Does not deploy the app or create Postgres/Redis/Qdrant/R2. See [terraform-a.md](../deployment/terraform-a.md).

Prefer **`http://127.0.0.1/`** locally for the full Nginx proxy path. Prefer **`https://api.aisystem.world/`** in prod. After recreating `api`, restart `nginx` if `/health` returns 502.

**File upload smoke test:** register → `POST /files/upload` multipart (`file`, `is_private`, optional `description`). Expect **200** with `id`, `mime_type`, `download_url`. After ~45s, worker should populate `extracted_text`, `summary`, `tags` in DB and index vectors to `files_chunks`.

**Note create smoke test:** `POST /notes/` → after ~45s worker should log `generate_note_tags complete` and populate `notes.tags` in DB.

**Agent smoke test:** `POST /ai/agent` with Bearer token → expect **200** with tool calls, or **503** when LLM quota exhausted (never silent empty response). Mutation tools may return `approval_required` → `POST /ai/agent/resume` or `/reject`. Full E2E: `python scripts/e2e_agent_test.py`.

### Dependency tiers & deploy profiles

| Tier | Services | Deploy gate |
|------|----------|-------------|
| **Hard** | Postgres (Supabase), Redis (`REDIS_URL` cache + `ARQ_REDIS_URL` queue) | `/health` must return 200 |
| **Soft** | Qdrant Cloud, LLM providers (LiteLLM → NIM / Gemini) | App boots; AI/automation degrades; probe via `/health/ai` |
| **Optional** | Langfuse, LangSmith, Grafana Cloud remote_write | Never block startup or CD |

| Concern | Production choice |
|---------|-------------------|
| Compute | AWS EC2 `t3.small` (~2 GB) — Terraform Level A |
| Edge | Cloudflare → `api.aisystem.world` (Full + origin `:443`) |
| Files | Cloudflare R2 (`STORAGE_BACKEND=r2`) |
| Vectors | Qdrant Cloud (`notes_chunks`, `files_chunks`) |
| CORS | `https://aisystem.world` (+ local FE origins in `.env`); never `*` in prod |

**Dev:** `docker compose up` — full stack on the laptop.  
**Prod:** `docker compose -f docker-compose.prod.yml up` — thin VPS; hosted URLs from `.env` only (see `.env.production.example`).
