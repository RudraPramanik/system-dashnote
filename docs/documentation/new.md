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
<!--  -->
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
<!--  -->
# DashNoteSystem Low-Level Design (LLD)

**Purpose:** Implementation patterns, call flows, module responsibilities, and abstractions — use ASCII flows below as source material for UML sequence/class diagrams.

**Related:** `src/docs/system.md` (routing, Compose) · `src/docs/ai.md` (AI contracts) · `src/docs/rules.md` (import laws) · `src/docs/observe.md` (validation) · [`docs/uml/`](../../docs/uml/README.md) (Mermaid diagrams)

---

## 1) Objective and scope

Implementation-level design for the backend in this repository, aligned with code that exists today.

**In scope:** Auth/JWT context · multi-tenant repositories · RBAC · storage backends · modules `auth`, `workspaces`, `membership`, `notes`, `notebooks`, `files` · AI slices 1–7.5 · observability (`observability/*`, Prometheus, Grafana)

**Out of scope:** Frontend · cloud provisioning beyond Compose/nginx/monitoring · Loki/Tempo/Jaeger/OTel Collector · non-implemented runtime components

---

## 2) Design principles

| Principle | Rule |
|-----------|------|
| Thin routers | Validate input → inject deps → call service/repository/permissions → map to Pydantic |
| Explicit security context | Single `RequestContext` from JWT (`sub`, `wid`, `role`); no module decodes JWT alone |
| Tenant safety by construction | `TenantRepository` + `tenant_filter(...)` on every tenant query |
| Layered RBAC | Route: `require_roles(...)` · entity: domain permission helpers |
| Tenancy naming | `tenant_filter` supports `workspace_id` and legacy `tenant_id` |
| Binary assets | Bytes in `StorageBackend`; SQL holds metadata + `storage_key` + RBAC columns |

---

## 3) Runtime architecture

### 3.1 Composition (`src/main.py`)

Router map, middleware, rate limits, Compose services: **`src/docs/system.md`**.

LLD-relevant wiring:

- **Lifespan:** `setup_logging()` → ARQ pool → Qdrant bootstrap → LangGraph checkpointer (non-fatal)
- **Global deps:** `enforce_global_rate_limit` (Redis fixed-window)
- **Metrics:** `Instrumentator` → `GET /metrics` (`dashnote_api_*`)

### 3.2 Protected request flow (sequence diagram source)

```
Client
  │  Authorization: Bearer <token>
  ▼
[Nginx] X-Forwarded-For, X-Real-IP, X-Request-ID, limit_req
  ▼
[ProxyHeadersMiddleware] adjust ASGI client
  ▼
[enforce_global_rate_limit] Redis INCR (user_id or IP)
  ▼
[oauth2_scheme] extract token
  ▼
[get_current_context] JWT → RequestContext (+ optional blacklist via get_token_store)
  ▼
[Optional: get_workspace_cache] tenant-scoped cache-aside
  ▼
[Router] require_roles / domain permissions
  ▼
[Repository(session, workspace_id)] tenant_filter + SQLAlchemy
  ▼
[Pydantic response]
```

---

## 4) Module-level design

### 4.1 `auth`

| Endpoint | Flow |
|----------|------|
| `POST /auth/register` | Create user + workspace + membership → issue access/refresh JWT (`sub`, `wid`, `role`, `jti`, `typ`) |
| `POST /auth/login` | Validate creds → default membership → JWT; **5/min** rate limit |
| `POST /auth/refresh` | Validate refresh JWT; rotate when Redis tracks `jti` |
| `POST /auth/logout` | Blacklist access `jti`; revoke refresh when enabled |

Token state: `core/redis/redis.py` (`get_token_store`). Details: `src/docs/auth.md`.

### 4.2 `core.redis`

| Component | Role |
|-----------|------|
| `client.py` | Singleton `get_async_redis()` |
| `redis.py` | JWT blacklist + refresh tracking |
| `cache.py` | `WorkspaceRedisCache` — keys prefixed by `workspace_id`; generation counters (`notes`, `notebooks`) |
| `deps.py` | `get_redis_connection`, `get_workspace_cache` |

Consumers: `notes/router.py`, `notebooks/router.py` (cache-aside on reads; `INCR` generation on writes).

### 4.3 `core.security`

