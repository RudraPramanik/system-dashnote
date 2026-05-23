"""
RAG service for DashNoteSystem — core AI answer engine.

RagService.answer() is the single entry point for all RAG chat requests.
It is intentionally decoupled from HTTP and FastAPI.

Why plain strings instead of RequestContext?
  In Slice 6, LangGraph agent tools will call answer() directly.
  Agent tools operate outside the HTTP request lifecycle.
  A service that accepts RequestContext cannot be called by an agent tool.
  Accepting (workspace_id, user_id, role) as strings works from BOTH
  HTTP routes (Slice 3) and agent tools (Slice 6) without any change.

Pipeline:
  1. retrieve relevant chunks (WorkspaceVectorSearch + RBAC filter)
  2. enforce token budget — truncate context if needed
  3. build prompt from template (ai/prompts/rag.py)
  4. call Gemini via litellm.acompletion() with structured output
  5. ground citations against retrieved set — never trust LLM chunk IDs blindly
  6. return ChatResult

IMPORT LAW: Only litellm, pydantic, config, ai.retrieval.*, ai.prompts.*, stdlib.
NO FastAPI. NO RequestContext. NO SQLAlchemy. NO domain repositories.
"""
from __future__ import annotations

import logging
import time

import litellm
from pydantic import BaseModel, ConfigDict

from config import get_settings
from ai.retrieval.wrapper import WorkspaceVectorSearch, SearchResult, get_workspace_vector_search
from ai.prompts.rag import RAGAnswer, RAG_SYSTEM_INSTRUCTION, build_rag_user_message

logger = logging.getLogger(__name__)


# ── Response models ─────────────────────────────────────────────────────────

class Citation(BaseModel):
    """A grounded citation from retrieved note content."""
    model_config = ConfigDict(frozen=True)

    note_id: str
    chunk_id: str
    title: str
    relevance_score: float


class ChatResult(BaseModel):
    """
    Complete RAG response returned by RagService.answer().
    Used by HTTP routes and will be used by agent tools in Slice 6.
    """
    model_config = ConfigDict(frozen=True)

    answer: str
    citations: list[Citation]
    chunks_retrieved: int
    chunks_used: int
    latency_ms: float


# ── Service ──────────────────────────────────────────────────────────────────

