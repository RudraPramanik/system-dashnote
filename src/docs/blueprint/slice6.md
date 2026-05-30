# Slice 6 — LangGraph Workflows
## Final Cursor Prompts (4 Sub-steps, Production-Grade, No Hallucination)

> **Context carried from previous slices**
> - Slice 5 gate passed: conversation threads persist, history loads correctly ✅
> - `RagService.answer()` and `stream_answer()` in `src/ai/services/rag_service.py`
> - `WorkspaceVectorSearch` in `src/ai/retrieval/wrapper.py`
> - `ThreadRepository` in `src/ai_memory/repository.py`
> - `ThreadService` in `src/ai/memory/service.py`
> - Notes data access: `src/notes/repository.py` (existing, untouched)
> - Auth: `core/security/context.py` → `RequestContext`
> - DB session: `core/database/session.py` → `get_session()`
> - Import style: `from config import settings` (never `from src.config`)
> - `POST /ai/chat` and `POST /ai/chat/stream` — NEVER replaced or modified
> - LangGraph is a NEW capability on top of existing working chat

---

## ARCHITECTURE LAW
### Paste as your FIRST message in every Cursor Composer session.

```
ARCHITECTURE LAW — DashNoteSystem. Enforce in ALL generated code.

CRITICAL FOR SLICE 6:
  POST /ai/chat is NEVER replaced or modified — it remains the fast RAG path.
  POST /ai/chat/stream is NEVER replaced or modified.
  LangGraph adds NEW endpoints: POST /ai/agent and POST /ai/agent/stream.
  Users choose: fast RAG (/ai/chat) or agentic (/ai/agent).

MODULE PATHS:
  Import as: from config import settings, get_settings
             from ai.tools.note_tools import get_note_tools
             from ai.workflows.workspace_assistant import get_workspace_assistant
             from ai.memory.checkpointer import init_checkpointer, get_graph_checkpointer
             from notes.service import NoteService
  NEVER as:  from src.config import ...
             from src.ai.tools import ...

TOOL CHAIN LAW:
  Tools MUST call existing service layer only:
    search_notes_tool → RagService.answer()
    create_note_tool  → NoteService.create_note()
    update_note_tool  → NoteService.update_note()
    summarize_workspace_tool → RagService.answer() with broad query
  Tools NEVER call repositories directly.
  Tools accept (workspace_id, user_id, role) as plain strings ONLY.
  Tools NEVER accept RequestContext, FastAPI objects, or SQLAlchemy sessions.

LANGGRAPH CONNECTION LAW:
  AsyncPostgresSaver uses psycopg3 async — NOT SQLAlchemy.
  It does NOT share connection pool with SQLAlchemy engine.
  Use a single async psycopg connection for checkpointer only.
  Never pass DATABASE_URL to SQLAlchemy AND psycopg simultaneously in same pool.

GRAPH COMPILATION LAW:
  graph.compile() is NEVER called at module import time.
  It is called once inside an async init function, result cached.
  get_workspace_assistant() returns the cached compiled graph.
  Checkpointer must be initialized (init_checkpointer()) before compile().

TOOL FORMAT LAW:
  Tools use StructuredTool with explicit args_schema Pydantic models.
  Plain @tool decorator on async functions loses type safety.
  LiteLLM tool calling uses OpenAI function definition format — not
  LangChain .bind_tools() which is for LangChain LLM objects only.

MODIFICATION LAW:
  src/ai_routes/chat.py — NEVER modified in Slice 6
  src/ai/services/rag_service.py — NEVER modified in Slice 6
  src/main.py — append only (init_checkpointer + new router)

NEW FILES ONLY:
  src/notes/service.py         ← thin service over notes repository
  src/ai/tools/__init__.py
  src/ai/tools/note_tools.py   ← StructuredTool definitions
  src/ai/tools/schemas.py      ← Pydantic args_schema models for tools
  src/ai/memory/checkpointer.py
  src/ai/workflows/state.py
  src/ai/workflows/workspace_assistant.py
  src/ai_routes/agent.py       ← NEW endpoints only

Acknowledge these laws before writing any code.
```

---

## Sub-step 6.1 — Checkpointer + NoteService

**Goal:**
- `AGENT_MAX_ITERATIONS` and `AGENT_TOOL_TIMEOUT` settings appended
- `AsyncPostgresSaver` checkpointer wired safely — no pool conflict
- `NoteService` built — thin layer over existing `notes/repository.py`
- This is the foundation everything else calls — must be solid before tools

**Files to open in Cursor:**
- `src/config/settings.py`
- `src/notes/repository.py` (reference — understand existing interface)
- `src/ai/memory/checkpointer.py` (create empty)
- `src/notes/service.py` (create empty)

---

