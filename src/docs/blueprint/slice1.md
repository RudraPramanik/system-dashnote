# Slice 1 — Embed
## Final Cursor Prompts (Critic-Reviewed, LiteLLM, Production-Safe)

> **How to use**
> - Run sub-steps in strict order. Review output before proceeding.
> - Open ONLY the files listed under "Files to open" for each prompt.
> - After each sub-step: run the validation command. Do not proceed if it fails.
> - Each prompt is fully self-contained — no memory assumed from prior prompts.

---

## ARCHITECTURE LAW
### Paste this as your FIRST message in every new Cursor Composer session.

```
ARCHITECTURE LAW — DashNoteSystem. Memorise and enforce in ALL generated code.

LAYER STRUCTURE (all inside src/):
  src/shared/    → contracts, events, schemas. Imports NOTHING from other layers.
  src/ai/        → AI orchestration. No HTTP. No FastAPI.
  src/worker/    → ARQ background jobs. No HTTP. No FastAPI.
  src/notes/     → existing domain. Minimal additions only.

AI MODULE IMPORT LAW — src/ai/* may ONLY import from:
  - src.shared.*
  - src.config.settings
  - src.core.redis.*
  - stdlib + third-party packages

AI MODULES MUST NEVER IMPORT:
  - FastAPI, Request, Response, APIRouter, Depends, HTTPException
  - SQLAlchemy sessions or any repository class
  - src.notes.*, src.files.*, src.auth.*, src.workspaces.*
  - src.worker.*

WORKER MODULES MUST NEVER IMPORT:
  - FastAPI or any HTTP-related module
  - Domain repositories directly

ROUTER LAW:
  - Do not refactor, reorder, or rewrite existing router logic
  - Only append minimal enqueue blocks after successful DB commits
  - Never move, rename, or delete existing route functions

INFRA LAW:
  - Do not create additional Dockerfiles or docker-compose files
  - Do not create requirements.worker.txt or requirements.api.txt
  - All changes go into the existing Dockerfile and requirements.txt
  - Do not install or use qdrant-client in Slice 1 — that is Slice 2

PYDANTIC LAW:
  - Use Pydantic V2 throughout — BaseModel, ConfigDict, model_validator
  - All shared data models use ConfigDict(frozen=True)
  - Use Python 3.11+ type hints: str | None not Optional[str]

Acknowledge these laws before writing any code.
```

---

## Sub-step 1.1 — Infra Foundation

**Goal:** Settings fields, .env vars, docker-compose additions (worker + qdrant).
Qdrant container runs. Nothing else changes.

**Files to open in Cursor:**
- `src/config/settings.py`
- `.env`
- `docker-compose.yml`

---

```
ROLE: You are a senior backend engineer on DashNoteSystem.

OBJECTIVE: Sub-step 1.1 — Inject AI configuration variables and add
infrastructure services. Append-only. Nothing existing is modified.

LAWS IN EFFECT:
- Append-only. Never modify existing fields, credentials, or services.
- Do not create new Dockerfiles or compose files.
- Do not install qdrant-client yet — Qdrant container only, no client code.
- Do not create any Python files in this step.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 1 — src/config/settings.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Read the existing Settings class carefully.
Append these field groups at the END of the class, after all existing fields.
Skip any field that already exists.

    # ── AI Slice 1: Provider Keys ──────────────────────────────────
    # LiteLLM uses this for all hosted provider calls
    OPENAI_API_KEY: str | None = None

    # ── AI Slice 1: LiteLLM Embedding ──────────────────────────────
    # Format: "provider/model" — e.g. "openai/text-embedding-3-small"
    # Change this one value to swap embedding providers entirely
    EMBEDDING_MODEL: str = "openai/text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536
    EMBEDDING_BATCH_SIZE: int = 32
    EMBEDDING_MAX_RETRIES: int = 3
    EMBEDDING_CACHE_ENABLED: bool = True
    EMBEDDING_CACHE_TTL: int = 86400      # seconds — 24 hours

    # ── AI Slice 1: Chunking ────────────────────────────────────────
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 150
    CHUNK_MIN_LENGTH: int = 50

    # ── AI Slice 1: ARQ Background Worker ──────────────────────────
    ARQ_REDIS_URL: str = ""               # falls back to REDIS_URL if empty
    WORKER_MAX_JOBS: int = 5              # tune to your OpenAI tier TPM limit

Then append these computed properties after the new fields.
Check they do not already exist before adding:

    @property
    def ai_enabled(self) -> bool:
        """
        Global AI feature toggle.
        False = all embedding/LLM paths are skipped safely.
        Set OPENAI_API_KEY to enable. Works as a kill-switch in production.
        """
        return bool(self.OPENAI_API_KEY)

    @property
    def effective_arq_redis_url(self) -> str:
        """ARQ uses its own Redis URL, falls back to main REDIS_URL."""
        return self.ARQ_REDIS_URL or self.REDIS_URL

Then append this validator. Check it does not already exist:

    @model_validator(mode="after")
    def validate_ai_config(self) -> "Settings":
        if self.CHUNK_OVERLAP >= self.CHUNK_SIZE:
            raise ValueError(
                f"CHUNK_OVERLAP ({self.CHUNK_OVERLAP}) must be less than "
                f"CHUNK_SIZE ({self.CHUNK_SIZE})"
            )
        return self

Add these imports at the top if not already present:
  from typing import Literal   (only if Literal is used elsewhere in the file)
  model_validator from pydantic (only if not already imported)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 2 — .env
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Read the existing .env carefully.
Append these lines at the very bottom.
Skip any variable that already exists.

# ── AI Slice 1 ─────────────────────────────────────────────────────
OPENAI_API_KEY=sk-your-key-here
EMBEDDING_MODEL=openai/text-embedding-3-small
EMBEDDING_DIMENSION=1536
EMBEDDING_BATCH_SIZE=32
EMBEDDING_MAX_RETRIES=3
EMBEDDING_CACHE_ENABLED=true
EMBEDDING_CACHE_TTL=86400
CHUNK_SIZE=1000
CHUNK_OVERLAP=150
CHUNK_MIN_LENGTH=50
ARQ_REDIS_URL=redis://redis:6379
WORKER_MAX_JOBS=5

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 3 — docker-compose.yml
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Read the existing docker-compose.yml carefully.
Identify which services already exist.
DO NOT modify any existing service.
DO NOT change any existing credentials, ports, or volumes.

If `worker` service does not exist, append it under services:

  worker:
    build: .
    command: python -m arq src.worker.main.WorkerSettings
    env_file: .env
    depends_on:
      - db
      - redis
    restart: unless-stopped
    # Scale independently: docker compose up --scale worker=3 -d

If `qdrant` service does not exist, append it under services:

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage
    restart: unless-stopped
    # Dev only — for production set QDRANT_URL to Qdrant Cloud in .env

Append to the existing volumes section (do not replace it):
  qdrant_data:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Show me exactly the lines to append for each file.
Label each block clearly:
  === APPEND TO src/config/settings.py ===
  === APPEND TO .env ===
  === APPEND TO docker-compose.yml ===

Do not reprint files in full. Show additions only.
```

