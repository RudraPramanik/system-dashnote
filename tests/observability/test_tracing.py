"""Unit tests for the tracing facade (no Langfuse network)."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from observability.tracing import (
    clear_thread_traces,
    current_trace_id,
    lookup_thread_trace,
    rag_span,
    rag_trace,
    start_trace,
)


class _FakeObs:
    def __init__(self, name: str, parent: _FakeObs | None = None) -> None:
        self.name = name
        self.parent = parent
        self.children: list[_FakeObs] = []
        self.id = f"obs-{name}-{id(self)}"
        self.trace_id = parent.trace_id if parent is not None else f"trace-{id(self)}"
        self.ended = False
        self.as_type = None
        self.model = None
        self.input = None
        self.metadata = None
        self.output = None

    def start_observation(self, name: str, **kwargs: object) -> _FakeObs:
        child = _FakeObs(name, parent=self)
        child.as_type = kwargs.get("as_type")
        child.model = kwargs.get("model")
        child.input = kwargs.get("input")
        self.children.append(child)
        return child

    def update(self, **kwargs: object) -> None:
        if "output" in kwargs:
            self.output = kwargs["output"]

    def end(self) -> None:
        self.ended = True

    def score(self, **kwargs: object) -> None:
        return None


class _FakeClient:
    def __init__(self) -> None:
        self.roots: list[_FakeObs] = []
        self.flushed = 0

    def start_observation(self, name: str, **kwargs: object) -> _FakeObs:
        obs = _FakeObs(name)
        obs.input = kwargs.get("input")
        obs.metadata = kwargs.get("metadata")
        obs.as_type = kwargs.get("as_type")
        self.roots.append(obs)
        return obs

    def flush(self) -> None:
        self.flushed += 1

    def score(self, **kwargs: object) -> None:
        return None


@pytest.fixture(autouse=True)
def _clear_traces() -> None:
    clear_thread_traces()
    yield
    clear_thread_traces()


@pytest.mark.asyncio
async def test_start_trace_noop_when_client_missing() -> None:
    with patch("observability.tracing.get_langfuse_client", return_value=None):
        async with start_trace("agent.turn", {"workspace_id": "1"}) as handle:
            assert getattr(handle, "_noop", False) is True
            assert current_trace_id(handle) is None


@pytest.mark.asyncio
async def test_nested_start_trace_is_child_of_parent() -> None:
    fake = _FakeClient()
    with patch("observability.tracing.get_langfuse_client", return_value=fake):
        async with start_trace(
            "agent.turn",
            {"workspace_id": "9", "thread_id": "thr-1", "user_id": "u", "role": "owner"},
        ) as parent:
            async with start_trace("rag.answer", {"workspace_id": "9", "thread_id": "thr-1"}):
                async with rag_span(parent, "call_model", {"model": "x"}):
                    pass

    assert len(fake.roots) == 1
    root = fake.roots[0]
    assert root.name == "agent.turn"
    child_names = [c.name for c in root.children]
    assert "rag.answer" in child_names
    assert "call_model" in child_names
    call_model = next(c for c in root.children if c.name == "call_model")
    assert call_model.as_type == "generation"
    assert lookup_thread_trace("9", "thr-1") == root.trace_id


@pytest.mark.asyncio
async def test_rag_trace_alias_opens_root_when_no_parent() -> None:
    fake = _FakeClient()
    with patch("observability.tracing.get_langfuse_client", return_value=fake):
        async with rag_trace("rag.answer", {"workspace_id": "2"}):
            pass
    assert len(fake.roots) == 1
    assert fake.roots[0].name == "rag.answer"
    assert fake.flushed >= 1


@pytest.mark.asyncio
async def test_rag_service_nests_under_agent_parent() -> None:
    from unittest.mock import AsyncMock, MagicMock

    from ai.services.rag_service import RagService

    fake = _FakeClient()
    searcher = MagicMock()
    searcher.search = AsyncMock(return_value=[])
    with patch("observability.tracing.get_langfuse_client", return_value=fake):
        async with start_trace(
            "agent.turn",
            {
                "workspace_id": "9",
                "user_id": "u",
                "role": "owner",
                "thread_id": "thr-search",
            },
        ):
            svc = RagService(searcher=searcher)
            await svc.answer(
                question="what is in my notes?",
                workspace_id="9",
                user_id="u",
                role="owner",
            )
    assert len(fake.roots) == 1
    assert fake.roots[0].name == "agent.turn"
    assert any(c.name == "rag.answer" for c in fake.roots[0].children)
