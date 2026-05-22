## DashNoteSystem AI (Part 1 — configuration & infrastructure)

This document describes **Slice 1** of the AI agent notes system: settings, environment variables, and Compose services only. No embedding code, no Qdrant client, and no ARQ task implementations yet. For the core API platform (auth, notes, files, Redis, Nginx), see `src/docs/system.md`.

### Goals of Part 1

- Centralize AI-related configuration in `Settings` (`src/config.py`, imported as `config.settings`).
- Provide a **kill-switch** (`ai_enabled`) so production can disable all LLM/embedding paths when `OPENAI_API_KEY` is unset.
- Run **Qdrant** as a local vector store container (dev); production can point `QDRANT_URL` at Qdrant Cloud (vars already in `.env`, client wiring in a later slice).
- Reserve an **ARQ worker** service in Compose (job code and `arq` package come in later slices).

### Configuration module

- **Module**: `src/config.py`
- **Instance**: `settings = Settings()` (loaded from `.env` via Pydantic Settings).

#### Provider & embeddings (append-only fields)

| Field | Default | Purpose |
|-------|---------|---------|
| `OPENAI_API_KEY` | `None` | LiteLLM / OpenAI; when empty, `ai_enabled` is `False` |
| `EMBEDDING_MODEL` | `openai/text-embedding-3-small` | Provider/model string for LiteLLM embeddings |
| `EMBEDDING_DIMENSION` | `1536` | Vector size (must match model) |
| `EMBEDDING_BATCH_SIZE` | `32` | Batch size for embedding API calls |
| `EMBEDDING_MAX_RETRIES` | `3` | Retry budget per batch |
| `EMBEDDING_CACHE_ENABLED` | `True` | Redis cache-aside for chunk vectors (later slices) |
| `EMBEDDING_CACHE_TTL` | `86400` | Cache TTL in seconds (24h) |

#### Chunking

| Field | Default | Purpose |
|-------|---------|---------|
| `CHUNK_SIZE` | `1000` | Target characters per chunk |
| `CHUNK_OVERLAP` | `150` | Overlap between consecutive chunks |
| `CHUNK_MIN_LENGTH` | `50` | Minimum chunk length to index |

**Validation**: `validate_ai_config` raises if `CHUNK_OVERLAP >= CHUNK_SIZE`.

#### ARQ worker

| Field | Default | Purpose |
|-------|---------|---------|
| `ARQ_REDIS_URL` | `""` | Dedicated Redis for ARQ; see `effective_arq_redis_url` |
| `WORKER_MAX_JOBS` | `5` | Concurrency cap (align with OpenAI TPM tier) |

#### Computed properties

- **`settings.ai_enabled`**: `bool(settings.OPENAI_API_KEY)` — global AI toggle.
- **`settings.effective_arq_redis_url`**: `ARQ_REDIS_URL` or `REDIS_URL` or `""`.

### Environment (`.env`)

Slice 1 **does not duplicate** variables that already exist. Your `.env` should already define (among others):

- `OPENAI_API_KEY`, `EMBEDDING_MODEL`, `EMBEDDING_DIMENSION`, `EMBEDDING_BATCH_SIZE`, `EMBEDDING_MAX_RETRIES`
- `EMBEDDING_CACHE_ENABLED`, `EMBEDDING_CACHE_TTL`
- `CHUNK_SIZE`, `CHUNK_OVERLAP`, `CHUNK_MIN_LENGTH`
- `ARQ_REDIS_URL`, `WORKER_MAX_JOBS`
- `QDRANT_URL`, `QDRANT_API_KEY`, collection names (used in later slices)

**Compose vs local**: use `ARQ_REDIS_URL=redis://redis:6379` inside Docker; `redis://localhost:6379` when running the API on the host.

Set `OPENAI_API_KEY` to a real key to turn on `ai_enabled` for later slices.

### Docker Compose (append-only services)

Existing services (`db`, `redis`, `nginx`, `migrate`, `api`) are unchanged.

#### `worker` (new)

- **Image**: same build context as `api` (`build: .`).
- **Command**: `python -m arq src.worker.main.WorkerSettings` (requires `arq` in `requirements/base.txt` in a later slice).
- **Env**: `env_file: .env`
- **Depends on**: `db`, `redis`
- **Scale**: `docker compose up --scale worker=3 -d`

#### `qdrant` (new)