**Validation:**
```powershell
docker compose up -d qdrant
curl.exe -sS http://127.0.0.1:6333/health
# Expected: {"title":"qdrant - vector search engine",...}

# Verify settings load without error:
docker compose exec api python -c "from src.config.settings import get_settings; s=get_settings(); print('ai_enabled:', s.ai_enabled)"
# Expected: ai_enabled: False  (until OPENAI_API_KEY is set with a real key)
```

**Commit:**
```bash
git commit -am "infra(slice1.1): add litellm config, worker service, qdrant container"
```

---

## Sub-step 1.2A — Packages + Shared Contracts + Chunker

**Goal:** Install packages. Create shared contracts. Build the chunker.
No embedding code yet. No LiteLLM yet.

**Files to open in Cursor:**
- `requirements.txt`
- `src/shared/contracts/indexing.py` (create if missing)
- `src/ai/chunker.py` (create empty)
- `src/config/settings.py` (reference only)

---

```
ROLE: You are a senior backend engineer on DashNoteSystem.

OBJECTIVE: Sub-step 1.2A — Install packages, define shared contracts,
build deterministic text chunker.

LAWS IN EFFECT:
- src/ai/chunker.py imports ONLY from: stdlib, pydantic, langchain_text_splitters,
  src.config.settings, src.shared.*
- No FastAPI, no SQLAlchemy, no HTTP logic in chunker
- Do not install qdrant-client — that is Slice 2
- Do not create any embedding code in this step

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 1 — requirements.txt
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Read requirements.txt. Append ONLY packages not already present.
Add under this comment at the bottom:

# --- AI Slice 1: Embedding pipeline ---
litellm>=1.35.0
langchain-text-splitters>=0.2.0
arq>=0.26.0
tenacity>=8.3.0
tiktoken>=0.7.0

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 2 — src/shared/contracts/indexing.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Create or update this file. If it already has content, only add missing classes.

Module docstring:
"""
Contracts for note indexing operations.
API enqueues IndexingRequest. Worker processes it.
This module imports NOTHING from src/ai/, src/worker/, or domain modules.
"""

from __future__ import annotations
from enum import Enum
from typing import Any
from uuid import uuid4
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, model_validator

class IndexingOperation(str, Enum):
    UPSERT = "upsert"
    DELETE = "delete"

class IndexingRequest(BaseModel):
    """Enqueued by API after note create/update. Worker processes this."""
    model_config = ConfigDict(frozen=True)

    request_id: str = Field(default_factory=lambda: str(uuid4()))
    operation: IndexingOperation
    note_id: str
    workspace_id: str
    created_by: str
    is_private: bool
    title: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @model_validator(mode="after")
    def content_required_for_upsert(self) -> "IndexingRequest":
        if self.operation == IndexingOperation.UPSERT and not self.content.strip():
            raise ValueError("content must not be empty for upsert operation")
        return self

class DeletionRequest(BaseModel):
    """Enqueued by API after note delete. Worker removes vectors."""
    model_config = ConfigDict(frozen=True)

    request_id: str = Field(default_factory=lambda: str(uuid4()))
    note_id: str
    workspace_id: str
    deleted_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class IndexingResult(BaseModel):
    """Returned by worker after indexing completes."""
    model_config = ConfigDict(frozen=True)

    request_id: str
    note_id: str
    workspace_id: str
    success: bool
    chunks_indexed: int = 0
    error: str | None = None
    latency_ms: float = 0.0
    completed_at: datetime = Field(default_factory=datetime.utcnow)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 3 — src/ai/chunker.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Create this file completely.

Module docstring:
"""
Text chunker for DashNoteSystem.

Splits note content into overlapping chunks for vector embedding.
Chunk IDs are fully deterministic — same note always produces
the same chunk IDs. This makes Qdrant upserts idempotent.

chunk_id formula: str(uuid.uuid5(uuid.NAMESPACE_URL, f"{note_id}:{index}"))

IMPORT LAW: This module imports ONLY stdlib, pydantic,
langchain_text_splitters, and src.config.settings.
Never import FastAPI, SQLAlchemy, or domain modules here.
"""
from __future__ import annotations

import uuid
from typing import Any
from pydantic import BaseModel, ConfigDict, Field
from langchain_text_splitters import RecursiveCharacterTextSplitter
from src.config.settings import get_settings

class ChunkResult(BaseModel):
    """A single text chunk ready for embedding."""
    model_config = ConfigDict(frozen=True)

    chunk_id: str          # deterministic uuid5
    note_id: str
    chunk_index: int
    text: str
    char_start: int
    char_end: int
    token_estimate: int    # approximate: len(text.split())

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
        settings = get_settings()
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
            # Skip chunks that are too short to be meaningful
            if len(chunk_text.strip()) < self._min_length:
                continue

            # Find character positions in the original full_text
            char_start = full_text.find(chunk_text, search_start)
            char_end = char_start + len(chunk_text) if char_start >= 0 else 0
            if char_start >= 0:
                search_start = char_start + 1

            results.append(ChunkResult(
                chunk_id=self._make_chunk_id(note_id, index),
                note_id=note_id,
                chunk_index=index,
                text=chunk_text,
                char_start=max(char_start, 0),
                char_end=char_end,
                token_estimate=len(chunk_text.split()),
            ))

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
    # Quick validation: python -m src.ai.chunker
    chunker = TextChunker()
    sample_note_id = "test-note-123"
    sample_title = "My Test Note"
    sample_content = "This is the first paragraph of my note.\n\nThis is the second paragraph with more content to ensure chunking works correctly across multiple sections."

    chunks = chunker.chunk_note(sample_note_id, sample_title, sample_content)
    print(f"Produced {len(chunks)} chunks")
    for c in chunks:
        print(f"  [{c.chunk_index}] id={c.chunk_id[:8]}... tokens={c.token_estimate} chars={c.char_start}-{c.char_end}")

    # Verify determinism
    chunks2 = chunker.chunk_note(sample_note_id, sample_title, sample_content)
    ids1 = [c.chunk_id for c in chunks]
    ids2 = [c.chunk_id for c in chunks2]
    assert ids1 == ids2, "FAIL: chunk IDs are not deterministic!"
    print("PASS: chunk IDs are deterministic")
    print("PASS: chunker validated successfully")

OUTPUT FORMAT:
Generate each file completely with zero truncation placeholders.
```

