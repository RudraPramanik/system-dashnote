# Slice 7 — Event-Driven Automation
## Final Cursor Prompts (4 Sub-steps, Production-Grade, No Shortcuts)

> **Context carried from previous slices**
> - Slice 6 gate passed: `/ai/agent` invokes LangGraph with tool calling ✅
> - Event scaffolding exists: `src/shared/events/definitions.py` has `EventType`,
>   `BaseEvent`, and event class shells — **payload fields are still missing** (see 7.0)
> - Existing embedding pipeline: `src/ai/workflows/pipeline.py` → `EmbeddingPipeline`
> - Existing storage: `core/storage/client.py` → `get_storage()` → `download(key)` on `storage_key`
> - Existing Qdrant: notes use `QDRANT_NOTES_COLLECTION`; files need `QDRANT_FILES_COLLECTION` in `config.py`
> - Worker context: `ctx["redis"]` available (set in Slice 1 startup); `ctx["arq_pool"]` added in 7.1
> - API lifespan: `app.state.arq_pool` already exists (`main.py`) — routes can emit events today
> - Slice 1 already enqueues `embed_note_task` after note creation — Slice 7 adds a SECOND job
> - Import style: `from config import settings` (never `from src.config`)
> - Migration tool: Alembic — every model change needs a migration
> - ID types: `Note.id` is **int**; `File.id` is **UUID**; `workspace_id` is **int** everywhere in SQL

---

## Readiness gate (run before Sub-step 7.1)

| Prerequisite | Status in repo today | Action |
|--------------|---------------------|--------|
| Slices 1–6 (embed, Qdrant notes, RAG, threads, agent) | ✅ Implemented per `ai.md` / `lld.md` | None |
| `app.state.arq_pool` on API | ✅ `main.py` lifespan | None |
| `ctx["redis"]` on worker | ✅ `worker/main.py` startup | None |
| `shared/events/definitions.py` payload fields | ❌ Classes exist but have **no** `note_id`, `file_id`, `content`, etc. | **7.0** — extend definitions |
| `QDRANT_FILES_COLLECTION` in `config.py` | ❌ Only in `.env.example` | **7.0** — append to settings |
| `ensure_files_collection()` | ❌ Only `ensure_notes_collection()` exists | **7.0** — mirror in `collection.py` |
| `worker/automation/` | ❌ Not created yet | 7.1 |
| `files` model AI columns | ❌ No `extracted_text` / `summary` / `tags` | 7.2 |
| `notes.tags` column | ❌ Missing | 7.3 |
| Worker DB access pattern | ⚠️ `get_session()` is a FastAPI `yield` dep — **not** for workers | Use `AsyncSessionLocal()` (see 7.0) |

**Verdict:** Platform is ready for Slice 7 **after Sub-step 7.0**. Do not start 7.1 until event payloads and `QDRANT_FILES_COLLECTION` are in place — otherwise route emissions and worker handlers will fail at runtime.

---

## ARCHITECTURE LAW
### Paste as your FIRST message in every Cursor Composer session.

```
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
```

---

## Sub-step 7.0 — Prerequisites (gap fix from Slice 0 scaffolding)

**Goal:** Close gaps between the Slice 0 event contract (`total.md`) and the current
repo so Sub-steps 7.1+ can run without Pydantic validation errors or missing settings.

**Do this first.** Estimated: one focused session before 7.1.

### 7.0.1 — Extend `src/shared/events/definitions.py` (append payload fields only)

Current classes only carry `event_type` + `BaseEvent` fields. Append fields per event
(matching `docs/documentation/blueprint/total.md` Slice 0 spec):

```python
class NoteCreatedEvent(BaseEvent):
    event_type: EventType = EventType.NOTE_CREATED
    note_id: str
    created_by: str
    is_private: bool
    title: str
    content: str

class NoteUpdatedEvent(BaseEvent):
    event_type: EventType = EventType.NOTE_UPDATED
    note_id: str
    created_by: str
    is_private: bool
    title: str
    content: str

class NoteDeletedEvent(BaseEvent):
    event_type: EventType = EventType.NOTE_DELETED
    note_id: str

class FileUploadedEvent(BaseEvent):
    event_type: EventType = EventType.FILE_UPLOADED
    file_id: str
    uploaded_by: str
    file_name: str
    mime_type: str
    size_bytes: int
    is_private: bool

class FileDeletedEvent(BaseEvent):
    event_type: EventType = EventType.FILE_DELETED
    file_id: str
```

`model_dump(mode="json")` flattens these to top-level keys — worker tasks read
`event_data["file_id"]`, not `event_data["payload"]["file_id"]`.

### 7.0.2 — Append `QDRANT_FILES_COLLECTION` to `src/config.py`

```python
QDRANT_FILES_COLLECTION: str = "files_chunks"
```

Also append to `settings` / `.env.example` if not already loaded (`.env.example` has it).

### 7.0.3 — Add `ensure_files_collection()` in `src/ai/retrieval/collection.py`

Mirror `ensure_notes_collection()` but use `settings.QDRANT_FILES_COLLECTION`.
Call from **both** API lifespan (`main.py`) and worker startup (`worker/main.py`)
when `qdrant_enabled`.

### 7.0.4 — Add `FileVectorIndexer` in `src/ai/retrieval/indexer.py`

Mirror `NoteVectorIndexer` but upsert/delete against `QDRANT_FILES_COLLECTION`
(via a `WorkspaceFileVectorIndex` or a `collection_name` parameter on a shared base).
Sub-step 7.3 uses this instead of raw `AsyncQdrantClient.upsert` in worker tasks.

### 7.0.5 — Worker DB pattern (reference for all automation tasks)

```python
from core.database.session import AsyncSessionLocal

async with AsyncSessionLocal() as db:
    result = await db.execute(...)
    await db.commit()
```

**Validation:**
```powershell
python -c "from shared.events.definitions import NoteCreatedEvent; e=NoteCreatedEvent(workspace_id='1',note_id='42',created_by='1',is_private=False,title='t',content='c'); print(e.model_dump()['note_id'])"
# Expected: 42
```

**Commit:** `feat(slice7.0): event payloads, files Qdrant collection setting, FileVectorIndexer scaffold`

---

## Sub-step 7.1 — Event Bus + Worker Stubs + Route Emissions

**Goal:**
- `shared/events/bus.py` — dispatcher only, imports existing event definitions
- Worker startup wired with `arq_pool` on `ctx` for fan-out
- `handle_file_uploaded` and `handle_note_created` stub tasks registered
- `files/router.py` emits `FileUploadedEvent` after successful upload
- `notes/router.py` emits `NoteCreatedEvent` as second job alongside existing embed

**Files to open in Cursor:**
- `src/shared/events/definitions.py` (reference — read existing events)
- `src/shared/events/bus.py` (create empty)
- `src/worker/main.py` (reference — update startup + register tasks)
- `src/worker/automation/tasks.py` (create empty)
- `src/files/router.py` (reference — append only)
- `src/notes/router.py` (reference — append only, Slice 1 block untouched)

---

