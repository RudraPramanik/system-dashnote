"""
ContextBuilder — assembles the LiteLLM messages array for RAG conversations.

Combines:
  - System instruction (RAG_SYSTEM_INSTRUCTION)
  - Historical messages from ai_messages table (recent N messages)
  - Current context chunks from Qdrant retrieval
  - Current user question

Token budget enforcement:
  historical_chars + context_chars <= TOKEN_BUDGET_PER_REQUEST
  Historical messages are loaded first, then context chunks fill
  the remaining budget. If budget is exhausted by history,
  context chunks are reduced, never eliminated entirely (min 1 chunk).

IMPORT LAW: Only stdlib, config, ai.prompts.rag — no SQLAlchemy, no FastAPI.
AsyncSession is never imported here — history is passed as pre-loaded list.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from config import get_settings
from ai.prompts.rag import RAG_SYSTEM_INSTRUCTION, build_rag_user_message

logger = logging.getLogger(__name__)


@dataclass
class BuiltContext:
    """Result of ContextBuilder.build() — ready to pass to litellm.acompletion()."""
    messages: list[dict]        # full LiteLLM messages array
    context_chunks: list[dict]  # chunks that made it into budget (for citation grounding)
    history_messages_used: int
    context_chunks_used: int
    total_chars: int


class ContextBuilder:
    """
    Assembles the LiteLLM messages array respecting the token budget.

    Usage:
        builder = ContextBuilder()
        built = builder.build(
            question="What is the deadline?",
            history_messages=[{"role": "user", "content": "..."}, ...],
            retrieved_chunks=[{"chunk_id": "...", "text": "...", ...}, ...],
        )
        response = await litellm.acompletion(messages=built.messages, ...)
    """

    def build(
        self,
        *,
        question: str,
        history_messages: list[dict],
        retrieved_chunks: list[dict],
    ) -> BuiltContext:
        """
        Build the full messages array for a RAG conversation turn.

        Message order (required for correct LLM context):
          1. System instruction
          2. Historical messages (oldest first, budget-trimmed from oldest)
          3. Retrieved context as user message
          4. Current user question (if context present, merged with context)

        Budget strategy:
          - Historical messages consume budget from oldest first
          - Context chunks consume remaining budget
          - At least 1 context chunk always included if available
          - If history alone exceeds budget, trim oldest messages

        Args:
            question:          Current user question.
            history_messages:  List of {"role": str, "content": str} dicts,
                               ordered oldest first (from ThreadRepository).
            retrieved_chunks:  List of chunk dicts from WorkspaceVectorSearch.
        """
        settings = get_settings()
        budget = settings.TOKEN_BUDGET_PER_REQUEST

        # Step 1: fit historical messages into budget
        # Trim oldest messages first if history is too long
        fitted_history: list[dict] = []
        history_chars = 0

        # Reserve at least 30% of budget for context chunks
        history_budget = int(budget * 0.7)

        for msg in history_messages:
            msg_chars = len(msg.get("content", ""))
            if history_chars + msg_chars > history_budget:
                break
            fitted_history.append({"role": msg["role"], "content": msg["content"]})
            history_chars += msg_chars

        # Step 2: fit context chunks into remaining budget
        remaining_budget = budget - history_chars
        fitted_chunks: list[dict] = []
        context_chars = 0

        for chunk in retrieved_chunks:
            chunk_chars = len(chunk.get("text", ""))
            if context_chars + chunk_chars > remaining_budget and fitted_chunks:
                # At least 1 chunk always included — never send LLM with zero context
                break
            fitted_chunks.append(chunk)
            context_chars += chunk_chars

        # Step 3: build user message (context + question merged)
        user_content = build_rag_user_message(question, fitted_chunks)

        # Step 4: assemble final messages array
        messages: list[dict] = [
            {"role": "system", "content": RAG_SYSTEM_INSTRUCTION},
            *fitted_history,
            {"role": "user", "content": user_content},
        ]

        logger.debug(
            "Context built",
            extra={
                "history_messages_used": len(fitted_history),
                "context_chunks_used": len(fitted_chunks),
                "total_chars": history_chars + context_chars,
                "budget": budget,
            },
        )

        return BuiltContext(
            messages=messages,
            context_chunks=fitted_chunks,
            history_messages_used=len(fitted_history),
            context_chunks_used=len(fitted_chunks),
            total_chars=history_chars + context_chars,
        )
