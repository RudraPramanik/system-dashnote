"""
LangGraph AsyncPostgresSaver checkpointer for DashNoteSystem.

The checkpointer persists LangGraph graph execution state between
agent turns. It is the EXECUTION layer — separate from the PRODUCT
layer (ai_threads / ai_messages from Slice 5).

Both layers are linked only by thread_id string. No FK. No shared pool.

Connection isolation:
  SQLAlchemy uses asyncpg driver (postgresql+asyncpg://).
  AsyncPostgresSaver uses psycopg3 async (postgresql://).
  They are separate connection pools — no resource starvation.

Initialization:
  init_checkpointer() called ONCE in FastAPI lifespan startup.
  get_graph_checkpointer() returns cached instance after init.
  Never call get_graph_checkpointer() before init_checkpointer().

IMPORT LAW: Only langgraph, psycopg, config, stdlib.
No SQLAlchemy. No FastAPI.
"""
from __future__ import annotations

import logging

from config import get_settings

logger = logging.getLogger(__name__)

# Module-level singleton — set by init_checkpointer()
_checkpointer = None
_checkpointer_conn = None   # psycopg async connection — kept open


async def init_checkpointer() -> None:
    """
    Initialize the AsyncPostgresSaver checkpointer.

    Called ONCE from FastAPI lifespan startup — before any graph compilation.
    Creates the LangGraph internal checkpoint tables if they don't exist.
    Safe to call on every restart — setup() is idempotent.

    Tables created by LangGraph (separate from your application tables):
      checkpoints, checkpoint_blobs, checkpoint_writes, checkpoint_migrations
    """
    global _checkpointer, _checkpointer_conn

    if _checkpointer is not None:
        logger.debug("Checkpointer already initialized — skipping")
        return

    settings = get_settings()

    try:
        import psycopg
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        # Open a dedicated async psycopg3 connection for the checkpointer
        # This is separate from SQLAlchemy's asyncpg pool — no resource conflict
        _checkpointer_conn = await psycopg.AsyncConnection.connect(
            settings.psycopg_database_url,
            autocommit=True,
        )
        _checkpointer = AsyncPostgresSaver(_checkpointer_conn)

        # Create LangGraph internal tables if they don't exist
        # Idempotent — safe to run on every startup
        await _checkpointer.setup()

        logger.info(
            "LangGraph checkpointer initialized",
            extra={"tables": "checkpoints, checkpoint_blobs, checkpoint_writes"},
        )

    except Exception as e:
        logger.error(
            "Checkpointer initialization failed",
            extra={"error": str(e)},
        )
        # Non-fatal: agent features unavailable but RAG chat continues
        _checkpointer = None
        raise


async def close_checkpointer() -> None:
    """Close the psycopg connection. Called from FastAPI lifespan shutdown."""
    global _checkpointer, _checkpointer_conn
    if _checkpointer_conn is not None:
        try:
            await _checkpointer_conn.close()
            logger.info("Checkpointer connection closed")
        except Exception as e:
            logger.warning("Checkpointer close error", extra={"error": str(e)})
        finally:
            _checkpointer = None
            _checkpointer_conn = None


def get_graph_checkpointer():
    """
    Return the initialized checkpointer.
    Raises RuntimeError if init_checkpointer() was not called first.
    """
    if _checkpointer is None:
        raise RuntimeError(
            "Checkpointer not initialized. "
            "Ensure init_checkpointer() runs in FastAPI lifespan startup."
        )
    return _checkpointer
