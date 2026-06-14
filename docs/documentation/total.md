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
## DashNoteSystem AI

Multi-tenant note embeddings: chunk → Redis cache → LiteLLM → **Qdrant** (`notes_chunks`, dim **3072**). API enqueues ARQ jobs; worker indexes vectors.

**Related:** platform `src/docs/system.md` · import laws `src/docs/rules.md` · validation `src/docs/observe.md` · runbook `docs/observability.md`

### Architecture laws (enforce in all AI code)

| Law | Rule |
|-----|------|
| Imports | `from config import settings` / `get_settings` — never `from src.config` |
| `src/ai/*` | Only `config`, `ai.*`, `shared.*`, stdlib, third-party |
| `src/worker/*` | Only `config`, `ai.*`, `shared.*` — no raw Qdrant in tasks |
| Qdrant | `workspace_id` **must** filter on every search query; inject from `RequestContext` / `IndexingRequest` only |
| Qdrant search | **`WorkspaceVectorSearch`** in `ai/retrieval/wrapper.py` only — never `AsyncQdrantClient` in routers |
| Qdrant writes | `WorkspaceVectorIndex` + `NoteVectorIndexer` (notes); `WorkspaceFileVectorIndex` + `FileVectorIndexer` (files) — worker/indexer path only |
| RBAC filter | `build_rbac_filter()` in `ai/retrieval/filters.py` — mirrors `notes/permissions.py` exactly |
| Routers | Test: **`GET /ai/test-search`**; chat: **`POST /ai/chat`**, **`POST /ai/chat/stream`**; agent: **`POST /ai/agent`**, **`POST /ai/agent/stream`** |
| Services | **`RagService.answer()`** / **`stream_answer()`** — plain `workspace_id` / `user_id` / `role` strings only |
| Streaming | SSE citations in final `metadata` event only — never parsed from token stream |
| Memory ORM | **`src/ai_memory/`** — `AIThread`, `AIMessage`; never import SQLAlchemy from `src/ai/*` |
| Memory service | **`ThreadService`**, **`ContextBuilder`** |
| Agent tools | **`get_note_tools()`** — `StructuredTool` + Pydantic `args_schema`; service layer only |
| Note mutations (agent) | **`NoteService`** — `db_session_var` set by graph tool node before create/update |
| Checkpointer | **`init_checkpointer()`** / **`get_graph_checkpointer()`** — psycopg3, separate from SQLAlchemy pool |
| LLM tracing | **`observability.tracing`** only — **no** Langfuse SDK in `src/ai/*` |
| Coexistence | **`/ai/chat*`** = fast RAG; **`/ai/agent*`** = LangGraph tool loop — never replace chat routes |
| Infra | Append-only to `settings`, `.env`, `docker-compose.yml`, `requirements*.txt` |

### Key settings

| Field | Default | Purpose |
|-------|---------|---------|
| `EMBEDDING_MODEL` | `gemini/gemini-embedding-2` | Embeddings via LiteLLM |
| `EMBEDDING_DIMENSION` | `3072` | Must match Qdrant collection |
| `QDRANT_URL` | `None` | Enables Qdrant when set; `qdrant_enabled` property |
| `QDRANT_NOTES_COLLECTION` | `notes_chunks` | Note chunk vectors |
| `QDRANT_FILES_COLLECTION` | `files_chunks` | File chunk vectors (Slice 7) |
| `LLM_MODEL` | `nvidia_nim/mistralai/mistral-medium-3.5-128b` | Chat + automation via LiteLLM (prefix selects provider) |
| `LLM_TEMPERATURE` | `0.0` | Deterministic answers |
| `LLM_MAX_TOKENS` | `2048` | Max completion tokens |
| `LLM_MAX_RETRIES` | `4` | Tenacity attempts for completion calls (Slice 7.5) |
| `LLM_RETRY_MIN_WAIT` | `2.0` | Exponential backoff floor (seconds) |
| `LLM_RETRY_MAX_WAIT` | `60.0` | Exponential backoff ceiling (seconds) |
| `LLM_STRUCTURED_MAX_TOKENS_TAGS` | `256` | `generate_note_tags` completion cap |
| `LLM_STRUCTURED_MAX_TOKENS_METADATA` | `512` | `generate_file_metadata` completion cap |
| `NVIDIA_NIM_API_KEY` | `None` | NVIDIA NIM provider key (alias: `NVIDIA_API_KEY`) |
| `TOKEN_BUDGET_PER_REQUEST` | `8000` | Char budget for retrieved context |
| `AI_THREAD_MESSAGE_LIMIT` | `20` | History loaded per turn |
| `AGENT_MAX_ITERATIONS` | (see `config.py`) | Tool loop guard |
| `ai_enabled` | property | Any of `OPENAI_API_KEY`, `GEMINI_API_KEY`, `NVIDIA_NIM_API_KEY` / `NVIDIA_API_KEY` |
| Langfuse | `LANGFUSE_*` keys | Active LLM trace path when both keys set (LangSmith inactive) |

