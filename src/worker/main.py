"""
ARQ WorkerSettings — entrypoint for the worker container.
Started with: python -m arq src.worker.main.WorkerSettings
"""
from __future__ import annotations

import logging
import os
import sys

# Match API bootstrap: flat imports (config, ai, worker) from src/
_SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from arq.connections import RedisSettings

from config import get_settings
from worker.tasks import embed_note_task

logger = logging.getLogger(__name__)


async def startup(ctx: dict) -> None:
    """Called once when worker starts. Initialise shared resources."""
    import redis.asyncio as aioredis

    settings = get_settings()
    url = settings.effective_arq_redis_url
    if not url:
        logger.warning("ARQ Redis URL not configured — embedding cache disabled in worker")
        ctx["redis"] = None
        return

    ctx["redis"] = aioredis.from_url(url, decode_responses=True)
    logger.info(
        "ARQ worker started",
        extra={"max_jobs": settings.WORKER_MAX_JOBS, "redis_url": url},
    )


async def shutdown(ctx: dict) -> None:
    """Called once when worker shuts down. Clean up resources."""
    redis = ctx.get("redis")
    if redis is not None:
        await redis.aclose()
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
    keep_result = 3600
