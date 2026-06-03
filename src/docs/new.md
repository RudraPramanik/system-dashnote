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

Out of scope:
- Frontend design
- Cloud-specific provisioning beyond the provided `docker-compose.yml` and `nginx/default.conf`
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
- `ProxyHeadersMiddleware` (Uvicorn) so `request.client` reflects the proxied client when `X-Forwarded-For` is trusted.
- CORS middleware
- **Global application rate limit** dependency (`enforce_global_rate_limit`): Redis fixed-window counter per `user_id` (from JWT when present) or client IP; skipped when Redis is unavailable.
- module routers
- global exception handler

Registered routers:
- `core.health` → `GET /health` (deep probe: `SELECT 1`, Redis `PING` when Redis is configured; **503** if a required dependency fails)
- `/auth`
- `/files`
- `/notebooks`
- `/notes`
- `/workspaces`
- `/workspaces/members`
- `/ai` → `GET /ai/test-search` (internal semantic search validation; `ai_gateway/search.py`)
- `/ai` → `POST /ai/chat` (RAG chat MVP; `ai_routes/chat.py`)
- `/ai` → `POST /ai/chat/stream` (SSE streaming RAG; `ai_routes/chat.py`)

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
- `main.py`: app composition, module registration, `ProxyHeadersMiddleware`, global rate limit dependency
- `nginx/default.conf` (Compose): edge `limit_req` per `$binary_remote_addr`, reverse proxy to `api:8000`, tracing/proxy headers
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
<!-- system documentation -->
## DashNoteSystem backend (system workflow & routing)

### Overview
This project is a **multi-tenant Notes backend** built with **FastAPI + async SQLAlchemy**. Authentication is handled by the `auth` service (JWT), and every other service uses the JWT to build a **workspace-aware** `RequestContext`:

- `user_id` (from JWT `sub`)
- `workspace_id` (from JWT `wid`)
- `role` (from JWT `role`)

All tenant-scoped data access is performed through repositories that filter by `workspace_id`.

### Entry point: `src/main.py`
`src/main.py` creates the FastAPI app and registers routers:

- **Reverse-proxy headers**: `uvicorn.middleware.proxy_headers.ProxyHeadersMiddleware` (trusted hosts `*`) so `request.client` reflects the original client when `X-Forwarded-For` is set by Nginx.
- **Application rate limits**: a global FastAPI dependency (`core.security.rate_limit.enforce_global_rate_limit`) enforces Redis-backed fixed-window limits when `REDIS_URL` is configured (see **Rate limiting** below).
- `src/auth/router.py` (prefix: `/auth`)
- `src/notebooks/router.py` (prefix: `/notebooks`)
- `src/notes/router.py` (prefix: `/notes`)
- `src/files/router.py` (mounted at `/files` via `src/main.py`)
- `src/workspaces/router.py` (prefix: `/workspaces`)
- `src/membership/router.py` (prefix: `/workspaces/members`)
- `src/ai_gateway/search.py` (prefix: `/ai` — e.g. `GET /ai/test-search` for semantic note search validation)
- `src/ai_routes/chat.py` (prefix: `/ai` — `POST /ai/chat` RAG assistant; Slice 3; `POST /ai/chat/stream` SSE; Slice 4)
- `src/ai_routes/threads.py` (prefix: `/ai` — `GET /ai/threads`, `GET /ai/threads/{thread_id}/messages`, `DELETE /ai/threads/{thread_id}`; Slice 5.3)

It also mounts **`core.health`** for orchestration:

- `GET /health` — deep probe: async `SELECT 1` on PostgreSQL and Redis `PING` when Redis is configured (`REDIS_ENABLED` and `REDIS_URL`). Returns **200** when all required dependencies respond, **503** otherwise, with `timestamp`, `latency_ms`, and a `dependencies` map (`database`, and `redis` when applicable).

### Rate limiting (Nginx + FastAPI)
Traffic is limited at two layers: **per IP at the edge** (Nginx) and **per identity in the app** (FastAPI + Redis).

