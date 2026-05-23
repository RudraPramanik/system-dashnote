"""
High-level note vector indexing — used by the ARQ worker.

Delegates Qdrant upsert/delete to WorkspaceVectorIndex (never raw client in callers).
"""
from __future__ import annotations

import logging

from ai.embeddings.base import EmbeddedChunk
from ai.retrieval.workspace_search import WorkspaceVectorIndex

logger = logging.getLogger(__name__)


class NoteVectorIndexer:
    """Index or remove note chunk vectors for one workspace."""

    def __init__(self, workspace_id: str) -> None:
        self._search = WorkspaceVectorIndex(workspace_id)

    @property
    def workspace_id(self) -> str:
        return self._search.workspace_id

    async def index_note_chunks(
        self,
        note_id: str,
        chunks: list[EmbeddedChunk],
    ) -> int:
        """
        Re-index a note: delete existing vectors, then upsert new chunks.
        Returns number of points written.
        """
        await self._search.delete_note_vectors(note_id)
        if not chunks:
            return 0
        return await self._search.upsert_chunks(chunks)

    async def delete_note(self, note_id: str) -> None:
        await self._search.delete_note_vectors(note_id)


if __name__ == "__main__":
    import asyncio
    import os
    import sys

    _src = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    _root = os.path.dirname(_src)
    if _src not in sys.path:
        sys.path.insert(0, _src)
    os.chdir(_root)

    async def _validate() -> None:
        from config import get_settings
        from ai.embeddings.factory import get_embedding_provider
        from ai.workflows.pipeline import EmbeddingPipeline

        settings = get_settings()
        if not settings.qdrant_enabled or not settings.ai_enabled:
            print("SKIP: Qdrant or AI not configured")
            return

        provider = await get_embedding_provider()
        pipeline = EmbeddingPipeline(provider=provider, redis=None)
        result = await pipeline.process_note(
            note_id="indexer-validate-note",
            workspace_id="indexer-validate-ws",
            created_by="indexer-user",
            is_private=False,
            title="Indexer Validation",
            content=(
                "First paragraph for Qdrant indexer validation.\n\n"
                "Second paragraph with enough text to produce at least one chunk."
            ),
        )

        indexer = NoteVectorIndexer("indexer-validate-ws")
        n = await indexer.index_note_chunks(
            "indexer-validate-note",
            result.embedded_chunks,
        )
        assert n > 0, "FAIL: no points indexed"
        print(f"PASS: indexed {n} chunks to Qdrant")

        from ai.retrieval.wrapper import WorkspaceVectorSearch

        searcher = WorkspaceVectorSearch()
        hits = await searcher.search(
            query_text="Indexer Validation",
            workspace_id="indexer-validate-ws",
            user_id="indexer-user",
            role="owner",
            limit=3,
        )
        assert hits, "FAIL: search returned no hits"
        print(f"PASS: search returned {len(hits)} hit(s)")

    asyncio.run(_validate())