| Component | Role |
|-----------|------|
| `dependency.py` | `_context_from_access_token`, `get_current_context`, `get_optional_current_context` |
| `permissions.py` | `require_roles(*roles)` → 403 |
| `rate_limit.py` | `RateLimiter` keys `rate_limit:{scope}:{user_id\|ip}:{window_index}`; global **100/min**; fail-open without Redis |

Failures: missing/invalid token → **401** · insufficient role → **403** · limit exceeded → **429** + `Retry-After`

### 4.4–4.7 Domain modules (summary)

| Module | Pattern | RBAC highlight |
|--------|---------|----------------|
| `workspaces` | JWT `wid` only | `PATCH /me` owner/admin |
| `membership` | Service rules on `workspace_users` | Role changes owner-only |
| `notes` | `TenantRepository` + visibility SQL filter | Member: own notes + public notes |
| `notebooks` | `TenantRepository` | Create owner/admin; cached list |

### 4.8 `files`

```
Upload → validate_file (utils) → StorageBackend.upload → File row (workspace_id, storage_key, RBAC)
Download → permission check → StorageBackend.download stream
Attach → note_attachments association only (no cross-package imports)
```

RBAC mirrors notes visibility (`files/permissions.py`). Backends: `local`, `minio`, `r2` via `get_storage()`.

### 4.9 `ai_gateway`

| File | Status |
|------|--------|
| `search.py` | **Implemented** — `GET /ai/test-search` (JWT-scoped validation) |
| `router/router.py`, `schemas/` | Placeholders / partial — product routes live in `ai_routes/*` |

Contract: same router → dependency → service layering; `RequestContext` for tenant safety.

---

### 4.10 AI indexing — embeddings (Slice 1)

#### Contracts — `shared/contracts/indexing.py`

| Type | Producer | Consumer |
|------|----------|----------|
| `IndexingRequest` | API after note upsert | ARQ worker |
| `DeletionRequest` | API after note delete | ARQ worker |
| `IndexingResult` | Worker | Logging |

#### Chunking — `ai/embeddings/chunker.py`

```
IndexingRequest (content, title, note_id)
        │
        ▼
   TextChunker.chunk_note()
        │
        ▼
 list[ChunkResult]   # chunk_id = uuid5(NAMESPACE_URL, "{note_id}:{index}")
```

Title as markdown H1; splitter from `CHUNK_SIZE`, `CHUNK_OVERLAP`, `CHUNK_MIN_LENGTH`.

#### Provider abstraction

```
BaseEmbeddingProvider (ABC)
    embed_texts(texts) → list[EmbeddingVector]
            │
            ▼
LiteLLMEmbeddingProvider   ← get_embedding_provider() singleton (factory.py)
```

#### Pipeline — `ai/workflows/pipeline.py`

```
process_note
    ├─► TextChunker.chunk_note()
    ├─► per chunk: Redis cache hit/miss (embed:v1:{sha256})
    ├─► provider.embed_texts(uncached)
    └─► EmbeddedChunk[] + metrics
```

#### Import matrix (embeddings)

| Module | May import |
|--------|------------|
| `shared/contracts/indexing.py` | stdlib, pydantic |
| `ai/embeddings/*`, `ai/services/cache.py`, `ai/workflows/pipeline.py` | stdlib, pydantic, litellm, tenacity, langchain_text_splitters, `config`, `ai.*` |
| Must **not** | FastAPI, SQLAlchemy, `notes/*`, `worker/*`, `qdrant-client` |

### 4.11 ARQ worker — `src/worker/`

```
embed_note_task
    ├─► IndexingRequest validate
    ├─► get_embedding_provider() + EmbeddingPipeline.process_note
    ├─► NoteVectorIndexer (Qdrant delete/upsert when qdrant_enabled)
    └─► IndexingResult
```

**Automation tasks (Slice 7)**

```
FileUploadedEvent → handle_file_uploaded
    ├─► get_storage().download(storage_key)
    ├─► FileParsingEngine.extract_text (executor)
    ├─► persist files.extracted_text
    └─► fan-out: index_file_chunks, generate_file_metadata

NoteCreatedEvent → handle_note_created
    └─► fan-out: generate_note_tags

index_file_chunks
    ├─► EmbeddingPipeline.process_note (file_id as source)
    └─► FileVectorIndexer → files_chunks

generate_file_metadata / generate_note_tags
    └─► shared.llm.acompletion_structured(schema=...) → persist tags/summary
        ├─► transient / parse error → re-raise (ARQ retry)
        └─► auth / not-found → log [AUTOMATION_LLM_AUTH_FAIL] → return
```

