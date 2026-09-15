"""Compatibility gate: HTTP contracts, health, CI fixture-only evals."""
from __future__ import annotations

from pathlib import Path

from ai_routes.agent import AgentResponse, ApprovalRequiredResponse
from ai_routes.chat import ChatResponse
from core import health as health_mod

_REPO = Path(__file__).resolve().parents[2]


def test_chat_required_fields_unchanged() -> None:
    body = ChatResponse(
        answer="hello",
        citations=[],
        chunks_retrieved=1,
        chunks_used=1,
        latency_ms=12.5,
        thread_id=None,
    ).model_dump()
    for key in ("answer", "citations", "chunks_retrieved", "chunks_used", "latency_ms"):
        assert key in body


def test_agent_required_fields_unchanged() -> None:
    completed = AgentResponse(
        answer="done",
        thread_id="tid",
        steps_taken=2,
        tool_calls_made=1,
    ).model_dump()
    for key in ("status", "answer", "thread_id", "steps_taken", "tool_calls_made"):
        assert key in completed
    assert completed["status"] == "completed"

    hitl = ApprovalRequiredResponse(
        tool="create_note",
        args={"title": "n"},
        thread_id="tid",
        interrupt_id="iid",
    ).model_dump()
    for key in ("status", "type", "tool", "args", "thread_id", "interrupt_id"):
        assert key in hitl
    assert hitl["status"] == "approval_required"
    assert hitl["type"] == "approval_required"


def test_health_hard_gate_is_db_and_redis_only() -> None:
    import inspect

    src = inspect.getsource(health_mod.deep_health)
    assert "check_database" in src
    assert "check_redis" in src
    assert "_probe_qdrant" not in src
    assert "_probe_llm" not in src
    assert "Qdrant/LLM never affect this gate" in src


def test_ci_fixture_eval_has_no_langfuse_judge() -> None:
    ci = (_REPO / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "evals/run_eval.py --mode fixture" in ci
    assert "run_langfuse_faithfulness" not in ci
    assert "langfuse" not in ci.lower()
    assert "--mode live" not in ci
