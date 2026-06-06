# Slice 5 — Memory: Conversation Persistence
## Final Cursor Prompts (3 Sub-steps, Production-Grade, SQLAlchemy Async)

> **Context carried from previous slices**
> - Slice 4 gate passed: `POST /ai/chat/stream` streams tokens progressively ✅
> - `RagService.answer()` and `stream_answer()` in `src/ai/services/rag_service.py`
> - Auth context: `core/security/context.py` → `RequestContext`
> - DB session: `core/database/session.py` → `get_session()` → `AsyncSession`
> - Existing mixins: `core/database/mixins.py` → `TimestampMixin`, `WorkspaceTenantMixin`
> - Existing base: wherever your existing models inherit from (check `src/notes/models.py`)
> - Import style: `from config import settings` (never `from src.config`)
> - Migration tool: Alembic — `alembic revision --autogenerate` then `alembic upgrade head`
> - Pattern to follow: `src/notes/repository.py` — stateless, session per method

---

## ARCHITECTURE LAW
### Paste as your FIRST message in every Cursor Composer session.

```
ARCHITECTURE LAW — DashNoteSystem. Enforce in ALL generated code.

MODULE PATHS:
  Import as: from config import settings, get_settings
             from core.database.session import get_session
             from core.security.context import RequestContext
             from ai_memory.models import AIThread, AIMessage
             from ai_memory.repository import ThreadRepository
             from ai.memory.service import ThreadService
             from ai.memory.context_builder import ContextBuilder
  NEVER as:  from src.config import ...
             from src.ai_memory import ...

SQLALCHEMY LAW:
  - AI domain models (ai_threads, ai_messages) live in src/ai_memory/models.py
  - src/ai/memory/ contains ONLY service logic, context building — NO ORM models
  - src/ai/* MUST NEVER import SQLAlchemy directly
  - AsyncSession is NEVER stored on a class — passed per method call
  - Follow the pattern in src/notes/repository.py exactly

AI SERVICE LAW — src/ai/memory/* MUST NEVER import:
  - FastAPI, Request, Response, HTTPException, APIRouter, Depends
  - SQLAlchemy (use repository pattern — session injected as parameter)
  - RequestContext (accept workspace_id, user_id as plain strings)
  - src/notes/*, src/files/*, src/auth/*, src/workspaces/*

MIGRATION LAW:
  - Tables created via Alembic only — never engine.create_all() or auto-migrate
  - Generate: alembic revision --autogenerate -m "add ai_threads ai_messages"
  - Apply: alembic upgrade head (via migrate service or direct)
  - Import new models in alembic/env.py so autogenerate detects them

MODIFICATION LAW for Slice 5:
  - answer() and stream_answer() get MINIMAL signature change only
  - Add thread_id: str | None = None as keyword argument
  - Extract _build_messages_with_history() as a NEW private method
  - answer() and stream_answer() CALL the new method — not rewritten
  - Never let Cursor rewrite the full method body

ROUTER LAW:
  - ChatRequest gets thread_id: str | None = None appended
  - ChatResponse gets thread_id: str | None = None appended
  - POST /ai/chat and /ai/chat/stream handlers get minimal addition
  - New routes: GET /ai/threads, GET /ai/threads/{id}/messages
  - All new routes in src/ai_routes/threads.py (new file)
  - Never touch notes/router.py

LANGGRAPH NOTE:
  - Install langgraph now — used in Slice 6
  - AsyncPostgresSaver from langgraph is NOT used in Slice 5
  - Slice 5 uses plain SQL for conversation persistence
  - ai_threads + ai_messages are the PRODUCT layer (what user sees)
  - LangGraph checkpointer is the EXECUTION layer (Slice 6 only)

Acknowledge these laws before writing any code.
```

---

## Sub-step 5.1 — Database Layer

**Goal:**
- `langgraph` installed in requirements.txt
- `AI_THREAD_MESSAGE_LIMIT` setting appended
- `AIThread` and `AIMessage` SQLAlchemy models created in `src/ai_memory/`
- `ThreadRepository` created — stateless, session per method, follows `notes/repository.py`
- Alembic migration generated and applied
- Tables confirmed in database

**Files to open in Cursor:**
- `requirements.txt`
- `src/config/settings.py` (or `src/config.py`)
- `src/notes/models.py` (reference — to match base class pattern)
- `src/notes/repository.py` (reference — to match repository pattern)
- `src/ai_memory/models.py` (create empty)
- `src/ai_memory/repository.py` (create empty)

---

