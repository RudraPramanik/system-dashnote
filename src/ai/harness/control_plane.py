"""Harness control plane (Blueprint 9H.5.3).

One module chat and agent routes use for trusted-context bind, AI budget
gate, and provider-unavailable helpers. Routes stay HTTP/SSE adapters.

Does not import FastAPI. Does not call repositories or NoteService.
Cooldownoldown stays in shared.llm.fallback. Mid-turn agent budget checks stay
in the model node (9H.4.2).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from redis.asyncio import Redis

from ai.harness.budget_check import (
    OUTCOME_ALLOWED,
    OUTCOME_DENIED,
    OUTCOME_FAIL_OPEN,
    BudgetDecision,
    BudgetDenied,
    budget_denied_from,
    budget_error_payload,
    budget_redis_var,
    consume_ai_request_budget,
    denial_message,
    retry_after_header,
)
from ai.harness.context import HarnessContext, harness_context_var
from shared.llm.fallback import (
    LLM_UNAVAILABLE_MESSAGE,
    LLMUnavailableError,
    is_model_gone,
)

__all__ = [
    "OUTCOME_ALLOWED",
    "OUTCOME_DENIED",
    "OUTCOME_FAIL_OPEN",
    "BoundAgentHarness",
    "BudgetDecision",
    "BudgetDenied",
    "LLM_UNAVAILABLE_MESSAGE",
    "LLMUnavailableError",
    "bind_agent_harness",
    "budget_denied_from",
    "budget_error_payload",
    "denial_message",
    "gate_ai_request_budget",
    "is_provider_unavailable",
    "provider_unavailable_message",
    "reset_agent_harness",
    "retry_after_header",
]


@dataclass(frozen=True)
class BoundAgentHarness:
    """Tokens for harness context and optional mid-turn budget Redis binding."""

    harness_token: Any
    budget_token: Any | None = None


def bind_agent_harness(
    *,
    workspace_id: str,
    user_id: str,
    role: str,
    redis: Redis | None = None,
    with_budget_redis: bool = True,
    trace_id: str | None = None,
) -> BoundAgentHarness:
    """Freeze JWT tenant into HarnessContext; optionally bind budget Redis."""
    harness_token = harness_context_var.set(
        HarnessContext(
            workspace_id=workspace_id,
            user_id=user_id,
            role=role,
            trace_id=trace_id,
        )
    )
    budget_token = budget_redis_var.set(redis) if with_budget_redis else None
    return BoundAgentHarness(
        harness_token=harness_token,
        budget_token=budget_token,
    )


def reset_agent_harness(bound: BoundAgentHarness) -> None:
    """Reset budget Redis binding (if any) then harness context."""
    if bound.budget_token is not None:
        budget_redis_var.reset(bound.budget_token)
    harness_context_var.reset(bound.harness_token)


async def gate_ai_request_budget(
    redis: Redis | None,
    user_id: str,
    workspace_id: str,
) -> BudgetDecision:
    """Run the existing AI request-ceiling check. Fail-open on Redis errors."""
    return await consume_ai_request_budget(redis, user_id, workspace_id)


def is_provider_unavailable(exc: BaseException) -> bool:
    """True when the exception is total provider exhaustion or model-gone."""
    return isinstance(exc, LLMUnavailableError) or is_model_gone(exc)


def provider_unavailable_message(_exc: BaseException | None = None) -> str:
    """User-safe unavailable copy shared by chat and agent routes."""
    return LLM_UNAVAILABLE_MESSAGE
