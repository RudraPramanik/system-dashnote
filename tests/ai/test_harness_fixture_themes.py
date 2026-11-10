"""9H.6.1 harness fixture themes (grade-proof gate). No live model key.

Fixture vehicle: pytest under tests/ai/ — not evals/golden/.
RAG JSONL goldens stay on the search/eval path; these four themes are
harness/tool/route contracts already proven in-process.

Theme map (designated check → source of truth):
  invented workspace  → test_theme_invented_workspace_not_used
                        ← test_harness_trust.test_search_uses_harness_workspace_not_foreign
  role forbidden      → test_theme_forbidden_role_does_not_commit
                        ← test_harness_policy.test_forbidden_update_does_not_commit
  poisoned retrieval  → test_theme_poisoned_retrieval_cannot_retarget_or_skip_hitl
                        ← test_injection_hygiene.test_poisoned_content_cannot_retarget_workspace
                          + test_poisoned_content_cannot_skip_hitl (single nodeid)
  budget exceeded     → test_theme_budget_exceeded_skips_model
                        ← test_harness_budget_refusal.test_chat_over_budget_is_429_and_skips_the_model

Required before claiming security B+ / cost B+ / orchestration A- (claims are 9H.6.3).
Focused command: python -m pytest tests/ai/test_harness_fixture_themes.py -q
PR CI already runs these via python -m pytest -q.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from config import settings

_HERE = Path(__file__).resolve().parent


def _load_sibling(module_stem: str):
    path = _HERE / f"{module_stem}.py"
    spec = importlib.util.spec_from_file_location(
        f"harness_fixture_themes.{module_stem}",
        path,
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.asyncio
async def test_theme_invented_workspace_not_used() -> None:
    # Source: test_harness_trust.test_search_uses_harness_workspace_not_foreign
    trust = _load_sibling("test_harness_trust")
    await trust.test_search_uses_harness_workspace_not_foreign()


@pytest.mark.asyncio
async def test_theme_forbidden_role_does_not_commit() -> None:
    # Source: test_harness_policy.test_forbidden_update_does_not_commit
    policy = _load_sibling("test_harness_policy")
    await policy.test_forbidden_update_does_not_commit()


@pytest.mark.asyncio
async def test_theme_poisoned_retrieval_cannot_retarget_or_skip_hitl() -> None:
    # Source: test_injection_hygiene retarget + skip-HITL (one gate nodeid)
    injection = _load_sibling("test_injection_hygiene")
    await injection.test_poisoned_content_cannot_retarget_workspace()
    await injection.test_poisoned_content_cannot_skip_hitl()


@pytest.mark.asyncio
async def test_theme_budget_exceeded_skips_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Source: test_harness_budget_refusal.test_chat_over_budget_is_429_and_skips_the_model
    # tiny_ceiling fixture only monkeypatches settings; apply the same side effect here.
    monkeypatch.setattr(settings, "AI_USER_REQUESTS_PER_MINUTE", 1)
    monkeypatch.setattr(settings, "AI_WORKSPACE_REQUESTS_PER_DAY", 1)
    budget = _load_sibling("test_harness_budget_refusal")
    await budget.test_chat_over_budget_is_429_and_skips_the_model(object())
