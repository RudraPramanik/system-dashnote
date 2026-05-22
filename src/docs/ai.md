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

- Python modules under `src/ai/` (orchestration, LiteLLM, chunking).
- `qdrant-client` install or vector CRUD.
- ARQ job functions beyond `src/worker/tasks.py` stub (`functions = []`).
- Router changes, embedding pipelines, or Neo4j / LangSmith wiring.

### Next slices (planned)

1. **Part 2+**: `requirements` — `litellm`, `arq`, etc., only when importing code.
2. **Worker**: `WorkerSettings`, Redis pool, register tasks from `src/worker/tasks.py`.
3. **AI package**: chunking, embedding service, Qdrant indexer using shared contracts (`IndexingRequest`, domain events).
4. **API**: enqueue indexing after note/file commits (append-only router blocks).

### Verify infrastructure (after `docker compose up -d`)

```powershell
docker compose ps
curl.exe -sS http://127.0.0.1:6333/readyz
curl.exe -sS http://127.0.0.1/health
```

- **API health**: unchanged — `GET /health` via Nginx on port 80.
- **Qdrant**: `GET http://127.0.0.1:6333/readyz` should respond when the `qdrant` service is up.
- **Worker**: will stay unhealthy or restart until `arq` is installed and `src.worker.main.WorkerSettings` exists (later slice).

### Related docs

- `src/docs/system.md` — FastAPI app, tenancy, Redis cache, files, Compose stack for `api` / `migrate` / `nginx`.
- `src/docs/rules.md` — append-only law, dependency direction, package install discipline.
