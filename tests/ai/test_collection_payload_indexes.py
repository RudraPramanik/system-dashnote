"""Unit tests for Qdrant collection ensure + payload indexes."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai.retrieval import collection as collection_mod


def _settings(*, notes: str = "notes_chunks", files: str = "files_chunks") -> MagicMock:
    settings = MagicMock()
    settings.qdrant_enabled = True
    settings.QDRANT_NOTES_COLLECTION = notes
    settings.QDRANT_FILES_COLLECTION = files
    settings.EMBEDDING_DIMENSION = 3072
    return settings


@pytest.fixture(autouse=True)
def _reset_ready_flags():
    collection_mod._reset_collection_ready_flags_for_tests()
    yield
    collection_mod._reset_collection_ready_flags_for_tests()


@pytest.mark.asyncio
async def test_ensure_notes_collection_creates_missing_payload_indexes():
    client = AsyncMock()
    client.collection_exists = AsyncMock(return_value=True)
    info = MagicMock()
    info.config.params.vectors = MagicMock(size=3072)
    info.payload_schema = {}  # no indexes yet
    client.get_collection = AsyncMock(return_value=info)
    client.create_payload_index = AsyncMock()

    with (
        patch(
            "ai.retrieval.collection.get_async_qdrant_client",
            new_callable=AsyncMock,
            return_value=client,
        ),
        patch("ai.retrieval.collection.get_settings", return_value=_settings()),
    ):
        await collection_mod.ensure_notes_collection()
        # Second call is a no-op via process flag
        await collection_mod.ensure_notes_collection()

    assert client.create_collection.await_count == 0
    created = {
        call.kwargs["field_name"] for call in client.create_payload_index.await_args_list
    }
    assert created == {"workspace_id", "note_id", "created_by", "visibility"}
    assert client.create_payload_index.await_count == 4


@pytest.mark.asyncio
async def test_ensure_files_collection_skips_existing_indexes():
    client = AsyncMock()
    client.collection_exists = AsyncMock(return_value=False)
    client.create_collection = AsyncMock()
    info = MagicMock()
    info.payload_schema = {
        "workspace_id": {},
        "file_id": {},
        "created_by": {},
        "visibility": {},
    }
    client.get_collection = AsyncMock(return_value=info)
    client.create_payload_index = AsyncMock()

    with (
        patch(
            "ai.retrieval.collection.get_async_qdrant_client",
            new_callable=AsyncMock,
            return_value=client,
        ),
        patch("ai.retrieval.collection.get_settings", return_value=_settings()),
    ):
        await collection_mod.ensure_files_collection()

    client.create_collection.assert_awaited_once()
    client.create_payload_index.assert_not_awaited()