```
ROLE: You are a senior backend engineer on DashNoteSystem.

OBJECTIVE: Sub-step 5.1 — Install langgraph, append memory settings,
create AIThread and AIMessage SQLAlchemy models, and build a stateless
ThreadRepository following the existing notes/repository.py pattern.

CONTEXT:
- Existing model base class: check src/notes/models.py to find what
  Base class and mixins are used (likely TimestampMixin, WorkspaceTenantMixin
  from core/database/mixins.py). Use the EXACT same pattern.
- Existing repository pattern: src/notes/repository.py — stateless class,
  AsyncSession passed per method, workspace_id filter on every query.
  Match this pattern exactly for ThreadRepository.
- Migration tool: Alembic with autogenerate. Models must be imported
  in alembic/env.py for autogenerate to detect them.
- Database: PostgreSQL with asyncpg driver.

LAWS IN EFFECT:
- src/ai_memory/ is a NEW top-level module inside src/
  (same level as src/notes/, src/files/, etc.)
- SQLAlchemy models NEVER go inside src/ai/
- AsyncSession is NEVER stored on a class instance
- Follow notes/repository.py pattern — not ThreadManager with session in __init__
- Append-only to requirements.txt and settings

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 1 — requirements.txt (append-only)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Read requirements.txt. Check if langgraph is present.
If NOT present, append under:

# --- AI Slice 5: Memory + LangGraph prep ---
langgraph>=0.1.0
langgraph-checkpoint-postgres>=0.1.0

Do NOT add any other packages. SQLAlchemy, asyncpg, pydantic already present.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 2 — Settings (append-only)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Read Settings class. Append if not present:

    # ── AI Slice 5: Memory ──────────────────────────────────────────
    AI_THREAD_MESSAGE_LIMIT: int = 20   # recent messages loaded into context

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 3 — src/ai_memory/__init__.py (CREATE NEW)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""AI conversation memory persistence layer — DashNoteSystem."""

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 4 — src/ai_memory/models.py (CREATE NEW)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Read src/notes/models.py first to identify:
  - The exact Base class used (e.g. from core.database.base import Base)
  - The exact mixins used (e.g. TimestampMixin, WorkspaceTenantMixin)
  - The UUID column pattern (e.g. sa.UUID with gen_random_uuid())
  - How created_at/updated_at are defined

Then create src/ai_memory/models.py matching that EXACT style:

"""
SQLAlchemy models for AI conversation persistence.

Tables:
  ai_threads  — conversation threads (one per user conversation)
  ai_messages — individual messages within a thread

These are the PRODUCT layer — what the user sees in the UI.
LangGraph's AsyncPostgresSaver (Slice 6) creates its own internal tables.
Both layers are linked only by thread_id string — never via FK.

IMPORT LAW: Only SQLAlchemy, stdlib, and project base/mixins.
No ai.*, no FastAPI, no pydantic business logic here.
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, TEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Import Base and mixins matching the pattern in src/notes/models.py
# FILL IN: use whatever Base and mixins exist in your project
from core.database.base import Base          # adjust if different
from core.database.mixins import TimestampMixin   # adjust if different


class AIThread(TimestampMixin, Base):
    """
    A conversation thread between a user and the AI assistant.

    workspace_id scopes threads to a workspace — cross-workspace access
    is rejected at the repository layer (workspace_id filter on every query).
    created_by is the user who started the thread.

    LangGraph link: thread.id (as string) becomes the LangGraph thread_id
    in Slice 6. No FK — just string linking.
    """
    __tablename__ = "ai_threads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    title: Mapped[str | None] = mapped_column(TEXT, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        default=True,
        server_default=sa.text("true"),
    )

    # Relationship — cascade delete messages when thread is deleted
    messages: Mapped[list["AIMessage"]] = relationship(
        "AIMessage",
        back_populates="thread",
        cascade="all, delete-orphan",
        lazy="noload",   # always load explicitly — never lazy load in async
    )

    def __repr__(self) -> str:
        return f"<AIThread id={self.id} workspace={self.workspace_id}>"


class AIMessage(Base):
    """
    A single message in a conversation thread.

    role must be one of: 'user', 'assistant', 'tool'
    citations stores the note references used to generate the assistant response.
    token_count is approximate — used for context budget calculations.
    """
    __tablename__ = "ai_messages"

    # Check constraint enforced at DB level — not just application level
    VALID_ROLES = ("user", "assistant", "tool")

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )
    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("ai_threads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        sa.String(20),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(TEXT, nullable=False)
    citations: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=sa.text("'[]'::jsonb"),
    )
    token_count: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )

    # DB-level role check
    __table_args__ = (
        sa.CheckConstraint(
            "role IN ('user', 'assistant', 'tool')",
            name="ai_messages_role_check",
        ),
        sa.Index("idx_ai_messages_thread_created", "thread_id", "created_at"),
    )

    thread: Mapped["AIThread"] = relationship(
        "AIThread",
        back_populates="messages",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<AIMessage id={self.id} role={self.role} thread={self.thread_id}>"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 5 — src/ai_memory/repository.py (CREATE NEW)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Read src/notes/repository.py carefully to match the EXACT style.
Then create src/ai_memory/repository.py:

"""
ThreadRepository — data access for ai_threads and ai_messages.

Follows the same stateless repository pattern as src/notes/repository.py.
AsyncSession is passed per method — never stored on the instance.
workspace_id filter is applied on EVERY query — no exceptions.

IMPORT LAW: SQLAlchemy, ai_memory.models, stdlib only.
No FastAPI. No RequestContext. No business logic — only data access.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from ai_memory.models import AIThread, AIMessage

logger = logging.getLogger(__name__)


class ThreadRepository:
    """
    Stateless repository for ai_threads and ai_messages.

    Every method receives AsyncSession as first argument.
    workspace_id is always applied as a filter — cross-workspace
    access is structurally impossible through this class.

    Usage (from service layer):
        repo = ThreadRepository()
        thread = await repo.create_thread(db, workspace_id=..., user_id=...)
    """

    async def create_thread(
        self,
        db: AsyncSession,
        *,
        workspace_id: str,
        user_id: str,
        title: str | None = None,
    ) -> AIThread:
        """Create a new conversation thread."""
        thread = AIThread(
            workspace_id=uuid.UUID(workspace_id),
            created_by=uuid.UUID(user_id),
            title=title,
            is_active=True,
        )
        db.add(thread)
        await db.commit()
        await db.refresh(thread)
        logger.info(
            "Thread created",
            extra={"thread_id": str(thread.id), "workspace_id": workspace_id},
        )
        return thread

    async def get_thread(
        self,
        db: AsyncSession,
        *,
        thread_id: str,
        workspace_id: str,
    ) -> AIThread | None:
        """
        Fetch a thread by ID — returns None if not found OR wrong workspace.
        workspace_id filter prevents cross-tenant access structurally.
        """
        result = await db.execute(
            sa.select(AIThread).where(
                AIThread.id == uuid.UUID(thread_id),
                AIThread.workspace_id == uuid.UUID(workspace_id),
                AIThread.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def list_threads(
        self,
        db: AsyncSession,
        *,
        workspace_id: str,
        user_id: str,
        limit: int = 50,
    ) -> list[AIThread]:
        """
        List active threads for a user in a workspace.
        Filters by both workspace_id AND created_by — users see only their threads.
        Owners/admins who need to see all threads should use a separate admin method.
        """
        result = await db.execute(
            sa.select(AIThread)
            .where(
                AIThread.workspace_id == uuid.UUID(workspace_id),
                AIThread.created_by == uuid.UUID(user_id),
                AIThread.is_active.is_(True),
            )
            .order_by(AIThread.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_recent_messages(
        self,
        db: AsyncSession,
        *,
        thread_id: str,
        workspace_id: str,
        limit: int = 20,
    ) -> list[AIMessage]:
        """
        Load recent messages for a thread — workspace_id verified via thread lookup.

        Security: thread must belong to workspace_id or returns empty list.
        Messages ordered ASC (oldest first) for correct LLM context order.
        """
        # Verify thread belongs to this workspace
        thread = await self.get_thread(db, thread_id=thread_id, workspace_id=workspace_id)
        if thread is None:
            logger.warning(
                "Thread not found or workspace mismatch",
                extra={"thread_id": thread_id, "workspace_id": workspace_id},
            )
            return []

        result = await db.execute(
            sa.select(AIMessage)
            .where(AIMessage.thread_id == uuid.UUID(thread_id))
            .order_by(AIMessage.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def save_message(
        self,
        db: AsyncSession,
        *,
        thread_id: str,
        role: str,
        content: str,
        citations: list[dict] | None = None,
        token_count: int | None = None,
    ) -> AIMessage:
        """
        Save a message to the thread.
        role must be 'user', 'assistant', or 'tool' — enforced at DB level.
        """
        message = AIMessage(
            thread_id=uuid.UUID(thread_id),
            role=role,
            content=content,
            citations=citations or [],
            token_count=token_count,
        )
        db.add(message)
        await db.commit()
        await db.refresh(message)
        return message

    async def update_thread_title(
        self,
        db: AsyncSession,
        *,
        thread_id: str,
        workspace_id: str,
        title: str,
    ) -> bool:
        """Update thread title — workspace_id verified before update."""
        result = await db.execute(
            sa.update(AIThread)
            .where(
                AIThread.id == uuid.UUID(thread_id),
                AIThread.workspace_id == uuid.UUID(workspace_id),
            )
            .values(title=title, updated_at=datetime.now(timezone.utc))
        )
        await db.commit()
        return result.rowcount > 0

    async def delete_thread(
        self,
        db: AsyncSession,
        *,
        thread_id: str,
        workspace_id: str,
    ) -> bool:
        """
        Soft-delete a thread (sets is_active=False).
        workspace_id verified — cannot delete threads from other workspaces.
        Messages are preserved for audit — hard delete if needed separately.
        """
        result = await db.execute(
            sa.update(AIThread)
            .where(
                AIThread.id == uuid.UUID(thread_id),
                AIThread.workspace_id == uuid.UUID(workspace_id),
                AIThread.is_active.is_(True),
            )
            .values(is_active=False, updated_at=datetime.now(timezone.utc))
        )
        await db.commit()
        deleted = result.rowcount > 0
        if deleted:
            logger.info(
                "Thread soft-deleted",
                extra={"thread_id": thread_id, "workspace_id": workspace_id},
            )
        return deleted

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 6 — Alembic migration instructions
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Show me:
1. The exact line to add to alembic/env.py to import the new models
   so autogenerate detects them:
   from ai_memory.models import AIThread, AIMessage  # noqa: F401

2. The exact commands to run:
   docker compose run --rm migrate alembic revision --autogenerate -m "add_ai_threads_ai_messages"
   docker compose run --rm migrate alembic upgrade head

3. The verification command:
   docker compose exec db psql -U <user> -d <dbname> -c "\dt ai_*"
   Expected: ai_messages and ai_threads listed

OUTPUT FORMAT:
Complete file content for each task.
Label each:
  === FILE: <path> ===
  === ACTION: create | append ===
Zero truncation.
```

