"""ARQ worker entrypoint — register job functions on WorkerSettings."""

from arq.connections import RedisSettings

from src.config import settings


async def noop(ctx) -> None:
    """Placeholder until ingestion jobs are wired."""
    return None


def _redis_dsn() -> str:
    dsn = getattr(settings, "ARQ_REDIS_URL", None) or settings.REDIS_URL
    if not dsn:
        return "redis://localhost:6379"
    return dsn


class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(_redis_dsn())
    functions = [noop]
    max_jobs = int(getattr(settings, "WORKER_MAX_JOBS", 5))
    job_timeout = int(getattr(settings, "WORKER_JOB_TIMEOUT", 300))
