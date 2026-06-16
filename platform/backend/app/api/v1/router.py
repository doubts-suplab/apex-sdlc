from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from sqlalchemy import text

from app.api.v1 import integrations, organisations, projects
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

api_router = APIRouter(prefix="/api/v1")

# Include sub-routers
api_router.include_router(organisations.router)
api_router.include_router(projects.router)
api_router.include_router(integrations.router)


@api_router.get(
    "/health",
    tags=["health"],
    summary="Health check",
    response_model=dict[str, str],
)
async def health_check() -> dict[str, Any]:
    """Return service health including DB connectivity status."""
    from app.db.session import get_engine

    settings = get_settings()
    db_status = "ok"

    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("health_check.db_error", error=str(exc))
        db_status = "error"

    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "db": db_status,
    }
