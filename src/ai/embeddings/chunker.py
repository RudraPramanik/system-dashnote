"""
Text chunker for DashNoteSystem.

Splits note content into overlapping chunks for vector embedding.
Chunk IDs are fully deterministic — same note always produces
the same chunk IDs. This makes Qdrant upserts idempotent.

chunk_id formula: str(uuid.uuid5(uuid.NAMESPACE_URL, f"{note_id}:{index}"))

IMPORT LAW: This module imports ONLY stdlib, pydantic,
langchain_text_splitters, and config.settings.
Never import FastAPI, SQLAlchemy, or domain modules here.
"""

from __future__ import annotations

import os
import sys
import uuid

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import BaseModel, ConfigDict

from config import settings


class ChunkResult(BaseModel):
    """A single text chunk ready for embedding."""

    model_config = ConfigDict(frozen=True)

    chunk_id: str
    note_id: str
    chunk_index: int
    text: str
    char_start: int
    char_end: int
    token_estimate: int


class TextChunker:
    """
    Wraps RecursiveCharacterTextSplitter with deterministic chunk IDs.

    Why RecursiveCharacterTextSplitter?
    Notes are semi-structured markdown. This splitter respects paragraph
    and sentence boundaries before falling back to character splitting,
    producing more semantically coherent chunks than fixed-size splitting.

    Why deterministic IDs?
    Re-indexing the same note always produces the same chunk_ids.
    Qdrant upsert with the same ID = overwrite, not duplicate.
    Safe to re-run on note update without vector accumulation.
    """

    def __init__(self) -> None:
        self._chunk_size = settings.CHUNK_SIZE
        self._chunk_overlap = settings.CHUNK_OVERLAP
        self._min_length = settings.CHUNK_MIN_LENGTH
        self._splitter = RecursiveCharacterTextSplitter(
            separators=["\n\n", "\n", ". ", "! ", "? ", ", ", " ", ""],
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=len,
            is_separator_regex=False,
        )

    def chunk_note(
        self,
        note_id: str,
        title: str,
        content: str,
    ) -> list[ChunkResult]:
        """
        Chunk a note into overlapping text segments.

        Title is prepended to the full text so every chunk carries
        note context even when retrieved independently.

        Returns empty list if content is blank after stripping.
        """
        if not content or not content.strip():
            return []

        full_text = f"# {title}\n\n{content}"
        raw_chunks: list[str] = self._splitter.split_text(full_text)

        results: list[ChunkResult] = []
        search_start = 0

        for index, chunk_text in enumerate(raw_chunks):
            if len(chunk_text.strip()) < self._min_length:
                continue

            char_start = full_text.find(chunk_text, search_start)
            char_end = char_start + len(chunk_text) if char_start >= 0 else 0
            if char_start >= 0:
                search_start = char_start + 1

            results.append(
                ChunkResult(
                    chunk_id=self._make_chunk_id(note_id, index),
                    note_id=note_id,
                    chunk_index=index,
                    text=chunk_text,
                    char_start=max(char_start, 0),
                    char_end=char_end,
                    token_estimate=len(chunk_text.split()),
                )
            )

        return results

    @staticmethod
    def _make_chunk_id(note_id: str, index: int) -> str:
        """
        Deterministic chunk ID using UUID v5.
        Same note_id + index always produces the same UUID.
        This is critical for idempotent Qdrant upserts.
        """
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{note_id}:{index}"))


if __name__ == "__main__":
    _src_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if _src_dir not in sys.path:
        sys.path.insert(0, _src_dir)

    chunker = TextChunker()
    sample_note_id = "test-note-123"
    sample_title = "My Test Note"
    sample_content = (
        "This is the first paragraph of my note.\n\n"
        "This is the second paragraph with more content to ensure chunking "
        "works correctly across multiple sections."
    )

    chunks = chunker.chunk_note(sample_note_id, sample_title, sample_content)
    print(f"Produced {len(chunks)} chunks")
    for c in chunks:
        print(
            f"  [{c.chunk_index}] id={c.chunk_id[:8]}... "
            f"tokens={c.token_estimate} chars={c.char_start}-{c.char_end}"
        )

    chunks2 = chunker.chunk_note(sample_note_id, sample_title, sample_content)
    ids1 = [c.chunk_id for c in chunks]
    ids2 = [c.chunk_id for c in chunks2]
    assert ids1 == ids2, "FAIL: chunk IDs are not deterministic!"
    print("PASS: chunk IDs are deterministic")
    print("PASS: chunker validated successfully")
