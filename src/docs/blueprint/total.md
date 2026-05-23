# DashNoteSystem — AI Evolution Blueprint (v3, Final)
## Vertical Slice Architecture — Ship Value Early, Validate Before Building More

> **Core philosophy:** We build the AI product layer, not AI inference infrastructure.
> We own orchestration, memory, retrieval, workflows, automation, and tenancy.
> LLM inference and embeddings come from hosted providers (OpenAI).

---

## Key Decisions Locked In

| Decision | Reason |
|---|---|
| `ai/`, `worker/`, `shared/` live **inside** `src/` | Single PYTHONPATH, one Dockerfile, standard FastAPI pattern |
| **One Dockerfile, one `requirements.txt`** | Evolve what exists — never rewrite what works |
| **Install packages when the code needs them** | No bloat, no speculative installs |
| **Append to docker-compose, never rewrite** | Existing services stay untouched forever |
| **Append to settings.py per slice** | Only add fields the code actually reads |
| **Append to .env per slice** | Only add vars the feature actually needs |
| No `unstructured` package | pypdf + python-docx + beautifulsoup4 is enough |
| No local ML models ever | Hosted APIs only — OpenAI. 8GB RAM friendly. |
| Qdrant local in docker for dev | Point `QDRANT_URL` to Qdrant Cloud for prod — zero code change |
| **Vertical slices, not phase completion** | Validate product value before building more infrastructure |
| **No LangGraph until tool loops are real** | Simple orchestration handles RAG, streaming, memory fine |
| Neo4j deferred — optional | Only if relationship traversal becomes a proven user need |

---

## Repository Structure

Everything lives inside `src/`. No new root-level packages.
Folders are created slice by slice — only what the current slice needs.

```
src/
├── auth/                         ← existing, never touched
├── notes/                        ← existing, minimal additions per slice
├── files/                        ← existing, minimal additions per slice
├── workspaces/                   ← existing, never touched
├── membership/                   ← existing, never touched
│
├── core/                         ← existing, never touched
│   ├── database/
│   ├── redis/
│   ├── security/
│   └── health.py
│
├── shared/                       ← NEW in Slice 1
│   ├── events/                   # domain events — NoteCreatedEvent etc.
│   ├── contracts/                # inter-module contracts — IndexingRequest etc.
│   └── schemas/                  # shared models — WorkspaceContext, NoteChunk
│
├── ai/                           ← NEW — grows slice by slice
│   ├── embeddings/               # Slice 1: chunker, provider, pipeline, cache
│   ├── retrieval/                # Slice 2: Qdrant wrapper, RBAC filters, hybrid search
│   ├── services/                 # Slice 3+: chat_service, rag_service
│   ├── providers/                # Slice 3: LLM provider abstraction
│   ├── prompts/                  # Slice 3: all prompt templates
│   ├── memory/                   # Slice 5: context builder, thread manager
│   ├── workflows/                # Slice 6: LangGraph graphs (only here)
│   ├── tools/                    # Slice 6: agent tools
│   └── schemas/                  # grows as needed
│
├── worker/                       ← NEW — ARQ background jobs
│   ├── ingestion/                # Slice 1: embed_note_task
│   ├── indexing/                 # Slice 2: index_chunks_task, delete_vectors_task
│   ├── automation/               # Slice 7: event-driven tasks
│   ├── tasks.py                  # ARQ registry — grows per slice
│   └── main.py                   # ARQ WorkerSettings
│
└── main.py                       ← existing, one line added per slice for new routers
```

---

## Dependency Direction Law (Never Violate)

```
src/shared/  ←  imported by ai/, worker/, domain modules. Imports NOTHING.
src/ai/      ←  imports from src/shared/ only. Never src/notes/, src/worker/.
src/worker/  ←  imports from src/ai/ and src/shared/. Never FastAPI/HTTP logic.
src/notes/   ←  calls src/ai/services/ via service interface only.
src/files/   ←  same pattern as src/notes/.
```

**One sentence:** `shared ← ai ← worker` and `shared ← src modules → ai/services`

Tools → services → repositories. Never shortcut this chain.

---

## Infrastructure Rules (All Slices)

### Never Rewrite — Only Append

```
docker-compose.yml  →  append new services only
requirements.txt    →  append new packages only, grouped by slice comment
settings.py         →  append new fields only, grouped by slice comment
.env                →  append new vars only, grouped by slice comment
Dockerfile          →  evolve only if a new system package is truly needed
```

### Package Install Discipline

```
Install a package ONLY when writing the code that imports it.
Add it to requirements.txt immediately under # --- AI Slice N ---
Never install speculatively.
```

### Validation Gates

