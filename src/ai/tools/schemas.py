"""
Pydantic args_schema models for LangGraph agent tools.

Tenant identity (workspace_id, user_id, role) is NOT model-owned —
tools bind it from HarnessContext (Blueprint 9H.1).

IMPORT LAW: pydantic and stdlib only.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class SearchNotesArgs(BaseModel):
    """Arguments for search_notes_tool."""

    question: str = Field(description="The search query to find relevant notes.")


class CreateNoteArgs(BaseModel):
    """Arguments for create_note_tool."""

    title: str = Field(description="Title for the new note.")
    content: str = Field(description="Full markdown content for the note body.")


class UpdateNoteArgs(BaseModel):
    """Arguments for update_note_tool."""

    note_id: str = Field(description="UUID of the note to update.")
    content: str = Field(description="New full markdown content for the note.")


class SummarizeWorkspaceArgs(BaseModel):
    """Arguments for summarize_workspace_tool (no model-owned fields)."""

    pass