Import law: stdlib, arq, pydantic, `config`, `ai.*`, `shared.*` — no FastAPI in `decision.py`; worker tasks use `AsyncSessionLocal` for DB.

### 4.12 AI retrieval (Slice 2)

```
GET /ai/test-search?q=...
    ├─► RequestContext
    ├─► WorkspaceVectorSearch.search()
    │       ├─► embed query
    │       ├─► build_rbac_filter(workspace_id, user_id, role)
    │       └─► query_points(..., query_filter=rbac)
    └─► list[SearchResult]
```

| Role | Qdrant filter |
|------|----------------|
| `owner`, `admin` | `must`: `workspace_id` |
| `member` | `must`: `workspace_id`; `should`: `visibility=public` OR `created_by=user_id` |

**Invariants:** `workspace_id` from JWT only · routers never use `AsyncQdrantClient` · search entry = `wrapper.py` only.

### 4.13 RAG chat — Slices 3–4

**JSON path**

```
POST /ai/chat  { message, thread_id? }
    ├─► freeze workspace_id, user_id, role (plain str)
    ├─► RagService.answer(...)
    │       ├─► WorkspaceVectorSearch.search
    │       ├─► ContextBuilder (when thread_id + db)
    │       ├─► char budget TOKEN_BUDGET_PER_REQUEST
    │       ├─► litellm.acompletion(response_format=RAGAnswer)
    │       ├─► ground cited_chunk_ids against retrieved set
    │       └─► ThreadService.persist_turn (when db)
    └─► ChatResponse
```

**SSE path**

```
POST /ai/chat/stream
    ├─► freeze ctx BEFORE generate()
    ├─► async for event in stream_answer():
    │       token → metadata (citations from top chunks, not token parse)
    └─► data: [DONE]
```

| SSE `type` | Payload |
|------------|---------|
| `token` | `content` |
| `metadata` | `citations`, `chunks_*`, `latency_ms`, `thread_id` |
| `error` | `message` (generic) |

Headers: `Cache-Control: no-cache`, `X-Accel-Buffering: no`.

**Invariants:** `RagService` has no FastAPI/SQLAlchemy/RequestContext imports · citations only from retrieved chunks · structured output only.

### 4.14 Conversation memory + threads (Slice 5)

**Layering**

| Layer | Storage | Purpose |
|-------|---------|---------|
| Product | `ai_threads`, `ai_messages` | UI history via `ThreadService` |
| Execution | LangGraph `AsyncPostgresSaver` | Agent checkpoints (Slice 6); linked by `thread_id` string |

```
GET /ai/threads | GET /ai/threads/{id}/messages | DELETE /ai/threads/{id}
    └─► ThreadRepository (workspace_id on every query) → 404 cross-tenant
```

`ContextBuilder`: char budget ~70% history / 30% retrieval context.

### 4.15 LangGraph agent (Slice 6)

**Tool dispatch**

```
tool_node
    ├─► db_session_var.set(session)   # mutation tools
    └─► StructuredTool invoke

search_notes / summarize_workspace → RagService.answer(...)
create_note / update_note            → NoteService.*(db from db_session_var)
```

**Agent invoke**

```
POST /ai/agent { message, thread_id? }
    ├─► freeze ctx, resolve thread, db_session_var.set(db)
    ├─► get_workspace_assistant().ainvoke(state, config={thread_id})
    │       └─► call_model → shared.llm.acompletion_with_retry(tools=...)
    ├─► RateLimitError / ServiceUnavailableError after retries → 503
    └─► AgentResponse(answer, thread_id, steps_taken, tool_calls_made)
```

Graph: `START → agent → tools → agent → END` · LiteLLM `tools=` (OpenAI function defs) · `AGENT_MAX_ITERATIONS` guard · lazy compile with optional checkpointer.

**Coexistence:** `/ai/chat*` unchanged (fast RAG) · `/ai/agent*` additive. See `src/docs/rules.md` for modification laws.

### 4.16 Observability

```
RagService.answer / stream_answer
    └─► rag_trace → spans: retrieval, context_building, llm_generation
            └─► get_langfuse_client() (lazy, optional)

HTTP → Instrumentator → dashnote_api_* → Prometheus → Grafana (API Overview)
```

| Langfuse observation | Outputs |
|---------------------|---------|
| `rag.answer` | metadata: workspace_id, user_id, role |
| `retrieval` | chunks_retrieved, latency_ms |
| `context_building` | chunks_used, char_budget, latency_ms |
| `llm_generation` | tokens, cost, latency_ms |