**Validation:**
```powershell
# Step 1: Import new models in alembic/env.py, then:
docker compose run --rm migrate alembic revision --autogenerate -m "add_ai_threads_ai_messages"
# Expected: new file in alembic/versions/ with ai_threads and ai_messages tables

docker compose run --rm migrate alembic upgrade head
# Expected: migration runs without error

# Step 2: Verify tables exist:
docker compose exec db psql -U dashuser -d dashnotes -c "\dt ai_*"
# Expected:
#   ai_messages
#   ai_threads

# Step 3: Verify constraints:
docker compose exec db psql -U dashuser -d dashnotes -c "\d ai_messages"
# Expected: role check constraint visible, thread_id FK with CASCADE

# Step 4: Build cleanly:
docker compose build api
```

**Commit:**
```bash
git commit -am "feat(slice5.1): ai_threads + ai_messages models, ThreadRepository, alembic migration"
```

---

## Sub-step 5.2 — Memory Service + Context Builder

**Goal:**
- `ThreadService` — thin business logic layer over `ThreadRepository`
- `ContextBuilder` — builds LiteLLM message array from history + notes, enforces budget
- `answer()` and `stream_answer()` get minimal `thread_id` parameter — not rewritten
- Private `_load_thread_context()` extracted — called by both methods
- Conversation persisted after each response

