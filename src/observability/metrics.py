"""
Low-cardinality Prometheus counters for known AI quality events.

Import law: prometheus_client, stdlib only.
No user id, workspace id, or question text as labels.
"""
from __future__ import annotations

from prometheus_client import Counter

EMPTY_RETRIEVAL = Counter(
    "dashnote_ai_empty_retrieval_total",
    "RAG turns where retrieval returned zero chunks",
)
AGENT_INTERRUPT = Counter(
    "dashnote_ai_agent_interrupt_total",
    "Agent turns that paused for HITL approval",
)
LLM_FALLBACK = Counter(
    "dashnote_ai_llm_fallback_total",
    "LLM candidate skipped (gone or timeout) before trying the next model",
)
AI_BUDGET_OUTCOME = Counter(
    "dashnote_ai_budget_outcome_total",
    "AI budget decisions",
    ["outcome"],
)

_BUDGET_OUTCOMES = frozenset({"allowed", "denied", "fail_open"})


def inc_empty_retrieval() -> None:
    EMPTY_RETRIEVAL.inc()


def inc_agent_interrupt() -> None:
    AGENT_INTERRUPT.inc()


def inc_llm_fallback() -> None:
    LLM_FALLBACK.inc()


def inc_ai_budget_outcome(outcome: str) -> None:
    if outcome not in _BUDGET_OUTCOMES:
        return
    AI_BUDGET_OUTCOME.labels(outcome=outcome).inc()
