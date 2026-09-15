"""Observability package — structured logging, tracing, and metrics."""

from observability.langfuse_client import get_langfuse_client
from observability.logging import get_logger, setup_logging
from observability.metrics import (
    inc_agent_interrupt,
    inc_empty_retrieval,
    inc_llm_fallback,
)
from observability.tracing import (
    current_parent,
    current_trace_id,
    lookup_thread_trace,
    rag_span,
    rag_trace,
    remember_thread_trace,
    retrieval_depth_payload,
    score_by_trace_id,
    score_trace,
    span,
    start_trace,
)

__all__ = [
    "get_logger",
    "setup_logging",
    "get_langfuse_client",
    "start_trace",
    "span",
    "rag_trace",
    "rag_span",
    "retrieval_depth_payload",
    "score_trace",
    "score_by_trace_id",
    "current_parent",
    "current_trace_id",
    "lookup_thread_trace",
    "remember_thread_trace",
    "inc_empty_retrieval",
    "inc_agent_interrupt",
    "inc_llm_fallback",
]