```
ROLE: You are a senior backend engineer on DashNoteSystem.

OBJECTIVE: Sub-step 7.1 — Create the event bus dispatcher, add arq_pool
to worker context, create stub automation tasks, and wire route emissions.

CONTEXT:
- shared/events/definitions.py already has: NoteCreatedEvent, FileUploadedEvent,
  EventType, BaseEvent. Read this file to understand the existing schema.
- Worker startup is in src/worker/main.py — it already sets ctx["redis"]
  from Slice 1. Add ctx["arq_pool"] in the same startup function.
- notes/router.py already enqueues embed_note_task (Slice 1) — ADD a second
  emit_event call alongside it, never remove or replace the Slice 1 block.
- files/router.py has POST /files/upload — emit FileUploadedEvent after
  successful file save to DB.

LAWS IN EFFECT:
- shared/events/definitions.py is NEVER modified — import from it
- shared/events/bus.py contains ONLY emit_event() — no event class definitions
- Append-only to router files
- Slice 1 embed_note_task enqueue in notes/router.py is NEVER touched
- Worker stubs log "received event" and return — no business logic yet

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 1 — src/shared/events/bus.py (CREATE NEW)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Create this file completely:

"""
Event bus dispatcher for DashNoteSystem.

emit_event() converts domain events into ARQ background jobs.
This module does NOT define event schemas — those live in
shared/events/definitions.py.

Task routing:
  FileUploadedEvent → handle_file_uploaded (worker/automation/tasks.py)
  NoteCreatedEvent  → handle_note_created  (worker/automation/tasks.py)

Failure handling:
  Redis unavailable → log error, return None
  Unknown event type → log warning, return None
  Never raise — never block the HTTP request lifecycle

IMPORT LAW: shared.events.definitions, stdlib, logging only.
No FastAPI. No SQLAlchemy. No AI imports.
"""
from __future__ import annotations

import logging
from typing import Any

from shared.events.definitions import BaseEvent, EventType

logger = logging.getLogger(__name__)

# Maps event type string to ARQ task function name
_TASK_MAP: dict[str, str] = {
    EventType.FILE_UPLOADED.value: "handle_file_uploaded",
    EventType.NOTE_CREATED.value: "handle_note_created",
    EventType.NOTE_UPDATED.value: "handle_note_updated",
    EventType.FILE_DELETED.value: "handle_file_deleted",
}


async def emit_event(
    event: BaseEvent,
    arq_pool: Any,
) -> bool:
    """
    Dispatch a domain event to the ARQ background worker queue.

    Args:
        event:    A frozen Pydantic BaseEvent subclass from shared/events/definitions.py
        arq_pool: app.state.arq_pool — the ARQ connection pool from lifespan

    Returns:
        True if enqueued successfully, False otherwise.
        Never raises — failure is logged and swallowed.

    Security:
        event.workspace_id comes from RequestContext (JWT) — already validated
        before reaching this function. No re-validation needed here.
    """
    if arq_pool is None:
        logger.warning(
            "emit_event called with no arq_pool — event dropped",
            extra={"event_type": event.event_type.value},
        )
        return False

    task_name = _TASK_MAP.get(event.event_type.value)
    if task_name is None:
        logger.warning(
            "No task registered for event type",
            extra={"event_type": event.event_type.value},
        )
        return False

    try:
        await arq_pool.enqueue_job(
            task_name,
            event_data=event.model_dump(mode="json"),
        )
        logger.info(
            "Event emitted",
            extra={
                "event_type": event.event_type.value,
                "event_id": event.event_id,
                "workspace_id": event.workspace_id,
                "task": task_name,
            },
        )
        return True
    except Exception as e:
        logger.error(
            "emit_event failed — event dropped, HTTP response unaffected",
            extra={
                "event_type": event.event_type.value,
                "error": str(e),
            },
        )
        return False

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 2 — src/worker/automation/__init__.py (CREATE NEW)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""Event-driven automation worker tasks — Slice 7."""

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 3 — src/worker/automation/tasks.py (CREATE NEW — stubs only)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Create this file with stub implementations only.
Full logic added in Sub-steps 7.2 and 7.3.

"""
Automation worker tasks for DashNoteSystem.

Task progression:
  handle_file_uploaded  → extract text → index vectors → generate metadata
  handle_note_created   → auto-tag note

Fan-out pattern:
  Each task does ONE job and enqueues the next task on success.
  This ensures retries are isolated — extract failure ≠ index failure.

Slice 7.1: stubs — log event receipt, no business logic yet
Slice 7.2: handle_file_uploaded gets extraction + DB persistence
Slice 7.3: fan-out to indexing + metadata generation + note tagging
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def handle_file_uploaded(ctx: dict, *, event_data: dict) -> None:
    """
    Triggered when a file is uploaded.
    Full implementation added in Sub-steps 7.2 and 7.3.
    """
    logger.info(
        "handle_file_uploaded received",
        extra={
            "event_type": event_data.get("event_type"),
            "file_id": event_data.get("file_id"),
            "workspace_id": event_data.get("workspace_id"),
        },
    )
    # TODO 7.2: extract text from file binary
    # TODO 7.3: fan-out to index_file_chunks + generate_file_metadata


async def handle_note_created(ctx: dict, *, event_data: dict) -> None:
    """
    Triggered when a note is created.
    Full implementation added in Sub-step 7.3.
    """
    logger.info(
        "handle_note_created received",
        extra={
            "event_type": event_data.get("event_type"),
            "note_id": event_data.get("note_id"),
            "workspace_id": event_data.get("workspace_id"),
        },
    )
    # TODO 7.3: auto-tag note


async def handle_note_updated(ctx: dict, *, event_data: dict) -> None:
    """Triggered when note content changes. Stub for future use."""
    logger.info("handle_note_updated received", extra={"event_data": event_data})


async def handle_file_deleted(ctx: dict, *, event_data: dict) -> None:
    """Triggered when a file is deleted. Stub for Qdrant vector cleanup."""
    logger.info("handle_file_deleted received", extra={"event_data": event_data})
    # TODO: delete file vectors from QDRANT_FILES_COLLECTION

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 4 — src/worker/main.py (update startup + register tasks)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Read src/worker/main.py carefully.

CHANGE 1 — Update startup() to add arq_pool to ctx:
Find the existing startup() function.
After the redis client is attached to ctx, append:

    # --- AI Slice 7: arq_pool for fan-out job enqueuing ---
    from arq import create_pool
    from arq.connections import RedisSettings
    ctx["arq_pool"] = await create_pool(
        RedisSettings.from_dsn(settings.effective_arq_redis_url)
    )
    logger.info("ARQ fan-out pool initialized in worker context")

CHANGE 2 — Update shutdown() to close the pool:
Find the existing shutdown() function.
Append:

    if "arq_pool" in ctx:
        await ctx["arq_pool"].close()

CHANGE 3 — Add automation tasks to WorkerSettings.functions:
Find the functions list in WorkerSettings.
Add the new tasks (import at top of file):

    from worker.automation.tasks import (
        handle_file_uploaded,
        handle_note_created,
        handle_note_updated,
        handle_file_deleted,
    )

    class WorkerSettings:
        functions = [
            embed_note_task,          # Slice 1 — already there
            handle_file_uploaded,     # Slice 7
            handle_note_created,      # Slice 7
            handle_note_updated,      # Slice 7
            handle_file_deleted,      # Slice 7
        ]

Show the exact lines changed with surrounding context.
Do not modify any Slice 1 functionality.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 5 — src/files/router.py (append only)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Read src/files/router.py carefully.
Find the POST /files/upload route.

CHANGE A — Add imports at top (if missing):
    import logging
    from fastapi import Request
    from config import settings

    logger = logging.getLogger(__name__)

CHANGE B — Add `request: Request` to the upload_file signature (alongside existing deps).

CHANGE C — After `record = await files_repo.create(...)` (repo already commits),
append BEFORE the return statement:

    # --- AI Slice 7: emit file uploaded event ---
    if settings.ai_enabled:
        try:
            from shared.events.definitions import FileUploadedEvent
            from shared.events.bus import emit_event
            await emit_event(
                FileUploadedEvent(
                    workspace_id=str(ctx.workspace_id),
                    file_id=str(record.id),
                    uploaded_by=str(ctx.user_id),
                    file_name=record.name,
                    mime_type=record.mime_type,
                    size_bytes=record.size_bytes,
                    is_private=record.is_private,
                ),
                request.app.state.arq_pool,
            )
        except Exception:
            # Never block file upload response for background failure
            logger.warning("FileUploadedEvent emission failed", extra={"file_id": str(record.id)})

IMPORTANT: Match the exact field names used in FileUploadedEvent
in shared/events/definitions.py. Read that file first to get them right.
Show the exact insertion location with 5 lines of surrounding context.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 6 — src/notes/router.py (append only — alongside Slice 1 block)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Read src/notes/router.py carefully.
Find the Slice 1 AI embedding block:
  # --- AI Slice 1: enqueue embedding job ---
  if settings.ai_enabled:
      try:
          await request.app.state.arq_pool.enqueue_job("embed_note_task", ...)

DO NOT TOUCH THIS BLOCK.
Append a SECOND block IMMEDIATELY AFTER the Slice 1 block's except clause:

    # --- AI Slice 7: emit note created event for automation ---
    if settings.ai_enabled:
        try:
            from shared.events.definitions import NoteCreatedEvent
            from shared.events.bus import emit_event
            await emit_event(
                NoteCreatedEvent(
                    workspace_id=str(ctx.workspace_id),
                    note_id=str(note.id),
                    created_by=str(ctx.user_id),
                    is_private=note.is_private,
                    title=note.title,
                    content=body.content,
                ),
                request.app.state.arq_pool,
            )
        except Exception:
            logger.warning("NoteCreatedEvent emission failed", extra={"note_id": str(note.id)})

IMPORTANT: The Slice 1 embed_note_task block is untouched.
Both blocks run independently after note creation.
Show the exact insertion with surrounding context.

OUTPUT FORMAT:
Task 1-3: complete new file content.
Task 4-6: exact lines changed with surrounding context (5 lines before/after).
Zero truncation. No placeholder comments.
```

