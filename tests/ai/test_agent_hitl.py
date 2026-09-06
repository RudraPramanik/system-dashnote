"""Unit tests for agent HITL helpers and mutation interrupt behavior."""
from __future__ import annotations

from typing import Annotated, TypedDict
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.types import Command, interrupt
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from ai.hitl import (
    approval_event_from_interrupt,
    build_approval_payload,
    extract_interrupts,
    is_approved,
)


class _CreateArgs(BaseModel):
    title: str = Field(...)
    content: str = Field(...)
    workspace_id: str = Field(...)
    user_id: str = Field(...)
    role: str = Field(...)


def test_build_approval_payload_locked_keys():
    payload = build_approval_payload(
        tool="create_note",
        args={"title": "t"},
        thread_id="tid",
        interrupt_id="iid",
    )
    assert payload["type"] == "approval_required"
    assert payload["tool"] == "create_note"
    assert payload["args"]["title"] == "t"
    assert payload["thread_id"] == "tid"
    assert payload["interrupt_id"] == "iid"


def test_is_approved():
    assert is_approved({"action": "approve"}) is True
    assert is_approved({"action": "reject"}) is False
    assert is_approved("approve") is False


def test_approval_event_from_interrupt_uses_langgraph_id():
    class _I:
        id = "lg-123"
        value = {"tool": "update_note", "args": {"note_id": "n1"}}

    event = approval_event_from_interrupt(_I(), thread_id="thr-1")
    assert event["interrupt_id"] == "lg-123"
    assert event["thread_id"] == "thr-1"
    assert event["tool"] == "update_note"


@pytest.mark.asyncio
async def test_interrupt_before_side_effect_and_approve_reject():
    """Mutation tool interrupts before side effect; approve commits, reject does not."""
    created: list[str] = []

    async def _create_note(
        title: str,
        content: str,
        workspace_id: str,
        user_id: str,
        role: str,
    ) -> str:
        decision = interrupt(
            build_approval_payload(
                tool="create_note",
                args={"title": title, "content": content},
            )
        )
        if not is_approved(decision):
            return "rejected"
        created.append(title)
        return f"created:{title}"

    tool = StructuredTool.from_function(
        coroutine=_create_note,
        name="create_note",
        description="Create a note",
        args_schema=_CreateArgs,
    )

    class S(TypedDict):
        messages: Annotated[list, add_messages]
        workspace_id: str

    def agent(state: S):
        return {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "create_note",
                            "args": {
                                "title": "Hello",
                                "content": "Body",
                                "workspace_id": "w1",
                                "user_id": "u1",
                                "role": "owner",
                            },
                            "id": "c1",
                        }
                    ],
                )
            ]
        }

    g = StateGraph(S)
    g.add_node("agent", agent)
    g.add_node("tools", ToolNode([tool]))
    g.add_edge(START, "agent")
    g.add_edge("agent", "tools")
    g.add_edge("tools", END)
    app = g.compile(checkpointer=MemorySaver())

    cfg = {"configurable": {"thread_id": "hitl-approve"}}
    r1 = await app.ainvoke(
        {"messages": [HumanMessage("create")], "workspace_id": "w1"},
        cfg,
    )
    interrupts = extract_interrupts(r1)
    assert interrupts
    assert created == []

    r2 = await app.ainvoke(Command(resume={"action": "approve"}), cfg)
    assert created == ["Hello"]
    assert "created:Hello" in str(r2["messages"][-1].content)

    # Reject path
    created.clear()
    cfg2 = {"configurable": {"thread_id": "hitl-reject"}}
    await app.ainvoke(
        {"messages": [HumanMessage("create")], "workspace_id": "w1"},
        cfg2,
    )
    r3 = await app.ainvoke(Command(resume={"action": "reject"}), cfg2)
    assert created == []
    assert "rejected" in str(r3["messages"][-1].content)


def test_cross_workspace_resume_denied_helper():
    """Router maps mismatched checkpoint workspace to 403 — exercise ownership check shape."""
    from ai_routes.agent import _pending_interrupt_for_thread

    # Smoke that the helper exists; full HTTP coverage needs TestClient + DB.
    assert callable(_pending_interrupt_for_thread)


def test_mutation_fails_closed_without_checkpointer():
    from ai.tools import note_tools

    with patch("ai.memory.checkpointer.get_graph_checkpointer", side_effect=RuntimeError("no cp")):
        # Call the private guard via create path coroutine setup
        err = note_tools._ensure_checkpointer_for_mutation()
        assert err is not None
        assert "checkpointer" in err.lower()


def test_retrieval_depth_payload():
    from observability.tracing import retrieval_depth_payload

    payload = retrieval_depth_payload(
        [
            MagicMock(
                chunk_id="c1",
                note_id="n1",
                file_id="",
                source_type="note",
                score=0.91,
            )
        ]
    )
    assert payload["chunks_retrieved"] == 1
    assert payload["chunk_ids"] == ["c1"]
    assert payload["note_ids"] == ["n1"]
    assert payload["scores"] == [0.91]
