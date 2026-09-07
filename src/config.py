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
    # NVIDIA NIM — LLM via nvidia_nim/<model> (see docs/nvidia.md)
    NVIDIA_NIM_API_KEY: str | None = None
    NVIDIA_API_KEY: str | None = None  # alias used in NVIDIA docs / .env
    NVIDIA_NIM_API_BASE: str = "https://integrate.api.nvidia.com/v1"

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
    QDRANT_FILES_COLLECTION: str = "files_chunks"
    QDRANT_TIMEOUT: int = 30

    # ── AI Slice 3: LLM ────────────────────────────────────────────
    # Provider prefix selects backend. Hosted NIM ids are retired often (HTTP 410);
    # LLM_MODEL_FALLBACKS walks additional LiteLLM ids after the primary.
    LLM_MODEL: str = "nvidia_nim/nvidia/nemotron-3-nano-30b-a3b"
    LLM_MODEL_FALLBACKS: str = (
        "nvidia_nim/nvidia/nemotron-3-super-120b-a12b,gemini/gemini-2.5-flash"
    )
    LLM_TEMPERATURE: float = 0.0
    LLM_MAX_TOKENS: int = 2048
    LLM_MAX_RETRIES: int = 4
    LLM_RETRY_MIN_WAIT: float = 2.0
    LLM_RETRY_MAX_WAIT: float = 60.0
    LLM_STRUCTURED_MAX_TOKENS_TAGS: int = 256
    LLM_STRUCTURED_MAX_TOKENS_METADATA: int = 512
    TOKEN_BUDGET_PER_REQUEST: int = 8000   # max chars of context sent to LLM

    # ── AI Slice 3: LangSmith (wired now, enabled in Slice 10) ─────
    LANGSMITH_API_KEY: str | None = None
    LANGSMITH_PROJECT: str = "dashnote"
    LANGSMITH_TRACING_ENABLED: bool = False

    # ── Observability: Langfuse (lazy client; tracing in Step 3) ───
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    # ── AI Slice 5: Memory ──────────────────────────────────────────
    AI_THREAD_MESSAGE_LIMIT: int = 20   # recent messages loaded into context

    # ── AI Slice 6: LangGraph Agent ────────────────────────────────
    AGENT_MAX_ITERATIONS: int = 10    # prevents infinite tool loops
    AGENT_TOOL_TIMEOUT: int = 30      # seconds per tool call

    # ── Inbound channels (email / WhatsApp) ─────────────────────────
    INBOUND_API_KEY: str = ""
    INBOUND_HMAC_SECRET: str = ""
    INBOUND_AGENTIC_ENABLED: bool = False
    INBOUND_AGENTIC_TIMEOUT_SECONDS: float = 12.0
    WHATSAPP_VERIFY_TOKEN: str = ""
    WHATSAPP_APP_SECRET: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""

    @property
    def llm_model_candidates(self) -> list[str]:
        """Primary LLM_MODEL then unique fallbacks, order preserved."""
        seen: set[str] = set()
        out: list[str] = []
        for raw in [self.LLM_MODEL, *self.LLM_MODEL_FALLBACKS.split(",")]:
            model = raw.strip()
            if model and model not in seen:
                seen.add(model)
                out.append(model)
        return out

    @property
    def effective_nvidia_nim_api_key(self) -> str | None:
        """NVIDIA NIM key — accepts NVIDIA_NIM_API_KEY or NVIDIA_API_KEY alias."""
        return self.NVIDIA_NIM_API_KEY or self.NVIDIA_API_KEY

    @property
    def ai_enabled(self) -> bool:
        """
        Global AI feature toggle.
        False = all embedding/LLM paths are skipped safely.
        Requires a key for the configured LLM/embedding providers (any of the below).
        """
        return bool(
            self.OPENAI_API_KEY
            or self.GEMINI_API_KEY
            or self.effective_nvidia_nim_api_key
        )

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

    @property
    def langfuse_enabled(self) -> bool:
        """True when Langfuse API keys are configured."""
        return bool(self.LANGFUSE_PUBLIC_KEY and self.LANGFUSE_SECRET_KEY)

    @property
    def psycopg_database_url(self) -> str:
        """
        DATABASE_URL adapted for psycopg3 (AsyncPostgresSaver).
        Strips '+asyncpg' driver suffix — psycopg3 uses plain postgresql://.
        """
        return self.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

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
