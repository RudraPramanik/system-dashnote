from pydantic import model_validator
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
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
    # LiteLLM uses this for all hosted provider calls
    OPENAI_API_KEY: str | None = None

    # ──  LiteLLM Embedding ──────────────────────────────
    # Format: "provider/model" — e.g. "openai/text-embedding-3-small"
    # Change this one value to swap embedding providers entirely
    EMBEDDING_MODEL: str = "openai/text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536
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
        return self.ARQ_REDIS_URL or self.REDIS_URL or ""

    @model_validator(mode="after")
    def validate_ai_config(self) -> "Settings":
        if self.CHUNK_OVERLAP >= self.CHUNK_SIZE:
            raise ValueError(
                f"CHUNK_OVERLAP ({self.CHUNK_OVERLAP}) must be less than "
                f"CHUNK_SIZE ({self.CHUNK_SIZE})"
            )
        return self

    class Config:
        env_file = ".env"

# we can call config for env
settings = Settings()