**Validation:**
```powershell
docker compose build api
# Expected: builds cleanly, no dependency conflicts

docker compose exec api python -m src.ai.chunker
# Expected:
#   Produced N chunks
#   [0] id=xxxxxxxx... tokens=N chars=0-NNN
#   PASS: chunk IDs are deterministic
#   PASS: chunker validated successfully
```

**Commit:**
```bash
git commit -am "feat(slice1.2a): add packages, shared contracts, deterministic chunker"
```

---

## Sub-step 1.2B — LiteLLM Embedding Provider

**Goal:** Abstract embedding base class. LiteLLM async provider with retry.
Singleton factory. No pipeline yet.

**Files to open in Cursor:**
- `src/ai/embeddings/base.py` (create empty)
- `src/ai/embeddings/litellm_provider.py` (create empty)
- `src/ai/embeddings/factory.py` (create empty)
- `src/config/settings.py` (reference only)

---

```
ROLE: You are a senior backend engineer on DashNoteSystem.

OBJECTIVE: Sub-step 1.2B — Implement LiteLLM embedding provider,
abstract base class, and singleton factory.

LAWS IN EFFECT:
- These files import ONLY from: stdlib, litellm, tenacity, pydantic,
  src.config.settings, src.shared.*
- NEVER import FastAPI, SQLAlchemy, repositories, or domain modules
- Do not write any pipeline orchestration here — that is 1.2C
- Do not write any cache logic here — that is 1.2C
- Do not install or reference qdrant-client

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 1 — src/ai/embeddings/base.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
Abstract base for all embedding providers.

Any provider that implements BaseEmbeddingProvider can be dropped in
without changing any calling code. LiteLLM is the current implementation.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from pydantic import BaseModel, ConfigDict

EmbeddingVector = list[float]   # type alias — a single embedding vector

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
    metadata: dict = {}

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

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 2 — src/ai/embeddings/litellm_provider.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
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
from typing import Any

import litellm
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from src.ai.embeddings.base import (
    BaseEmbeddingProvider,
    EmbeddingVector,
    EmbeddingProviderError,
)
from src.config.settings import get_settings

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

        # Filter out empty strings — most providers reject them
        clean_texts = [t for t in texts if t and t.strip()]
        if len(clean_texts) < len(texts):
            logger.warning(
                "Filtered %d empty texts before embedding",
                len(texts) - len(clean_texts),
            )
        if not clean_texts:
            return []

        # Process in batches to respect provider limits
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
            # Auth errors, bad requests — no point retrying
            raise EmbeddingProviderError(
                message=str(e),
                provider=self._model,
                retryable=False,
            ) from e
        except Exception as e:
            raise EmbeddingProviderError(
                message=str(e),
                provider=self._model,
                retryable=True,
            ) from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type(_RETRYABLE_EXCEPTIONS),
        reraise=True,
    )
    async def _call_litellm(self, texts: list[str]) -> list[EmbeddingVector]:
        """Direct LiteLLM call with retry decorator."""
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
        return [item["embedding"] for item in response["data"]]


if __name__ == "__main__":
    # Quick validation: python -m src.ai.embeddings.litellm_provider
    # Requires OPENAI_API_KEY to be set in .env
    import asyncio

    async def _validate() -> None:
        provider = LiteLLMEmbeddingProvider()
        print(f"Model: {provider.get_model_name()}")
        print(f"Dimension: {provider.get_dimension()}")

        # Test with a simple text
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

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 3 — src/ai/embeddings/factory.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
Embedding provider factory and FastAPI dependency.

This is the ONLY place where providers are instantiated.
All calling code uses get_embedding_provider() — never imports
a specific provider class directly.
"""
from __future__ import annotations

import asyncio
import logging
from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from src.ai.embeddings.base import BaseEmbeddingProvider

logger = logging.getLogger(__name__)

# Module-level singleton — one provider instance per process
_provider_instance: BaseEmbeddingProvider | None = None
_provider_lock = asyncio.Lock()


async def get_embedding_provider() -> BaseEmbeddingProvider:
    """
    FastAPI dependency and singleton factory.

    Returns the same provider instance for every request.
    Thread-safe via asyncio.Lock — safe for async concurrent requests.
    Provider type is determined by EMBEDDING_MODEL in settings.

    Usage in routes:
        provider: EmbeddingProviderDep
    Usage elsewhere:
        provider = await get_embedding_provider()
    """
    global _provider_instance

    if _provider_instance is not None:
        return _provider_instance

    async with _provider_lock:
        # Double-checked locking — re-check after acquiring lock
        if _provider_instance is not None:
            return _provider_instance

        # Only LiteLLM provider for now — add others here if needed
        from src.ai.embeddings.litellm_provider import LiteLLMEmbeddingProvider
        _provider_instance = LiteLLMEmbeddingProvider()
        logger.info(
            "Embedding provider initialised",
            extra={"model": _provider_instance.get_model_name()},
        )

    return _provider_instance


async def reset_embedding_provider() -> None:
    """Reset singleton — used in tests only."""
    global _provider_instance
    _provider_instance = None


# Annotated type alias for clean FastAPI dependency injection
EmbeddingProviderDep = Annotated[
    BaseEmbeddingProvider,
    Depends(get_embedding_provider),
]

OUTPUT FORMAT:
Generate all three files completely with zero truncation placeholders.
```