**Validation:**
```powershell
docker compose up -d --build api worker

# Upload a file:
python -c "
import httpx, uuid
b='http://127.0.0.1'
e=f'test_{uuid.uuid4().hex[:8]}@test.com'
t=httpx.post(f'{b}/auth/register',json={'email':e,'password':'Test123!','workspace_name':'ws'},timeout=30).json()['access_token']
r=httpx.post(f'{b}/files/upload',headers={'Authorization':f'Bearer {t}'},files={'file':('test.txt',b'Hello this is test content for slice 7','text/plain')},data={'is_private':'false'},timeout=30)
print(r.status_code, r.json().get('id'))
"

# Check worker received event:
docker compose logs worker --tail 20
# Expected: "handle_file_uploaded received" with file_id and workspace_id

# Create a note and verify second event:
# POST /notes — check worker logs
# Expected: "handle_note_created received" alongside "embed_note_task complete"
# Both must appear — embed_note_task from Slice 1, handle_note_created from Slice 7
```

**Commit:**
```bash
git commit -am "feat(slice7.1): event bus, automation stubs, route emissions wired"
```

---

## Sub-step 7.2 — File Extraction + Storage + Migration

**Goal:**
- `pypdf`, `python-docx`, `beautifulsoup4` installed
- `FileParsingEngine` — isolated parser, handles PDF/DOCX/HTML/text
- `extracted_text` column added to `files/models.py` + Alembic migration
- `handle_file_uploaded` updated to download binary, extract, persist text

**Files to open in Cursor:**
- `requirements.txt`
- `src/shared/utils/parsers.py` (create empty)
- `src/files/models.py` (reference — check existing columns)
- `src/worker/automation/tasks.py` (update `handle_file_uploaded`)
- `core/storage/client.py` (reference — understand `get_storage()` interface)

---

