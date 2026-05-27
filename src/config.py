from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    DATABASE_URL: str
    JWT_SECRET: str
    JWT_REFRESH_SECRET: str = "change-me-refresh-secret"
    REDIS_URL: str | None = None
    REDIS_ENABLED: bool = True
    CACHE_TTL_SECONDS: int = 60

    # App / runtime
    DEBUG: bool = True

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    # Storage
    STORAGE_BACKEND: str = "local"
    LOCAL_STORAGE_PATH: str = "storage"

    MINIO_ENDPOINT: str = ""
    MINIO_ACCESS_KEY: str = ""
    MINIO_SECRET_KEY: str = ""
    MINIO_BUCKET: str = ""
    MINIO_USE_SSL: bool = False

    R2_ENDPOINT: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET: str = ""

    MAX_FILE_SIZE_BYTES: int = 1_048_576

    # ── Provider Keys ──────────────────────────────────
    # LiteLLM uses these for hosted provider calls (model prefix selects provider)
    OPENAI_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None

    # ──  LiteLLM Embedding ──────────────────────────────
    # Format: "provider/model" — e.g. "openai/text-embedding-3-small"
    # Change this one value to swap embedding providers entirely
    # EMBEDDING_MODEL: str = "openai/text-embedding-3-small"
    EMBEDDING_MODEL: str = "gemini/gemini-embedding-2"
    EMBEDDING_DIMENSION: int = 3072
    EMBEDDING_BATCH_SIZE: int = 32
    EMBEDDING_MAX_RETRIES: int = 3
    EMBEDDING_CACHE_ENABLED: bool = True
    EMBEDDING_CACHE_TTL: int = 86400      # seconds — 24 hours

    # ── : Chunking ────────────────────────────────────────
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 150
    CHUNK_MIN_LENGTH: int = 50

    # ── : ARQ Background Worker ──────────────────────────
    ARQ_REDIS_URL: str = ""               # falls back to REDIS_URL if empty
    WORKER_MAX_JOBS: int = 5              # tune to your OpenAI tier TPM limit

    # ── AI Slice 2: Qdrant vector store ─────────────────
    QDRANT_URL: str | None = None
    QDRANT_API_KEY: str | None = None
    QDRANT_NOTES_COLLECTION: str = "notes_chunks"
    QDRANT_TIMEOUT: int = 30

    # ── AI Slice 3: LLM ────────────────────────────────────────────
    # gemini/gemini-2.5-flash: fast, high-context, low-latency
    # Change this string to swap LLM providers — no code change needed
    LLM_MODEL: str = "gemini/gemini-2.5-flash"
    LLM_TEMPERATURE: float = 0.0
    LLM_MAX_TOKENS: int = 2048
    TOKEN_BUDGET_PER_REQUEST: int = 8000   # max chars of context sent to LLM

    # ── AI Slice 3: LangSmith (wired now, enabled in Slice 10) ─────
    LANGSMITH_API_KEY: str | None = None
    LANGSMITH_PROJECT: str = "dashnote"
    LANGSMITH_TRACING_ENABLED: bool = False

    # ── AI Slice 5: Memory ──────────────────────────────────────────
    AI_THREAD_MESSAGE_LIMIT: int = 20   # recent messages loaded into context

    @property
    def ai_enabled(self) -> bool:
        """
        Global AI feature toggle.
        False = all embedding/LLM paths are skipped safely.
        Set OPENAI_API_KEY and/or GEMINI_API_KEY for the configured EMBEDDING_MODEL.
        """
        return bool(self.OPENAI_API_KEY or self.GEMINI_API_KEY)

    @property
    def effective_arq_redis_url(self) -> str:
        """ARQ uses its own Redis URL, falls back to main REDIS_URL."""
        return self.ARQ_REDIS_URL or self.REDIS_URL or ""

    @property
    def qdrant_enabled(self) -> bool:
        """True when Qdrant URL is configured (local container or cloud)."""
        return bool(self.QDRANT_URL)

    @property
    def langsmith_enabled(self) -> bool:
        """True when LangSmith tracing is configured and active."""
        return bool(self.LANGSMITH_API_KEY) and self.LANGSMITH_TRACING_ENABLED

    @model_validator(mode="after")
    def validate_ai_config(self) -> "Settings":
        if self.CHUNK_OVERLAP >= self.CHUNK_SIZE:
            raise ValueError(
                f"CHUNK_OVERLAP ({self.CHUNK_OVERLAP}) must be less than "
                f"CHUNK_SIZE ({self.CHUNK_SIZE})"
            )
        return self

# we can call config for env
settings = Settings()


def get_settings() -> Settings:
    """Return the process-wide Settings singleton."""
    return settings
