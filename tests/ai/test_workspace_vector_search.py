"""Unit tests for dual-collection WorkspaceVectorSearch — no live Qdrant."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai.retrieval.wrapper import WorkspaceVectorSearch


def _point(*, point_id: str, score: float, payload: dict) -> MagicMock:
    point = MagicMock()
    point.id = point_id
    point.score = score
    point.payload = payload
    return point


def _settings() -> MagicMock:
    settings = MagicMock()
    settings.QDRANT_NOTES_COLLECTION = "notes_chunks"
    settings.QDRANT_FILES_COLLECTION = "files_chunks"
    return settings


async def _search_with_client(client: AsyncMock, *, role: str = "owner", limit: int = 10):
    provider = AsyncMock()
    provider.embed_single = AsyncMock(return_value=[0.1, 0.2])
    with (
        patch(
            "ai.retrieval.wrapper.get_embedding_provider",
            new_callable=AsyncMock,
            return_value=provider,
        ),
        patch(
            "ai.retrieval.wrapper.get_async_qdrant_client",
            new_callable=AsyncMock,
            return_value=client,
        ),
        patch("ai.retrieval.wrapper.ensure_notes_collection", new_callable=AsyncMock),
        patch("ai.retrieval.wrapper.ensure_files_collection", new_callable=AsyncMock),
        patch("ai.retrieval.wrapper.get_settings", return_value=_settings()),
    ):
        searcher = WorkspaceVectorSearch()
        return await searcher.search(
            query_text="llm frameworks",
            workspace_id="108",
            user_id="111",
            role=role,
            limit=limit,
        )


@pytest.mark.asyncio
async def test_search_merges_by_score_and_maps_source_types():
    note_point = _point(
        point_id="n1",
        score=0.5,
        payload={
            "note_id": "40",
            "workspace_id": "108",
            "created_by": "111",
            "visibility": "public",
            "text": "note chunk",
            "title": "Note",
            "chunk_index": 0,
        },
    )
    file_point = _point(
        point_id="f1",
        score=0.9,
        payload={
            "file_id": "2c13e530-3a39-4547-b5c8-2b47cee89966",
            "workspace_id": "108",
            "created_by": "111",
            "visibility": "private",
            "text": "file chunk",
            "title": "Paper",
            "chunk_index": 0,
        },
    )

    async def query_points(**kwargs):
        name = kwargs["collection_name"]
        if name == "notes_chunks":
            return MagicMock(points=[note_point])
        if name == "files_chunks":
            return MagicMock(points=[file_point])
        raise AssertionError(name)

    client = AsyncMock()
    client.query_points = AsyncMock(side_effect=query_points)

    hits = await _search_with_client(client)

    assert [hit.source_type for hit in hits] == ["file", "note"]
    assert hits[0].file_id == "2c13e530-3a39-4547-b5c8-2b47cee89966"
    assert hits[0].note_id == ""
    assert hits[1].note_id == "40"
    assert hits[1].file_id == ""
    collections = [
        call.kwargs["collection_name"] for call in client.query_points.await_args_list
    ]
    assert collections == ["notes_chunks", "files_chunks"]
    note_filter = client.query_points.await_args_list[0].kwargs["query_filter"]
    file_filter = client.query_points.await_args_list[1].kwargs["query_filter"]
    assert note_filter == file_filter


@pytest.mark.asyncio
async def test_search_member_rbac_filter_applied_to_both_collections():
    client = AsyncMock()
    client.query_points = AsyncMock(
        return_value=MagicMock(points=[]),
    )

    await _search_with_client(client, role="member")

    assert client.query_points.await_count == 2
    for call in client.query_points.await_args_list:
        filt = call.kwargs["query_filter"]
        assert filt.min_should is not None
        assert filt.min_should.min_count == 1
        assert len(filt.must) == 1
        assert filt.must[0].match.value == "108"


@pytest.mark.asyncio
async def test_search_caps_merged_results_at_limit():
    notes = [
        _point(
            point_id=f"n{i}",
            score=0.4 + (i * 0.01),
            payload={"note_id": str(i), "text": "n", "title": "n", "chunk_index": 0},
        )
        for i in range(3)
    ]
    files = [
        _point(
            point_id=f"f{i}",
            score=0.8 + (i * 0.01),
            payload={
                "file_id": f"file-{i}",
                "text": "f",
                "title": "f",
                "chunk_index": 0,
            },
        )
        for i in range(3)
    ]

    async def query_points(**kwargs):
        if kwargs["collection_name"] == "notes_chunks":
            return MagicMock(points=notes)
        return MagicMock(points=files)

    client = AsyncMock()
    client.query_points = AsyncMock(side_effect=query_points)

    hits = await _search_with_client(client, limit=2)

    assert len(hits) == 2
    assert all(hit.source_type == "file" for hit in hits)