**Files to open in Cursor:**
- `src/ai/memory/service.py` (create empty)
- `src/ai/memory/context_builder.py` (create empty)
- `src/ai/services/rag_service.py` (minimal additions only)
- `src/ai/prompts/rag.py` (reference only — no changes)
- `src/ai_memory/repository.py` (reference)

---

```
ROLE: You are a senior backend engineer on DashNoteSystem.

OBJECTIVE: Sub-step 5.2 — Build ThreadService and ContextBuilder,
then make MINIMAL additions to RagService for thread_id support.

CONTEXT:
- ThreadRepository is in src/ai_memory/repository.py (Slice 5.1)
- RagService is in src/ai/services/rag_service.py
  answer() and stream_answer() must NOT be rewritten
  Only: add thread_id param, add call to _load_thread_context()
- ContextBuilder assembles LiteLLM messages array:
  [system_instruction, ...history_messages, user_message]
  Token budget: historical chars + context_chunks chars <= TOKEN_BUDGET_PER_REQUEST
- AsyncSession is injected per call — never stored on service instance
- RAG_SYSTEM_INSTRUCTION unchanged — no streaming variant needed

LAWS IN EFFECT:
- src/ai/memory/*.py imports NO SQLAlchemy, NO ORM models directly
  It uses ThreadRepository — repository abstracts the DB layer
- src/ai/memory/*.py imports NO FastAPI, NO RequestContext
- RagService modifications: MINIMAL — two things only:
  1. Add thread_id: str | None = None to both method signatures
  2. Add call to self._load_thread_context() at the start of each method
  The method BODIES are NOT rewritten
- AsyncSession passed as parameter to service methods — never imported
  into rag_service.py directly. Session comes from route layer.
- ChatResult gets thread_id: str | None = None appended (not modified)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 1 — src/ai/memory/__init__.py (CREATE NEW)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""AI memory service layer — context building and thread management."""

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 2 — src/ai/memory/context_builder.py (CREATE NEW)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Create this file completely:

"""
ContextBuilder — assembles the LiteLLM messages array for RAG conversations.

Combines:
  - System instruction (RAG_SYSTEM_INSTRUCTION)
  - Historical messages from ai_messages table (recent N messages)
  - Current context chunks from Qdrant retrieval
  - Current user question

Token budget enforcement:
  historical_chars + context_chars <= TOKEN_BUDGET_PER_REQUEST
  Historical messages are loaded first, then context chunks fill
  the remaining budget. If budget is exhausted by history,
  context chunks are reduced, never eliminated entirely (min 1 chunk).

IMPORT LAW: Only stdlib, config, ai.prompts.rag — no SQLAlchemy, no FastAPI.
AsyncSession is never imported here — history is passed as pre-loaded list.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from config import get_settings
from ai.prompts.rag import RAG_SYSTEM_INSTRUCTION, build_rag_user_message

logger = logging.getLogger(__name__)


@dataclass
class BuiltContext:
    """Result of ContextBuilder.build() — ready to pass to litellm.acompletion()."""
    messages: list[dict]        # full LiteLLM messages array
    context_chunks: list[dict]  # chunks that made it into budget (for citation grounding)
    history_messages_used: int
    context_chunks_used: int
    total_chars: int


class ContextBuilder:
    """
    Assembles the LiteLLM messages array respecting the token budget.

    Usage:
        builder = ContextBuilder()
        built = builder.build(
            question="What is the deadline?",
            history_messages=[{"role": "user", "content": "..."}, ...],
            retrieved_chunks=[{"chunk_id": "...", "text": "...", ...}, ...],
        )
        response = await litellm.acompletion(messages=built.messages, ...)
    """

    def build(
        self,
        *,
        question: str,
        history_messages: list[dict],
        retrieved_chunks: list[dict],
    ) -> BuiltContext:
        """
        Build the full messages array for a RAG conversation turn.

        Message order (required for correct LLM context):
          1. System instruction
          2. Historical messages (oldest first, budget-trimmed from oldest)
          3. Retrieved context as user message
          4. Current user question (if context present, merged with context)

        Budget strategy:
          - Historical messages consume budget from oldest first
          - Context chunks consume remaining budget
          - At least 1 context chunk always included if available
          - If history alone exceeds budget, trim oldest messages

        Args:
            question:          Current user question.
            history_messages:  List of {"role": str, "content": str} dicts,
                               ordered oldest first (from ThreadRepository).
            retrieved_chunks:  List of chunk dicts from WorkspaceVectorSearch.
        """
        settings = get_settings()
        budget = settings.TOKEN_BUDGET_PER_REQUEST

        # Step 1: fit historical messages into budget
        # Trim oldest messages first if history is too long
        fitted_history: list[dict] = []
        history_chars = 0

        # Reserve at least 30% of budget for context chunks
        history_budget = int(budget * 0.7)

        for msg in history_messages:
            msg_chars = len(msg.get("content", ""))
            if history_chars + msg_chars > history_budget:
                break
            fitted_history.append({"role": msg["role"], "content": msg["content"]})
            history_chars += msg_chars

        # Step 2: fit context chunks into remaining budget
        remaining_budget = budget - history_chars
        fitted_chunks: list[dict] = []
        context_chars = 0

        for chunk in retrieved_chunks:
            chunk_chars = len(chunk.get("text", ""))
            if context_chars + chunk_chars > remaining_budget and fitted_chunks:
                # At least 1 chunk always included — never send LLM with zero context
                break
            fitted_chunks.append(chunk)
            context_chars += chunk_chars

        # Step 3: build user message (context + question merged)
        user_content = build_rag_user_message(question, fitted_chunks)

        # Step 4: assemble final messages array
        messages: list[dict] = [
            {"role": "system", "content": RAG_SYSTEM_INSTRUCTION},
            *fitted_history,
            {"role": "user", "content": user_content},
        ]

        logger.debug(
            "Context built",
            extra={
                "history_messages_used": len(fitted_history),
                "context_chunks_used": len(fitted_chunks),
                "total_chars": history_chars + context_chars,
                "budget": budget,
            },
        )

        return BuiltContext(
            messages=messages,
            context_chunks=fitted_chunks,
            history_messages_used=len(fitted_history),
            context_chunks_used=len(fitted_chunks),
            total_chars=history_chars + context_chars,
        )

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 3 — src/ai/memory/service.py (CREATE NEW)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Create this file completely:

"""
ThreadService — business logic layer for conversation threads.

Thin layer over ThreadRepository. Handles:
  - Thread creation with automatic title generation
  - Loading history for context injection
  - Persisting messages after each response
  - Workspace isolation enforcement

IMPORT LAW: ai_memory.repository, config, stdlib only.
No SQLAlchemy imports. No FastAPI. No RequestContext.
AsyncSession passed per method — never stored.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ai_memory.repository import ThreadRepository
from config import get_settings

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from ai_memory.models import AIThread, AIMessage

logger = logging.getLogger(__name__)

# Module-level singleton repository
_repo = ThreadRepository()


class ThreadService:
    """
    Business logic for conversation thread management.

    All methods accept AsyncSession as first parameter — never stored.
    workspace_id is enforced on every operation via ThreadRepository.

    LangGraph note (Slice 6):
        This service manages the PRODUCT layer (what users see).
        LangGraph's AsyncPostgresSaver manages the EXECUTION layer.
        They are linked only by thread_id string — no FK or direct coupling.
    """

    async def get_or_create_thread(
        self,
        db: "AsyncSession",
        *,
        thread_id: str | None,
        workspace_id: str,
        user_id: str,
    ) -> "AIThread":
        """
        Return existing thread or create a new one.

        If thread_id is provided: verify it belongs to workspace_id.
        If thread_id is None: create a new thread.
        Security: thread from wrong workspace raises ValueError.
        """
        if thread_id:
            thread = await _repo.get_thread(
                db,
                thread_id=thread_id,
                workspace_id=workspace_id,
            )
            if thread is None:
                raise ValueError(
                    f"Thread {thread_id} not found or does not belong to workspace {workspace_id}. "
                    "Cross-workspace thread access is not permitted."
                )
            return thread

        # Create new thread
        return await _repo.create_thread(
            db,
            workspace_id=workspace_id,
            user_id=user_id,
        )

    async def load_history_as_messages(
        self,
        db: "AsyncSession",
        *,
        thread_id: str,
        workspace_id: str,
    ) -> list[dict]:
        """
        Load recent messages formatted for LiteLLM messages array.

        Returns list of {"role": str, "content": str} dicts,
        ordered oldest first — correct order for LLM context.
        Workspace isolation enforced via ThreadRepository.
        """
        settings = get_settings()
        messages = await _repo.get_recent_messages(
            db,
            thread_id=thread_id,
            workspace_id=workspace_id,
            limit=settings.AI_THREAD_MESSAGE_LIMIT,
        )
        return [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

    async def persist_turn(
        self,
        db: "AsyncSession",
        *,
        thread_id: str,
        user_question: str,
        assistant_answer: str,
        citations: list[dict],
        token_count: int | None = None,
    ) -> None:
        """
        Save both the user message and assistant response to the thread.

        Called AFTER the LLM response is complete (or stream finishes).
        Never called before — partial responses are not persisted.
        """
        await _repo.save_message(
            db,
            thread_id=thread_id,
            role="user",
            content=user_question,
        )
        await _repo.save_message(
            db,
            thread_id=thread_id,
            role="assistant",
            content=assistant_answer,
            citations=citations,
            token_count=token_count,
        )
        logger.debug(
            "Conversation turn persisted",
            extra={"thread_id": thread_id},
        )

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 4 — src/ai/services/rag_service.py (MINIMAL additions only)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Read rag_service.py carefully. Make ONLY these changes:

CHANGE 1: Append ChatResult field (after existing fields):
  thread_id: str | None = None

CHANGE 2: Add new private method to RagService class
(append BEFORE the answer() method — not inside it):

    async def _load_thread_context(
        self,
        *,
        thread_id: str | None,
        workspace_id: str,
        user_id: str,
        db: "AsyncSession | None",
    ) -> tuple[str, list[dict]]:
        """
        Load conversation history if thread_id provided.

        Returns:
            (resolved_thread_id, history_messages_list)
            history_messages_list is empty if no thread or no db session.

        Security: ThreadService.get_or_create_thread() verifies
        thread belongs to workspace_id before returning it.
        ValueError raised if workspace mismatch — propagates to route.
        """
        if db is None or not hasattr(db, "execute"):
            # No DB session available — skip history gracefully
            return (thread_id or "", [])

        from ai.memory.service import ThreadService
        thread_svc = ThreadService()

        thread = await thread_svc.get_or_create_thread(
            db,
            thread_id=thread_id,
            workspace_id=workspace_id,
            user_id=user_id,
        )
        resolved_id = str(thread.id)

        if thread_id:
            # Load existing history
            history = await thread_svc.load_history_as_messages(
                db,
                thread_id=resolved_id,
                workspace_id=workspace_id,
            )
        else:
            history = []

        return (resolved_id, history)

CHANGE 3: Add thread_id param to answer() signature only:
  Find: async def answer(self, *, question: str, workspace_id: str, user_id: str, role: str, retrieval_limit: int = 8,
  Replace with: async def answer(self, *, question: str, workspace_id: str, user_id: str, role: str, retrieval_limit: int = 8, thread_id: str | None = None, db: "AsyncSession | None" = None,

  Then add at the START of answer() body (before step 1 retrieval):
    resolved_thread_id, history_messages = await self._load_thread_context(
        thread_id=thread_id,
        workspace_id=workspace_id,
        user_id=user_id,
        db=db,
    )

  Replace the prompt building section (step 3) to use ContextBuilder:
    from ai.memory.context_builder import ContextBuilder
    builder = ContextBuilder()
    built = builder.build(
        question=question,
        history_messages=history_messages,
        retrieved_chunks=context_chunks,
    )
    # Use built.messages instead of the manually assembled messages list
    # Use built.context_chunks instead of context_chunks for citations

  After the LLM call succeeds, persist the turn:
    if db is not None and resolved_thread_id:
        from ai.memory.service import ThreadService
        await ThreadService().persist_turn(
            db,
            thread_id=resolved_thread_id,
            user_question=question,
            assistant_answer=rag_answer.answer,
            citations=[c.model_dump() for c in citations],
        )

  Update the ChatResult return to include thread_id:
    return ChatResult(
        answer=rag_answer.answer,
        citations=citations,
        chunks_retrieved=len(retrieved),
        chunks_used=len(built.context_chunks),
        latency_ms=latency_ms,
        thread_id=resolved_thread_id or None,
    )

CHANGE 4: Same minimal additions to stream_answer():
  - Add thread_id: str | None = None, db: AsyncSession | None = None params
  - Add _load_thread_context() call at start
  - Use ContextBuilder to build messages
  - Persist turn AFTER stream completes (in the metadata yield section)
  - Include thread_id in StreamMetadata (append field: thread_id: str | None = None)

RULES:
- DO NOT rewrite answer() or stream_answer() body logic
- DO NOT remove existing code — only add the four changes listed
- Show me exactly which lines change and the surrounding context
- If in doubt, show additions only — not the full method

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 5 — Add TYPE_CHECKING import to rag_service.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
At the top of rag_service.py, add if not already present:

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

This keeps SQLAlchemy out of the runtime import chain of rag_service.py
while allowing type hints. The actual session is passed from the route layer.

OUTPUT FORMAT:
Task 1-3: complete new files.
Task 4-5: exact lines to change with surrounding context.
Label each task clearly.
Zero truncation.
```

