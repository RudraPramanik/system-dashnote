"""CI-safe tests for L0 fixture scoring (no live HTTP or LLM keys)."""
from __future__ import annotations

import sys
from pathlib import Path

_EVALS = Path(__file__).resolve().parents[2] / "evals"
if str(_EVALS) not in sys.path:
    sys.path.insert(0, str(_EVALS))

import run_eval  # noqa: E402


def _hit_payload(text: str, *, title: str = "Eval note") -> dict:
    return {
        "results": [
            {
                "title": title,
                "content_chunk": {"text": text},
            }
        ]
    }


def test_retrieval_marker_present_passes() -> None:
    case = {
        "id": "ret-happy",
        "expect_content_markers": ["alpha-project-milestone"],
    }
    ok, detail = run_eval.score_case(
        case, _hit_payload("Notes about the alpha-project-milestone kickoff")
    )
    assert ok is True
    assert detail == "ok"


def test_retrieval_marker_miss_fails() -> None:
    case = {
        "id": "ret-miss",
        "expect_content_markers": ["alpha-project-milestone"],
    }
    ok, detail = run_eval.score_case(case, _hit_payload("unrelated grocery list"))
    assert ok is False
    assert "missing marker" in detail
    assert "alpha-project-milestone" in detail


def test_tenant_isolation_no_leak_passes() -> None:
    case = {
        "id": "ten-happy",
        "expect_no_content_markers": ["peer-private-secret"],
    }
    ok, detail = run_eval.score_case(case, _hit_payload("public workspace recap"))
    assert ok is True
    assert detail == "ok"


def test_tenant_leaked_marker_fails() -> None:
    case = {
        "id": "ten-leak",
        "expect_no_content_markers": ["peer-private-secret"],
    }
    ok, detail = run_eval.score_case(
        case, _hit_payload("leaked peer-private-secret from another user")
    )
    assert ok is False
    assert "leaked marker" in detail
    assert "peer-private-secret" in detail


def test_trajectory_happy_path_passes() -> None:
    case = {
        "id": "traj-happy",
        "required_tools": ["search_notes"],
        "forbidden_tools": ["create_note"],
        "sequence_mode": "subset",
    }
    ok, detail = run_eval.score_trajectory(
        case, {"tools": ["search_notes"], "answer": "found it"}
    )
    assert ok is True
    assert detail == "ok"


def test_trajectory_forbidden_create_note_fails() -> None:
    case = {
        "id": "traj-forbid",
        "required_tools": ["search_notes"],
        "forbidden_tools": ["create_note"],
        "sequence_mode": "subset",
    }
    ok, detail = run_eval.score_trajectory(
        case, {"tools": ["search_notes", "create_note"], "answer": "created"}
    )
    assert ok is False
    assert "forbidden tool used: create_note" in detail
