"""
Walk LLM_MODEL then LLM_MODEL_FALLBACKS when a hosted id is gone (HTTP 410).

Import law: config, litellm, shared.llm.retry, stdlib only.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import litellm

from config import get_settings
from shared.llm.retry import acompletion_with_retry

logger = logging.getLogger(__name__)

LLM_UNAVAILABLE_MESSAGE = "LLM temporarily unavailable; retry shortly"

_cached_model: str | None = None
_skip: set[str] = set()


class LLMUnavailableError(RuntimeError):
    """Raised when every configured LLM candidate is gone or unreachable."""

    def __init__(self, message: str = LLM_UNAVAILABLE_MESSAGE) -> None:
        super().__init__(message)


def is_model_gone(exc: BaseException) -> bool:
    """True when the provider retired or cannot find the model id."""
    if isinstance(exc, litellm.exceptions.NotFoundError):
        return True
    status = getattr(exc, "status_code", None)
    if status == 410:
        return True
    msg = str(exc).lower()
    return (
        " 410" in msg
        or "error code: 410" in msg
        or "end of life" in msg
        or "no longer available" in msg
    )


def reset_fallback_state() -> None:
    """Test helper — clear process cache."""
    global _cached_model
    _cached_model = None
    _skip.clear()


def cached_llm_model() -> str | None:
    return _cached_model


def _remember(model: str) -> None:
    global _cached_model
    _cached_model = model
    _skip.discard(model)


def _mark_gone(model: str) -> None:
    global _cached_model
    _skip.add(model)
    if _cached_model == model:
        _cached_model = None


def _candidates(explicit: str | None) -> list[str]:
    settings = get_settings()
    ordered = settings.llm_model_candidates
    if explicit and explicit not in ordered:
        ordered = [explicit, *ordered]
    if _cached_model and _cached_model in ordered:
        rest = [m for m in ordered if m != _cached_model]
        ordered = [_cached_model, *rest]
    return [m for m in ordered if m not in _skip] or list(ordered)


async def acompletion_with_fallback(**kwargs: Any) -> Any:
    """
    litellm.acompletion with model-gone fallback.

    Non-stream calls use acompletion_with_retry (transient errors).
    Stream calls use litellm.acompletion directly.
    """
    stream = bool(kwargs.get("stream", False))
    models = _candidates(kwargs.get("model") if isinstance(kwargs.get("model"), str) else None)
    last_exc: BaseException | None = None

    for model in models:
        call_kwargs = {**kwargs, "model": model}
        try:
            if stream:
                result = await litellm.acompletion(**call_kwargs)
            else:
                result = await acompletion_with_retry(**call_kwargs)
            _remember(model)
            return result
        except Exception as exc:
            last_exc = exc
            if is_model_gone(exc):
                logger.warning(
                    "LLM model gone; trying next candidate",
                    extra={"model": model, "error": str(exc)[:240]},
                )
                _mark_gone(model)
                continue
            raise

    logger.error(
        "All LLM candidates unavailable",
        extra={"tried": models, "error": str(last_exc)[:240] if last_exc else ""},
    )
    raise LLMUnavailableError() from last_exc


async def resolve_llm_model(*, timeout: float = 15.0) -> str | None:
    """Best-effort startup / health probe. Never raises."""
    if _cached_model:
        return _cached_model
    try:
        await asyncio.wait_for(
            acompletion_with_fallback(
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=8,
                temperature=0.0,
            ),
            timeout=timeout,
        )
    except Exception as exc:
        logger.warning(
            "LLM candidate resolve failed",
            extra={"error": str(exc)[:240]},
        )
    return _cached_model
