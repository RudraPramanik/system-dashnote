"""Qdrant vector retrieval — workspace-scoped search and indexing."""

__all__ = ["NoteVectorIndexer", "WorkspaceVectorSearch"]


def __getattr__(name: str):
    if name == "NoteVectorIndexer":
        from ai.retrieval.indexer import NoteVectorIndexer

        return NoteVectorIndexer
    if name == "WorkspaceVectorSearch":
        from ai.retrieval.workspace_search import WorkspaceVectorSearch

        return WorkspaceVectorSearch
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
