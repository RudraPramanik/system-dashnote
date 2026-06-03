# DashNoteSystem Low-Level Design (LLD)

## 1) Objective and scope
This document defines the implementation-level design for the current backend in `g:\projects\dashnotesystem`, aligned with code that exists today.

In scope:
- Auth + JWT context propagation
- Multi-tenant data access model
- RBAC + domain permissions
- Object storage abstraction (local / S3-compatible backends) and the `files` module
- Implemented modules: `auth`, `workspaces`, `membership`, `notes`, `notebooks`, `files`
- AI indexing foundation: `src/shared/contracts/indexing.py`, `src/ai/embeddings/*` (chunker, LiteLLM provider, factory) — see §4.10
- Edge reverse proxy and dual-layer rate limiting (Nginx + Redis-backed FastAPI limits) as implemented in-repo
- AI retrieval (Slice 2): `ai/retrieval/*`, `ai_gateway/search.py`, Qdrant RBAC search
- AI chat RAG (Slice 3): `ai/prompts/rag.py`, `ai/services/rag_service.py`, `ai_routes/chat.py`
- AI chat streaming (Slice 4): `RagService.stream_answer()`, `POST /ai/chat/stream` SSE (`ai_routes/chat.py`)
- AI conversation memory (Slice 5): `ai_memory/*` ORM, `ai/memory/*` services, `ContextBuilder`, thread-aware RAG
- AI LangGraph agent (Slice 6): `ai/workflows/*`, `ai/tools/*`, `ai_routes/agent.py`, checkpointer lifecycle
- Observability: `src/observability/*` (JSON logging, Langfuse RAG traces), Prometheus `/metrics`, Compose `prometheus` + `grafana` + `monitoring/*` provisioning

Out of scope:
- Frontend design
- Cloud-specific provisioning beyond the provided `docker-compose.yml`, `nginx/default.conf`, and `monitoring/` stack
- Loki, Tempo, Jaeger, OpenTelemetry Collector
- Non-implemented runtime components

## 2) Design principles used

### 2.1 API layer stays thin
Routers only orchestrate:
- input schema validation
- dependency injection (DB, auth context)
- calling service/repository/permission helpers
- mapping models to response schemas

Business logic is kept in services/permission helpers/repositories.

### 2.2 Security and tenant context are explicit
Every protected request derives a single `RequestContext` from JWT:
- `user_id` (`sub`)
- `workspace_id` (`wid`)
- `role`

No protected module should decode JWT by itself.

### 2.3 Tenant safety by construction
Tenant-aware repositories inherit from `TenantRepository(session, workspace_id)` and enforce workspace scoping via `tenant_filter(...)`.

### 2.4 RBAC is layered
- Coarse route-level role checks: `require_roles(...)`
- Fine-grained entity checks: domain permission helpers (example: `notes/permissions.py`)

### 2.5 Backward-compatible tenancy naming
`tenant_filter` supports both `workspace_id` and `tenant_id`, allowing gradual model migration while preserving query safety.

### 2.6 Binary assets use storage backends, not SQL blobs
File bytes live in a `StorageBackend` implementation (`core/storage/client.py`: local disk, MinIO, or R2). SQL stores metadata, `storage_key`, and tenant/RBAC columns so repositories can enforce `workspace_id` the same way as notes.

## 3) Runtime architecture

### 3.1 Entry point and composition
`src/main.py` creates the FastAPI app and registers:
- **Lifespan**: `setup_logging()` (JSON stdout), ARQ pool, Qdrant collection bootstrap, LangGraph checkpointer init/shutdown (checkpointer failure is non-fatal).
- `ProxyHeadersMiddleware` (Uvicorn) so `request.client` reflects the proxied client when `X-Forwarded-For` is trusted.
- CORS middleware
- **Global application rate limit** dependency (`enforce_global_rate_limit`): Redis fixed-window counter per `user_id` (from JWT when present) or client IP; skipped when Redis is unavailable.
- module routers
- global exception handler
- **Prometheus**: `Instrumentator` at end of `create_app()` → `GET /metrics` (`dashnote_api_*` metrics; scraped by Compose `prometheus`, not Nginx).

Registered routers:
- `core.health` → `GET /health` (deep probe: `SELECT 1`, Redis `PING` when Redis is configured; **503** if a required dependency fails)
- `/auth`
- `/files`
- `/notebooks`
- `/notes`
- `/workspaces`
- `/workspaces/members`
- `/ai` → `GET /ai/test-search` (internal semantic search validation; `ai_gateway/search.py`)
- `/ai` → `POST /ai/chat`, `POST /ai/chat/stream` (`ai_routes/chat.py`)
- `/ai` → `GET /ai/threads`, `GET /ai/threads/{thread_id}/messages`, `DELETE /ai/threads/{thread_id}` (`ai_routes/threads.py`)
- `/ai` → `POST /ai/agent`, `POST /ai/agent/stream` (`ai_routes/agent.py`)

### 3.2 Request flow (protected endpoint)
1. When behind Nginx, the edge sets `X-Forwarded-For` / `X-Real-IP`; `ProxyHeadersMiddleware` adjusts ASGI `client` so downstream code (including rate limiting) sees the original host.
2. Global rate limit dependency runs (Redis `INCR` on a fixed-window key before route handlers).
3. Client sends `Authorization: Bearer <token>`.
4. `oauth2_scheme` extracts the token.
5. `get_current_context` validates JWT and builds `RequestContext` (including optional Redis access-token blacklist check via `get_token_store()`).
6. Optional: routers that support read caching also resolve `WorkspaceRedisCache` via `get_workspace_cache` (nested `Depends(get_current_context)` + shared Redis client from `get_async_redis()`).
7. Router instantiates repository with `ctx.workspace_id` where tenant-scoped.
8. Permission checks run (`require_roles` and/or domain helper).
9. Repository executes async SQLAlchemy query (on cache miss for cached routes).
10. Router returns Pydantic schema.

