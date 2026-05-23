"""
Embedding pipeline for DashNoteSystem.

Orchestrates the full embedding flow for a single note:
  1. Chunk the note content (TextChunker)
  2. Check Redis cache for each chunk (embedding cache)
  3. Embed uncached chunks in batch (LiteLLM provider)
  4. Write new vectors to cache
  5. Return list[EmbeddedChunk] ready for Qdrant (Slice 2)

This module has NO knowledge of Qdrant, ARQ, or HTTP.
It produces EmbeddedChunk objects and that is all.

IMPORT LAW: stdlib, pydantic, ai.embeddings.*, ai.services.cache, config
"""
from __future__ import annotations

import logging
import os
import sys
import time
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict

from ai.embeddings.base import (
    BaseEmbeddingProvider,
    EmbeddedChunk,
    EmbeddingProviderError,
)
from ai.embeddings.chunker import TextChunker
from ai.services import cache as embedding_cache

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class PipelineResult(BaseModel):
    """Result of running the embedding pipeline on one note."""

    model_config = ConfigDict(frozen=True)

    note_id: str
    workspace_id: str
    chunks_processed: int
    chunks_from_cache: int
    chunks_embedded: int
    total_tokens: int
    latency_ms: float
    embedded_chunks: list[EmbeddedChunk]


