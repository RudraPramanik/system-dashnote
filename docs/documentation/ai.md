## DashNoteSystem AI

Multi-tenant note **and file** embeddings: chunk → Redis cache → LiteLLM → **Qdrant** (`notes_chunks` + `files_chunks`, dim **3072**). API enqueues ARQ jobs; worker indexes vectors. Fast RAG and the agent search **both** collections via `WorkspaceVectorSearch`.

**Related:** platform [system.md](./system.md) · import laws [rules.md](./rules.md) · validation [observe.md](./observe.md) · runbook [observability.md](../observability.md) · soft AI probe `GET /health/ai`

### Architecture laws (enforce in all AI code)

| Law | Rule |
|-----|------|
| Imports | `from config import settings` / `get_settings` — never `from src.config` |
| `src/ai/*` | Only `config`, `ai.*`, `shared.*`, stdlib, third-party |
| `src/worker/*` | Only `config`, `ai.*`, `shared.*` — no raw Qdrant in tasks |
| Qdrant | `workspace_id` **must** filter on every search query; inject from `RequestContext` / `IndexingRequest` only |
| Qdrant search | **`WorkspaceVectorSearch`** in `ai/retrieval/wrapper.py` only — queries `notes_chunks` **and** `files_chunks` (merge by score); never `AsyncQdrantClient` in routers |
| Qdrant writes | `WorkspaceVectorIndex` + `NoteVectorIndexer` (notes); `WorkspaceFileVectorIndex` + `FileVectorIndexer` (files) — worker/indexer path only |
| RBAC filter | `build_rbac_filter()` in `ai/retrieval/filters.py` — mirrors `notes/permissions.py` exactly |
| Routers | Test: **`GET /ai/test-search`**; chat: **`POST /ai/chat`**, **`POST /ai/chat/stream`**; agent: **`POST /ai/agent`**, **`POST /ai/agent/stream`**, **`POST /ai/agent/resume`**, **`POST /ai/agent/reject`** |
| Services | **`RagService.answer()`** / **`stream_answer()`** — plain `workspace_id` / `user_id` / `role` strings only |
| Streaming | SSE citations in final `metadata` event only — never parsed from token stream; quiet streams emit SSE comment heartbeats (`ai_routes/sse_heartbeat.py`) |
| HITL | Mutation tools (`create_note`, `update_note`) interrupt → `approval_required` then stream ends; client reconnects via resume/reject |
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
| `LLM_MODEL` | `nvidia_nim/nvidia/nemotron-3.5-lightning-30b-a3b` | Primary chat/agent/automation model (LiteLLM prefix) |
| `LLM_MODEL_FALLBACKS` | `gemini/gemini-2.5-flash` | Tried in order after HTTP 410 / model gone **or** wall-clock timeout — see `issue_solve.md` |
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
| `shared/llm/fallback.py` | `acompletion_with_fallback` / `resolve_llm_model` — wall-clock abort + walk `LLM_MODEL` then `LLM_MODEL_FALLBACKS` on 410 or timeout |
| `shared/llm/structured.py` | `extract_json_blob()`, `parse_structured_response()`, `acompletion_structured()`, `StructuredLLMParseError` |

**Import law:** `shared/llm/*` may import `config`, `litellm`, `pydantic`, `tenacity`, stdlib only. Both `src/worker/*` and `src/ai/*` import from `shared/llm/` — never `worker` from `ai`.

**Consumers:**

| Caller | Function | On transient failure |
|--------|----------|----------------------|
| `generate_note_tags`, `generate_file_metadata` | `acompletion_structured` | Re-raise → ARQ job retry |
| `AutomationDecisionEngine.evaluate_action` | `acompletion_structured` | Fail-safe block (`is_destructive=True`) |
| `workspace_assistant.call_model`, `RagService` | `acompletion_with_fallback` | Exhausted candidates → **503** / `LLMUnavailableError` |

**Log markers:** `[AUTOMATION_LLM_RETRY_EXHAUSTED]`, `[AUTOMATION_LLM_PARSE_FAIL]`, `[AUTOMATION_LLM_AUTH_FAIL]`

**Embedding retry** stays in `ai/embeddings/litellm_provider.py` — not merged into `shared/llm/`.

**Soft health:** `GET /health/ai` reports Qdrant + LLM reachability; never part of hard `GET /health`.

**Agent / chat HTTP:** `ai_routes/agent.py` and chat map exhausted LLM to **503** `"LLM temporarily unavailable; retry shortly"` (not opaque 500). Streams use `iter_with_heartbeat` so nginx does not drop a quiet first hop.

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

