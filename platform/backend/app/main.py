from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.session import init_engine
from app.middleware.correlation import CorrelationMiddleware

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup / shutdown lifecycle."""
    settings = get_settings()
    configure_logging(settings.LOG_LEVEL)
    init_engine(settings)
    logger.info(
        "apex_platform.startup",
        environment=settings.ENVIRONMENT,
        version=settings.APP_VERSION,
    )
    yield
    logger.info("apex_platform.shutdown")


def create_app() -> FastAPI:
    """Factory function that creates and configures the FastAPI application."""
    application = FastAPI(
        title="APEX SDLC Platform",
        description="Enterprise AI-powered SDLC operating system",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # --- Middleware (order matters: outermost = first to process request) ---
    application.add_middleware(CorrelationMiddleware)

    # --- Exception handlers ---
    @application.exception_handler(404)
    async def not_found_handler(request: Request, exc: Any) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={
                "type": "about:blank",
                "title": "Not Found",
                "status": 404,
                "detail": str(exc.detail) if hasattr(exc, "detail") else "Resource not found",
            },
        )

    @application.exception_handler(422)
    async def validation_exception_handler(request: Request, exc: Any) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "type": "https://apex.example.com/problems/validation-error",
                "title": "Validation Error",
                "status": 422,
                "detail": exc.errors() if hasattr(exc, "errors") else str(exc),
            },
        )

    @application.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
        logger.warning("db.integrity_error", detail=str(exc.orig))
        return JSONResponse(
            status_code=409,
            content={
                "type": "https://apex.example.com/problems/conflict",
                "title": "Conflict",
                "status": 409,
                "detail": "A resource with the same unique identifier already exists.",
            },
        )

    # --- Routers ---
    application.include_router(api_router)

    # Root health alias (no prefix)
    @application.get("/health", tags=["health"], include_in_schema=False)
    async def root_health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
