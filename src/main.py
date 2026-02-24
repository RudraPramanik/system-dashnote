from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.requests import Request

from config import settings
from auth.router import router as auth_router
from notebooks.router import router as notebooks_router


# Routers
def register_routes(app: FastAPI) -> None:
    app.include_router(auth_router)
    app.include_router(notebooks_router)

    @app.get("/health", tags=["health"])
    async def health_check():
        return {"status": "ok"}
    @app.get("/",tags=["base"])
    async def base():
        return {"status": "base"}


# Middleware
def register_middlewares(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


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


# App factory (important for testing & scalability)
def create_app() -> FastAPI:
    app = FastAPI(
        title="2nd Brain Backend",
        version="1.0.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
    )

    register_middlewares(app)
    register_routes(app)
    register_exception_handlers(app)

    return app


app = create_app()