```
Every slice has a gate. Do NOT proceed to the next slice until the gate passes.
A gate is a concrete, observable thing you can check yourself.
Not a feeling. Not "it seems to work". A specific curl or log output.
```

---

## Slice Overview

```
Slice 0   Foundation          Folders + shared contracts. Nothing runs yet.
Slice 1   Embed               Notes chunked + embedded silently in background.
Slice 2   Retrieve            Vectors in Qdrant. Retrieval quality validated.
Slice 3   Chat MVP            POST /ai/chat works. No memory. No streaming. Ships.
Slice 4   Polish              Streaming + citations + better prompts.
Slice 5   Memory              Conversation threads. Continue where you left off.
Slice 6   Workflows           LangGraph enters. Tool calling. Agent actions.
Slice 7   Automation          File upload → auto-summarize. Event-driven intelligence.
Slice 8   GraphRAG (optional) Neo4j relationship intelligence. Only if needed.
Slice 9   Multi-agent (later) Supervisor + specialized agents. Late stage only.
Slice 10  Observability       LangSmith active. Cost tracking. Usage dashboard.
Slice 11  Scale               Caching, model routing, worker scaling.
```

---

## SLICE 0 — Foundation

**Goal:** Create folder structure and shared contracts. Zero logic. Zero packages. Zero docker changes.
**Gate:** `python -c "from src.shared.events import NoteCreatedEvent; print('ok')"` prints ok.
**Existing system:** Completely untouched. All existing tests still pass.

### What gets created

```
src/shared/__init__.py
src/shared/events/__init__.py
src/shared/events/definitions.py      → domain events (frozen Pydantic models)
src/shared/contracts/__init__.py
src/shared/contracts/indexing.py      → IndexingRequest, DeletionRequest, IndexingResult
src/shared/schemas/__init__.py
src/shared/schemas/workspace.py       → WorkspaceContext
src/shared/schemas/note.py            → NoteChunk, NoteReference
src/shared/schemas/retrieval.py       → HybridSearchQuery, RetrievalResult

src/ai/__init__.py                    + all subdirectory __init__.py stubs
src/worker/__init__.py                + all subdirectory __init__.py stubs
src/worker/tasks.py                   → empty ARQ registry (functions = [])
src/worker/main.py                    → ARQ WorkerSettings stub
```

### Domain events (src/shared/events/definitions.py)

All frozen. All import only stdlib + pydantic. Never import from ai/, worker/, domain modules.

```python
class EventType(str, Enum):
    NOTE_CREATED = "note.created"
    NOTE_UPDATED = "note.updated"
    NOTE_DELETED = "note.deleted"
    FILE_UPLOADED = "file.uploaded"
    FILE_DELETED = "file.deleted"

class BaseEvent(BaseModel):
    model_config = ConfigDict(frozen=True)
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: EventType
    workspace_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class NoteCreatedEvent(BaseEvent):
    event_type: EventType = EventType.NOTE_CREATED
    note_id: str
    created_by: str
    is_private: bool
    title: str
    content: str

# NoteUpdatedEvent, NoteDeletedEvent, FileUploadedEvent, FileDeletedEvent
# — same pattern
```

### Packages installed: **None**

### What does NOT change
```
Dockerfile          ← untouched
docker-compose.yml  ← untouched
requirements.txt    ← untouched
.env                ← untouched
settings.py         ← untouched
Every existing src/ module ← untouched
```

---

## SLICE 1 — Embed

**Goal:** Every note created or updated gets chunked and embedded silently in the background.
The API never blocks. The user never sees this. It just happens.

**Gate:**
```bash
# Create a note via API, then check worker logs:
docker compose logs worker | grep "embedding complete"
# Must show chunk count and latency. No errors.
```

**Retrieval quality is NOT validated here. That is Slice 2's job.**

### Packages installed
```bash
pip install openai                    # embedding API
pip install langchain-text-splitters  # RecursiveCharacterTextSplitter
pip install arq                       # background job queue
pip install tenacity                  # retry on rate limit
pip install tiktoken                  # token counting

# Add to requirements.txt under:
# --- AI Slice 1: Embedding pipeline ---
```

### Docker additions (append to existing docker-compose.yml)
```yaml
# Append under services: — do not touch any existing service
  worker:
    build: .
    command: python -m arq src.worker.main.WorkerSettings
    env_file: .env
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    # Scale: docker compose up --scale worker=3 -d

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage
    restart: unless-stopped
    # Production: remove this, set QDRANT_URL to Qdrant Cloud

# Append to volumes: section
  qdrant_data:
```

