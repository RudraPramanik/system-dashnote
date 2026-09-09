"""Thread title generation — deterministic truncate + optional LLM polish.

IMPORT LAW: config, shared.llm, stdlib only.
No FastAPI. No SQLAlchemy. No RequestContext.
"""
from __future__ import annotations

import asyncio
import logging
import re

from config import get_settings

logger = logging.getLogger(__name__)

_DISPLAY_MAX = 80
_STORE_MAX = 255
_ASSISTANT_SLICE = 500
_POLISH_TIMEOUT_SECONDS = 8.0


def deterministic_thread_title(user_text: str) -> str:
    """Whitespace-normalize and truncate the first user message for a title."""
    collapsed = " ".join((user_text or "").split())
    if not collapsed:
        return "New conversation"
    if len(collapsed) <= _DISPLAY_MAX:
        return collapsed[:_STORE_MAX]
    return collapsed[: _DISPLAY_MAX - 1].rstrip() + "…"


async def generate_thread_title(
    user_text: str,
    assistant_text: str | None = None,
) -> str:
    """
    Return a short thread title.

    Always starts from a deterministic truncate of the user message.
    When AI is enabled, may polish with a short LLM call using the user
    message and an optional assistant slice. On disable/timeout/failure,
    returns the deterministic title.
    """
    base = deterministic_thread_title(user_text)
    settings = get_settings()
    if not settings.ai_enabled:
        return base

    polished = await _polish_title(
        user_text=user_text,
        assistant_text=assistant_text,
        fallback=base,
    )
    return polished or base


async def _polish_title(
    *,
    user_text: str,
    assistant_text: str | None,
    fallback: str,
) -> str | None:
    prompt = (
        "Propose a short conversation title (max 80 characters). "
        "Reply with the title only — no quotes, no JSON, no explanation.\n\n"
        f"User:\n{(user_text or '')[:2000]}\n\n"
        f"Assistant (excerpt):\n{(assistant_text or '')[:_ASSISTANT_SLICE]}\n"
    )

    async def _call() -> str | None:
        try:
            from shared.llm.fallback import acompletion_with_fallback

            resp = await acompletion_with_fallback(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=64,
                temperature=0.0,
            )
            text = ""
            if hasattr(resp, "choices") and resp.choices:
                text = (resp.choices[0].message.content or "").strip()
            else:
                text = str(resp).strip()
            return _clean_polished(text, fallback=fallback)
        except Exception as e:
            logger.warning(
                "Thread title LLM polish failed",
                extra={"error": str(e)[:240]},
            )
            return None

    try:
        return await asyncio.wait_for(_call(), timeout=_POLISH_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        logger.warning("Thread title LLM polish timed out")
        return None


def _clean_polished(text: str, *, fallback: str) -> str | None:
    cleaned = (text or "").strip().strip("\"'`")
    cleaned = re.sub(r"\s+", " ", cleaned)
    # Drop accidental wrappers like Title: ...
    if cleaned.lower().startswith("title:"):
        cleaned = cleaned[6:].strip()
    if not cleaned:
        return None
    if cleaned.lower() in {"new conversation", "new session", "untitled"}:
        return fallback
    return cleaned[:_STORE_MAX]