#### Layer 1 — Nginx (`nginx/default.conf`)
- Compose runs **`nginx:alpine`** in front of the **`api`** service (host port **80** → container **80**).
- `limit_req_zone $binary_remote_addr zone=api_per_ip:10m rate=10r/s;` with `limit_req zone=api_per_ip burst=20 nodelay;` on proxied traffic.
- Nginx forwards to `http://api:8000`, sets **`X-Real-IP`**, appends the client to **`X-Forwarded-For`**, forwards **`X-Forwarded-Proto`**, and sets **`X-Request-ID`** (`$request_id`) for tracing.

#### Layer 2 — FastAPI (`core/security/rate_limit.py`)
- **`RateLimiter`**: fixed-window counters in Redis (`INCR` + `EXPIRE` on first hit in the window). Keys follow `rate_limit:{scope}:{user_id|ip}:{window_index}` so each window is isolated without scanning.
- **Redis**: `core/redis/deps.py` (`get_redis_connection`) supplies the async client. When Redis is not configured, checks are skipped (fail-open) so local/dev without Redis keeps working.
- **Identity**: `get_optional_current_context` in `core/security/dependency.py` uses the same access-token validation path as `get_current_context` (via `_context_from_access_token`). If a valid access token is present, the counter is keyed by **`user_id`**; otherwise by **client IP** (after `ProxyHeadersMiddleware`).
- **Global limit**: **100 requests per minute** per identity, applied as an app-level dependency in `main.py`.
- **`POST /auth/login`**: stricter limit **5 requests per minute** per identity (`enforce_auth_login_rate_limit` on the route).
- **429 responses**: `HTTPException` with status **429** and a **`Retry-After`** header (seconds), derived from Redis `TTL` when possible.

### Request lifecycle (workflow)
Most endpoints follow the same flow:

1. **Client authenticates** using `POST /auth/login` and obtains an `access_token`.
2. Client calls any protected route with:
   - header: `Authorization: Bearer <access_token>`
3. Router dependency `core.security.dependency.get_current_context` decodes the JWT and returns `core.security.context.RequestContext`.
4. Router uses:
   - `ctx.workspace_id` to scope repository queries
   - `ctx.user_id` to enforce ownership rules (when needed)
   - `ctx.role` to enforce RBAC (via `core.security.permissions.require_roles(...)` or per-entity permission helpers)
5. Repository executes an **async SQLAlchemy** query and returns DB models.
6. Router maps models to response schemas (Pydantic).

### Auth-to-context injection (how it works everywhere)
The shared injection mechanism is:

- `core/security/dependency.py` provides `get_current_context(ctx=Depends(oauth2_scheme))`
- `auth/dependency.py` defines `oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")`

Routers typically add:

- `ctx: RequestContext = Depends(get_current_context)`
- OR role-gated: `ctx: RequestContext = Depends(require_roles("owner", "admin"))`

### Dependency map (which files depend on what)

#### App wiring
- `src/main.py`
  - depends on `config.settings`
  - registers `ProxyHeadersMiddleware` and `CORSMiddleware`
  - applies global `Depends(enforce_global_rate_limit)` on the FastAPI app
  - registers `core.health` (`GET /health`) before feature routers
  - depends on each module’s `router` (`auth/router.py`, `notes/router.py`, etc.)

#### Health / readiness
- `core/health.py`
  - `check_database(db)` runs `SELECT 1` via SQLAlchemy
  - `check_redis(redis)` runs `PING` when Redis is required
  - `GET /health` uses `Depends(get_db)` and `Depends(get_redis)` (`core/redis/deps.py`)
- `core/database/session.py`
  - depends on `config.settings.DATABASE_URL`
  - provides `get_session()` used by routers via `Depends(get_session)`

- `core/database/utils.py`
  - provides `tenant_filter(model, workspace_id)`
  - used by tenant-scoped repositories (e.g. `notes/repository.py`, `notebooks/repository.py`)

- `core/database/mixins.py`
  - provides `TimestampMixin`, `WorkspaceTenantMixin`, etc.

#### Tenant scoping and RBAC
- `core/security/context.py`
  - defines `RequestContext(user_id, workspace_id, role)`

- `core/security/dependency.py`
  - decodes JWT and builds `RequestContext`
  - optional bearer: `get_optional_current_context` (same decode path as `get_current_context`, used for rate-limit identity without forcing auth on public routes)

