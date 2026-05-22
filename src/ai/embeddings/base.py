"""
Abstract base for all embedding providers.

Any provider that implements BaseEmbeddingProvider can be dropped in
without changing any calling code. LiteLLM is the current implementation.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

EmbeddingVector = list[float]  # type alias — a single embedding vector


class EmbeddingProviderError(Exception):
    """Raised when an embedding provider call fails."""

    def __init__(self, message: str, provider: str, retryable: bool = True):
        super().__init__(message)
        self.provider = provider
        self.retryable = retryable


class EmbeddedChunk(BaseModel):
    """
    A text chunk with its embedding vector.
    Produced by the pipeline and passed to Qdrant indexing (Slice 2).
    frozen=True: immutable after creation — safe to pass between layers.
    """

    model_config = ConfigDict(frozen=True)

    chunk_id: str
    note_id: str
    workspace_id: str
    created_by: str
    is_private: bool
    chunk_index: int
    chunk_text: str
    token_count: int
    vector: EmbeddingVector
    metadata: dict[str, Any] = Field(default_factory=dict)


class BaseEmbeddingProvider(ABC):
    """
    Abstract embedding provider.
    Implement this to add a new embedding backend.
    """

    @abstractmethod
    async def embed_texts(self, texts: list[str]) -> list[EmbeddingVector]:
        """Embed a list of texts. Returns one vector per text."""
        ...

    @abstractmethod
    def get_model_name(self) -> str:
        """Return the model identifier string."""
        ...

    @abstractmethod
    def get_dimension(self) -> int:
        """Return the embedding vector dimension."""
        ...

    async def embed_single(self, text: str) -> EmbeddingVector:
        """Convenience method for embedding a single text."""
        vectors = await self.embed_texts([text])
        return vectors[0]