Langfuse SDK only in `observability/langfuse_client.py` and `tracing.py`. Validation: **`src/docs/observe.md`**.

### 4.17 Automation governance (Slice 7.4)

```
Proposed destructive AI action (future tasks: auto-delete, auto-merge, …)
    ├─► AutomationDecisionEngine.evaluate_action(context)
    │       └─► shared.llm.acompletion_structured(schema=AutomationDecision)
    ├─► should_execute_immediately(decision)
    │       ├─► True  (confidence >= 0.95 AND is_destructive=False) → execute
    │       └─► False → log [AUTOMATION_GOVERNANCE_BLOCK] → pending review (future)
    └─► LLM failure → fail-safe block (is_destructive=True, confidence=0.0)
```

| Task | Governance |
|------|------------|
| `generate_note_tags`, `generate_file_metadata`, `index_file_chunks` | **Skipped** — additive/idempotent |
| Future destructive automation | **Required** — `evaluate_and_gate()` before side effects |

`worker/automation/decision.py`: `shared.llm`, `pydantic`, `config`, stdlib only — no FastAPI, SQLAlchemy, repositories.

### 4.18 Shared LLM layer (Slice 7.5)

```
acompletion_structured(messages, schema, max_tokens)
    ├─► tenacity retry on RETRYABLE_EXCEPTIONS (RateLimit, Timeout, 503, connection)
    ├─► litellm.acompletion(response_format=schema)
    ├─► parse_structured_response(raw, schema)
    │       ├─► model_validate_json(raw)
    │       └─► extract_json_blob(raw) → salvage markdown fences / preamble
    └─► StructuredLLMParseError → re-raise (ARQ retry in worker tasks)

acompletion_with_retry(**kwargs)
    └─► tenacity-wrapped litellm.acompletion (agent call_model; non-structured)
```

| Module | May import |
|--------|------------|
| `shared/llm/*` | `config`, `litellm`, `pydantic`, `tenacity`, stdlib |
| Must **not** | FastAPI, SQLAlchemy, `worker/*`, `ai/*` (shared is imported by both) |

**Coexistence:** embedding retry remains in `ai/embeddings/litellm_provider.py` (`EMBEDDING_MAX_RETRIES`); completion retry uses `LLM_MAX_RETRIES`.

---

## 5) Data model

**Entities:** `users`, `workspaces`, `workspace_users`, `notes`, `notebooks`, `pages`, `files`, `note_attachments`, `ai_threads`, `ai_messages`

**Patterns:** `TimestampMixin`, `WorkspaceTenantMixin`, `tenant_filter(model, workspace_id)`

**Writes:** repository methods own `add` → `commit` → optional `refresh`

---

## 6) Layer responsibility matrix

| Layer | Paths | Responsibility |
|-------|-------|----------------|
| Edge | `nginx/default.conf` | Rate limit, proxy headers |
| App shell | `main.py` | Lifespan, routers, global rate limit, `/metrics` |
| Security | `core/security/*` | JWT → context, RBAC, rate limits |
| Persistence | `core/database/*`, `<module>/repository.py` | Session, tenant filter, CRUD |
| Cache | `core/redis/*` | JWT state, cache-aside, embedding cache |
| Storage | `core/storage/*` | Backend abstraction, upload validation |
| Domain | `auth`, `notes`, `files`, … | Business rules + HTTP adapters |
| AI core | `ai/embeddings/*`, `ai/retrieval/*`, `ai/services/rag_service.py` | Embeddings, search, RAG (no HTTP) |
| AI routes | `ai_gateway/search.py`, `ai_routes/*` | HTTP adapters; freeze ctx |
| AI memory | `ai_memory/*`, `ai/memory/*` | Threads ORM + services |
| AI agent | `ai/workflows/*`, `ai/tools/*`, `ai/memory/checkpointer.py` | LangGraph + tools |
| Shared LLM | `shared/llm/*` | Retry policy, structured completion, JSON salvage |
| Worker | `worker/*` | ARQ embed, automation fan-out, governance gate |
| Observability | `observability/*`, `monitoring/*` | Logs, traces, metrics, dashboards |

---

## 7) Error handling