## 4) Module-level low-level design

### 4.1 `auth` module
Responsibilities:
- user registration
- credential validation
- token issuance, refresh rotation, and logout (access blacklist + optional refresh revocation)

Primary flow:
- `POST /auth/register`
  - creates `users`, `workspaces`, `workspace_users`
  - issues access + refresh JWTs with `sub`, `wid`, `role`, `jti`, `typ`
  - when Redis is enabled, stores the refresh token `jti` in Redis for rotation checks
- `POST /auth/login`
  - validates credentials
  - selects first membership as default workspace
  - issues access + refresh JWTs (same Redis refresh tracking when enabled)
  - additionally guarded by **`enforce_auth_login_rate_limit`** (5/min per identity in Redis when configured)
- `POST /auth/refresh`
  - validates refresh JWT; requires active refresh `jti` in Redis when enabled; rotates refresh token
- `POST /auth/logout`
  - blacklists access token `jti` until expiry when Redis is enabled; optionally revokes refresh `jti`

Operational state is delegated to `core/redis/redis.py` (`get_token_store`) using the shared async client from `core/redis/client.py` when `REDIS_URL` is configured (details in `src/docs/auth.md`).

### 4.2 `core.redis` — shared client + tenant cache-aside
Components:
- `core/redis/client.py`: lazy singleton `get_async_redis()`; `reset_async_redis_client()` clears the client and resets the token-store singleton (tests).
- `core/redis/redis.py`: `RedisTokenStore` / `BaseTokenStore` for JWT blacklist + refresh tracking.
- `core/redis/cache.py`: `WorkspaceRedisCache` — tenant-scoped key layout (`workspace_id` prefix), generation counters per domain (`notes`, `notebooks`), JSON cache-aside helpers.
- `core/redis/deps.py`: `get_redis_connection`, `get_workspace_cache` — FastAPI dependencies composing `RequestContext` with Redis (no-op cache when Redis is disabled).

Consumers (read caching):
- `notes/router.py`: `GET /notes` (list), `GET /notes/{id}` (detail after permission); all note mutations `INCR` the workspace notes generation.
- `notebooks/router.py`: `GET /notebooks/`; `POST /notebooks/` bumps workspace notebooks generation.

### 4.3 `core.security` module
Responsibilities:
- auth context extraction from token
- generic role gating
- optional access-token decode for non-auth-gated flows (rate limit identity)

Components:
- `_context_from_access_token` / `get_current_context`: JWT decode -> `RequestContext`
- `get_optional_current_context`: same validation when a bearer token is supplied; otherwise `None` (used by rate limiting without forcing login on public routes)
- `require_roles(*roles)`: dependency factory for 403 enforcement

Failure behavior:
- invalid/missing claims/token -> `401 Invalid or expired token` (strict `get_current_context` path only)
- insufficient role -> `403 Insufficient permissions`

### 4.3a `core.security.rate_limit` — application fixed-window limits
Responsibilities:
- enforce Redis-backed fixed-window quotas per logical **scope** and **identity**
- emit **429** with **`Retry-After`** when a window is exceeded

Components:
- `RateLimiter(scope, limit, window_seconds)`: builds keys `rate_limit:{scope}:{user_id|ip}:{window_index}`, uses `INCR` + `EXPIRE`
- `enforce_global_rate_limit`: FastAPI dependency (wired on the app in `main.py`) — default **100/min** (`scope=global`)
- `enforce_auth_login_rate_limit`: route-level dependency on `POST /auth/login` — **5/min** (`scope=auth_login`)

Identity rules:
- If `get_optional_current_context` returns a `RequestContext`, the identity segment is `str(user_id)` (same JWT semantics as `get_current_context`).
- Otherwise the identity segment is the client IP string from `Request.client` (after `ProxyHeadersMiddleware`).

Operational notes:
- When `get_redis_connection` yields `None`, checks are skipped (no Redis URL / disabled Redis) so unit tests and minimal dev setups keep working.

### 4.4 `workspaces` module
Responsibilities:
- retrieve current workspace
- rename workspace

Endpoints:
- `GET /workspaces/me`: authenticated user
- `PATCH /workspaces/me`: owner/admin only

Design note:
- workspace identity is always taken from JWT `wid` through context.

### 4.5 `membership` module
Responsibilities:
- list members
- invite member
- update member role
- remove member

Key rules in service layer:
- valid roles: `owner`, `admin`, `member`
- cannot invite `owner`
- admin cannot invite admin
- only owner can change roles
- admin cannot remove owner/admin
- user cannot remove self

Storage model:
- joins `workspace_users` with `users` for member listing.

### 4.6 `notes` module
Responsibilities:
- CRUD notes within workspace
- visibility and ownership checks

Data model highlights:
- tenant key (`workspace_id` via mixin)
- `created_by`
- `is_private`

Permission rules:
- owner/admin: full access
- member:
  - manage only own notes
  - view public notes + own private notes

Repository guarantees:
- all note queries include tenant scope
- member listing query applies visibility filter in SQL

Read performance:
- `GET /notes` and `GET /notes/{id}` use Redis cache-aside when configured (`WorkspaceRedisCache` from `core/redis/deps.py`); keys include `workspace_id`, viewer variant, and a workspace generation counter bumped on any note mutation.

### 4.7 `notebooks` module
Responsibilities:
- list notebooks in workspace
- create notebook (owner/admin only)

