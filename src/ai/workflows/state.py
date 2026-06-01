"""
AgentState — the typed state envelope for the workspace assistant graph.

Every node in the graph reads from and writes to this state.
LangGraph merges state updates — nodes return partial state dicts.

messages uses add_messages reducer: each node appends to the list,
never replaces it. This is the correct LangGraph pattern.

Tenant fields (workspace_id, user_id, role) are immutable once set
in the initial state. Nodes read them but never write them.

steps_taken is incremented by call_model — guards against infinite loops.
"""
from __future__ import annotations

from typing import Annotated

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """
    Complete state for one agent conversation turn.

    Passed through every graph node. Nodes return partial dicts
    that LangGraph merges into the accumulated state.

    messages:     Conversation history. add_messages reducer appends
                  new messages rather than replacing the list.
    workspace_id: Injected at graph invocation — never modified by nodes.
    user_id:      Injected at graph invocation — never modified by nodes.
    role:         Injected at graph invocation — never modified by nodes.
    steps_taken:  Incremented by call_model. Checked by should_continue
                  to prevent infinite tool execution loops.
    thread_id:    Links to ai_threads product table (Slice 5).
                  Also used as LangGraph configurable thread_id.
    """

    messages: Annotated[list, add_messages]
    workspace_id: str
    user_id: str
    role: str
    steps_taken: int
    thread_id: str | None