### Settings appended (src/config/settings.py)
```python
# --- AI Slice 1: Embedding ---
OPENAI_API_KEY: str | None = None
EMBEDDING_MODEL: str = "text-embedding-3-small"
EMBEDDING_DIMENSION: int = 1536
EMBEDDING_BATCH_SIZE: int = 32
EMBEDDING_MAX_RETRIES: int = 3
EMBEDDING_CACHE_ENABLED: bool = True
EMBEDDING_CACHE_TTL: int = 86400      # 24h

# --- AI Slice 1: Chunking ---
CHUNK_SIZE: int = 1000
CHUNK_OVERLAP: int = 150
CHUNK_MIN_LENGTH: int = 50

# --- AI Slice 1: ARQ Worker ---
ARQ_REDIS_URL: str = ""               # falls back to REDIS_URL if empty
WORKER_MAX_JOBS: int = 5              # tune per OpenAI tier TPM limit

# Computed properties:
@property
def ai_enabled(self) -> bool:
    return bool(self.OPENAI_API_KEY)

@property
def effective_arq_redis_url(self) -> str:
    return self.ARQ_REDIS_URL or self.REDIS_URL
```

### .env appended
```env
# --- AI Slice 1 ---
OPENAI_API_KEY=sk-your-key-here
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536
EMBEDDING_BATCH_SIZE=32
EMBEDDING_MAX_RETRIES=3
EMBEDDING_CACHE_ENABLED=true
EMBEDDING_CACHE_TTL=86400
CHUNK_SIZE=1000
CHUNK_OVERLAP=150
CHUNK_MIN_LENGTH=50
ARQ_REDIS_URL=redis://redis:6379
WORKER_MAX_JOBS=5
```

### What gets built
```
src/ai/embeddings/
  base.py             → BaseEmbeddingProvider (ABC), EmbeddedChunk, EmbeddingProviderError
  openai_provider.py  → AsyncOpenAI client, tenacity retry on RateLimitError only
  factory.py          → singleton provider, FastAPI Depends
  chunker.py          → RecursiveCharacterTextSplitter
                        chunk_id = uuid5(NAMESPACE_URL, f"{note_id}:{index}")
                        deterministic = safe to re-run (idempotent upserts later)
  cache.py            → Redis cache: sha256(chunk_text) → vector
                        hit = skip OpenAI call entirely (cost control)
  pipeline.py         → orchestrates: chunk → cache check → embed → EmbeddedChunk list

src/worker/
  main.py             → ARQ WorkerSettings with embed_note_task registered
  tasks.py            → imports and lists embed_note_task
  ingestion/
    tasks.py          → embed_note_task: receives IndexingRequest, runs pipeline
                        logs: note_id, chunks_processed, tokens_used, latency_ms
```

### Change to notes router (minimal, append only)
```python
# src/notes/router.py — add AFTER note is saved to DB, before return

if settings.ai_enabled:
    try:
        await arq_pool.enqueue_job(
            "embed_note_task",
            request=IndexingRequest(
                operation=IndexingOperation.UPSERT,
                note_id=str(note.id),
                workspace_id=str(ctx.workspace_id),
                created_by=str(ctx.user_id),
                is_private=note.is_private,
                title=note.title,
                content=body.content,
            ).model_dump(),
        )
    except Exception:
        # Never block the API response for background work
        logger.warning("Failed to enqueue embedding job", note_id=str(note.id))

# Same pattern for update and delete endpoints
```

### Design rules
- Retry only on: `RateLimitError`, `APITimeoutError`, `APIConnectionError`
- Never retry on: `AuthenticationError`, `BadRequestError`
- ARQ `max_jobs=5` — never hammer OpenAI, respect TPM limits
- Embedding cache key: `sha256(chunk_text)` — same text = same vector = free
- `chunk_id` is deterministic — re-running embed on same note = safe overwrite in Qdrant
- API enqueues and returns immediately — no `await` on embedding work

---

## SLICE 2 — Retrieve

**Goal:** Embedded chunks stored in Qdrant. A test endpoint lets you validate
retrieval quality before building any user-facing chat feature.

**This slice is a quality gate. Do not proceed to Slice 3 until retrieval is good.**

**Gate:**
```bash
# Call the internal test endpoint:
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/ai/test-search?q=your+note+content&limit=5"

# Check:
# 1. Results are relevant to the query
# 2. workspace_id in every result matches your workspace
# 3. Private notes from other users do NOT appear for member role
# 4. Scores are reasonable (> 0.5 for good matches)
# If retrieval is bad: tune CHUNK_SIZE, CHUNK_OVERLAP before proceeding
```

### Packages installed
```bash
pip install qdrant-client[async]   # Qdrant vector DB client

# Add to requirements.txt under:
# --- AI Slice 2: Vector retrieval ---
```

### Settings appended
```python
# --- AI Slice 2: Qdrant ---
QDRANT_URL: str = "http://qdrant:6333"
QDRANT_API_KEY: str | None = None
QDRANT_NOTES_COLLECTION: str = "notes_chunks"
QDRANT_TIMEOUT: int = 30
```