Tenant handling:
- repository extends `TenantRepository`
- all operations scoped by workspace

Read performance:
- `GET /notebooks/` uses the same tenant-scoped cache-aside pattern; notebook create bumps the workspace notebooks generation.

### 4.8 `files` module
Responsibilities:
- upload and persist file metadata in the active workspace
- list, read metadata, stream download, update, delete
- attach files to notes via the shared association table only

Storage layer:
- `get_storage()` returns a `StorageBackend` selected by `STORAGE_BACKEND` (`local`, `minio`, `r2`).
- Upload path validates MIME and policy in `core/storage/utils.py` before writing bytes through the backend.

Tenancy and data:
- `File` model uses `WorkspaceTenantMixin`; `storage_key` is unique and maps to the object key in the backend.

RBAC:
- `files/permissions.py` mirrors the notes visibility pattern: owner/admin see all workspace files; members see public files plus files they created.

Integration boundary:
- Note-to-file links use `note_attachments` in `core/database/associations.py` so `notes/` and `files/` stay loosely coupled.

### 4.9 `ai_gateway` module (current state)
Current code status:
- `src/ai_gateway/router.py` and `src/ai_gateway/schemas.py` are placeholders (empty).

LLD contract for implementation:
- must follow same router -> dependency -> service/repository layering
- must consume `RequestContext` for workspace-safe behavior
- avoid bypassing tenant and permission patterns used by other modules

### 4.10 AI indexing — shared contracts and embeddings (Slice 1.2)

This slice prepares note vector indexing without HTTP routes, Qdrant I/O, or ARQ job handlers. Full narrative: `src/docs/ai.md`. Import laws: `src/docs/rules.md`.

#### 4.10.1 Shared contracts — `src/shared/contracts/indexing.py`

| Type | Producer | Consumer (planned) |
|------|----------|-------------------|
| `IndexingRequest` | API after note upsert | ARQ worker |
| `DeletionRequest` | API after note delete | ARQ worker |
| `IndexingResult` | Worker | Logging / metrics |

Frozen Pydantic models; imports stdlib + pydantic only.

#### 4.10.2 Text chunking — `src/ai/embeddings/chunker.py`

```
IndexingRequest (content, title, note_id)
        │
        ▼
   TextChunker.chunk_note()
        │
        ▼
 list[ChunkResult]   # deterministic chunk_id = uuid5(NAMESPACE_URL, "{note_id}:{index}")
```

- `RecursiveCharacterTextSplitter` driven by `CHUNK_SIZE`, `CHUNK_OVERLAP`, `CHUNK_MIN_LENGTH`.
- Title prefixed as markdown H1 for retrieval context.
- Chunks below `CHUNK_MIN_LENGTH` dropped.

#### 4.10.3 Embedding provider abstraction — `src/ai/embeddings/base.py`

```
                    BaseEmbeddingProvider (ABC)
                              │
                    embed_texts(texts) -> list[EmbeddingVector]
                    get_model_name() / get_dimension()
                              │
                              ▼
                 LiteLLMEmbeddingProvider (only impl today)
```

| Type | Purpose |
|------|---------|
| `EmbeddingVector` | `list[float]` |
| `EmbeddingProviderError` | Unified failure; `retryable` flag for callers |
| `EmbeddedChunk` | Pipeline output: chunk metadata + vector (Qdrant payload in Slice 2) |

#### 4.10.4 LiteLLM provider — `src/ai/embeddings/litellm_provider.py`

Sequence for one batch:

```
embed_texts
  → filter empty/whitespace
  → for each batch (size EMBEDDING_BATCH_SIZE):
        _embed_batch_with_retry
          → _call_litellm (+ tenacity on transient litellm errors)
          → on fatal auth/4xx: EmbeddingProviderError(retryable=False)
```

Configuration (from `config.Settings`):

| Setting | Used for |
|---------|----------|
| `EMBEDDING_MODEL` | `litellm.aembedding(model=...)` |
| `EMBEDDING_DIMENSION` | Validation / Qdrant collection size (later) |
| `EMBEDDING_BATCH_SIZE` | Batch loop |
| `EMBEDDING_MAX_RETRIES` | Tenacity `stop_after_attempt` |
| `OPENAI_API_KEY` / `GEMINI_API_KEY` | `settings.ai_enabled` kill-switch (not read inside provider) |

Provider swap: change `EMBEDDING_MODEL` env only (e.g. `openai/text-embedding-3-small`, `voyage/voyage-3`).

#### 4.10.5 Factory — `src/ai/embeddings/factory.py`

```
Process start
    │
    ▼
get_embedding_provider()  ──first call──► LiteLLMEmbeddingProvider()
    │                                      (stored in module singleton)
    └── subsequent calls ──► same instance (asyncio.Lock + double-check)
```

- **Single instantiation point** for embedding backends.
- `reset_embedding_provider()` for tests.
- FastAPI `Depends(...)` wiring deferred to route modules (AI layer must not import FastAPI).

#### 4.10.6 Embedding cache — `src/ai/services/cache.py`

| Function | Behavior |
|----------|----------|
| `get_cached_vector(text, redis)` | `GET embed:v1:{sha256}` → `list[float]` or `None` |
| `cache_vector(text, vector, redis)` | `SETEX` with `EMBEDDING_CACHE_TTL` |

Non-fatal on Redis errors. Disabled when `EMBEDDING_CACHE_ENABLED=false`.

#### 4.10.7 Pipeline — `src/ai/workflows/pipeline.py`

