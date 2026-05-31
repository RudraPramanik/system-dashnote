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