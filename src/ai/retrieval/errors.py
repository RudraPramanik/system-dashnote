"""Vector store errors for Qdrant operations."""


class VectorStoreError(Exception):
    """Raised when a Qdrant operation fails."""

    def __init__(self, message: str, *, retryable: bool = True):
        super().__init__(message)
        self.retryable = retryable
