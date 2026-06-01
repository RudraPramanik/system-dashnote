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
from langchain_core.messages import AIMessage
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ai.memory.service import ThreadService
from ai.tools.note_tools import db_session_var
from ai.workflows.workspace_assistant import get_workspace_assistant
from ai_memory.repository import ThreadRepository
from core.database.session import get_session
from core.security.context import RequestContext
from core.security.dependency import get_current_context

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
    repo = ThreadRepository()
    thread = await repo.create_thread(
        db,
        workspace_id=workspace_id,
        user_id=user_id,
        title=None,
    )
    return str(thread.id)


def _extract_stream_chunk_content(chunk: Any) -> str:
    """Best-effort extraction of token text from stream chunk object."""
    if hasattr(chunk, "content") and isinstance(chunk.content, str):
        return chunk.content

    if isinstance(chunk, dict):
        content = chunk.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text = item.get("text")
                    if isinstance(text, str):
                        parts.append(text)
            return "".join(parts)

    return ""


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
        ) from e

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
        ) from e
    except Exception as e:
        logger.error(
            "Agent invocation failed",
            extra={"workspace_id": workspace_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Agent encountered an error. Try /ai/chat for direct RAG.",
        ) from e
    finally:
        # Always reset the context variable
        db_session_var.reset(token)

    # Extract final answer from last AI message
    final_answer = ""
    tool_calls_made = 0
    for msg in reversed(final_state["messages"]):
        if isinstance(msg, AIMessage):
            tool_calls_made += len(msg.tool_calls or [])
            if not msg.tool_calls and not final_answer:
                final_answer = msg.content

    return AgentResponse(
        answer=final_answer or "Agent completed without producing a final answer.",
        thread_id=resolved_thread_id,
        steps_taken=int(final_state.get("steps_taken", 0)),
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
        raise HTTPException(status_code=400, detail=str(e)) from e

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
            }

            steps = 0
            async for event in graph.astream_events(
                initial_state, config=config, version="v2"
            ):
                kind = event.get("event", "")
                data = event.get("data", {})

                if kind == "on_chat_model_stream":
                    chunk = data.get("chunk", {})
                    content = _extract_stream_chunk_content(chunk)
                    if content:
                        yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"

                elif kind == "on_tool_start":
                    payload = {
                        "type": "tool_start",
                        "tool": event.get("name", ""),
                        "args": data.get("input", {}),
                    }
                    yield f"data: {json.dumps(payload)}\n\n"

                elif kind == "on_tool_end":
                    result = data.get("output", "")
                    payload = {
                        "type": "tool_end",
                        "tool": event.get("name", ""),
                        "result": str(result)[:200],
                    }
                    yield f"data: {json.dumps(payload)}\n\n"

                elif kind == "on_chain_end" and event.get("name") == "LangGraph":
                    output = data.get("output", {})
                    if isinstance(output, dict):
                        steps = int(output.get("steps_taken", 0))

            yield f"data: {json.dumps({'type': 'done', 'thread_id': resolved_thread_id, 'steps_taken': steps})}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error("Agent stream failed", extra={"error": str(e)})
            error_payload = {
                "type": "error",
                "message": "Agent stream failed. Try /ai/chat for direct RAG.",
            }
            yield f"data: {json.dumps(error_payload)}\n\n"
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