**Validation:**
```powershell
docker compose build api
# Expected: clean build

docker compose exec -e PYTHONPATH=/app/src api python -c "
from ai.memory.context_builder import ContextBuilder, BuiltContext
from ai.memory.service import ThreadService
builder = ContextBuilder()
built = builder.build(
    question='test',
    history_messages=[{'role':'user','content':'hello'}],
    retrieved_chunks=[{'chunk_id':'abc','note_id':'n1','title':'T','text':'content','score':0.8}]
)
print('PASS: context built, messages:', len(built.messages))
print('PASS: history_messages_used:', built.history_messages_used)
print('PASS: context_chunks_used:', built.context_chunks_used)
"
# Expected: PASS messages: 3 (system + history + user+context merged)
```

**Commit:**
```bash
git commit -am "feat(slice5.2): thread service, context builder, rag_service thread_id support"
```

---

## Sub-step 5.3 — Routes + Schema Updates + End-to-End Gate

**Goal:**
- `ChatRequest` gets `thread_id: str | None = None`
- `ChatResponse` gets `thread_id: str | None = None`
- `POST /ai/chat` and `POST /ai/chat/stream` pass `thread_id` and `db` to service
- `GET /ai/threads` — list user's conversation threads
- `GET /ai/threads/{thread_id}/messages` — load messages for UI
- `DELETE /ai/threads/{thread_id}` — soft delete
- Full end-to-end conversation flow verified

