"""CI-safe tests for L2 quality helpers (no deepeval import / no live HTTP)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_EVALS = Path(__file__).resolve().parents[2] / "evals"
if str(_EVALS) not in sys.path:
    sys.path.insert(0, str(_EVALS))

import quality_lab  # noqa: E402


def test_judge_key_fail_closed_via_quality_lab() -> None:
    env = {"GEMINI_API_KEY": "product-embed-key", "GEMINI_API_KEY_2": ""}
    with pytest.raises(quality_lab.JudgeKeyError) as exc:
        quality_lab.load_judge_key(env)
    assert "GEMINI_API_KEY_2" in str(exc.value)
    assert "will not fall back" in str(exc.value)


def test_configure_judge_env_sets_google_not_product() -> None:
    env: dict[str, str] = {"GEMINI_API_KEY": "product-key"}
    quality_lab.configure_judge_env("judge-only-key", environ=env)
    assert env["GOOGLE_API_KEY"] == "judge-only-key"
    assert env["USE_GEMINI_MODEL"] == "1"
    assert env["GEMINI_API_KEY"] == "product-key"


def test_classify_collection_skip_reasons() -> None:
    assert (
        quality_lab.classify_collection_skip(
            status_code=500, answer="x", retrieval_texts=["a"]
        )
        == "chat HTTP 500"
    )
    assert (
        quality_lab.classify_collection_skip(
            status_code=200, answer="", retrieval_texts=["a"]
        )
        == "empty answer"
    )
    assert (
        quality_lab.classify_collection_skip(
            status_code=200, answer="hi", retrieval_texts=[], chunks_retrieved=0
        )
        == "empty retrieval"
    )
    assert (
        quality_lab.classify_collection_skip(
            status_code=200, answer="hi", retrieval_texts=["chunk"], chunks_retrieved=1
        )
        is None
    )


def test_hard_floors_and_aggregates() -> None:
    rows = [
        {
            "id": "a",
            "scores": {"correctness": 0.8, "completeness": 0.9, "style": 0.4},
        },
        {
            "id": "b",
            "scores": {"correctness": 0.6, "completeness": 0.7, "style": None},
        },
    ]
    agg = quality_lab.aggregate_metric_scores(rows)
    assert agg["correctness"] == pytest.approx(0.7)
    assert agg["completeness"] == pytest.approx(0.8)
    assert agg["style"] == pytest.approx(0.4)

    ok, problems = quality_lab.hard_floors_met(agg, floor=0.7)
    assert ok is True
    assert problems == []

    ok2, problems2 = quality_lab.hard_floors_met(
        {"correctness": 0.5, "completeness": 0.9, "style": 0.1},
        floor=0.7,
    )
    assert ok2 is False
    assert any("correctness" in p for p in problems2)

    ok3, problems3 = quality_lab.hard_floors_met(
        {"correctness": None, "completeness": 0.9},
        floor=0.7,
    )
    assert ok3 is False
    assert any("NaN" in p or "missing" in p for p in problems3)


def test_rag_answers_golden_shape() -> None:
    cases = quality_lab.load_rag_answer_goldens()
    assert len(cases) >= 10
    selected = quality_lab.select_rag_answer_cases(cases, limit=3)
    assert len(selected) == 3
    for case in cases:
        assert case.get("theme") == "rag_answer"
        assert case.get("surface") == "POST /ai/chat"
        assert case.get("id")
        assert case.get("query_text")
        assert case.get("expected_output")
        assert case.get("completeness_checklist")
        seed = case.get("seed")
        assert isinstance(seed, dict)
        # Seed law: content present; no hard-coded note_id / chunk_id required.
        assert "note_id" not in case
        assert "chunk_id" not in case
        # Round-trip JSON sanity
        json.dumps(case)


def test_collection_failure_hint_names_nim_hatch() -> None:
    hint = quality_lab.COLLECTION_FAILURE_HINT
    assert "zero scored rows" in hint.lower()
    assert "NIM" in hint or "nim" in hint.lower()
    assert "429" in hint
    assert quality_lab.REQUIREMENTS_QUALITY.is_file()
    text = quality_lab.REQUIREMENTS_QUALITY.read_text(encoding="utf-8")
    assert "deepeval" in text.lower()


def test_chat_payload_never_sends_workspace_id() -> None:
    body = quality_lab.chat_payload("alpha project milestone")
    assert body == {"message": "alpha project milestone"}
    assert "workspace_id" not in body
