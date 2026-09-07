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

from langchain_core.tools import StructuredTool

from ai.tools.schemas import (
    CreateNoteArgs,
    SearchNotesArgs,
    SummarizeWorkspaceArgs,
    UpdateNoteArgs,
)

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
    Search the user's workspace notes and uploaded files using semantic retrieval.

    Use this tool when the user asks about content in their notes or files,
    wants to find specific information, or needs context from past writing
    or indexed documents. Always pass workspace_id, user_id, and role from
    the current agent state.
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


def _ensure_checkpointer_for_mutation() -> str | None:
    """
    Fail closed: mutations require a live checkpointer so HITL can resume.
    Returns an error string if unavailable, else None.
    """
    try:
        from ai.memory.checkpointer import get_graph_checkpointer

        get_graph_checkpointer()
    except RuntimeError:
        return (
            "Error: note mutations require human approval and a checkpointer. "
            "Checkpointer is not initialized — mutation blocked."
        )
    except Exception as e:  # noqa: BLE001
        logger.error("checkpointer probe failed", extra={"error": str(e)})
        return "Error: note mutations unavailable (checkpointer error)."
    return None


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
    blocked = _ensure_checkpointer_for_mutation()
    if blocked:
        return blocked

    from langgraph.types import interrupt

    from ai.hitl import build_approval_payload, is_approved

    decision = interrupt(
        build_approval_payload(
            tool="create_note",
            args={
                "title": title,
                "content": content,
                "workspace_id": workspace_id,
                "user_id": user_id,
                "role": role,
            },
        )
    )
    if not is_approved(decision):
        return "Note creation rejected by user. No note was created."

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
        return (
            f"Note created successfully. ID: {result['note_id']}, "
            f"Title: {result['title']}"
        )
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
    blocked = _ensure_checkpointer_for_mutation()
    if blocked:
        return blocked

    from langgraph.types import interrupt

    from ai.hitl import build_approval_payload, is_approved

    decision = interrupt(
        build_approval_payload(
            tool="update_note",
            args={
                "note_id": note_id,
                "content": content,
                "workspace_id": workspace_id,
                "user_id": user_id,
                "role": role,
            },
        )
    )
    if not is_approved(decision):
        return "Note update rejected by user. No changes were saved."

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
            question=(
                "Provide a comprehensive overview and summary of all the main "
                "topics, projects, and information covered in the workspace notes."
            ),
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
        "Search the user's workspace notes and indexed uploaded files for "
        "relevant information. Use when the user asks about content in their "
        "notes or documents, or wants to find specific information. "
        "Pass workspace_id, user_id, role from state."
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