class EmbeddingPipeline:
    """
    Orchestrates chunking, cache lookup, and embedding for a note.

    Constructed once and reused — stateless between calls.
    Redis is optional: if None, cache is skipped gracefully.
    """

    def __init__(
        self,
        provider: BaseEmbeddingProvider,
        redis: "Redis | None" = None,
    ) -> None:
        self._provider = provider
        self._redis = redis
        self._chunker = TextChunker()

    async def process_note(
        self,
        *,
        note_id: str,
        workspace_id: str,
        created_by: str,
        is_private: bool,
        title: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> PipelineResult:
        """
        Run the full embedding pipeline for one note.

        Keyword-only args prevent positional mistakes on sensitive fields
        like workspace_id and is_private.
        """
        start = time.monotonic()

        chunks = self._chunker.chunk_note(note_id, title, content)
        if not chunks:
            latency_ms = round((time.monotonic() - start) * 1000, 2)
            logger.info(
                "Embedding pipeline complete",
                extra={
                    "note_id": note_id,
                    "workspace_id": workspace_id,
                    "chunks_processed": 0,
                    "chunks_from_cache": 0,
                    "chunks_embedded": 0,
                    "total_tokens": 0,
                    "latency_ms": latency_ms,
                },
            )
            return PipelineResult(
                note_id=note_id,
                workspace_id=workspace_id,
                chunks_processed=0,
                chunks_from_cache=0,
                chunks_embedded=0,
                total_tokens=0,
                latency_ms=latency_ms,
                embedded_chunks=[],
            )

        vectors_by_index: dict[int, list[float]] = {}
        uncached_indices: list[int] = []

        for i, chunk in enumerate(chunks):
            if self._redis:
                cached = await embedding_cache.get_cached_vector(
                    chunk.text, self._redis
                )
                if cached is not None:
                    vectors_by_index[i] = cached
                    continue
            uncached_indices.append(i)

        chunks_from_cache = len(chunks) - len(uncached_indices)

        if uncached_indices:
            uncached_texts = [chunks[i].text for i in uncached_indices]
            try:
                new_vectors = await self._provider.embed_texts(uncached_texts)
            except EmbeddingProviderError:
                raise

            for local_idx, chunk_idx in enumerate(uncached_indices):
                vector = new_vectors[local_idx]
                vectors_by_index[chunk_idx] = vector
                if self._redis:
                    await embedding_cache.cache_vector(
                        chunks[chunk_idx].text, vector, self._redis
                    )

        embedded: list[EmbeddedChunk] = []
        for i, chunk in enumerate(chunks):
            vector = vectors_by_index.get(i)
            if vector is None:
                logger.warning(
                    "Missing vector for chunk — skipping",
                    extra={"note_id": note_id, "chunk_index": i},
                )
                continue
            embedded.append(
                EmbeddedChunk(
                    chunk_id=chunk.chunk_id,
                    note_id=note_id,
                    workspace_id=workspace_id,
                    created_by=created_by,
                    is_private=is_private,
                    chunk_index=chunk.chunk_index,
                    chunk_text=chunk.text,
                    token_count=chunk.token_estimate,
                    vector=vector,
                    metadata={
                        "title": title,
                        "char_start": chunk.char_start,
                        "char_end": chunk.char_end,
                        **(metadata or {}),
                    },
                )
            )

        latency_ms = (time.monotonic() - start) * 1000
        total_tokens = sum(c.token_count for c in embedded)

        logger.info(
            "Embedding pipeline complete",
            extra={
                "note_id": note_id,
                "workspace_id": workspace_id,
                "chunks_processed": len(chunks),
                "chunks_from_cache": chunks_from_cache,
                "chunks_embedded": len(uncached_indices),
                "total_tokens": total_tokens,
                "latency_ms": round(latency_ms, 2),
            },
        )

        return PipelineResult(
            note_id=note_id,
            workspace_id=workspace_id,
            chunks_processed=len(chunks),
            chunks_from_cache=chunks_from_cache,
            chunks_embedded=len(uncached_indices),
            total_tokens=total_tokens,
            latency_ms=round(latency_ms, 2),
            embedded_chunks=embedded,
        )


if __name__ == "__main__":
    _src_dir = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    _repo_root = os.path.dirname(_src_dir)
    if _src_dir not in sys.path:
        sys.path.insert(0, _src_dir)
    os.chdir(_repo_root)

    import asyncio

    from config import get_settings
    from ai.embeddings.factory import get_embedding_provider

    async def _validate() -> None:
        settings = get_settings()
        provider = await get_embedding_provider()
        redis = None
        if settings.REDIS_ENABLED and settings.REDIS_URL:
            from redis.asyncio import Redis

            try:
                candidate = Redis.from_url(
                    settings.REDIS_URL, decode_responses=True
                )
                await candidate.ping()
                redis = candidate
            except Exception as exc:
                logger.warning(
                    "Redis unavailable for pipeline validation",
                    extra={"error": str(exc)},
                )

        pipeline = EmbeddingPipeline(provider=provider, redis=redis)

        result = await pipeline.process_note(
            note_id="test-note-001",
            workspace_id="test-ws-001",
            created_by="test-user-001",
            is_private=False,
            title="Test Note",
            content=(
                "This is the first paragraph.\n\n"
                "This is the second paragraph with enough content to potentially "
                "create multiple chunks if the settings allow for it."
            ),
        )

        print("Pipeline result:")
        print(f"  model: {provider.get_model_name()}")
        print(f"  chunks_processed: {result.chunks_processed}")
        print(f"  chunks_from_cache: {result.chunks_from_cache}")
        print(f"  chunks_embedded: {result.chunks_embedded}")
        print(f"  total_tokens: {result.total_tokens}")
        print(f"  latency_ms: {result.latency_ms}")
        print(f"  embedded_chunks: {len(result.embedded_chunks)}")

        if result.embedded_chunks:
            first = result.embedded_chunks[0]
            print(f"  first chunk_id: {first.chunk_id[:8]}...")
            print(f"  first vector dim: {len(first.vector)}")
            assert len(first.vector) > 0, "FAIL: empty vector"
            print("PASS: pipeline produces valid EmbeddedChunk objects")

            if redis:
                result2 = await pipeline.process_note(
                    note_id="test-note-002",
                    workspace_id="test-ws-001",
                    created_by="test-user-001",
                    is_private=False,
                    title="Test Note",
                    content=(
                        "This is the first paragraph.\n\n"
                        "This is the second paragraph with enough content to potentially "
                        "create multiple chunks if the settings allow for it."
                    ),
                )
                if (
                    result2.chunks_processed > 0
                    and result2.chunks_from_cache > 0
                ):
                    print(
                        f"PASS: cache hits on repeat text "
                        f"({result2.chunks_from_cache}/{result2.chunks_processed})"
                    )
                await redis.aclose()
        else:
            print("INFO: no embedded chunks (empty content or provider failure)")

    asyncio.run(_validate())