### .env appended
```env
# --- AI Slice 2 ---
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=
QDRANT_NOTES_COLLECTION=notes_chunks
QDRANT_TIMEOUT=30
```

### What gets built
```
src/ai/retrieval/
  client.py       → AsyncQdrantClient singleton
                    collection_init(): creates collection + payload indexes on startup
  filters.py      → build_rbac_filter(ctx) — mirrors src/notes/permissions.py exactly
  wrapper.py      → WorkspaceVectorSearch
                    ONLY interface to Qdrant — raw client never called directly
                    workspace_id always injected from RequestContext, never optional
  hybrid.py       → dense (OpenAI) + BM25 sparse (Qdrant native) combined via RRF
                    sparse is zero extra infrastructure — Qdrant computes it natively

src/worker/indexing/
  tasks.py        → index_chunks_task: upsert EmbeddedChunks to Qdrant
                    delete_note_vectors_task: delete by note_id + workspace_id filter

src/main.py       → add collection_init() call to lifespan startup
```

### Payload indexes (mandatory, created on startup)
```python
# Without these: every workspace_id filter = full collection scan
# With these: filter runs before ANN search — fast at any scale
for field in ["workspace_id", "note_id", "created_by", "visibility"]:
    await client.create_payload_index(
        collection_name=settings.QDRANT_NOTES_COLLECTION,
        field_name=field,
        field_schema="keyword",
    )
```

### Payload stored per chunk
```json
{
  "workspace_id": "uuid",
  "note_id": "uuid",
  "created_by": "uuid",
  "visibility": "public|private",
  "chunk_index": 0,
  "title": "note title",
  "char_start": 0,
  "char_end": 450
}
```

### RBAC filter — mirrors notes/permissions.py exactly
```python
def build_rbac_filter(ctx: RequestContext) -> Filter:
    # workspace_id is ALWAYS a must — never optional
    workspace_must = FieldCondition(
        key="workspace_id", match=MatchValue(value=str(ctx.workspace_id))
    )
    if ctx.role in ("owner", "admin"):
        return Filter(must=[workspace_must])  # see everything in workspace
    else:
        return Filter(                         # member: own OR public
            must=[workspace_must],
            should=[
                FieldCondition(key="visibility", match=MatchValue(value="public")),
                FieldCondition(key="created_by", match=MatchValue(value=str(ctx.user_id))),
            ],
            minimum_should_match=1,
        )
```

### Internal test endpoint (not for users — validation only)
```python
# src/ai_routes/search.py — internal route, remove or gate behind admin role later
@router.get("/ai/test-search")
async def test_search(
    q: str,
    limit: int = 5,
    ctx: RequestContext = Depends(get_current_context),
):
    results = await workspace_vector_search.search(
        query_text=q, ctx=ctx, limit=limit
    )
    return results   # raw results — good for tuning, not for users
```

### Vector deletion — always by filter, never ID scan
```python
await client.delete(
    collection=settings.QDRANT_NOTES_COLLECTION,
    points_selector=FilterSelector(filter=Filter(must=[
        FieldCondition(key="note_id", match=MatchValue(value=note_id)),
        FieldCondition(key="workspace_id", match=MatchValue(value=workspace_id)),
    ]))
)
# workspace_id in delete filter = tenant safety on deletion too
```

### Retrieval tuning guide (if gate fails)
```
Results irrelevant?          → decrease CHUNK_SIZE (try 600-800)
Results too fragmented?      → increase CHUNK_SIZE (try 1200-1500)
Missing exact terms?         → verify sparse vectors are being used (hybrid.py)
Wrong tenant results?        → check RBAC filter in filters.py
Scores all low (< 0.3)?      → check EMBEDDING_MODEL matches collection dimension
```

---

## SLICE 3 — Chat MVP

**Goal:** Ship the first user-facing AI feature. Simple, no frills.
`POST /ai/chat` answers questions about notes. No streaming. No memory. No LangGraph.
Just: embed query → search → prompt → answer.

**Ship this internally as soon as it works. Get feedback before building more.**

**Gate:**
```bash
curl -X POST http://localhost:8000/ai/chat \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"message": "what did I write about project X?"}'

# Must return:
# - answer grounded in actual note content
# - citations list with note_id and title
# - response in under 5 seconds
```

### Packages installed
```bash
pip install langchain-core   # prompt templates, message types
pip install langsmith        # tracing — wire now, enable in Slice 10

# Add to requirements.txt under:
# --- AI Slice 3: Chat MVP ---
```

