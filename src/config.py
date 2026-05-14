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

    class Config:
        env_file = ".env"

# we can call config for env
settings = Settings()
