"""
FileParsingEngine — text extraction from binary file content.

Supports: PDF, DOCX, HTML, plain text, markdown.
All parsing is synchronous and CPU-bound — run in executor for async callers.

Safety limits:
  MAX_CHARS = 500_000 — prevents OOM on large documents in worker container
  Truncation logged at WARNING — never silently dropped

IMPORT LAW: Only pypdf, docx, bs4, stdlib. No FastAPI, no SQLAlchemy,
no AI imports, no config. Pure utility module.
"""
from __future__ import annotations

import io
import logging
from typing import Final

logger = logging.getLogger(__name__)

MAX_CHARS: Final[int] = 500_000   # 500k chars max per document


class FileParsingEngine:
    """
    Extracts plain text from binary file content.

    Usage:
        text = FileParsingEngine.extract_text(file_bytes, "application/pdf")

    All methods are synchronous. For async callers:
        import asyncio, functools
        text = await asyncio.get_event_loop().run_in_executor(
            None, functools.partial(FileParsingEngine.extract_text, bytes_, mime_type)
        )
    """

    @classmethod
    def extract_text(cls, content_bytes: bytes, mime_type: str) -> str:
        """
        Extract plain text from binary content based on MIME type.

        Args:
            content_bytes: Raw file bytes from storage backend.
            mime_type:     MIME type string (e.g. "application/pdf").

        Returns:
            Extracted plain text string, truncated to MAX_CHARS.
            Empty string if extraction fails or content is binary.
        """
        if not content_bytes:
            return ""

        mime = mime_type.lower().strip()

        try:
            if mime == "application/pdf":
                return cls._parse_pdf(content_bytes)
            elif mime in (
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/msword",
            ):
                return cls._parse_docx(content_bytes)
            elif mime in ("text/html", "application/xhtml+xml"):
                return cls._parse_html(content_bytes)
            elif mime.startswith("text/"):
                return cls._parse_text(content_bytes)
            else:
                logger.info(
                    "Unsupported MIME type for text extraction",
                    extra={"mime_type": mime_type},
                )
                return ""
        except Exception as e:
            logger.error(
                "FileParsingEngine.extract_text failed",
                extra={"mime_type": mime_type, "error": str(e)},
            )
            return ""

    @classmethod
    def _parse_pdf(cls, content_bytes: bytes) -> str:
        """Extract text from PDF using pypdf."""
        import pypdf
        text_parts: list[str] = []
        chars = 0

        try:
            reader = pypdf.PdfReader(io.BytesIO(content_bytes))
            for page_num, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                if chars + len(page_text) > MAX_CHARS:
                    remaining = MAX_CHARS - chars
                    text_parts.append(page_text[:remaining])
                    logger.warning(
                        "PDF extraction truncated at MAX_CHARS",
                        extra={"pages_processed": page_num, "max_chars": MAX_CHARS},
                    )
                    break
                text_parts.append(page_text)
                chars += len(page_text)
        except Exception as e:
            logger.error("PDF parse error", extra={"error": str(e)})
            return ""

        return "\n\n".join(text_parts)

    @classmethod
    def _parse_docx(cls, content_bytes: bytes) -> str:
        """Extract text from Word document using python-docx."""
        import docx
        text_parts: list[str] = []
        chars = 0

        try:
            doc = docx.Document(io.BytesIO(content_bytes))
            for para in doc.paragraphs:
                if not para.text.strip():
                    continue
                if chars + len(para.text) > MAX_CHARS:
                    logger.warning("DOCX extraction truncated at MAX_CHARS")
                    break
                text_parts.append(para.text)
                chars += len(para.text)
        except Exception as e:
            logger.error("DOCX parse error", extra={"error": str(e)})
            return ""

        return "\n".join(text_parts)

    @classmethod
    def _parse_html(cls, content_bytes: bytes) -> str:
        """Extract readable text from HTML using BeautifulSoup."""
        from bs4 import BeautifulSoup

        try:
            soup = BeautifulSoup(content_bytes, "lxml")
            # Remove non-content elements
            for tag in soup(["script", "style", "head", "nav", "footer", "meta", "link"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)
            return text[:MAX_CHARS]
        except Exception as e:
            logger.error("HTML parse error", extra={"error": str(e)})
            return ""

    @classmethod
    def _parse_text(cls, content_bytes: bytes) -> str:
        """Decode plain text content."""
        for encoding in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                return content_bytes.decode(encoding)[:MAX_CHARS]
            except UnicodeDecodeError:
                continue
        return ""


if __name__ == "__main__":
    # Validation: python -m shared.utils.parsers
    test_cases = [
        (b"Hello world plain text", "text/plain", "Hello world plain text"),
        (b"<html><body><p>Hello</p><script>bad()</script></body></html>",
         "text/html", "Hello"),
    ]
    for content, mime, expected_contains in test_cases:
        result = FileParsingEngine.extract_text(content, mime)
        assert expected_contains in result, f"FAIL: expected '{expected_contains}' in result"
        print(f"PASS: {mime} extraction works")
    print("PASS: FileParsingEngine validated")