```
ROLE: You are a senior backend engineer on DashNoteSystem.

OBJECTIVE: Sub-step 6.1 — Append agent settings, build the LangGraph
AsyncPostgresSaver checkpointer, and create NoteService as a thin
service layer over the existing notes repository.

CONTEXT:
- Existing notes repository: src/notes/repository.py
  Read it carefully to understand available methods and their signatures.
  NoteService wraps these methods — never duplicates logic.
- AsyncPostgresSaver needs psycopg3 (not psycopg2, not SQLAlchemy).
  Check if psycopg (psycopg3) is already in requirements.txt.
  asyncpg is for SQLAlchemy — psycopg[async] is for LangGraph checkpointer.
- DATABASE_URL uses asyncpg driver: postgresql+asyncpg://...
  For psycopg3, strip the "+asyncpg" driver part: postgresql://...
- Checkpointer is initialized ONCE in lifespan startup via init_checkpointer()
  get_graph_checkpointer() returns the cached instance after init

LAWS IN EFFECT:
- Append-only to settings and requirements.txt
- NoteService accepts AsyncSession per method — never stored on instance
- NoteService has NO FastAPI imports, NO RequestContext
- Checkpointer uses psycopg[async] — separate from SQLAlchemy asyncpg pool
- graph.compile() is NOT called in this step — that is 6.3

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 1 — requirements.txt (append-only)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Read requirements.txt. Check which of these are already present.
Append ONLY what is missing under:

# --- AI Slice 6: LangGraph workflows ---
psycopg[async]>=3.1.0   # required by AsyncPostgresSaver (psycopg3, not asyncpg)

Do NOT add psycopg2, psycopg2-binary, or any other postgres driver.
asyncpg is already there for SQLAlchemy — this is a separate driver for LangGraph.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 2 — Settings (append-only)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Read Settings class. Append if not already present:

    # ── AI Slice 6: LangGraph Agent ────────────────────────────────
    AGENT_MAX_ITERATIONS: int = 10    # prevents infinite tool loops
    AGENT_TOOL_TIMEOUT: int = 30      # seconds per tool call

Append computed property:

    @property
    def psycopg_database_url(self) -> str:
        """
        DATABASE_URL adapted for psycopg3 (AsyncPostgresSaver).
        Strips '+asyncpg' driver suffix — psycopg3 uses plain postgresql://.
        """
        return self.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 3 — src/ai/memory/checkpointer.py (CREATE NEW)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Create this file completely:

"""
LangGraph AsyncPostgresSaver checkpointer for DashNoteSystem.

The checkpointer persists LangGraph graph execution state between
agent turns. It is the EXECUTION layer — separate from the PRODUCT
layer (ai_threads / ai_messages from Slice 5).

Both layers are linked only by thread_id string. No FK. No shared pool.

Connection isolation:
  SQLAlchemy uses asyncpg driver (postgresql+asyncpg://).
  AsyncPostgresSaver uses psycopg3 async (postgresql://).
  They are separate connection pools — no resource starvation.

Initialization:
  init_checkpointer() called ONCE in FastAPI lifespan startup.
  get_graph_checkpointer() returns cached instance after init.
  Never call get_graph_checkpointer() before init_checkpointer().

IMPORT LAW: Only langgraph, psycopg, config, stdlib.
No SQLAlchemy. No FastAPI.
"""
from __future__ import annotations

import logging

from config import get_settings

logger = logging.getLogger(__name__)

# Module-level singleton — set by init_checkpointer()
_checkpointer = None
_checkpointer_conn = None   # psycopg async connection — kept open


async def init_checkpointer() -> None:
    """
    Initialize the AsyncPostgresSaver checkpointer.

    Called ONCE from FastAPI lifespan startup — before any graph compilation.
    Creates the LangGraph internal checkpoint tables if they don't exist.
    Safe to call on every restart — setup() is idempotent.

    Tables created by LangGraph (separate from your application tables):
      checkpoints, checkpoint_blobs, checkpoint_writes, checkpoint_migrations
    """
    global _checkpointer, _checkpointer_conn

    if _checkpointer is not None:
        logger.debug("Checkpointer already initialized — skipping")
        return

    settings = get_settings()

    try:
        import psycopg
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        # Open a dedicated async psycopg3 connection for the checkpointer
        # This is separate from SQLAlchemy's asyncpg pool — no resource conflict
        _checkpointer_conn = await psycopg.AsyncConnection.connect(
            settings.psycopg_database_url,
            autocommit=True,
        )
        _checkpointer = AsyncPostgresSaver(_checkpointer_conn)

        # Create LangGraph internal tables if they don't exist
        # Idempotent — safe to run on every startup
        await _checkpointer.setup()

        logger.info(
            "LangGraph checkpointer initialized",
            extra={"tables": "checkpoints, checkpoint_blobs, checkpoint_writes"},
        )

    except Exception as e:
        logger.error(
            "Checkpointer initialization failed",
            extra={"error": str(e)},
        )
        # Non-fatal: agent features unavailable but RAG chat continues
        _checkpointer = None
        raise


async def close_checkpointer() -> None:
    """Close the psycopg connection. Called from FastAPI lifespan shutdown."""
    global _checkpointer, _checkpointer_conn
    if _checkpointer_conn is not None:
        try:
            await _checkpointer_conn.close()
            logger.info("Checkpointer connection closed")
        except Exception as e:
            logger.warning("Checkpointer close error", extra={"error": str(e)})
        finally:
            _checkpointer = None
            _checkpointer_conn = None


def get_graph_checkpointer():
    """
    Return the initialized checkpointer.
    Raises RuntimeError if init_checkpointer() was not called first.
    """
    if _checkpointer is None:
        raise RuntimeError(
            "Checkpointer not initialized. "
            "Ensure init_checkpointer() runs in FastAPI lifespan startup."
        )
    return _checkpointer

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 4 — src/notes/service.py (CREATE NEW)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Read src/notes/repository.py carefully FIRST.
Identify the exact method signatures available.
Then create src/notes/service.py as a thin service layer:

"""
NoteService — thin service layer over notes/repository.py.

Exists so LangGraph agent tools can create and update notes
without importing SQLAlchemy or domain repositories directly.

This service accepts AsyncSession per method — never stored.
It accepts plain strings for IDs — converts to UUID internally.

CRITICAL: Read src/notes/repository.py to match method signatures exactly.
This file adapts the existing repository to an agent-callable interface.

IMPORT LAW: notes.repository, core.database.session, stdlib, pydantic only.
No FastAPI. No RequestContext. AsyncSession injected per method.
"""
from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

from notes.repository import NoteRepository   # adjust import if path differs

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

_repo = NoteRepository()   # stateless — safe to instantiate once


class NoteService:
    """
    Agent-callable note operations.

    All methods accept AsyncSession as first parameter and plain
    string IDs — never SQLAlchemy models or RequestContext objects.

    LangGraph tools call this service. Tools never call the repository directly.
    This enforces the tool → service → repository chain.

    IMPORTANT: Read notes/repository.py to verify method names before calling.
    Adjust method calls below to match what actually exists in your repository.
    """

    async def create_note(
        self,
        db: "AsyncSession",
        *,
        title: str,
        content: str,
        workspace_id: str,
        created_by: str,
        is_private: bool = False,
    ) -> dict:
        """
        Create a new note.
        Returns dict with note_id and title for tool confirmation.

        ADJUST: Match the exact create method signature in notes/repository.py.
        This may need a schema object (NoteCreate) depending on your repository.
        """
        try:
            # Build whatever schema/object your repository's create method expects
            # Read notes/repository.py and adjust this call accordingly
            note = await _repo.create(
                db,
                workspace_id=uuid.UUID(workspace_id),
                created_by=uuid.UUID(created_by),
                title=title,
                content=content,
                is_private=is_private,
            )
            logger.info(
                "Note created via agent tool",
                extra={"note_id": str(note.id), "workspace_id": workspace_id},
            )
            return {"note_id": str(note.id), "title": note.title}
        except Exception as e:
            logger.error(
                "NoteService.create_note failed",
                extra={"error": str(e), "workspace_id": workspace_id},
            )
            raise

    async def update_note(
        self,
        db: "AsyncSession",
        *,
        note_id: str,
        content: str,
        workspace_id: str,
        updated_by: str,
    ) -> dict:
        """
        Update note content.
        workspace_id enforced — cannot update notes from other workspaces.

        ADJUST: Match the exact update method signature in notes/repository.py.
        """
        try:
            note = await _repo.update(
                db,
                note_id=uuid.UUID(note_id),
                workspace_id=uuid.UUID(workspace_id),
                content=content,
            )
            if note is None:
                raise ValueError(f"Note {note_id} not found in workspace {workspace_id}")
            return {"note_id": str(note.id), "title": note.title}
        except Exception as e:
            logger.error(
                "NoteService.update_note failed",
                extra={"note_id": note_id, "error": str(e)},
            )
            raise

OUTPUT FORMAT:
Generate all files completely. Zero truncation.
For Task 4: add a prominent comment at the top of every method:
  # IMPORTANT: Verify this matches your notes/repository.py signature
  # Adjust the method call if needed before running
```