- `core/security/rate_limit.py`
  - `RateLimiter` (fixed window) + `enforce_global_rate_limit` / `enforce_auth_login_rate_limit`

- `core/security/permissions.py`
  - provides `require_roles(*allowed_roles)` dependency factory

#### Module specifics
- `src/auth/*`
  - issues JWTs in `auth/router.py`
  - stores/validates users and memberships in `auth/models.py` and `auth/service.py`

- `src/workspaces/*`
  - reads/updates `workspaces.models.Workspace` using `RequestContext.workspace_id`

- `src/membership/*`
  - uses existing `auth.models.WorkspaceUser` table (`workspace_users`) to list/invite/update/remove members

- `src/files/*`
  - tenant-scoped file metadata, upload/download orchestration, and permissions; details in **Storage system** below.

- `src/notes/*`
  - note ownership + visibility rules live in `notes/permissions.py`
  - note persistence lives in `notes/repository.py`

#### Redis (shared client, auth state, and cache-aside)
Redis is optional at runtime (`REDIS_ENABLED`, `REDIS_URL` in `config.settings`). When configured, the process uses **one shared async Redis client** (`core/redis/client.py`: `get_async_redis`) for:
- **JWT operational state** (refresh-token presence, access-token logout blacklist) via `get_token_store()` / `core/redis/redis.py` (see `src/docs/auth.md`).
- **Application reads** using **cache-aside** in selected routers (`GET /notes`, `GET /notes/{id}`, `GET /notebooks/`).

Tenant safety for cached reads:
- Keys are always prefixed with `workspace_id` from `RequestContext` (JWT `wid`), plus a **list variant** for notes (`staff` for owner/admin vs `u{user_id}` for members) so member-visible subsets cannot leak across users.
- **Invalidation** does not scan keys: each workspace keeps monotonic **generation counters** (`INCR` on `app:cache:gen:notes:{wid}` and `app:cache:gen:notebooks:{wid}`). Any note write bumps the notes generation; notebook create bumps the notebooks generation, so stale list/detail entries age out immediately when Redis is enabled.

FastAPI wiring (no change to how JWT context is produced):
- `core/redis/deps.py` exposes `get_redis_connection` (alias `get_redis`), and `get_workspace_cache`. Routers that need caching add `cache: WorkspaceRedisCache = Depends(get_workspace_cache)` alongside existing `get_current_context` / `get_session` dependencies. FastAPI deduplicates nested `Depends(get_current_context)` per request.
- **TTL**: cached JSON entries use `settings.CACHE_TTL_SECONDS` (default 60) as the Redis `SETEX` lifetime; generations provide correctness, TTL bounds recovery if a bump is missed.

When Redis is disabled, `WorkspaceRedisCache` receives `redis=None`: every read is a cache miss and mutations still succeed (no-op bump), preserving existing API behavior without Redis.

### Tenancy model (current implementation)
Multi-tenancy is implemented using:

- JWT claim `wid` -> `RequestContext.workspace_id`
- DB columns:
  - tenant-aware entities include `workspace_id` (via `WorkspaceTenantMixin`)

Tenant filtering is standardized through:

- `core/database/utils.tenant_filter(...)`

### RBAC rules (current implementation)
Roles come from `RequestContext.role` which is populated from JWT.

Common meaning:

- `owner`: workspace creator / highest privileges
- `admin`: admin privileges for the workspace
- `member`: standard member privileges

General enforcement patterns:

- Router-level role enforcement: `core.security.permissions.require_roles(...)`
- Entity-specific permission logic: `src/notes/permissions.py`

Notes RBAC/visibility (important):

- `owner/admin`: can CRUD any note in the workspace
- `member`:
  - can CRUD only their own notes
  - can view:
    - all public notes (`is_private = false`)
    - their own private notes (`created_by == ctx.user_id`)

### Storage system (current implementation)
Binary objects are stored **outside PostgreSQL** behind a small backend abstraction; the database holds **metadata**, **`workspace_id`**, and fields used for RBAC—same tenancy story as notes and notebooks.

