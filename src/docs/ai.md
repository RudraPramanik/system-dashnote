## DashNoteSystem AI

Multi-tenant note embeddings: chunk → Redis cache → LiteLLM → **Qdrant** (`notes_chunks`, dim **3072**). API enqueues ARQ jobs; worker indexes vectors. Platform stack: `src/docs/system.md`. Import laws: `src/docs/rules.md`. Observability: `docs/observability.md`, `src/docs/observe.md`.

### Architecture laws (enforce in all AI code)

| Law | Rule |
|-----|------|
| Imports | `from config import settings` / `get_settings` — never `from src.config` |
| `src/ai/*` | Only `config`, `ai.*`, `shared.*`, stdlib, third-party |
| `src/worker/*` | Only `config`, `ai.*`, `shared.*` — no raw Qdrant in tasks |
| Qdrant | `workspace_id` **must** filter on every search query; inject from `RequestContext` / `IndexingRequest` only |
| Qdrant search | **`WorkspaceVectorSearch`** in `ai/retrieval/wrapper.py` only — never `AsyncQdrantClient` in routers |
| Qdrant writes | `WorkspaceVectorIndex` + `NoteVectorIndexer` — worker/indexer path only |
| RBAC filter | `build_rbac_filter()` in `ai/retrieval/filters.py` — mirrors `notes/permissions.py` exactly |
| Routers | Test search: **`GET /ai/test-search`** (`ai_gateway/search.py`); chat: **`POST /ai/chat`** (`ai_routes/chat.py`) |
| Services | **`RagService.answer()`** / **`stream_answer()`** (`ai/services/rag_service.py`) — plain `workspace_id` / `user_id` / `role` strings only |
| Streaming | **`POST /ai/chat/stream`** (SSE) — same prompt/RBAC/budget as `/ai/chat`; citations in final `metadata` event only |
| Memory ORM | **`src/ai_memory/`** — `AIThread`, `AIMessage`; never import SQLAlchemy from `src/ai/*` |
| Memory service | **`ThreadService`** (`ai/memory/service.py`), **`ContextBuilder`** (`ai/memory/context_builder.py`) |
| Agent tools | **`get_note_tools()`** (`ai/tools/note_tools.py`) — `StructuredTool` + Pydantic `args_schema`; service layer only |
| Note mutations (agent) | **`NoteService`** (`notes/service.py`) — `db_session_var` set by graph tool node before create/update |
| Checkpointer | **`init_checkpointer()`** / **`get_graph_checkpointer()`** (`ai/memory/checkpointer.py`) — psycopg3, separate from SQLAlchemy pool |
| LLM tracing | **`observability.tracing`** (`rag_trace`, `rag_span`) only — **no** Langfuse SDK in `src/ai/*` |
| Infra | Append-only to `settings`, `.env`, `docker-compose.yml`, `requirements*.txt` |

---

## Slice 1 (complete) — embeddings pipeline

**Config** (`config.py`): `EMBEDDING_MODEL` default `gemini/gemini-embedding-2`, `EMBEDDING_DIMENSION=3072`, chunking, ARQ, `ai_enabled` when `OPENAI_API_KEY` or `GEMINI_API_KEY` is set.

**Modules**

| Path | Role |
|------|------|
| `shared/contracts/indexing.py` | `IndexingRequest`, `IndexingResult`, `IndexingOperation` |
| `ai/embeddings/chunker.py` | Deterministic `chunk_id` (uuid5), title prepended as H1 |
| `ai/embeddings/litellm_provider.py` | Batched `litellm.aembedding` + tenacity |
| `ai/embeddings/factory.py` | `get_embedding_provider()` singleton |
| `ai/services/cache.py` | Redis `embed:v1:{sha256(text)}` |
| `ai/workflows/pipeline.py` | `EmbeddingPipeline.process_note` → `EmbeddedChunk[]` |
| `worker/ingestion/tasks.py` | `embed_note_task` |
| `notes/router.py` | Enqueue after commit when `ai_enabled` |

**Compose**: `worker`, `qdrant` (:6333), `ARQ_REDIS_URL` / `REDIS_URL`.

---

## Slice 2 (current) — RBAC search, Qdrant indexing, quality gate

### Settings

