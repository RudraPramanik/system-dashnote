"""FileResponse automation fields and extracted_text clipping."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

from files.router import _to_response
from files.schemas import (
    EXTRACTED_TEXT_DETAIL_MAX,
    FileResponse,
    clip_extracted_text,
)


def test_clip_extracted_text_null_on_list():
    assert clip_extracted_text("hello " * 100, include=False) is None


def test_clip_extracted_text_truncates_on_detail():
    text = "x" * (EXTRACTED_TEXT_DETAIL_MAX + 500)
    clipped = clip_extracted_text(text, include=True)
    assert clipped is not None
    assert len(clipped) == EXTRACTED_TEXT_DETAIL_MAX


def test_file_response_includes_summary_tags_and_nullable_extracted():
    now = datetime.now(timezone.utc)
    row = FileResponse(
        id=uuid4(),
        workspace_id=108,
        created_by=111,
        name="paper.pdf",
        storage_key="108/abc/paper.pdf",
        mime_type="application/pdf",
        size_bytes=1024,
        is_private=True,
        description=None,
        created_at=now,
        updated_at=now,
        summary="A short summary.",
        tags=["ml", "llm"],
        extracted_text=None,
    )
    dumped = row.model_dump()
    assert dumped["summary"] == "A short summary."
    assert dumped["tags"] == ["ml", "llm"]
    assert dumped["extracted_text"] is None


def test_to_response_detail_truncates_list_omits_extracted():
    now = datetime.now(timezone.utc)
    file = SimpleNamespace(
        id=uuid4(),
        workspace_id=108,
        created_by=111,
        name="paper.pdf",
        storage_key="108/abc/paper.pdf",
        mime_type="application/pdf",
        size_bytes=1024,
        is_private=True,
        description=None,
        created_at=now,
        updated_at=now,
        summary="A short summary.",
        tags=["ml"],
        extracted_text="x" * (EXTRACTED_TEXT_DETAIL_MAX + 500),
    )
    storage = MagicMock()
    storage.presigned_url.return_value = None
    detail = _to_response(file, storage, include_extracted=True)
    listing = _to_response(file, storage, include_extracted=False)
    assert listing.extracted_text is None
    assert listing.summary == "A short summary."
    assert listing.tags == ["ml"]
    assert detail.extracted_text is not None
    assert len(detail.extracted_text) == EXTRACTED_TEXT_DETAIL_MAX
