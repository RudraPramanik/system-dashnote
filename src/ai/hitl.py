"""
HITL helpers for agent note mutations (LangGraph interrupt / resume).

IMPORT LAW: langgraph types, stdlib only — no FastAPI / SQLAlchemy.
"""
from __future__ import annotations

from typing import Any


MUTATION_TOOLS = frozenset({"create_note", "update_note"})


def build_approval_payload(
    *,
    tool: str,
    args: dict[str, Any],
    thread_id: str | None = None,
    interrupt_id: str | None = None,
) -> dict[str, Any]:
    """Locked SSE / JSON shape for approval_required."""
    # Client-facing args: omit huge blobs later if needed; keep tool args as-is.
    payload: dict[str, Any] = {
        "type": "approval_required",
        "tool": tool,
        "args": args,
    }
    if thread_id is not None:
        payload["thread_id"] = thread_id
    if interrupt_id is not None:
        payload["interrupt_id"] = interrupt_id
    return payload


def extract_interrupts(result: Any) -> list[Any]:
    """Pull Interrupt objects from ainvoke result or state snapshot."""
    if result is None:
        return []
    if isinstance(result, dict) and result.get("__interrupt__"):
        return list(result["__interrupt__"])
    interrupts = getattr(result, "interrupts", None)
    if interrupts:
        return list(interrupts)
    return []


def approval_event_from_interrupt(
    interrupt_obj: Any,
    *,
    thread_id: str,
) -> dict[str, Any]:
    """Merge LangGraph Interrupt id into locked approval_required payload."""
    value = getattr(interrupt_obj, "value", None)
    if not isinstance(value, dict):
        value = {"raw": value}
    interrupt_id = getattr(interrupt_obj, "id", None) or value.get("interrupt_id")
    tool = value.get("tool") or "unknown"
    args = value.get("args") if isinstance(value.get("args"), dict) else {}
    return build_approval_payload(
        tool=str(tool),
        args=args,
        thread_id=thread_id,
        interrupt_id=str(interrupt_id) if interrupt_id else None,
    )


def is_approved(decision: Any) -> bool:
    return isinstance(decision, dict) and decision.get("action") == "approve"