**Validation:**
```powershell
docker compose build api
# Expected: psycopg[async] installs cleanly alongside asyncpg

docker compose exec -e PYTHONPATH=/app/src api python -c "
from ai.memory.checkpointer import init_checkpointer, get_graph_checkpointer
from notes.service import NoteService
from config import get_settings
s = get_settings()
print('psycopg_database_url:', s.psycopg_database_url[:30], '...')
print('AGENT_MAX_ITERATIONS:', s.AGENT_MAX_ITERATIONS)
print('PASS: imports clean')
"
```

**Commit:**
```bash
git commit -am "feat(slice6.1): checkpointer, note_service, agent settings"
```

---

## Sub-step 6.2 — Tool Definitions

**Goal:**
- Pydantic `args_schema` models for every tool — type-safe
- `StructuredTool` definitions with rich docstrings (LLM reads these)
- Tools call real services — `RagService.answer()` and `NoteService`
- Tools are stateless — no DB session stored — session injected per call

**Files to open in Cursor:**
- `src/ai/tools/schemas.py` (create empty)
- `src/ai/tools/note_tools.py` (create empty)
- `src/ai/services/rag_service.py` (reference — existing interface)
- `src/notes/service.py` (reference — just created)

---

```
ROLE: You are a senior backend engineer on DashNoteSystem.

OBJECTIVE: Sub-step 6.2 — Build StructuredTool definitions for the
LangGraph workspace assistant. Tools have rich docstrings, explicit
Pydantic args_schema, and call only existing service layer methods.

CONTEXT:
- RagService.answer() exists: accepts (question, workspace_id, user_id, role)
  as keyword strings. Returns ChatResult with .answer and .citations.
- NoteService exists: create_note(), update_note() accept AsyncSession + strings.
- Tools are called by LangGraph with JSON-serialized arguments.
  args_schema (Pydantic BaseModel) handles deserialization and validation.
- db session for NoteService: tools receive it via tool_context or
  it is injected into the tool at graph node execution time.
  Pattern: store db on AgentState and retrieve in tool via context variable.
- LiteLLM tool calling: tools registered as OpenAI function definitions.
  StructuredTool.from_function() produces the correct format.

LAWS IN EFFECT:
- Tools use StructuredTool — NOT plain @tool decorator on async functions
- Every tool has a Pydantic args_schema model in schemas.py
- Tools call service layer only — never repository, never direct DB
- Tools accept (workspace_id, user_id, role) as plain string params
- NO FastAPI, NO RequestContext, NO SQLAlchemy imports in tool files
- db session for note mutation tools: use contextvars pattern (see Task 3)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 1 — src/ai/tools/__init__.py (CREATE NEW)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""LangGraph agent tools for DashNoteSystem workspace assistant."""

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 2 — src/ai/tools/schemas.py (CREATE NEW)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Create this file completely:

"""
Pydantic args_schema models for LangGraph agent tools.

Each StructuredTool needs an args_schema so LangGraph can:
  1. Validate LLM-generated arguments before calling the tool
  2. Serialize/deserialize arguments correctly
  3. Generate accurate JSON schema for the LLM's function definitions

IMPORT LAW: pydantic and stdlib only.
"""
from __future__ import annotations
from pydantic import BaseModel, Field


class SearchNotesArgs(BaseModel):
    """Arguments for search_notes_tool."""
    question: str = Field(description="The search query to find relevant notes.")
    workspace_id: str = Field(description="Workspace ID from agent state — do not modify.")
    user_id: str = Field(description="User ID from agent state — do not modify.")
    role: str = Field(description="User role from agent state — do not modify.")


class CreateNoteArgs(BaseModel):
    """Arguments for create_note_tool."""
    title: str = Field(description="Title for the new note.")
    content: str = Field(description="Full markdown content for the note body.")
    workspace_id: str = Field(description="Workspace ID from agent state — do not modify.")
    user_id: str = Field(description="User ID from agent state — do not modify.")
    role: str = Field(description="User role from agent state — do not modify.")


class UpdateNoteArgs(BaseModel):
    """Arguments for update_note_tool."""
    note_id: str = Field(description="UUID of the note to update.")
    content: str = Field(description="New full markdown content for the note.")
    workspace_id: str = Field(description="Workspace ID from agent state — do not modify.")
    user_id: str = Field(description="User ID from agent state — do not modify.")
    role: str = Field(description="User role from agent state — do not modify.")


class SummarizeWorkspaceArgs(BaseModel):
    """Arguments for summarize_workspace_tool."""
    workspace_id: str = Field(description="Workspace ID from agent state — do not modify.")
    user_id: str = Field(description="User ID from agent state — do not modify.")
    role: str = Field(description="User role from agent state — do not modify.")

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 3 — src/ai/tools/note_tools.py (CREATE NEW)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Create this file completely:

"""
LangGraph agent tools for DashNoteSystem workspace assistant.

These tools are called by the LangGraph agent when it decides to
take actions inside the user's workspace.

Tool → Service → Repository chain (never shortcut):
  search_notes_tool       → RagService.answer()
  create_note_tool        → NoteService.create_note()
  update_note_tool        → NoteService.update_note()
  summarize_workspace_tool → RagService.answer() (broad query)

DB session for mutation tools:
  NoteService requires AsyncSession. Tools cannot accept it as a
  LLM-generated argument. Solution: contextvars.ContextVar injected
  by the graph node before calling the tool. Tool retrieves it from context.

IMPORT LAW: langchain_core.tools, ai.services.*, notes.service,
            ai.tools.schemas, config, stdlib, contextvars.
No FastAPI. No RequestContext. No SQLAlchemy raw imports.
"""
from __future__ import annotations

import contextvars
import logging
from typing import Any

from langchain_core.tools import StructuredTool

from ai.tools.schemas import (
    SearchNotesArgs, CreateNoteArgs, UpdateNoteArgs, SummarizeWorkspaceArgs
)
from config import get_settings

logger = logging.getLogger(__name__)

# ── DB session context variable ──────────────────────────────────────────────
# The graph's tool execution node sets this before calling mutation tools.
# This avoids passing AsyncSession as an LLM-generated argument (impossible).
db_session_var: contextvars.ContextVar = contextvars.ContextVar(
    "agent_db_session", default=None
)


# ── Tool implementations ─────────────────────────────────────────────────────

async def _search_notes(
    question: str,
    workspace_id: str,
    user_id: str,
    role: str,
) -> str:
    """
    Search the user's workspace notes using semantic retrieval.

    Use this tool when the user asks about content in their notes,
    wants to find specific information, or needs context from past writing.
    Always pass workspace_id, user_id, and role from the current agent state.
    """
    try:
        from ai.services.rag_service import get_rag_service
        rag = get_rag_service()
        result = await rag.answer(
            question=question,
            workspace_id=workspace_id,
            user_id=user_id,
            role=role,
        )
        return result.answer
    except Exception as e:
        logger.error("search_notes_tool failed", extra={"error": str(e)})
        return f"Search failed: {str(e)}"


async def _create_note(
    title: str,
    content: str,
    workspace_id: str,
    user_id: str,
    role: str,
) -> str:
    """
    Create a new note in the user's workspace.

    Use this tool when the user explicitly asks to create, write, or save
    a new note document. Always use workspace_id, user_id, and role from
    agent state — never guess or fabricate these values.
    Returns the new note's ID as confirmation.
    """
    db = db_session_var.get()
    if db is None:
        return "Error: database session not available for note creation."

    try:
        from notes.service import NoteService
        svc = NoteService()
        result = await svc.create_note(
            db,
            title=title,
            content=content,
            workspace_id=workspace_id,
            created_by=user_id,
            is_private=False,
        )
        return f"Note created successfully. ID: {result['note_id']}, Title: {result['title']}"
    except Exception as e:
        logger.error("create_note_tool failed", extra={"error": str(e)})
        return f"Note creation failed: {str(e)}"


async def _update_note(
    note_id: str,
    content: str,
    workspace_id: str,
    user_id: str,
    role: str,
) -> str:
    """
    Update the content of an existing note in the user's workspace.

    Use this tool when the user asks to edit, modify, or update a specific note.
    Requires a note_id — ask the user for it or find it via search_notes first.
    workspace_id is enforced — cannot modify notes from other workspaces.
    """
    db = db_session_var.get()
    if db is None:
        return "Error: database session not available for note update."

    try:
        from notes.service import NoteService
        svc = NoteService()
        result = await svc.update_note(
            db,
            note_id=note_id,
            content=content,
            workspace_id=workspace_id,
            updated_by=user_id,
        )
        return f"Note updated successfully. ID: {result['note_id']}"
    except Exception as e:
        logger.error("update_note_tool failed", extra={"error": str(e)})
        return f"Note update failed: {str(e)}"


async def _summarize_workspace(
    workspace_id: str,
    user_id: str,
    role: str,
) -> str:
    """
    Generate a high-level summary of the user's workspace notes.

    Use this tool when the user asks for an overview, digest, or summary
    of everything in their workspace. Returns a markdown summary.
    """
    try:
        from ai.services.rag_service import get_rag_service
        rag = get_rag_service()
        result = await rag.answer(
            question="Provide a comprehensive overview and summary of all the main topics, projects, and information covered in the workspace notes.",
            workspace_id=workspace_id,
            user_id=user_id,
            role=role,
            retrieval_limit=12,
        )
        return result.answer
    except Exception as e:
        logger.error("summarize_workspace_tool failed", extra={"error": str(e)})
        return f"Workspace summary failed: {str(e)}"


# ── StructuredTool instances ─────────────────────────────────────────────────

search_notes_tool = StructuredTool.from_function(
    coroutine=_search_notes,
    name="search_notes",
    description=(
        "Search the user's workspace notes for relevant information. "
        "Use when the user asks about content in their notes or wants to "
        "find specific information. Pass workspace_id, user_id, role from state."
    ),
    args_schema=SearchNotesArgs,
)

create_note_tool = StructuredTool.from_function(
    coroutine=_create_note,
    name="create_note",
    description=(
        "Create a new note document in the user's workspace. "
        "Use only when user explicitly asks to create or save a note. "
        "Pass workspace_id, user_id, role from state exactly as received."
    ),
    args_schema=CreateNoteArgs,
)

update_note_tool = StructuredTool.from_function(
    coroutine=_update_note,
    name="update_note",
    description=(
        "Update an existing note's content. "
        "Requires note_id — search for it first if unknown. "
        "Pass workspace_id, user_id, role from state exactly as received."
    ),
    args_schema=UpdateNoteArgs,
)

summarize_workspace_tool = StructuredTool.from_function(
    coroutine=_summarize_workspace,
    name="summarize_workspace",
    description=(
        "Generate a comprehensive summary of all workspace notes. "
        "Use when user asks for overview, digest, or workspace summary. "
        "Pass workspace_id, user_id, role from state exactly as received."
    ),
    args_schema=SummarizeWorkspaceArgs,
)


def get_note_tools() -> list[StructuredTool]:
    """Return all workspace tools. Called during graph compilation."""
    return [
        search_notes_tool,
        create_note_tool,
        update_note_tool,
        summarize_workspace_tool,
    ]

OUTPUT FORMAT:
Generate all files completely. Zero truncation.
```