**Files to open in Cursor:**
- `src/ai_routes/chat.py`
- `src/ai_routes/threads.py` (create empty)
- `src/main.py` (reference — register new router)

---

```
ROLE: You are a senior backend engineer on DashNoteSystem.

OBJECTIVE: Sub-step 5.3 — Update chat schemas and handlers to pass
thread_id and db session, and create the threads management routes.

CONTEXT:
- get_session() from core.database.session — provides AsyncSession
- get_current_context() from core.security.dependency — provides RequestContext
- ThreadRepository from ai_memory.repository
- All ctx fields frozen to strings before any service call
- db session passed to rag.answer() and rag.stream_answer() as parameter
  Session must be resolved in route handler scope, NOT inside generate()

LAWS IN EFFECT:
- Append-only to src/ai_routes/chat.py
- POST /ai/chat and /ai/chat/stream remain fully functional
- ctx frozen to primitives before generator opens (SSE law)
- db session resolved in route handler scope — never inside generate()
- New file: src/ai_routes/threads.py for thread management routes
- Append one new include_router to main.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 1 — Update ChatRequest and ChatResponse in src/ai_routes/chat.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Find ChatRequest in src/ai_routes/chat.py.
Append field if not present:
  thread_id: str | None = Field(default=None, description="Continue an existing conversation.")

Find ChatResponse in src/ai_routes/chat.py.
Append field if not present:
  thread_id: str | None = None   # populated when conversation is persisted

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 2 — Update POST /ai/chat handler (minimal addition)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Find the chat() handler in src/ai_routes/chat.py.
Add get_session dependency to its signature:
  db: AsyncSession = Depends(get_session)

Add import at top if missing:
  from sqlalchemy.ext.asyncio import AsyncSession
  from core.database.session import get_session

Update the rag.answer() call to pass thread_id and db:
  result = await rag.answer(
      question=body.message,
      workspace_id=workspace_id,
      user_id=user_id,
      role=role,
      thread_id=body.thread_id,
      db=db,
  )

Update the return statement to include thread_id:
  return ChatResponse(
      answer=result.answer,
      citations=result.citations,
      chunks_retrieved=result.chunks_retrieved,
      chunks_used=result.chunks_used,
      latency_ms=result.latency_ms,
      thread_id=result.thread_id,
  )

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 3 — Update POST /ai/chat/stream handler (minimal addition)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Find chat_stream() in src/ai_routes/chat.py.
Add db session dependency (same as Task 2).

In the handler scope (BEFORE generate() is defined), add:
  thread_id_str = body.thread_id   # frozen primitive for closure

In the rag.stream_answer() call inside generate():
  async for event in rag.stream_answer(
      question=body.message,
      workspace_id=workspace_id,
      user_id=user_id,
      role=role,
      thread_id=thread_id_str,
      db=db,              # db resolved in handler scope, captured by closure
  ):

IMPORTANT: db session must be resolved in handler scope, not inside generate().
The handler scope is: before the line "async def generate():".
db is captured by the generate() closure — not re-fetched inside it.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 4 — src/ai_routes/threads.py (CREATE NEW)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Create this file completely:

"""
Thread management routes for DashNoteSystem AI conversations.

GET    /ai/threads                     — list user's threads
GET    /ai/threads/{thread_id}/messages — load messages for a thread
DELETE /ai/threads/{thread_id}         — soft-delete a thread

SECURITY: workspace_id always from RequestContext (JWT wid claim).
          Never from path params or query strings.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.security.dependency import get_current_context
from core.security.context import RequestContext
from core.database.session import get_session
from ai_memory.repository import ThreadRepository

router = APIRouter(prefix="/ai", tags=["ai-threads"])
_repo = ThreadRepository()


# ── Response schemas ─────────────────────────────────────────────────────────

class ThreadResponse(BaseModel):
    id: str
    workspace_id: str
    created_by: str
    title: str | None
    is_active: bool
    created_at: str
    updated_at: str


class MessageResponse(BaseModel):
    id: str
    thread_id: str
    role: str
    content: str
    citations: list[dict]
    token_count: int | None
    created_at: str


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("/threads", response_model=list[ThreadResponse])
async def list_threads(
    ctx: RequestContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_session),
) -> list[ThreadResponse]:
    """
    List the authenticated user's active conversation threads.
    Scoped to workspace_id from JWT — never shows other workspaces.
    """
    workspace_id = str(ctx.workspace_id)
    user_id = str(ctx.user_id)

    threads = await _repo.list_threads(
        db,
        workspace_id=workspace_id,
        user_id=user_id,
    )
    return [
        ThreadResponse(
            id=str(t.id),
            workspace_id=str(t.workspace_id),
            created_by=str(t.created_by),
            title=t.title,
            is_active=t.is_active,
            created_at=t.created_at.isoformat(),
            updated_at=t.updated_at.isoformat(),
        )
        for t in threads
    ]


@router.get("/threads/{thread_id}/messages", response_model=list[MessageResponse])
async def get_thread_messages(
    thread_id: str,
    ctx: RequestContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_session),
) -> list[MessageResponse]:
    """
    Load messages for a thread.
    Security: thread must belong to ctx.workspace_id — verified in repository.
    Returns 404 if thread not found or belongs to different workspace.
    """
    workspace_id = str(ctx.workspace_id)

    messages = await _repo.get_recent_messages(
        db,
        thread_id=thread_id,
        workspace_id=workspace_id,
        limit=50,
    )

    if not messages:
        # Could be empty thread or wrong workspace — same 404 response
        # (don't reveal whether thread exists in another workspace)
        thread = await _repo.get_thread(db, thread_id=thread_id, workspace_id=workspace_id)
        if thread is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thread not found.",
            )

    return [
        MessageResponse(
            id=str(m.id),
            thread_id=str(m.thread_id),
            role=m.role,
            content=m.content,
            citations=m.citations or [],
            token_count=m.token_count,
            created_at=m.created_at.isoformat(),
        )
        for m in messages
    ]


@router.delete("/threads/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_thread(
    thread_id: str,
    ctx: RequestContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_session),
) -> None:
    """
    Soft-delete a conversation thread.
    Security: only the thread's workspace can delete it.
    Returns 404 if not found — same response for security (no enumeration).
    """
    workspace_id = str(ctx.workspace_id)

    deleted = await _repo.delete_thread(
        db,
        thread_id=thread_id,
        workspace_id=workspace_id,
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found.",
        )

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 5 — src/main.py (append router registration)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Find where ai_chat_router is registered.
Append immediately after:

    # --- AI Slice 5: Thread management routes ---
    from ai_routes.threads import router as ai_threads_router
    app.include_router(ai_threads_router)

Show exact insertion location. No other changes to main.py.

OUTPUT FORMAT:
Task 1-2: exact lines changed with surrounding context (5 lines before/after).
Task 3: same — exact additions only.
Task 4: complete new file.
Task 5: exact line and location.
Zero truncation.
```

