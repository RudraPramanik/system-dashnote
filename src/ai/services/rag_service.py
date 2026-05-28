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
from typing import TYPE_CHECKING, AsyncGenerator, Literal

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

import litellm
from pydantic import BaseModel, ConfigDict

from config import get_settings
from ai.retrieval.wrapper import WorkspaceVectorSearch, SearchResult, get_workspace_vector_search
from ai.prompts.rag import RAGAnswer

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
    thread_id: str | None = None


# ── Slice 4: Streaming event models ─────────────────────────────────────────

class StreamToken(BaseModel):
    """
    A single token chunk yielded during streaming.
    type is always "token" — lets the client distinguish from metadata.
    """
    model_config = ConfigDict(frozen=True)

    type: Literal["token"] = "token"
    content: str   # may be empty string for keep-alive chunks — client should skip


class StreamMetadata(BaseModel):
    """
    Final packet yielded after all tokens are streamed.
    Contains grounded citations and performance metrics.
    type is always "metadata" — client renders citations after stream completes.
    """
    model_config = ConfigDict(frozen=True)

    type: Literal["metadata"] = "metadata"
    citations: list[Citation]
    chunks_retrieved: int
    chunks_used: int
    latency_ms: float
    thread_id: str | None = None


# Union type for the generator yield type
StreamEvent = StreamToken | StreamMetadata


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

    async def _load_thread_context(
        self,
        *,
        thread_id: str | None,
        workspace_id: str,
        user_id: str,
        db: "AsyncSession | None",
    ) -> tuple[str, list[dict]]:
        """
        Load conversation history if thread_id provided.

        Returns:
            (resolved_thread_id, history_messages_list)
            history_messages_list is empty if no thread or no db session.

        Security: ThreadService.get_or_create_thread() verifies
        thread belongs to workspace_id before returning it.
        ValueError raised if workspace mismatch — propagates to route.
        """
        if db is None or not hasattr(db, "execute"):
            # No DB session available — skip history gracefully
            return (thread_id or "", [])

        from ai.memory.service import ThreadService
        thread_svc = ThreadService()

        thread = await thread_svc.get_or_create_thread(
            db,
            thread_id=thread_id,
            workspace_id=workspace_id,
            user_id=user_id,
        )
        resolved_id = str(thread.id)

        if thread_id:
            # Load existing history
            history = await thread_svc.load_history_as_messages(
                db,
                thread_id=resolved_id,
                workspace_id=workspace_id,
            )
        else:
            history = []

        return (resolved_id, history)

    async def answer(
        self,
        *,
        question: str,
        workspace_id: str,
        user_id: str,
        role: str,
        retrieval_limit: int = 8,
        thread_id: str | None = None,
        db: "AsyncSession | None" = None,
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

        resolved_thread_id, history_messages = await self._load_thread_context(
            thread_id=thread_id,
            workspace_id=workspace_id,
            user_id=user_id,
            db=db,
        )

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
            fallback_answer = "I could not find relevant information in your notes for this query."
            if db is not None and resolved_thread_id:
                from ai.memory.service import ThreadService
                await ThreadService().persist_turn(
                    db,
                    thread_id=resolved_thread_id,
                    user_question=question,
                    assistant_answer=fallback_answer,
                    citations=[],
                )
            return ChatResult(
                answer=fallback_answer,
                citations=[],
                chunks_retrieved=0,
                chunks_used=0,
                latency_ms=round((time.monotonic() - start) * 1000, 2),
                thread_id=resolved_thread_id or None,
            )

        context_chunks: list[dict] = [
            {
                "chunk_id": result.chunk_id,
                "note_id": result.note_id,
                "title": result.title,
                "text": result.chunk_text,
                "score": result.score,
            }
            for result in retrieved
        ]

        from ai.memory.context_builder import ContextBuilder
        builder = ContextBuilder()
        built = builder.build(
            question=question,
            history_messages=history_messages,
            retrieved_chunks=context_chunks,
        )

        # ── Step 4: call Gemini via LiteLLM with structured output ──────────
        try:
            response = await litellm.acompletion(
                model=settings.LLM_MODEL,
                messages=built.messages,
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
        chunk_map = {c["chunk_id"]: c for c in built.context_chunks}
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
        if not citations and built.context_chunks:
            citations = [
                Citation(
                    note_id=c["note_id"],
                    chunk_id=c["chunk_id"],
                    title=c["title"],
                    relevance_score=c["score"],
                )
                for c in built.context_chunks[:3]
            ]

        if db is not None and resolved_thread_id:
            from ai.memory.service import ThreadService
            await ThreadService().persist_turn(
                db,
                thread_id=resolved_thread_id,
                user_question=question,
                assistant_answer=rag_answer.answer,
                citations=[c.model_dump() for c in citations],
            )

        latency_ms = round((time.monotonic() - start) * 1000, 2)

        logger.info(
            "rag_service.answer complete",
            extra={
                "workspace_id": workspace_id,
                "chunks_retrieved": len(retrieved),
                "chunks_used": len(built.context_chunks),
                "citations_count": len(citations),
                "model": settings.LLM_MODEL,
                "latency_ms": latency_ms,
            },
        )

        return ChatResult(
            answer=rag_answer.answer,
            citations=citations,
            chunks_retrieved=len(retrieved),
            chunks_used=len(built.context_chunks),
            latency_ms=latency_ms,
            thread_id=resolved_thread_id or None,
        )

    async def stream_answer(
        self,
        *,
        question: str,
        workspace_id: str,
        user_id: str,
        role: str,
        retrieval_limit: int = 8,
        thread_id: str | None = None,
        db: "AsyncSession | None" = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Stream a RAG answer as progressive token events.

        Yields:
            StreamToken events as text arrives from the LLM.
            One final StreamMetadata event with citations and metrics.

        Citation strategy:
            Citations are grounded against retrieved chunks at stream end.
            We do NOT parse [CHUNK:uuid] tags from the token stream — this
            is fragile and unreliable mid-stream. Instead, top retrieved
            chunks become citations after streaming completes.

        LangGraph compatibility:
            Same plain string signature as answer() — works from both
            HTTP routes (Slice 4) and agent tools (Slice 6) unchanged.

        Args:
            question:        User's natural language question.
            workspace_id:    From RequestContext.workspace_id — plain string.
            user_id:         From RequestContext.user_id — plain string.
            role:            "owner" | "admin" | "member" — plain string.
            retrieval_limit: Max chunks to retrieve before streaming.
        """
        start = time.monotonic()
        settings = get_settings()

        resolved_thread_id, history_messages = await self._load_thread_context(
            thread_id=thread_id,
            workspace_id=workspace_id,
            user_id=user_id,
            db=db,
        )

        # ── Step 1: retrieve relevant chunks (same as answer()) ─────────────
        retrieved: list[SearchResult] = await self._searcher.search(
            query_text=question,
            workspace_id=workspace_id,
            user_id=user_id,
            role=role,
            limit=retrieval_limit,
        )

        if not retrieved:
            logger.info(
                "stream_answer: no relevant chunks found",
                extra={"workspace_id": workspace_id},
            )
            fallback_answer = "I could not find relevant information in your notes for this query."
            if db is not None and resolved_thread_id:
                from ai.memory.service import ThreadService
                await ThreadService().persist_turn(
                    db,
                    thread_id=resolved_thread_id,
                    user_question=question,
                    assistant_answer=fallback_answer,
                    citations=[],
                )
            yield StreamToken(content=fallback_answer)
            yield StreamMetadata(
                citations=[],
                chunks_retrieved=0,
                chunks_used=0,
                latency_ms=round((time.monotonic() - start) * 1000, 2),
                thread_id=resolved_thread_id or None,
            )
            return

        context_chunks: list[dict] = [
            {
                "chunk_id": result.chunk_id,
                "note_id": result.note_id,
                "title": result.title,
                "text": result.chunk_text,
                "score": result.score,
            }
            for result in retrieved
        ]

        from ai.memory.context_builder import ContextBuilder
        builder = ContextBuilder()
        built = builder.build(
            question=question,
            history_messages=history_messages,
            retrieved_chunks=context_chunks,
        )

        # ── Step 4: stream LiteLLM completion ───────────────────────────────
        try:
            response = await litellm.acompletion(
                model=settings.LLM_MODEL,
                messages=built.messages,
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
                stream=True,
            )
        except Exception as e:
            logger.error(
                "LLM streaming failed",
                extra={
                    "model": settings.LLM_MODEL,
                    "workspace_id": workspace_id,
                    "error": str(e),
                },
            )
            raise

        # ── Step 5: yield token events as they arrive ────────────────────────
        streamed_answer_parts: list[str] = []
        async for chunk in response:
            delta = chunk.choices[0].delta.content
            if delta:
                streamed_answer_parts.append(delta)
                yield StreamToken(content=delta)

        full_answer = "".join(streamed_answer_parts)

        # ── Step 6: ground citations and yield metadata ──────────────────────
        # Citations from retrieval — never from LLM token parsing
        citations: list[Citation] = [
            Citation(
                note_id=c["note_id"],
                chunk_id=c["chunk_id"],
                title=c["title"],
                relevance_score=c["score"],
            )
            for c in built.context_chunks[:5]   # top 5 retrieved chunks as citations
        ]

        if db is not None and resolved_thread_id and full_answer:
            from ai.memory.service import ThreadService
            await ThreadService().persist_turn(
                db,
                thread_id=resolved_thread_id,
                user_question=question,
                assistant_answer=full_answer,
                citations=[c.model_dump() for c in citations],
            )

        latency_ms = round((time.monotonic() - start) * 1000, 2)

        logger.info(
            "stream_answer complete",
            extra={
                "workspace_id": workspace_id,
                "chunks_retrieved": len(retrieved),
                "chunks_used": len(built.context_chunks),
                "citations_count": len(citations),
                "model": settings.LLM_MODEL,
                "latency_ms": latency_ms,
            },
        )

        yield StreamMetadata(
            citations=citations,
            chunks_retrieved=len(retrieved),
            chunks_used=len(built.context_chunks),
            latency_ms=latency_ms,
            thread_id=resolved_thread_id or None,
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
    # Validation: docker compose exec -e PYTHONPATH=/app/src api python -m ai.services.rag_service
    import asyncio

    async def _validate() -> None:
        print("RagService Slice 4 import validation...")

        # Verify Slice 3 models still present
        from ai.services.rag_service import (
            Citation, ChatResult, get_rag_service,
            StreamToken, StreamMetadata, StreamEvent,
        )
        print("PASS: all models importable (Citation, ChatResult, StreamToken, StreamMetadata)")

        # Verify StreamToken model
        token = StreamToken(content="Hello")
        assert token.type == "token"
        assert token.content == "Hello"
        print("PASS: StreamToken model valid")

        # Verify StreamMetadata model
        meta = StreamMetadata(
            citations=[],
            chunks_retrieved=3,
            chunks_used=2,
            latency_ms=1200.5,
        )
        assert meta.type == "metadata"
        assert meta.chunks_retrieved == 3
        print("PASS: StreamMetadata model valid")

        # Verify empty StreamToken is safe (keep-alive chunks)
        empty_token = StreamToken(content="")
        assert empty_token.content == ""
        print("PASS: empty StreamToken is safe (client should skip)")

        # Verify service has stream_answer method
        service = get_rag_service()
        assert hasattr(service, "stream_answer"), "FAIL: stream_answer() not found on RagService"
        assert hasattr(service, "answer"), "FAIL: answer() was accidentally removed"
        print("PASS: RagService has both answer() and stream_answer() methods")

        print(f"PASS: LLM model configured: {get_settings().LLM_MODEL}")
        print("PASS: Slice 4 service layer validation complete — ready for 4.2")

    asyncio.run(_validate())
