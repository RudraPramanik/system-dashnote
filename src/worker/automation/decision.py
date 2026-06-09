"""
AutomationDecisionEngine — governs AI-initiated destructive actions.

When to use:
  Any automation that modifies, deletes, or sends based on PURE AI judgment
  without explicit user instruction. Examples:
    - Auto-delete duplicate notes
    - Auto-merge similar content
    - Auto-archive old items
    - Auto-send notifications to external systems

When NOT to use:
  Additive, idempotent, non-destructive operations:
    - generate_note_tags    → just adds tags, reversible
    - generate_file_metadata → just adds summary, reversible
    - index_file_chunks      → vector upsert, idempotent
  Never call evaluate_action() on these — pure cost with no safety benefit.

Decision flow:
  evaluate_action(context) → AutomationDecision
  should_execute_immediately(decision) → bool
    True only if confidence >= 0.95 AND is_destructive=False
    False → log [AUTOMATION_GOVERNANCE_BLOCK], store as pending action

IMPORT LAW: litellm, pydantic, config, stdlib only.
No FastAPI. No SQLAlchemy. No domain repositories.
"""
from __future__ import annotations

import logging
from typing import ClassVar

import litellm
from pydantic import BaseModel, Field, field_validator

from config import get_settings

logger = logging.getLogger(__name__)

# Searchable log marker — used for monitoring/alerting
GOVERNANCE_BLOCK_MARKER = "[AUTOMATION_GOVERNANCE_BLOCK]"


class AutomationDecision(BaseModel):
    """
    Structured output from AutomationDecisionEngine.evaluate_action().

    action_type:   Describes the planned operation clearly.
    is_destructive: True if operation modifies, deletes, or sends irreversibly.
    confidence:    0.0 to 1.0 — model's confidence this action is correct.
    reasoning:     Concise explanation of the decision factors.
    """

    action_type: str = Field(
        description="The planned operation — e.g. 'delete_duplicate_note', 'merge_notes'."
    )
    is_destructive: bool = Field(
        description="True if this modifies, deletes, or sends data irreversibly."
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score 0.0–1.0 that this action is correct and safe.",
    )
    reasoning: str = Field(
        description="Concise reasoning for the action and confidence score."
    )

    @field_validator("confidence")
    @classmethod
    def round_confidence(cls, v: float) -> float:
        return round(v, 3)


class AutomationDecisionEngine:
    """
    Evaluates whether an AI-initiated action should execute immediately
    or be held for human review.

    Usage (only for genuinely ambiguous/destructive actions):
        decision = await AutomationDecisionEngine.evaluate_action(
            context="The system found 3 notes with identical content. "
                    "Proposed action: delete 2 duplicates."
        )
        if await AutomationDecisionEngine.should_execute_immediately(decision):
            await execute_action()
        else:
            await store_pending_action(decision)  # human reviews later
    """

    SAFE_THRESHOLD: ClassVar[float] = 0.95

    @classmethod
    async def evaluate_action(cls, context: str) -> AutomationDecision:
        """
        Evaluate whether a proposed automation action is safe to execute.

        Args:
            context: Plain English description of the proposed action and
                     its context. Include relevant data but not PII.

        Returns:
            AutomationDecision with confidence, is_destructive, reasoning.
        """
        settings = get_settings()

        try:
            response = await litellm.acompletion(
                model=settings.LLM_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an automation safety evaluator. "
                            "Assess whether the proposed automated action is safe to execute "
                            "without human approval. Be conservative — when in doubt, "
                            "mark confidence below 0.95 or is_destructive=True to require review."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Evaluate this proposed action:\n\n{context}",
                    },
                ],
                response_format=AutomationDecision,
                temperature=0.0,
                max_tokens=256,
            )
            return AutomationDecision.model_validate_json(
                response.choices[0].message.content
            )
        except Exception as e:
            logger.error(
                "AutomationDecisionEngine.evaluate_action failed",
                extra={"error": str(e)},
            )
            # Fail safe — unknown = block
            return AutomationDecision(
                action_type="unknown",
                is_destructive=True,
                confidence=0.0,
                reasoning=f"Evaluation failed: {str(e)}. Blocking for safety.",
            )

    @classmethod
    async def should_execute_immediately(cls, decision: AutomationDecision) -> bool:
        """
        Return True ONLY if confidence >= 0.95 AND is_destructive is False.
        Any other combination → block and require human review.

        This is an absolute rule — no exceptions, no overrides.
        """
        safe = decision.confidence >= cls.SAFE_THRESHOLD and not decision.is_destructive

        if not safe:
            logger.warning(
                f"{GOVERNANCE_BLOCK_MARKER} Action blocked — requires human approval",
                extra={
                    "action_type": decision.action_type,
                    "is_destructive": decision.is_destructive,
                    "confidence": decision.confidence,
                    "reasoning": decision.reasoning,
                },
            )

        return safe

    @classmethod
    async def evaluate_and_gate(
        cls,
        context: str,
        action_description: str,
    ) -> tuple[bool, AutomationDecision]:
        """
        Convenience method: evaluate and return (should_execute, decision).

        Usage:
            should_run, decision = await AutomationDecisionEngine.evaluate_and_gate(
                context="...", action_description="delete duplicate"
            )
            if should_run:
                await do_it()
        """
        decision = await cls.evaluate_action(context)
        should_run = await cls.should_execute_immediately(decision)
        return should_run, decision


if __name__ == "__main__":
    # Validation: python -m worker.automation.decision
    import asyncio

    async def _validate() -> None:
        # Test safe decision path (no real LLM call — just schema validation)
        safe_decision = AutomationDecision(
            action_type="add_tags",
            is_destructive=False,
            confidence=0.97,
            reasoning="Adding tags is additive and reversible.",
        )
        result = await AutomationDecisionEngine.should_execute_immediately(safe_decision)
        assert result is True, "FAIL: safe action should execute"
        print("PASS: safe action executes immediately")

        # Test blocked decision
        risky = AutomationDecision(
            action_type="delete_notes",
            is_destructive=True,
            confidence=0.99,
            reasoning="Deleting is irreversible.",
        )
        result = await AutomationDecisionEngine.should_execute_immediately(risky)
        assert result is False, "FAIL: destructive action should be blocked"
        print("PASS: destructive action blocked correctly")

        # Test low confidence path
        uncertain = AutomationDecision(
            action_type="merge_notes",
            is_destructive=False,
            confidence=0.72,
            reasoning="Not sure if these notes should be merged.",
        )
        result = await AutomationDecisionEngine.should_execute_immediately(uncertain)
        assert result is False, "FAIL: low confidence should be blocked"
        print("PASS: low confidence action blocked correctly")

        print("PASS: AutomationDecisionEngine validated")

    asyncio.run(_validate())