```
ROLE: You are a senior backend engineer on DashNoteSystem.

OBJECTIVE: Sub-step 7.2 — Install text extraction packages, build the
FileParsingEngine utility, add extracted_text to files model, create
Alembic migration, and update handle_file_uploaded to extract and persist.

CONTEXT:
- Storage client: read core/storage/client.py to understand the StorageBackend
  interface. The download method returns bytes — verify the exact method name.
- Files model: read src/files/models.py to see existing columns.
  Add extracted_text as a new nullable Text column. Match existing style exactly.
- Alembic migration: required for every model change.
- FileParsingEngine: pure utility — no DB, no FastAPI, no async required.
  Parsing is CPU-bound — sync is fine. Run in executor if needed.
- handle_file_uploaded receives event_data dict from emit_event().
  Extract file_id and workspace_id from top-level event_data keys (flat model_dump from 7.0).

LAWS IN EFFECT:
- Use get_storage() from core.storage.client for file download — never hardcode paths
- FileParsingEngine lives in src/shared/utils/ — no AI imports, no FastAPI
- extracted_text column: nullable Text — never JSONB for raw text
- Alembic migration must be generated — not auto-migrate, not create_all()
- handle_file_uploaded: update the existing stub — do not create a new function
- All DB operations in handle_file_uploaded use get_session() pattern,
  open session, commit, close — never leave sessions open

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 1 — requirements.txt (append-only)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Read requirements.txt. Check which packages are already present.
Append ONLY what is missing under:

# --- AI Slice 7: File parsing ---
pypdf>=4.2.0            # PDF text extraction
python-docx>=1.1.2      # Word document extraction
beautifulsoup4>=4.12.3  # HTML/text extraction
lxml>=5.2.0             # HTML parser backend for beautifulsoup4

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 2 — src/shared/utils/__init__.py (CREATE IF MISSING)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""Shared utility modules for DashNoteSystem."""

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 3 — src/shared/utils/parsers.py (CREATE NEW)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Create this file completely:

"""
FileParsingEngine — text extraction from binary file content.

Supports: PDF, DOCX, HTML, plain text, markdown.
All parsing is synchronous and CPU-bound — run in executor for async callers.

Safety limits:
  MAX_CHARS = 500_000 — prevents OOM on large documents in worker container
  Truncation logged at WARNING — never silently dropped

IMPORT LAW: Only pypdf, docx, bs4, stdlib. No FastAPI, no SQLAlchemy,
no AI imports, no config. Pure utility module.
"""
from __future__ import annotations

import io
import logging
from typing import Final

logger = logging.getLogger(__name__)

MAX_CHARS: Final[int] = 500_000   # 500k chars max per document


class FileParsingEngine:
    """
    Extracts plain text from binary file content.

    Usage:
        text = FileParsingEngine.extract_text(file_bytes, "application/pdf")

    All methods are synchronous. For async callers:
        import asyncio, functools
        text = await asyncio.get_event_loop().run_in_executor(
            None, functools.partial(FileParsingEngine.extract_text, bytes_, mime_type)
        )
    """

    @classmethod
    def extract_text(cls, content_bytes: bytes, mime_type: str) -> str:
        """
        Extract plain text from binary content based on MIME type.

        Args:
            content_bytes: Raw file bytes from storage backend.
            mime_type:     MIME type string (e.g. "application/pdf").

        Returns:
            Extracted plain text string, truncated to MAX_CHARS.
            Empty string if extraction fails or content is binary.
        """
        if not content_bytes:
            return ""

        mime = mime_type.lower().strip()

        try:
            if mime == "application/pdf":
                return cls._parse_pdf(content_bytes)
            elif mime in (
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/msword",
            ):
                return cls._parse_docx(content_bytes)
            elif mime in ("text/html", "application/xhtml+xml"):
                return cls._parse_html(content_bytes)
            elif mime.startswith("text/"):
                return cls._parse_text(content_bytes)
            else:
                logger.info(
                    "Unsupported MIME type for text extraction",
                    extra={"mime_type": mime_type},
                )
                return ""
        except Exception as e:
            logger.error(
                "FileParsingEngine.extract_text failed",
                extra={"mime_type": mime_type, "error": str(e)},
            )
            return ""

    @classmethod
    def _parse_pdf(cls, content_bytes: bytes) -> str:
        """Extract text from PDF using pypdf."""
        import pypdf
        text_parts: list[str] = []
        chars = 0

        try:
            reader = pypdf.PdfReader(io.BytesIO(content_bytes))
            for page_num, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                if chars + len(page_text) > MAX_CHARS:
                    remaining = MAX_CHARS - chars
                    text_parts.append(page_text[:remaining])
                    logger.warning(
                        "PDF extraction truncated at MAX_CHARS",
                        extra={"pages_processed": page_num, "max_chars": MAX_CHARS},
                    )
                    break
                text_parts.append(page_text)
                chars += len(page_text)
        except Exception as e:
            logger.error("PDF parse error", extra={"error": str(e)})
            return ""

        return "\n\n".join(text_parts)

    @classmethod
    def _parse_docx(cls, content_bytes: bytes) -> str:
        """Extract text from Word document using python-docx."""
        import docx
        text_parts: list[str] = []
        chars = 0

        try:
            doc = docx.Document(io.BytesIO(content_bytes))
            for para in doc.paragraphs:
                if not para.text.strip():
                    continue
                if chars + len(para.text) > MAX_CHARS:
                    logger.warning("DOCX extraction truncated at MAX_CHARS")
                    break
                text_parts.append(para.text)
                chars += len(para.text)
        except Exception as e:
            logger.error("DOCX parse error", extra={"error": str(e)})
            return ""

        return "\n".join(text_parts)

    @classmethod
    def _parse_html(cls, content_bytes: bytes) -> str:
        """Extract readable text from HTML using BeautifulSoup."""
        from bs4 import BeautifulSoup

        try:
            soup = BeautifulSoup(content_bytes, "lxml")
            # Remove non-content elements
            for tag in soup(["script", "style", "head", "nav", "footer", "meta", "link"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)
            return text[:MAX_CHARS]
        except Exception as e:
            logger.error("HTML parse error", extra={"error": str(e)})
            return ""

    @classmethod
    def _parse_text(cls, content_bytes: bytes) -> str:
        """Decode plain text content."""
        for encoding in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                return content_bytes.decode(encoding)[:MAX_CHARS]
            except UnicodeDecodeError:
                continue
        return ""


if __name__ == "__main__":
    # Validation: python -m shared.utils.parsers
    test_cases = [
        (b"Hello world plain text", "text/plain", "Hello world plain text"),
        (b"<html><body><p>Hello</p><script>bad()</script></body></html>",
         "text/html", "Hello"),
    ]
    for content, mime, expected_contains in test_cases:
        result = FileParsingEngine.extract_text(content, mime)
        assert expected_contains in result, f"FAIL: expected '{expected_contains}' in result"
        print(f"PASS: {mime} extraction works")
    print("PASS: FileParsingEngine validated")

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 4 — src/files/models.py (append column only)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Read src/files/models.py carefully.
Check if extracted_text, summary, or tags columns already exist.
Add ONLY what is missing — append after the last existing column:

    # --- AI Slice 7: text extraction and metadata ---
    extracted_text: Mapped[str | None] = mapped_column(
        sa.Text,
        nullable=True,
        comment="Raw extracted text from file binary — populated by worker",
    )
    summary: Mapped[str | None] = mapped_column(
        sa.Text,
        nullable=True,
        comment="AI-generated summary — populated by generate_file_metadata worker",
    )
    tags: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=sa.text("'[]'::jsonb"),
        comment="AI-generated tags — populated by generate_file_metadata worker",
    )

Add JSONB to imports if not already present:
  from sqlalchemy.dialects.postgresql import JSONB

Show exact column positions and surrounding context.
If columns already exist, show me what exists and skip adding them.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 5 — Alembic migration instructions
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Show me the exact commands to generate and apply the migration:

  # Import new columns in alembic/env.py if not auto-detected:
  from files.models import File  # noqa: F401

  # Generate migration:
  docker compose run --rm migrate alembic revision \
    --autogenerate -m "add_extracted_text_summary_tags_to_files"

  # Apply:
  docker compose run --rm migrate alembic upgrade head

  # Verify:
  docker compose exec db psql -U dashuser -d dashnotes \
    -c "\d files" | grep -E "extracted_text|summary|tags"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 6 — Update handle_file_uploaded in tasks.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Read src/worker/automation/tasks.py.
Find the existing handle_file_uploaded stub.
REPLACE the stub body only (keep the function signature):

async def handle_file_uploaded(ctx: dict, *, event_data: dict) -> None:
    """
    Step 1 of file automation: extract text from uploaded file binary.

    Flow:
      1. Parse event_data to get file_id, workspace_id, mime_type
      2. Load file metadata from DB to get storage path
      3. Download file binary from storage backend
      4. Extract text using FileParsingEngine
      5. Persist extracted_text to files table
      6. Enqueue fan-out tasks (added in Sub-step 7.3)
    """
    import uuid
    import asyncio
    import functools

    from shared.events.definitions import FileUploadedEvent
    from shared.utils.parsers import FileParsingEngine
    from core.storage.client import get_storage
    from core.database.session import AsyncSessionLocal
    from config import get_settings
    import sqlalchemy as sa

    settings = get_settings()

    # Parse event — model_dump(mode="json") flattens payload fields to top level (7.0)
    try:
        file_id = event_data.get("file_id")
        workspace_id = event_data.get("workspace_id")
        mime_type = event_data.get("mime_type", "text/plain")

        if not file_id or not workspace_id:
            logger.error(
                "handle_file_uploaded: missing file_id or workspace_id",
                extra={"event_data_keys": list(event_data.keys())},
            )
            return
    except Exception as e:
        logger.error("handle_file_uploaded: event_data parse failed", extra={"error": str(e)})
        return

    # Step 1: Load file record to get storage_key
    file_record = None
    async with AsyncSessionLocal() as db:
        try:
            from files.models import File
            result = await db.execute(
                sa.select(File).where(
                    File.id == uuid.UUID(file_id),
                    File.workspace_id == int(workspace_id),
                )
            )
            file_record = result.scalar_one_or_none()
        except Exception as e:
            logger.error(
                "handle_file_uploaded: DB lookup failed",
                extra={"file_id": file_id, "error": str(e)},
            )
            return

    if file_record is None:
        logger.warning(
            "handle_file_uploaded: file not found",
            extra={"file_id": file_id, "workspace_id": workspace_id},
        )
        return

    # Step 2: Download file binary from storage
    try:
        storage = get_storage()
        file_bytes = await storage.download(file_record.storage_key)
    except Exception as e:
        logger.error(
            "handle_file_uploaded: storage download failed",
            extra={"file_id": file_id, "error": str(e)},
        )
        return

    # Step 3: Extract text (CPU-bound — run in executor)
    try:
        loop = asyncio.get_event_loop()
        extracted_text = await loop.run_in_executor(
            None,
            functools.partial(
                FileParsingEngine.extract_text,
                file_bytes,
                file_record.mime_type,
            ),
        )
    except Exception as e:
        logger.error(
            "handle_file_uploaded: text extraction failed",
            extra={"file_id": file_id, "mime_type": file_record.mime_type, "error": str(e)},
        )
        extracted_text = ""   # non-fatal — continue without text

    # Step 4: Persist extracted_text to DB
    async with AsyncSessionLocal() as db:
        try:
            from files.models import File
            await db.execute(
                sa.update(File)
                .where(
                    File.id == uuid.UUID(file_id),
                    File.workspace_id == int(workspace_id),
                )
                .values(extracted_text=extracted_text)
            )
            await db.commit()
            logger.info(
                "handle_file_uploaded: extracted_text saved",
                extra={
                    "file_id": file_id,
                    "chars_extracted": len(extracted_text),
                    "mime_type": mime_type,
                },
            )
        except Exception as e:
            logger.error(
                "handle_file_uploaded: DB update failed",
                extra={"file_id": file_id, "error": str(e)},
            )
            return

    # Step 5: Fan-out to indexing + metadata (added in Sub-step 7.3)
    # TODO 7.3: enqueue index_file_chunks + generate_file_metadata

IMPORTANT NOTES FOR CURSOR:
  1. File model uses storage_key (not storage_path). StorageBackend.download(key) exists.
  2. Workers use AsyncSessionLocal() — never get_session() (FastAPI dependency only).
  3. workspace_id is int in SQL; file_id is UUID. Note.id is int (relevant in 7.3).
  4. LocalStorageBackend.download raises HTTPException on missing files — catch in worker.

OUTPUT FORMAT:
Complete file content for Tasks 1-3.
Exact changes with surrounding context for Tasks 4-6.
Zero truncation. Highlight all IMPORTANT NOTES clearly.
```

