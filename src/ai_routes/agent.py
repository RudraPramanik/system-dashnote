"""
Agent routes for DashNoteSystem — LangGraph stateful workspace assistant.

POST /ai/agent              — invoke agent (waits for final answer or approval_required)
POST /ai/agent/stream       — stream agent execution events via SSE
POST /ai/agent/resume       — approve a pending mutation interrupt
POST /ai/agent/reject       — reject a pending mutation interrupt

These endpoints are SEPARATE from /ai/chat and /ai/chat/stream.
POST /ai/chat = fast direct RAG (always available, always fast)
POST /ai/agent = stateful LangGraph agent with tool calling

Both coexist. Users choose based on their need.

HITL SSE contract:
  Existing: token | tool_start | tool_end | done | error
  Add: approval_required { type, tool, args, thread_id, interrupt_id }
  Lifecycle: emit approval_required → end stream (client reconnects via resume/reject)
  Ordering: interrupt may follow tool_start; no successful mutation tool_end before approve

Security:
  workspace_id from JWT only — never from request body.
  ctx frozen to primitives before any async operation.
  db_session_var set before graph invocation for mutation tools.
  Resume/reject re-validate thread + checkpoint workspace ownership.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage
from langgraph.types import Command
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ai.hitl import approval_event_from_interrupt, extract_interrupts
from ai.memory.service import ThreadService
from ai.tools.note_tools import db_session_var
from ai.workflows.workspace_assistant import get_workspace_assistant
from ai_memory.repository import ThreadRepository
from core.database.session import get_session
from core.security.context import RequestContext
from core.security.dependency import get_current_context
from shared.llm.fallback import (
    LLM_UNAVAILABLE_MESSAGE,
    LLMUnavailableError,
    is_model_gone,
)
from shared.llm.retry import RETRYABLE_EXCEPTIONS

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
    """Output from POST /ai/agent (completed turn)."""

    status: Literal["completed"] = "completed"
    answer: str
    thread_id: str
    steps_taken: int
    tool_calls_made: int


class ApprovalRequiredResponse(BaseModel):
    """Output when a mutation interrupt pauses the agent."""

    status: Literal["approval_required"] = "approval_required"
    type: Literal["approval_required"] = "approval_required"
    tool: str
    args: dict[str, Any]
    thread_id: str
    interrupt_id: str


class AgentResumeRequest(BaseModel):
    """Approve or reject a pending HITL interrupt."""

    thread_id: str = Field(..., min_length=1)
    interrupt_id: str | None = Field(
        default=None,
        description="Optional; when set must match the pending interrupt id.",
    )


class AgentRejectResponse(BaseModel):
    status: Literal["rejected"] = "rejected"
    answer: str
    thread_id: str
    steps_taken: int = 0
    tool_calls_made: int = 0


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


def _final_answer_from_state(final_state: dict[str, Any]) -> tuple[str, int]:
    final_answer = ""
    tool_calls_made = 0
    for msg in reversed(final_state.get("messages") or []):
        if isinstance(msg, AIMessage):
            tool_calls_made += len(msg.tool_calls or [])
            if not msg.tool_calls and not final_answer:
                final_answer = msg.content or ""
    return (
        final_answer or "Agent completed without producing a final answer.",
        tool_calls_made,
    )


async def _assert_thread_workspace(
    *,
    thread_id: str,
    workspace_id: str,
    user_id: str,
    db: AsyncSession,
) -> None:
    """Deny cross-tenant thread access (product AIThread table)."""
    try:
        await _resolve_thread_id(thread_id, workspace_id, user_id, db)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Thread does not belong to this workspace",
        ) from e


async def _pending_interrupt_for_thread(
    graph: Any,
    *,
    thread_id: str,
    workspace_id: str,
) -> Any:
    """
    Load checkpoint; require a pending interrupt owned by this workspace.
    """
    config = {"configurable": {"thread_id": thread_id}}
    try:
        snap = await graph.aget_state(config)
    except Exception as e:
        logger.error(
            "aget_state failed on resume",
            extra={"thread_id": thread_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No resumable agent state for this thread",
        ) from e

    if snap is None or not extract_interrupts(snap):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No pending approval on this thread",
        )

    values = snap.values if isinstance(snap.values, dict) else {}
    checkpoint_wid = str(values.get("workspace_id") or "")
    if checkpoint_wid and checkpoint_wid != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Thread checkpoint does not belong to this workspace",
        )

    return extract_interrupts(snap)[0]


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post(
    "/agent",
    response_model=None,
    responses={
        200: {
            "description": "Completed agent turn or approval_required",
            "content": {
                "application/json": {
                    "examples": {
                        "completed": {"value": {"status": "completed", "answer": "..."}},
                        "approval": {
                            "value": {
                                "status": "approval_required",
                                "type": "approval_required",
                                "tool": "create_note",
                            }
                        },
                    }
                }
            },
        }
    },
)
async def agent_chat(
    body: AgentRequest,
    ctx: RequestContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_session),
) -> AgentResponse | ApprovalRequiredResponse:
    """
    Invoke the workspace assistant agent.

    Unlike /ai/chat (fast RAG), this endpoint uses LangGraph for:
    - Multi-step reasoning with tool calls
    - Creating and updating notes on your behalf (HITL before side effects)
    - Maintaining conversation state across turns

    Returns either a completed answer or approval_required when a mutation
    interrupt pauses the graph. Use /ai/agent/resume or /ai/agent/reject next.
    """
    workspace_id = str(ctx.workspace_id)
    user_id = str(ctx.user_id)
    role = ctx.role

    try:
        resolved_thread_id = await _resolve_thread_id(
            body.thread_id, workspace_id, user_id, db
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

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

    except LLMUnavailableError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Agent unavailable: {str(e)}",
        ) from e
    except RETRYABLE_EXCEPTIONS as e:
        logger.error(
            "Agent LLM temporarily unavailable",
            extra={"workspace_id": workspace_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM temporarily unavailable; retry shortly",
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
        db_session_var.reset(token)

    interrupts = extract_interrupts(final_state)
    if interrupts:
        event = approval_event_from_interrupt(
            interrupts[0], thread_id=resolved_thread_id
        )
        return ApprovalRequiredResponse(
            tool=event["tool"],
            args=event.get("args") or {},
            thread_id=resolved_thread_id,
            interrupt_id=str(event.get("interrupt_id") or ""),
        )

    answer, tool_calls_made = _final_answer_from_state(final_state)
    return AgentResponse(
        answer=answer,
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
      {"type": "token", "content": "..."}
      {"type": "tool_start", "tool": "...", "args": {...}}
      {"type": "tool_end", "tool": "...", "result": "..."}
      {"type": "approval_required", "tool": "...", "args": {...},
       "thread_id": "...", "interrupt_id": "..."}  — then stream ends
      {"type": "done", "thread_id": "...", "steps_taken": N}
      {"type": "error", "message": "..."}

    Nginx note: X-Accel-Buffering: no required for streaming through proxy.
    """
    workspace_id = str(ctx.workspace_id)
    user_id = str(ctx.user_id)
    role = ctx.role

    try:
        resolved_thread_id = await _resolve_thread_id(
            body.thread_id, workspace_id, user_id, db
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

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

            # After stream: HITL pause → approval_required then close (no done)
            snap = await graph.aget_state(config)
            pending = extract_interrupts(snap)
            if pending:
                event_payload = approval_event_from_interrupt(
                    pending[0], thread_id=resolved_thread_id
                )
                yield f"data: {json.dumps(event_payload)}\n\n"
                yield "data: [DONE]\n\n"
                return

            yield f"data: {json.dumps({'type': 'done', 'thread_id': resolved_thread_id, 'steps_taken': steps})}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.exception("Agent stream failed")
            err_message = (
                LLM_UNAVAILABLE_MESSAGE
                if isinstance(e, LLMUnavailableError) or is_model_gone(e)
                else "Agent stream failed. Try /ai/chat for direct RAG."
            )
            error_payload = {
                "type": "error",
                "message": err_message,
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


@router.post("/agent/resume", response_model=None)
async def agent_resume(
    body: AgentResumeRequest,
    ctx: RequestContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_session),
) -> AgentResponse | ApprovalRequiredResponse:
    """Approve a pending mutation interrupt and continue the agent graph."""
    workspace_id = str(ctx.workspace_id)
    user_id = str(ctx.user_id)

    await _assert_thread_workspace(
        thread_id=body.thread_id,
        workspace_id=workspace_id,
        user_id=user_id,
        db=db,
    )

    token = db_session_var.set(db)
    try:
        graph = get_workspace_assistant()
        pending = await _pending_interrupt_for_thread(
            graph, thread_id=body.thread_id, workspace_id=workspace_id
        )
        pending_id = getattr(pending, "id", None)
        if body.interrupt_id and pending_id and body.interrupt_id != str(pending_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="interrupt_id does not match pending interrupt",
            )

        config = {"configurable": {"thread_id": body.thread_id}}
        final_state = await graph.ainvoke(
            Command(resume={"action": "approve"}),
            config=config,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Agent resume failed",
            extra={"workspace_id": workspace_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resume agent turn",
        ) from e
    finally:
        db_session_var.reset(token)

    interrupts = extract_interrupts(final_state)
    if interrupts:
        event = approval_event_from_interrupt(
            interrupts[0], thread_id=body.thread_id
        )
        return ApprovalRequiredResponse(
            tool=event["tool"],
            args=event.get("args") or {},
            thread_id=body.thread_id,
            interrupt_id=str(event.get("interrupt_id") or ""),
        )

    answer, tool_calls_made = _final_answer_from_state(final_state)
    return AgentResponse(
        answer=answer,
        thread_id=body.thread_id,
        steps_taken=int(final_state.get("steps_taken", 0)),
        tool_calls_made=tool_calls_made,
    )


@router.post("/agent/reject", response_model=AgentRejectResponse)
async def agent_reject(
    body: AgentResumeRequest,
    ctx: RequestContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_session),
) -> AgentRejectResponse:
    """Reject a pending mutation interrupt; no note create/update side effect."""
    workspace_id = str(ctx.workspace_id)
    user_id = str(ctx.user_id)

    await _assert_thread_workspace(
        thread_id=body.thread_id,
        workspace_id=workspace_id,
        user_id=user_id,
        db=db,
    )

    token = db_session_var.set(db)
    try:
        graph = get_workspace_assistant()
        pending = await _pending_interrupt_for_thread(
            graph, thread_id=body.thread_id, workspace_id=workspace_id
        )
        pending_id = getattr(pending, "id", None)
        if body.interrupt_id and pending_id and body.interrupt_id != str(pending_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="interrupt_id does not match pending interrupt",
            )

        config = {"configurable": {"thread_id": body.thread_id}}
        final_state = await graph.ainvoke(
            Command(resume={"action": "reject"}),
            config=config,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Agent reject failed",
            extra={"workspace_id": workspace_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reject agent turn",
        ) from e
    finally:
        db_session_var.reset(token)

    # Another interrupt should be rare; treat as completed rejection message.
    if extract_interrupts(final_state):
        return AgentRejectResponse(
            answer="Mutation rejected; another approval is still pending.",
            thread_id=body.thread_id,
        )

    answer, tool_calls_made = _final_answer_from_state(final_state)
    return AgentRejectResponse(
        answer=answer,
        thread_id=body.thread_id,
        steps_taken=int(final_state.get("steps_taken", 0)),
        tool_calls_made=tool_calls_made,
    )
