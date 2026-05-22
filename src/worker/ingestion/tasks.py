"""
Ingestion worker tasks — Slice 1.

embed_note_task: chunks and embeds a note.
Vectors are logged only — Qdrant upsert added in Slice 2.
"""
from __future__ import annotations

import logging
import time

from config import get_settings
from shared.contracts.indexing import (
    IndexingOperation,
    IndexingRequest,
    IndexingResult,
)

logger = logging.getLogger(__name__)


async def embed_note_task(ctx: dict, *, request_dict: dict) -> dict:
    """
    ARQ task: chunk and embed a note.

    Called by ARQ with the serialised IndexingRequest dict.
    ctx contains ARQ context including redis connection.

    Returns IndexingResult as dict (ARQ serialises this to Redis).

    NOTE (Slice 1): Vectors are logged but NOT written to Qdrant yet.
    Qdrant upsert is added in Slice 2 once retrieval quality is validated.
    """
    start = time.monotonic()
    settings = get_settings()

    try:
        request = IndexingRequest(**request_dict)
    except Exception as e:
        logger.error("Invalid IndexingRequest payload: %s", e)
        return IndexingResult(
            request_id=request_dict.get("request_id", "unknown"),
            note_id=request_dict.get("note_id", "unknown"),
            workspace_id=request_dict.get("workspace_id", "unknown"),
            success=False,
            error=f"Invalid request payload: {e}",
        ).model_dump(mode="json")

    if request.operation == IndexingOperation.DELETE:
        logger.info(
            "Delete request received — Qdrant deletion wired in Slice 2",
            extra={"note_id": request.note_id, "workspace_id": request.workspace_id},
        )
        return IndexingResult(
            request_id=request.request_id,
            note_id=request.note_id,
            workspace_id=request.workspace_id,
            success=True,
            chunks_indexed=0,
        ).model_dump(mode="json")

    if not settings.ai_enabled:
        logger.debug(
            "AI disabled — skipping embedding",
            extra={"note_id": request.note_id},
        )
        return IndexingResult(
            request_id=request.request_id,
            note_id=request.note_id,
            workspace_id=request.workspace_id,
            success=True,
            chunks_indexed=0,
        ).model_dump(mode="json")

    try:
        from ai.embeddings.factory import get_embedding_provider
        from ai.workflows.pipeline import EmbeddingPipeline

        provider = await get_embedding_provider()
        redis = ctx.get("redis")
        pipeline = EmbeddingPipeline(provider=provider, redis=redis)

        result = await pipeline.process_note(
            note_id=request.note_id,
            workspace_id=request.workspace_id,
            created_by=request.created_by,
            is_private=request.is_private,
            title=request.title,
            content=request.content,
            metadata=request.metadata,
        )

        latency_ms = round((time.monotonic() - start) * 1000, 2)

        if result.embedded_chunks:
            sample = result.embedded_chunks[0]
            logger.info(
                "Embedding vectors produced (not written to Qdrant — Slice 2)",
                extra={
                    "note_id": request.note_id,
                    "embedded_count": len(result.embedded_chunks),
                    "sample_chunk_id": sample.chunk_id,
                    "sample_vector_dim": len(sample.vector),
                },
            )

        logger.info(
            "embed_note_task complete",
            extra={
                "note_id": request.note_id,
                "workspace_id": request.workspace_id,
                "chunks_processed": result.chunks_processed,
                "chunks_from_cache": result.chunks_from_cache,
                "chunks_embedded": result.chunks_embedded,
                "total_tokens": result.total_tokens,
                "latency_ms": latency_ms,
                "qdrant_indexed": False,
            },
        )

        return IndexingResult(
            request_id=request.request_id,
            note_id=request.note_id,
            workspace_id=request.workspace_id,
            success=True,
            chunks_indexed=result.chunks_processed,
            latency_ms=latency_ms,
        ).model_dump(mode="json")

    except Exception as e:
        latency_ms = round((time.monotonic() - start) * 1000, 2)
        logger.error(
            "embed_note_task failed",
            extra={
                "note_id": request.note_id,
                "error": str(e),
                "latency_ms": latency_ms,
            },
        )
        return IndexingResult(
            request_id=request.request_id,
            note_id=request.note_id,
            workspace_id=request.workspace_id,
            success=False,
            error=str(e),
            latency_ms=latency_ms,
        ).model_dump(mode="json")


if __name__ == "__main__":
    import asyncio
    import os
    import sys

    _src_dir = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
    _repo_root = os.path.dirname(_src_dir)
    if _src_dir not in sys.path:
        sys.path.insert(0, _src_dir)
    os.chdir(_repo_root)

    async def _validate() -> None:
        request = IndexingRequest(
            operation=IndexingOperation.UPSERT,
            note_id="worker-test-note-001",
            workspace_id="worker-test-ws-001",
            created_by="worker-test-user-001",
            is_private=False,
            title="Worker Test Note",
            content=(
                "First paragraph for worker validation.\n\n"
                "Second paragraph with enough text to produce at least one chunk."
            ),
        )
        result_dict = await embed_note_task(
            {"redis": None},
            request_dict=request.model_dump(mode="json"),
        )
        print("embed_note_task result:", result_dict)
        assert result_dict["success"], f"FAIL: {result_dict.get('error')}"
        assert result_dict["chunks_indexed"] > 0, "FAIL: no chunks indexed"
        print(
            f"PASS: worker task embedded {result_dict['chunks_indexed']} chunks "
            f"in {result_dict['latency_ms']}ms (qdrant_indexed=false)"
        )

    asyncio.run(_validate())
