"""
Workspace assistant LangGraph graph — DashNoteSystem.

Graph topology:
  START → agent → (conditional) → tools → agent → ... → END

Nodes:
  agent:  Calls LiteLLM with tools available. Returns AI message.
  tools:  Executes tool calls from the AI message.

Routing (should_continue):
  "tools"  → agent called a tool — execute it and loop back
  "end"    → agent produced final answer — exit graph
  "limit"  → AGENT_MAX_ITERATIONS exceeded — force exit with warning

Safety:
  steps_taken incremented on every agent call.
  should_continue checks steps_taken before routing to tools.
  Maximum iterations: settings.AGENT_MAX_ITERATIONS (default 10).

LiteLLM tool calling:
  Tools registered as OpenAI function definitions (list of dicts).
  NOT LangChain bind_tools() — LiteLLM is not a LangChain LLM.
  Tool results added to messages as tool_result messages.

Compilation:
  compile_workspace_graph() called ONCE in get_workspace_assistant().
  Result cached in _compiled_graph module variable.
  Never compiled at import time.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from ai.tools.note_tools import db_session_var, get_note_tools
from ai.workflows.state import AgentState
from config import get_settings

logger = logging.getLogger(__name__)

# Module-level cache — set by get_workspace_assistant() on first call
_compiled_graph = None

# System prompt for the workspace assistant
WORKSPACE_ASSISTANT_PROMPT = """You are an active workspace assistant for DashNoteSystem.

You have access to tools that let you search, read, create, and update notes
inside the user's workspace. Use them when the user explicitly asks you to.

Critical rules:
1. ALWAYS pass workspace_id, user_id, and role exactly as they appear in your
   system context. Never modify, omit, or fabricate these values.