**Validation:**
```powershell
docker compose build api
# Expected: builds cleanly

docker compose exec api python -m src.ai.embeddings.litellm_provider
# Expected (without real API key):
#   Model: openai/text-embedding-3-small
#   Dimension: 1536
#   Provider error (expected if no API key): ...
#
# Expected (with real API key in .env):
#   PASS: got vector of dimension 1536
```

**Commit:**
```bash
git commit -am "feat(slice1.2b): add litellm embedding provider, base class, factory"
```

---

## Sub-step 1.2C — Embedding Cache + Pipeline

**Goal:** Redis embedding cache. Pipeline that orchestrates
chunk → cache check → embed → cache write → return EmbeddedChunks.

**Files to open in Cursor:**
- `src/ai/cache.py` (create empty)
- `src/ai/pipeline.py` (create empty)
- `src/ai/chunker.py` (reference)
- `src/ai/embeddings/factory.py` (reference)
- `src/config/settings.py` (reference)

---

```
ROLE: You are a senior backend engineer on DashNoteSystem.

OBJECTIVE: Sub-step 1.2C — Implement Redis embedding cache and
pipeline orchestrator that ties chunker + provider + cache together.

LAWS IN EFFECT:
- src/ai/cache.py and src/ai/pipeline.py import ONLY from:
  stdlib, pydantic, redis (async), src.config.settings,
  src.ai.chunker, src.ai.embeddings.*, src.shared.*
- NEVER import FastAPI, SQLAlchemy, or domain repositories
- Do not write any Qdrant code — that is Slice 2
- Do not write any ARQ task code — that is Sub-step 1.3

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 1 — src/ai/cache.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
Redis embedding cache for DashNoteSystem.

Cache key format: embed:v1:{sha256(chunk_text)}

Why sha256(chunk_text)?
- Same text always produces the same cache key
- Provider-agnostic: same text, same vector regardless of call count
- Changing EMBEDDING_MODEL invalidates naturally (different vectors)
- No note_id in key: same text in different notes shares the cache

Cache hit = skip OpenAI API call entirely = zero cost for repeated text.
Primary use case: note updates that change only a few chunks.

IMPORT LAW: Only stdlib, redis.asyncio, src.config.settings
"""
from __future__ import annotations

import hashlib
import json
import logging
from typing import TYPE_CHECKING

from src.ai.embeddings.base import EmbeddingVector

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)

_CACHE_KEY_PREFIX = "embed:v1"


def _make_cache_key(chunk_text: str) -> str:
    """
    Deterministic cache key from chunk text content.
    sha256 of the text → consistent key for identical content.
    """
    text_hash = hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()
    return f"{_CACHE_KEY_PREFIX}:{text_hash}"


async def get_cached_vector(
    chunk_text: str,
    redis: "Redis",
) -> EmbeddingVector | None:
    """
    Retrieve a cached embedding vector for this chunk text.
    Returns None on cache miss or if caching is disabled.
    """
    from src.config.settings import get_settings
    settings = get_settings()

    if not settings.EMBEDDING_CACHE_ENABLED:
        return None

    try:
        key = _make_cache_key(chunk_text)
        cached = await redis.get(key)
        if cached:
            logger.debug("Embedding cache hit", extra={"key": key[:20]})
            return json.loads(cached)
    except Exception as e:
        # Cache failure is non-fatal — degrade gracefully
        logger.warning("Embedding cache read failed: %s", e)

    return None


async def cache_vector(
    chunk_text: str,
    vector: EmbeddingVector,
    redis: "Redis",
) -> None:
    """
    Store an embedding vector in Redis cache.
    TTL from settings.EMBEDDING_CACHE_TTL (default 24h).
    Failures are logged but never propagate — cache is non-critical.
    """
    from src.config.settings import get_settings
    settings = get_settings()

    if not settings.EMBEDDING_CACHE_ENABLED:
        return

    try:
        key = _make_cache_key(chunk_text)
        await redis.setex(
            key,
            settings.EMBEDDING_CACHE_TTL,
            json.dumps(vector),
        )
        logger.debug("Embedding cached", extra={"key": key[:20]})
    except Exception as e:
        logger.warning("Embedding cache write failed: %s", e)


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 2 — src/ai/pipeline.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
Embedding pipeline for DashNoteSystem.

Orchestrates the full embedding flow for a single note:
  1. Chunk the note content (TextChunker)
  2. Check Redis cache for each chunk (EmbeddingCache)
  3. Embed uncached chunks in batch (LiteLLM provider)
  4. Write new vectors to cache
  5. Return list[EmbeddedChunk] ready for Qdrant (Slice 2)

This module has NO knowledge of Qdrant, ARQ, or HTTP.
It produces EmbeddedChunk objects and that is all.

IMPORT LAW: Only stdlib, pydantic, src.ai.*, src.shared.*, src.config.settings
"""
from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict

from src.ai.chunker import TextChunker
from src.ai.embeddings.base import BaseEmbeddingProvider, EmbeddedChunk, EmbeddingProviderError
from src.ai import cache as embedding_cache

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class PipelineResult(BaseModel):
    """Result of running the embedding pipeline on one note."""
    model_config = ConfigDict(frozen=True)

    note_id: str
    workspace_id: str
    chunks_processed: int
    chunks_from_cache: int
    chunks_embedded: int
    total_tokens: int
    latency_ms: float
    embedded_chunks: list[EmbeddedChunk]


class EmbeddingPipeline:
    """
    Orchestrates chunking, cache lookup, and embedding for a note.

    Constructed once and reused — stateless between calls.
    Redis is optional: if None, cache is skipped gracefully.
    """

    def __init__(
        self,
        provider: BaseEmbeddingProvider,
        redis: "Redis | None" = None,
    ) -> None:
        self._provider = provider
        self._redis = redis
        self._chunker = TextChunker()

    async def process_note(
        self,
        *,
        note_id: str,
        workspace_id: str,
        created_by: str,
        is_private: bool,
        title: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> PipelineResult:
        """
        Run the full embedding pipeline for one note.

        Keyword-only args prevent positional mistakes on sensitive fields
        like workspace_id and is_private.
        """
        start = time.monotonic()

        # Step 1: chunk
        chunks = self._chunker.chunk_note(note_id, title, content)
        if not chunks:
            logger.info("No chunks produced — empty content?", extra={"note_id": note_id})
            return PipelineResult(
                note_id=note_id,
                workspace_id=workspace_id,
                chunks_processed=0,
                chunks_from_cache=0,
                chunks_embedded=0,
                total_tokens=0,
                latency_ms=0.0,
                embedded_chunks=[],
            )

        # Step 2: cache lookup
        vectors_by_index: dict[int, list[float]] = {}
        uncached_indices: list[int] = []

        for i, chunk in enumerate(chunks):
            if self._redis:
                cached = await embedding_cache.get_cached_vector(chunk.text, self._redis)
                if cached is not None:
                    vectors_by_index[i] = cached
                    continue
            uncached_indices.append(i)

        chunks_from_cache = len(chunks) - len(uncached_indices)

        # Step 3: embed uncached chunks
        if uncached_indices:
            uncached_texts = [chunks[i].text for i in uncached_indices]
            try:
                new_vectors = await self._provider.embed_texts(uncached_texts)
            except EmbeddingProviderError as e:
                logger.error(
                    "Embedding provider error",
                    extra={"note_id": note_id, "error": str(e), "retryable": e.retryable},
                )
                raise

            # Step 4: cache new vectors
            for local_idx, chunk_idx in enumerate(uncached_indices):
                vector = new_vectors[local_idx]
                vectors_by_index[chunk_idx] = vector
                if self._redis:
                    await embedding_cache.cache_vector(
                        chunks[chunk_idx].text, vector, self._redis
                    )

        # Step 5: assemble EmbeddedChunk objects
        embedded: list[EmbeddedChunk] = []
        for i, chunk in enumerate(chunks):
            vector = vectors_by_index.get(i)
            if vector is None:
                logger.warning("Missing vector for chunk %d — skipping", i)
                continue
            embedded.append(EmbeddedChunk(
                chunk_id=chunk.chunk_id,
                note_id=note_id,
                workspace_id=workspace_id,
                created_by=created_by,
                is_private=is_private,
                chunk_index=chunk.chunk_index,
                chunk_text=chunk.text,
                token_count=chunk.token_estimate,
                vector=vector,
                metadata={
                    "char_start": chunk.char_start,
                    "char_end": chunk.char_end,
                    **(metadata or {}),
                },
            ))

        latency_ms = (time.monotonic() - start) * 1000
        total_tokens = sum(c.token_count for c in embedded)

        logger.info(
            "Embedding pipeline complete",
            extra={
                "note_id": note_id,
                "workspace_id": workspace_id,
                "chunks_processed": len(chunks),
                "chunks_from_cache": chunks_from_cache,
                "chunks_embedded": len(uncached_indices),
                "total_tokens": total_tokens,
                "latency_ms": round(latency_ms, 2),
            },
        )

        return PipelineResult(
            note_id=note_id,
            workspace_id=workspace_id,
            chunks_processed=len(chunks),
            chunks_from_cache=chunks_from_cache,
            chunks_embedded=len(uncached_indices),
            total_tokens=total_tokens,
            latency_ms=round(latency_ms, 2),
            embedded_chunks=embedded,
        )


if __name__ == "__main__":
    # Validation: docker compose exec api python -m src.ai.pipeline
    import asyncio

    async def _validate() -> None:
        from src.ai.embeddings.factory import get_embedding_provider
        provider = await get_embedding_provider()
        pipeline = EmbeddingPipeline(provider=provider, redis=None)

        result = await pipeline.process_note(
            note_id="test-note-001",
            workspace_id="test-ws-001",
            created_by="test-user-001",
            is_private=False,
            title="Test Note",
            content="This is the first paragraph.\n\nThis is the second paragraph with enough content to potentially create multiple chunks if the settings allow for it.",
        )

        print(f"Pipeline result:")
        print(f"  chunks_processed: {result.chunks_processed}")
        print(f"  chunks_from_cache: {result.chunks_from_cache}")
        print(f"  chunks_embedded: {result.chunks_embedded}")
        print(f"  total_tokens: {result.total_tokens}")
        print(f"  latency_ms: {result.latency_ms}")
        print(f"  embedded_chunks: {len(result.embedded_chunks)}")

        if result.embedded_chunks:
            first = result.embedded_chunks[0]
            print(f"  first chunk_id: {first.chunk_id[:8]}...")
            print(f"  first vector dim: {len(first.vector)}")
            assert len(first.vector) > 0, "FAIL: empty vector"
            print("PASS: pipeline produces valid EmbeddedChunk objects")
        else:
            print("INFO: no embedded chunks (expected without API key)")

    asyncio.run(_validate())

OUTPUT FORMAT:
Generate both files completely with zero truncation placeholders.
```