**Validation:**
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
# Verify args_schema works
args = SearchNotesArgs(question='test', workspace_id='ws1', user_id='u1', role='member')
print(f'PASS: SearchNotesArgs validates: {args.question}')
print('PASS: all tool validations passed')
"
```

**Commit:**
```bash
git commit -am "feat(slice6.2): structured tools with args_schema, note_tools, tool schemas"
```

---

## Sub-step 6.3 — Graph State + Compilation

**Goal:**
- `AgentState` TypedDict with tenant primitives and safety counter
- `workspace_assistant.py` — graph nodes, conditional routing, compilation
- LiteLLM tool calling via OpenAI function definition format
- `db_session_var` set in tool node before mutation tools run
- Lazy initialization — compiled graph cached after first call

**Files to open in Cursor:**
- `src/ai/workflows/state.py` (create empty)
- `src/ai/workflows/workspace_assistant.py` (create empty)
- `src/ai/tools/note_tools.py` (reference — `db_session_var`)
- `src/ai/memory/checkpointer.py` (reference — `get_graph_checkpointer`)

---

```
ROLE: You are a senior backend engineer on DashNoteSystem.

OBJECTIVE: Sub-step 6.3 — Build AgentState, implement graph nodes with
LiteLLM tool calling, wire conditional routing with iteration guard,
and provide lazy-initialized compiled graph factory.

CONTEXT:
- LiteLLM tool calling: litellm.acompletion(model=..., tools=[...])
  tools parameter takes OpenAI function definition format (list of dicts).
  StructuredTool.as_openai_function_dict() or manual format — verify which works.
- Tool execution: ToolNode from langgraph.prebuilt handles tool dispatch.
  It calls the StructuredTool by name with the LLM-generated arguments.