class RagService:
    """
    Core RAG answer engine.

    Stateless between calls — safe to instantiate once and reuse.
    All tenant scoping is enforced via workspace_id, user_id, role
    passed explicitly — never derived from HTTP context inside this class.

    LangGraph compatibility:
        answer() signature is agent-tool-compatible from day one.
        Slice 6 agent tools call this directly with no HTTP adapter needed.
    """

    def __init__(
        self,
        searcher: WorkspaceVectorSearch | None = None,
    ) -> None:
        self._searcher = searcher or get_workspace_vector_search()

    async def answer(
        self,
        *,
        question: str,
        workspace_id: str,
        user_id: str,
        role: str,
        retrieval_limit: int = 8,
    ) -> ChatResult:
        """
        Answer a question using retrieved note context.

        Args:
            question:        User's natural language question.
            workspace_id:    From RequestContext.workspace_id (JWT wid).
                             Passed as plain string — not RequestContext object.
            user_id:         From RequestContext.user_id (JWT sub).
            role:            From RequestContext.role — "owner"/"admin"/"member".
            retrieval_limit: Max chunks to retrieve (default 8).

        Returns:
            ChatResult with grounded answer and verified citations.

        LangGraph note:
            This exact signature is what agent tools will call in Slice 6.
            Do not add RequestContext, Request, or any HTTP object here.
        """
        start = time.monotonic()
        settings = get_settings()

        # ── Step 1: retrieve relevant chunks with RBAC enforcement ──────────
        retrieved: list[SearchResult] = await self._searcher.search(
            query_text=question,
            workspace_id=workspace_id,   # always from JWT — never user-supplied
            user_id=user_id,
            role=role,
            limit=retrieval_limit,
        )

        if not retrieved:
            logger.info(
                "No relevant chunks found",
                extra={
                    "workspace_id": workspace_id,
                    "question_length": len(question),
                },
            )
            return ChatResult(
                answer="I could not find relevant information in your notes for this query.",
                citations=[],
                chunks_retrieved=0,
                chunks_used=0,
                latency_ms=round((time.monotonic() - start) * 1000, 2),
            )

        # ── Step 2: enforce token budget ────────────────────────────────────
        # Prevent context overflow — keep total chars under TOKEN_BUDGET_PER_REQUEST
        # This is a simple char-based budget; tiktoken can replace it later
        budget = settings.TOKEN_BUDGET_PER_REQUEST
        context_chunks: list[dict] = []
        chars_used = 0

        for result in retrieved:
            chunk_chars = len(result.chunk_text)
            if chars_used + chunk_chars > budget:
                break
            context_chunks.append({
                "chunk_id": result.chunk_id,
                "note_id": result.note_id,
                "title": result.title,
                "text": result.chunk_text,
                "score": result.score,
            })
            chars_used += chunk_chars

        # ── Step 3: build prompt from template ──────────────────────────────
        user_message = build_rag_user_message(question, context_chunks)

        # ── Step 4: call Gemini via LiteLLM with structured output ──────────
        try:
            response = await litellm.acompletion(
                model=settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": RAG_SYSTEM_INSTRUCTION},
                    {"role": "user", "content": user_message},
                ],
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
                response_format=RAGAnswer,
            )
        except Exception as e:
            logger.error(
                "LLM completion failed",
                extra={
                    "model": settings.LLM_MODEL,
                    "workspace_id": workspace_id,
                    "error": str(e),
                },
            )
            raise

        # Parse the structured response
        raw_content = response.choices[0].message.content
        try:
            rag_answer = RAGAnswer.model_validate_json(raw_content)
        except Exception:
            # Fallback: treat raw content as plain answer if JSON parse fails
            logger.warning(
                "RAGAnswer parse failed — using raw content as answer",
                extra={"workspace_id": workspace_id},
            )
            rag_answer = RAGAnswer(answer=raw_content, cited_chunk_ids=[])

        # ── Step 5: ground citations against retrieved set ──────────────────
        # CRITICAL: never trust chunk IDs from the LLM directly.
        # Map LLM-cited IDs back against what was actually retrieved.
        # This prevents hallucinated citations entirely.
        chunk_map = {c["chunk_id"]: c for c in context_chunks}
        citations: list[Citation] = []

        for chunk_id in rag_answer.cited_chunk_ids:
            if chunk_id in chunk_map:
                c = chunk_map[chunk_id]
                citations.append(Citation(
                    note_id=c["note_id"],
                    chunk_id=chunk_id,
                    title=c["title"],
                    relevance_score=c["score"],
                ))

        # If LLM cited nothing but we have context, cite top results anyway
        if not citations and context_chunks:
            citations = [
                Citation(
                    note_id=c["note_id"],
                    chunk_id=c["chunk_id"],
                    title=c["title"],
                    relevance_score=c["score"],
                )
                for c in context_chunks[:3]
            ]

        latency_ms = round((time.monotonic() - start) * 1000, 2)

        logger.info(
            "rag_service.answer complete",
            extra={
                "workspace_id": workspace_id,
                "chunks_retrieved": len(retrieved),
                "chunks_used": len(context_chunks),
                "citations_count": len(citations),
                "model": settings.LLM_MODEL,
                "latency_ms": latency_ms,
            },
        )

        return ChatResult(
            answer=rag_answer.answer,
            citations=citations,
            chunks_retrieved=len(retrieved),
            chunks_used=len(context_chunks),
            latency_ms=latency_ms,
        )


# ── Module-level singleton ───────────────────────────────────────────────────

_rag_service: RagService | None = None


def get_rag_service() -> RagService:
    """Return the process-wide RagService singleton."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RagService()
    return _rag_service


if __name__ == "__main__":
    # Validation: docker compose exec api python -m ai.services.rag_service
    import asyncio

    async def _validate() -> None:
        print("RagService import validation...")
        from ai.prompts.rag import RAGAnswer, build_rag_user_message

        # Test prompt building
        chunks = [
            {"chunk_id": "abc-123", "note_id": "n1", "title": "Test Note",
             "text": "This is test content about project X.", "score": 0.87},
        ]
        msg = build_rag_user_message("What is project X?", chunks)
        assert "[CHUNK:abc-123]" in msg, "FAIL: chunk ID tag missing"
        assert "QUESTION:" in msg, "FAIL: question section missing"
        print("PASS: prompt builder works correctly")

        # Test RAGAnswer schema
        test_json = '{"answer": "Test answer.", "cited_chunk_ids": ["abc-123"]}'
        parsed = RAGAnswer.model_validate_json(test_json)
        assert parsed.answer == "Test answer."
        assert "abc-123" in parsed.cited_chunk_ids
        print("PASS: RAGAnswer schema validates correctly")

        # Test service instantiation (no API call)
        service = get_rag_service()
        print(f"PASS: RagService instantiated — model: {get_settings().LLM_MODEL}")
        print("PASS: All validations passed — ready for 3.2")

    asyncio.run(_validate())
