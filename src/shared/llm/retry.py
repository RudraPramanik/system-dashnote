"""
Shared LiteLLM retry policy for completion calls (Slice 7.5).

Import law: config, litellm, tenacity, stdlib only.
"""
from __future__ import annotations

import logging
import time
from typing import Any

import litellm
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config import get_settings

logger = logging.getLogger(__name__)

RETRYABLE_EXCEPTIONS = (
    litellm.exceptions.RateLimitError,
    litellm.exceptions.Timeout,
    litellm.exceptions.ServiceUnavailableError,
    litellm.exceptions.APIConnectionError,
)

FATAL_EXCEPTIONS = (
    litellm.exceptions.AuthenticationError,
    litellm.exceptions.BadRequestError,
    litellm.exceptions.NotFoundError,
)


def is_retryable(exc: BaseException) -> bool:
    """Return True if the exception is transient and safe to retry."""
    return isinstance(exc, RETRYABLE_EXCEPTIONS)


def is_fatal(exc: BaseException) -> bool:
    """Return True if the exception is permanent — do not retry."""
    return isinstance(exc, FATAL_EXCEPTIONS)


async def acompletion_with_retry(**kwargs: Any) -> Any:
    """
    Call litellm.acompletion with tenacity retry on transient errors.

    Re-raises the last exception after all retries are exhausted.
    """
    settings = get_settings()
    model = kwargs.get("model", settings.LLM_MODEL)
    start = time.monotonic()
    attempt = 0

    @retry(
        stop=stop_after_attempt(settings.LLM_MAX_RETRIES),
        wait=wait_exponential(
            multiplier=1,
            min=settings.LLM_RETRY_MIN_WAIT,
            max=settings.LLM_RETRY_MAX_WAIT,
        ),
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        reraise=True,
    )
    async def _invoke() -> Any:
        nonlocal attempt
        attempt += 1
        return await litellm.acompletion(**kwargs)

    try:
        response = await _invoke()
        latency_ms = (time.monotonic() - start) * 1000
        logger.debug(
            "acompletion_with_retry complete",
            extra={
                "model": model,
                "latency_ms": round(latency_ms, 2),
                "retry_count": max(0, attempt - 1),
            },
        )
        return response
    except RETRYABLE_EXCEPTIONS as e:
        logger.error(
            "[AUTOMATION_LLM_RETRY_EXHAUSTED] LLM retries exhausted",
            extra={
                "model": model,
                "error": str(e),
                "retry_count": max(0, attempt - 1),
            },
        )
        raise
