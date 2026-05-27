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