- db_session_var: contextvars.ContextVar in ai.tools.note_tools.
  Set it in the tool_node execution so mutation tools can access the session.
- AgentState.messages: uses Annotated[list, add_messages] from langgraph.
  This enables automatic message accumulation across graph turns.
- Compilation: lazy — graph compiled once, cached in module variable.
  Never compiled at import time.

LAWS IN EFFECT:
- graph.compile() called INSIDE get_workspace_assistant() first call only
- get_graph_checkpointer() raises RuntimeError if checkpointer not initialized
  Handle this: if checkpointer unavailable, compile without checkpointer
  and log a warning (agent works without persistence — degraded mode)
- call_model node uses litellm.acompletion with tools= parameter
  NOT LangChain .bind_tools() — LiteLLM is not a LangChain LLM object
- steps_taken incremented in call_model node — checked in should_continue
- db session set via db_session_var in custom tool node wrapper

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 1 — src/ai/workflows/state.py (CREATE NEW)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Create this file completely:

"""
AgentState — the typed state envelope for the workspace assistant graph.

Every node in the graph reads from and writes to this state.
LangGraph merges state updates — nodes return partial state dicts.

messages uses add_messages reducer: each node appends to the list,
never replaces it. This is the correct LangGraph pattern.

Tenant fields (workspace_id, user_id, role) are immutable once set
in the initial state. Nodes read them but never write them.

steps_taken is incremented by call_model — guards against infinite loops.
"""
from __future__ import annotations

from typing import Annotated
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """
    Complete state for one agent conversation turn.

    Passed through every graph node. Nodes return partial dicts
    that LangGraph merges into the accumulated state.

    messages:     Conversation history. add_messages reducer appends
                  new messages rather than replacing the list.
    workspace_id: Injected at graph invocation — never modified by nodes.
    user_id:      Injected at graph invocation — never modified by nodes.
    role:         Injected at graph invocation — never modified by nodes.
    steps_taken:  Incremented by call_model. Checked by should_continue
                  to prevent infinite tool execution loops.
    thread_id:    Links to ai_threads product table (Slice 5).
                  Also used as LangGraph configurable thread_id.
    """
    messages: Annotated[list, add_messages]
    workspace_id: str
    user_id: str
    role: str
    steps_taken: int
    thread_id: str | None

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 2 — src/ai/workflows/workspace_assistant.py (CREATE NEW)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Create this file completely:

"""
Workspace assistant LangGraph graph — DashNoteSystem.

Graph topology:
  START → agent → (conditional) → tools → agent → ... → END

Nodes:
  agent:  Calls LiteLLM with tools available. Returns AI message.
  tools:  Executes tool calls from the AI message.

Routing (should_continue):
  "tools"  → agent called a tool — execute it and loop back
  "end"    → agent produced final answer — exit graph
  "limit"  → AGENT_MAX_ITERATIONS exceeded — force exit with warning

Safety:
  steps_taken incremented on every agent call.
  should_continue checks steps_taken before routing to tools.
  Maximum iterations: settings.AGENT_MAX_ITERATIONS (default 10).

LiteLLM tool calling:
  Tools registered as OpenAI function definitions (list of dicts).
  NOT LangChain bind_tools() — LiteLLM is not a LangChain LLM.
  Tool results added to messages as tool_result messages.

Compilation:
  compile_workspace_graph() called ONCE in get_workspace_assistant().
  Result cached in _compiled_graph module variable.
  Never compiled at import time.

IMPORT LAW: langgraph, langchain_core, litellm, ai.tools.*, ai.memory.*,
            config, stdlib only.
No FastAPI. No SQLAlchemy. No RequestContext.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import litellm
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from ai.workflows.state import AgentState
from ai.tools.note_tools import get_note_tools, db_session_var
from config import get_settings

logger = logging.getLogger(__name__)

# Module-level cache — set by get_workspace_assistant() on first call
_compiled_graph = None

# System prompt for the workspace assistant
WORKSPACE_ASSISTANT_PROMPT = """You are an active workspace assistant for DashNoteSystem.

You have access to tools that let you search, read, create, and update notes
inside the user's workspace. Use them when the user explicitly asks you to.

Critical rules:
1. ALWAYS pass workspace_id, user_id, and role exactly as they appear in your
   system context. Never modify, omit, or fabricate these values.