- **Image**: `qdrant/qdrant:latest` (official image; no `qdrant-client` in the API image yet).
- **Port**: `6333:6333` (HTTP API + dashboard on host).
- **Volume**: `qdrant_data:/qdrant/storage`
- **Production**: prefer Qdrant Cloud via `QDRANT_URL` in `.env` instead of this container.

#### Volumes (append-only)

- `qdrant_data` — persistent Qdrant storage for dev.

### Dependency & import law (AI slices)

From `src/docs/rules.md` (summary):

- `src/shared/` — contracts only; no imports from `ai/`, `worker/`, or domain modules.
- `src/ai/` — may import `src.shared.*`, `config.settings`, `core.redis.*`, stdlib, and third-party packages added when code needs them.
- `src/worker/` — may import `src.ai.*` and `src.shared.*`; no FastAPI, no direct repository access.
- Domain modules (`notes`, `files`) call `src/ai/services/` only; routers append minimal enqueue after successful commits in later slices.

### What is explicitly out of scope for Part 1

- `qdrant-client` install or vector CRUD (Slice 2).
- ARQ job implementations beyond `embed_note_task` (Slice 1.3).
- Router enqueue blocks and embedding API calls.

---

## Sub-step 1.2A — Packages, indexing contracts, text chunker

### Requirements (append-only)

Added under `# --- AI Slice 1: Embedding pipeline ---` in `requirements.txt` and `requirements/base.txt` (Docker installs `base.txt`):

| Package | Purpose |
|---------|---------|
| `litellm` | Unified embedding/LLM provider calls (used in later slices) |
| `langchain-text-splitters` | `RecursiveCharacterTextSplitter` for note chunking |
| `arq` | Background worker queue (Compose `worker` service) |
| `tenacity` | Retries for LiteLLM embedding batches (1.2B) |
| `tiktoken` | Token counting helpers (later slices) |

**Not installed in 1.2A**: `qdrant-client` (Slice 2).

### Shared contracts — `src/shared/contracts/indexing.py`

Frozen Pydantic models for the API → worker indexing pipeline:

| Type | Role |
|------|------|
| `IndexingOperation` | `upsert` \| `delete` |
| `IndexingRequest` | Enqueued after note create/update (`request_id`, `note_id`, `workspace_id`, `title`, `content`, RBAC fields, `metadata`) |
| `DeletionRequest` | Enqueued after note delete |
| `IndexingResult` | Worker outcome (`chunks_indexed`, `latency_ms`, `error`) |

`IndexingRequest` validates non-empty `content` when `operation == upsert`.

Imports **only** stdlib + pydantic — no `src/ai/`, `src/worker/`, or domain modules.

### Text chunker — `src/ai/embeddings/chuncker.py`

| Type | Role |
|------|------|
| `ChunkResult` | One chunk: deterministic `chunk_id`, `note_id`, `chunk_index`, `text`, char span, `token_estimate` |
| `TextChunker` | Wraps `RecursiveCharacterTextSplitter` using `settings.CHUNK_SIZE`, `CHUNK_OVERLAP`, `CHUNK_MIN_LENGTH` |

**Behavior**

- Prepends `# {title}\n\n` to content so chunks retain note context.
- Skips chunks shorter than `CHUNK_MIN_LENGTH` (after strip).
- **Deterministic IDs**: `uuid.uuid5(NAMESPACE_URL, f"{note_id}:{index}")` — re-indexing the same note overwrites the same Qdrant point IDs.

**Import law**: stdlib, pydantic, `langchain_text_splitters`, `config.settings` only.

**Local validation**

```powershell
cd src
python -m ai.embeddings.chunker
```

**Docker** (after `docker compose build api`):

```powershell
docker compose exec -e PYTHONPATH=/app/src api python -m ai.embeddings.chunker
```

Do not use `python -m src.ai.embeddings.chunker` — the API image has `/app/src` on the path as `config`, `ai`, etc., not as a `src.` package prefix.

Expected: chunk count printed, `PASS: chunk IDs are deterministic`, `PASS: chunker validated successfully`.

**Dependencies**: `arq` requires `redis-py` **<6** (`redis>=5.2,<6` in `requirements/base.txt`). The Compose **Redis server** image can stay on 7.x; only the Python client pin changes.

### Settings helper