2. Use search_notes before answering questions about workspace content.
3. Use create_note only when explicitly asked to create or save a note.
4. Use update_note only when explicitly asked to modify an existing note.
5. Use summarize_workspace when asked for an overview of all notes.
6. If you cannot complete a task with available tools, say so clearly.
7. Never invent note IDs — search first to find real ones.
"""


def _to_litellm_messages(messages: list[Any]) -> list[dict[str, Any]]:
    """Convert LangChain messages to LiteLLM/OpenAI chat message format."""
    converted: list[dict[str, Any]] = []
    for message in messages:
        if isinstance(message, AIMessage):
            payload: dict[str, Any] = {
                "role": "assistant",
                "content": message.content or "",
            }
            if message.tool_calls:
                payload["tool_calls"] = [
                    {
                        "id": tool_call["id"],
                        "type": "function",
                        "function": {
                            "name": tool_call["name"],
                            "arguments": json.dumps(tool_call["args"]),
                        },
                    }
                    for tool_call in message.tool_calls
                ]
            converted.append(payload)
            continue

        message_type = getattr(message, "type", None)
        if message_type == "tool":
            converted.append(
                {
                    "role": "tool",
                    "content": message.content or "",
                    "tool_call_id": getattr(message, "tool_call_id", ""),
                }
            )
            continue

        if message_type == "human":
            converted.append({"role": "user", "content": message.content or ""})
            continue

        if message_type == "system":
            converted.append({"role": "system", "content": message.content or ""})
            continue

        if isinstance(message, dict):
            converted.append(message)
            continue

        converted.append({"role": "user", "content": str(message)})
    return converted


async def call_model(state: AgentState) -> dict[str, Any]:
    """
    Agent node: call LiteLLM with tools available.

    Formats tools as OpenAI function definitions for LiteLLM.
    Injects tenant primitives into system prompt for tool guidance.
    Increments steps_taken as iteration safety counter.
    Returns partial state dict with updated messages and steps_taken.
    """
    settings = get_settings()
    tools = get_note_tools()

    # Format tools as OpenAI function definitions for LiteLLM
    openai_tools = [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.args_schema.model_json_schema(),
            },
        }
        for tool in tools
    ]

    # Build system message with tenant context injected
    system_content = (
        f"{WORKSPACE_ASSISTANT_PROMPT}\n\n"
        f"Current session context:\n"
        f"  workspace_id: {state['workspace_id']}\n"
        f"  user_id: {state['user_id']}\n"
        f"  role: {state['role']}\n"
        "Always use these exact values in every tool call."
    )

    # Build messages array: system + conversation history
    messages = [{"role": "system", "content": system_content}] + _to_litellm_messages(
        state["messages"]
    )

    from shared.llm.retry import acompletion_with_retry

    try:
        response = await acompletion_with_retry(
            model=settings.LLM_MODEL,
            messages=messages,
            tools=openai_tools,
            tool_choice="auto",
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            timeout=settings.AGENT_TOOL_TIMEOUT,
        )
    except Exception as e:
        logger.error(
            "call_model failed",
            extra={"error": str(e), "workspace_id": state["workspace_id"]},
        )
        raise

    response_message = response.choices[0].message

    # Convert to LangChain AIMessage format for add_messages reducer
    tool_calls = []
    if hasattr(response_message, "tool_calls") and response_message.tool_calls:
        for tc in response_message.tool_calls:
            args_raw = tc.function.arguments or "{}"
            try:
                parsed_args = json.loads(args_raw)
            except json.JSONDecodeError:
                parsed_args = {}
            tool_calls.append(
                {
                    "id": tc.id,
                    "name": tc.function.name,
                    "args": parsed_args,
                }
            )

    ai_msg = AIMessage(
        content=response_message.content or "",
        tool_calls=tool_calls,
    )

    logger.debug(
        "call_model complete",
        extra={
            "workspace_id": state["workspace_id"],
            "steps_taken": state["steps_taken"] + 1,
            "has_tool_calls": bool(tool_calls),
        },
    )

    return {
        "messages": [ai_msg],
        "steps_taken": state["steps_taken"] + 1,
    }


async def execute_tools(state: AgentState) -> dict[str, Any]:
    """
    Tool execution node: run tools called by the agent.

    Sets db_session_var context variable before execution so
    mutation tools (create_note, update_note) can access the session.
    """
    tool_node = ToolNode(get_note_tools())
    token = db_session_var.set(None)
    try:
        return await tool_node.ainvoke(state)
    finally:
        db_session_var.reset(token)


def should_continue(state: AgentState) -> str:
    """
    Conditional routing function — determines next node after agent call.

    Returns:
      "tools"  → agent has tool calls — execute them
      "end"    → agent produced final answer — exit
      "limit"  → AGENT_MAX_ITERATIONS exceeded — force exit
    """
    settings = get_settings()

    if state["steps_taken"] >= settings.AGENT_MAX_ITERATIONS:
        logger.warning(
            "Agent iteration limit reached",
            extra={
                "steps_taken": state["steps_taken"],
                "max_iterations": settings.AGENT_MAX_ITERATIONS,
                "workspace_id": state.get("workspace_id"),
            },
        )
        return "limit"

    last_message = state["messages"][-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"

    return "end"


def compile_workspace_graph():
    """
    Compile the workspace assistant StateGraph.

    Called once by get_workspace_assistant(). Result cached.
    Attempts to use checkpointer — falls back to no persistence
    if checkpointer not initialized (degraded mode, logs warning).
    """
    graph = StateGraph(AgentState)

    graph.add_node("agent", call_model)
    graph.add_node("tools", execute_tools)

    graph.add_edge(START, "agent")
    graph.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END,
            "limit": END,
        },
    )
    graph.add_edge("tools", "agent")

    # Attempt to use checkpointer — non-fatal if unavailable
    try:
        from ai.memory.checkpointer import get_graph_checkpointer

        checkpointer = get_graph_checkpointer()
        compiled = graph.compile(checkpointer=checkpointer)
        logger.info("Workspace assistant graph compiled with checkpointer")
    except RuntimeError:
        logger.warning(
            "Checkpointer not available — compiling graph without persistence. "
            "Call init_checkpointer() in lifespan startup to enable."
        )
        compiled = graph.compile()

    return compiled


def get_workspace_assistant():
    """
    Return the compiled workspace assistant graph (singleton).

    Lazy initialization — compiled on first call, cached thereafter.
    Thread-safe for asyncio (single-threaded event loop).
    """
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = compile_workspace_graph()
    return _compiled_graph