2. Use search_notes before answering questions about workspace content.
3. Use create_note only when explicitly asked to create or save a note.
4. Use update_note only when explicitly asked to modify an existing note.
5. Use summarize_workspace when asked for an overview of all notes.
6. If you cannot complete a task with available tools, say so clearly.
7. Never invent note IDs — search first to find real ones.
"""


async def call_model(state: AgentState) -> dict:
    """
    Agent node: call LiteLLM with tools available.

    Formats tools as OpenAI function definitions for LiteLLM.
    Injects tenant primitives into system prompt for tool guidance.
    Increments steps_taken as iteration safety counter.
    Returns partial state dict with updated messages and steps_taken.
    """
    settings = get_settings()
    tools = get_note_tools()

    # Format tools as OpenAI function definitions for LiteLLM
    openai_tools = [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.args_schema.model_json_schema(),
            },
        }
        for tool in tools
    ]

    # Build system message with tenant context injected
    system_content = (
        f"{WORKSPACE_ASSISTANT_PROMPT}\n\n"
        f"Current session context:\n"
        f"  workspace_id: {state['workspace_id']}\n"
        f"  user_id: {state['user_id']}\n"
        f"  role: {state['role']}\n"
        f"Always use these exact values in every tool call."
    )

    # Build messages array: system + conversation history
    messages = [
        {"role": "system", "content": system_content},
        *[
            {"role": m.type if hasattr(m, "type") else m.get("role", "user"),
             "content": m.content if hasattr(m, "content") else m.get("content", "")}
            for m in state["messages"]
        ],
    ]

    try:
        response = await litellm.acompletion(
            model=settings.LLM_MODEL,
            messages=messages,
            tools=openai_tools,
            tool_choice="auto",
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            timeout=settings.AGENT_TOOL_TIMEOUT,
        )
    except Exception as e:
        logger.error(
            "call_model failed",
            extra={"error": str(e), "workspace_id": state["workspace_id"]},
        )
        raise

    response_message = response.choices[0].message

    # Convert to LangChain AIMessage format for add_messages reducer
    tool_calls = None
    if hasattr(response_message, "tool_calls") and response_message.tool_calls:
        tool_calls = [
            {
                "id": tc.id,
                "name": tc.function.name,
                "args": json.loads(tc.function.arguments),
            }
            for tc in response_message.tool_calls
        ]

    ai_msg = AIMessage(
        content=response_message.content or "",
        tool_calls=tool_calls or [],
    )

    logger.debug(
        "call_model complete",
        extra={
            "workspace_id": state["workspace_id"],
            "steps_taken": state["steps_taken"] + 1,
            "has_tool_calls": bool(tool_calls),
        },
    )

    return {
        "messages": [ai_msg],
        "steps_taken": state["steps_taken"] + 1,
    }


async def execute_tools(state: AgentState) -> dict:
    """
    Tool execution node: run tools called by the agent.

    Sets db_session_var context variable before execution so
    mutation tools (create_note, update_note) can access the session.

    Note: db session is not available in the graph context at this point.
    Mutation tools return an error message if session is None.
    For full mutation support, the session must be passed through AgentState
    or injected via a closure — this is a known LangGraph limitation.
    See Slice 6.4 route layer for session injection pattern.
    """
    tools = get_note_tools()
    tool_map = {tool.name: tool for tool in tools}

    last_message = state["messages"][-1]
    if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
        return {"messages": []}

    tool_results = []
    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"] if isinstance(tool_call, dict) else tool_call.name
        tool_args = tool_call["args"] if isinstance(tool_call, dict) else tool_call.args
        tool_call_id = tool_call["id"] if isinstance(tool_call, dict) else tool_call.id

        tool = tool_map.get(tool_name)
        if tool is None:
            result = f"Unknown tool: {tool_name}"
        else:
            try:
                result = await tool.acoroutine(**tool_args)
            except Exception as e:
                logger.error(
                    "Tool execution failed",
                    extra={"tool": tool_name, "error": str(e)},
                )
                result = f"Tool {tool_name} failed: {str(e)}"

        tool_results.append(
            ToolMessage(content=str(result), tool_call_id=tool_call_id)
        )

    return {"messages": tool_results}


def should_continue(state: AgentState) -> str:
    """
    Conditional routing function — determines next node after agent call.

    Returns:
      "tools"  → agent has tool calls — execute them
      "end"    → agent produced final answer — exit
      "limit"  → AGENT_MAX_ITERATIONS exceeded — force exit
    """
    settings = get_settings()

    if state["steps_taken"] >= settings.AGENT_MAX_ITERATIONS:
        logger.warning(
            "Agent iteration limit reached",
            extra={
                "steps_taken": state["steps_taken"],
                "max_iterations": settings.AGENT_MAX_ITERATIONS,
                "workspace_id": state.get("workspace_id"),
            },
        )
        return "end"

    last_message = state["messages"][-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"

    return "end"


def compile_workspace_graph():
    """
    Compile the workspace assistant StateGraph.

    Called once by get_workspace_assistant(). Result cached.
    Attempts to use checkpointer — falls back to no persistence
    if checkpointer not initialized (degraded mode, logs warning).
    """
    graph = StateGraph(AgentState)

    graph.add_node("agent", call_model)
    graph.add_node("tools", execute_tools)

    graph.add_edge(START, "agent")
    graph.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END,
        },
    )
    graph.add_edge("tools", "agent")

    # Attempt to use checkpointer — non-fatal if unavailable
    try:
        from ai.memory.checkpointer import get_graph_checkpointer
        checkpointer = get_graph_checkpointer()
        compiled = graph.compile(checkpointer=checkpointer)
        logger.info("Workspace assistant graph compiled with checkpointer")
    except RuntimeError:
        logger.warning(
            "Checkpointer not available — compiling graph without persistence. "
            "Call init_checkpointer() in lifespan startup to enable."
        )
        compiled = graph.compile()

    return compiled


def get_workspace_assistant():
    """
    Return the compiled workspace assistant graph (singleton).

    Lazy initialization — compiled on first call, cached thereafter.
    Thread-safe for asyncio (single-threaded event loop).
    """
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = compile_workspace_graph()
    return _compiled_graph

OUTPUT FORMAT:
Generate both files completely. Zero truncation.
```

**Validation:**
```powershell
docker compose build api

docker compose exec -e PYTHONPATH=/app/src api python -c "
from ai.workflows.state import AgentState
from ai.workflows.workspace_assistant import should_continue, WORKSPACE_ASSISTANT_PROMPT
from langchain_core.messages import AIMessage
print('PASS: AgentState imported')
print('PASS: should_continue imported')
# Test routing logic
state = {'messages': [AIMessage(content='hello', tool_calls=[])], 'steps_taken': 0, 'workspace_id': 'w', 'user_id': 'u', 'role': 'member', 'thread_id': None}
route = should_continue(state)
print(f'PASS: no tool_calls → routes to: {route}')
assert route == 'end'
print('PASS: graph state and routing logic validated')
"
```

**Commit:**
```bash
git commit -am "feat(slice6.3): agent_state, workspace_assistant graph, conditional routing"
```

---

## Sub-step 6.4 — Agent Routes (NEW endpoints only)

**Goal:**
- `POST /ai/agent` — new endpoint, invokes graph synchronously
- `POST /ai/agent/stream` — streams graph execution events via SSE
- `POST /ai/chat` and `POST /ai/chat/stream` — NEVER touched
- Checkpointer initialized in `main.py` lifespan
- db session injected via `db_session_var` before graph execution

**Files to open in Cursor:**
- `src/ai_routes/agent.py` (create empty)
- `src/main.py` (reference — append only)
- `src/ai_routes/chat.py` (reference ONLY — never modify)

---

```
ROLE: You are a senior backend engineer on DashNoteSystem.

OBJECTIVE: Sub-step 6.4 — Create POST /ai/agent and POST /ai/agent/stream
as NEW endpoints. Existing /ai/chat routes are NEVER touched.
Wire checkpointer to main.py lifespan.

CONTEXT:
- POST /ai/chat → fast direct RAG (Slice 3) — NEVER replaced
- POST /ai/agent → new stateful agent via LangGraph graph
- Both coexist — users choose which path to use
- db session injected via db_session_var before graph.ainvoke()
- LangGraph config: {"configurable": {"thread_id": thread_id}}
  thread_id links to ai_threads (Slice 5) and LangGraph checkpoints
- graph.astream_events(state, config) yields LangGraph events for streaming
  Filter for "on_chat_model_stream" event type for token streaming
  Filter for "on_tool_start"/"on_tool_end" for tool execution events

LAWS IN EFFECT:
- src/ai_routes/chat.py is NEVER opened, NEVER modified
- POST /ai/agent lives in src/ai_routes/agent.py (new file)
- ctx frozen to primitives before any async call
- db session resolved in route handler scope — never inside generate()
- db_session_var set BEFORE graph.ainvoke() — mutation tools need it
- AgentResponse is a NEW schema — separate from ChatResponse
- main.py gets: init_checkpointer() in startup, close_checkpointer() in shutdown

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 1 — src/main.py (append to lifespan only)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Find the lifespan startup block in src/main.py.
Append AFTER existing startup logic (Qdrant init, ARQ pool, etc.):

    # --- AI Slice 6: LangGraph checkpointer ---
    try:
        from ai.memory.checkpointer import init_checkpointer
        await init_checkpointer()
        logger.info("LangGraph checkpointer ready")
    except Exception as e:
        logger.error("Checkpointer init failed — agent features degraded", extra={"error": str(e)})
        # Non-fatal: /ai/chat continues working, /ai/agent degrades gracefully

Find the lifespan shutdown block.
Append:

    # --- AI Slice 6: LangGraph checkpointer cleanup ---
    try:
        from ai.memory.checkpointer import close_checkpointer
        await close_checkpointer()
    except Exception:
        pass

Find where existing AI routers are registered.
Append:

    # --- AI Slice 6: Agent routes ---
    from ai_routes.agent import router as ai_agent_router
    app.include_router(ai_agent_router)

Show insertion locations with surrounding context.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 2 — src/ai_routes/agent.py (CREATE NEW)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Create this file completely:

"""
Agent routes for DashNoteSystem — LangGraph stateful workspace assistant.

