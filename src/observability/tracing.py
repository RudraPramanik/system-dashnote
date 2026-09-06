"""
Reusable async tracing for RAG and future AI services.

Import law: stdlib, observability.langfuse_client only.
No FastAPI, SQLAlchemy, or domain modules.
"""
from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Protocol

from observability.langfuse_client import get_langfuse_client

logger = logging.getLogger(__name__)


class _TraceLike(Protocol):
    def span(self, name: str, input: dict | None = None) -> Any: ...
    def update(self, *, output: dict | None = None, **kwargs: Any) -> None: ...


class _SpanLike(Protocol):
    def update(self, *, output: dict | None = None, **kwargs: Any) -> None: ...


class _NoOpSpan:
    """Stand-in span when Langfuse is disabled or tracing fails."""

    def update(self, *, output: dict | None = None, **kwargs: Any) -> None:
        return None


class _NoOpTrace:
    """Stand-in trace when Langfuse is disabled or tracing fails."""

    _noop = True

    def span(self, name: str, input: dict | None = None) -> _NoOpSpan:
        return _NoOpSpan()

    def update(self, *, output: dict | None = None, **kwargs: Any) -> None:
        return None


class _LangfuseSpanHandle:
    def __init__(self, observation: Any) -> None:
        self._obs = observation
        self._output: dict[str, Any] = {}

    def update(self, *, output: dict | None = None, **kwargs: Any) -> None:
        try:
            if output:
                self._output.update(output)
            if kwargs:
                self._obs.update(**kwargs)
        except Exception:
            logger.debug("Langfuse span update failed", exc_info=True)

    def _finalize(self, latency_ms: float) -> None:
        try:
            merged = {**self._output, "latency_ms": latency_ms}
            self._obs.update(output=merged)
            self._obs.end()
        except Exception:
            logger.debug("Langfuse span finalize failed", exc_info=True)


class _LangfuseTraceHandle:
    _noop = False

    def __init__(self, observation: Any) -> None:
        self._obs = observation

    def span(self, name: str, input: dict | None = None) -> _SpanLike:
        try:
            child = self._obs.start_observation(name=name, input=input or {})
            return _LangfuseSpanHandle(child)
        except Exception:
            logger.debug("Langfuse trace.span failed", exc_info=True)
            return _NoOpSpan()

    def update(self, *, output: dict | None = None, **kwargs: Any) -> None:
        try:
            if output is not None:
                self._obs.update(output=output, **kwargs)
            elif kwargs:
                self._obs.update(**kwargs)
        except Exception:
            logger.debug("Langfuse trace update failed", exc_info=True)


def _is_noop_parent(parent: Any) -> bool:
    return getattr(parent, "_noop", False) or parent is None


def _start_child_observation(parent: Any, name: str, input_data: dict) -> Any | None:
    obs = getattr(parent, "_obs", None)
    if obs is None:
        return None
    kwargs: dict[str, Any] = {"name": name, "input": input_data}
    if name == "llm_generation":
        kwargs["as_type"] = "generation"
        model = input_data.get("model")
        if model:
            kwargs["model"] = model
    return obs.start_observation(**kwargs)


@asynccontextmanager
async def rag_trace(name: str, metadata: dict) -> AsyncIterator[_TraceLike]:
    """
    Open a Langfuse trace (root observation). Flushes the client on exit.
    Never raises — yields a no-op trace when Langfuse is unavailable.
    """
    client = None
    trace_obs = None
    handle: _TraceLike = _NoOpTrace()

    try:
        client = get_langfuse_client()
        if client is not None:
            trace_obs = client.start_observation(
                name=name,
                input=metadata,
                metadata=metadata,
            )
            handle = _LangfuseTraceHandle(trace_obs)
    except Exception:
        logger.debug("rag_trace setup failed", exc_info=True)
        handle = _NoOpTrace()

    try:
        yield handle
    finally:
        try:
            if trace_obs is not None:
                trace_obs.end()
        except Exception:
            logger.debug("rag_trace end failed", exc_info=True)
        try:
            if client is not None:
                client.flush()
        except Exception:
            logger.debug("rag_trace flush failed", exc_info=True)


@asynccontextmanager
async def rag_span(
    parent: Any,
    name: str,
    input_data: dict,
) -> AsyncIterator[_SpanLike]:
    """
    Open a child span under a rag_trace parent. Records latency_ms on exit.
    Never raises — yields a no-op span when parent is a no-op or setup fails.
    """
    started = time.monotonic()
    span_obs = None
    handle: _SpanLike = _NoOpSpan()

    if not _is_noop_parent(parent):
        try:
            span_obs = _start_child_observation(parent, name, input_data)
            if span_obs is not None:
                handle = _LangfuseSpanHandle(span_obs)
        except Exception:
            logger.debug("rag_span setup failed", exc_info=True)
            handle = _NoOpSpan()

    try:
        yield handle
    finally:
        latency_ms = round((time.monotonic() - started) * 1000, 2)
        if isinstance(handle, _LangfuseSpanHandle) and span_obs is not None:
            handle._finalize(latency_ms)
        elif span_obs is not None:
            try:
                span_obs.update(output={"latency_ms": latency_ms})
                span_obs.end()
            except Exception:
                logger.debug("rag_span finalize failed", exc_info=True)


def score_trace(
    parent: Any,
    *,
    name: str,
    value: float | int | str,
    comment: str | None = None,
) -> None:
    """
    Attach a score to the current Langfuse observation/trace.
    Soft no-op when Langfuse is disabled or the call fails.
    """
    if _is_noop_parent(parent):
        return
    try:
        obs = getattr(parent, "_obs", None)
        if obs is None:
            return
        kwargs: dict[str, Any] = {"name": name, "value": value}
        if comment:
            kwargs["comment"] = comment
        score_fn = getattr(obs, "score", None)
        if callable(score_fn):
            score_fn(**kwargs)
            return
        client = get_langfuse_client()
        if client is None:
            return
        obs_id = getattr(obs, "id", None) or getattr(obs, "trace_id", None)
        if obs_id is None:
            return
        client.score(trace_id=str(obs_id), **kwargs)
    except Exception:
        logger.debug("Langfuse score_trace failed", exc_info=True)


def retrieval_depth_payload(results: list[Any]) -> dict[str, Any]:
    """
    Build span output with retrieved identities + scores (not counts only).
    Accepts SearchResult-like objects or dicts with chunk_id/note_id/score.
    """
    items: list[dict[str, Any]] = []
    for result in results:
        if isinstance(result, dict):
            items.append(
                {
                    "chunk_id": result.get("chunk_id"),
                    "note_id": result.get("note_id"),
                    "file_id": result.get("file_id"),
                    "source_type": result.get("source_type"),
                    "score": result.get("score"),
                }
            )
            continue
        items.append(
            {
                "chunk_id": getattr(result, "chunk_id", None),
                "note_id": getattr(result, "note_id", None),
                "file_id": getattr(result, "file_id", None),
                "source_type": getattr(result, "source_type", None),
                "score": getattr(result, "score", None),
            }
        )
    return {
        "chunks_retrieved": len(items),
        "retrieved": items,
        "chunk_ids": [i.get("chunk_id") for i in items if i.get("chunk_id")],
        "note_ids": list({i.get("note_id") for i in items if i.get("note_id")}),
        "scores": [i.get("score") for i in items if i.get("score") is not None],
    }
