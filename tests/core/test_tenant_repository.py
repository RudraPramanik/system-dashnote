import pytest

from core.database.mixins import WorkspaceTenantMixin
from core.database.repository import TenantRepository
from core.database.utils import tenant_filter
from core.database.base import Base
from sqlalchemy.orm import Mapped, mapped_column


class DummyModel(Base, WorkspaceTenantMixin):
    __tablename__ = "dummy_tenant_model"

    id: Mapped[int] = mapped_column(primary_key=True)


def test_tenant_repository_holds_workspace_id() -> None:
    class DummySession:
        pass

    session = DummySession()
    repo = TenantRepository(session=session, workspace_id=42)

    assert repo.session is session
    assert repo.workspace_id == 42


def test_tenant_filter_uses_workspace_id_column() -> None:
    expr = tenant_filter(DummyModel, 99)

    # SQLAlchemy binary expression; left/right should reflect the workspace filter
    assert str(expr.left).endswith(".workspace_id")
    assert expr.right.value == 99


@pytest.mark.asyncio
async def test_embed_note_task_empty_content_success() -> None:
    from shared.contracts.indexing import IndexingOperation
    from worker.ingestion.tasks import embed_note_task

    for content in ("", "   "):
        result = await embed_note_task(
            {"redis": None},
            request_dict={
                "operation": IndexingOperation.UPSERT.value,
                "note_id": "test-empty",
                "workspace_id": "test-ws",
                "created_by": "test-user",
                "is_private": False,
                "title": "Empty",
                "content": content,
            },
        )
        assert result["success"] is True
        assert result["chunks_indexed"] == 0
        assert result.get("error") is None


@pytest.mark.asyncio
async def test_embedding_pipeline_empty_content() -> None:
    from unittest.mock import AsyncMock, MagicMock

    from ai.workflows.pipeline import EmbeddingPipeline

    provider = MagicMock()
    provider.embed_texts = AsyncMock()
    pipeline = EmbeddingPipeline(provider=provider, redis=None)

    result = await pipeline.process_note(
        note_id="pipe-empty",
        workspace_id="pipe-ws",
        created_by="pipe-user",
        is_private=False,
        title="Empty",
        content="   ",
    )

    assert result.chunks_processed == 0
    assert result.chunks_embedded == 0
    provider.embed_texts.assert_not_called()