POST /ai/agent        — invoke agent (waits for final answer)
POST /ai/agent/stream — stream agent execution events via SSE

These endpoints are SEPARATE from /ai/chat and /ai/chat/stream.
POST /ai/chat = fast direct RAG (always available, always fast)
POST /ai/agent = stateful LangGraph agent with tool calling

Both coexist. Users choose based on their need.

Security:
  workspace_id from JWT only — never from request body.
  ctx frozen to primitives before any async operation.
  db_session_var set before graph invocation for mutation tools.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.security.dependency import get_current_context
from core.security.context import RequestContext
from core.database.session import get_session
from ai.workflows.workspace_assistant import get_workspace_assistant
from ai.tools.note_tools import db_session_var
from ai.memory.service import ThreadService
from langchain_core.messages import AIMessage

router = APIRouter(prefix="/ai", tags=["ai-agent"])
logger = logging.getLogger(__name__)


# ── Request / Response schemas ────────────────────────────────────────────────

class AgentRequest(BaseModel):
    """Input for the agent endpoints."""
    message: str = Field(..., min_length=1, max_length=2000)
    thread_id: str | None = Field(
        default=None,
        description="Continue existing agent conversation. None = new thread.",
    )


class AgentResponse(BaseModel):
    """Output from POST /ai/agent."""
    answer: str
    thread_id: str
    steps_taken: int
    tool_calls_made: int


# ── Helper ────────────────────────────────────────────────────────────────────

