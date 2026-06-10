"""
LiteLLM embedding provider for DashNoteSystem.

Why LiteLLM?
A single aembedding() call supports OpenAI, Cohere, Voyage, Azure,
and others — swap providers by changing EMBEDDING_MODEL in .env only.
No code changes needed when switching providers.

Current default: openai/text-embedding-3-small (1536 dimensions)
Switch to Voyage: voyage/voyage-3
Switch to Cohere: cohere/embed-english-v3.0
"""
from __future__ import annotations

import logging
import time

import litellm
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ai.embeddings.base import (
    BaseEmbeddingProvider,
    EmbeddingProviderError,
    EmbeddingVector,
)
from config import get_settings

logger = logging.getLogger(__name__)

# Exceptions that are transient — safe to retry
_RETRYABLE_EXCEPTIONS = (
    litellm.exceptions.RateLimitError,
    litellm.exceptions.Timeout,
    litellm.exceptions.ServiceUnavailableError,
    litellm.exceptions.APIConnectionError,
)

# Exceptions that are permanent — do not retry, fail immediately
_FATAL_EXCEPTIONS = (
    litellm.exceptions.AuthenticationError,
    litellm.exceptions.BadRequestError,
    litellm.exceptions.NotFoundError,
)


class LiteLLMEmbeddingProvider(BaseEmbeddingProvider):
    """
    Embedding provider backed by LiteLLM's aembedding().

    Handles:
    - Async batch embedding calls
    - Exponential backoff retry on transient errors
    - Immediate failure on auth/format errors (no retry waste)
    - Empty text filtering (OpenAI rejects empty strings)
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._model = settings.EMBEDDING_MODEL
        self._dimension = settings.EMBEDDING_DIMENSION
        self._batch_size = settings.EMBEDDING_BATCH_SIZE
        self._max_retries = settings.EMBEDDING_MAX_RETRIES
        from shared.llm.env import configure_litellm_env

        configure_litellm_env(settings)

    def get_model_name(self) -> str:
        return self._model

    def get_dimension(self) -> int:
        return self._dimension

    async def embed_texts(self, texts: list[str]) -> list[EmbeddingVector]:
        """
        Embed a list of texts using LiteLLM.

        Filters empty/whitespace texts before calling the provider.
        Retries on transient errors. Fails fast on permanent errors.
        Processes in batches to respect provider rate limits.
        """
        if not texts:
            return []

        clean_texts = [t for t in texts if t and t.strip()]
        if len(clean_texts) < len(texts):
            logger.warning(
                "Filtered %d empty texts before embedding",
                len(texts) - len(clean_texts),
            )
        if not clean_texts:
            return []

        all_vectors: list[EmbeddingVector] = []
        for i in range(0, len(clean_texts), self._batch_size):
            batch = clean_texts[i : i + self._batch_size]
            vectors = await self._embed_batch_with_retry(batch)
            all_vectors.extend(vectors)

        return all_vectors

    async def _embed_batch_with_retry(
        self, texts: list[str]
    ) -> list[EmbeddingVector]:
        """Inner method with tenacity retry applied."""
        try:
            return await self._call_litellm(texts)
        except _FATAL_EXCEPTIONS as e:
            raise EmbeddingProviderError(
                message=str(e),
                provider=self._model,
                retryable=False,
            ) from e
        except _RETRYABLE_EXCEPTIONS as e:
            raise EmbeddingProviderError(
                message=str(e),
                provider=self._model,
                retryable=True,
            ) from e
        except Exception as e:
            raise EmbeddingProviderError(
                message=str(e),
                provider=self._model,
                retryable=True,
            ) from e

    async def _call_litellm(self, texts: list[str]) -> list[EmbeddingVector]:
        """Direct LiteLLM call with tenacity retry (attempts from EMBEDDING_MAX_RETRIES)."""

        @retry(
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential(multiplier=1, min=2, max=30),
            retry=retry_if_exception_type(_RETRYABLE_EXCEPTIONS),
            reraise=True,
        )
        async def _invoke() -> list[EmbeddingVector]:
            start = time.monotonic()
            response = await litellm.aembedding(
                model=self._model,
                input=texts,
            )
            latency_ms = (time.monotonic() - start) * 1000
            logger.debug(
                "LiteLLM embedding complete",
                extra={
                    "model": self._model,
                    "batch_size": len(texts),
                    "latency_ms": round(latency_ms, 2),
                },
            )
            data = response.data if hasattr(response, "data") else response["data"]
            return [item["embedding"] for item in data]

        return await _invoke()


if __name__ == "__main__":
    import asyncio
    import os
    import sys

    _src_dir = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    if _src_dir not in sys.path:
        sys.path.insert(0, _src_dir)

    async def _validate() -> None:
        provider = LiteLLMEmbeddingProvider()
        print(f"Model: {provider.get_model_name()}")
        print(f"Dimension: {provider.get_dimension()}")

        try:
            vectors = await provider.embed_texts(["Hello, this is a test."])
            assert len(vectors) == 1
            assert len(vectors[0]) == provider.get_dimension()
            print(f"PASS: got vector of dimension {len(vectors[0])}")
        except EmbeddingProviderError as e:
            print(f"Provider error (expected if no API key): {e}")
        except Exception as e:
            print(f"Error: {e}")

    asyncio.run(_validate())