**Backend selection**
- `core/storage/client.py`: `get_storage()` reads `config.settings.STORAGE_BACKEND` (`local`, `minio`, or `r2`) and returns a `StorageBackend` (`upload`, `download`, `delete`, `presigned_url`).
- **Local** (`LocalStorageBackend`): files under `LOCAL_STORAGE_PATH`; `presigned_url` returns `None` so clients typically use the app’s download route.
- **MinIO / R2** (`MinIOStorageBackend`, `R2StorageBackend`): S3-compatible endpoints via `aioboto3` / `boto3`; `presigned_url` may be used for direct client downloads depending on router/service behavior.

**Upload validation**
- `core/storage/utils.py`: MIME sniffing (`detect_mime_type`), `validate_file`, allowed extensions, and size limits so uploads stay consistent with detected type.

**Tenancy**
- `files.models.File` uses `WorkspaceTenantMixin`; repositories scope queries with `workspace_id` like other tenant modules (`tenant_filter` pattern).

**RBAC and visibility**
- `files/permissions.py`: `owner` and `admin` see all files in the workspace; `member` sees non-private files and any file they created (`created_by` matches `ctx.user_id`).

**Note ↔ file association**
- `core/database/associations.py` defines `note_attachments` only; `notes/` and `files/` do not import each other’s packages beyond this shared table.

**HTTP surface**
- `files/router.py` is mounted in `main.py` at prefix `/files` (upload, list, get, streamed download, patch, delete, attach to note, admin-oriented listing as implemented in code).

### Production-grade notes / operational concerns
Recommended operational practices:

- Treat `core/security/dependency.py` as the **single source of truth** for JWT claim names (`sub`, `wid`, `role`).
- Keep permission logic out of routers:
  - routers should call dedicated helpers (for example `notes/permissions.py`, `files/permissions.py`).
- When adding new tenant-scoped entities:
  - include a `workspace_id` column (use `WorkspaceTenantMixin`)
  - always scope queries via repository + `tenant_filter`.
- For file-like features, keep bytes in object storage and metadata in SQL; extend `StorageBackend` or settings rather than embedding secrets in code.

### AI vector search (Slice 2)
- Indexed note chunks live in Qdrant collection `notes_chunks` (see `src/docs/ai.md`).
- **Search** is only through `ai.retrieval.wrapper.WorkspaceVectorSearch` with `build_rbac_filter()` (`ai.retrieval.filters`) — same rules as `notes/permissions.py`. `workspace_id` is always from JWT `RequestContext`, never from query parameters.
- **Indexing** (worker) uses `ai.retrieval.workspace_search.WorkspaceVectorIndex` + `NoteVectorIndexer`.
- Diagnostic route: `GET /ai/test-search` (`ai_gateway/search.py`) — requires `ai_enabled` and `qdrant_enabled`; quality gate: relevance score > 0.4, workspace isolation verified.

### AI chat and thread APIs (Slice 3–5.3)
- Product route: `POST /ai/chat` (`ai_routes/chat.py`) — JWT required; router freezes `RequestContext` to plain strings before calling `RagService.answer()`. Optional body field `thread_id` continues a conversation; response includes `thread_id` for follow-up turns.
- Streaming route: `POST /ai/chat/stream` (`ai_routes/chat.py`) — same auth/freeze pattern; `StreamingResponse` with `text/event-stream`; `Cache-Control: no-cache` and `X-Accel-Buffering: no` so Nginx does not buffer the full response before forwarding. Final `metadata` event includes `thread_id`.
- Thread routes: `GET /ai/threads`, `GET /ai/threads/{thread_id}/messages`, `DELETE /ai/threads/{thread_id}` (`ai_routes/threads.py`) for conversation management in UI.
- Core engine: `ai/services/rag_service.py` — `answer()` (JSON) and `stream_answer()` (SSE events); no HTTP imports — reusable from LangGraph tools in Slice 6. Accepts optional `thread_id` and `db` (injected from route layer only).
- Memory ORM: `ai_memory/models.py` — `ai_threads`, `ai_messages` (Alembic migration `d3339fc62797`).
- Memory data access: `ai_memory/repository.py` — stateless `ThreadRepository` (workspace filter on every query).
- Memory services: `ai/memory/service.py` (`ThreadService`), `ai/memory/context_builder.py` (`ContextBuilder` — history + retrieval budget).
- Prompts: `ai/prompts/rag.py` only (one system instruction for both streaming and non-streaming).