async def _resolve_thread_id(
    thread_id: str | None,
    workspace_id: str,
    user_id: str,
    db: AsyncSession,
) -> str:
    """
    Return existing thread_id or create a new thread.
    Validates cross-workspace access before returning.
    """
    if thread_id:
        # Validate thread belongs to workspace (raises ValueError if not)
        svc = ThreadService()
        thread = await svc.get_or_create_thread(
            db,
            thread_id=thread_id,
            workspace_id=workspace_id,
            user_id=user_id,
        )
        return str(thread.id)

    # Create new thread for this agent conversation
    from ai_memory.repository import ThreadRepository
    repo = ThreadRepository()
    thread = await repo.create_thread(
        db,
        workspace_id=workspace_id,
        user_id=user_id,
        title=None,
    )
    return str(thread.id)


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/agent", response_model=AgentResponse)
async def agent_chat(
    body: AgentRequest,
    ctx: RequestContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_session),
) -> AgentResponse:
    """
    Invoke the workspace assistant agent.

    Unlike /ai/chat (fast RAG), this endpoint uses LangGraph for:
    - Multi-step reasoning with tool calls
    - Creating and updating notes on your behalf
    - Maintaining conversation state across turns
    - Looping until a complete answer is found

    Returns when the agent produces a final answer (no more tool calls).
    Use /ai/agent/stream to see execution progress in real time.
    """
    # Freeze context primitives
    workspace_id = str(ctx.workspace_id)
    user_id = str(ctx.user_id)
    role = ctx.role

    # Resolve thread
    try:
        resolved_thread_id = await _resolve_thread_id(
            body.thread_id, workspace_id, user_id, db
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Inject db session for mutation tools via contextvars
    token = db_session_var.set(db)

    try:
        graph = get_workspace_assistant()
        initial_state = {
            "messages": [{"role": "user", "content": body.message}],
            "workspace_id": workspace_id,
            "user_id": user_id,
            "role": role,
            "steps_taken": 0,
            "thread_id": resolved_thread_id,
        }
        config = {"configurable": {"thread_id": resolved_thread_id}}

        final_state = await graph.ainvoke(initial_state, config=config)

    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Agent unavailable: {str(e)}",
        )
    except Exception as e:
        logger.error(
            "Agent invocation failed",
            extra={"workspace_id": workspace_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Agent encountered an error. Try /ai/chat for direct RAG.",
        )
    finally:
        # Always reset the context variable
        db_session_var.reset(token)

    # Extract final answer from last AI message
    final_answer = ""
    tool_calls_made = 0
    for msg in reversed(final_state["messages"]):
        if isinstance(msg, AIMessage):
            if not msg.tool_calls:
                final_answer = msg.content
                break
            tool_calls_made += len(msg.tool_calls)

    return AgentResponse(
        answer=final_answer or "Agent completed without producing a final answer.",
        thread_id=resolved_thread_id,
        steps_taken=final_state.get("steps_taken", 0),
        tool_calls_made=tool_calls_made,
    )


@router.post("/agent/stream", response_class=StreamingResponse)
async def agent_chat_stream(
    body: AgentRequest,
    ctx: RequestContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    """
    Stream agent execution events via SSE.

    Events:
      {"type": "token", "content": "..."}         — LLM text tokens
      {"type": "tool_start", "tool": "...", "args": {...}}  — tool beginning
      {"type": "tool_end", "tool": "...", "result": "..."}  — tool result
      {"type": "done", "thread_id": "...", "steps_taken": N} — completion
      {"type": "error", "message": "..."}         — error

    Nginx note: X-Accel-Buffering: no required for streaming through proxy.
    """
    # Freeze context before generator
    workspace_id = str(ctx.workspace_id)
    user_id = str(ctx.user_id)
    role = ctx.role

    # Resolve thread before generator (db available here)
    try:
        resolved_thread_id = await _resolve_thread_id(
            body.thread_id, workspace_id, user_id, db
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Capture for closure — never reference ctx inside generate()
    message = body.message

    async def generate():
        token = db_session_var.set(db)
        try:
            graph = get_workspace_assistant()
            initial_state = {
                "messages": [{"role": "user", "content": message}],
                "workspace_id": workspace_id,
                "user_id": user_id,
                "role": role,
                "steps_taken": 0,
                "thread_id": resolved_thread_id,
            }
            config = {
                "configurable": {"thread_id": resolved_thread_id},
                "stream_mode": "events",   # enable event streaming
            }

            steps = 0
            async for event in graph.astream_events(
                initial_state, config=config, version="v2"
            ):
                kind = event.get("event", "")
                data = event.get("data", {})

                if kind == "on_chat_model_stream":
                    chunk = data.get("chunk", {})
                    content = ""
                    if hasattr(chunk, "content"):
                        content = chunk.content
                    elif isinstance(chunk, dict):
                        content = chunk.get("content", "")
                    if content:
                        yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"

                elif kind == "on_tool_start":
                    yield f"data: {json.dumps({'type': 'tool_start', 'tool': event.get('name', ''), 'args': data.get('input', {})})}\n\n"

                elif kind == "on_tool_end":
                    result = data.get("output", "")
                    yield f"data: {json.dumps({'type': 'tool_end', 'tool': event.get('name', ''), 'result': str(result)[:200]})}\n\n"

                elif kind == "on_chain_end" and event.get("name") == "LangGraph":
                    output = data.get("output", {})
                    steps = output.get("steps_taken", 0)

            yield f"data: {json.dumps({'type': 'done', 'thread_id': resolved_thread_id, 'steps_taken': steps})}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error("Agent stream failed", extra={"error": str(e)})
            yield f"data: {json.dumps({'type': 'error', 'message': 'Agent stream failed. Try /ai/chat for direct RAG.'})}\n\n"
            yield "data: [DONE]\n\n"
        finally:
            db_session_var.reset(token)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )

OUTPUT FORMAT:
Task 1: exact lines and insertion locations only.
Task 2: complete file, zero truncation.
```

**Validation — Slice 6 Gate:**
```powershell
docker compose up -d --build api

# GATE 1 — Checkpointer initialized on startup:
docker compose logs api --tail 30
# Expected: "LangGraph checkpointer ready"
# Check DB: docker compose exec db psql -U dashuser -d dashnotes -c "\dt checkpoint*"
# Expected: checkpoints, checkpoint_blobs, checkpoint_writes tables

# GATE 2 — Existing chat still works (NEVER broken by Slice 6):
Invoke-RestMethod -Uri "http://127.0.0.1/ai/chat" `
  -Method Post -Headers @{ Authorization = "Bearer <TOKEN>" } `
  -ContentType "application/json" -Body '{"message": "test"}'
# Expected: same JSON response as Slice 3/4 — unchanged

# GATE 3 — Agent endpoint works:
$resp = Invoke-RestMethod -Uri "http://127.0.0.1/ai/agent" `
  -Method Post -Headers @{ Authorization = "Bearer <TOKEN>" } `
  -ContentType "application/json" `
  -Body '{"message": "What is in my workspace notes?", "thread_id": null}'
$resp  # Inspect response
# Expected: answer populated, thread_id non-null UUID, steps_taken >= 1

# GATE 4 — Multi-step tool use:
Invoke-RestMethod -Uri "http://127.0.0.1/ai/agent" `
  -Method Post -Headers @{ Authorization = "Bearer <TOKEN>" } `
  -ContentType "application/json" `
  -Body '{"message": "Search my notes and create a summary note titled AI Workspace Synopsis"}'
# Expected: tool_calls_made >= 2 (search + create)
# Verify note created:
docker compose exec db psql -U dashuser -d dashnotes -c "SELECT id, title FROM notes WHERE title = 'AI Workspace Synopsis';"

# GATE 5 — Conversation continues with thread_id:
$thread = $resp.thread_id
Invoke-RestMethod -Uri "http://127.0.0.1/ai/agent" `
  -Method Post -Headers @{ Authorization = "Bearer <TOKEN>" } `
  -ContentType "application/json" `
  -Body "{`"message`": `"What did I just ask you?`", `"thread_id`": `"$thread`"}"
# Expected: agent references the previous question — history loaded

# GATE 6 — Streaming agent:
curl.exe -sS -X POST http://127.0.0.1/ai/agent/stream `
  -H "Authorization: Bearer <TOKEN>" `
  -H "Content-Type: application/json" `
  -d '{"message": "Summarize my workspace"}' --no-buffer
# Expected: tool_start events, token events, done event with steps_taken

# GATE 7 — Cross-workspace isolation:
# Pass thread_id from Workspace A using Workspace B token
# Expected: 400 Bad Request with workspace mismatch error

# GATE 8 — Iteration limit respected:
# Agent cannot exceed AGENT_MAX_ITERATIONS=10 steps
# Check: docker compose logs api | grep "iteration limit"
```

**Commit:**
```bash
git commit -am "feat(slice6.4): post /ai/agent + stream, checkpointer lifespan, slice 6 complete"
```

---

## Slice 6 Complete — What Was Built

```
src/notes/service.py                  ← NoteService over notes/repository.py
src/ai/memory/checkpointer.py         ← AsyncPostgresSaver, psycopg3, singleton
src/ai/tools/__init__.py
src/ai/tools/schemas.py               ← Pydantic args_schema per tool
src/ai/tools/note_tools.py            ← StructuredTool definitions, db_session_var
src/ai/workflows/state.py             ← AgentState TypedDict
src/ai/workflows/workspace_assistant.py ← graph nodes, routing, compilation
src/ai_routes/agent.py                ← POST /ai/agent + /ai/agent/stream
src/main.py                           ← init/close checkpointer, agent router (3 lines)
requirements.txt                      ← psycopg[async] added
settings                              ← AGENT_MAX_ITERATIONS, AGENT_TOOL_TIMEOUT
```

```
What was NEVER touched (critical):
  src/ai_routes/chat.py               ← POST /ai/chat unchanged
  src/ai/services/rag_service.py      ← RagService unchanged
  src/ai_routes/threads.py            ← Thread routes unchanged
  Any existing slice 1-5 code         ← All working features preserved

Two paths now coexist:
  POST /ai/chat        → fast RAG (< 2s, no tools, always works)
  POST /ai/agent       → stateful agent (3-15s, tools, LangGraph)

What is NOT in Slice 6 (correct — later slices):
  ✗ Multi-agent supervisor (Slice 9)
  ✗ ResearchAgent, AutomationAgent (Slice 9)
  ✗ Neo4j GraphRAG (Slice 8)
  ✗ LangSmith active tracing (Slice 10 — flip LANGSMITH_TRACING_ENABLED=true)
```

---

> **Next:** Slice 7 — Automation
> `FileUploadedEvent` and `NoteCreatedEvent` trigger intelligent background workflows.
> Worker automation tasks: extract text → embed → summarize → auto-tag.
> Human approval gate for destructive agent actions.
> pypdf + python-docx installed here — not before.