`get_settings()` in `src/config.py` — returns the `settings` singleton (same object as `from config import settings`). With `PYTHONPATH` / cwd set to `src` (Docker API image, local `cd src`), import as `from config import get_settings` or `from config import settings`.

---

## Sub-step 1.2B — LiteLLM embedding provider, base class, factory

### Module layout — `src/ai/embeddings/`

| File | Role |
|------|------|
| `base.py` | `BaseEmbeddingProvider` ABC, `EmbeddedChunk`, `EmbeddingProviderError`, `EmbeddingVector` alias |
| `litellm_provider.py` | `LiteLLMEmbeddingProvider` — async `litellm.aembedding()`, batching, tenacity retry |
| `factory.py` | Process singleton via `get_embedding_provider()` / `reset_embedding_provider()` (tests) |
| `chunker.py` | `TextChunker` / `ChunkResult` (1.2A) |
| `chuncker.py` | Deprecated re-export → use `chunker` |

**Pipeline / cache (1.2C)**: see below — implemented in `ai/workflows/pipeline.py` and `ai/services/cache.py`.

### `base.py` — contracts

| Type | Role |
|------|------|
| `EmbeddingVector` | `list[float]` — one embedding |
| `EmbeddingProviderError` | Provider failure; `provider`, `retryable` attributes |
| `EmbeddedChunk` | Frozen chunk + vector for indexing (pipeline / Qdrant in later slices) |
| `BaseEmbeddingProvider` | `embed_texts`, `get_model_name`, `get_dimension`; default `embed_single` |

**Import law**: stdlib, pydantic only.

### `litellm_provider.py` — LiteLLM

| Behavior | Detail |
|----------|--------|
| Settings | `EMBEDDING_MODEL`, `EMBEDDING_DIMENSION`, `EMBEDDING_BATCH_SIZE`, `EMBEDDING_MAX_RETRIES` via `get_settings()` |
| Batching | Splits input into batches of `EMBEDDING_BATCH_SIZE` |
| Empty texts | Stripped/empty strings filtered before API call (logged) |
| Retry | Tenacity exponential backoff on `RateLimitError`, `Timeout`, `ServiceUnavailableError`, `APIConnectionError`; attempts = `EMBEDDING_MAX_RETRIES` |
| Fail fast | `AuthenticationError`, `BadRequestError`, `NotFoundError` → `EmbeddingProviderError(retryable=False)` |
| Provider swap | Change `EMBEDDING_MODEL` only (e.g. `voyage/voyage-3`, `cohere/embed-english-v3.0`) |

**Import law**: stdlib, `litellm`, `tenacity`, `config.get_settings`, `ai.embeddings.base` — no FastAPI, SQLAlchemy, Qdrant.

### `factory.py` — singleton

- `get_embedding_provider()` — double-checked locking with `asyncio.Lock`; lazily constructs `LiteLLMEmbeddingProvider`.
- `reset_embedding_provider()` — clears singleton (tests).
- **No FastAPI** in this module (AI import law). Routes that need DI wrap `Depends` in the router layer when wired in a later slice.

### Data flow (1.2B only)

```mermaid
flowchart LR
  subgraph callers [Future callers]
    W[Worker 1.2D]
    P[Pipeline 1.2C]
  end
  F[factory.get_embedding_provider]
  L[LiteLLMEmbeddingProvider]
  LLM[litellm.aembedding]
  callers --> F --> L --> LLM
```

### Local validation

From `src/` (or Docker `exec` with `PYTHONPATH=/app/src`). Ensure required env vars exist (`DATABASE_URL`, `JWT_SECRET` at minimum — same as API boot).

```powershell
cd src
$env:DATABASE_URL="postgresql+asyncpg://dashuser:dashpass@127.0.0.1:5432/dashnotes"
$env:JWT_SECRET="pytest-jwt-secret"
python -m ai.embeddings.chunker
python -m ai.embeddings.litellm_provider
```

**Chunker**: `PASS: chunker validated successfully`.

**LiteLLM**: prints model/dimension; with `OPENAI_API_KEY` or `GEMINI_API_KEY` set, `PASS: got vector of dimension N`. Without a key, provider error is acceptable.

**Docker** (after rebuild):

```powershell
docker compose exec -e PYTHONPATH=/app/src api python -m ai.embeddings.litellm_provider
```

Do not use `python -m src.ai.embeddings.*` — the API image exposes `ai`, `config`, etc. under `/app/src`, not a `src.` package prefix.

