"""Unit tests for AutomationDecisionEngine — no live LLM for gate logic."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from worker.automation.decision import (
    GOVERNANCE_BLOCK_MARKER,
    AutomationDecision,
    AutomationDecisionEngine,
)


@pytest.mark.asyncio
async def test_should_execute_immediately_safe_action():
    decision = AutomationDecision(
        action_type="add_tags",
        is_destructive=False,
        confidence=0.97,
        reasoning="Adding tags is additive and reversible.",
    )
    assert await AutomationDecisionEngine.should_execute_immediately(decision) is True


@pytest.mark.asyncio
async def test_should_execute_immediately_blocks_destructive(caplog):
    decision = AutomationDecision(
        action_type="delete_notes",
        is_destructive=True,
        confidence=0.99,
        reasoning="Deleting is irreversible.",
    )
    assert await AutomationDecisionEngine.should_execute_immediately(decision) is False
    assert GOVERNANCE_BLOCK_MARKER in caplog.text


@pytest.mark.asyncio
async def test_should_execute_immediately_blocks_low_confidence(caplog):
    decision = AutomationDecision(
        action_type="merge_notes",
        is_destructive=False,
        confidence=0.72,
        reasoning="Not sure if these notes should be merged.",
    )
    assert await AutomationDecisionEngine.should_execute_immediately(decision) is False
    assert GOVERNANCE_BLOCK_MARKER in caplog.text


@pytest.mark.asyncio
async def test_should_execute_immediately_blocks_at_threshold_boundary(caplog):
    decision = AutomationDecision(
        action_type="archive_note",
        is_destructive=False,
        confidence=0.949,
        reasoning="Just below safe threshold.",
    )
    assert await AutomationDecisionEngine.should_execute_immediately(decision) is False
    assert GOVERNANCE_BLOCK_MARKER in caplog.text


def test_automation_decision_rounds_confidence():
    decision = AutomationDecision(
        action_type="test",
        is_destructive=False,
        confidence=0.956789,
        reasoning="rounding test",
    )
    assert decision.confidence == 0.957


@pytest.mark.asyncio
async def test_evaluate_action_fails_safe_on_llm_error():
    with patch(
        "worker.automation.decision.acompletion_structured",
        new_callable=AsyncMock,
        side_effect=RuntimeError("LLM unavailable"),
    ):
        decision = await AutomationDecisionEngine.evaluate_action(
            "Proposed: delete 2 duplicate notes."
        )

    assert decision.action_type == "unknown"
    assert decision.is_destructive is True
    assert decision.confidence == 0.0
    assert "Evaluation failed" in decision.reasoning
    assert await AutomationDecisionEngine.should_execute_immediately(decision) is False


@pytest.mark.asyncio
async def test_evaluate_and_gate_blocks_destructive():
    blocked_json = (
        '{"action_type":"delete_duplicate_note","is_destructive":true,'
        '"confidence":0.98,"reasoning":"Irreversible deletion."}'
    )
    with patch(
        "worker.automation.decision.acompletion_structured",
        new_callable=AsyncMock,
        return_value=AutomationDecision.model_validate_json(blocked_json),
    ):
        should_run, decision = await AutomationDecisionEngine.evaluate_and_gate(
            context="Found 2 duplicate notes. Proposed: delete duplicates.",
            action_description="delete duplicate",
        )

    assert should_run is False
    assert decision.is_destructive is True


@pytest.mark.asyncio
async def test_evaluate_and_gate_allows_safe_non_destructive():
    safe_json = (
        '{"action_type":"notify_owner","is_destructive":false,'
        '"confidence":0.96,"reasoning":"Read-only notification."}'
    )
    with patch(
        "worker.automation.decision.acompletion_structured",
        new_callable=AsyncMock,
        return_value=AutomationDecision.model_validate_json(safe_json),
    ):
        should_run, decision = await AutomationDecisionEngine.evaluate_and_gate(
            context="Proposed: send in-app notification to workspace owner.",
            action_description="notify owner",
        )

    assert should_run is True
    assert decision.is_destructive is False
    assert decision.confidence >= AutomationDecisionEngine.SAFE_THRESHOLD
