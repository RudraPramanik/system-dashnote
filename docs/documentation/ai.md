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
| `LLM_MODEL` | `gemini/gemini-2.5-flash` | Chat via LiteLLM |
| `LLM_TEMPERATURE` | `0.0` | Deterministic answers |
| `LLM_MAX_TOKENS` | `2048` | Max completion tokens |
| `TOKEN_BUDGET_PER_REQUEST` | `8000` | Char budget for retrieved context |
| `AI_THREAD_MESSAGE_LIMIT` | `20` | History loaded per turn |
| `AGENT_MAX_ITERATIONS` | (see `config.py`) | Tool loop guard |
| `ai_enabled` | property | `OPENAI_API_KEY` or `GEMINI_API_KEY` set |
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

## Slice 7 — event-driven automation (7.0–7.2)

| Path | Role |
|------|------|
| `shared/events/definitions.py` | Frozen Pydantic event schemas (`NoteCreatedEvent`, `FileUploadedEvent`, …) — **extend payloads only** |
| `shared/events/bus.py` | `emit_event()` — maps `EventType` → ARQ task name; never raises |
| `shared/utils/parsers.py` | `FileParsingEngine` — sync text extraction (PDF, DOCX, HTML, text/*); CPU-bound, no DB/FastAPI |
| `worker/automation/tasks.py` | `handle_file_uploaded` extracts text + saves `extracted_text`; other handlers stubbed until 7.3 |
| `worker/main.py` | Registers automation tasks; `ctx["arq_pool"]` for fan-out; imports all ORM models at startup |

**Event → task routing:**

| Event | ARQ task |
|-------|----------|
| `file.uploaded` | `handle_file_uploaded` |
| `note.created` | `handle_note_created` |
| `note.updated` | `handle_note_updated` |
| `file.deleted` | `handle_file_deleted` |

**File upload pipeline (7.2):** upload → `FileUploadedEvent` → worker downloads via `get_storage()` → `FileParsingEngine.extract_text()` (executor) → persist `files.extracted_text`. Fan-out to indexing + metadata in **7.3**.

**Files model (7.2):** `extracted_text`, `summary` (nullable `Text`); `tags` (`JSONB`, default `[]`). Migration: `95fb65156e52`. Deps: `pypdf`, `python-docx`, `beautifulsoup4`, `lxml`.

**Coexistence:** Slice 1 `embed_note_task` enqueue in `notes/router.py` is unchanged. Slice 7 adds a second `emit_event()` call after note create. File upload emits `FileUploadedEvent` only (no direct embed enqueue).

**Worker context:** `ctx["redis"]` (Slice 1 cache) + `ctx["arq_pool"]` (Slice 7 fan-out). Worker DB: `AsyncSessionLocal` directly — never `get_session()`. Storage download: `get_storage().download(storage_key)`.

**Validation (Compose):**

```powershell
docker compose up -d --build api worker
docker compose exec -e PYTHONPATH=/app/src api python -m shared.utils.parsers
python -m pytest tests/shared/test_parsers.py -q
# POST /files/upload (.txt or .pdf) → wait ~10s
docker compose exec db psql -U dashuser -d dashnotes \
  -c "SELECT name, length(extracted_text) FROM files ORDER BY created_at DESC LIMIT 3;"
# Expect length(extracted_text) > 0
docker compose logs worker --tail 20
# Expect: handle_file_uploaded: extracted_text saved
```

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

**Agent contract:** `POST /ai/agent` → `AgentResponse` (`answer`, `thread_id`, `steps_taken`, `tool_calls_made`). Stream: SSE from `graph.astream_events` (`token`, `tool_start`, `tool_end`, `done`, `[DONE]`). LangGraph config: `{"configurable": {"thread_id": thread_id}}`. LiteLLM `tools=` with OpenAI function defs — not LangChain `.bind_tools()`.

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
| `src/docs/lld.md` | §4.12–4.16 (flows, retrieval, RAG, agent, observability) |
| `src/docs/observe.md` | Validation commands, observability steps |
| `src/docs/blueprint/slice*.md` | Per-slice build history and sign-off gates |
