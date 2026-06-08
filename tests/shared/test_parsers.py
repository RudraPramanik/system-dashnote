"""Tests for FileParsingEngine text extraction."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from shared.utils.parsers import MAX_CHARS, FileParsingEngine


def test_extract_text_plain():
    result = FileParsingEngine.extract_text(b"Hello world plain text", "text/plain")
    assert result == "Hello world plain text"


def test_extract_text_html_strips_scripts():
    html = b"<html><body><p>Hello</p><script>bad()</script></body></html>"
    result = FileParsingEngine.extract_text(html, "text/html")
    assert "Hello" in result
    assert "bad()" not in result


def test_extract_text_empty_bytes():
    assert FileParsingEngine.extract_text(b"", "text/plain") == ""


def test_extract_text_unsupported_mime():
    assert FileParsingEngine.extract_text(b"\x00\x01\x02", "application/octet-stream") == ""


def test_extract_text_markdown():
    content = b"# Title\n\nSome markdown content."
    result = FileParsingEngine.extract_text(content, "text/markdown")
    assert "Title" in result
    assert "markdown content" in result


def test_extract_text_truncates_at_max_chars():
    content = b"x" * (MAX_CHARS + 1000)
    result = FileParsingEngine.extract_text(content, "text/plain")
    assert len(result) == MAX_CHARS


def test_extract_text_utf8_sig():
    content = "\ufeffHello".encode("utf-8-sig")
    result = FileParsingEngine.extract_text(content, "text/plain")
    assert "Hello" in result