**Validation:**
```powershell
docker compose build api worker

# Validate parser:
docker compose exec -e PYTHONPATH=/app/src api python -m shared.utils.parsers
# Expected: PASS for text/plain and text/html

# Apply migration:
docker compose run --rm migrate alembic upgrade head

# Upload a file and wait 10 seconds:
# POST /files/upload with a .txt or .pdf file

# Check extracted_text in DB:
docker compose exec db psql -U dashuser -d dashnotes \
  -c "SELECT id, name, length(extracted_text) FROM files ORDER BY created_at DESC LIMIT 3;"
# Expected: length(extracted_text) > 0 for uploaded file
```

**Commit:**
```bash
git commit -am "feat(slice7.2): file parser, extracted_text column, migration, extraction worker"
```

---

## Sub-step 7.3 — Fan-out: Indexing + Metadata Generation + Note Tagging

**Goal:**
- `index_file_chunks` task — indexes file text into `QDRANT_FILES_COLLECTION`
- `generate_file_metadata` task — structured LLM call → summary + tags on File
- `generate_note_tags` task — structured LLM call → tags on Note
- `handle_file_uploaded` enqueues both fan-out tasks after extraction
- `handle_note_created` enqueues `generate_note_tags`
- All tasks registered in `WorkerSettings`

**Files to open in Cursor:**
- `src/worker/automation/tasks.py`
- `src/worker/indexing/tasks.py` (reference — existing indexing pattern)
- `src/ai/workflows/pipeline.py` (reference — existing `EmbeddingPipeline`)
- `src/config/settings.py` (reference — `QDRANT_FILES_COLLECTION`)
- `src/notes/models.py` (reference — check if tags column exists)

---