```
process_note (keyword-only RBAC + content args)
    │
    ├─► TextChunker.chunk_note()
    │
    ├─► per chunk: get_cached_vector? ──hit──► vectors_by_index
    │                    └──miss──► uncached_indices
    │
    ├─► provider.embed_texts(uncached_texts)
    │
    ├─► cache_vector for each new vector
    │
    └─► EmbeddedChunk[] + PipelineResult metrics
```

`EmbeddingPipeline(provider, redis=None)` — `redis=None` skips cache entirely.

Worker flow (1.3): dequeue `IndexingRequest` → `embed_note_task` → `EmbeddingPipeline.process_note` → log vectors → `IndexingResult`. Qdrant upsert in Slice 2.

#### 4.10.8 Dependency matrix (AI embeddings + pipeline)

| Module | May import |
|--------|------------|
| `shared/contracts/indexing.py` | stdlib, pydantic |
| `ai/embeddings/base.py` | stdlib, pydantic |
| `ai/embeddings/litellm_provider.py` | stdlib, litellm, tenacity, `config`, `ai.embeddings.base` |
| `ai/embeddings/factory.py` | stdlib, `ai.embeddings.base`, lazy `litellm_provider` |
| `ai/embeddings/chunker.py` | stdlib, pydantic, langchain_text_splitters, `config` |
| `ai/services/cache.py` | stdlib, `redis.asyncio`, `config`, `ai.embeddings.base` |
| `ai/workflows/pipeline.py` | stdlib, pydantic, `ai.embeddings.*`, `ai.services.cache` |

Must **not** import: FastAPI, SQLAlchemy, `notes/*`, `worker/*`, `qdrant-client`.

### 4.11 ARQ worker — `src/worker/` (Sub-step 1.3)

```
ARQ queue (Redis)
    │
    ▼
embed_note_task(ctx, request_dict)
    │
    ├─► IndexingRequest validate
    ├─► ai_enabled / DELETE short-circuits
    ├─► get_embedding_provider()
    ├─► EmbeddingPipeline(process_note)  [ctx["redis"] for cache]
    ├─► NoteVectorIndexer (Qdrant upsert/delete when qdrant_enabled)
    └─► IndexingResult → Redis job result
```

| Module | Responsibility |
|--------|----------------|
| `worker/main.py` | `WorkerSettings`, `startup`/`shutdown`, shared `ctx["redis"]` |
| `worker/tasks.py` | Export registered ARQ functions |
| `worker/ingestion/tasks.py` | `embed_note_task` implementation |

**Import law**: stdlib, arq, pydantic, `config`, `ai.*`, `shared.*` — no FastAPI, SQLAlchemy, domain repositories, `qdrant-client`.

### 4.12 AI retrieval — RBAC search (Sub-step 2.2)

```
GET /ai/test-search?q=...
    │
    ├─► get_current_context() → RequestContext (user_id, workspace_id, role)
    ├─► get_workspace_vector_search().search(...)
    │       ├─► get_embedding_provider().embed_single(q)
    │       ├─► build_rbac_filter(workspace_id, user_id, role)
    │       └─► get_async_qdrant_client().query_points(..., query_filter=rbac)
    └─► list[dict] hits (scores + payload fields for validation)
```

| Module | Responsibility |
|--------|----------------|
| `ai/retrieval/filters.py` | Pure `build_rbac_filter()` — mirrors `notes/permissions.py`; no FastAPI/SQLAlchemy |
| `ai/retrieval/wrapper.py` | `WorkspaceVectorSearch`, `SearchResult`, `get_workspace_vector_search()` — **only** search entry point |
| `ai/retrieval/workspace_search.py` | `WorkspaceVectorIndex` — upsert/delete vectors per workspace |
| `ai/retrieval/indexer.py` | `NoteVectorIndexer` — worker-facing delete-then-upsert |
| `ai/retrieval/client.py` | `get_async_qdrant_client()` singleton |
| `ai/retrieval/collection.py` | Collection bootstrap (`notes_chunks`, dim 3072) |
| `ai_gateway/search.py` | `GET /ai/test-search` — JWT-scoped validation endpoint |

**RBAC filter contract** (must stay aligned with `notes/permissions.py`):

| Role | Filter |
|------|--------|
| `owner`, `admin` | `must`: `workspace_id` |
| `member` | `must`: `workspace_id`; `should`: `visibility=public` OR `created_by=user_id` (min 1) |

**Security invariants**

- `workspace_id` on every search is a `must` condition from JWT `wid`, never from query/body.
- Routers never import `AsyncQdrantClient` directly.
- `filters.py` / `wrapper.py` do not import FastAPI, SQLAlchemy, or domain repositories.

**Quality gate** (engineering sign-off): relevance `score` > 0.4 for on-topic queries; cross-workspace isolation; member cannot see others’ private chunks.

### 4.13 AI chat RAG — Slice 3 (Sub-steps 3.1–3.2)

```
POST /ai/chat  { "message": "..." }
    │
    ├─► get_current_context() → RequestContext
    ├─► freeze: workspace_id, user_id, role as plain str (never pass ctx to services)
    ├─► RagService.answer(question, workspace_id, user_id, role)
    │       ├─► WorkspaceVectorSearch.search(...)  — RBAC + embed query
    │       ├─► token budget: TOKEN_BUDGET_PER_REQUEST (char cap on context)
    │       ├─► build_rag_user_message() + RAG_SYSTEM_INSTRUCTION (ai/prompts/rag.py)
    │       ├─► litellm.acompletion(model=LLM_MODEL, response_format=RAGAnswer)
    │       └─► ground cited_chunk_ids against retrieved set → list[Citation]
    └─► ChatResponse(answer, citations, chunks_*, latency_ms)
```