### Settings appended
```python
# --- AI Slice 3: LLM ---
LLM_MODEL: str = "gpt-4.1-mini"
LLM_TEMPERATURE: float = 0.0
LLM_MAX_TOKENS: int = 2048
TOKEN_BUDGET_PER_REQUEST: int = 8000

# --- AI Slice 3: LangSmith (wired now, enabled in Slice 10) ---
LANGSMITH_API_KEY: str | None = None
LANGSMITH_PROJECT: str = "dashnote"
LANGSMITH_TRACING_ENABLED: bool = False
```

### .env appended
```env
# --- AI Slice 3 ---
LLM_MODEL=gpt-4.1-mini
LLM_TEMPERATURE=0.0
LLM_MAX_TOKENS=2048
TOKEN_BUDGET_PER_REQUEST=8000
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=dashnote
LANGSMITH_TRACING_ENABLED=false
```

### What gets built
```
src/ai/providers/
  base.py             → BaseLLMProvider (ABC): chat(), structured()
  openai_provider.py  → OpenAI chat completion, tenacity retry

src/ai/prompts/
  base.py             → template utilities
  rag.py              → RAG answer + citations prompt template
                        (no prompt strings anywhere else — ever)

src/ai/services/
  rag_service.py      → full pipeline:
                        embed query → hybrid search → token budget check
                        → assemble prompt → call LLM → return answer + citations

src/ai_routes/
  chat.py             → POST /ai/chat (simple, no streaming yet)

src/main.py           → app.include_router(ai_chat_router, prefix="/ai")
```

### Chat endpoint — simple version (no streaming yet)
```python
# src/ai_routes/chat.py
@router.post("/ai/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    ctx: RequestContext = Depends(get_current_context),
    rag: RagService = Depends(get_rag_service),
):
    return await rag.answer(
        question=body.message,
        ctx=ctx,
    )
```

### RAG pipeline (no LangGraph — plain async functions)
```python
# src/ai/services/rag_service.py
async def answer(self, question: str, ctx: RequestContext) -> ChatResponse:
    # 1. embed the question
    query_vector = await self._embedder.embed_single(question)

    # 2. hybrid search with RBAC
    chunks = await self._retrieval.search(
        query_vector=query_vector,
        ctx=ctx,
        limit=8,
    )

    # 3. token budget check — stay under TOKEN_BUDGET_PER_REQUEST
    chunks = self._fit_to_budget(chunks)

    # 4. build prompt from template (src/ai/prompts/rag.py only)
    prompt = rag_prompt.format(
        question=question,
        context=self._format_chunks(chunks),
    )

    # 5. call LLM via provider
    response = await self._llm.structured(prompt, response_model=RAGAnswer)

    # 6. return answer + citations
    return ChatResponse(
        answer=response.answer,
        citations=[Citation(note_id=c.note_id, title=c.title,
                            chunk_id=c.chunk_id, relevance_score=c.score)
                   for c in chunks],
    )
```

### Citation schema
```python
class Citation(BaseModel):
    note_id: str
    chunk_id: str
    title: str
    relevance_score: float

class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    thread_id: str | None = None   # populated in Slice 5
```

### Structured outputs — always, no exceptions
```python
# Never: raw_text = await llm.generate(prompt)  then parse with regex
# Always:
result = await llm.structured(prompt, response_model=RAGAnswer)
# Reliable. Testable. No fragile string parsing.
```

---

## SLICE 4 — Polish

**Goal:** Make the chat experience production-quality.
Streaming responses. Better citations. Prompt tuning.
**Ship this to real users.**

**Gate:**
```bash
# Test SSE streaming:
curl -X POST http://localhost:8000/ai/chat \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"message": "summarize my notes"}' \
  --no-buffer

# Must stream tokens progressively, not wait for full response
# Citations must appear after stream completes
```

### Packages installed: **None** (all already present)

### What gets built
```
src/ai_routes/chat.py    → replace sync response with StreamingResponse + SSE

src/ai/prompts/
  rag.py                 → refined prompt with better citation instructions
  summarize.py           → workspace/note summarization prompt

src/ai/services/
  rag_service.py         → add stream_answer() method alongside answer()
```

### SSE streaming — security pattern (never deviate)
```python
@router.post("/ai/chat/stream")
async def chat_stream(
    body: ChatRequest,
    ctx: RequestContext = Depends(get_current_context),
):
    # Step 1: validate and freeze BEFORE opening the generator
    # RequestContext is validated here by the Depends above
    workspace_id = str(ctx.workspace_id)   # frozen primitive
    user_id = str(ctx.user_id)             # frozen primitive
    role = ctx.role                         # frozen primitive

    async def generate():
        # Step 2: only frozen primitives inside — NEVER reference ctx here
        # ctx could be garbage collected; frozen strings are safe
        async for chunk in rag_service.stream_answer(
            workspace_id=workspace_id,    # explicit pass
            user_id=user_id,              # explicit pass
            role=role,                    # explicit pass
            question=body.message,
        ):
            yield f"data: {json.dumps({'content': chunk})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
```

