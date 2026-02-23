from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET: str
    JWT_REFRESH_SECRET: str = "change-me-refresh-secret"

    # App / runtime
    DEBUG: bool = True

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    class Config:
        env_file = ".env"


settings = Settings()