| Module | Responsibility |
|--------|----------------|
| `config.py` | `LLM_MODEL`, `LLM_TEMPERATURE`, `LLM_MAX_TOKENS`, `TOKEN_BUDGET_PER_REQUEST`, `LANGSMITH_*`, `langsmith_enabled` |
| `ai/prompts/rag.py` | `RAGAnswer` schema, `RAG_SYSTEM_INSTRUCTION`, `build_rag_user_message()` — **only** prompt strings |
| `ai/services/rag_service.py` | `RagService`, `ChatResult`, `Citation`, `get_rag_service()` — no FastAPI/SQLAlchemy/RequestContext |
| `ai_routes/chat.py` | `POST /ai/chat` — freezes ctx, injects `RagService` via `Depends(get_rag_service)` |

**Security invariants**

- `workspace_id` / `user_id` / `role` passed to `RagService` are frozen strings from JWT only.
- Citations are built only from chunks actually retrieved; LLM `cited_chunk_ids` are validated against that set (top-3 fallback if empty).
- Structured output only: `response_format=RAGAnswer` — no regex parsing of LLM text.

**Slice 3 gate** (sign-off): `POST /ai/chat` returns 401 without token; grounded answer + `citations` with real `note_id` when notes are indexed; `latency_ms` < 5000; empty workspace returns the refusal string, not cross-tenant data.

### 4.14 AI chat streaming — Slice 4 (Sub-steps 4.1–4.2)

```
POST /ai/chat/stream  { "message": "..." }
    │
    ├─► get_current_context() → RequestContext
    ├─► freeze: workspace_id, user_id, role as plain str BEFORE generator opens
    ├─► rag = Depends(get_rag_service) resolved BEFORE generate() — closure capture
    ├─► StreamingResponse(generate(), text/event-stream)
    │       headers: Cache-Control: no-cache, X-Accel-Buffering: no
    │       async for event in rag.stream_answer(...):
    │           yield data: {StreamToken|StreamMetadata JSON}\n\n
    │       finally: data: [DONE]\n\n
    └─► Client receives progressive tokens, then metadata + citations
```

| Module | Responsibility |
|--------|----------------|
| `ai/services/rag_service.py` | `StreamToken`, `StreamMetadata`, `StreamEvent`; `RagService.stream_answer()` — same retrieve/budget/prompt as `answer()`, `litellm.acompletion(stream=True)`, citations from top retrieved chunks at end (not LLM token parsing) |
| `ai_routes/chat.py` | `POST /ai/chat/stream` — SSE adapter; `ctx` never referenced inside `generate()` |

**SSE event contract**

| `type` | When | Payload |
|--------|------|---------|
| `token` | During LLM stream | `content` (string; client skips empty) |
| `metadata` | After stream completes | `citations`, `chunks_retrieved`, `chunks_used`, `latency_ms` |
| `error` | On exception mid-stream | `message` (generic; no stack leak) |
| `[DONE]` | Always in `finally` | Literal terminal frame |

**Security / infra invariants**

- Same JWT freeze pattern as `POST /ai/chat`; `generate()` uses only `workspace_id`, `user_id`, `role`, `body.message`, and closure-captured `rag`.
- Nginx: `X-Accel-Buffering: no` + `Cache-Control: no-cache` required or edge may buffer the full response (Gate 1 failure).
- `POST /ai/chat` unchanged — JSON `ChatResponse` for non-streaming clients.

**Slice 4 gate** (sign-off): progressive `token` events via curl `--no-buffer`; final `metadata` with `citations[]`; `data: [DONE]` closes stream; empty workspace yields refusal token + empty citations; `POST /ai/chat` still returns JSON; `GET /health` unchanged.

### 4.15 AI conversation memory — Slice 5 (Sub-steps 5.1–5.2)

```
POST /ai/chat  { "message": "...", "thread_id": "<optional-uuid>" }
    │
    ├─► get_current_context() → RequestContext
    ├─► get_session() → AsyncSession (route layer only)
    ├─► freeze: workspace_id, user_id, role as plain str
    ├─► RagService.answer(..., thread_id=..., db=session)
    │       ├─► _load_thread_context() → ThreadService.get_or_create_thread + load_history
    │       ├─► WorkspaceVectorSearch.search(...)
    │       ├─► ContextBuilder.build(history + retrieved_chunks) → BuiltContext.messages
    │       ├─► litellm.acompletion(messages=built.messages, ...)
    │       ├─► ground citations against built.context_chunks
    │       └─► ThreadService.persist_turn() after success
    └─► ChatResponse(..., thread_id=resolved_uuid)
```

| Module | Responsibility |
|--------|----------------|
| `ai_memory/models.py` | `AIThread` (UUID id, `WorkspaceTenantMixin`, `created_by`, `is_active`), `AIMessage` (role check, JSONB citations, FK cascade) |
| `ai_memory/repository.py` | `ThreadRepository` — stateless; `workspace_id` filter on every query |
| `ai/memory/service.py` | `ThreadService` — business logic over repository; no SQLAlchemy imports |
| `ai/memory/context_builder.py` | `ContextBuilder` — char budget: 70% history / 30% context minimum; at least one chunk if available |
| `ai/services/rag_service.py` | `_load_thread_context()`, `thread_id`/`db` kwargs; `ChatResult.thread_id`, `StreamMetadata.thread_id` |
| `ai_routes/chat.py` | `ChatRequest.thread_id`, `ChatResponse.thread_id`; `Depends(get_session)` passed to RAG |

**Layering rule**

- **Product layer** (`ai_threads`, `ai_messages`): what users see in the UI; managed by `ThreadService`.
- **Execution layer** (LangGraph `AsyncPostgresSaver`): Slice 6 only; linked by `thread_id` string, no FK.