```
ROLE: You are a senior backend engineer on DashNoteSystem.

OBJECTIVE: Sub-step 7.3 — Build three fan-out worker tasks and wire them
into the existing automation task handlers. Reuse existing pipeline code.

CONTEXT:
- Existing EmbeddingPipeline in src/ai/workflows/pipeline.py
  process_note() accepts (note_id, workspace_id, created_by, is_private,
  title, content, metadata). Adapt for files: use file_id as source_id.
- Existing Qdrant upsert in src/worker/indexing/tasks.py
  Read it to understand the PointStruct pattern. Reuse, never duplicate.
- QDRANT_FILES_COLLECTION: separate from notes_chunks — use settings var.
- LiteLLM structured outputs: litellm.acompletion(response_format=Schema)
  Same pattern as existing rag_service.py — reuse understanding.
- Notes tags column: check src/notes/models.py first.
  If tags column missing, add it + generate Alembic migration.
- Fan-out from handle_file_uploaded: enqueue AFTER extracted_text saved
  (at the TODO 7.3 comment from Sub-step 7.2)
- ctx["arq_pool"] available from the Slice 7.1 startup addition

LAWS IN EFFECT:
- Reuse EmbeddingPipeline — NEVER duplicate pipeline logic
- index_file_chunks uses QDRANT_FILES_COLLECTION — never notes_chunks
- Governance check (AutomationDecision) NOT applied to tagging/summarizing —
  these are non-destructive idempotent operations, governance is overhead
- Governance applied to destructive actions only (Sub-step 7.4)
- All fan-out tasks: try/except wrapping, structured logging
- Notes tags migration required if column missing

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 1 — Check and update src/notes/models.py (if tags missing)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Read src/notes/models.py.
If tags column does NOT exist, append:

    # --- AI Slice 7: auto-tagging ---
    tags: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=sa.text("'[]'::jsonb"),
        comment="AI-generated tags — populated by generate_note_tags worker",
    )

If it already exists, show me what exists and skip.
If added, generate migration:
  docker compose run --rm migrate alembic revision \
    --autogenerate -m "add_tags_to_notes"
  docker compose run --rm migrate alembic upgrade head

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 2 — Append 3 new tasks to src/worker/automation/tasks.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Append these 3 tasks at the bottom of tasks.py.
Do NOT modify existing handle_file_uploaded or handle_note_created stubs yet
(the stubs are updated in Tasks 3 and 4 below).

TASK A — index_file_chunks:

async def index_file_chunks(ctx: dict, *, file_id: str, workspace_id: str, created_by: str, is_private: bool) -> None:
    """
    Embed and index file extracted_text into QDRANT_FILES_COLLECTION.
    Reuses EmbeddingPipeline (Slice 1) + FileVectorIndexer (7.0) — no raw Qdrant in task.
  """
    import uuid
    import sqlalchemy as sa
    from config import get_settings
    from core.database.session import AsyncSessionLocal
    from ai.embeddings.factory import get_embedding_provider
    from ai.workflows.pipeline import EmbeddingPipeline
    from ai.retrieval.indexer import FileVectorIndexer   # added in 7.0

    settings = get_settings()
    if not settings.ai_enabled or not settings.qdrant_enabled:
        return

    file_name = "Untitled File"
    extracted_text = None
    async with AsyncSessionLocal() as db:
        try:
            from files.models import File
            result = await db.execute(
                sa.select(File.extracted_text, File.name).where(
                    File.id == uuid.UUID(file_id),
                    File.workspace_id == int(workspace_id),
                )
            )
            row = result.first()
            if row:
                extracted_text = row.extracted_text
                file_name = row.name or file_name
        except Exception as e:
            logger.error("index_file_chunks: DB load failed", extra={"error": str(e)})
            return

    if not extracted_text or not extracted_text.strip():
        logger.info("index_file_chunks: no text to index", extra={"file_id": file_id})
        return

    try:
        provider = await get_embedding_provider()
        pipeline = EmbeddingPipeline(provider=provider, redis=ctx.get("redis"))
        result = await pipeline.process_note(
            note_id=file_id,          # chunker treats source id as string; file_id stored as note_id in chunks
            workspace_id=workspace_id,
            created_by=created_by,
            is_private=is_private,
            title=file_name,
            content=extracted_text,
            metadata={"source_type": "file", "title": file_name},
        )
        if not result.embedded_chunks:
            return

        indexer = FileVectorIndexer(workspace_id)
        count = await indexer.index_file_chunks(file_id, result.embedded_chunks)
        logger.info(
            "index_file_chunks complete",
            extra={
                "file_id": file_id,
                "chunks_indexed": count,
                "collection": settings.QDRANT_FILES_COLLECTION,
            },
        )
    except Exception as e:
        logger.error("index_file_chunks failed", extra={"file_id": file_id, "error": str(e)})
        raise   # allow ARQ retry


TASK B — generate_file_metadata:

from pydantic import BaseModel, Field as PydanticField

class FileMetadataAnalysis(BaseModel):
    """Structured output for file metadata generation."""
    summary: str = PydanticField(description="Concise, informative summary of the document content. 2-4 sentences.")
    tags: list[str] = PydanticField(description="Up to 5 lowercase keyword tags. Single words or short phrases.")

async def generate_file_metadata(ctx: dict, *, file_id: str, workspace_id: str) -> None:
    """
    Generate AI summary and tags for a file using structured LLM output.
    Non-destructive — safe to retry. No governance check needed.
    Triggered by handle_file_uploaded fan-out.
    """
    import uuid
    import litellm
    import sqlalchemy as sa
    from config import get_settings
    from core.database.session import AsyncSessionLocal

    settings = get_settings()
    if not settings.ai_enabled:
        return

    # Load extracted_text
    async with AsyncSessionLocal() as db:
        try:
            from files.models import File
            result = await db.execute(
                sa.select(File.extracted_text).where(
                    File.id == uuid.UUID(file_id),
                    File.workspace_id == int(workspace_id),
                )
            )
            row = result.first()
            extracted_text = row.extracted_text if row else None
        except Exception as e:
            logger.error("generate_file_metadata: DB load failed", extra={"error": str(e)})
            return

    if not extracted_text or not extracted_text.strip():
        logger.info("generate_file_metadata: no text", extra={"file_id": file_id})
        return

    # Truncate to 6000 chars for metadata generation (cost control)
    context_text = extracted_text[:6000]

    try:
        response = await litellm.acompletion(
            model=settings.LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a document analyst. Generate a concise summary and "
                        "relevant keyword tags for the provided document content. "
                        "Base everything strictly on the provided text. No external knowledge."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Document content:\n\n{context_text}\n\nGenerate summary and tags.",
                },
            ],
            response_format=FileMetadataAnalysis,
            temperature=0.0,
            max_tokens=512,
        )
        parsed = FileMetadataAnalysis.model_validate_json(
            response.choices[0].message.content
        )
    except Exception as e:
        logger.error("generate_file_metadata: LLM call failed", extra={"error": str(e)})
        return

    # Persist summary and tags
    async with AsyncSessionLocal() as db:
        try:
            from files.models import File
            await db.execute(
                sa.update(File)
                .where(
                    File.id == uuid.UUID(file_id),
                    File.workspace_id == int(workspace_id),
                )
                .values(summary=parsed.summary, tags=parsed.tags)
            )
            await db.commit()
            logger.info(
                "generate_file_metadata complete",
                extra={"file_id": file_id, "tags": parsed.tags},
            )
        except Exception as e:
            logger.error("generate_file_metadata: DB update failed", extra={"error": str(e)})


TASK C — generate_note_tags:

class NoteTagAnalysis(BaseModel):
    """Structured output for note auto-tagging."""
    tags: list[str] = PydanticField(description="Up to 5 lowercase keyword tags for the note. Single words or short phrases.")

async def generate_note_tags(ctx: dict, *, note_id: str, workspace_id: str, content: str, title: str) -> None:
    """
    Auto-tag a note using structured LLM output.
    Non-destructive — safe to retry. No governance check needed.
    Triggered by handle_note_created fan-out.
    """
    import uuid
    import litellm
    import sqlalchemy as sa
    from config import get_settings
    from core.database.session import AsyncSessionLocal

    settings = get_settings()
    if not settings.ai_enabled:
        return

    context_text = f"Title: {title}\n\n{content[:3000]}"

    try:
        response = await litellm.acompletion(
            model=settings.LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "Generate relevant keyword tags for the note. Base tags strictly on content provided.",
                },
                {"role": "user", "content": context_text},
            ],
            response_format=NoteTagAnalysis,
            temperature=0.0,
            max_tokens=128,
        )
        parsed = NoteTagAnalysis.model_validate_json(
            response.choices[0].message.content
        )
    except Exception as e:
        logger.error("generate_note_tags: LLM call failed", extra={"error": str(e)})
        return

    # Persist tags — Note.id is int, not UUID
    async with AsyncSessionLocal() as db:
        try:
            from notes.models import Note
            await db.execute(
                sa.update(Note)
                .where(
                    Note.id == int(note_id),
                    Note.workspace_id == int(workspace_id),
                )
                .values(tags=parsed.tags)
            )
            await db.commit()
            logger.info(
                "generate_note_tags complete",
                extra={"note_id": note_id, "tags": parsed.tags},
            )
        except Exception as e:
            logger.error("generate_note_tags: DB update failed", extra={"error": str(e)})

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 3 — Update handle_file_uploaded fan-out section
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Find the TODO 7.3 comment at the end of handle_file_uploaded.
Replace it with the actual fan-out calls:

    # --- AI Slice 7.3: fan-out to indexing and metadata ---
    arq_pool = ctx.get("arq_pool")
    if arq_pool and extracted_text:
        try:
            await arq_pool.enqueue_job(
                "index_file_chunks",
                file_id=file_id,
                workspace_id=workspace_id,
                created_by=event_data.get("uploaded_by", ""),
                is_private=event_data.get("is_private", False),
            )
            await arq_pool.enqueue_job(
                "generate_file_metadata",
                file_id=file_id,
                workspace_id=workspace_id,
            )
            logger.info(
                "handle_file_uploaded: fan-out jobs enqueued",
                extra={"file_id": file_id},
            )
        except Exception as e:
            logger.error("handle_file_uploaded: fan-out enqueue failed", extra={"error": str(e)})

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 4 — Update handle_note_created fan-out
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Find the handle_note_created stub.
Replace the TODO comment with:

    # --- AI Slice 7.3: fan-out to note tagging ---
    from config import get_settings
    settings = get_settings()
    arq_pool = ctx.get("arq_pool")
    if arq_pool and settings.ai_enabled:
        try:
            await arq_pool.enqueue_job(
                "generate_note_tags",
                note_id=event_data.get("note_id"),
                workspace_id=event_data.get("workspace_id"),
                content=event_data.get("content", ""),
                title=event_data.get("title", ""),
            )
        except Exception as e:
            logger.error("handle_note_created: fan-out enqueue failed", extra={"error": str(e)})

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 5 — Register new tasks in WorkerSettings
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Update src/worker/main.py WorkerSettings.functions to include:
  index_file_chunks, generate_file_metadata, generate_note_tags

Update the import at top of worker/main.py:
  from worker.automation.tasks import (
      handle_file_uploaded,
      handle_note_created,
      handle_note_updated,
      handle_file_deleted,
      index_file_chunks,         # NEW
      generate_file_metadata,    # NEW
      generate_note_tags,        # NEW
  )

Show exact functions list after update.

OUTPUT FORMAT:
Tasks 1: check and show result.
Tasks 2: complete new task code (append to tasks.py).
Tasks 3-5: exact lines with surrounding context.
Zero truncation.
```

