"""Citation mapping for notes vs files."""

from ai.prompts.rag import RAG_SYSTEM_INSTRUCTION
from ai.services.rag_service import EMPTY_RETRIEVAL_ANSWER, _citation_from_chunk


def test_file_hit_citation_has_source_type_file():
    citation = _citation_from_chunk(
        {
            "chunk_id": "chunk-file-1",
            "note_id": "",
            "file_id": "2c13e530-3a39-4547-b5c8-2b47cee89966",
            "source_type": "file",
            "title": "Paper",
            "score": 0.91,
        }
    )
    assert citation.source_type == "file"
    assert citation.file_id == "2c13e530-3a39-4547-b5c8-2b47cee89966"
    assert citation.note_id == ""
    assert citation.chunk_id == "chunk-file-1"


def test_note_hit_citation_keeps_source_type_note():
    citation = _citation_from_chunk(
        {
            "chunk_id": "chunk-note-1",
            "note_id": "41",
            "file_id": "",
            "source_type": "note",
            "title": "Untitled note",
            "score": 0.7,
        }
    )
    assert citation.source_type == "note"
    assert citation.note_id == "41"
    assert citation.file_id == ""


def test_empty_retrieval_copy_mentions_files():
    assert "notes and files" in EMPTY_RETRIEVAL_ANSWER
    assert "notes and files" in RAG_SYSTEM_INSTRUCTION