| Field | Default | Purpose |
|-------|---------|---------|
| `QDRANT_URL` | `None` | e.g. `http://127.0.0.1:6333` (host) or `http://qdrant:6333` (Compose) |
| `QDRANT_API_KEY` | `None` | Qdrant Cloud |
| `QDRANT_NOTES_COLLECTION` | `notes_chunks` | Single collection for note chunks |
| `QDRANT_TIMEOUT` | `30` | Client timeout (seconds) |
| `qdrant_enabled` | property | `bool(QDRANT_URL)` |

### Module layout — `ai/retrieval/`

| File | Role |
|------|------|
| `client.py` | `get_async_qdrant_client()` singleton (retrieval package only) |
| `collection.py` | `ensure_notes_collection()` — cosine, `EMBEDDING_DIMENSION` |
| `filters.py` | **`build_rbac_filter(workspace_id, user_id, role)`** — pure Qdrant Filter; mirrors `notes/permissions.py` |
| `wrapper.py` | **`WorkspaceVectorSearch`** — embed query + `query_points` + RBAC; **`get_workspace_vector_search()`** singleton |
| `workspace_search.py` | **`WorkspaceVectorIndex`** — upsert/delete-by-note (indexing only) |
| `indexer.py` | `NoteVectorIndexer` — delete-then-upsert per note (worker-facing) |

### RBAC filter (`build_rbac_filter`)

Aligned with `notes/permissions.py`:

| Role | Qdrant filter |
|------|----------------|
| `owner`, `admin` | `must`: `workspace_id` |
| `member` | `must`: `workspace_id` **and** (`visibility=public` **or** `created_by=user_id`) |

Payload field `visibility`: `"public"` ↔ `is_private=False`, `"private"` ↔ `is_private=True`.

`workspace_id` is **never** optional and **never** taken from request query/body on search routes.

### Qdrant payload (indexed chunks)

| Field | Purpose |
|-------|---------|
| `workspace_id` | Tenant isolation (mandatory filter) |
| `note_id`, `chunk_id`, `chunk_index` | Identity / ordering |
| `text`, `chunk_text` | Chunk body (search display; `text` preferred by wrapper) |
| `title` | Note title for display / retrieval context |
| `created_by` | Member RBAC (own private notes) |
| `visibility` | `"public"` \| `"private"` for member RBAC |
| `is_private` | Legacy bool (kept for re-index compatibility) |
| `token_count`, `char_start`, `char_end` | Metrics / debugging |

Point id = UUID from deterministic `chunk_id`.

### HTTP — internal test search

**Route**: `GET /ai/test-search`  
**Module**: `ai_gateway/search.py`  
**Auth**: `Authorization: Bearer` → `RequestContext` (`sub`, `wid`, `role`)

| Query param | Source |
|-------------|--------|
| `q` | User query (1–500 chars) |
| `limit` | Max hits (1–20, default 5) |
| `workspace_id` | **Never accepted** — always `ctx.workspace_id` from JWT |

**503** when `ai_enabled` or `qdrant_enabled` is false.

**Response** (per hit): `chunk_id`, `note_id`, `title`, `chunk_text` (truncated), `score`, `visibility`, `chunk_index`, `workspace_id`.

### Quality gate (Sub-step 2.2)

Before promoting search to product routes:

1. **Relevance**: cosine `score` > **0.4** for queries that match indexed note content.
2. **Tenant isolation**: every `workspace_id` in results equals JWT `wid`; another workspace’s JWT returns empty or only that workspace’s data.
3. **Member RBAC**: members do not see other members’ private notes; own private + all public notes are visible.

**Tuning** if scores are low:

- Scores &lt; 0.3 → verify `EMBEDDING_DIMENSION=3072` matches model.
- Scores &lt; 0.4 → try `CHUNK_SIZE` 600–800 and re-index.
- Irrelevant hits → confirm chunker prepends title as H1.
- Empty results → check Qdrant payload indexes; re-index after payload schema changes.

### Worker flow (`embed_note_task`)

```
IndexingRequest
  → DELETE: NoteVectorIndexer.delete_note (if qdrant_enabled)
  → UPSERT: EmbeddingPipeline → NoteVectorIndexer.index_note_chunks
  → logs: qdrant_indexed, qdrant_points
```

When `QDRANT_URL` is unset, embeddings still run; `qdrant_indexed=false`.

### Validation commands

```powershell
docker compose up -d --build api

# Route exists (401 without token)
curl.exe -sS http://127.0.0.1/ai/test-search?q=test

# Authenticated search
Invoke-RestMethod `
  -Uri "http://127.0.0.1/ai/test-search?q=your+note+content&limit=5" `
  -Headers @{ Authorization = "Bearer <YOUR_TOKEN>" }
```

