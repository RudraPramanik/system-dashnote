"""
Walk LLM_MODEL then LLM_MODEL_FALLBACKS when a hosted id is gone (HTTP 410),
rate-limited (HTTP 429), upstream 5xx, or exceeds the per-candidate wall clock.

Transient 429/5xx enter a process-local cooldown (LLM_PROVIDER_COOLDOWN_SECONDS).
Model-gone stays a durable skip. Cooldown is not Redis.

Import law: config, litellm, shared.llm.retry, observability.metrics, stdlib only.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import litellm

from config import get_settings
from observability.metrics import inc_llm_fallback
from shared.llm.retry import acompletion_with_retry

logger = logging.getLogger(__name__)

LLM_UNAVAILABLE_MESSAGE = "LLM temporarily unavailable; retry shortly"

_cached_model: str | None = None
_skip: set[str] = set()
_cooldown_until: dict[str, float] = {}


class LLMUnavailableError(RuntimeError):
    """Raised when every configured LLM candidate is gone or unreachable."""

    def __init__(self, message: str = LLM_UNAVAILABLE_MESSAGE) -> None:
        super().__init__(message)


class _ReplayStream:
    """Async iterator that replays the first chunk then continues the source."""

    def __init__(self, first: Any, rest: Any, *, empty: bool) -> None:
        self._first = first
        self._rest = rest
        self._empty = empty
        self._sent_first = False

    def __aiter__(self) -> _ReplayStream:
        return self

    async def __anext__(self) -> Any:
        if self._empty and not self._sent_first:
            self._sent_first = True
            raise StopAsyncIteration
        if not self._sent_first:
            self._sent_first = True
            return self._first
        return await self._rest.__anext__()


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


def is_rate_limited(exc: BaseException) -> bool:
    """True when the provider rejected the candidate for quota / HTTP 429."""
    if isinstance(exc, litellm.exceptions.RateLimitError):
        return True
    status = getattr(exc, "status_code", None)
    if status == 429:
        return True
    msg = str(exc).lower()
    return (
        " 429" in msg
        or "error code: 429" in msg
        or "rate limit" in msg
        or "rate-limit" in msg
        or "ratelimit" in msg
        or "quota exceeded" in msg
        or "resource exhausted" in msg
    )


def is_upstream_server_error(exc: BaseException) -> bool:
    """True when the provider returned HTTP 5xx / equivalent server failure."""
    internal = getattr(litellm.exceptions, "InternalServerError", None)
    if internal is not None and isinstance(exc, internal):
        return True
    service = getattr(litellm.exceptions, "ServiceUnavailableError", None)
    if service is not None and isinstance(exc, service):
        return True
    status = getattr(exc, "status_code", None)
    if isinstance(status, int) and 500 <= status <= 599:
        return True
    msg = str(exc).lower()
    return (
        "error code: 500" in msg
        or "error code: 502" in msg
        or "error code: 503" in msg
        or "error code: 504" in msg
        or "internal server error" in msg
        or "bad gateway" in msg
        or "service unavailable" in msg
        or "gateway timeout" in msg
    )


def warn_if_no_distinct_llm_fallback() -> None:
    """Soft boot warning when FALLBACKS are set but dedupe leaves one candidate.

    Does not raise — API/worker must stay up. Duplicate primary=fallback is not
    a working hatch (see llm-resilience distinct-hatch requirement).
    """
    settings = get_settings()
    raw_fallbacks = [
        m.strip() for m in settings.LLM_MODEL_FALLBACKS.split(",") if m.strip()
    ]
    candidates = settings.llm_model_candidates
    if raw_fallbacks and len(candidates) < 2:
        logger.warning(
            "LLM_MODEL_FALLBACKS collapses to a single candidate after dedupe; "
            "not a distinct hatch — set a different live id before calling AI healthy",
            extra={
                "primary": settings.LLM_MODEL,
                "fallbacks": settings.LLM_MODEL_FALLBACKS,
                "candidates": candidates,
            },
        )


def reset_fallback_state() -> None:
    """Test helper — clear process cache, durable skip, and cooldowns."""
    global _cached_model
    _cached_model = None
    _skip.clear()
    _cooldown_until.clear()


def cached_llm_model() -> str | None:
    return _cached_model


def _cooldown_seconds(settings: Any) -> float:
    raw = getattr(settings, "LLM_PROVIDER_COOLDOWN_SECONDS", 60)
    if isinstance(raw, (int, float)) and not isinstance(raw, bool) and raw > 0:
        return float(raw)
    return 60.0


def _mark_cooldown(model: str) -> None:
    """Skip model for LLM_PROVIDER_COOLDOWN_SECONDS (process-local)."""
    global _cached_model
    seconds = _cooldown_seconds(get_settings())
    _cooldown_until[model] = time.monotonic() + seconds
    if _cached_model == model:
        _cached_model = None


def _is_cooling(model: str) -> bool:
    until = _cooldown_until.get(model)
    if until is None:
        return False
    if time.monotonic() >= until:
        _cooldown_until.pop(model, None)
        return False
    return True


def _remember(model: str) -> None:
    global _cached_model
    _cached_model = model
    _skip.discard(model)
    _cooldown_until.pop(model, None)


def _mark_gone(model: str) -> None:
    global _cached_model
    _skip.add(model)
    _cooldown_until.pop(model, None)
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
    # Filter after cache reorder so a cooling cached primary cannot win.
    # Empty means unavailable — do not re-loop cooling/skipped ids.
    return [m for m in ordered if m not in _skip and not _is_cooling(m)]


def _wall_clock(settings: Any) -> float:
    raw = getattr(settings, "AGENT_TOOL_TIMEOUT", 30)
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        return float(raw)
    return 30.0


def _disable_nvidia_thinking(call_kwargs: dict[str, Any]) -> None:
    """Nemotron thinking traces can ignore LLM_MAX_TOKENS; keep agent hops bounded."""
    model = str(call_kwargs.get("model") or "")
    if not model.startswith("nvidia_nim/"):
        return
    extra = call_kwargs.get("extra_body")
    extra_body: dict[str, Any] = dict(extra) if isinstance(extra, dict) else {}
    chat_kwargs = extra_body.get("chat_template_kwargs")
    merged = dict(chat_kwargs) if isinstance(chat_kwargs, dict) else {}
    merged["enable_thinking"] = False
    extra_body["chat_template_kwargs"] = merged
    call_kwargs["extra_body"] = extra_body


async def _first_chunk_stream(stream: Any, wall: float) -> Any:
    aiter = stream.__aiter__()
    try:
        first = await asyncio.wait_for(aiter.__anext__(), timeout=wall)
    except StopAsyncIteration:
        return _ReplayStream(None, aiter, empty=True)
    return _ReplayStream(first, aiter, empty=False)


async def _invoke_candidate(
    *, stream: bool, call_kwargs: dict[str, Any], wall: float
) -> Any:
    if stream:
        result = await asyncio.wait_for(
            litellm.acompletion(**call_kwargs), timeout=wall
        )
        if hasattr(result, "__aiter__"):
            return await _first_chunk_stream(result, wall)
        return result
    return await asyncio.wait_for(
        acompletion_with_retry(**call_kwargs), timeout=wall
    )


async def acompletion_with_fallback(**kwargs: Any) -> Any:
    """
    litellm.acompletion with model-gone, rate-limit, 5xx, and wall-clock fallback.

    Non-stream calls use acompletion_with_retry (transient errors) inside
    asyncio.wait_for(AGENT_TOOL_TIMEOUT). Stream calls use litellm.acompletion
    and wait for the first chunk under the same budget. Exhausted 429/5xx walk
    to the next candidate and enter process-local cooldown; they are not logged
    as model-gone.
    """
    stream = bool(kwargs.get("stream", False))
    models = _candidates(
        kwargs.get("model") if isinstance(kwargs.get("model"), str) else None
    )
    settings = get_settings()
    wall = _wall_clock(settings)
    last_exc: BaseException | None = None

    if not models:
        logger.error("All LLM candidates unavailable", extra={"tried": [], "error": ""})
        raise LLMUnavailableError()

    for model in models:
        call_kwargs = {**kwargs, "model": model}
        _disable_nvidia_thinking(call_kwargs)
        try:
            result = await _invoke_candidate(
                stream=stream, call_kwargs=call_kwargs, wall=wall
            )
            _remember(model)
            return result
        except asyncio.TimeoutError as exc:
            last_exc = exc
            inc_llm_fallback()
            logger.warning(
                "LLM candidate timed out; trying next",
                extra={"model": model, "timeout_s": wall},
            )
            continue
        except Exception as exc:
            last_exc = exc
            if is_model_gone(exc):
                inc_llm_fallback()
                logger.warning(
                    "LLM model gone; trying next candidate",
                    extra={"model": model, "error": str(exc)[:240]},
                )
                _mark_gone(model)
                continue
            if is_rate_limited(exc):
                inc_llm_fallback()
                logger.warning(
                    "LLM candidate rate-limited; cooling down then trying next",
                    extra={"model": model, "error": str(exc)[:240]},
                )
                _mark_cooldown(model)
                continue
            if is_upstream_server_error(exc):
                inc_llm_fallback()
                logger.warning(
                    "LLM candidate upstream 5xx; cooling down then trying next",
                    extra={"model": model, "error": str(exc)[:240]},
                )
                _mark_cooldown(model)
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
