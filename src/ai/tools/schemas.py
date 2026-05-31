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