**Validation:**
```powershell
docker compose build api

docker compose exec api python -m src.ai.pipeline
# Expected (without real API key):
#   Pipeline result:
#   chunks_processed: N
#   INFO: no embedded chunks (expected without API key)
#
# Expected (with real API key):
#   PASS: pipeline produces valid EmbeddedChunk objects
```

**Commit:**
```bash
git commit -am "feat(slice1.2c): add embedding cache and pipeline orchestrator"
```

---

## Sub-step 1.3 — ARQ Worker

**Goal:** Worker boots. `embed_note_task` runs. Logs confirm
chunks processed, tokens, latency. Vectors NOT sent to Qdrant yet.

**Files to open in Cursor:**
- `src/worker/main.py`
- `src/worker/tasks.py`
- `src/worker/ingestion/tasks.py` (create empty)
- `src/shared/contracts/indexing.py` (reference)

---

```
ROLE: You are a senior backend engineer on DashNoteSystem.

OBJECTIVE: Sub-step 1.3 — Wire ARQ worker. Register embed_note_task.
Logs must confirm embedding pipeline runs end-to-end.
Vectors are NOT written to Qdrant in this step — that is Slice 2.

LAWS IN EFFECT:
- Worker modules import ONLY: stdlib, arq, pydantic, src.ai.*,
  src.shared.*, src.config.settings, src.core.redis.*
- NEVER import FastAPI, HTTPException, SQLAlchemy sessions,
  or any domain repository in worker code
- Do not add Qdrant client code — that is Slice 2
- Do not refactor existing worker/main.py beyond populating WorkerSettings

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 1 — src/worker/ingestion/tasks.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
Ingestion worker tasks — Slice 1.

embed_note_task: chunks and embeds a note.
Vectors are logged only — Qdrant upsert added in Slice 2.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from src.shared.contracts.indexing import IndexingRequest, IndexingOperation, IndexingResult
from src.config.settings import get_settings

logger = logging.getLogger(__name__)


async def embed_note_task(ctx: dict, *, request_dict: dict) -> dict:
    """
    ARQ task: chunk and embed a note.

    Called by ARQ with the serialised IndexingRequest dict.
    ctx contains ARQ context including redis connection.

    Returns IndexingResult as dict (ARQ serialises this to Redis).

    NOTE (Slice 1): Vectors are logged but NOT written to Qdrant yet.
    Qdrant upsert is added in Slice 2 once retrieval quality is validated.
    """
    start = time.monotonic()
    settings = get_settings()

    try:
        request = IndexingRequest(**request_dict)
    except Exception as e:
        logger.error("Invalid IndexingRequest payload: %s", e)
        return IndexingResult(
            request_id=request_dict.get("request_id", "unknown"),
            note_id=request_dict.get("note_id", "unknown"),
            workspace_id=request_dict.get("workspace_id", "unknown"),
            success=False,
            error=f"Invalid request payload: {e}",
        ).model_dump()

    # Handle deletions — Qdrant deletion added in Slice 2
    if request.operation == IndexingOperation.DELETE:
        logger.info(
            "Delete request received — Qdrant deletion wired in Slice 2",
            extra={"note_id": request.note_id, "workspace_id": request.workspace_id},
        )
        return IndexingResult(
            request_id=request.request_id,
            note_id=request.note_id,
            workspace_id=request.workspace_id,
            success=True,
            chunks_indexed=0,
        ).model_dump()

    if not settings.ai_enabled:
        logger.debug("AI disabled — skipping embedding", extra={"note_id": request.note_id})
        return IndexingResult(
            request_id=request.request_id,
            note_id=request.note_id,
            workspace_id=request.workspace_id,
            success=True,
            chunks_indexed=0,
        ).model_dump()

    try:
        # Get embedding provider (singleton)
        from src.ai.embeddings.factory import get_embedding_provider
        provider = await get_embedding_provider()

        # Get Redis from ARQ context for embedding cache
        redis = ctx.get("redis")

        # Run pipeline
        from src.ai.pipeline import EmbeddingPipeline
        pipeline = EmbeddingPipeline(provider=provider, redis=redis)

        result = await pipeline.process_note(
            note_id=request.note_id,
            workspace_id=request.workspace_id,
            created_by=request.created_by,
            is_private=request.is_private,
            title=request.title,
            content=request.content,
            metadata=request.metadata,
        )

        latency_ms = round((time.monotonic() - start) * 1000, 2)

        logger.info(
            "embed_note_task complete",
            extra={
                "note_id": request.note_id,
                "workspace_id": request.workspace_id,
                "chunks_processed": result.chunks_processed,
                "chunks_from_cache": result.chunks_from_cache,
                "chunks_embedded": result.chunks_embedded,
                "total_tokens": result.total_tokens,
                "latency_ms": latency_ms,
                "qdrant_indexed": False,  # Slice 2 sets this to True
            },
        )

        return IndexingResult(
            request_id=request.request_id,
            note_id=request.note_id,
            workspace_id=request.workspace_id,
            success=True,
            chunks_indexed=result.chunks_processed,
            latency_ms=latency_ms,
        ).model_dump()

    except Exception as e:
        latency_ms = round((time.monotonic() - start) * 1000, 2)
        logger.error(
            "embed_note_task failed",
            extra={
                "note_id": request.note_id,
                "error": str(e),
                "latency_ms": latency_ms,
            },
        )
        return IndexingResult(
            request_id=request.request_id,
            note_id=request.note_id,
            workspace_id=request.workspace_id,
            success=False,
            error=str(e),
            latency_ms=latency_ms,
        ).model_dump()


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 2 — src/worker/tasks.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
ARQ task registry — all background tasks listed here.

Slice 1: embed_note_task
Slice 2: index_chunks_task, delete_note_vectors_task  (TODO)
Slice 7: handle_file_uploaded, handle_note_created    (TODO)
"""
from src.worker.ingestion.tasks import embed_note_task

__all__ = ["embed_note_task"]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 3 — src/worker/main.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
ARQ WorkerSettings — entrypoint for the worker container.
Started with: python -m arq src.worker.main.WorkerSettings
"""
from __future__ import annotations

import logging

from arq.connections import RedisSettings

from src.worker.tasks import embed_note_task
from src.config.settings import get_settings

logger = logging.getLogger(__name__)


async def startup(ctx: dict) -> None:
    """Called once when worker starts. Initialise shared resources."""
    import redis.asyncio as aioredis
    settings = get_settings()
    ctx["redis"] = aioredis.from_url(
        settings.effective_arq_redis_url,
        encoding="utf-8",
        decode_responses=False,
    )
    logger.info("ARQ worker started", extra={"max_jobs": settings.WORKER_MAX_JOBS})


async def shutdown(ctx: dict) -> None:
    """Called once when worker shuts down. Clean up resources."""
    if "redis" in ctx:
        await ctx["redis"].aclose()
    logger.info("ARQ worker stopped")


def _get_redis_settings() -> RedisSettings:
    settings = get_settings()
    return RedisSettings.from_dsn(settings.effective_arq_redis_url)


class WorkerSettings:
    """
    ARQ WorkerSettings.
    Add task functions here as slices are implemented.
    """
    functions = [embed_note_task]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = _get_redis_settings()
    max_jobs = get_settings().WORKER_MAX_JOBS
    job_timeout = 300
    keep_result = 3600   # keep job results in Redis for 1 hour

OUTPUT FORMAT:
Generate all three files completely with zero truncation placeholders.
```