Stream headers: `Cache-Control: no-cache`, `X-Accel-Buffering: no`. Quiet streams also emit SSE comment heartbeats via `iter_with_heartbeat`. Citations from **top retrieved chunks** (not the token stream). Shape: `{ note_id, chunk_id, title, relevance_score, source_type, file_id }` with `source_type` `note` | `file`. Empty retrieval: *I could not find relevant information in your notes and files for this query.*

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
| `PATCH /ai/threads/{thread_id}` | Rename thread (`{ "title": "..." }`) |
| `DELETE /ai/threads/{thread_id}` | Soft delete (`is_active=false`) |

Cross-workspace access: **404** on thread routes, **400** on chat reuse. `workspace_id` always from JWT, never query/body/path.

---

## Slice 6 — LangGraph workspace assistant (+ HITL)

Adds **`POST /ai/agent`**, **`POST /ai/agent/stream`**, **`POST /ai/agent/resume`**, **`POST /ai/agent/reject`**. **`/ai/chat*`** unchanged (fast RAG).

| Path | Role |
|------|------|
| `ai/memory/checkpointer.py` | `AsyncPostgresSaver` (psycopg3); `init_checkpointer()` in lifespan |
| `ai/hitl.py` | Interrupt extraction → `approval_required` event fields |
| `notes/service.py` | `create_note()` / `update_note()` for agent tools |
| `ai/tools/schemas.py` | Pydantic `args_schema` models |
| `ai/tools/note_tools.py` | Four `StructuredTool`s; `db_session_var` for mutations; HITL before create/update side effects |
| `ai/workflows/state.py` | `AgentState` — messages, tenant fields, `steps_taken`, `thread_id` |
| `ai/workflows/workspace_assistant.py` | Graph: `START → agent → tools → agent → END`; lazy compile |
| `ai_routes/agent.py` | Agent HTTP endpoints |
| `ai_routes/sse_heartbeat.py` | SSE comment keepalives for quiet streams |

**Tool chain** (never shortcut to repository):

| Tool | Service | HITL |
|------|---------|------|
| `search_notes` | `RagService.answer(...)` — notes **and** indexed files | No |
| `create_note` | `NoteService.create_note(db, ...)` — `db` from `db_session_var` | **Yes** — interrupt before persist |
| `update_note` | `NoteService.update_note(db, ...)` | **Yes** — interrupt before persist |
| `summarize_workspace` | `RagService.answer(..., retrieval_limit=12)` | No |

**Agent contract:**

| Route | Behavior |
|-------|----------|
| `POST /ai/agent` | JSON: completed turn **or** `approval_required` (`tool`, `args`, `thread_id`, `interrupt_id`) |
| `POST /ai/agent/stream` | SSE: `token`, `tool_start`, `tool_end`, `approval_required`, `done`/`error`, `[DONE]`. After `approval_required`, stream **ends** |
| `POST /ai/agent/resume` | Body `{ thread_id, interrupt_id? }` — JWT workspace only; continues pending mutation |
| `POST /ai/agent/reject` | Same body — ends turn without applying create/update |

LangGraph config: `{"configurable": {"thread_id": thread_id}}`. LiteLLM `tools=` with OpenAI function defs — not LangChain `.bind_tools()`. `call_model` uses `shared.llm.acompletion_with_fallback` (wall-clock + candidate walk).

Slice 6 invariants: see [rules.md](./rules.md). HITL blueprint history: [blueprint/slice8_hitl.md](./blueprint/slice8_hitl.md).

---

## Observability

RAG instrumentation via `observability.tracing` (`rag_trace` → spans `retrieval`, `context_building`, `llm_generation`). HTTP metrics at `GET /metrics` (`dashnote_api_*`). Soft AI readiness: **`GET /health/ai`**. Details and validation commands: **[observe.md](./observe.md)**.

---

## Related docs

| Doc | Content |
|-----|---------|
| [system.md](./system.md) | Routers, tenancy, Compose, rate limits, `/health` vs `/health/ai` |
| [rules.md](./rules.md) | Import direction, Slice 6 modification laws |
| [lld.md](./lld.md) | §4.12–4.18 (flows, retrieval, RAG, agent, automation, shared LLM) |
| [observe.md](./observe.md) | Validation commands, observability steps |
| [frontendguide.md](./frontendguide.md) | Client SSE + HITL Approve/Reject |
| [blueprint/](./blueprint/) | Per-slice build history and sign-off gates |
| [blueprint/slice7-llm-hardening.md](./blueprint/slice7-llm-hardening.md) | Slice 7.5 recovery blueprint and gate criteria |
