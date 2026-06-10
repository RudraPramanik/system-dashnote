"""Shared LiteLLM helpers (provider env, structured calls — Slice 7.5)."""

from shared.llm.env import configure_litellm_env
from shared.llm.retry import (
    FATAL_EXCEPTIONS,
    RETRYABLE_EXCEPTIONS,
    acompletion_with_retry,
    is_fatal,
    is_retryable,
)
from shared.llm.structured import (
    StructuredLLMParseError,
    acompletion_structured,
    extract_json_blob,
    parse_structured_response,
)

__all__ = [
    "FATAL_EXCEPTIONS",
    "RETRYABLE_EXCEPTIONS",
    "StructuredLLMParseError",
    "acompletion_structured",
    "acompletion_with_retry",
    "configure_litellm_env",
    "extract_json_blob",
    "is_fatal",
    "is_retryable",
    "parse_structured_response",
]
