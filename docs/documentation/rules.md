ARCHITECTURE LAW — DashNoteSystem. Enforce in ALL generated code.

CRITICAL FOR SLICE 7:
  shared/events/definitions.py defines EventType, BaseEvent, and event class shells.
  Sub-step 7.0 APPENDS payload fields to each event class — do not rename EventType
  values or BaseEvent. Import event classes from here only.
  shared/events/bus.py is NEW — contains only the emit_event() dispatcher.

EXISTING CODE THAT MUST NOT CHANGE:
  src/shared/events/definitions.py    ← extend payload fields in 7.0 only; no EventType renames
  src/ai/workflows/pipeline.py        ← reuse EmbeddingPipeline, never duplicate
  core/storage/client.py              ← use get_storage() for file downloads
  src/notes/router.py Slice 1 block   ← embed_note_task enqueue stays intact
                                         Slice 7 adds a SECOND enqueue alongside it

ARQ WORKER CONTEXT LAW:
  ctx["redis"] exists (set in worker startup from Slice 1)
  ctx["arq_pool"] does NOT exist by default
  To enqueue fan-out jobs from inside a worker task:
    from arq import create_pool
    from arq.connections import RedisSettings
    pool = await create_pool(RedisSettings.from_dsn(settings.effective_arq_redis_url))
    await pool.enqueue_job(...)
    await pool.close()
  OR: create arq_pool once in worker startup, store on ctx["arq_pool"]
  Use the startup pattern — create once, reuse across all tasks

STORAGE LAW:
  File binary download: use get_storage() from core.storage.client
  Never hardcode file paths or invent a new download mechanism
  Storage returns bytes via .download(storage_key) — File model field is storage_key, not storage_path

WORKER DB LAW:
  Routers use Depends(get_session). Workers use AsyncSessionLocal directly:
    from core.database.session import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        ...
  Never call get_session() inside worker tasks — it is a FastAPI generator dependency.

QDRANT WRITE LAW (files):
  Notes: NoteVectorIndexer → WorkspaceVectorIndex (notes_chunks) — existing Slice 2 path.
  Files: add FileVectorIndexer (mirror NoteVectorIndexer) targeting QDRANT_FILES_COLLECTION.
  Worker tasks must NOT call AsyncQdrantClient.upsert directly — same law as embed_note_task.

MIGRATION LAW:
  Every model column addition requires an Alembic migration
  Never add columns without the corresponding migration command

QDRANT COLLECTION LAW:
  Notes index to: settings.QDRANT_NOTES_COLLECTION ("notes_chunks")
  Files index to: settings.QDRANT_FILES_COLLECTION ("files_chunks")
  Never mix collections

GOVERNANCE LAW:
  AutomationDecision gate applies to: destructive, external, irreversible actions
  Auto-tagging and auto-summarizing are NON-destructive — skip governance check
  Governance check = extra LLM call = extra cost — use only where warranted

WORKER TASK LAW:
  All worker task functions: async def task_name(ctx: dict, ...) -> None
  Never raise unhandled exceptions — all tasks wrapped in try/except
  Log success AND failure with structured extra={} fields
  Fan-out pattern: one task does one job, enqueues next task on success

MODULE PATHS:
  Import as: from config import settings, get_settings
             from shared.events.definitions import NoteCreatedEvent, FileUploadedEvent
             from shared.events.bus import emit_event
             from core.storage.client import get_storage
             from ai.workflows.pipeline import EmbeddingPipeline
  NEVER as:  from src.config import ...

Acknowledge these laws before writing any code.