**Validation:**
```powershell
docker compose up -d worker
docker compose logs worker --tail 20
# Expected: "ARQ worker started" — no errors

# Create a test note via API, then:
docker compose logs worker --tail 20
# Expected log line containing:
#   "embed_note_task complete" with chunks_processed, total_tokens, latency_ms
```

**Commit:**
```bash
git commit -am "feat(slice1.3): wire arq worker with embed_note_task"
```

---

## Sub-step 1.4 — Router Enqueue Hooks

**Goal:** Note create/update/delete routes enqueue ARQ jobs.
API response never slows down. Background embedding begins silently.

**Files to open in Cursor:**
- `src/notes/router.py`
- `src/main.py`
- `src/shared/contracts/indexing.py` (reference)

---

```
ROLE: You are a senior backend engineer on DashNoteSystem.

OBJECTIVE: Sub-step 1.4 — Add minimal, non-blocking ARQ enqueue hooks
to the notes router. API response must never be delayed by this code.

LAWS IN EFFECT:
- Do not refactor, reorder, or rewrite any existing router logic
- Do not move, rename, or restructure any existing route function
- Only append the enqueue block AFTER the successful DB commit,
  before the return statement
- The try/except around enqueue must NEVER re-raise
- The API response must be identical whether enqueue succeeds or fails
- Do not import Qdrant, pipeline, or provider into the router

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 1 — src/main.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Read the existing lifespan context manager in src/main.py.
Add ARQ pool initialisation to the startup section and store on app.state.
Add ARQ pool cleanup to the shutdown section.

Append these imports at the top (only if not already present):
  from arq import create_pool
  from arq.connections import RedisSettings

In the lifespan startup block, append:
  # --- AI Slice 1: ARQ pool ---
  from src.config.settings import get_settings as _get_settings
  _s = _get_settings()
  app.state.arq_pool = await create_pool(
      RedisSettings.from_dsn(_s.effective_arq_redis_url)
  )

In the lifespan shutdown block, append:
  # --- AI Slice 1: ARQ pool cleanup ---
  if hasattr(app.state, "arq_pool"):
      await app.state.arq_pool.close()

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 2 — src/notes/router.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Read src/notes/router.py carefully.
Locate the note CREATE, UPDATE, and DELETE route functions.
Do not modify any existing logic.

In the CREATE route, after the DB commit and before return, append:

    # --- AI Slice 1: enqueue embedding job ---
    if settings.ai_enabled:
        try:
            await request.app.state.arq_pool.enqueue_job(
                "embed_note_task",
                request_dict=IndexingRequest(
                    operation=IndexingOperation.UPSERT,
                    note_id=str(note.id),
                    workspace_id=str(ctx.workspace_id),
                    created_by=str(ctx.user_id),
                    is_private=note.is_private,
                    title=note.title,
                    content=body.content,
                ).model_dump(),
            )
        except Exception:
            # Never block the API response for background failures
            logger.warning(
                "Failed to enqueue embedding job",
                extra={"note_id": str(note.id)},
            )

Apply the same pattern to the UPDATE route (operation=UPSERT, same fields).

For the DELETE route, append:

    # --- AI Slice 1: enqueue vector deletion ---
    if settings.ai_enabled:
        try:
            await request.app.state.arq_pool.enqueue_job(
                "embed_note_task",
                request_dict=IndexingRequest(
                    operation=IndexingOperation.DELETE,
                    note_id=note_id,
                    workspace_id=str(ctx.workspace_id),
                    created_by=str(ctx.user_id),
                    is_private=False,
                    title="",
                    content="",
                ).model_dump(),
            )
        except Exception:
            logger.warning(
                "Failed to enqueue deletion job",
                extra={"note_id": note_id},
            )

Add these imports at the top of router.py if not already present:
  from src.shared.contracts.indexing import IndexingRequest, IndexingOperation
  from src.config.settings import get_settings
  settings = get_settings()

Show me exactly which lines are appended and where.
Do not reprint the full router file. Show only the additions and
their exact insertion locations (e.g., "after line X, before return statement").

OUTPUT FORMAT:
For each route, show:
  ROUTE: <function name>
  INSERT AFTER: <description of anchor line>
  CODE:
    <exact code to insert>
```