---

## Sub-step 1.2C — Redis embedding cache + pipeline

### Module layout

| File | Role |
|------|------|
| `ai/services/cache.py` | `get_cached_vector`, `cache_vector` — Redis JSON cache keyed by `sha256(chunk_text)` |
| `ai/workflows/pipeline.py` | `EmbeddingPipeline`, `PipelineResult` — chunk → cache → embed → cache write → `EmbeddedChunk[]` |

**Out of scope**: Qdrant client (Slice 2). ARQ wiring is Sub-step 1.3.

### Redis cache — `ai/services/cache.py`

| Item | Detail |
|------|--------|
| Key | `embed:v1:{sha256(utf-8 chunk_text)}` |
| Value | JSON-serialized `list[float]` |
| TTL | `EMBEDDING_CACHE_TTL` (default 86400s) |
| Toggle | `EMBEDDING_CACHE_ENABLED` — when false, all cache ops no-op |
| Failure mode | Read/write errors logged; never raised (degrade to embed) |
| Sharing | Same text in different notes hits the same key (by design) |

**Import law**: stdlib, `redis.asyncio`, `config.get_settings`, `ai.embeddings.base`.

Callers inject a `redis.asyncio.Redis` client (e.g. from `core.redis.client.get_async_redis()` in the worker/API layer). The cache module does not import `core.*`.

### Pipeline — `ai/workflows/pipeline.py`

```
process_note(...)
  1. TextChunker.chunk_note(note_id, title, content) → ChunkResult[]
  2. For each chunk: get_cached_vector(text) if redis provided
  3. embed_texts(uncached texts) via BaseEmbeddingProvider
  4. cache_vector for each newly embedded chunk
  5. Build EmbeddedChunk[] (RBAC fields + char span metadata)
  → PipelineResult
```

| Field | Meaning |
|-------|---------|
| `chunks_processed` | Chunks after chunker |
| `chunks_from_cache` | Served from Redis without API call |
| `chunks_embedded` | New provider calls |
| `embedded_chunks` | Ready for Qdrant upsert (Slice 2) |

**Import law**: stdlib, pydantic, `ai.embeddings.*`, `ai.services.cache` — no FastAPI, SQLAlchemy, Qdrant, ARQ.

### Provider configuration (Gemini example)

| Env | Example |
|-----|---------|
| `GEMINI_API_KEY` | Google AI key for LiteLLM |
| `EMBEDDING_MODEL` | `gemini/gemini-embedding-2` |
| `EMBEDDING_DIMENSION` | `3072` (must match model output) |

`settings.ai_enabled` is true when `OPENAI_API_KEY` **or** `GEMINI_API_KEY` is set. Avoid duplicate empty `EMBEDDING_*=` lines in `.env` — they override defaults and break integer parsing.

### Local validation

From repository root (loads `.env` from cwd):

```powershell
cd g:\projects\dashnotesystemv1
$env:PYTHONPATH="src"
python -m ai.workflows.pipeline
```

Expected with a valid `GEMINI_API_KEY` (or `OPENAI_API_KEY`) and optional local Redis (`REDIS_URL`):

- `PASS: pipeline produces valid EmbeddedChunk objects`
- With Redis up and repeat run: `PASS: cache hits on repeat text`

**Docker**:

```powershell
docker compose exec -e PYTHONPATH=/app/src api python -m ai.workflows.pipeline
```

---

## Sub-step 1.3 — ARQ worker (`embed_note_task`)

### Module layout

| File | Role |
|------|------|
| `worker/ingestion/tasks.py` | `embed_note_task` — deserialise `IndexingRequest`, run `EmbeddingPipeline` |
| `worker/tasks.py` | Task registry (re-exports `embed_note_task`) |
| `worker/main.py` | `WorkerSettings` — ARQ entrypoint, startup Redis for embedding cache |

### `embed_note_task` flow

```
IndexingRequest (dict from ARQ)
  → ai_enabled? skip if false
  → DELETE? log + success (Qdrant delete in Slice 2)
  → get_embedding_provider() + EmbeddingPipeline(redis=ctx["redis"])
  → process_note(...) → log vectors (qdrant_indexed=false)
  → IndexingResult dict
```

| Log line | Meaning |
|----------|---------|
| `Embedding vectors produced (not written to Qdrant — Slice 2)` | Pipeline returned vectors; sample `chunk_id` + `vector_dim` |
| `embed_note_task complete` | `chunks_processed`, `chunks_from_cache`, `chunks_embedded`, `qdrant_indexed: false` |