---

## SLICE 5 — Memory

**Goal:** Conversations persist. Users can continue previous chats.
Threads listed in UI. Context from previous messages injected into answers.

**Gate:**
```bash
# 1. Start a conversation
POST /ai/chat {"message": "what is my project about?", "thread_id": null}
# → returns thread_id in response

# 2. Continue it
POST /ai/chat {"message": "what did I say about the deadline?", "thread_id": "<id>"}
# → must reference context from message 1 without re-explaining
```

### Packages installed
```bash
pip install langgraph   # AsyncPostgresSaver for graph checkpointing
                        # NOTE: plain conversation memory does NOT need LangGraph
                        # Install now so it is ready for Slice 6
                        # But conversation persistence is plain SQL + context injection

# Add to requirements.txt under:
# --- AI Slice 5: Memory ---
```

### New DB tables (Alembic migration)
```sql
-- Product layer: what the user sees
CREATE TABLE ai_threads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    created_by UUID NOT NULL,
    title TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE ai_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID NOT NULL REFERENCES ai_threads(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'tool')),
    content TEXT NOT NULL,
    citations JSONB DEFAULT '[]',
    token_count INTEGER,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_ai_messages_thread ON ai_messages(thread_id, created_at DESC);
CREATE INDEX idx_ai_threads_workspace ON ai_threads(workspace_id, updated_at DESC);
```

### Settings appended
```python
# --- AI Slice 5: Memory ---
AI_THREAD_MESSAGE_LIMIT: int = 20   # recent messages loaded into context
```

### What gets built
```
src/ai/memory/
  context_builder.py  → assembles: recent messages + retrieved chunks
                        respects TOKEN_BUDGET_PER_REQUEST
  thread_manager.py   → create_thread(), list_threads(), get_thread()
                        RBAC: threads scoped to workspace + created_by

src/ai_routes/
  threads.py          → GET /ai/threads
                        GET /ai/threads/{id}/messages
                        DELETE /ai/threads/{id}

src/ai/services/
  rag_service.py      → extend answer() and stream_answer() to accept thread_id
                        load recent messages → inject into prompt context
                        save user message + assistant response to ai_messages
```

### Two concerns, linked only by thread_id
```
ai_threads / ai_messages    → product layer (UI, RBAC, listing) — plain SQL
AsyncPostgresSaver          → LangGraph execution state (Slice 6 only)
Linked by: thread_id string → the only bridge between them
```

---

## SLICE 6 — Workflows (LangGraph Enters Here)

**Goal:** Agent takes actions. Tool calling with conditional loops.
Note creation, updates, workspace summarization via agent.

**LangGraph is introduced ONLY in this slice.**
Everything before this works without it.
It enters now because tool loops need state management.

**Gate:**
```bash
# Agent must complete a multi-step task:
POST /ai/chat {"message": "summarize my workspace and create a note with the summary"}

# Must:
# 1. call summarize_workspace tool
# 2. decide to call create_note tool with the summary
# 3. return confirmation with note_id
# 4. NOT hallucinate — note must actually exist in DB after
```

### Packages installed: **None** (langgraph installed in Slice 5)

### Settings appended
```python
# --- AI Slice 6: Workflows ---
AGENT_MAX_ITERATIONS: int = 10    # prevent infinite tool loops
AGENT_TOOL_TIMEOUT: int = 30      # seconds per tool call
```

### What gets built
```
src/ai/workflows/
  state.py                  → AgentState TypedDict
  workspace_assistant.py    → LangGraph graph:
                              retrieve → reason → tool_or_respond (conditional)
                              → tool → reason (loop back)
                              → respond → END

src/ai/tools/
  search_notes.py           → calls rag_service.search()
  create_note.py            → calls note service (never repository directly)
  update_note.py            → calls note service
  summarize_workspace.py    → calls summary service

src/ai/memory/
  checkpointer.py           → AsyncPostgresSaver setup, linked by thread_id
```

### Graph structure
```python
graph.add_edge(START, "retrieve")
graph.add_edge("retrieve", "reason")
graph.add_conditional_edges(
    "reason",
    lambda state: "tool" if state["tool_calls"] else "respond"
)
graph.add_edge("tool", "reason")   # reason again after each tool call
graph.add_edge("respond", END)
```

### Tool chain law (never shortcut)
```python
# tool → service → repository
# NEVER: tool → repository directly

@tool
async def create_note_tool(title: str, content: str, ctx: RequestContext):
    # calls the service which enforces RBAC
    return await note_service.create(title=title, content=content, ctx=ctx)
    # NOT: await note_repository.create(...)
```