**Security invariants**

- `ThreadRepository` applies `workspace_id` on every read/write — cross-workspace thread access returns `None` or no-op.
- `get_or_create_thread()` raises `ValueError` when `thread_id` does not belong to JWT workspace.
- `RagService` never imports `AsyncSession` at runtime (TYPE_CHECKING only); session injected from routes.

**Slice 5 gate** (sign-off): `ContextBuilder` produces 3 messages for sample input; migration applied (`ai_threads`, `ai_messages`); `POST /ai/chat` returns `thread_id`; second message with same `thread_id` includes prior turn in context when notes are indexed.

### 4.16 AI thread management routes — Slice 5.3

```
GET /ai/threads
    ├─► get_current_context() → RequestContext
    ├─► get_session() → AsyncSession
    ├─► ThreadRepository.list_threads(db, workspace_id, user_id)
    └─► list[ThreadResponse]

GET /ai/threads/{thread_id}/messages
    ├─► get_current_context() → RequestContext
    ├─► get_session() → AsyncSession
    ├─► ThreadRepository.get_recent_messages(...)
    ├─► if empty: ThreadRepository.get_thread(...) for secure 404 discrimination
    └─► list[MessageResponse] (ordered oldest→newest)

DELETE /ai/threads/{thread_id}
    ├─► get_current_context() → RequestContext
    ├─► get_session() → AsyncSession
    ├─► ThreadRepository.delete_thread(...)  # soft delete
    └─► 204 (or 404 if not found / wrong workspace)
```

| Module | Responsibility |
|--------|----------------|
| `ai_routes/chat.py` | Passes `thread_id` and `db` to `RagService.answer()` / `stream_answer()`; maps invalid cross-workspace thread reuse to HTTP 400 |
| `ai_routes/threads.py` | Thread list/messages/delete HTTP adapters |
| `ai_memory/repository.py` | Workspace-scoped thread/message queries and soft delete |
| `ai/services/rag_service.py` | Returns `thread_id` in JSON and SSE metadata; persists turns even when retrieval is empty |

**Slice 5.3 gate** (sign-off): end-to-end flow verified with real JWTs — new thread UUID returned, history thread continuation works, thread list/messages routes return expected data, foreign-workspace `thread_id` blocked (400), SSE metadata includes `thread_id` + `[DONE]`, delete returns 204, `/health` unchanged.

### 4.17 LangGraph agent tools — Slice 6.2

```
Agent graph tool_node (Slice 6.3+)
    ├─► db_session_var.set(session)   # before mutation tools only
    ├─► LiteLLM tools=[OpenAI function defs from StructuredTool]
    └─► invoke tool coroutine with validated args_schema

search_notes / summarize_workspace
    └─► RagService.answer(workspace_id, user_id, role as str)
            └─► WorkspaceVectorSearch + litellm (no HTTP, no RequestContext)

create_note / update_note
    └─► db = db_session_var.get()
    └─► NoteService.create_note(db, ...) / update_note(db, ...)
            └─► NoteRepository(session, workspace_id=int(...))
```

| Module | Responsibility |
|--------|----------------|
| `ai/tools/schemas.py` | Pydantic `args_schema` for LLM argument validation and JSON schema generation |
| `ai/tools/note_tools.py` | `StructuredTool.from_function()` × 4; `get_note_tools()`; `db_session_var` |
| `notes/service.py` | Agent-facing note mutations; string IDs → `int` for repository |
| `ai/services/rag_service.py` | Unchanged; `answer()` reused by search/summarize tools |
| `ai/memory/checkpointer.py` | Execution-layer persistence (Slice 6.1); linked to product `thread_id` by string only |

**Invariants**

- Tools never import repositories, FastAPI, or `RequestContext`.
- `workspace_id`, `user_id`, `role` on every tool schema — copied from agent state, not LLM-invented.
- `AsyncSession` is not an LLM argument; only `contextvars` for note mutations.

**Slice 6.2 gate**: `get_note_tools()` returns 4 tools; each `args_schema` validates; import smoke test in Docker passes.

### 4.18 LangGraph agent routes + lifecycle wiring — Slice 6.4

```
POST /ai/agent  { "message": "...", "thread_id": "<optional-uuid>" }
    │
    ├─► get_current_context() → RequestContext
    ├─► get_session() → AsyncSession
    ├─► freeze: workspace_id, user_id, role before async graph call
    ├─► resolve thread_id via ThreadService / ThreadRepository
    ├─► db_session_var.set(db)
    ├─► graph = get_workspace_assistant()   # lazy-compiled singleton
    ├─► graph.ainvoke(initial_state, config={"configurable":{"thread_id":...}})
    ├─► db_session_var.reset(token)
    └─► AgentResponse(answer, thread_id, steps_taken, tool_calls_made)
```

```
POST /ai/agent/stream  (SSE)
    │
    ├─► same auth/context freeze/thread resolution
    ├─► db_session_var.set(db) before graph streaming
    ├─► graph.astream_events(..., version="v2")
    │     ├─ on_chat_model_stream → {"type":"token","content":"..."}
    │     ├─ on_tool_start       → {"type":"tool_start","tool":"...","args":...}
    │     ├─ on_tool_end         → {"type":"tool_end","tool":"...","result":"..."}
    │     └─ final               → {"type":"done","thread_id":"...","steps_taken":N}
    ├─► emit terminal `data: [DONE]`
    └─► db_session_var.reset(token) in finally
```

