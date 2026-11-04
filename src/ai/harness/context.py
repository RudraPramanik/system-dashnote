"""
HarnessContext — trusted tenant identity for one agent invoke.

Built from JWT RequestContext (never from model tool args). Tools read
workspace_id / user_id / role only via harness_context_var.

IMPORT LAW: stdlib / typing only — no FastAPI, no SQLAlchemy.
"""
from __future__ import annotations

import contextvars
from dataclasses import dataclass


MISSING_HARNESS_MESSAGE = (
    "Error: forbidden — trusted harness context missing. Tool denied."
)


@dataclass(frozen=True)
class HarnessContext:
    """Trusted session object for the agent harness (9H.1+)."""

    workspace_id: str
    user_id: str
    role: str
    trace_id: str | None = None
    # Placeholder for 9H.4 AI budgets — unused until that phase.
    remaining_budget: int | None = None


harness_context_var: contextvars.ContextVar[HarnessContext | None] = (
    contextvars.ContextVar("agent_harness_context", default=None)
)


def require_harness_context() -> HarnessContext | None:
    """Return bound HarnessContext, or None when missing (caller must fail closed)."""
    return harness_context_var.get()