### LangGraph checkpointing — wired to AsyncPostgresSaver
```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

checkpointer = AsyncPostgresSaver.from_conn_string(settings.DATABASE_URL)
await checkpointer.setup()   # creates langgraph internal tables

graph = workflow.compile(checkpointer=checkpointer)
result = await graph.ainvoke(
    state,
    config={"configurable": {"thread_id": str(thread.id)}}
)
# thread_id links product tables (ai_threads) to graph execution state
```

---

## SLICE 7 — Automation

**Goal:** Events trigger intelligent background actions automatically.
File uploads auto-summarized. Notes auto-tagged. No user input needed.

**Gate:**
```bash
# Upload a PDF file
POST /files/upload  (multipart)

# Within 30 seconds, check:
GET /files/{id}
# Must have: summary field populated, tags populated
# Check worker logs: "automation complete" for file_id
```

### Packages installed (when writing file extraction)
```bash
pip install pypdf            # PDF text extraction
pip install python-docx      # Word document extraction
pip install beautifulsoup4   # HTML content extraction

# Add to requirements.txt under:
# --- AI Slice 7: File parsing ---
```

### What gets built
```
src/shared/events/bus.py    → emit_event(event, arq_pool) — ARQ enqueue by event type

src/worker/automation/
  tasks.py                  → handle_file_uploaded, handle_note_created

src/files/router.py         → EXTEND: emit FileUploadedEvent after save (append only)
src/notes/router.py         → EXTEND: emit NoteCreatedEvent after save (already has embed)
```

### Event bus — uses existing ARQ (no new infrastructure)
```python
async def emit_event(event: BaseEvent, arq_pool: ArqRedis) -> None:
    task_map = {
        "file.uploaded":  "handle_file_uploaded",
        "note.created":   "handle_note_created",
    }
    task_name = task_map.get(event.event_type.value)
    if task_name:
        await arq_pool.enqueue_job(task_name, event=event.model_dump())
```

### File automation pipeline
```
FileUploadedEvent
  → worker: extract text (pypdf / python-docx / beautifulsoup4)
  → worker: chunk text using existing chunker
  → worker: embed chunks → Qdrant (existing indexing pipeline)
  → worker: structured LLM call → generate summary + tags
  → worker: store summary + tags to DB
  → done — user sees enriched file metadata on next fetch
```

### Human approval gate for destructive actions
```python
class AutomationDecision(BaseModel):
    action: str
    requires_approval: bool
    confidence: float
    reasoning: str

# confidence > 0.95 AND not destructive → execute immediately
# anything else → store as pending action, surface to user for approval
```

---

## SLICE 8 — GraphRAG with Neo4j (Optional)

**Start this ONLY when ALL are true:**
- Retrieval is working well in production (real users, real queries)
- Users are specifically asking for "related notes" or "connected knowledge"
- A product decision has been made that graph relationships add value

**If none of those are true: skip this slice indefinitely.**

### Packages installed (only when starting)
```bash
pip install neo4j
# Add to requirements.txt under:
# --- AI Slice 8: GraphRAG ---
```

### Docker addition (only when starting)
```yaml
  neo4j:
    image: neo4j:5-community
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      NEO4J_AUTH: neo4j/your_password
    volumes:
      - neo4j_data:/data
    restart: unless-stopped
```

### Settings appended (only when starting)
```python
# --- AI Slice 8: Neo4j ---
NEO4J_URI: str = ""
NEO4J_USER: str = "neo4j"
NEO4J_PASSWORD: str = ""
```

### Combined retrieval (GraphRAG)
```
user question
  → Qdrant hybrid search  → semantic chunks (existing)
  → Neo4j traversal       → related notes + entities (new)
  → merge + deduplicate   → richer context than vector alone
  → LLM answer with relationship awareness
```

---

## SLICE 9 — Multi-Agent (Late Stage)

**Start this ONLY when:**
- Slice 6 workflows are stable in production
- Users need capabilities that single-agent cannot handle
- A concrete product requirement exists for multiple specialized agents

### What gets built
```
src/ai/workflows/
  supervisor.py         → LangGraph supervisor routes between agents
  research_graph.py     → deep retrieval + cross-note synthesis
  automation_graph.py   → multi-step workflow execution

src/ai/
  orchestration/
    router.py           → intent classification → agent routing
```

### Routing — cheap model classifies, expensive model reasons
```python
async def route(state) -> Literal["workspace", "research", "automation"]:
    classification = await ai_gateway.structured(
        prompt=classify_intent_prompt(state["question"]),
        response_model=IntentClassification,
        model="gpt-4o-mini",     # cheap — routing only
    )
    return classification.agent  # expensive model used inside each agent
```

---

## SLICE 10 — Observability

