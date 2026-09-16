"""CI-safe tests for the operator RAGAS lab helpers (no ragas import)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_EVALS = Path(__file__).resolve().parents[2] / "evals"
if str(_EVALS) not in sys.path:
    sys.path.insert(0, str(_EVALS))

import ragas_lab  # noqa: E402


def test_judge_key_fail_closed_does_not_use_product_gemini() -> None:
    env = {"GEMINI_API_KEY": "product-embed-key", "GEMINI_API_KEY_2": ""}
    with pytest.raises(ragas_lab.JudgeKeyError) as exc:
        ragas_lab.load_judge_key(env)
    assert "GEMINI_API_KEY_2" in str(exc.value)
    assert "will not fall back" in str(exc.value)


def test_judge_key_strips_whitespace() -> None:
    env = {"GEMINI_API_KEY": "product", "GEMINI_API_KEY_2": "  judge-key  "}
    assert ragas_lab.load_judge_key(env) == "judge-key"


def test_chat_payload_never_sends_workspace_id() -> None:
    body = ragas_lab.chat_payload("alpha project milestone")
    assert body == {"message": "alpha project milestone"}
    assert "workspace_id" not in body


def test_search_params_never_sends_workspace_id() -> None:
    params = ragas_lab.search_params("alpha project milestone", limit=5)
    assert params == {"q": "alpha project milestone", "limit": 5}
    assert "workspace_id" not in params


def test_select_retrieval_skips_empty_and_non_retrieval() -> None:
    cases = [
        {"id": "ret-08-irrelevant-emptyish", "theme": "retrieval", "query_text": "zxqv"},
        {
            "id": "ten-01",
            "theme": "tenant_isolation",
            "query_text": "secret",
        },
        {
            "id": "ret-01-marker-alpha",
            "theme": "retrieval",
            "query_text": "alpha project milestone",
        },
    ]
    selected = ragas_lab.select_retrieval_cases(cases, limit=5)
    assert [c["id"] for c in selected] == ["ret-01-marker-alpha"]


def test_collection_failure_hint_distinguishes_api_from_pin() -> None:
    hint = ragas_lab.COLLECTION_FAILURE_HINT
    assert "zero scored rows" in hint.lower() or "zero scored rows" in hint
    assert "not a RAGAS pin" in hint or "not a ragas pin" in hint.lower()
    assert "/health" in hint
    assert "429" in hint or "quota" in hint.lower()

    text = ragas_lab.REQUIREMENTS_RAGAS.read_text(encoding="utf-8")
    assert ragas_lab.requirements_ragas_allows_google_factory(text) is True


def test_requirements_ragas_rejects_broken_03_pin() -> None:
    broken = (
        "ragas>=0.2.15,<0.4\n"
        "google-genai>=1.0.0,<2\n"
        "datasets>=2.14,<4\n"
    )
    assert ragas_lab.requirements_ragas_allows_google_factory(broken) is False


def test_evaluation_dataset_dict_uses_ragas_04_columns() -> None:
    rows = [
        {
            "question": "q",
            "answer": "a",
            "contexts": ["c1"],
            "reference": "ref",
        }
    ]
    assert ragas_lab.evaluation_dataset_dict(rows) == {
        "user_input": ["q"],
        "response": ["a"],
        "retrieved_contexts": [["c1"]],
        "reference": ["ref"],
    }


def test_judge_stack_hint_points_at_reinstall() -> None:
    assert "pip install -r evals/requirements-ragas.txt" in ragas_lab.JUDGE_STACK_HINT


def test_numeric_metric_aggregates_reads_repr_dict() -> None:
    class _FakeResult:
        _repr_dict = {"faithfulness": 1.0, "context_precision": 0.5}

    assert ragas_lab.numeric_metric_aggregates(_FakeResult()) == [1.0, 0.5]


def test_numeric_metric_aggregates_rejects_nan() -> None:
    class _FakeResult:
        _repr_dict = {"faithfulness": float("nan"), "context_precision": float("nan")}

    assert ragas_lab.numeric_metric_aggregates(_FakeResult()) == []
