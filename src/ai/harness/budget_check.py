"""AI request-ceiling check (Blueprint 9H.4.2).

Counts one user-minute key and one workspace-day key per model completion.
Does not import FastAPI or core. Does not write the token key.

Redis connection errors fail open. A blank identity fails closed.
"""
from __future__ import annotations

import contextvars
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import RedisError

from ai.harness.budget import budget_keys
from config import get_settings
from observability.metrics import inc_ai_budget_outcome

logger = logging.getLogger(__name__)

OUTCOME_ALLOWED = "allowed"
OUTCOME_DENIED = "denied"
OUTCOME_FAIL_OPEN = "fail_open"

MINUTE_TTL_SECONDS = 120
DAY_TTL_SECONDS = 48 * 60 * 60

RETRY_SHORTLY = "AI request limit reached. Retry shortly."

budget_redis_var: contextvars.ContextVar[Redis | None] = contextvars.ContextVar(
    "ai_budget_redis",
    default=None,
)


@dataclass(frozen=True)
class BudgetDecision:
    outcome: str
    retry_after: int | None = None


class BudgetDenied(Exception):
    """Raised by the agent model node so routes can refuse without a provider call."""

    def __init__(self, decision: BudgetDecision) -> None:
        self.decision = decision
        super().__init__(denial_message(decision))


def denial_message(decision: BudgetDecision) -> str:
    if decision.retry_after is None:
        return RETRY_SHORTLY
    return f"AI request limit reached. Retry after {decision.retry_after} seconds."


def retry_after_header(decision: BudgetDecision) -> dict[str, str] | None:
    if decision.retry_after is None:
        return None
    return {"Retry-After": str(decision.retry_after)}


def budget_error_payload(decision: BudgetDecision) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "type": "error",
        "code": "budget_exceeded",
        "message": denial_message(decision),
    }
    if decision.retry_after is not None:
        payload["retry_after"] = decision.retry_after
    return payload


def budget_denied_from(exc: BaseException) -> BudgetDenied | None:
    """Return a budget denial on the exception or one wrapped cause."""
    if isinstance(exc, BudgetDenied):
        return exc
    cause = exc.__cause__
    if isinstance(cause, BudgetDenied):
        return cause
    return None


async def consume_ai_request_budget(
    redis: Redis | None,
    user_id: str,
    workspace_id: str,
) -> BudgetDecision:
    """Increment request ceilings. Does not increment the token key."""
    user_key, day_key, _token_key = budget_keys(
        user_id,
        workspace_id,
        datetime.now(timezone.utc),
    )
    if user_key is None or day_key is None:
        inc_ai_budget_outcome(OUTCOME_DENIED)
        return BudgetDecision(outcome=OUTCOME_DENIED)

    if redis is None:
        logger.warning("AI budget Redis client missing (fail open)")
        inc_ai_budget_outcome(OUTCOME_FAIL_OPEN)
        return BudgetDecision(outcome=OUTCOME_FAIL_OPEN)

    settings = get_settings()
    try:
        user_count, user_ttl = await _incr_window(redis, user_key, MINUTE_TTL_SECONDS)
        day_count, day_ttl = await _incr_window(redis, day_key, DAY_TTL_SECONDS)
    except RedisError as exc:
        logger.warning("AI budget Redis error (fail open): %s", str(exc)[:200])
        inc_ai_budget_outcome(OUTCOME_FAIL_OPEN)
        return BudgetDecision(outcome=OUTCOME_FAIL_OPEN)

    user_over = user_count > settings.AI_USER_REQUESTS_PER_MINUTE
    day_over = day_count > settings.AI_WORKSPACE_REQUESTS_PER_DAY
    if not user_over and not day_over:
        inc_ai_budget_outcome(OUTCOME_ALLOWED)
        return BudgetDecision(outcome=OUTCOME_ALLOWED)

    windows = []
    if user_over and user_ttl is not None:
        windows.append(user_ttl)
    if day_over and day_ttl is not None:
        windows.append(day_ttl)
    retry_after = max(windows) if windows else None
    inc_ai_budget_outcome(OUTCOME_DENIED)
    return BudgetDecision(outcome=OUTCOME_DENIED, retry_after=retry_after)


async def _incr_window(redis: Redis, key: str, ttl_seconds: int) -> tuple[int, int | None]:
    current = int(await redis.incr(key))
    if current == 1:
        await redis.expire(key, ttl_seconds)
    raw_ttl = await redis.ttl(key)
    ttl = int(raw_ttl) if raw_ttl is not None and int(raw_ttl) > 0 else None
    return current, ttl
