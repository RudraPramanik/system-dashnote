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

# Register ORM models before worker tasks query relationships (File ↔ Note, etc.)
import auth.models  # noqa: F401
import workspaces.models  # noqa: F401
import pages.models  # noqa: F401
import notebooks.models  # noqa: F401
import notes.models  # noqa: F401
import files.models  # noqa: F401
from ai_memory.models import AIThread, AIMessage  # noqa: F401

from arq.connections import RedisSettings

from config import get_settings
from worker.automation.tasks import (
    handle_file_deleted,
    handle_file_uploaded,
    handle_note_created,
    handle_note_updated,
)
from worker.tasks import embed_note_task

logger = logging.getLogger(__name__)


class _ExtraFormatter(logging.Formatter):
    """Append structured `extra={}` fields to console log lines for Compose grep."""

    _SKIP = frozenset(
        {
            "name",
            "msg",
            "args",
            "created",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "module",
            "msecs",
            "message",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "stack_info",
            "exc_info",
            "exc_text",
            "thread",
            "threadName",
            "taskName",
        }
    )

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        extra = {
            k: v
            for k, v in record.__dict__.items()
            if k not in self._SKIP and not k.startswith("_")
        }
        if not extra:
            return base
        parts = " ".join(f"{k}={v}" for k, v in sorted(extra.items()))
        return f"{base} {parts}"


def _configure_worker_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(
        _ExtraFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)


async def startup(ctx: dict) -> None:
    """Called once when worker starts. Initialise shared resources."""
    import redis.asyncio as aioredis

    _configure_worker_logging()
    settings = get_settings()
    url = settings.effective_arq_redis_url
    if not url:
        logger.warning("ARQ Redis URL not configured — embedding cache disabled in worker")
        ctx["redis"] = None
        return

    ctx["redis"] = aioredis.from_url(url, decode_responses=True)

    # --- AI Slice 7: arq_pool for fan-out job enqueuing ---
    from arq import create_pool

    ctx["arq_pool"] = await create_pool(
        RedisSettings.from_dsn(settings.effective_arq_redis_url)
    )
    logger.info("ARQ fan-out pool initialized in worker context")

    if settings.qdrant_enabled:
        from ai.retrieval.collection import ensure_files_collection, ensure_notes_collection

        await ensure_notes_collection()
        await ensure_files_collection()
        logger.info(
            "Qdrant collections ready",
            extra={
                "notes_collection": settings.QDRANT_NOTES_COLLECTION,
                "files_collection": settings.QDRANT_FILES_COLLECTION,
            },
        )

    logger.info(
        "ARQ worker started",
        extra={"max_jobs": settings.WORKER_MAX_JOBS, "redis_url": url},
    )


async def shutdown(ctx: dict) -> None:
    """Called once when worker shuts down. Clean up resources."""
    if "arq_pool" in ctx:
        await ctx["arq_pool"].close()
    redis = ctx.get("redis")
    if redis is not None:
        await redis.aclose()
    from ai.retrieval.client import close_async_qdrant_client

    await close_async_qdrant_client()
    logger.info("ARQ worker stopped")


def _get_redis_settings() -> RedisSettings:
    settings = get_settings()
    return RedisSettings.from_dsn(settings.effective_arq_redis_url)


class WorkerSettings:
    """
    ARQ WorkerSettings.
    Add task functions here as slices are implemented.
    """

    functions = [
        embed_note_task,
        handle_file_uploaded,
        handle_note_created,
        handle_note_updated,
        handle_file_deleted,
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = _get_redis_settings()
    max_jobs = get_settings().WORKER_MAX_JOBS
    job_timeout = 300
    keep_result = 3600