**Validation:**
```powershell
docker compose up -d --build api worker

# Upload a text file:
# POST /files/upload

docker compose logs worker --tail 50
# Expected sequence:
#   "handle_file_uploaded received"
#   "handle_file_uploaded: extracted_text saved" chars_extracted > 0
#   "handle_file_uploaded: fan-out jobs enqueued"
#   "index_file_chunks complete" chunks_indexed > 0
#   "generate_file_metadata complete" tags populated

# Check file in DB:
docker compose exec db psql -U dashuser -d dashnotes \
  -c "SELECT id, name, length(extracted_text), summary, tags FROM files ORDER BY created_at DESC LIMIT 1;"
# Expected: extracted_text not null, summary not null, tags not empty []

# Check Qdrant files collection:
curl.exe -sS "http://127.0.0.1:6333/collections/files_chunks"
# Expected: vectors_count > 0

# Create a note and check tags:
docker compose logs worker --tail 20
# Expected: "generate_note_tags complete" with tags array

docker compose exec db psql -U dashuser -d dashnotes \
  -c "SELECT id, title, tags FROM notes ORDER BY created_at DESC LIMIT 3;"
# Expected: tags column populated with relevant keywords
```

**Commit:**
```bash
git commit -am "feat(slice7.3): file indexing, metadata generation, note auto-tagging fan-out"
```

---

## Sub-step 7.4 — Automation Governance

**Goal:**
- `AutomationDecision` schema — structured output for action evaluation
- `AutomationDecisionEngine` — evaluates destructive or external actions only
- Governance applied to: actions that modify or delete content based on AI decisions
- Governance NOT applied to: auto-tagging, auto-summarizing (non-destructive)
- `[AUTOMATION_GOVERNANCE_BLOCK]` log marker when action is blocked
- Foundation for future human-approval workflows

**Files to open in Cursor:**
- `src/worker/automation/decision.py` (create empty)
- `src/worker/automation/tasks.py` (reference — show example usage)

---

```
ROLE: You are a senior backend engineer on DashNoteSystem.

OBJECTIVE: Sub-step 7.4 — Build the AutomationDecisionEngine for
governing destructive AI-initiated actions. Apply it only where
warranted — not on idempotent metadata operations.

CONTEXT:
- AutomationDecision governs: actions that create/modify/delete records
  based SOLELY on AI judgment, without explicit user instruction.
  Examples: AI decides to auto-delete a duplicate note, auto-merge notes,
  auto-archive old content, auto-send notifications.
- AutomationDecision does NOT govern: auto-tagging, auto-summarizing,
  auto-indexing — these are read operations or additive metadata.
  Applying governance to these wastes LLM calls and adds latency.
- Confidence threshold: >= 0.95 AND is_destructive=False → execute
  Anything else → log [AUTOMATION_GOVERNANCE_BLOCK], store as pending
- Future human-approval: pending actions stored for user review (future slice)

LAWS IN EFFECT:
- AutomationDecisionEngine.evaluate_action() calls litellm — LLM cost
  Only call it for genuinely ambiguous or potentially destructive decisions
- Never call it in generate_note_tags, generate_file_metadata, index_file_chunks
- decision.py: no FastAPI, no SQLAlchemy, no RequestContext
- Log marker [AUTOMATION_GOVERNANCE_BLOCK] must be exact string — searchable in logs

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 1 — src/worker/automation/decision.py (CREATE NEW)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Create this file completely:

"""
AutomationDecisionEngine — governs AI-initiated destructive actions.

When to use:
  Any automation that modifies, deletes, or sends based on PURE AI judgment
  without explicit user instruction. Examples:
    - Auto-delete duplicate notes
    - Auto-merge similar content
    - Auto-archive old items
    - Auto-send notifications to external systems

When NOT to use:
  Additive, idempotent, non-destructive operations:
    - generate_note_tags    → just adds tags, reversible
    - generate_file_metadata → just adds summary, reversible
    - index_file_chunks      → vector upsert, idempotent
  Never call evaluate_action() on these — pure cost with no safety benefit.

Decision flow:
  evaluate_action(context) → AutomationDecision
  should_execute_immediately(decision) → bool
    True only if confidence >= 0.95 AND is_destructive=False
    False → log [AUTOMATION_GOVERNANCE_BLOCK], store as pending action

IMPORT LAW: litellm, pydantic, config, stdlib only.
No FastAPI. No SQLAlchemy. No domain repositories.
"""
from __future__ import annotations

import logging
from typing import ClassVar

import litellm
from pydantic import BaseModel, Field, field_validator

from config import get_settings

logger = logging.getLogger(__name__)

# Searchable log marker — used for monitoring/alerting
GOVERNANCE_BLOCK_MARKER = "[AUTOMATION_GOVERNANCE_BLOCK]"


class AutomationDecision(BaseModel):
    """
    Structured output from AutomationDecisionEngine.evaluate_action().

    action_type:   Describes the planned operation clearly.
    is_destructive: True if operation modifies, deletes, or sends irreversibly.
    confidence:    0.0 to 1.0 — model's confidence this action is correct.
    reasoning:     Concise explanation of the decision factors.
    """
    action_type: str = Field(
        description="The planned operation — e.g. 'delete_duplicate_note', 'merge_notes'."
    )
    is_destructive: bool = Field(
        description="True if this modifies, deletes, or sends data irreversibly."
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score 0.0–1.0 that this action is correct and safe.",
    )
    reasoning: str = Field(
        description="Concise reasoning for the action and confidence score."
    )

    @field_validator("confidence")
    @classmethod
    def round_confidence(cls, v: float) -> float:
        return round(v, 3)


class AutomationDecisionEngine:
    """
    Evaluates whether an AI-initiated action should execute immediately
    or be held for human review.

    Usage (only for genuinely ambiguous/destructive actions):
        decision = await AutomationDecisionEngine.evaluate_action(
            context="The system found 3 notes with identical content. "
                    "Proposed action: delete 2 duplicates."
        )
        if await AutomationDecisionEngine.should_execute_immediately(decision):
            await execute_action()
        else:
            await store_pending_action(decision)  # human reviews later
    """

    SAFE_THRESHOLD: ClassVar[float] = 0.95

    @classmethod
    async def evaluate_action(cls, context: str) -> AutomationDecision:
        """
        Evaluate whether a proposed automation action is safe to execute.

        Args:
            context: Plain English description of the proposed action and
                     its context. Include relevant data but not PII.

        Returns:
            AutomationDecision with confidence, is_destructive, reasoning.
        """
        settings = get_settings()

        try:
            response = await litellm.acompletion(
                model=settings.LLM_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an automation safety evaluator. "
                            "Assess whether the proposed automated action is safe to execute "
                            "without human approval. Be conservative — when in doubt, "
                            "mark confidence below 0.95 or is_destructive=True to require review."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Evaluate this proposed action:\n\n{context}",
                    },
                ],
                response_format=AutomationDecision,
                temperature=0.0,
                max_tokens=256,
            )
            return AutomationDecision.model_validate_json(
                response.choices[0].message.content
            )
        except Exception as e:
            logger.error(
                "AutomationDecisionEngine.evaluate_action failed",
                extra={"error": str(e)},
            )
            # Fail safe — unknown = block
            return AutomationDecision(
                action_type="unknown",
                is_destructive=True,
                confidence=0.0,
                reasoning=f"Evaluation failed: {str(e)}. Blocking for safety.",
            )

    @classmethod
    async def should_execute_immediately(cls, decision: AutomationDecision) -> bool:
        """
        Return True ONLY if confidence >= 0.95 AND is_destructive is False.
        Any other combination → block and require human review.

        This is an absolute rule — no exceptions, no overrides.
        """
        safe = decision.confidence >= cls.SAFE_THRESHOLD and not decision.is_destructive

        if not safe:
            logger.warning(
                f"{GOVERNANCE_BLOCK_MARKER} Action blocked — requires human approval",
                extra={
                    "action_type": decision.action_type,
                    "is_destructive": decision.is_destructive,
                    "confidence": decision.confidence,
                    "reasoning": decision.reasoning,
                },
            )

        return safe

    @classmethod
    async def evaluate_and_gate(
        cls,
        context: str,
        action_description: str,
    ) -> tuple[bool, AutomationDecision]:
        """
        Convenience method: evaluate and return (should_execute, decision).

        Usage:
            should_run, decision = await AutomationDecisionEngine.evaluate_and_gate(
                context="...", action_description="delete duplicate"
            )
            if should_run:
                await do_it()
        """
        decision = await cls.evaluate_action(context)
        should_run = await cls.should_execute_immediately(decision)
        return should_run, decision


if __name__ == "__main__":
    # Validation: python -m worker.automation.decision
    import asyncio

    async def _validate() -> None:
        # Test safe decision path (no real LLM call — just schema validation)
        safe_decision = AutomationDecision(
            action_type="add_tags",
            is_destructive=False,
            confidence=0.97,
            reasoning="Adding tags is additive and reversible.",
        )
        result = await AutomationDecisionEngine.should_execute_immediately(safe_decision)
        assert result is True, "FAIL: safe action should execute"
        print("PASS: safe action executes immediately")

        # Test blocked decision
        risky = AutomationDecision(
            action_type="delete_notes",
            is_destructive=True,
            confidence=0.99,
            reasoning="Deleting is irreversible.",
        )
        result = await AutomationDecisionEngine.should_execute_immediately(risky)
        assert result is False, "FAIL: destructive action should be blocked"
        print("PASS: destructive action blocked correctly")

        # Test low confidence path
        uncertain = AutomationDecision(
            action_type="merge_notes",
            is_destructive=False,
            confidence=0.72,
            reasoning="Not sure if these notes should be merged.",
        )
        result = await AutomationDecisionEngine.should_execute_immediately(uncertain)
        assert result is False, "FAIL: low confidence should be blocked"
        print("PASS: low confidence action blocked correctly")

        print("PASS: AutomationDecisionEngine validated")

    asyncio.run(_validate())

OUTPUT FORMAT:
Complete file content. Zero truncation.
```