```powershell
cd g:\projects\dashnotesystemv1
$env:PYTHONPATH="src"
$env:QDRANT_URL="http://127.0.0.1:6333"
python -m ai.retrieval.indexer
```

### Dependencies

`qdrant-client ~= 1.16.0` under `# --- AI Slice 2: Qdrant vector retrieval ---` in `requirements/base.txt`.

---

## Slice 3 (complete) — RAG chat MVP

### Settings (Sub-step 3.1)

| Field | Default | Purpose |
|-------|---------|---------|
| `LLM_MODEL` | `gemini/gemini-2.5-flash` | Chat completion via LiteLLM |
| `LLM_TEMPERATURE` | `0.0` | Deterministic answers |
| `LLM_MAX_TOKENS` | `2048` | Max completion tokens |
| `TOKEN_BUDGET_PER_REQUEST` | `8000` | Char budget for retrieved context sent to LLM |
| `LANGSMITH_API_KEY` | `None` | Wired for Slice 10 |
| `LANGSMITH_PROJECT` | `dashnote` | LangSmith project name |
| `LANGSMITH_TRACING_ENABLED` | `False` | Inactive; Langfuse is the active trace path |
| `langsmith_enabled` | property | `bool(LANGSMITH_API_KEY) and LANGSMITH_TRACING_ENABLED` |
| `LANGFUSE_PUBLIC_KEY` | `""` | Langfuse project public key |
| `LANGFUSE_SECRET_KEY` | `""` | Langfuse secret key |
| `LANGFUSE_HOST` | `https://cloud.langfuse.com` | EU cloud; US: `https://us.cloud.langfuse.com` |
| `langfuse_enabled` | property | Both Langfuse keys non-empty |

### Module layout — prompts + service

| Path | Role |
|------|------|
| `ai/prompts/rag.py` | `RAGAnswer` (structured output), `RAG_SYSTEM_INSTRUCTION`, `build_rag_user_message()` |
| `ai/services/rag_service.py` | `RagService.answer()` — retrieve → budget → LLM → ground citations → `ChatResult` |
| `observability/tracing.py` | `rag_trace` / `rag_span` wrap `answer()` and `stream_answer()` (Langfuse observations when enabled) |

**Import law**: `rag_service.py` imports only `litellm`, `pydantic`, `config`, `ai.retrieval.*`, `ai.prompts.*`, `observability.tracing`, stdlib — no FastAPI, SQLAlchemy, `RequestContext`, or Langfuse SDK.

### HTTP — `POST /ai/chat` (Sub-step 3.2)

**Module**: `ai_routes/chat.py`  
**Auth**: `Authorization: Bearer` → `RequestContext`; ctx frozen to plain strings before `RagService.answer()`.

| Body field | Constraints |
|------------|-------------|
| `message` | 1–2000 chars |

**Response**: `answer` (markdown), `citations[]` (`note_id`, `chunk_id`, `title`, `relevance_score`), `chunks_retrieved`, `chunks_used`, `latency_ms`.

**Not in Slice 3**: `thread_id` / memory, LangGraph agents.

---

## Slice 5 (current) — Conversation memory

### Settings (Sub-step 5.1)

| Field | Default | Purpose |
|-------|---------|---------|
| `AI_THREAD_MESSAGE_LIMIT` | `20` | Recent messages loaded into LLM context per turn |

### Module layout — persistence + service

| Path | Role |
|------|------|
| `ai_memory/models.py` | `AIThread`, `AIMessage` SQLAlchemy models (product layer) |
| `ai_memory/repository.py` | `ThreadRepository` — stateless, `AsyncSession` per method, workspace filter on every query |
| `ai/memory/service.py` | `ThreadService` — get/create thread, load history, persist turn |
| `ai/memory/context_builder.py` | `ContextBuilder.build()` — `[system, ...history, user+context]` with char budget |

**Import law**: `ai/memory/*` imports `ai_memory.repository`, `config`, `ai.prompts.rag` only — no SQLAlchemy, no FastAPI, no `RequestContext`.

### RagService integration (Sub-step 5.2)

| Change | Detail |
|--------|--------|
| `ChatResult.thread_id` | Optional UUID string returned after each turn |
| `StreamMetadata.thread_id` | Same for streaming clients |
| `_load_thread_context()` | Resolves thread via `ThreadService`; loads history when `thread_id` set |
| `ContextBuilder` | Replaces manual step-2/3 budget + prompt assembly in `answer()` / `stream_answer()` |
| `persist_turn()` | After LLM completes (or stream ends), saves user + assistant messages |

