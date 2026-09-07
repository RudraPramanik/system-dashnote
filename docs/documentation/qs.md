# DashNoteSystem — Interview & Job Prep Q&A

Short answers tied to how this repository is built today. Use this for technical interviews, Upwork client calls, and system-design discussions.

**Production AI / RAG interview (general):** [`qs2.md`](qs2.md) — concept-clearance and hire-loop Q&A that is not tied to this repo’s file names.

**§1–20** — core Q&A on what we built and why.  
**§21** — **counter-questions**: pushback and “why not X?” follow-ups interviewers ask after your first answer. Practice answering without reading.

**Deeper references:** `system.md` · `ai.md` · `auth.md` · `rules.md` · `lld.md` · `blueprint/goal.md`

---

## Table of contents

1. [System overview](#1-system-overview)
2. [Architecture & module design](#2-architecture--module-design)
3. [Authentication & authorization](#3-authentication--authorization)
4. [Database & multi-tenancy](#4-database--multi-tenancy)
5. [API design & request lifecycle](#5-api-design--request-lifecycle)
6. [Storage & files](#6-storage--files)
7. [Redis, caching & rate limits](#7-redis-caching--rate-limits)
8. [Workers, events & background jobs](#8-workers-events--background-jobs)
9. [Embeddings & indexing](#9-embeddings--indexing)
10. [Vector search & RBAC retrieval](#10-vector-search--rbac-retrieval)
11. [RAG chat](#11-rag-chat)
12. [Streaming (SSE)](#12-streaming-sse)
13. [Threads & conversation memory](#13-threads--conversation-memory)
14. [LangGraph agent](#14-langgraph-agent)
15. [Automation & governance](#15-automation--governance)
16. [LLM layer & providers](#16-llm-layer--providers)
17. [Observability](#17-observability)
18. [Deployment & dependency tiers](#18-deployment--dependency-tiers)
19. [Tradeoffs & “why not X?”](#19-tradeoffs--why-not-x)
20. [Extending the codebase](#20-extending-the-codebase)
21. [Counter-questions — interviewer pushback](#21-counter-questions--interviewer-pushback)

**Format:** Each block is `They ask → You answer`. Practice the answer without reading first.

---

## 1. System overview

### What is DashNoteSystem?

A **multi-tenant notes backend**: FastAPI + async SQLAlchemy + PostgreSQL, with AI features (embeddings, RAG chat, LangGraph agent, file automation) layered on top. Every tenant is a **workspace**; JWT carries `workspace_id` and `role` so API and vector search enforce the same RBAC rules.

### What is the high-level request flow?

`Client → Nginx (optional) → FastAPI → JWT → RequestContext → router → service/repository → DB/storage`. AI routes call `RagService` or the LangGraph agent with **frozen** `workspace_id`, `user_id`, `role` strings — never raw user input for tenant scope.

### Why FastAPI + async SQLAlchemy?

Async I/O fits LLM calls, Qdrant, Redis, and S3-style storage without blocking the event loop. FastAPI gives typed dependencies (`RequestContext`, `get_session`) and OpenAPI docs for frontend integration.

### What are the main AI surfaces?

| Route | Purpose |
|-------|---------|
| `GET /ai/test-search` | Internal retrieval quality check |
| `POST /ai/chat`, `/ai/chat/stream` | Fast RAG — single retrieve + answer |
| `GET /ai/threads`, `.../messages` | Conversation history |
| `POST /ai/agent`, `/ai/agent/stream` | LangGraph tool loop (search, create/update notes, summarize) |

**Both** `/ai/chat*` and `/ai/agent*` coexist — chat is low-latency RAG; agent is multi-step tool use.

---

## 2. Architecture & module design

### Why vertical slices instead of a big “AI monolith”?

Each slice (embed → retrieve → chat → memory → agent → automation) ships value and has a **gate** before the next slice. Rollback is possible per slice. The blueprint in `blueprint/total.md` documents this explicitly.

### What is the dependency direction law?

```
shared/  ← imported by ai/, worker/, domain modules. Imports nothing from domain.
ai/      ← imports shared/ only. Never notes/, files/, FastAPI.
worker/  ← imports ai/ + shared/. Never HTTP routers.
notes/   ← calls ai/services via service interface only.
```

**Tools → services → repositories** — never shortcut to the DB from agent tools.

### Why keep `ai/` free of SQLAlchemy and FastAPI?

`RagService` and retrieval code must run from **workers** and **agent tools** outside HTTP. Importing `RequestContext` or ORM into `ai/` would couple inference to the web layer and break worker reuse.

### Why separate `ai_memory/` from `ai/memory/`?

- **`ai_memory/`** — SQLAlchemy models (`AIThread`, `AIMessage`) — product persistence for the UI.
- **`ai/memory/`** — pure services (`ThreadService`, `ContextBuilder`) — no ORM in `ai/*` import law.

LangGraph checkpoint state lives in Postgres via `AsyncPostgresSaver` (`ai/memory/checkpointer.py`), linked to product threads by `thread_id` string only.

### Why LiteLLM instead of direct OpenAI/Gemini SDKs?

One interface for embeddings and chat across providers (`gemini/...`, `nvidia_nim/...`, `openai/...`). Provider keys are configured in `shared/llm/env.py`. Switching models is an env change, not a refactor.

### Why hosted embeddings/LLMs only — no local models?

8GB-friendly deploys, no GPU ops, predictable cost. The product owns **orchestration, retrieval, tenancy, and evals** — not inference infrastructure.

### Why ARQ instead of Celery or in-request embedding?

Embedding and file parsing are slow and rate-limited. The API **enqueues** after DB commit and returns immediately. ARQ on Redis reuses existing infra; worker retries on transient LLM failures.

### Why Qdrant instead of pgvector?

Dedicated vector DB with payload indexes on `workspace_id`, `note_id`, `created_by`, `visibility` — filters run before ANN search. pgvector would work for smaller scale; Qdrant matches the retrieval + RBAC filter pattern we need at growth.

---

## 3. Authentication & authorization

### Why centralize JWT handling in `core/security/dependency.py`?

Every protected route shares one claim contract (`sub`, `wid`, `role`, `typ`, `jti`) and one revocation path (access blacklist via `get_token_store()`). Routers cannot drift to different validation rules or skip blacklist checks.

### What claims does the JWT carry?

| Claim | Meaning |
|-------|---------|
| `sub` | User ID |
| `wid` | Workspace ID (tenant) |
| `role` | `owner`, `admin`, or `member` |
| `jti` | Token ID for blacklist / refresh tracking |
| `typ` | `access` or `refresh` |

### How does refresh token rotation work?

On login/register, refresh `jti` is stored in Redis. On refresh, old token must exist → revoke old → issue new. On logout, access `jti` is blacklisted until `exp`. If Redis is off, auth works stateless without rotation guarantees.

### What is `RequestContext`?

A small immutable object: `user_id`, `workspace_id`, `role`. Built only from validated JWT in `get_current_context`. All tenant-scoped routes depend on it — **never** accept `workspace_id` from query/body on protected resources.

### What is the difference between `require_roles` and entity permission helpers?

- **`require_roles("owner", "admin")`** — coarse route gate (“can this role hit this endpoint?”).
- **`notes/permissions.py`, `files/permissions.py`** — per-resource rules using `created_by`, `is_private`, visibility.

Repositories enforce SQL scope; permission helpers enforce business rules; routers orchestrate.

### What are the note visibility rules?

| Role | Notes |
|------|-------|
| owner / admin | CRUD any note in workspace |
| member | CRUD own notes; **read** all public + own private |

Vector search mirrors this via `build_rbac_filter()` in Qdrant.

### What are the file visibility rules?

Owner/admin see all files. Members see non-private files + files they uploaded (`created_by`).

---

## 4. Database & multi-tenancy

### How is tenancy enforced in SQL?

Models use `WorkspaceTenantMixin` (`workspace_id` column). Repositories apply `tenant_filter(workspace_id)` or subclass `TenantRepository` so every query is workspace-scoped.

### Why does `TenantRepository` take `workspace_id` in the constructor?

Tenant scope becomes a construction-time guarantee: once built, the repository cannot query another workspace without a new instance. Matches JWT-derived `workspace_id` from `RequestContext`.

### Why `expire_on_commit=False` on the async sessionmaker?

After `commit()`, ORM instances remain usable for response DTOs without immediate refresh — typical FastAPI “commit then return” flow. Trade-off: know when you need explicit `refresh()`.

### How does a request’s DB session relate to concurrency?

Each request gets its own `AsyncSession` from `get_session()`. Sessions are not shared across concurrent requests. Pool size and handler duration determine throughput.

### Why do workers use `AsyncSessionLocal` directly, not `get_session()`?

`get_session()` is a FastAPI generator dependency. Workers have no request scope — they open `async with AsyncSessionLocal() as db` per task.

### What AI-related tables exist in Postgres?

- **`ai_threads`**, **`ai_messages`** — product conversation UI (Slice 5).
- LangGraph **checkpoint tables** — created by `AsyncPostgresSaver.setup()` (execution state, separate from product messages).
- **`files`**: `extracted_text`, `summary`, `tags` (automation metadata).
- **`notes`**: `tags` (JSONB, auto-generated).

Vectors live in **Qdrant**, not Postgres.

### Why Alembic for every schema change?

Model columns without migrations break prod deploys. Rule: every new column → migration command before merge.

---

## 5. API design & request lifecycle

### What routers are registered in `main.py`?

Health, auth, files, notebooks, notes, workspaces, membership, AI search/chat/threads/agent. Global middleware: `ProxyHeadersMiddleware`, optional Redis rate limit.

### What happens in application lifespan startup?

`setup_logging()` → ARQ pool on `app.state` → Qdrant collection bootstrap (**non-fatal** if down) → LangGraph checkpointer init (**non-fatal** if down). Core CRUD works even when soft AI deps fail.

### Why never accept `workspace_id` from the client on AI routes?

Tenant isolation is a security property. `workspace_id` always comes from JWT `wid`. Accepting it from query/body would allow cross-tenant retrieval — the most common RAG security bug in demos.

### Why return 404 (not 403) for cross-workspace thread access?

Avoid leaking whether a resource ID exists in another tenant. Same pattern for thread reuse on chat with wrong `thread_id`.

### What does `GET /health` check?

Postgres `SELECT 1` + Redis `PING` when configured. **200** ok / **503** degraded. Qdrant is **not** in the hard deploy gate — AI degrades separately (`GET /health/ai` optional).

### Why Pydantic schemas on every route?

Request validation, OpenAPI docs, and clear contracts for frontend. Domain events use frozen Pydantic models in `shared/events/definitions.py`.

---

## 6. Storage & files

### Why a `StorageBackend` protocol and `get_storage()` factory?

Upload/download/delete differ across local disk, MinIO, and R2. Routers stay backend-agnostic; `STORAGE_BACKEND` selects implementation. Easy to mock in tests.

### Where do file bytes vs metadata live?

- **Bytes** — object storage (`storage_key` in S3/R2/local path).
- **Metadata** — PostgreSQL (`mime_type`, `extracted_text`, `summary`, `tags`).

### Why do api and worker share a local volume in dev Compose?

With `STORAGE_BACKEND=local`, the worker must read uploaded bytes for extraction. Prod uses R2 — no shared volume; worker downloads via `get_storage().download(storage_key)`.

### What happens on file upload (AI enabled)?

Router saves metadata + bytes → commits → `emit_event(FileUploadedEvent)`. Worker: download → `FileParsingEngine.extract_text()` (PDF/DOCX/HTML) → save `extracted_text` → fan-out `index_file_chunks` + `generate_file_metadata`.

### Why validate MIME type and size in `core/storage/utils.py`?

Reject bad uploads before storage write. Sniff MIME, enforce extension allowlist and max size — defense in depth, not only client-side checks.

---

## 7. Redis, caching & rate limits

### Why is Redis optional if refresh rotation and cache assume it?

App boots and serves CRUD without Redis: token store and cache degrade to no-op / always-miss. When Redis is on: refresh tracking, logout blacklist, cache-aside, app rate limits.

### Why fail-open on app rate limits when Redis is down?

Blocking all traffic when Redis is down is worse than temporary abuse risk for small deployments and pytest. Nginx `limit_req` still applies on port 80 in Compose.

### Why fixed-window counters for rate limits?

Simple `INCR` + `EXPIRE` per time bucket — few round-trips, easy to explain (“100/min global, 5/min login”). Sliding windows cost more Redis ops for marginal benefit here.

### Why both Nginx and FastAPI rate limits?

Nginx protects CPU/connections per IP before Python. App layer keys by **`user_id`** when JWT present, else IP — important behind NATs and for authenticated abuse.

### Why generation counters for cache invalidation?

`INCR app:cache:gen:notes:{workspace_id}` bumps a generation embedded in cache keys. No `SCAN` or wildcard delete. Miss after bump; TTL bounds staleness if bump fails.

### Why notes list cache uses `staff` vs `u{user_id}` key variant?

Owner/admin see a different list than members (RBAC). Key encodes viewer class so a staff-shaped list is never served to a member.

### Why `get_optional_current_context` for rate limiting?

Public routes have no token. Optional decode keys authenticated traffic by user; anonymous traffic falls back to IP after `ProxyHeadersMiddleware`.

### How does embedding cache work?

Redis key `embed:v1:{sha256(text)}` — same chunk text = cache hit = skip provider API call. Cost control on re-index and duplicate content.

---

## 8. Workers, events & background jobs

### What worker tasks exist?

| Task | Trigger |
|------|---------|
| `embed_note_task` | Direct enqueue from notes router (Slice 1) |
| `handle_file_uploaded` | `FileUploadedEvent` |
| `handle_note_created` | `NoteCreatedEvent` |
| `handle_note_updated` | `NoteUpdatedEvent` |
| `handle_file_deleted` | `FileDeletedEvent` |
| Fan-out: `index_file_chunks`, `generate_file_metadata`, `generate_note_tags` | From automation handlers |

### Why `emit_event()` never raises?

Domain writes must not fail because Redis or ARQ hiccuped. Log and drop — ops monitors logs. HTTP already returned success after DB commit.

### Why both direct `embed_note_task` enqueue and `NoteCreatedEvent`?

Slice 1 predates the event bus. Slice 7 **adds** `emit_event` alongside embed enqueue — no breaking change. File upload uses events only (no direct embed in router).

### Why fan-out from worker via `ctx["arq_pool"]`?

One uploaded file triggers extraction, then parallel indexing + metadata LLM calls. Pool created once at worker startup, reused across tasks.

### Why run `FileParsingEngine` in a thread executor?

PDF/DOCX parsing is CPU-bound and sync. Executor keeps the async worker event loop responsive.

### What happens on worker LLM failure?

Transient errors in automation → re-raise → ARQ retries. `AutomationDecisionEngine` on LLM failure → fail-safe block (`is_destructive=True`). Agent route maps exhausted retries to **503** `"LLM temporarily unavailable"`.

---

## 9. Embeddings & indexing

### Walk through the embed pipeline for a note.

`notes/router` commits → enqueues `IndexingRequest` → worker `embed_note_task` → delete old vectors for note (if Qdrant on) → `EmbeddingPipeline.process_note` → chunk → cache lookup per chunk → LiteLLM `aembedding` on miss → `NoteVectorIndexer` upsert to `notes_chunks`.

### Why deterministic `chunk_id`?

`uuid5(NAMESPACE_URL, f"{note_id}:{index}")`. Re-indexing same note overwrites same Qdrant point IDs — idempotent, no duplicate vectors on retry.

### Why prepend title as H1 to chunk text?

Retrieved chunks carry note context even when the match is a body paragraph — better answers and citations.

### Why `RecursiveCharacterTextSplitter`?

Respects paragraph/sentence boundaries before character splits — more coherent chunks than fixed windows for markdown-ish notes.

### What is stored in Qdrant payload?

`workspace_id`, `note_id`, `chunk_id`, `chunk_index`, `text`/`chunk_text`, `title`, `created_by`, `visibility`, `is_private`, token/char offsets. **Always** filter on `workspace_id` + RBAC fields.

### Why separate collections `notes_chunks` and `files_chunks`?

Different ingestion paths and payloads; avoids mixed delete/reindex logic. Never upsert files into notes collection.

### What if `QDRANT_URL` is unset?

Embeddings still run; `qdrant_indexed=false`. Search and RAG return 503 when `qdrant_enabled` is false. Lets dev without Qdrant.

---

## 10. Vector search & RBAC retrieval

### Why `WorkspaceVectorSearch` as the only Qdrant search interface?

Routers and services never touch `AsyncQdrantClient` directly. All searches inject `workspace_id` + RBAC filter server-side — one place to audit tenant safety.

### How does `build_rbac_filter` work?

| Role | Qdrant filter |
|------|----------------|
| owner / admin | `must`: `workspace_id` |
| member | `must`: `workspace_id` AND (`visibility=public` OR `created_by=user_id`) |

Mirrors `notes/permissions.py` exactly. `workspace_id` is always `must` — never optional.

### Why cosine score threshold ~0.4?

Filters low-relevance noise before RAG context assembly. Tune with `GET /ai/test-search` and golden evals — not a universal constant.

### Why payload indexes on Qdrant fields?

Without indexes on `workspace_id`, `note_id`, etc., filters devolve into full scans. Created at startup in `ensure_notes_collection()` / `ensure_files_collection()`.

### How do you prevent cross-tenant leakage in retrieval?

1. `workspace_id` only from JWT, frozen before service call.  
2. `must` filter on every query.  
3. RBAC filter for members.  
4. Eval case: member B cannot retrieve member A’s private note.

---

## 11. RAG chat

### What is the RAG pipeline in `RagService.answer()`?

1. Retrieve chunks (`WorkspaceVectorSearch`)  
2. Fit to `TOKEN_BUDGET_PER_REQUEST` (char budget)  
3. Load thread history if `thread_id` + DB session provided  
4. Build prompt from `ai/prompts/rag.py`  
5. LiteLLM completion → structured `RAGAnswer`  
6. **Ground citations** against retrieved set — never trust LLM-hallucinated chunk IDs  
7. Persist turn via `ThreadService` if threaded  

### Why does `RagService` take plain strings, not `RequestContext`?

Agent tools (Slice 6) call the same service outside HTTP. `(workspace_id, user_id, role)` works from routes **and** LangGraph tools without refactoring.

### Why structured output for RAG answers?

`RAGAnswer` Pydantic model — reliable parsing, testable, no regex on free text. Same pattern for automation via `acompletion_structured`.

### Why citations from top retrieved chunks, not from the token stream?

LLMs hallucinate sources in streaming text. Citations are computed from retrieval results and sent in SSE **`metadata`** event after stream completes.

### Fast RAG vs agent — when to use which?

| Path | Use when |
|------|----------|
| `/ai/chat` | Single question, low latency, no tool mutations |
| `/ai/agent` | Multi-step: search → reason → create/update note |

Coexist by design — don’t force all traffic through the agent loop.

---

## 12. Streaming (SSE)

### Why freeze `workspace_id`, `user_id`, `role` before opening the SSE generator?

`RequestContext` from FastAPI `Depends` may not be safe to reference inside a long-running async generator. Primitives captured before `StreamingResponse` — tenant context cannot be lost or mutated mid-stream.

### What SSE events does chat stream emit?

`token` events (text deltas) → final `metadata` (citations, `thread_id`, chunk counts) → `[DONE]`. Headers: `Cache-Control: no-cache`, `X-Accel-Buffering: no` for Nginx.

### What about agent streaming?

`graph.astream_events` → `token`, `tool_start`, `tool_end`, `done`, `[DONE]`. Frontend can show tool progress separately from answer tokens.

---

## 13. Threads & conversation memory

### What is stored in `ai_threads` / `ai_messages`?

Product layer: thread title, workspace, creator, messages with role/content/citations. Used for UI list and history — plain SQL with workspace filter.

### How is history injected into RAG?

`ContextBuilder` loads last `AI_THREAD_MESSAGE_LIMIT` (default 20) messages, respects token budget with retrieved chunks. Cross-workspace `thread_id` → **400** on chat, **404** on thread routes.

### What is the relationship between product threads and LangGraph checkpointer?

Linked by **`thread_id` string only**. Product tables = what user sees; checkpointer = graph execution state for agent loops. Two concerns, one ID bridge.

---

## 14. LangGraph agent

### What is the agent graph topology?

`START → agent → (tools | end) → tools → agent → ... → END`. Conditional edge on tool calls. `AGENT_MAX_ITERATIONS` caps loops.

### What tools exist?

| Tool | Implementation |
|------|----------------|
| `search_notes` | `RagService.answer()` |
| `create_note` | `NoteService.create_note()` |
| `update_note` | `NoteService.update_note()` |
| `summarize_workspace` | `RagService.answer(..., retrieval_limit=12)` |

All via **service layer** — `db_session_var` set in tool node before DB mutations.

### Why LiteLLM `tools=` instead of LangChain `bind_tools()`?

LiteLLM is not a LangChain LLM. OpenAI-style function defs passed to `acompletion_with_retry`.

### Why separate Postgres pool for checkpointer (psycopg3)?

LangGraph `AsyncPostgresSaver` uses psycopg3; SQLAlchemy async pool is separate. Avoids mixing connection semantics.

### What happens when LLM retries are exhausted on the agent route?

**503** with `"LLM temporarily unavailable; retry shortly"` — not silent empty response or opaque 500.

---

## 15. Automation & governance

### What runs automatically without user action?

- Note create → embed + auto-tags  
- File upload → extract text → index vectors + summary/tags  

### When does `AutomationDecisionEngine` run?

Only for **destructive or ambiguous** AI-initiated actions (auto-delete duplicates, merge, archive, external notify). **Not** for additive tasks (tags, summary, index upsert).

### What is the governance decision rule?

`should_execute_immediately` → `True` **only** if `confidence >= 0.95` **and** `is_destructive=False`. Else log `[AUTOMATION_GOVERNANCE_BLOCK]` and hold for human review (approval queue = future slice).

### Why fail-safe on governance LLM failure?

If the evaluator LLM fails, treat as `is_destructive=True`, `confidence=0.0` — block rather than auto-execute.

---

## 16. LLM layer & providers

### What is in `shared/llm/`?

| Module | Role |
|--------|------|
| `retry.py` | `acompletion_with_retry` — tenacity, retryable vs fatal exceptions |
| `structured.py` | `acompletion_structured` — JSON salvage + Pydantic validation |
| `env.py` | Push provider keys into environment for LiteLLM |

Import law: no FastAPI, SQLAlchemy, or domain repos in `shared/llm/`.

### What models does the project use by default?

- Embeddings: `gemini/gemini-embedding-2` (3072 dim)  
- Chat/agent: configurable via `LLM_MODEL` (e.g. NVIDIA NIM Mistral)  
- `ai_enabled` if any of OpenAI, Gemini, or NVIDIA NIM keys set  

### Why tenacity retries with exponential backoff?

Provider rate limits and transient outages are normal. `LLM_MAX_RETRIES`, min/max wait configured in settings. Fatal auth errors fail fast with log marker `[AUTOMATION_LLM_AUTH_FAIL]`.

### Why not merge embedding retry into `shared/llm/`?

Embedding retry lives in `ai/embeddings/litellm_provider.py` — different batching semantics; kept separate intentionally (Slice 7.5).

---

## 17. Observability

### What tracing exists?

`observability.tracing` — `rag_trace` / `rag_span` for retrieval, context build, LLM generation. Langfuse when `LANGFUSE_*` keys set. **No** Langfuse SDK inside `src/ai/*` — import law.

### What metrics exist?

`GET /metrics` — Prometheus `dashnote_api_*` via instrumentator. Compose includes Prometheus + Grafana folder **DashNote**.

### What log markers should ops search for?

`[AUTOMATION_GOVERNANCE_BLOCK]`, `[AUTOMATION_LLM_RETRY_EXHAUSTED]`, `[AUTOMATION_LLM_PARSE_FAIL]`, `[AUTOMATION_LLM_AUTH_FAIL]`.

### Why JSON structured logging?

Machine-parseable logs for grep/Loki; `request_id`, `workspace_id` in `extra` where applicable.

---

## 18. Deployment & dependency tiers

### What are hard vs soft dependencies?

| Tier | Services | Gate |
|------|----------|------|
| **Hard** | Postgres, Redis | `GET /health` must 200 |
| **Soft** | Qdrant, LLM providers | App boots; AI routes 503 or degrade |
| **Optional** | Langfuse, Grafana remote_write | Never block startup |

### Why soft Qdrant boot (7P.3)?

Collection init in try/except at API/worker startup. Log ERROR, continue — notes/files CRUD work; search/RAG down until Qdrant returns.

### Dev vs prod Compose difference?

- **`docker-compose.yml`** — full local stack (db, redis, qdrant, worker, nginx).  
- **`docker-compose.prod.yml`** — api, worker, nginx, migrate only; hosted Postgres/Redis/Qdrant/R2 from `.env`.

### Why one Dockerfile for api, worker, migrate?

Same Python deps and `src/` tree; only `command` differs. Simpler CI and image promotion.

---

## 19. Tradeoffs & “why not X?”

### Why not LangGraph for simple RAG chat?

RAG is linear: retrieve → prompt → answer. LangGraph adds state machine complexity without benefit until **tool loops** are required (Slice 6).

### Why not fine-tune a model?

Hosted APIs + good retrieval + prompts solve most note Q&A. Fine-tuning is cost, data pipeline, and eval overhead — deferred unless base model consistently fails on domain.

### Why not Neo4j / GraphRAG yet?

Optional Slice 8 — only if users need relationship traversal and vector search is insufficient. Most portfolios over-invest here too early.

### Why not parse citations from streamed tokens?

Unreliable — models invent `[1]` markers. Metadata event from retrieval set is the source of truth.

### Why not hybrid BM25 + vector yet?

Planned in Slice 7R / ship-plan. Current search is dense semantic; hybrid improves exact-keyword recall — common interview “next step.”

### Why not unstructured.io for file parsing?

`pypdf` + `python-docx` + `beautifulsoup4` cover MVP formats without heavy deps — 8GB-friendly.

### Why score threshold instead of reranker first?

Rerankers add latency and cost. Threshold + chunk tuning is the first lever; reranker is Phase 2 optimization.

### Why 503 for LLM down instead of cached fallback?

Wrong answers from stale or generic fallback damage trust more than a clear “try again” error.

---

## 20. Extending the codebase

### When adding a new tenant-scoped module, what is the minimum contract?

`workspace_id` on model (`WorkspaceTenantMixin`), `tenant_filter` in repository, `RequestContext` in router, permission helper if rules exceed roles, register router in `main.py`, tests for tenant isolation.

### When adding a new AI feature, what must you check?

- Import law (`ai.md`, `rules.md`)  
- `workspace_id` from JWT only  
- Qdrant writes only via indexer classes in worker  
- Qdrant reads only via `WorkspaceVectorSearch`  
- Prompts only in `ai/prompts/`  
- Structured outputs for machine-parseable LLM results  
- Gate script or pytest before merge  

### When adding a new agent tool?

Pydantic `args_schema`, call **service** not repository, respect RBAC inside service, add to `get_note_tools()`, test with `e2e_agent_test.py` scenario.

### When adding a new domain event?

Extend payload in `shared/events/definitions.py` only (frozen models), map in `shared/events/bus.py`, handler in `worker/automation/tasks.py`, emit after DB commit in router.

---

## Quick interview pitches

### 2-minute project pitch

“I built a multi-tenant notes API where JWT workspace scope applies to both SQL and Qdrant retrieval. Notes and files are chunked and embedded in background workers; RAG chat streams answers with citations grounded in retrieval, not the LLM stream. A LangGraph agent can search, summarize, and create notes through the same service layer. Automation tags and summarizes uploads; destructive actions go through a governance engine that blocks unless confidence is very high. Everything is designed for prod: soft deps, rate limits, tracing, and explicit architecture laws.”

### Three tradeoffs to defend

1. **Chunk size (~1000 chars, overlap 150)** — balance coherence vs granularity; tune with evals not guesses.  
2. **Fast RAG vs agent** — latency and cost for Q&A vs multi-step mutations.  
3. **Fail-open rate limits without Redis** — availability over strict abuse prevention at small scale; Nginx still protects edge.

### One failure story (template)

“Early on, citations could include chunk IDs the model invented. We fixed it by grounding citations only against the retrieved chunk set in `RagService` and sending citations in the SSE metadata event after streaming — never parsing the token stream.”

---

## 21. Counter-questions — interviewer pushback

Real follow-ups when you explain DashNote. Interviewers probe tradeoffs, failure modes, and whether you understand alternatives — not just happy-path architecture.

---

### System & architecture

**“Isn’t this over-engineered for a notes app? Why not just call OpenAI with the note text?”**

At small scale, yes — paste into ChatGPT works. We built for **multi-tenant RBAC**, background indexing, file uploads, and agent mutations. Passing full workspace text per request doesn’t scale (token cost, latency, privacy). Retrieval + tenant filters is the minimum for a real product, not a demo.

**“You have both RAG chat and an agent. Isn’t that redundant?”**

Different cost/latency profiles. Chat is one retrieve + one LLM call — good for 80% of Q&A. Agent is 3–10+ LLM calls with tools — only when the user needs actions (create note, multi-step summarize). Forcing everything through the agent would 3× cost and latency for simple questions.

**“Why so many import laws and slices? Sounds like bureaucracy.”**

They prevent the bugs that kill AI prod: cross-tenant retrieval, tools bypassing RBAC, Langfuse in business logic. Slices let us ship embed → chat → agent incrementally with gates. Bureaucracy for a solo project; **risk control** for multi-tenant SaaS.

**“Would you use the same stack if you started again today?”**

Yes on: FastAPI, workers, Qdrant, LiteLLM, tenant-scoped retrieval. Maybe simplify: pgvector for v1 if <100k chunks. I’d still separate `ai/` from HTTP and still add evals earlier — that’s what I’d change, not the core stack.

---

### Auth, tenancy & security

**“JWT with workspace in the token — what if a user belongs to multiple workspaces?”**

Today login picks **first membership** as default `wid`. Switching workspace needs a new token (future: `POST /auth/switch-workspace`). The important part: `wid` is **server-issued**, never client-supplied on data routes.

**“Why 404 instead of 403 on cross-tenant thread access?”**

403 confirms the resource exists but is forbidden — **information leak** across tenants. 404 is indistinguishable from “never existed” for an attacker guessing UUIDs.

**“Redis optional for auth — isn’t that insecure?”**

Without Redis: no refresh rotation blacklist, logout is client-side only. Acceptable for local dev and tests. **Production enables Redis** — refresh tracking and access `jti` blacklist are required for real sessions.

**“How do you know RBAC in Qdrant matches SQL?”**

`build_rbac_filter()` is documented to mirror `notes/permissions.py`. Same rules: owner/admin = workspace only; member = public OR own. We test with `tests/ai/test_rbac_search_filter.py` and tenant-isolation eval cases. Drift is a code-review + test obligation, not automatic.

**“What if someone patches the JWT `wid` claim?”**

Tokens are HMAC-signed with `JWT_SECRET`. Tampering fails verification in `get_current_context` before any handler runs. Never trust decoded claims without signature check.

---

### Database & storage

**“Why Postgres + Qdrant? Why not pgvector in one database?”**

Valid for MVP. We chose Qdrant for payload indexes on `workspace_id`, `visibility`, `created_by` — filter-before-search at scale. pgvector reduces ops complexity; Qdrant reduces retrieval tuning pain. Trade-off: two systems to operate.

**“`expire_on_commit=False` — couldn’t that return stale data?”**

Only within the same request after commit — we build the response from objects we just wrote. Cross-request staleness goes through cache with TTL + generation bump, or fresh DB read. We don’t rely on session state across requests.

**“Local shared volume for files in dev — how is that not broken in prod?”**

Dev convenience only. Prod uses R2/MinIO — worker calls `get_storage().download(storage_key)`. The shared volume is explicitly **not** in `docker-compose.prod.yml`.

**“What if extraction fails on a corrupted PDF?”**

Worker logs error; `extracted_text` may stay empty; indexing/metadata tasks skip or no-op. Upload still succeeds — user sees file metadata, AI features degrade for that file. We don’t fail the HTTP upload for parse errors.

---

### Redis, cache & rate limits

**“Fail-open rate limits — a attacker could DDoS you when Redis dies.”**

True at the app layer. Mitigation: Nginx `limit_req` on port 80, infra alerts on Redis, horizontal scale later. For a small VPS, **availability during Redis blip** beat locking out all users. Enterprise would use always-on Redis cluster + stricter policy.

**“Generation counters vs deleting cache keys — what if INCR fails?”**

Worst case: stale list until TTL expires (60s default). Bounded staleness, not permanent wrong data. Pub/sub invalidation can miss messages; generation bump is simpler and correct on success.

**“Embedding cache by text hash — what about semantically identical but differently worded chunks?”**

Cache is **exact-text** dedup — saves money on re-index of unchanged chunks, not semantic dedup. Near-duplicate notes still embed separately. Semantic dedup would be a different (harder) problem.

---

### Workers & events

**“`emit_event` swallows errors — couldn’t you lose automation silently?”**

Yes — by design so HTTP never rolls back after commit. Mitigation: structured logs on enqueue failure, metrics on worker queue depth, smoke tests that upload a file and assert `summary` within 60s. **At-least-once** job processing is ARQ’s job; emit failure is ops-visible.

**“Why ARQ and not Celery / Kafka?”**

ARQ is Redis-native, async-friendly, minimal config — matches our existing Redis. Kafka is overkill for event volume here. Celery is fine but heavier; ARQ fits one worker process + fan-out pattern.

**“Double enqueue on note create — embed task AND event. Isn’t that duplicate work?”**

Different jobs: `embed_note_task` indexes vectors; `handle_note_created` runs tagging. Could merge later; keeping Slice 1 path unchanged reduced regression risk when Slice 7 shipped.

**“What if the worker is 5 minutes behind?”**

User sees note immediately; search catches up async. Chat may not find new note until embed completes — acceptable UX with “indexing” indicator on frontend. Agent `create_note` returns after DB write; embed follows same path.

---

### Embeddings & retrieval

**“Chunk size 1000 — how did you pick that? What if it’s wrong?”**

Starting point from common RAG practice; tuned via `GET /ai/test-search` and planned golden evals (Slice 7R). Too large = irrelevant context; too small = fragmented answers. **I’d defend the process (eval-driven tuning), not the number as sacred.**

**“3072-dim embeddings — isn’t that expensive vs 1536 or smaller models?”**

Gemini embedding-2 quality/dimension trade-off. Cost is per token, not just dimension. Could switch model + re-index if cost dominates — dimension must match Qdrant collection config.

**“Cosine threshold 0.4 — arbitrary?”**

Yes — empirically tuned gate to drop noise before RAG. Should be validated on golden set per domain. Interview answer: “I’d plot score distribution on labeled queries and set threshold where precision/recall cross is acceptable.”

**“No hybrid search yet — wouldn’t you miss exact keyword matches?”**

Correct — known gap. “Project X-47B” might miss if embedding doesn’t align. Next step: Qdrant sparse/BM25 hybrid (Slice 7R). Honest answer beats pretending dense search is enough.

**“Deterministic chunk IDs — what if you change chunking algorithm?”**

All chunks get new IDs → full re-index for that note. Expected migration cost when `CHUNK_SIZE` changes. We have re-index script planned; not magic — **payload schema changes require re-index.**

---

### RAG & chat

**“How do you prevent hallucination?”**

We don’t eliminate it — we **ground**: retrieve first, instruct model to use context only, citations from retrieval set not LLM output, structured answer schema. Residual hallucination when context is insufficient — evals measure faithfulness.

**“What if retrieval returns wrong chunks but high scores?”**

Model may still hallucinate or mis-synthesize. Mitigations: score threshold, chunk tuning, hybrid search, reranker (future), eval suite. This is the #1 RAG problem — show you know retrieval quality matters more than prompt tweaking.

**“Char budget vs token budget — why chars?”**

Simpler approximation without tiktoken on every chunk in hot path. Slight inaccuracy vs true token count; `TOKEN_BUDGET_PER_REQUEST` is conservative. Production hardening could switch to tiktoken — trade simplicity now for precision later.

**“Why temperature 0?”**

Deterministic, reproducible answers for notes/Q&A. Creative writing would raise it. Easier to eval and debug.

**“Structured RAG output — doesn’t that add latency?”**

One JSON parse vs free text — negligible vs LLM time. Reliability gain for citations and tests is worth it.

---

### Streaming & threads

**“Why send citations only at the end? Users want sources while reading.”**

UX choice — frontend can show “searching…” then render citations when `metadata` arrives. Streaming citations from tokens was **rejected** because models fake them mid-stream. End metadata is trustworthy.

**“20 message thread limit — users with long conversations lose context.”**

Intentional cost/latency cap. Older messages drop from prompt; retrieval still pulls relevant notes from workspace. Full history in DB for UI scroll; not all in LLM context. Scale-up: summarization of older turns.

**“Two thread systems (SQL + checkpointer) — confusing?”**

Separation of concerns: product CRUD vs graph execution state. Alternative: one table — couples LangGraph internals to UI schema. `thread_id` bridge is explicit and documented.

---

### Agent & LangGraph

**“Agents are unreliable. Why expose one to users?”**

Guardrails: `AGENT_MAX_ITERATIONS`, tools only through services (RBAC), no destructive automation without governance, 503 on LLM failure. Agent is for **actions**, not default Q&A. We keep fast RAG for reliability-sensitive queries.

**“What if the agent calls `create_note` with wrong content?”**

User can edit/delete (RBAC). Future: confirmation step for mutations, tool policy per role. Agent mistakes are product risk — we don’t claim 100% correctness; we claim **auditable tool paths** through `NoteService`.

**“Why LangGraph and not a simple while-loop with tool calls?”**

Could do while-loop for v1. LangGraph gives checkpointing, `astream_events`, conditional routing, and a path to multi-agent later. Cost: dependency + learning curve. We introduced it only in Slice 6 when tool loops were real.

**“`db_session_var` in tools — thread-safe?”**

Set per tool-node invocation in the graph for that request’s async context. Not global across concurrent requests — each agent invocation sets it before tools run. Would use explicit session pass in a refactor if we hit context issues.

---

### Automation & LLM ops

**“Governance LLM to judge another LLM — turtles all the way down?”**

Only for **destructive** actions — rare path. Additive automation skips it. Evaluator uses structured output + fail-safe block. Human approval queue is the ultimate backstop (Slice 7A).

**“0.95 confidence threshold — arbitrary?”**

Conservative default — prefer blocking false positives over auto-deleting user data. Would calibrate on labeled automation decisions. Business rule, not model property.

**“LiteLLM as single point of failure?”**

Provider outages hit everyone. Mitigation: retries, multi-provider keys via LiteLLM routing (future), 503 to client, queue jobs for worker. Abstraction lets us swap models without rewriting `RagService`.

**“How do you control LLM cost per workspace?”**

Planned: `ai_usage` table (Slice 10). Today: Langfuse traces, rate limits, `TOKEN_BUDGET`, embedding cache. Per-workspace billing is on roadmap — honest if not shipped yet.

---

### Observability & production

**“Langfuse optional — how do you debug prod without it?”**

JSON logs with `workspace_id`, operation markers, Prometheus HTTP metrics. Langfuse is for trace detail and cost — recommended in prod, not hard dependency. Soft tier like Qdrant.

**“Qdrant not in `/health` — how do you know search is broken?”**

Optional `GET /health/ai`, smoke scripts post-deploy, user reports, Grafana/Langfuse retrieval span failures. Hard gate stays db+redis so deploy isn’t blocked by vector DB blip.

**“One VPS — what’s your scaling story?”**

Scale workers horizontally (`--scale worker=N`), move to Qdrant Cloud + hosted Postgres, add RAG response cache (Slice 11), model routing for cheap vs expensive paths. Not Kubernetes on day one — **thin compute, fat managed data plane**.

**“No evals in CI yet — how do you prevent RAG regressions?”**

Gap acknowledged — job-search baseline includes golden set + `run_eval.py`. Until then: manual smoke + unit tests on RBAC filter. Strong candidates admit what’s not done and what’s next.

---

### Behavioral / judgment

**“Tell me something you’d do differently.”**

Ship eval harness earlier (before agent). Finish prod deploy before more slices. Maybe pgvector for v0 if solo and no RBAC-in-vector requirement yet — though we’d still need tenant filters somewhere.

**“Biggest production risk in this system?”**

Cross-tenant retrieval bug — catastrophic. Second: silent worker failures (lost indexing). We mitigate with filter laws, tests, smoke scripts, and structured logs — not with hope.

**“How do you stay current when models change every month?”**

LiteLLM abstracts providers; prompts versioned in `ai/prompts/`; evals detect quality drift; don’t fine-tune unless retrieval is proven insufficient. Models are replaceable; **retrieval + tenancy + evals** are the durable engineering.

**“Why should we hire you over someone who used LangChain for a weekend?”**

I can walk through tenant-isolated retrieval, why citations come from metadata not streams, what happens when Redis or Qdrant is down, and how agent tools enforce RBAC through services. Weekend tutorials rarely touch multi-tenant prod failure modes.

---

### Rapid-fire counter round (30-second answers)

| They ask | You answer |
|----------|------------|
| pgvector or Qdrant? | Qdrant for payload-filtered ANN; pgvector if ops simplicity wins and scale is small. |
| LangChain or LiteLLM? | LiteLLM for provider calls; LangGraph only for agent graph — not full LangChain stack. |
| Sync or async embed on upload? | Async worker — API must not block on provider rate limits. |
| One collection or per-tenant? | Shared collections with `workspace_id` filter — ops simpler than 1000 collections. |
| OpenAI only? | Multi-provider via LiteLLM — avoid vendor lock-in for embeddings and chat. |
| Prompt in code or DB? | Code (`ai/prompts/`) — versioned in git, reviewed in PR, traced via metadata. |
| Fine-tune? | Last resort after retrieval + prompts + evals show gap. |
| RAG or long context? | RAG — workspace notes exceed any context window; retrieval is mandatory. |
| Agent for everything? | No — fast RAG path for Q&A; agent for mutations and multi-step. |
| How measure RAG quality? | Golden questions, recall@k, citation grounding, tenant isolation cases — not vibes. |

---

*Update this file when architecture decisions change. Cross-link new slices in `blueprint/total.md` and `blueprint/goal.md`.*
