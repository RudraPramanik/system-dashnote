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


def test_live_skip_fixture_only_mode_hint() -> None:
    case = {"id": "ret-08", "mode_hint": "fixture", "theme": "retrieval"}
    reason = run_eval.case_skip_reason(case, mode="live")
    assert reason is not None
    assert "fixture-only" in reason


def test_live_skip_trajectory_not_wired() -> None:
    case = {
        "id": "traj-01",
        "mode_hint": "fixture",
        "theme": "agent_trajectory",
    }
    # mode_hint fixture already skips; also cover either + trajectory
    either = {
        "id": "traj-live-hypo",
        "mode_hint": "either",
        "theme": "agent_trajectory",
    }
    reason = run_eval.case_skip_reason(either, mode="live")
    assert reason is not None
    assert "trajectory not wired" in reason


def test_live_skip_actor_b_without_token_b() -> None:
    case = {
        "id": "ten-01",
        "mode_hint": "either",
        "theme": "tenant_isolation",
        "actor": "b",
    }
    reason = run_eval.case_skip_reason(case, mode="live", token_b=None)
    assert reason is not None
    assert "--token-b" in reason


def test_live_actor_b_runs_when_token_b_present() -> None:
    case = {
        "id": "ten-01",
        "mode_hint": "either",
        "theme": "tenant_isolation",
        "actor": "b",
    }
    assert run_eval.case_skip_reason(case, mode="live", token_b="member-jwt") is None


def test_pick_token_never_falls_back_for_actor_b() -> None:
    case = {"actor": "b"}
    assert run_eval.pick_token(case, "owner-jwt", None) is None
    assert run_eval.pick_token(case, "owner-jwt", "member-jwt") == "member-jwt"
    assert run_eval.pick_token({"actor": "a"}, "owner-jwt", "member-jwt") == "owner-jwt"