**Import law**: stdlib, arq (via `worker/main` only), pydantic contracts, `config`, `ai.*`, `shared.*` — no FastAPI, SQLAlchemy, repositories, Qdrant.

### Compose worker

```text
command: python -m arq src.worker.main.WorkerSettings
depends_on: db, redis
env: ARQ_REDIS_URL=redis://redis:6379  (in Docker network)
```

`startup` attaches `ctx["redis"]` (`decode_responses=True`) for embedding cache; same Redis server as ARQ queue when `ARQ_REDIS_URL` falls back to `REDIS_URL`.

### Local validation

**Task only** (no ARQ process):

```powershell
cd g:\projects\dashnotesystemv1
$env:PYTHONPATH="src"
python -m worker.ingestion.tasks
```

Expected: `PASS: worker task embedded N chunks ... (qdrant_indexed=false)`.

**Full ARQ** (Redis required):

```powershell
docker compose up -d redis worker
docker compose logs -f worker
```

Enqueue from a one-off shell (repo root, `PYTHONPATH=src`):

```powershell
python -c "
import asyncio
from arq import create_pool
from arq.connections import RedisSettings
from config import get_settings
from shared.contracts.indexing import IndexingRequest, IndexingOperation

async def main():
    s = get_settings()
    pool = await create_pool(RedisSettings.from_dsn(s.effective_arq_redis_url))
    req = IndexingRequest(
        operation=IndexingOperation.UPSERT,
        note_id='arq-test-001',
        workspace_id='ws-001',
        created_by='user-001',
        is_private=False,
        title='ARQ Test',
        content='Paragraph one.\n\nParagraph two with enough content to chunk.',
    )
    job = await pool.enqueue_job('embed_note_task', request_dict=req.model_dump(mode='json'))
    print('enqueued', job.job_id)
    await pool.close()

asyncio.run(main())
"
```

Worker logs should show `embed_note_task complete` and `qdrant_indexed: false`.

## Sub-step 1.4 — API enqueue hooks (`notes/router.py`)

After a successful note create/update/delete (repository commit + cache bump), the notes router enqueues `embed_note_task` when `settings.ai_enabled` is true. Enqueue runs in `try/except` and never changes the HTTP response.

| Route | Operation | When skipped |
|-------|-----------|--------------|
| `POST /notes/` | `IndexingOperation.UPSERT` | `ai_enabled` false or enqueue failure (logged) |
| `PATCH /notes/{id}` | `UPSERT` (uses persisted `note.content`) | same |
| `DELETE /notes/{id}` | `IndexingOperation.DELETE` | same |

`src/main.py` lifespan creates `app.state.arq_pool` from `effective_arq_redis_url` at startup (or `None` when unset) and closes it on shutdown.

### Next slices (planned)

1. **Slice 2**: `qdrant-client`, upsert/delete vectors from `EmbeddedChunk`.

### Verify infrastructure (after `docker compose up -d`)

```powershell
docker compose up -d qdrant
curl.exe -sS http://127.0.0.1:6333/
# Expected: {"title":"qdrant - vector search engine",...}

docker compose exec api python -c "import sys; sys.path.insert(0, '/app/src'); from config import settings; print('ai_enabled:', settings.ai_enabled)"
# Expected: ai_enabled: False  (until OPENAI_API_KEY is set with a real key)

curl.exe -sS http://127.0.0.1/health
```

- **Settings import**: `from config import settings` or `from config import get_settings` (`src/config.py`). The API adds `/app/src` to `sys.path` at startup; one-off `exec` commands must do the same.
- **API health**: unchanged — `GET /health` via Nginx on port 80.
- **Qdrant**: `GET http://127.0.0.1:6333/` (root) or `/readyz` when the `qdrant` service is up.
- **Rebuild** after changing `src/config.py`: `docker compose up -d --build api`
- **Worker**: `docker compose logs worker` should show `ARQ worker started` and, after a job, `embed_note_task complete` with `qdrant_indexed: false`.

### Related docs

- `src/docs/system.md` — FastAPI app, tenancy, Redis cache, files, Compose stack for `api` / `migrate` / `nginx`.
- `src/docs/rules.md` — append-only law, dependency direction, package install discipline.
