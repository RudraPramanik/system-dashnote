"""Qdrant vector retrieval — workspace-scoped search and indexing."""

__all__ = [
    "NoteVectorIndexer",
    "WorkspaceVectorIndex",
    "WorkspaceVectorSearch",
    "get_workspace_vector_search",
]


def __getattr__(name: str):
    if name == "NoteVectorIndexer":
        from ai.retrieval.indexer import NoteVectorIndexer

        return NoteVectorIndexer
    if name == "WorkspaceVectorIndex":
        from ai.retrieval.workspace_search import WorkspaceVectorIndex

        return WorkspaceVectorIndex
    if name == "WorkspaceVectorSearch":
        from ai.retrieval.wrapper import WorkspaceVectorSearch

        return WorkspaceVectorSearch
    if name == "get_workspace_vector_search":
        from ai.retrieval.wrapper import get_workspace_vector_search

        return get_workspace_vector_search
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
