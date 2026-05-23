ARCHITECTURE LAW — DashNoteSystem. Enforce in ALL generated code.

MODULE PATHS:
  Import as: from config import settings, get_settings
             from ai.services.rag_service import RagService
             from ai.retrieval.wrapper import get_workspace_vector_search
             from core.security.context import RequestContext
  NEVER as:  from src.config import ...
             from src.ai.services import ...

AI SERVICE LAW — src/ai/services/* MUST NEVER import:
  - FastAPI, Request, Response, HTTPException, APIRouter, Depends
  - SQLAlchemy sessions or any repository class
  - RequestContext (accept workspace_id, user_id, role as plain str instead)
  - src/worker/*, src/notes/*, src/files/*, src/auth/*

WHY RequestContext is banned in services:
  LangGraph agent tools will call these services directly in Slice 6.
  Agent tools have no HTTP context — they pass plain strings.
  Services that accept RequestContext cannot be reused by agents.
  Design services for reuse from both HTTP routes AND agent tools.

AI ROUTE LAW — src/ai_routes/* may import:
  - FastAPI components, get_current_context, RequestContext
  - ai.services.*, ai.retrieval.*
  The router freezes ctx to plain strings before calling services.

ROUTER LAW:
  - Chat endpoint lives in src/ai_routes/chat.py — never notes/router.py
  - Do not refactor or reorder any existing router
  - Append new router registration to main.py only

STRUCTURED OUTPUT LAW:
  - Never parse raw LLM text with regex or string splitting
  - Use litellm.acompletion() with response_format=RAGAnswer (Pydantic model)
  - Citations must be grounded in retrieved chunks — never trust LLM-generated IDs

PACKAGE DISCIPLINE:
  - Install packages only when the code that needs them is written
  - Do not add langchain-core or langsmith in Slice 3 — not needed yet
  - LiteLLM already installed — it handles the completion call directly

INFRA LAW:
  - No new Dockerfiles or compose files
  - Append-only to requirements.txt, settings, .env

LangGraph compatibility note:
  RagService.answer() accepts (question, workspace_id, user_id, role) as plain str.
  This signature works identically from HTTP routes AND future agent tools.
  Never couple service methods to HTTP request lifecycle objects.

Acknowledge these laws before writing any code.