`RagService` accepts `thread_id: str | None` and `db: AsyncSession | None`. Session is passed from `ai_routes/chat.py` via `Depends(get_session)` — never imported at module level in `rag_service.py` (TYPE_CHECKING only).

### HTTP — `POST /ai/chat` and `/ai/chat/stream` (memory fields)

| Body field | Purpose |
|------------|---------|
| `message` | User question (required) |
| `thread_id` | Optional — continue existing thread; omit to create new |

| Response field | Purpose |
|----------------|---------|
| `thread_id` | Use on next request to continue conversation |

### Slice 5.3 (complete) — Thread management routes

Thread management HTTP routes live in `ai_routes/threads.py` and are mounted in `main.py`:

- `GET /ai/threads` — list current user conversation threads in JWT workspace.
- `GET /ai/threads/{thread_id}/messages` — load UI message history (default limit 50).
- `DELETE /ai/threads/{thread_id}` — soft delete (`is_active=false`) with workspace isolation.

Security contract:

- `workspace_id` is always read from JWT `RequestContext` (`wid`), never from query/body/path.
- Cross-workspace thread access returns `404` for thread routes and `400` for chat reuse attempts.

### Slice 5.3 validation (executed)

Validated with `docker compose up -d --build api` and fresh `POST /auth/register` tokens:

- Gate 1: first `POST /ai/chat` with `thread_id: null` returns non-null UUID `thread_id`.
- Gate 2: second `POST /ai/chat` with same `thread_id` succeeds and reuses thread.
- Gate 3: `GET /ai/threads` returns list containing created thread id.
- Gate 4: `GET /ai/threads/{thread_id}/messages` returns ordered messages (`user,assistant,user,assistant`).
- Gate 5: different-workspace token + foreign `thread_id` returns HTTP `400`.
- Gate 6: `POST /ai/chat/stream` returns SSE token + metadata including `thread_id`, and terminal `data: [DONE]`.
- Gate 7: `DELETE /ai/threads/{thread_id}` returns HTTP `204`.
- Gate 8: `GET /health` unchanged (`status: ok`).

**Not in Slice 5**: LangGraph checkpointer integration (Slice 6).

---

## Observability (complete) — Langfuse + Prometheus

RAG paths are instrumented without changing public API contracts. Full stack: `docs/observability.md`.

### Langfuse (RAG traces)

| Item | Detail |
|------|--------|
| Enable | `LANGFUSE_PUBLIC_KEY` + `LANGFUSE_SECRET_KEY` in `.env` |
| Client | `get_langfuse_client()` — lazy; **not** called from `main.py` lifespan |
| Instrumentation | `RagService.answer()` / `stream_answer()` via `rag_trace` → spans `retrieval`, `context_building`, `llm_generation` |
| Root observation | `rag.answer` with metadata `workspace_id`, `user_id`, `role` |
| Agent tools | `search_notes` / `summarize_workspace` call `RagService.answer()` — traces follow the same path |

**Validate:** `POST /ai/chat` with JWT + keys → Langfuse UI shows `rag.answer` and three child spans (checklist in `src/docs/observe.md` Step 3).

### Prometheus metrics (HTTP)

Exposed at `GET /metrics` (`prometheus-fastapi-instrumentator` in `main.py`). Prefix **`dashnote_api_`**.

| Metric | Use in Grafana |
|--------|----------------|
| `dashnote_api_http_requests_total` | Request rate, 5xx error rate |
| `dashnote_api_http_request_duration_seconds_bucket` | P95/P99 via `histogram_quantile` |

Compose **`prometheus`** scrapes `api:8000`; **`grafana`** dashboard **API Overview** under folder **DashNote**.

---

## Slice 6 (complete) — LangGraph workspace assistant

`POST /ai/chat` and `POST /ai/chat/stream` are **unchanged** — fast RAG path. Slice 6 adds **`POST /ai/agent`** and **`POST /ai/agent/stream`** (wired in sub-steps 6.3–6.4).

### Sub-step 6.1 — checkpointer, settings, NoteService

| Path | Role |
|------|------|
| `config.py` | `AGENT_MAX_ITERATIONS`, `AGENT_TOOL_TIMEOUT`, `psycopg_database_url` |
| `ai/memory/checkpointer.py` | `AsyncPostgresSaver` via dedicated psycopg3 async connection; `init_checkpointer()` / `close_checkpointer()` |
| `notes/service.py` | Agent-callable `create_note()` / `update_note()` over `NoteRepository` |