| Code | Use |
|------|-----|
| 400 | Invalid input, role/state conflict, cross-workspace thread reuse |
| 401 | Auth failure |
| 403 | Permission denied |
| 404 | Entity not found (includes cross-workspace thread) |
| 429 | Rate limit (`Retry-After`) |
| 500 | Unhandled (global handler; generic body) |
| 503 | Health probe failure; AI disabled (`ai_enabled` / `qdrant_enabled`); agent LLM retries exhausted (`RateLimitError` / `ServiceUnavailableError`) |

---

## 8) Testing alignment

| Area | Location |
|------|----------|
| Permissions / tenant repos | `tests/` (module-specific) |
| Rate limit | `tests/core/test_rate_limit.py` |
| Redis cache-aside | `tests/core/test_workspace_redis_cache.py` |
| Files (mocked storage) | `tests/files/` |
| Auth token flows | auth tests |
| Automation governance | `tests/worker/test_automation_decision.py` |
| Shared LLM structured | `tests/shared/test_llm_structured.py` |
| Automation LLM tasks | `tests/worker/test_automation_llm_tasks.py` |
| Agent LLM retry mapping | `tests/ai/test_agent_retry.py` |

**Rule for new modules:** tenant-scope tests + RBAC tests + happy-path CRUD; mock `StorageBackend` for file IO.

---

## 9) Extension blueprint

New module under `src/<module>/`:

1. `models.py`, `schemas.py`, `repository.py`, `router.py` (+ `service.py` if non-trivial)
2. `RequestContext` on protected routes
3. `tenant_filter` in repository
4. `require_roles` + domain permission helpers
5. Register in `main.py` · migration · tests

Binary blobs: `StorageBackend` for bytes; SQL for metadata + `workspace_id` (follow `files` pattern).

---

## UML diagrams

Mermaid diagrams (sequence, component, class, state, deployment) live in **`docs/uml/`**:

