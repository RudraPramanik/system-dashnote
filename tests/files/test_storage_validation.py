from unittest.mock import patch

import pytest
from fastapi import HTTPException

from core.storage.utils import (
    ALLOWED_MIME_TYPES,
    MIME_EXTENSION_MAP,
    detect_mime_type,
    safe_filename,
    validate_file,
)


def test_rejects_oversized_file():
    with pytest.raises(HTTPException) as exc_info:
        validate_file("doc.pdf", 1_048_577, "application/pdf")
    assert exc_info.value.status_code == 413


def test_accepts_exactly_1mb():
    validate_file("doc.pdf", 1_048_576, "application/pdf")


def test_rejects_disallowed_mime():
    with pytest.raises(HTTPException) as exc_info:
        validate_file("doc.pdf", 100, "application/zip")
    assert exc_info.value.status_code == 415


def test_rejects_extension_mismatch():
    with pytest.raises(HTTPException) as exc_info:
        validate_file("wrong.exe", 100, "application/pdf")
    assert exc_info.value.status_code == 415


@pytest.mark.parametrize("mime_type", sorted(ALLOWED_MIME_TYPES))
def test_accepts_all_allowed_types(mime_type: str):
    ext = sorted(MIME_EXTENSION_MAP[mime_type])[0]
    validate_file(f"file{ext}", 1024, mime_type)


def test_detect_mime_pdf():
    pdf_bytes = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
    with patch("core.storage.utils.magic.from_buffer", return_value="application/pdf"):
        assert detect_mime_type(pdf_bytes) == "application/pdf"


def test_safe_filename_strips_path():
    assert "/" not in safe_filename("../../etc/passwd")


def test_safe_filename_replaces_spaces():
    assert safe_filename("my doc.docx") == "my_doc.docx"