**Deps**: `psycopg[async]`, `psycopg-binary` (libpq on slim Docker), `langgraph`, `langgraph-checkpoint-postgres` in `requirements/base.txt`.

### Sub-step 6.2 — StructuredTool definitions

| Path | Role |
|------|------|
| `ai/tools/schemas.py` | Pydantic `args_schema` models (`SearchNotesArgs`, `CreateNoteArgs`, `UpdateNoteArgs`, `SummarizeWorkspaceArgs`) |
| `ai/tools/note_tools.py` | Four `StructuredTool.from_function()` tools; `db_session_var` for mutation tools |
| `ai/tools/__init__.py` | Package marker |

**Tool chain** (never shortcut to repository):

| Tool | Service |
|------|---------|
| `search_notes` | `RagService.answer(question=..., workspace_id, user_id, role)` |
| `create_note` | `NoteService.create_note(db, ...)` — `db` from `db_session_var` |
| `update_note` | `NoteService.update_note(db, ...)` — `db` from `db_session_var` |
| `summarize_workspace` | `RagService.answer(..., retrieval_limit=12)` with broad overview question |

**Invariants**: no FastAPI / `RequestContext` / SQLAlchemy imports in tool modules; tenant IDs passed as plain strings from agent state; LiteLLM receives OpenAI function definitions from `StructuredTool` (not LangChain `.bind_tools()`).

### Sub-step 6.3 — Agent graph (implemented)

| Path | Role |
|------|------|
| `ai/workflows/state.py` | `AgentState` with `messages: Annotated[list, add_messages]`, tenant primitives, `steps_taken`, `thread_id` |
| `ai/workflows/workspace_assistant.py` | LangGraph topology (`START -> agent -> tools -> agent -> END`), LiteLLM tool-calling, routing guard, lazy singleton compile |
| `ai/workflows/workspace_assistent.py` | Backward-compatible alias for `workspace_assistant` |

Runtime behavior:

- `call_model()` uses `litellm.acompletion(..., tools=[OpenAI function defs])` (no LangChain `.bind_tools()`).
- `steps_taken` increments on each model step and is checked by `should_continue()` against `AGENT_MAX_ITERATIONS`.
- `compile_workspace_graph()` tries `get_graph_checkpointer()` and falls back to compile-without-checkpointer when unavailable.
- `get_workspace_assistant()` compiles lazily on first call and caches the compiled graph.

### Sub-step 6.4 — Agent routes + lifespan wiring (implemented)

| Path | Role |
|------|------|
| `ai_routes/agent.py` | New `POST /ai/agent` and `POST /ai/agent/stream` endpoints |
| `main.py` | Registers agent router and wires checkpointer init/cleanup in lifespan |

Endpoint contract:

- `POST /ai/agent` returns `AgentResponse`: `answer`, `thread_id`, `steps_taken`, `tool_calls_made`.
- `POST /ai/agent/stream` emits SSE events from `graph.astream_events(..., version="v2")`:
  - `token` from `on_chat_model_stream`
  - `tool_start` from `on_tool_start`
  - `tool_end` from `on_tool_end`
  - `done` plus final `[DONE]`

Invariants:

- Existing `/ai/chat` and `/ai/chat/stream` are unchanged and remain the fast direct RAG path.
- Route layer freezes `workspace_id`, `user_id`, `role` before async graph calls.
- `db_session_var` is set in route scope before graph execution, enabling mutation tools.
- LangGraph config uses `{"configurable": {"thread_id": thread_id}}` for checkpoint linkage.

### Slice 6.2 validation

```powershell
docker compose build api

docker compose exec -e PYTHONPATH=/app/src api python -c "
from ai.tools.note_tools import get_note_tools
from ai.tools.schemas import SearchNotesArgs, CreateNoteArgs
tools = get_note_tools()
print(f'PASS: {len(tools)} tools loaded')
for t in tools:
    print(f'  tool: {t.name}')
    print(f'  schema: {t.args_schema.__name__}')
args = SearchNotesArgs(question='test', workspace_id='ws1', user_id='u1', role='member')
print(f'PASS: SearchNotesArgs validates: {args.question}')
print('PASS: all tool validations passed')
"
```

### Slice 5 validation