### AI agent system path (Slice 6.1–6.4)
- **Checkpointer** (`ai/memory/checkpointer.py`): LangGraph `AsyncPostgresSaver` on dedicated psycopg3 async connection; initialized in `main.py` lifespan startup and closed in shutdown. Failure is non-fatal (agent degrades gracefully).
- **Graph state + workflow** (`ai/workflows/state.py`, `ai/workflows/workspace_assistant.py`): lazy-compiled singleton graph (`get_workspace_assistant()`), LiteLLM `tools=` calling, tool loop routing with `AGENT_MAX_ITERATIONS` guard.
- **Agent tools** (`ai/tools/note_tools.py`, `ai/tools/schemas.py`): four `StructuredTool` definitions (`search_notes`, `create_note`, `update_note`, `summarize_workspace`); mutation tools use `db_session_var`.
- **Agent routes** (`ai_routes/agent.py`): mounted under `/ai`:
  - `POST /ai/agent` (final answer response model `AgentResponse`)
  - `POST /ai/agent/stream` (SSE event stream from `graph.astream_events`)
- **Thread linkage**: route resolves/validates thread via `ThreadService`/`ThreadRepository`, then passes `{"configurable": {"thread_id": thread_id}}` so LangGraph checkpoints align with product `ai_threads.id`.
- **Coexistence rule**: `POST /ai/chat` and `POST /ai/chat/stream` remain unchanged as fast direct RAG endpoints; `/ai/agent*` is additive for multi-step tool-calling.

### Where to extend next
If you add new note-like resources or collaboration features:

- create a new module under `src/<module_name>/`
- implement:
  - `models.py`, `schemas.py`, `repository.py`, `router.py`
  - permission helper(s) if RBAC is non-trivial
- inject auth as described in `src/docs/auth.md`.

### Automated testing (files module)
Tests under `tests/files/` exercise the files flow with **pytest** and **pytest-asyncio**. Storage and IO boundaries (`aioboto3`, `pathlib.Path`, and related calls) are **mocked** so the suite does not require a live PostgreSQL instance or real object storage.

**Rate limiting (`core/security/rate_limit.py`)** is covered by `tests/core/test_rate_limit.py` (mocked async Redis).

**Fixtures and environment**
- `tests/conftest.py` wires `Settings` (database URL and JWT secret placeholders) for imports and dependencies used by file tests.
- On hosts without **libmagic** (typical on Windows), conftest provides a minimal **`magic` import stub** so `core.storage.utils` loads; production Docker images install **`libmagic1`** for real MIME detection.

**Command** (repository root):

```powershell
python -m pytest tests/files -q
```

**Pytest configuration**
- `pytest.ini`: `pythonpath = src`, `asyncio_mode = auto`, `addopts = --import-mode=importlib` (avoids duplicate `test_*.py` basenames across folders).

### Smoke testing (file upload, live API)
Use this after the stack is healthy (`docker compose up -d --build`, then `GET /health` → HTTP **200** with `"status":"ok"` and dependency details) to validate `files/router.py` end-to-end.

**Steps**
1. `POST /auth/register` (or login) to obtain `access_token`.
2. `POST /files/upload` as `multipart/form-data` with file part name `file`, form fields `is_private` and optional `description`.
3. Use an allowed extension consistent with sniffed MIME (example: `.txt` with `text/plain` body).

**Example** (repo root; requires `httpx`):

```powershell
python -c "import uuid, httpx; b='http://127.0.0.1'; e=f'test_{uuid.uuid4().hex[:8]}@exame.com'; t=httpx.post(f'{b}/auth/register', json={'email':e,'password':'Test123!','workspace_name':'ws'}, timeout=30).json()['access_token']; r=httpx.post(f'{b}/files/upload', headers={'Authorization':f'Bearer {t}'}, files={'file':('requirement.txt',b'req line\n','text/plain')}, data={'is_private':'false','description':'smoke'}, timeout=30); print(r.status_code, r.json())"
```