| Module | Responsibility |
|--------|----------------|
| `ai_routes/agent.py` | `POST /ai/agent` and `POST /ai/agent/stream`; HTTP adapter only |
| `ai/workflows/workspace_assistant.py` | Lazy graph factory + `call_model`/`execute_tools`/`should_continue` |
| `ai/workflows/state.py` | `AgentState` (`messages`, tenant primitives, `steps_taken`, `thread_id`) |
| `ai/memory/checkpointer.py` | LangGraph checkpoint execution persistence |
| `main.py` | Lifespan `init_checkpointer()` startup + `close_checkpointer()` shutdown; router registration |

**Operational invariants**

- `POST /ai/chat` and `POST /ai/chat/stream` are unchanged and remain the direct RAG path.
- Agent routes are additive (`/ai/agent*`) and can degrade gracefully if checkpointer init fails.
- `workspace_id` is always from JWT context; never from request body.
- Graph configurable thread key is `{"configurable": {"thread_id": thread_id}}` and aligns with `ai_threads.id`.

**Slice 6.4 gate** (sign-off): checkpointer startup log present; `/ai/chat` unaffected; `/ai/agent` returns `thread_id` + `steps_taken`; streaming emits token/tool/done SSE frames; cross-workspace thread reuse blocked (400); iteration guard enforced by `AGENT_MAX_ITERATIONS`.

### 4.19 Observability — logging, Langfuse, Prometheus, Grafana

```
FastAPI request
    ├─► JSON log lines (stdout)     setup_logging() in lifespan only
    ├─► GET /metrics                Instrumentator → dashnote_api_* counters/histograms
    └─► RagService path
            └─► rag_trace / rag_span → get_langfuse_client() (lazy, optional)

Prometheus (Compose)
    scrape api:8000/metrics every 15s  (monitoring/prometheus.yml)
    └─► Grafana (Compose :3001)
            datasource: http://prometheus:9090
            dashboard: DashNote / API Overview (provisioned JSON)
```

| Module | Responsibility |
|--------|----------------|
| `observability/logging.py` | `setup_logging()`, `get_logger()` — JSON schema to stdout |
| `observability/langfuse_client.py` | `get_langfuse_client()` singleton; never raises; not called from lifespan |
| `observability/tracing.py` | `rag_trace`, `rag_span` — async context managers; no-op when Langfuse disabled |
| `observability/__init__.py` | Public exports for logging + Langfuse + tracing |
| `ai/services/rag_service.py` | Only RAG instrumentation site (wraps `answer()` / `stream_answer()`) |
| `main.py` | Lifespan calls `setup_logging()`; `Instrumentator` exposes `/metrics` |
| `config.py` | `LANGFUSE_*`, `langfuse_enabled`; `LANGSMITH_*` present but inactive |
| `monitoring/prometheus.yml` | Job `dashnote_api` → `api:8000`, path `/metrics`, 15s interval, 7d retention |
| `monitoring/grafana/provisioning/` | Datasource + **API Overview** dashboard (4 panels on Step 4 metric names) |

**Langfuse trace contract** (when keys set):

| Observation | Children / outputs |
|-------------|-------------------|
| `rag.answer` | metadata: `workspace_id`, `user_id`, `role` |
| `retrieval` | `chunks_retrieved`, `latency_ms` |
| `context_building` | `chunks_used`, `char_budget`, `latency_ms` |
| `llm_generation` | token fields, optional `cost`, `latency_ms` |

**Prometheus metric contract** (HTTP only; prefix `dashnote_api_`):

| Metric | Type | Dashboard use |
|--------|------|----------------|
| `dashnote_api_http_requests_total` | counter | `rate(...[5m])`, 5xx filter `status=~"5.."` |
| `dashnote_api_http_request_duration_seconds_bucket` | histogram | `histogram_quantile(0.95|0.99, sum(rate(..._bucket[5m])) by (le))` |

**Import / wiring invariants**

- Langfuse SDK only in `langfuse_client.py` and `tracing.py`; `RagService` imports `observability.tracing` only.
- No custom metrics in routers/services; no Loki/Tempo/Jaeger/OTel Collector in Compose.
- Prometheus scrapes **`api`** directly (port 8000 on Compose network), not Nginx :80.

**Documentation:** `docs/observability.md` (runbook), `src/docs/observe.md` (agent steps).

**Observability gate** (sign-off): JSON logs from `docker compose logs api`; `/metrics` exposes `dashnote_api_*`; Prometheus target `dashnote_api` UP; Grafana **API Overview** shows data after API traffic; Langfuse `rag.answer` trace after `/ai/chat` when keys configured.

## 5) Data model and persistence design

### 5.1 Core entities (implemented)
- `users`
- `workspaces`
- `workspace_users` (membership + role)
- `notes`
- `notebooks`
- `pages` (model exists and relates to notebooks)
- `files` (metadata + `storage_key`; binary content in configured `StorageBackend`)
- `note_attachments` (association between `notes` and `files`)
- `ai_threads` (conversation threads per workspace/user)
- `ai_messages` (messages within a thread; role check constraint)

### 5.2 Shared mixins/patterns
- `TimestampMixin` for auditing fields
- `WorkspaceTenantMixin` for tenant key
- `tenant_filter(model, workspace_id)` for standardized predicate

### 5.3 Transaction pattern
Repositories currently perform:
- `session.add(...)`
- `session.commit()`
- optional `session.refresh(...)`

This keeps write semantics explicit and local to repository methods.

