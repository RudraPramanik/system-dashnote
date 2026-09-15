"""
Reusable async tracing for RAG, agent, and future AI services.

Import law: stdlib, observability.langfuse_client only.
No FastAPI, SQLAlchemy, or domain modules.
"""
from __future__ import annotations

import contextvars
import logging
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Protocol

from observability.langfuse_client import get_langfuse_client

logger = logging.getLogger(__name__)

_GENERATION_NAMES = frozenset({"llm_generation", "call_model"})

_current_parent: contextvars.ContextVar[Any] = contextvars.ContextVar(
    "observability_trace_parent",
    default=None,
)
_thread_traces: dict[str, str] = {}


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
    observation_id: str | None = None
    trace_id: str | None = None

    def span(self, name: str, input: dict | None = None) -> _NoOpSpan:
        return _NoOpSpan()

    def update(self, *, output: dict | None = None, **kwargs: Any) -> None:
        return None


def _obs_ids(observation: Any, *, fallback_trace_id: str | None = None) -> tuple[str | None, str | None]:
    obs_id = getattr(observation, "id", None)
    trace_id = getattr(observation, "trace_id", None) or fallback_trace_id or obs_id
    return (
        str(obs_id) if obs_id is not None else None,
        str(trace_id) if trace_id is not None else None,
    )


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

    def __init__(self, observation: Any, *, trace_id: str | None = None) -> None:
        self._obs = observation
        obs_id, resolved_tid = _obs_ids(observation, fallback_trace_id=trace_id)
        self.observation_id = obs_id
        self.trace_id = resolved_tid

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
    if name in _GENERATION_NAMES:
        kwargs["as_type"] = "generation"
        model = input_data.get("model")
        if model:
            kwargs["model"] = model
    return obs.start_observation(**kwargs)


def current_parent() -> Any:
    """Active trace handle for this task, or None."""
    return _current_parent.get()


def current_trace_id(parent: Any | None = None) -> str | None:
    """Langfuse trace id for the active (or given) handle."""
    handle = parent if parent is not None else _current_parent.get()
    if _is_noop_parent(handle):
        return None
    return getattr(handle, "trace_id", None)


def remember_thread_trace(workspace_id: str, thread_id: str, trace_id: str) -> None:
    if workspace_id and thread_id and trace_id:
        _thread_traces[f"{workspace_id}:{thread_id}"] = trace_id


def lookup_thread_trace(workspace_id: str, thread_id: str) -> str | None:
    return _thread_traces.get(f"{workspace_id}:{thread_id}")


def clear_thread_traces() -> None:
    """Test helper."""
    _thread_traces.clear()


def _maybe_remember(metadata: dict, handle: Any) -> None:
    if _is_noop_parent(handle):
        return
    tid = getattr(handle, "trace_id", None)
    workspace_id = str(metadata.get("workspace_id") or "")
    thread_id = str(metadata.get("thread_id") or "")
    if tid and workspace_id and thread_id:
        remember_thread_trace(workspace_id, thread_id, str(tid))


@asynccontextmanager
async def start_trace(name: str, metadata: dict) -> AsyncIterator[_TraceLike]:
    """
    Open a named observation. Nested calls attach as children of the active parent.
    Never raises — yields a no-op trace when Langfuse is unavailable.
    """
    parent = _current_parent.get()
    nested = parent is not None and not _is_noop_parent(parent)
    client = None
    trace_obs = None
    handle: _TraceLike = _NoOpTrace()
    is_root = False

    try:
        if nested:
            trace_obs = _start_child_observation(parent, name, metadata)
            if trace_obs is not None:
                handle = _LangfuseTraceHandle(
                    trace_obs,
                    trace_id=getattr(parent, "trace_id", None),
                )
        else:
            client = get_langfuse_client()
            if client is not None:
                start_kwargs: dict[str, Any] = {
                    "name": name,
                    "input": metadata,
                    "metadata": metadata,
                }
                if name in _GENERATION_NAMES:
                    start_kwargs["as_type"] = "generation"
                    model = metadata.get("model")
                    if model:
                        start_kwargs["model"] = model
                trace_obs = client.start_observation(**start_kwargs)
                handle = _LangfuseTraceHandle(trace_obs)
                is_root = True
    except Exception:
        logger.debug("start_trace setup failed", exc_info=True)
        handle = _NoOpTrace()
        trace_obs = None
        is_root = False

    token = _current_parent.set(handle)
    try:
        yield handle
    finally:
        _current_parent.reset(token)
        _maybe_remember(metadata, handle)
        try:
            if trace_obs is not None:
                trace_obs.end()
        except Exception:
            logger.debug("start_trace end failed", exc_info=True)
        if is_root:
            try:
                if client is not None:
                    client.flush()
            except Exception:
                logger.debug("start_trace flush failed", exc_info=True)


# Existing RAG callers keep `async with rag_trace("rag.answer", meta)`.
rag_trace = start_trace


@asynccontextmanager
async def rag_span(
    parent: Any,
    name: str,
    input_data: dict,
) -> AsyncIterator[_SpanLike]:
    """
    Open a child span under a parent handle. Records latency_ms on exit.
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


span = rag_span


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


def score_by_trace_id(
    trace_id: str,
    *,
    name: str,
    value: float | int | str,
    comment: str | None = None,
) -> bool:
    """Attach a score to a known trace id. Returns False when tracing is off."""
    if not trace_id:
        return False
    try:
        client = get_langfuse_client()
        if client is None:
            return False
        kwargs: dict[str, Any] = {
            "trace_id": trace_id,
            "name": name,
            "value": value,
        }
        if comment:
            kwargs["comment"] = comment
        client.score(**kwargs)
        try:
            client.flush()
        except Exception:
            logger.debug("Langfuse score flush failed", exc_info=True)
        return True
    except Exception:
        logger.debug("Langfuse score_by_trace_id failed", exc_info=True)
        return False


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
