import os
import sys

# Ensure `src/` is on sys.path so imports like `from auth...` work when running:
#   uvicorn src.main:app
#   fastapi dev src.main:app
_SRC_DIR = os.path.dirname(__file__)
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from contextlib import asynccontextmanager

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.requests import Request
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from config import settings
from observability import get_logger, setup_logging
from core.security.rate_limit import enforce_global_rate_limit
from auth.router import router as auth_router
from files.router import router as files_router
from notebooks.router import router as notebooks_router
from notes.router import router as notes_router
from membership.router import router as membership_router
from workspaces.router import router as workspaces_router
from core.health import router as health_router
from ai_gateway.search import router as ai_search_router

logger = get_logger(__name__)

# Routers
def register_routes(app: FastAPI) -> None:
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(files_router, prefix="/files", tags=["files"])
    app.include_router(notebooks_router)
    app.include_router(notes_router)
    app.include_router(workspaces_router)
    app.include_router(membership_router)
    # --- AI Slice 2: internal search validation ---
    app.include_router(ai_search_router)
    # --- AI Slice 3: Chat MVP ---
    from ai_routes.chat import router as ai_chat_router
    app.include_router(ai_chat_router)
    # --- AI Slice 5: Thread management routes ---
    from ai_routes.threads import router as ai_threads_router
    app.include_router(ai_threads_router)
    # --- AI Slice 6: Agent routes ---
    from ai_routes.agent import router as ai_agent_router
    app.include_router(ai_agent_router)


# Middleware
def register_middlewares(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")


# Global exception handling
def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ):
        # In prod, log this to Sentry / Datadog
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error"},
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()

    from config import get_settings as _get_settings
    from shared.llm.env import configure_litellm_env

    _s = _get_settings()
    configure_litellm_env(_s)
    try:
        from shared.llm.fallback import resolve_llm_model

        resolved = await resolve_llm_model(timeout=12.0)
        if resolved:
            logger.info("LLM candidate ready", extra={"model": resolved})
        else:
            logger.warning("LLM candidate resolve skipped or failed — /ai/* may degrade")
    except Exception as e:
        logger.warning(
            "LLM candidate resolve failed — API continues",
            extra={"error": str(e)[:240]},
        )
    if _s.effective_arq_redis_url:
        app.state.arq_pool = await create_pool(
            RedisSettings.from_dsn(_s.effective_arq_redis_url)
        )
    else:
        app.state.arq_pool = None

    if _s.qdrant_enabled:
        try:
            from ai.retrieval.collection import (
                ensure_files_collection,
                ensure_notes_collection,
            )

            await ensure_notes_collection()
            await ensure_files_collection()
            logger.info("Qdrant collections ready")
        except Exception as e:
            logger.error(
                "Qdrant collection bootstrap failed — AI retrieval degraded",
                extra={"error": str(e)},
            )
            # Non-fatal: core API boots; /ai/* degrades when Qdrant unreachable
    # --- AI Slice 6: LangGraph checkpointer ---
    try:
        from ai.memory.checkpointer import init_checkpointer
        await init_checkpointer()
        logger.info("LangGraph checkpointer ready")
    except Exception as e:
        logger.error(
            "Checkpointer init failed — agent features degraded",
            extra={"error": str(e)},
        )
        # Non-fatal: /ai/chat continues working, /ai/agent degrades gracefully

    yield

    # --- AI Slice 1: ARQ pool cleanup ---
    if hasattr(app.state, "arq_pool") and app.state.arq_pool is not None:
        await app.state.arq_pool.close()

    from ai.retrieval.client import close_async_qdrant_client

    await close_async_qdrant_client()
    # --- AI Slice 6: LangGraph checkpointer cleanup ---
    try:
        from ai.memory.checkpointer import close_checkpointer
        await close_checkpointer()
    except Exception:
        pass


# App factory (important for testing & scalability)
def create_app() -> FastAPI:
    app = FastAPI(
        title="2nd Brain Backend",
        version="1.0.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
        dependencies=[Depends(enforce_global_rate_limit)],
        lifespan=lifespan,
    )

    register_middlewares(app)
    register_routes(app)
    register_exception_handlers(app)

    Instrumentator(
        should_group_status_codes=False,
        should_ignore_untemplated=True,
    ).instrument(
        app,
        metric_namespace="dashnote",
        metric_subsystem="api",
    ).expose(app, endpoint="/metrics")

    return app


app = create_app()