## 6) Dependency and responsibility matrix
- `main.py`: app composition, lifespan (`setup_logging`, ARQ, Qdrant, checkpointer), module registration, `ProxyHeadersMiddleware`, global rate limit dependency, Prometheus `Instrumentator` → `/metrics`
- `nginx/default.conf` (Compose): edge `limit_req` per `$binary_remote_addr`, reverse proxy to `api:8000`, tracing/proxy headers
- `monitoring/prometheus.yml` (Compose): scrape config for `dashnote_api` job
- `monitoring/grafana/provisioning/` (Compose): Prometheus datasource + provisioned dashboards
- `observability/logging.py`: JSON logging setup
- `observability/langfuse_client.py`: optional Langfuse client
- `observability/tracing.py`: RAG trace/spans for Langfuse
- `core/database/session.py`: async engine/session factory + DI dependency
- `core/redis/client.py`: shared async Redis client (`get_async_redis`) when `REDIS_URL` is set
- `core/redis/redis.py`: JWT refresh + access blacklist token store (`get_token_store`)
- `core/redis/cache.py`: tenant-scoped `WorkspaceRedisCache` (cache-aside JSON + generation bumps)
- `core/redis/deps.py`: `get_workspace_cache` / `get_redis_connection` for routers and rate limiting
- `core/storage/client.py`: storage backend factory (`get_storage`) used by file write/read/delete paths
- `core/storage/utils.py`: MIME and upload validation helpers
- `core/security/dependency.py`: token decode to context; optional decode for rate limit identity
- `core/security/rate_limit.py`: fixed-window Redis rate limits + FastAPI dependencies
- `core/security/permissions.py`: route-level RBAC
- `shared/contracts/indexing.py`: API ↔ worker indexing message contracts
- `ai/embeddings/base.py`: embedding provider ABC + `EmbeddedChunk`
- `ai/embeddings/litellm_provider.py`: LiteLLM `aembedding` + retries
- `ai/embeddings/factory.py`: process-wide embedding provider singleton
- `ai/embeddings/chunker.py`: deterministic note chunking
- `ai/services/cache.py`: Redis embedding vector cache-aside
- `ai/workflows/pipeline.py`: chunk → cache → embed orchestration
- `worker/main.py`: ARQ `WorkerSettings` and process lifecycle
- `worker/ingestion/tasks.py`: `embed_note_task` (pipeline + Qdrant via `NoteVectorIndexer`)
- `ai/retrieval/filters.py`: RBAC Qdrant `Filter` builder
- `ai/retrieval/wrapper.py`: tenant-safe semantic search (`WorkspaceVectorSearch`)
- `ai/retrieval/workspace_search.py`: Qdrant upsert/delete (`WorkspaceVectorIndex`)
- `ai/retrieval/indexer.py`: note-level vector indexing orchestration
- `ai_gateway/search.py`: `GET /ai/test-search` validation route
- `ai/prompts/rag.py`: RAG prompt templates and `RAGAnswer` structured output schema
- `ai/services/rag_service.py`: `RagService.answer()` / `stream_answer()` — retrieval + LLM + grounded citations
- `ai_memory/models.py`: `AIThread`, `AIMessage` ORM (product conversation layer)
- `ai_memory/repository.py`: `ThreadRepository` — tenant-scoped thread/message persistence
- `ai/memory/service.py`: `ThreadService` — thread lifecycle + persist turn
- `ai/memory/context_builder.py`: `ContextBuilder` — LiteLLM messages array + budget
- `ai_routes/chat.py`: `POST /ai/chat` (JSON), `POST /ai/chat/stream` (SSE) — HTTP adapters (ctx freeze + `Depends(get_session)`)
- `ai_routes/threads.py`: thread list, messages, soft delete
- `ai_routes/agent.py`: `POST /ai/agent`, `POST /ai/agent/stream` — LangGraph HTTP adapters
- `ai/workflows/workspace_assistant.py`: compiled LangGraph workspace assistant
- `ai/tools/note_tools.py`: agent `StructuredTool` definitions
- `<module>/router.py`: HTTP orchestration
- `<module>/service.py`: domain/business rules (where present)
- `<module>/repository.py`: DB access + persistence
- `<module>/schemas.py`: request/response contracts
- `<module>/models.py`: ORM table mapping

## 7) Error handling strategy
- Domain validation and authorization use HTTP exceptions with explicit status codes:
  - 400: invalid role/state conflicts
  - 401: auth failure
  - 403: permission denied
  - 404: entity/membership not found
  - 429: application rate limit exceeded (`Retry-After` header)
- Fallback global exception handler returns generic 500 body.

## 8) Testing strategy alignment
Current tests validate:
- permissions and tenant repository behavior
- notebooks API
- notes RBAC API
- auth security logic and token rotation / blacklist flows
- `WorkspaceRedisCache` cache-aside and generation invalidation (`tests/core/test_workspace_redis_cache.py`)
- application rate limiter behavior (`tests/core/test_rate_limit.py`)
- page versioning behavior
- files module flows with mocked storage (`tests/files/`)
- Supabase smoke path for integrated flow

Recommended rule:
- each new module must add at least:
  - context/tenant-scope tests
  - role-based authorization tests
  - happy-path CRUD/service tests
- for modules that touch object storage: mock `StorageBackend` / IO boundaries so CI does not depend on MinIO, R2, or local disk layout

## 9) Extension blueprint for new modules
For any new bounded module under `src/<module>/`:
1. Create `models.py`, `schemas.py`, `repository.py`, `router.py`.
2. Add `service.py` if business rules are non-trivial.
3. Inject `RequestContext` in protected routes.
4. Scope tenant queries through repository + `tenant_filter`.
5. Use `require_roles` and domain permission helpers where needed.
6. Register router in `main.py`.
7. Add migration + tests.

If the module stores binary blobs, use `StorageBackend` (`core/storage/client.py`) for bytes and keep SQL rows tenant-scoped with metadata and `storage_key`, following the `files` module pattern.

This keeps all modules consistent with current architecture and minimizes security regression risk.
<!--  -->
