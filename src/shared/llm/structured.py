"""
Structured LLM completion with retry and JSON salvage (Slice 7.5).

Import law: config, litellm, pydantic, tenacity, stdlib only.
"""
from __future__ import annotations

import logging
import re
import time
from typing import Any

import litellm
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config import get_settings
from shared.llm.retry import RETRYABLE_EXCEPTIONS

logger = logging.getLogger(__name__)


class StructuredLLMParseError(ValueError):
    """Raised when structured output cannot be parsed after salvage attempts."""


def extract_json_blob(raw: str) -> str:
    """
    Extract a JSON object from model output that may include markdown fences
    or a preamble (e.g. Gemini's "Here is the JSON").
    """
    text = raw.strip()
    if not text:
        return text

    fence_match = re.search(
        r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL | re.IGNORECASE
    )
    if fence_match:
        text = fence_match.group(1).strip()

    text = re.sub(
        r"^here(?:'s| is) the json[:\s]*",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()
    text = re.sub(r"^json[:\s]*", "", text, flags=re.IGNORECASE).strip()

    start = text.find("{")
    if start == -1:
        return text

    depth = 0
    for i, ch in enumerate(text[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]

    return text[start:]


def parse_structured_response(raw: str, schema: type[BaseModel]) -> BaseModel:
    """
    Parse LLM text into a Pydantic model.

    Tries direct validation first, then JSON salvage on failure.
    """
    try:
        return schema.model_validate_json(raw)
    except Exception:
        salvaged = extract_json_blob(raw)
        try:
            return schema.model_validate_json(salvaged)
        except Exception as e:
            raise StructuredLLMParseError(
                f"Could not parse {schema.__name__} from LLM output"
            ) from e


async def acompletion_structured(
    *,
    messages: list[dict[str, Any]],
    schema: type[BaseModel],
    max_tokens: int,
    model: str | None = None,
    temperature: float = 0.0,
    **kwargs: Any,
) -> BaseModel:
    """
    Structured LiteLLM completion with retry, JSON salvage, and Pydantic validation.
    """
    settings = get_settings()
    resolved_model = model or settings.LLM_MODEL
    schema_name = schema.__name__
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
        return await litellm.acompletion(
            model=resolved_model,
            messages=messages,
            response_format=schema,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

    try:
        response = await _invoke()
    except RETRYABLE_EXCEPTIONS as e:
        logger.error(
            "[AUTOMATION_LLM_RETRY_EXHAUSTED] Structured LLM retries exhausted",
            extra={
                "model": resolved_model,
                "schema_name": schema_name,
                "error": str(e),
                "retry_count": max(0, attempt - 1),
            },
        )
        raise

    raw = response.choices[0].message.content or ""
    try:
        parsed = parse_structured_response(raw, schema)
    except StructuredLLMParseError:
        logger.warning(
            "[AUTOMATION_LLM_PARSE_FAIL] Could not parse structured output",
            extra={
                "model": resolved_model,
                "schema_name": schema_name,
                "raw_preview": raw[:500],
            },
        )
        raise

    latency_ms = (time.monotonic() - start) * 1000
    logger.debug(
        "acompletion_structured complete",
        extra={
            "model": resolved_model,
            "schema_name": schema_name,
            "latency_ms": round(latency_ms, 2),
            "retry_count": max(0, attempt - 1),
        },
    )
    return parsed
