ARCHITECTURE LAW — DashNoteSystem. Enforce in ALL generated code.

MODULE PATHS:
  Import as: from config import settings, get_settings
             from ai.services.rag_service import RagService, get_rag_service
             from ai.prompts.rag import RAG_SYSTEM_INSTRUCTION, build_rag_user_message
             from core.security.dependency import get_current_context
  NEVER as:  from src.config import ...
             from src.ai.services import ...

STREAMING LAWS:
  1. stream_answer() accepts plain strings (workspace_id, user_id, role)
     NEVER RequestContext — required for LangGraph tool reuse in Slice 6
  2. RequestContext is frozen to plain strings in the ROUTE before generator opens
     workspace_id = str(ctx.workspace_id)
     user_id = str(ctx.user_id)
     role = ctx.role
     ctx is NEVER referenced inside async def generate()
  3. RagService singleton is resolved BEFORE the generator function is defined
     rag = get_rag_service()  ← resolved here, in route handler scope
     async def generate():
         async for chunk in rag.stream_answer(...):  ← rag captured by closure
  4. Nginx buffering must be disabled for SSE to work end-to-end:
     Headers: Cache-Control: no-cache, X-Accel-Buffering: no
     Without these, Nginx holds the full response before forwarding = no streaming

PROMPT LAW:
  - ONE system instruction for both streaming and non-streaming: RAG_SYSTEM_INSTRUCTION
  - No streaming-specific prompt variant — same instruction, stream=True is the only diff
  - Never add inline [CHUNK:uuid] parsing from token stream — unreliable mid-stream
  - Citations come from retrieval grounding at stream END, not from LLM token parsing

SERVICE LAW — src/ai/services/rag_service.py:
  - APPEND ONLY — never touch existing answer() method or existing models
  - stream_answer() is a NEW method added below existing code
  - No FastAPI, RequestContext, SQLAlchemy in this file

ROUTE LAW — src/ai_routes/chat.py:
  - APPEND ONLY — POST /ai/chat must remain fully functional
  - POST /ai/chat/stream is a NEW endpoint appended below existing route
  - Do not restructure, reorder, or rewrite existing route logic

INFRA LAW:
  - No new packages needed — litellm already handles streaming
  - No new Dockerfiles or compose files
  - Append-only to requirements.txt only if a package is genuinely missing

LangGraph compatibility:
  stream_answer() signature is agent-tool-compatible:
  (question, workspace_id, user_id, role) as plain strings.
  Slice 6 agent tools call this with no adapter needed.

Acknowledge these laws before writing any code.