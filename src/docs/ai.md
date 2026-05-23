## DashNoteSystem AI

Multi-tenant note embeddings: chunk → Redis cache → LiteLLM → **Qdrant** (`notes_chunks`, dim **3072**). API enqueues ARQ jobs; worker indexes vectors. Platform stack: `src/docs/system.md`. Import laws: `src/docs/rules.md`.

### Architecture laws (enforce in all AI code)

| Law | Rule |
|-----|------|
| Imports | `from config import settings` — never `from src.config` |
| `src/ai/*` | Only `config`, `ai.*`, `shared.*`, stdlib, third-party |
| `src/worker/*` | Only `config`, `ai.*`, `shared.*` — no raw Qdrant in tasks |
| Qdrant | `workspace_id` **must** filter on every query; inject from `RequestContext` / `IndexingRequest` only |
| Qdrant access | `WorkspaceVectorSearch` / `NoteVectorIndexer` only — never `AsyncQdrantClient` in routers or tasks |
| Routers | Append-only; test search at **`POST /ai/test-search`** |
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

**Validate (repo root, `PYTHONPATH=src`)**

```powershell
python -m ai.embeddings.chunker
python -m ai.workflows.pipeline
python -m worker.ingestion.tasks
```

---

## Slice 2 (current) — Qdrant indexing & test search

### Settings (append-only)

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
| `workspace_search.py` | **`WorkspaceVectorSearch`** — upsert, delete-by-note, search with mandatory `workspace_id` + member RBAC |
| `indexer.py` | `NoteVectorIndexer` — delete-then-upsert per note (worker-facing) |

**HTTP** (outside `ai/` import law): `ai_search/router.py` → `POST /ai/test-search` (JWT `workspace_id` only; embeds query, searches via `WorkspaceVectorSearch`).

### Worker flow (`embed_note_task`)

```
IndexingRequest
  → DELETE: NoteVectorIndexer.delete_note (if qdrant_enabled)
  → UPSERT: EmbeddingPipeline → NoteVectorIndexer.index_note_chunks
  → logs: qdrant_indexed, qdrant_points
```

When `QDRANT_URL` is unset, embeddings still run; `qdrant_indexed=false`.

### Payload (Qdrant)

`workspace_id`, `note_id`, `chunk_id`, `chunk_index`, `chunk_text`, `created_by`, `is_private`, `token_count`, plus pipeline metadata (`char_start`, `char_end`, …). Point id = UUID from `chunk_id`.

### Docker

`api` and `worker` get `QDRANT_URL=http://qdrant:6333`; worker `depends_on: qdrant`.

```powershell
docker compose up -d qdrant api worker
docker compose exec -e PYTHONPATH=/app/src api python -m ai.retrieval.indexer
docker compose logs --tail 30 worker   # expect qdrant_indexed=True after note create
```

### Local validation

```powershell
cd g:\projects\dashnotesystemv1
$env:PYTHONPATH="src"
$env:QDRANT_URL="http://127.0.0.1:6333"
python -m ai.retrieval.indexer
python -m worker.ingestion.tasks
```

**End-to-end (stack on :80)**

1. Register/login → create note with body text.
2. Wait for worker: `embed_note_task complete` with `qdrant_indexed=True`.
3. `POST /ai/test-search` with `{"query_text":"...", "limit":5}` and Bearer token.

```powershell
curl.exe -sS http://127.0.0.1:6333/readyz
curl.exe -sS http://127.0.0.1/health
```

### Dependencies

`qdrant-client ~= 1.16.0` under `# --- AI Slice 2: Qdrant vector retrieval ---` in `requirements/base.txt` and `requirements.txt`.

### Next slices (planned)

- Hybrid / rerank search, agent tools, file chunk collection (`QDRANT_FILES_COLLECTION`).

### Related docs

- `src/docs/system.md` — API, Compose, `/ai/test-search` registration
- `src/docs/rules.md` — dependency direction