For **local uvicorn** without Docker (direct port **8000**), use `http://127.0.0.1:8000` as the base URL; Nginx and edge limits apply only when using the Compose stack as documented.

**Expected success**
- HTTP **200** and JSON including `id`, `name`, `mime_type`, `size_bytes`, and `download_url` (often a relative `/files/{id}/download` when the backend does not return a presigned URL).

### Docker Compose (Nginx, API, database, Redis, migrations)
Compose starts PostgreSQL and Redis, runs **`alembic upgrade head`** once via a **`migrate`** service after the database is healthy, then starts the **API** (listens on **8000** inside the Compose network). **`nginx`** publishes host port **80** and reverse-proxies to **`api:8000`** with the rate limit and tracing headers described under **Rate limiting**.

#### Prerequisites
- Docker Desktop running
- Host ports **80**, **5432**, and **6379** free (or change mappings in compose)

#### Start the stack
From the repository root:

```powershell
docker compose up -d --build
```

**Services**
- **nginx**: `nginx:alpine`, binds **80:80**, mounts `nginx/default.conf` (edge `limit_req` + proxy headers including `X-Request-ID`).
- **api**: built from `Dockerfile`, including **`libmagic1`** for `python-magic` during upload validation; also mapped **`8000:8000`** on the host for direct access to `/docs` and debugging (bypasses Nginx edge limits). Uses `env_file: .env` plus Compose `environment` overrides (`DATABASE_URL`, `ARQ_REDIS_URL`, etc.) so `settings.ai_enabled` and ARQ enqueue work in Docker. Prefer **`http://127.0.0.1/`** (port **80**) when testing the full proxy + Nginx `limit_req` path. After recreating `api`, restart **nginx** if `/health` returns 502 (stale upstream).
- **db**: `postgres:16-alpine` with healthcheck.
- **redis**: `redis:7-alpine` (JWT token state when the API is given `REDIS_URL`, application rate limits, optional cache-aside for read-heavy routes, ARQ job queue, and embedding vector cache keys `embed:v1:*`).
- **worker**: same image as `api`; runs `python -m arq src.worker.main.WorkerSettings`. Processes `embed_note_task` (chunk, embed, upsert/delete in Qdrant via `NoteVectorIndexer` when `QDRANT_URL` is set). Logs `qdrant_indexed`, `qdrant_points`, embedding metrics. Depends on `db`, `redis`, and `qdrant`.
- **qdrant**: vector store for dev (`6333`, collection `notes_chunks`, dim 3072). Set `QDRANT_URL=http://qdrant:6333` in Compose; host dev uses `http://127.0.0.1:6333`. Production: Qdrant Cloud via `.env`.
- **migrate**: one-shot job; exits after `alembic upgrade head` succeeds.

#### Verify
```powershell
docker compose ps
curl.exe -sS --max-time 10 http://127.0.0.1/health
docker compose logs --tail 50 api
docker compose logs --tail 50 nginx
docker compose logs --tail 50 migrate
docker compose logs --tail 50 worker
```

**Health check**: expect HTTP **200** and JSON including `status`, `timestamp`, `latency_ms`, and `dependencies` (each dependency reports `reachable`; Redis may include `configured: false` when Redis is not enabled in settings).

#### Stop
```powershell
docker compose down
```

#### Reset including volumes
```powershell
docker compose down -v
```

#### Re-run migrations only
```powershell
docker compose run --rm migrate
```

<!-- ai part documentation -->
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
| Agent tools | **`get_note_tools()`** (`ai/tools/note_tools.py`) — `StructuredTool` + Pydantic `args_schema`; service layer only |
| Note mutations (agent) | **`NoteService`** (`notes/service.py`) — `db_session_var` set by graph tool node before create/update |
| Checkpointer | **`init_checkpointer()`** / **`get_graph_checkpointer()`** (`ai/memory/checkpointer.py`) — psycopg3, separate from SQLAlchemy pool |
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

## Slice 6 (in progress) — LangGraph workspace assistant

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

- `src/docs/system.md` — API wiring, Compose, short AI summary
- `src/docs/lld.md` — §4.12 retrieval LLD
- `src/docs/rules.md` — dependency direction
