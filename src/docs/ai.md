## DashNoteSystem AI

Multi-tenant note embeddings: chunk → Redis cache → LiteLLM → **Qdrant** (`notes_chunks`, dim **3072**). API enqueues ARQ jobs; worker indexes vectors. Platform stack: `src/docs/system.md`. Import laws: `src/docs/rules.md`.

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
| `LANGSMITH_TRACING_ENABLED` | `False` | Enable in Slice 10 |
| `langsmith_enabled` | property | `bool(LANGSMITH_API_KEY) and LANGSMITH_TRACING_ENABLED` |

### Module layout — prompts + service

| Path | Role |
|------|------|
| `ai/prompts/rag.py` | `RAGAnswer` (structured output), `RAG_SYSTEM_INSTRUCTION`, `build_rag_user_message()` |
| `ai/services/rag_service.py` | `RagService.answer()` — retrieve → budget → LLM → ground citations → `ChatResult` |

**Import law**: `rag_service.py` imports only `litellm`, `pydantic`, `config`, `ai.retrieval.*`, `ai.prompts.*`, stdlib — no FastAPI, SQLAlchemy, or `RequestContext`.

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

**Not in Slice 5**: `GET /ai/threads` list routes (Slice 5.3), LangGraph checkpointer (Slice 6).

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

- `src/docs/system.md` — API wiring, Compose, short AI summary
- `src/docs/lld.md` — §4.12 retrieval LLD
- `src/docs/rules.md` — dependency direction