```powershell
docker compose build api

docker compose exec -e PYTHONPATH=/app/src api python -c "
from ai.memory.context_builder import ContextBuilder
from ai.memory.service import ThreadService
builder = ContextBuilder()
built = builder.build(
    question='test',
    history_messages=[{'role':'user','content':'hello'}],
    retrieved_chunks=[{'chunk_id':'abc','note_id':'n1','title':'T','text':'content','score':0.8}]
)
print('PASS: messages:', len(built.messages))
"
# Expected: PASS: messages: 3
```

---

## Slice 4 — RAG streaming (SSE)

### Service layer (Sub-step 4.1)

| Path | Role |
|------|------|
| `ai/services/rag_service.py` | `StreamToken`, `StreamMetadata`, `StreamEvent`; `RagService.stream_answer()` async generator |

**`stream_answer()` pipeline** (mirrors `answer()` for steps 1–3):

1. `WorkspaceVectorSearch.search(...)` + RBAC
2. Char budget: `TOKEN_BUDGET_PER_REQUEST`
3. `build_rag_user_message()` + `RAG_SYSTEM_INSTRUCTION` (no streaming-specific prompt)
4. `litellm.acompletion(..., stream=True)` → yield `StreamToken` per delta
5. Yield `StreamMetadata` with citations from **top 5 retrieved chunks** — never parsed from token stream

### HTTP — `POST /ai/chat/stream` (Sub-step 4.2)

**Module**: `ai_routes/chat.py` (appended below `POST /ai/chat`; Slice 3 route unchanged)  
**Auth**: same JWT → freeze `workspace_id`, `user_id`, `role` **before** `generate()` opens  
**Response**: `text/event-stream` (`StreamingResponse`)

| SSE frame | Example |
|-----------|---------|
| Token | `data: {"type":"token","content":"..."}` |
| Metadata | `data: {"type":"metadata","citations":[...],"chunks_retrieved":N,...}` |
| Terminal | `data: [DONE]` |

**Required headers** (Nginx buffering):

- `Cache-Control: no-cache`
- `X-Accel-Buffering: no`
- `Connection: keep-alive`
- `Transfer-Encoding: chunked`

**Not in Slice 4**: `thread_id` / memory, LangGraph agents.

### Slice 4 validation gate

```powershell
docker compose up -d --build api

# Non-streaming unchanged (JSON)
Invoke-RestMethod -Uri "http://127.0.0.1/ai/chat" -Method Post `
  -Headers @{ Authorization = "Bearer <TOKEN>" } `
  -ContentType "application/json" `
  -Body '{"message": "What is in my notes?"}'

# Streaming (progressive tokens — use --no-buffer)
curl.exe -sS -X POST http://127.0.0.1/ai/chat/stream `
  -H "Authorization: Bearer <TOKEN>" `
  -H "Content-Type: application/json" `
  -d '{"message": "Summarize my workspace notes on project plans."}' `
  --no-buffer

# Health unchanged
curl.exe -sS http://127.0.0.1/health
```

**Sign-off**: tokens arrive progressively (not one blob); penultimate event is `metadata` with `citations`; last line `data: [DONE]`; empty workspace → refusal token + `citations:[]`; `POST /ai/chat` still JSON.

```powershell
docker compose exec -e PYTHONPATH=/app/src api python -m ai.services.rag_service
```

### Slice 3 validation gate

```powershell
docker compose up -d --build api

# 401 without token (route exists + auth enforced)
curl.exe -sS -X POST http://127.0.0.1/ai/chat -H "Content-Type: application/json" -d "@$env:TEMP\chat-body.json"
# (write {"message":"test"} to chat-body.json first)

# Authenticated chat
Invoke-RestMethod -Uri "http://127.0.0.1/ai/chat" -Method Post `
  -Headers @{ Authorization = "Bearer <TOKEN>" } `
  -ContentType "application/json" `
  -Body '{"message": "What is the deadline for project X?"}'
```

**Sign-off criteria**: `latency_ms` < 5000; answer grounded in indexed notes; `citations` ≥ 1 with real `note_id`; empty workspace returns refusal string (not other tenants’ data); `GET /health` unchanged.

```powershell
python -m ai.services.rag_service   # import/schema validation (no LLM call)
```

### Related docs

- `src/docs/system.md` — API wiring, Compose, observability summary
- `src/docs/lld.md` — §4.12–4.19 (retrieval, RAG, agent, observability)
- `src/docs/observe.md` — agent-oriented observability steps
- `docs/observability.md` — human runbook (validation, troubleshooting)
- `src/docs/rules.md` — dependency direction