---

## Slice 1 — embeddings pipeline

| Path | Role |
|------|------|
| `shared/contracts/indexing.py` | `IndexingRequest`, `IndexingResult`, `IndexingOperation` |
| `ai/embeddings/chunker.py` | Deterministic `chunk_id` (uuid5), title prepended as H1 |
| `ai/embeddings/litellm_provider.py` | Batched `litellm.aembedding` + tenacity |
| `ai/embeddings/factory.py` | `get_embedding_provider()` singleton |
| `ai/services/cache.py` | Redis `embed:v1:{sha256(text)}` |
| `ai/workflows/pipeline.py` | `EmbeddingPipeline.process_note` → `EmbeddedChunk[]` |
| `worker/ingestion/tasks.py` | `embed_note_task` |
| `notes/router.py` | Enqueue `embed_note_task` + emit `NoteCreatedEvent` after commit when `ai_enabled` |
| `files/router.py` | Emit `FileUploadedEvent` after upload when `ai_enabled` |

**Worker flow:** `IndexingRequest` → delete note vectors (if `qdrant_enabled`) → embed → upsert. When `QDRANT_URL` unset, embeddings still run; `qdrant_indexed=false`.

---

## Slice 7 — event-driven automation (7.0–7.4)

| Path | Role |
|------|------|
| `shared/events/definitions.py` | Frozen Pydantic event schemas (`NoteCreatedEvent`, `FileUploadedEvent`, …) — **extend payloads only** |
| `shared/events/bus.py` | `emit_event()` — maps `EventType` → ARQ task name; never raises |
| `shared/utils/parsers.py` | `FileParsingEngine` — sync text extraction (PDF, DOCX, HTML, text/*); CPU-bound, no DB/FastAPI |
| `shared/llm/structured.py` | `acompletion_structured()` — tenacity retry + JSON salvage + Pydantic validation |
| `shared/llm/retry.py` | `acompletion_with_retry()` — shared retry policy for agent + automation LLM calls |
| `worker/automation/tasks.py` | Extraction, fan-out indexing/metadata/tagging tasks |
| `worker/automation/decision.py` | `AutomationDecisionEngine` — governance gate for destructive AI-initiated actions |
| `worker/main.py` | Registers 8 ARQ tasks; `ctx["arq_pool"]` for fan-out; imports all ORM models at startup |

**Event → task routing:**

| Event | ARQ task |
|-------|----------|
| `file.uploaded` | `handle_file_uploaded` |
| `note.created` | `handle_note_created` |
| `note.updated` | `handle_note_updated` |
| `file.deleted` | `handle_file_deleted` |

**Fan-out tasks (7.3):**

| Task | Purpose | Governance |
|------|---------|------------|
| `index_file_chunks` | Embed `extracted_text` → `files_chunks` via `EmbeddingPipeline` + `FileVectorIndexer` | **None** — idempotent upsert |
| `generate_file_metadata` | LLM summary + tags → `files.summary`, `files.tags` | **None** — additive metadata |
| `generate_note_tags` | LLM tags → `notes.tags` | **None** — additive metadata |

**File upload pipeline:** upload → `FileUploadedEvent` → worker downloads via `get_storage()` → `FileParsingEngine.extract_text()` (executor) → persist `files.extracted_text` → fan-out `index_file_chunks` + `generate_file_metadata`.

**Note create pipeline:** commit → `embed_note_task` (Slice 1) + `NoteCreatedEvent` → `handle_note_created` → fan-out `generate_note_tags`.

**Models:** `files`: `extracted_text`, `summary`, `tags` (migration `95fb65156e52`). `notes`: `tags` (`JSONB`, default `[]`, migration `6ee79b0f52a3`). Deps: `pypdf`, `python-docx`, `beautifulsoup4`, `lxml`.

**Governance (7.4) — `AutomationDecisionEngine`:**

| Use | Do not use |
|-----|------------|
| Auto-delete duplicates, auto-merge, auto-archive, external notifications | `generate_note_tags`, `generate_file_metadata`, `index_file_chunks` |

- `evaluate_action(context)` → `AutomationDecision` via `shared.llm.acompletion_structured` (retry + JSON salvage)
- `should_execute_immediately(decision)` → `True` **only** if `confidence >= 0.95` **and** `is_destructive=False`
- Otherwise: log **`[AUTOMATION_GOVERNANCE_BLOCK]`** (exact marker) and hold for human review (future slice)
- LLM failure → fail-safe block (`is_destructive=True`, `confidence=0.0`)
- Import law: `litellm`, `pydantic`, `config`, stdlib only — no FastAPI, SQLAlchemy, repositories

**Coexistence:** Slice 1 `embed_note_task` enqueue in `notes/router.py` is unchanged. Slice 7 adds a second `emit_event()` call after note create. File upload emits `FileUploadedEvent` only (no direct embed enqueue).

**Worker context:** `ctx["redis"]` (Slice 1 cache) + `ctx["arq_pool"]` (Slice 7 fan-out). Worker DB: `AsyncSessionLocal` directly — never `get_session()`. Storage download: `get_storage().download(storage_key)`.

**Validation (Compose):**

```powershell
docker compose up -d --build api worker
python -m pytest tests/shared/test_llm_structured.py tests/worker/test_automation_decision.py tests/worker/test_automation_llm_tasks.py -q
docker compose exec -e PYTHONPATH=/app/src worker python -m worker.automation.decision
# POST /files/upload (.txt) → wait ~45s (NVIDIA NIM latency)
docker compose logs worker --tail 50
# Expect: extracted_text saved → fan-out enqueued → index_file_chunks complete → generate_file_metadata complete
docker compose exec db psql -U dashuser -d dashnotes \
  -c "SELECT name, length(extracted_text), summary, tags FROM files ORDER BY created_at DESC LIMIT 1;"
curl.exe -sS "http://127.0.0.1:6333/collections/files_chunks"
# POST /notes/ → wait ~45s → generate_note_tags complete
docker compose exec db psql -U dashuser -d dashnotes \
  -c "SELECT id, title, tags FROM notes ORDER BY created_at DESC LIMIT 3;"
python scripts/e2e_agent_test.py   # register → notes → file → POST /ai/agent
```

---

## Slice 7.5 — LLM hardening (shared completion layer)

Resilience for automation LLM calls and agent `call_model`. Blueprint: `docs/documentation/blueprint/slice7-llm-hardening.md`.

| Path | Role |
|------|------|
| `shared/llm/env.py` | `configure_litellm_env()` — push provider keys into `os.environ` at API/worker startup |
| `shared/llm/retry.py` | `RETRYABLE_EXCEPTIONS`, `FATAL_EXCEPTIONS`, `acompletion_with_retry()` |
| `shared/llm/structured.py` | `extract_json_blob()`, `parse_structured_response()`, `acompletion_structured()`, `StructuredLLMParseError` |

**Import law:** `shared/llm/*` may import `config`, `litellm`, `pydantic`, `tenacity`, stdlib only. Both `src/worker/*` and `src/ai/*` import from `shared/llm/` — never `worker` from `ai`.

**Consumers:**

| Caller | Function | On transient failure |
|--------|----------|----------------------|
| `generate_note_tags`, `generate_file_metadata` | `acompletion_structured` | Re-raise → ARQ job retry |
| `AutomationDecisionEngine.evaluate_action` | `acompletion_structured` | Fail-safe block (`is_destructive=True`) |
| `workspace_assistant.call_model` | `acompletion_with_retry` | Re-raise → route maps to **503** |

**Log markers:** `[AUTOMATION_LLM_RETRY_EXHAUSTED]`, `[AUTOMATION_LLM_PARSE_FAIL]`, `[AUTOMATION_LLM_AUTH_FAIL]`

**Embedding retry** stays in `ai/embeddings/litellm_provider.py` — not merged into `shared/llm/`.

**Agent HTTP:** `ai_routes/agent.py` maps exhausted `RateLimitError` / `ServiceUnavailableError` to **503** `"LLM temporarily unavailable; retry shortly"` (not opaque 500).

---

## Slice 2 — RBAC search & Qdrant indexing

### Module layout — `ai/retrieval/`

| File | Role |
|------|------|
| `client.py` | `get_async_qdrant_client()` singleton (retrieval package only) |
| `collection.py` | `ensure_notes_collection()`, `ensure_files_collection()` — cosine, `EMBEDDING_DIMENSION` |
| `filters.py` | **`build_rbac_filter(workspace_id, user_id, role)`** |
| `wrapper.py` | **`WorkspaceVectorSearch`** + **`get_workspace_vector_search()`** |
| `workspace_search.py` | **`WorkspaceVectorIndex`** (notes), **`WorkspaceFileVectorIndex`** (files) |
| `indexer.py` | `NoteVectorIndexer`, `FileVectorIndexer` — delete-then-upsert per source |

### RBAC filter (mirrors `notes/permissions.py`)

| Role | Qdrant filter |
|------|----------------|
| `owner`, `admin` | `must`: `workspace_id` |
| `member` | `must`: `workspace_id` **and** (`visibility=public` **or** `created_by=user_id`) |

`visibility`: `"public"` ↔ `is_private=False`, `"private"` ↔ `is_private=True`.  
`workspace_id` is **never** optional and **never** from request query/body on search routes.

### Qdrant payload

| Field | Purpose |
|-------|---------|
| `workspace_id` | Tenant isolation (mandatory filter) |
| `note_id`, `chunk_id`, `chunk_index` | Identity / ordering |
| `text`, `chunk_text` | Chunk body (`text` preferred by wrapper) |
| `title` | Note title |
| `created_by`, `visibility`, `is_private` | Member RBAC |
| `token_count`, `char_start`, `char_end` | Metrics / debugging |

Point id = UUID from deterministic `chunk_id`.

### HTTP — `GET /ai/test-search` (`ai_gateway/search.py`)

Auth: Bearer JWT → `RequestContext`. **503** when `ai_enabled` or `qdrant_enabled` is false.

| Query | Rule |
|-------|------|
| `q` | 1–500 chars |
| `limit` | 1–20, default 5 |
| `workspace_id` | **Never accepted** — always JWT `wid` |

**Quality gate:** cosine `score` > **0.4** for matching content; tenant isolation; member RBAC. Tuning: verify dim 3072; try `CHUNK_SIZE` 600–800; re-index after payload changes.

---

## Slices 3–4 — RAG chat (JSON + SSE)

| Path | Role |
|------|------|
| `ai/prompts/rag.py` | `RAGAnswer`, `RAG_SYSTEM_INSTRUCTION`, `build_rag_user_message()` |
| `ai/services/rag_service.py` | `answer()`, `stream_answer()` — retrieve → budget → LLM → citations |
| `ai_routes/chat.py` | `POST /ai/chat`, `POST /ai/chat/stream` |

**Service imports:** `litellm`, `pydantic`, `config`, `ai.retrieval.*`, `ai.prompts.*`, `observability.tracing`, stdlib — no FastAPI, SQLAlchemy, `RequestContext`, or Langfuse SDK.

**Route pattern:** JWT → freeze `workspace_id`, `user_id`, `role` to plain strings **before** calling `RagService`.

| Route | Body | Response |
|-------|------|----------|
| `POST /ai/chat` | `message` (1–2000 chars); optional `thread_id` | `answer`, `citations[]`, `chunks_retrieved`, `chunks_used`, `latency_ms`, `thread_id` |
| `POST /ai/chat/stream` | Same | SSE: `token` events → `metadata` (citations, `thread_id`) → `[DONE]` |

Stream headers: `Cache-Control: no-cache`, `X-Accel-Buffering: no`. Citations from **top 5 retrieved chunks**, not token stream.

---

## Slice 5 — conversation memory & threads

| Path | Role |
|------|------|
| `ai_memory/models.py` | `AIThread`, `AIMessage` (product ORM layer) |
| `ai_memory/repository.py` | `ThreadRepository` — workspace filter on every query |
| `ai/memory/service.py` | `ThreadService` — get/create thread, load history, persist turn |
| `ai/memory/context_builder.py` | `ContextBuilder.build()` — history + retrieval char budget |
| `ai_routes/threads.py` | Thread CRUD routes |

**RagService:** accepts `thread_id` and `db: AsyncSession | None` (injected from route via `Depends(get_session)`; TYPE_CHECKING only in service).

| Route | Purpose |
|-------|---------|
| `GET /ai/threads` | List user threads in JWT workspace |
| `GET /ai/threads/{thread_id}/messages` | Message history (default limit 50) |
| `DELETE /ai/threads/{thread_id}` | Soft delete (`is_active=false`) |

Cross-workspace access: **404** on thread routes, **400** on chat reuse. `workspace_id` always from JWT, never query/body/path.

---

## Slice 6 — LangGraph workspace assistant

Adds **`POST /ai/agent`** and **`POST /ai/agent/stream`**. **`/ai/chat*`** unchanged (fast RAG).

| Path | Role |
|------|------|
| `ai/memory/checkpointer.py` | `AsyncPostgresSaver` (psycopg3); `init_checkpointer()` in lifespan |
| `notes/service.py` | `create_note()` / `update_note()` for agent tools |
| `ai/tools/schemas.py` | Pydantic `args_schema` models |
| `ai/tools/note_tools.py` | Four `StructuredTool`s; `db_session_var` for mutations |
| `ai/workflows/state.py` | `AgentState` — messages, tenant fields, `steps_taken`, `thread_id` |
| `ai/workflows/workspace_assistant.py` | Graph: `START → agent → tools → agent → END`; lazy compile |
| `ai_routes/agent.py` | Agent HTTP endpoints |

**Tool chain** (never shortcut to repository):

| Tool | Service |
|------|---------|
| `search_notes` | `RagService.answer(...)` |
| `create_note` | `NoteService.create_note(db, ...)` — `db` from `db_session_var` |
| `update_note` | `NoteService.update_note(db, ...)` |
| `summarize_workspace` | `RagService.answer(..., retrieval_limit=12)` |

**Agent contract:** `POST /ai/agent` → `AgentResponse` (`answer`, `thread_id`, `steps_taken`, `tool_calls_made`). Stream: SSE from `graph.astream_events` (`token`, `tool_start`, `tool_end`, `done`, `[DONE]`). LangGraph config: `{"configurable": {"thread_id": thread_id}}`. LiteLLM `tools=` with OpenAI function defs — not LangChain `.bind_tools()`. `call_model` uses `shared.llm.acompletion_with_retry` (Slice 7.5).

Slice 6 invariants: see `src/docs/rules.md`.

---

## Observability

RAG instrumentation via `observability.tracing` (`rag_trace` → spans `retrieval`, `context_building`, `llm_generation`). HTTP metrics at `GET /metrics` (`dashnote_api_*`). Details and validation commands: **`src/docs/observe.md`**.

---

## Related docs

| Doc | Content |
|-----|---------|
| `src/docs/system.md` | Routers, tenancy, Compose, rate limits |
| `src/docs/rules.md` | Import direction, Slice 6 modification laws |
| `src/docs/lld.md` | §4.12–4.18 (flows, retrieval, RAG, agent, automation, shared LLM) |
| `src/docs/observe.md` | Validation commands, observability steps |
| `src/docs/blueprint/slice*.md` | Per-slice build history and sign-off gates |
| `docs/documentation/blueprint/slice7-llm-hardening.md` | Slice 7.5 recovery blueprint and gate criteria |