| LLD section | Diagram |
|-------------|---------|
| §3.2 | [Protected HTTP request](../../docs/uml/diagrams.md#1-protected-http-request) |
| §6 | [Application layers](../../docs/uml/diagrams.md#2-application-layers) |
| §4.10 | [Embedding pipeline](../../docs/uml/diagrams.md#3-embedding-pipeline-slice-1) |
| §4.11 | [ARQ worker indexing](../../docs/uml/diagrams.md#4-arq-worker-indexing) |
| §4.12 | [Semantic search + RBAC](../../docs/uml/diagrams.md#5-semantic-search--rbac) |
| §4.13 | [RAG chat JSON](../../docs/uml/diagrams.md#6-rag-chat-json) · [RAG SSE](../../docs/uml/diagrams.md#7-rag-streaming-sse) |
| §4.14 | [Conversation memory classes](../../docs/uml/diagrams.md#8-conversation-memory-layers) |
| §4.15 | [LangGraph agent loop](../../docs/uml/diagrams.md#9-langgraph-agent-loop) |
| §4.11 | [Automation fan-out](../../docs/uml/diagrams.md#11-automation-fan-out-slice-7) |
| §4.18 | [Shared LLM layer](../../docs/uml/diagrams.md#12-shared-llm-layer-slice-75) |
| §3.1 / Compose | [Docker deployment](../../docs/uml/diagrams.md#10-docker-compose-deployment) |

Index: [`docs/uml/README.md`](../../docs/uml/README.md)
<!--  -->
# DashNote Observability (agent context)

Short reference for humans and AI agents working on observability in this repo.

**Code layout:** `src/observability/`  
**Blueprint (full steps):** `src/docs/blueprint/observation-blueprint.md`

---

## Progress

| Step | What | Status |
|------|------|--------|
| 1 | JSON logging (`setup_logging` in `main.py` lifespan) | Done |
| 2 | Langfuse lazy client (`get_langfuse_client`) | Done |
| 3 | RAG traces in `RagService` | Done |
| 4 | Prometheus `/metrics` | Done |
| 5 | Prometheus + Grafana (Compose) | Done |
| 6 | Grafana provisioning + dashboards | Done |

---

## Rules (do not break)

1. **`setup_logging()`** — only called in `src/main.py` lifespan (first line).
2. **`get_langfuse_client()`** — lazy only; **never** call from `main.py` lifespan (Step 3 tracing layer calls it).
3. **Langfuse SDK** — only imported in `src/observability/langfuse_client.py` and `tracing.py`. `RagService` uses `observability.tracing` only (no direct SDK).
4. **Imports:** `from config import get_settings` — never `from src.config`.
5. **LangSmith** — config exists; inactive. Langfuse is the active LLM trace path.

---

## Step 1 — JSON logging

- **Use:** `from observability import get_logger, setup_logging`
- **Schema:** `timestamp`, `level`, `logger`, `message` (+ optional `extra`: `request_id`, `workspace_id`, `user_id`, `route`, `latency_ms`)
- **Verify:** `docker compose logs --tail 20 api` → each line is JSON

---

## Step 2 — Langfuse client

### Config (`src/config.py`)

| Env var | Default | Purpose |
|---------|---------|---------|
| `LANGFUSE_PUBLIC_KEY` | `""` | Project public key (`pk-lf-...`) |
| `LANGFUSE_SECRET_KEY` | `""` | Secret key (`sk-lf-...`) |
| `LANGFUSE_HOST` | `https://cloud.langfuse.com` | EU cloud; US: `https://us.cloud.langfuse.com` |

**Enabled when:** both keys are non-empty → `settings.langfuse_enabled` is `True`.

Copy keys from Langfuse UI → Settings → API Keys. Put them in `.env` (not committed).

### Code

| File | Role |
|------|------|
| `src/observability/langfuse_client.py` | `get_langfuse_client()` — lazy singleton, never raises |
| `src/observability/__init__.py` | exports `get_langfuse_client` |

**Behaviour:**

- First call initializes once (`_initialized` flag).
- Missing keys → `None` + **warning** log (app keeps running).
- Bad keys / network error on init → `None` + **warning** log.
- Success → returns `Langfuse` instance + **info** log.

### Log messages (logger: `observability.langfuse_client`)

| Case | Level | Message |
|------|-------|---------|
| Keys missing | WARNING | `Langfuse disabled: LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY are not both set` |
| Init failed | WARNING | `Langfuse client init failed; tracing unavailable` (+ `extra.error`, `extra.host`) |
| Init OK | INFO | `Langfuse client initialized` (+ `extra.host`) |

After Step 1 JSON logging is active, these appear as JSON lines with the same `message` string.

### Verify module loads

```powershell
cd g:\projects\dashnotesystemv1
$env:PYTHONPATH = "src"
pip install "langfuse>=2.60.0,<4" -q

# Import only (no client call)
python -c "from observability.langfuse_client import get_langfuse_client; print('PASS: import ok')"
```

### Verify missing keys

```powershell
$env:LANGFUSE_PUBLIC_KEY = ""
$env:LANGFUSE_SECRET_KEY = ""
python -c "
import importlib
import observability.langfuse_client as lc
importlib.reload(lc)
c = lc.get_langfuse_client()
assert c is None
print('PASS: client is None when disabled')
"
```

Expect WARNING with message containing `Langfuse disabled`.

### Verify with keys (optional)

Set real keys in `.env` or env vars, then:

```powershell
python -c "
from observability import setup_logging, get_langfuse_client
setup_logging()
client = get_langfuse_client()
print('client:', type(client).__name__ if client else None)
"
```

Expect INFO `Langfuse client initialized` and a `Langfuse` instance.

### Docker

Rebuild after `requirements/base.txt` change:

```powershell
docker compose build api
docker compose up -d api
```

API must start without calling `get_langfuse_client()` at boot.

---

## Step 3 — RAG tracing (`tracing.py` + `RagService`)

### Code

| File | Role |
|------|------|
| `src/observability/tracing.py` | `rag_trace`, `rag_span` — async context managers, no-op when Langfuse disabled |
| `src/observability/__init__.py` | exports `rag_trace`, `rag_span` |
| `src/ai/services/rag_service.py` | `answer()` and `stream_answer()` only |

**Behaviour:**

- Root observation name: `rag.answer` (metadata: `workspace_id`, `user_id`, `role`).
- Child spans: `retrieval` → `context_building` → `llm_generation` (generation type for LLM).
- Each span records `latency_ms` in output on exit; callers add domain fields via `span.update(output={...})`.
- `rag_trace` flushes the Langfuse client in `finally`; never raises.
- Langfuse Python SDK v4 uses `start_observation` under the hood (no direct `client.trace()`).

**`RagService` span outputs:**

| Span | Recorded output |
|------|-----------------|
| `retrieval` | `chunks_retrieved` |
| `context_building` | `chunks_used`, `char_budget` (`TOKEN_BUDGET_PER_REQUEST`) |
| `llm_generation` | `prompt_tokens`, `completion_tokens`, `total_tokens`, `cost` (when LiteLLM returns them) + `latency_ms` |

Empty retrieval (no chunks): only `retrieval` span; trace still flushes.

### Verify module (no HTTP)

```powershell
cd g:\projects\dashnotesystemv1
$env:PYTHONPATH = "src"
python -c "from observability import rag_trace, rag_span; print('PASS')"
python -m ai.services.rag_service
```

### Trigger traces (requires JWT + Langfuse keys in `.env`)

```powershell
docker compose up -d --build api

# Non-streaming
curl.exe -sS -X POST http://127.0.0.1/ai/chat `
  -H "Authorization: Bearer <TOKEN>" `
  -H "Content-Type: application/json" `
  -d "{\"message\": \"What is in my notes?\"}"

# Streaming
curl.exe -sS -X POST http://127.0.0.1/ai/chat/stream `
  -H "Authorization: Bearer <TOKEN>" `
  -H "Content-Type: application/json" `
  -d "{\"message\": \"Summarize my workspace notes.\"}" `
  --no-buffer
```

Replace `<TOKEN>` with a valid workspace JWT.

### Langfuse UI checklist

After one `/ai/chat` and one `/ai/chat/stream` call:

1. Trace named **`rag.answer`** visible (Traces / Observations).
2. Three child spans: **`retrieval`**, **`context_building`**, **`llm_generation`**.
3. Each span output includes **`latency_ms`** (milliseconds).
4. **`retrieval`** output includes **`chunks_retrieved`** (integer).
5. **`context_building`** output includes **`chunks_used`** and **`char_budget`**.
6. **`llm_generation`** shows token fields when LiteLLM populates `response.usage` (and **`cost`** when `_hidden_params.response_cost` is set).
7. Trace input/metadata includes **`workspace_id`**, **`user_id`**, **`role`** (no raw JWT).

If keys are missing, the app runs normally; no traces are sent (no-op path).

---

## Step 4 — Prometheus HTTP metrics

### Dependency

`requirements/base.txt` (Docker image source):

```
prometheus-fastapi-instrumentator >= 0.11.0
```

Installed in API image: **7.1.0** (pulls `prometheus-client` transitively).

### Code (`src/main.py` only)

Instrumentation runs at the end of `create_app()`, after middleware, routes, and exception handlers — before the app serves traffic.

**Note (v7 API):** `metric_namespace` and `metric_subsystem` are passed to `.instrument()`, not `Instrumentator()`. Constructor options `should_group_status_codes` and `should_ignore_untemplated` are unchanged.

```python
from prometheus_fastapi_instrumentator import Instrumentator

# inside create_app(), before return app:
Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=True,
).instrument(
    app,
    metric_namespace="dashnote",
    metric_subsystem="api",
).expose(app, endpoint="/metrics")
```

### Metric prefix

All **HTTP metrics** from the instrumentator use the prefix **`dashnote_api_`** (namespace `dashnote` + subsystem `api`).

Standard process/Python metrics (`python_*`, `process_*`) have no application prefix — that is expected.

### Exact metric names (verified `curl http://localhost:8000/metrics`)

Use these names in Grafana/Prometheus queries (Step 6).

| Role | Exact name | Type |
|------|------------|------|
| Request total counter | `dashnote_api_http_requests_total` | counter |
| Latency histogram (handler labels; SLI dashboards) | `dashnote_api_http_request_duration_seconds` | histogram |
| Latency histogram (many buckets; percentiles) | `dashnote_api_http_request_duration_highr_seconds` | histogram |
| Request body size | `dashnote_api_http_request_size_bytes` | summary |
| Response body size | `dashnote_api_http_response_size_bytes` | summary |

**Step 6 defaults:**

- P95 latency: `histogram_quantile(0.95, sum(rate(dashnote_api_http_request_duration_seconds_bucket[5m])) by (le))`
- Request rate: `sum(rate(dashnote_api_http_requests_total[5m]))`
- Error rate (5xx): filter `dashnote_api_http_requests_total` with `status=~"5.."`

Labels on the counter/handler histogram: `handler`, `method`, `status` (status not grouped into families because `should_group_status_codes=False`).

### Verify

```powershell
cd g:\projects\dashnotesystemv1
docker compose up -d --build api

# Generate at least one request (optional but populates handler metrics)
curl.exe -sS http://localhost:8000/health

curl.exe -sS http://localhost:8000/metrics
```

Expect `# TYPE dashnote_api_http_requests_total counter` and histogram types for `dashnote_api_http_request_duration_*`.

### Rules

- No custom metrics in this step.
- Do not instrument in routers, services, or `src/observability/`.

---

## Step 5 — Prometheus + Grafana (Docker)

### Files

| Path | Role |
|------|------|
| `monitoring/prometheus.yml` | Scrape `api:8000` at `/metrics`, 15s interval |
| `docker-compose.yml` | `prometheus` (256m) + `grafana` (512m) services |
| `monitoring/grafana/provisioning/` | Mount point for Step 6 datasources/dashboards |

### Prometheus config

- **Job:** `dashnote_api` → `http://api:8000/metrics`
- **Retention:** 7d (`--storage.tsdb.retention.time=7d`)
- **Image:** `prom/prometheus:v2.51.2`

### Grafana config

- **URL:** http://localhost:3001 (host port `3001` → container `3000`)
- **Login:** `admin` / password from `GRAFANA_ADMIN_PASSWORD` in `.env` (default `changeme` via Compose)
- **Sign-up / anonymous:** disabled in Compose env
- **Image:** `grafana/grafana:10.4.2`
- **Datasource/dashboards:** Step 6 adds files under `monitoring/grafana/provisioning/`

### Env (`.env.example`)

```env
GRAFANA_ADMIN_PASSWORD=changeme
```

Compose maps this to `GF_SECURITY_ADMIN_PASSWORD` on the Grafana service.

### mem_limit note

`mem_limit` on `prometheus` and `grafana` is enforced by Docker Engine directly. `deploy.resources` is only respected in Swarm mode and is not used here.

### Bring up / verify

```powershell
cd g:\projects\dashnotesystemv1
docker compose up -d prometheus grafana
```

Ensure `api` is running (scrape target is the API container hostname `api` on the Compose network):

```powershell
docker compose up -d api
```

### Validation gate (confirmed)

| Check | URL / command | Expected |
|-------|----------------|----------|
| Prometheus targets | http://localhost:9090/targets | Job **`dashnote_api`**, endpoint `http://api:8000/metrics`, **State: UP** (green) |
| Targets API | `curl.exe -sS http://localhost:9090/api/v1/targets` | `"health":"up"` for `job":"dashnote_api"` |
| Grafana UI | http://localhost:3001/login | HTTP 200, login page loads |

On the targets page, **State: UP** means the last scrape succeeded (`health: up` in the API). If the API container is down, the target shows **DOWN** with a last error such as connection refused.

### Rules

- Do not change existing Compose services when editing monitoring stack.
- Prometheus scrapes the **`api`** service directly (not nginx on :80).

---

## Step 6 — Grafana dashboards + docs

**Human guide:** [`docs/observability.md`](../../docs/observability.md) (architecture, validation, troubleshooting). Also referenced from `src/docs/system.md`, `src/docs/ai.md`, and `src/docs/lld.md` §4.16.

### Provisioning files

| File | Role |
|------|------|
| `monitoring/grafana/provisioning/datasources/prometheus.yml` | Default Prometheus datasource → `http://prometheus:9090` |
| `monitoring/grafana/provisioning/dashboards/dashboard.yml` | File provider, folder **DashNote** |
| `monitoring/grafana/provisioning/dashboards/api_overview.json` | **API Overview** — 4 panels |

### Dashboard queries (Step 4 metric names only)

| Panel | Expression |
|-------|------------|
| Request Rate | `sum(rate(dashnote_api_http_requests_total[5m]))` |
| Error Rate (5xx) | `sum(rate(dashnote_api_http_requests_total{status=~"5.."}[5m]))` |
| P95 Latency | `histogram_quantile(0.95, sum(rate(dashnote_api_http_request_duration_seconds_bucket[5m])) by (le))` |
| P99 Latency | `histogram_quantile(0.99, sum(rate(dashnote_api_http_request_duration_seconds_bucket[5m])) by (le))` |

Uses `_bucket` because Step 4 confirmed `dashnote_api_http_request_duration_seconds_bucket` on `/metrics`.

### Reload + validate

```powershell
docker compose restart grafana
# UI: http://localhost:3001 → DashNote folder → API Overview
1..10 | ForEach-Object { curl.exe -sS http://localhost:8000/health | Out-Null }
```

### Images

Pinned `prom/prometheus:v2.51.2` and `grafana/grafana:10.4.2` are the standard lightweight official images; see `docs/observability.md` for alternatives note.

---

## Stack (live)

```
Nginx → FastAPI
          ├─ JSON logs (stdout)
          ├─ Langfuse (RAG/agent traces)
          └─ Prometheus → Grafana
```