**Goal:** Full visibility into costs, quality, and failures.
**User-visible:** Usage dashboard per workspace.

### Activation (already wired from Slice 3)
```env
# Flip in .env:
LANGSMITH_TRACING_ENABLED=true
```

### New DB table (Alembic migration)
```sql
CREATE TABLE ai_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    operation TEXT NOT NULL,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    model TEXT,
    cost_usd NUMERIC(10, 6),
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_ai_usage_workspace ON ai_usage(workspace_id, created_at DESC);
```

### Structured logging on every AI operation
```python
logger.info("ai_operation", extra={
    "request_id": request_id,
    "workspace_id": workspace_id,
    "thread_id": thread_id,
    "operation": "rag_chat",
    "prompt_tokens": usage.prompt_tokens,
    "completion_tokens": usage.completion_tokens,
    "retrieved_chunks": len(chunks),
    "latency_ms": latency,
})
```

---

## SLICE 11 — Scale

**Goal:** Cost controls, caching, horizontal scaling.

### Response cache (Redis — already running)
```python
cache_key = f"rag:{workspace_id}:{hash(question)}:{gen_counter}"
# gen_counter = existing workspace note generation counter
# Invalidate on any note write — same pattern as existing cache-aside
```

### Model routing by cost
```
intent classification:   gpt-4o-mini   (fast, cheap — routing only)
RAG chat responses:      gpt-4.1-mini  (balanced — most requests)
complex reasoning:       gpt-4.1       (expensive — use sparingly)
```

### Worker scaling
```bash
docker compose up --scale worker=3 -d
# Each worker: WORKER_MAX_JOBS=5
# 3 workers = 15 concurrent jobs max
# Tune based on OpenAI tier TPM limit
```

---

## Critical Rules (Never Violate)

| Rule | Why |
|---|---|
| `workspace_id` always from `RequestContext`, never user input | Tenant security |
| `workspace_id` always a `must` filter in every Qdrant query | Cross-tenant data leakage |
| Always `upsert`, never `insert` to Qdrant | Idempotency on ARQ retry |
| Freeze `ctx` to primitives before SSE generator | Streaming tenant security |
| Tools → services → repositories. Never shortcut. | RBAC enforcement |
| No prompt strings outside `src/ai/prompts/` | Maintainability |
| Structured outputs everywhere — no LLM response regex parsing | Reliability |
| `sha256(chunk_text)` as embedding cache key | Cost control |
| `ARQ max_jobs` aligned to OpenAI tier TPM | Rate limit protection |
| Install packages when writing the code that needs them | No bloat |
| Append to all infra files — never rewrite | Stability |
| `src/shared/` imports nothing from domain modules | Circular import prevention |
| LangGraph enters in Slice 6 only — not before | Complexity control |
| Every slice has a gate — do not proceed until it passes | Quality control |

---

## What Each Slice Ships

| Slice | User-Visible | Internal Milestone |
|---|---|---|
| 0 | Nothing | Folder structure, shared contracts |
| 1 | Nothing | Notes silently embedded in background |
| **2** | **Nothing** | **Retrieval quality validated — gate passed** |
| **3** | **✅ POST /ai/chat — AI answers questions about notes** | First LLM call |
| **3** | **✅ Citations in every answer** | RAG pipeline live |
| **4** | **✅ Streaming responses** | SSE working |
| **4** | **✅ Better answer quality** | Prompt tuning |
| **5** | **✅ Conversation history** | Threads + messages |
| **5** | **✅ Continue previous chats** | Context injection |
| **6** | **✅ Agent creates/updates notes** | LangGraph + tools |
| **6** | **✅ Workspace summarization** | Agent workflows |
| **7** | **✅ Auto-summarize file uploads** | Event automation |
| **7** | **✅ Auto-tagging on note creation** | Background intelligence |
| 8 | Related notes discovery | GraphRAG (optional) |
| 9 | Multi-step research | Multi-agent (late) |
| 10 | Usage dashboard | Cost tracking |
| 11 | Faster responses | Caching + scaling |

---

## What Never Changes

```
Dockerfile              → one file, only add apt-get packages if truly needed
requirements.txt        → one file, append-only, grouped by slice comment
docker-compose.yml      → append-only, existing services never modified
settings.py             → append-only, grouped by slice comment
.env                    → append-only, grouped by slice comment
nginx/                  → untouched
src/auth/               → untouched
src/workspaces/         → untouched
src/membership/         → untouched
src/core/               → untouched
src/notes/              → minimal additions only (enqueue job, emit event)
src/files/              → minimal additions only (emit event in Slice 7)
```

The existing backend runs correctly throughout every slice.
AI is purely additive. Each slice can be rolled back independently.
Nothing breaks when adding the next slice.