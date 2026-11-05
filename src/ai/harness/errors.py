"""Stable tool-failure envelopes for the agent harness (Blueprint 9H.2).

Tool nodes return strings. Failures are one JSON object. Success stays prose.
``budget_exceeded`` is reserved for 9H.4 (no Redis check here).
``approval_required`` names the existing HITL pause; tools do not return it
instead of the SSE event.

IMPORT LAW: stdlib only.
"""
from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)

CODE_FORBIDDEN = "forbidden"
CODE_NOT_FOUND = "not_found"
CODE_BUDGET_EXCEEDED = "budget_exceeded"
CODE_APPROVAL_REQUIRED = "approval_required"
CODE_UPSTREAM = "upstream"

TOOL_ERROR_CODES = frozenset(
    {
        CODE_FORBIDDEN,
        CODE_NOT_FOUND,
        CODE_BUDGET_EXCEEDED,
        CODE_APPROVAL_REQUIRED,
        CODE_UPSTREAM,
    }
)

# Reserved codes. 9H.2 must not return these from a budget counter or a new SSE type.
RESERVED_TOOL_ERROR_CODES = frozenset(
    {CODE_BUDGET_EXCEEDED, CODE_APPROVAL_REQUIRED}
)

_UPSTREAM_FALLBACK = (
    '{"ok": false, "code": "upstream", "message": "Tool failed."}'
)


def tool_error(code: str, message: str) -> str:
    """Return a failure envelope. Never raises."""
    if code not in TOOL_ERROR_CODES:
        code = CODE_UPSTREAM
        message = "Tool failed."
    try:
        return json.dumps(
            {"ok": False, "code": code, "message": message},
            ensure_ascii=True,
        )
    except Exception:
        logger.exception("tool envelope serialization failed")
        return _UPSTREAM_FALLBACK
