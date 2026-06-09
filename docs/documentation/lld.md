# DashNoteSystem Low-Level Design (LLD)

**Purpose:** Implementation patterns, call flows, module responsibilities, and abstractions — use ASCII flows below as source material for UML sequence/class diagrams.

**Related:** `src/docs/system.md` (routing, Compose) · `src/docs/ai.md` (AI contracts) · `src/docs/rules.md` (import laws) · `src/docs/observe.md` (validation) · [`docs/uml/`](../../docs/uml/README.md) (Mermaid diagrams)

---

## 1) Objective and scope

Implementation-level design for the backend in this repository, aligned with code that exists today.

**In scope:** Auth/JWT context · multi-tenant repositories · RBAC · storage backends · modules `auth`, `workspaces`, `membership`, `notes`, `notebooks`, `files` · AI slices 1–7 · observability (`observability/*`, Prometheus, Grafana)

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
    └─► litellm.acompletion(response_format=Schema) → persist tags/summary
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
    │       └─► litellm.acompletion(response_format=AutomationDecision)
    ├─► should_execute_immediately(decision)
    │       ├─► True  (confidence >= 0.95 AND is_destructive=False) → execute
    │       └─► False → log [AUTOMATION_GOVERNANCE_BLOCK] → pending review (future)
    └─► LLM failure → fail-safe block (is_destructive=True, confidence=0.0)
```

| Task | Governance |
|------|------------|
| `generate_note_tags`, `generate_file_metadata`, `index_file_chunks` | **Skipped** — additive/idempotent |
| Future destructive automation | **Required** — `evaluate_and_gate()` before side effects |

`worker/automation/decision.py`: `litellm`, `pydantic`, `config`, stdlib only — no FastAPI, SQLAlchemy, repositories.

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
| 503 | Health probe failure; AI disabled (`ai_enabled` / `qdrant_enabled`) |

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
| §3.1 / Compose | [Docker deployment](../../docs/uml/diagrams.md#10-docker-compose-deployment) |

Index: [`docs/uml/README.md`](../../docs/uml/README.md)