**Validation — Slice 5 Gate:**
```powershell
docker compose up -d --build api

# GATE 1 — New thread created on first message:
Invoke-RestMethod -Uri "http://127.0.0.1/ai/chat" `
  -Method Post `
  -Headers @{ Authorization = "Bearer <TOKEN>" } `
  -ContentType "application/json" `
  -Body '{"message": "What project codename is in my notes?", "thread_id": null}'
# Expected: response includes thread_id (non-null UUID string)
# Save this thread_id as $THREAD_ID

# GATE 2 — Conversation continues with history:
Invoke-RestMethod -Uri "http://127.0.0.1/ai/chat" `
  -Method Post `
  -Headers @{ Authorization = "Bearer <TOKEN>" } `
  -ContentType "application/json" `
  -Body "{`"message`": `"What did I just ask you?`", `"thread_id`": `"$THREAD_ID`"}"
# Expected: answer references "project codename" — proves history loaded

# GATE 3 — Thread list works:
Invoke-RestMethod -Uri "http://127.0.0.1/ai/threads" `
  -Headers @{ Authorization = "Bearer <TOKEN>" }
# Expected: array with at least 1 thread, id matches $THREAD_ID

# GATE 4 — Messages loadable:
Invoke-RestMethod -Uri "http://127.0.0.1/ai/threads/$THREAD_ID/messages" `
  -Headers @{ Authorization = "Bearer <TOKEN>" }