**Validation — Slice 7 Gate:**
```powershell
docker compose build api worker

# Validate governance engine:
docker compose exec -e PYTHONPATH=/app/src api python -m worker.automation.decision
# Expected:
#   PASS: safe action executes immediately
#   PASS: destructive action blocked correctly
#   PASS: low confidence action blocked correctly

docker compose up -d --build api worker

# Full end-to-end: upload a PDF file
# docker compose logs worker --tail 100 | grep -E "complete|BLOCK|enqueued"
# Expected sequence:
#   handle_file_uploaded received
#   extracted_text saved (chars > 0)
#   fan-out jobs enqueued
#   index_file_chunks complete
#   generate_file_metadata complete

# Search the file content via AI:
Invoke-RestMethod -Uri "http://127.0.0.1/ai/test-search?q=content+from+file&limit=3" `
  -Headers @{ Authorization = "Bearer <TOKEN>" }
# If QDRANT_FILES_COLLECTION is searched — extend search wrapper in Slice 8
# For now: verify index_file_chunks ran without error

# Check DB:
docker compose exec db psql -U dashuser -d dashnotes \
  -c "SELECT name, length(extracted_text), summary, array_length(tags,1) FROM files ORDER BY created_at DESC LIMIT 3;"
# Expected: extracted_text > 0, summary populated, tags array length >= 1

# Create note and check tags:
docker compose exec db psql -U dashuser -d dashnotes \
  -c "SELECT title, tags FROM notes ORDER BY created_at DESC LIMIT 3;"
# Expected: tags array populated for recent notes
```

**Commit:**
```bash
git commit -am "feat(slice7.4): automation governance engine, safe execution gate — slice 7 complete"
```

---

## Slice 7 Complete — What Was Built

```
src/shared/events/definitions.py       ← 7.0: payload fields appended to event classes
src/config.py                          ← 7.0: QDRANT_FILES_COLLECTION
src/ai/retrieval/collection.py         ← 7.0: ensure_files_collection()
src/ai/retrieval/indexer.py            ← 7.0: FileVectorIndexer (mirror NoteVectorIndexer)
src/shared/events/bus.py               ← emit_event() dispatcher (imports existing definitions)
src/shared/utils/__init__.py
src/shared/utils/parsers.py            ← FileParsingEngine (PDF/DOCX/HTML/text)
src/worker/automation/__init__.py
src/worker/automation/tasks.py         ← 7 tasks: handle_file_uploaded, handle_note_created,
                                          handle_note_updated, handle_file_deleted,
                                          index_file_chunks, generate_file_metadata,
                                          generate_note_tags
src/worker/automation/decision.py      ← AutomationDecisionEngine, AutomationDecision
src/files/models.py                    ← extracted_text, summary, tags columns added
src/notes/models.py                    ← tags column added (if missing)
src/worker/main.py                     ← arq_pool in ctx, 7 tasks registered
src/files/router.py                    ← FileUploadedEvent emitted after upload (+ Request dep)
src/notes/router.py                    ← NoteCreatedEvent emitted (alongside Slice 1 embed)
alembic/versions/xxx_slice7.py         ← migration for new columns
requirements.txt                       ← pypdf, python-docx, beautifulsoup4, lxml
```

```
What is NOT in Slice 7 (correct — later slices):
  ✗ Files searchable via /ai/test-search (needs wrapper extension — Slice 8 adds files collection)
  ✗ Human approval UI for blocked governance actions (pending actions table — later)
  ✗ Neo4j entity extraction (Slice 8 — optional)
  ✗ Multi-agent automation (Slice 9)
  ✗ LangSmith active tracing (Slice 10)

What was NEVER touched (logic unchanged):
  src/ai/workflows/pipeline.py        ← reused unchanged (listed again for emphasis)
  src/ai_routes/chat.py               ← RAG chat unchanged
  src/ai_routes/agent.py              ← Agent endpoints unchanged
  Slice 1 embed_note_task block       ← still runs alongside Slice 7 events

What 7.0 extended (schemas/infra only — no behavior change to existing routes):
  src/shared/events/definitions.py    ← payload fields only; EventType values unchanged
```

---

> **Next:** Slice 7P — Production Platform (`slice-platform.md`)
> Prod compose, env contract, CI/CD, VPS deploy. Run **before** Slice 8+ unless you only need local dev.
> If LLM automation flakes on 429/503: run `slice7-llm-hardening.md` first.
>
> **After 7P gate:** Slice 8 — GraphRAG with Neo4j (Optional), or Slice 10 — Observability.