**Validation:**
```powershell
docker compose up -d --build api

# Create a note:
# POST /notes with your existing auth token

# Check worker received the job:
docker compose logs worker --tail 30
# Expected: "embed_note_task complete"
# with note_id matching the note you just created
# chunks_processed > 0
# qdrant_indexed: false  (becomes true in Slice 2)

# Verify API response time unchanged (background = no delay):
# The POST /notes response must be as fast as before
```

**Commit:**
```bash
git commit -am "feat(slice1.4): enqueue background embedding on note create/update/delete"
```

---

## Sub-step 1.5 — Stabilisation & Observability

**Goal:** Confirm end-to-end flow is stable. Metrics are readable in logs.
Worker handles errors gracefully. Slice 1 gate passed.

**Files to open in Cursor:**
- `src/worker/ingestion/tasks.py`
- `src/ai/pipeline.py`

---

```
ROLE: You are a senior backend engineer on DashNoteSystem.

OBJECTIVE: Sub-step 1.5 — Harden error handling and confirm
structured logging metrics are consistent and readable.

LAWS IN EFFECT:
- No new files in this step — improvements to existing files only
- Do not add Qdrant code
- Do not change function signatures

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK — Review and harden these two files
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Read src/worker/ingestion/tasks.py and src/ai/pipeline.py.

Verify and fix if necessary:

1. Every log.info() and log.error() call uses the `extra={}` dict pattern
   for structured fields — not f-strings in the message body.
   Structured logs: logger.info("msg", extra={"key": value})
   NOT:             logger.info(f"msg key={value}")

2. embed_note_task must log these exact fields on success:
   note_id, workspace_id, chunks_processed, chunks_from_cache,
   chunks_embedded, total_tokens, latency_ms, qdrant_indexed

3. EmbeddingPipeline.process_note must log these exact fields on success:
   note_id, workspace_id, chunks_processed, chunks_from_cache,
   chunks_embedded, total_tokens, latency_ms

4. If EmbeddingProviderError.retryable is False, the task should log
   at ERROR level with "permanent_failure": True in extra fields.
   If retryable is True, log at WARNING (ARQ will retry the job).

5. Confirm empty note content (content="" or "   ") returns a successful
   IndexingResult with chunks_indexed=0, no error, no exception raised.

Show me only the lines that need to change. Do not reprint full files.
```

