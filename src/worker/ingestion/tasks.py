"""
Ingestion worker tasks — chunk, embed, and index notes in Qdrant.

embed_note_task: EmbeddingPipeline + NoteVectorIndexer (Slice 2).
"""
from __future__ import annotations

import logging
import time

from ai.embeddings.base import EmbeddingProviderError
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

    When QDRANT_URL is set, vectors are upserted via NoteVectorIndexer.
    When Qdrant is not configured, embedding still runs but qdrant_indexed=false.
    """
    start = time.monotonic()
    settings = get_settings()

    operation = request_dict.get("operation")
    if operation in (IndexingOperation.UPSERT, IndexingOperation.UPSERT.value):
        content = request_dict.get("content", "")
        if not str(content).strip():
            return IndexingResult(
                request_id=request_dict.get("request_id", "unknown"),
                note_id=request_dict.get("note_id", "unknown"),
                workspace_id=request_dict.get("workspace_id", "unknown"),
                success=True,
                chunks_indexed=0,
            ).model_dump(mode="json")

    try:
        request = IndexingRequest(**request_dict)
    except Exception as e:
        logger.error(
            "Invalid IndexingRequest payload",
            extra={
                "error": str(e),
                "note_id": request_dict.get("note_id", "unknown"),
            },
        )
        return IndexingResult(
            request_id=request_dict.get("request_id", "unknown"),
            note_id=request_dict.get("note_id", "unknown"),
            workspace_id=request_dict.get("workspace_id", "unknown"),
            success=False,
            error=f"Invalid request payload: {e}",
        ).model_dump(mode="json")

    if request.operation == IndexingOperation.DELETE:
        latency_ms = round((time.monotonic() - start) * 1000, 2)
        qdrant_indexed = False
        if settings.qdrant_enabled:
            try:
                from ai.retrieval.indexer import NoteVectorIndexer

                indexer = NoteVectorIndexer(str(request.workspace_id))
                await indexer.delete_note(str(request.note_id))
                qdrant_indexed = True
            except Exception as e:
                logger.error(
                    "Qdrant delete failed",
                    extra={
                        "note_id": request.note_id,
                        "workspace_id": request.workspace_id,
                        "error": str(e),
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

        logger.info(
            "embed_note_task delete complete",
            extra={
                "note_id": request.note_id,
                "workspace_id": request.workspace_id,
                "qdrant_indexed": qdrant_indexed,
                "latency_ms": latency_ms,
            },
        )
        return IndexingResult(
            request_id=request.request_id,
            note_id=request.note_id,
            workspace_id=request.workspace_id,
            success=True,
            chunks_indexed=0,
            latency_ms=latency_ms,
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
        qdrant_indexed = False
        qdrant_points = 0

        if settings.qdrant_enabled and result.embedded_chunks:
            from ai.retrieval.indexer import NoteVectorIndexer

            indexer = NoteVectorIndexer(str(request.workspace_id))
            qdrant_points = await indexer.index_note_chunks(
                str(request.note_id),
                result.embedded_chunks,
            )
            qdrant_indexed = True
        elif result.embedded_chunks:
            sample = result.embedded_chunks[0]
            logger.info(
                "Embedding vectors produced (Qdrant disabled)",
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
                "qdrant_indexed": qdrant_indexed,
                "qdrant_points": qdrant_points,
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

    except EmbeddingProviderError as e:
        latency_ms = round((time.monotonic() - start) * 1000, 2)
        log_extra = {
            "note_id": request.note_id,
            "workspace_id": request.workspace_id,
            "error": str(e),
            "provider": e.provider,
            "retryable": e.retryable,
            "latency_ms": latency_ms,
        }
        if e.retryable:
            logger.warning(
                "embed_note_task failed",
                extra=log_extra,
            )
            raise
        logger.error(
            "embed_note_task failed",
            extra={**log_extra, "permanent_failure": True},
        )
        return IndexingResult(
            request_id=request.request_id,
            note_id=request.note_id,
            workspace_id=request.workspace_id,
            success=False,
            error=str(e),
            latency_ms=latency_ms,
        ).model_dump(mode="json")

    except Exception as e:
        latency_ms = round((time.monotonic() - start) * 1000, 2)
        logger.error(
            "embed_note_task failed",
            extra={
                "note_id": request.note_id,
                "workspace_id": request.workspace_id,
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
        for empty_content in ("", "   "):
            empty_result = await embed_note_task(
                {"redis": None},
                request_dict={
                    "operation": IndexingOperation.UPSERT.value,
                    "note_id": "empty-note",
                    "workspace_id": "empty-ws",
                    "created_by": "empty-user",
                    "is_private": False,
                    "title": "Empty",
                    "content": empty_content,
                },
            )
            assert empty_result["success"], empty_result
            assert empty_result["chunks_indexed"] == 0, empty_result
            assert empty_result.get("error") is None, empty_result
        print("PASS: empty content returns success with chunks_indexed=0")

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
        qdrant = get_settings().qdrant_enabled
        print(
            f"PASS: worker task embedded {result_dict['chunks_indexed']} chunks "
            f"in {result_dict['latency_ms']}ms (qdrant_enabled={qdrant})"
        )

    asyncio.run(_validate())