# Expected: 4 messages (user, assistant, user, assistant) in order

# GATE 5 — Cross-workspace isolation:
# Use token from DIFFERENT workspace, pass $THREAD_ID
Invoke-RestMethod -Uri "http://127.0.0.1/ai/chat" `
  -Method Post `
  -Headers @{ Authorization = "Bearer <DIFFERENT_WORKSPACE_TOKEN>" } `
  -ContentType "application/json" `
  -Body "{`"message`": `"test`", `"thread_id`": `"$THREAD_ID`"}"
# Expected: HTTP 400/422 or ValueError — thread belongs to different workspace

# GATE 6 — Streaming with thread_id works:
curl.exe -sS -X POST http://127.0.0.1/ai/chat/stream `
  -H "Authorization: Bearer <TOKEN>" `
  -H "Content-Type: application/json" `
  -d "{\"message\": \"Summarize what we discussed\", \"thread_id\": \"$THREAD_ID\"}" `
  --no-buffer
# Expected: tokens stream, final metadata includes thread_id

# GATE 7 — Delete thread:
Invoke-RestMethod -Uri "http://127.0.0.1/ai/threads/$THREAD_ID" `
  -Method Delete `
  -Headers @{ Authorization = "Bearer <TOKEN>" }
# Expected: 204 No Content

# GATE 8 — API health unchanged:
curl.exe -sS http://127.0.0.1/health
```

**Commit:**
```bash
git commit -am "feat(slice5.3): thread routes, chat schema thread_id, full conversation flow — slice 5 complete"
```

---

## Slice 5 Complete — What Was Built

```
src/ai_memory/                          ← NEW domain module (ORM layer)
  __init__.py
  models.py                             ← AIThread, AIMessage SQLAlchemy models
  repository.py                         ← ThreadRepository (stateless, session per method)

src/ai/memory/                          ← NEW service layer (no ORM)
  __init__.py
  context_builder.py                    ← ContextBuilder — budget-aware message assembly
  service.py                            ← ThreadService — get_or_create, load_history, persist

src/ai/services/rag_service.py          ← MINIMAL additions:
                                           ChatResult.thread_id field
                                           StreamMetadata.thread_id field
                                           _load_thread_context() private method
                                           thread_id + db params on answer() + stream_answer()

src/ai_routes/chat.py                   ← MINIMAL additions:
                                           ChatRequest.thread_id field
                                           ChatResponse.thread_id field
                                           db session dependency added
                                           thread_id passed to service calls

src/ai_routes/threads.py                ← NEW: GET /ai/threads
                                              GET /ai/threads/{id}/messages
                                              DELETE /ai/threads/{id}

alembic/versions/xxx_add_ai_threads.py  ← NEW migration
src/main.py                             ← ai_threads_router registered (1 line)
requirements.txt                        ← langgraph + langgraph-checkpoint-postgres
settings                                ← AI_THREAD_MESSAGE_LIMIT
```

```
What is NOT in Slice 5 (correct — belongs to Slice 6):
  ✗ LangGraph graphs or nodes
  ✗ AsyncPostgresSaver (LangGraph checkpointer)
  ✗ Agent tools or tool calling
  ✗ LangGraph state machine
  ✗ Multi-agent routing
  langgraph IS installed — ready for Slice 6
  AsyncPostgresSaver IS NOT wired — that is Slice 6's first task
```

---

> **Next:** Slice 6 — LangGraph Workflows
> LangGraph enters HERE — not before. Now you have:
> - Stable retrieval (Slice 2)
> - Working chat (Slice 3-4)
> - Conversation persistence (Slice 5)
> The LangGraph graph adds tool calling and conditional loops on top of
> this foundation. First graph: retrieve → reason → tool_or_respond → END.
> First tools: search_notes_tool, create_note_tool — call existing services.