**Validation — Slice 1 Gate:**
```powershell
# 1. Create a note via API
# 2. Check worker logs:
docker compose logs worker --tail 50 | grep "embed_note_task complete"

# Must show all fields:
# note_id, workspace_id, chunks_processed, chunks_from_cache,
# chunks_embedded, total_tokens, latency_ms, qdrant_indexed: false

# 3. Update the same note — check cache hit:
docker compose logs worker --tail 20
# Must show: chunks_from_cache > 0 (if content unchanged)

# 4. Delete the note:
docker compose logs worker --tail 20
# Must show: "Delete request received — Qdrant deletion wired in Slice 2"

# 5. Verify API health still passes:
curl.exe -sS http://127.0.0.1/health
# Must return status: ok

# SLICE 1 GATE PASSED when all 5 checks are green.
```

**Commit:**
```bash
git commit -am "feat(slice1.5): harden logging and error handling — slice 1 complete"
```

---

## Slice 1 Complete — What Was Built

```
src/shared/contracts/indexing.py    ← IndexingRequest, DeletionRequest, IndexingResult
src/ai/chunker.py                   ← deterministic chunker, uuid5 chunk IDs
src/ai/embeddings/base.py           ← BaseEmbeddingProvider, EmbeddedChunk
src/ai/embeddings/litellm_provider.py ← LiteLLM async provider, tenacity retry
src/ai/embeddings/factory.py        ← singleton, FastAPI dependency
src/ai/cache.py                     ← Redis embedding cache, sha256 key
src/ai/pipeline.py                  ← full orchestration: chunk→cache→embed→result
src/worker/ingestion/tasks.py       ← embed_note_task ARQ handler
src/worker/tasks.py                 ← task registry
src/worker/main.py                  ← ARQ WorkerSettings
src/notes/router.py                 ← enqueue hooks (3 routes, append-only)
src/main.py                         ← ARQ pool lifecycle
docker-compose.yml                  ← worker + qdrant services added
requirements.txt                    ← 5 packages added
settings.py                         ← AI fields appended
.env                                ← AI vars appended
```

```
What is NOT in Slice 1 (belongs to Slice 2):
  ✗ qdrant-client installed
  ✗ Qdrant collection created
  ✗ Vectors upserted to Qdrant
  ✗ Any search or retrieval endpoint
```

> **Next:** Slice 2 prompts wire the `EmbeddedChunk` objects from the pipeline
> directly into Qdrant — collection setup, payload indexes, hybrid search,
> tenant-safe wrapper, and the internal test endpoint for retrieval quality validation.