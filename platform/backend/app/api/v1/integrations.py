from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import get_db
from app.models.integration import ProjectIntegration
from app.models.project import Project
from app.schemas.integration import IntegrationCreate, IntegrationResponse, IntegrationUpdate

logger = get_logger(__name__)

router = APIRouter(
    prefix="/projects/{project_id}/integrations",
    tags=["integrations"],
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


async def _get_project_or_404(
    project_id: uuid.UUID,
    db: AsyncSession,
) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(
            status_code=404,
            detail={
                "type": "https://apex-sdlc/errors/project-not-found",
                "title": "Project Not Found",
                "status": 404,
                "detail": f"No project with id={project_id} exists.",
                "instance": f"/api/v1/projects/{project_id}",
            },
        )
    return project


async def _get_integration_or_404(
    project_id: uuid.UUID,
    integration_type: str,
    db: AsyncSession,
) -> ProjectIntegration:
    result = await db.execute(
        select(ProjectIntegration).where(
            ProjectIntegration.project_id == project_id,
            ProjectIntegration.integration_type == integration_type,
        )
    )
    integration = result.scalar_one_or_none()
    if integration is None:
        raise HTTPException(
            status_code=404,
            detail={
                "type": "https://apex-sdlc/errors/integration-not-found",
                "title": "Integration Not Found",
                "status": 404,
                "detail": (
                    f"No {integration_type!r} integration for project {project_id}."
                ),
                "instance": (
                    f"/api/v1/projects/{project_id}/integrations/{integration_type}"
                ),
            },
        )
    return integration


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post(
    "",
    status_code=201,
    response_model=IntegrationResponse,
    summary="Create a project integration",
)
async def create_integration(
    project_id: uuid.UUID,
    payload: IntegrationCreate,
    db: AsyncSession = Depends(get_db),
) -> IntegrationResponse:
    """Register a new external integration for a project.

    Returns 409 if an integration of the same type already exists.
    """
    await _get_project_or_404(project_id, db)

    # Check for duplicate
    existing = await db.execute(
        select(ProjectIntegration).where(
            ProjectIntegration.project_id == project_id,
            ProjectIntegration.integration_type == payload.integration_type,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=409,
            detail={
                "type": "https://apex-sdlc/errors/integration-conflict",
                "title": "Integration Already Exists",
                "status": 409,
                "detail": (
                    f"A {payload.integration_type!r} integration for project "
                    f"{project_id} already exists. Use PATCH to update it."
                ),
                "instance": f"/api/v1/projects/{project_id}/integrations",
            },
        )

    integration = ProjectIntegration(
        id=uuid.uuid4(),
        project_id=project_id,
        integration_type=payload.integration_type,
        config=payload.config,
        credentials_ref=payload.credentials_ref,
        enabled=payload.enabled,
    )
    db.add(integration)
    await db.commit()
    await db.refresh(integration)

    logger.info(
        "integration.created",
        project_id=str(project_id),
        integration_type=payload.integration_type,
        integration_id=str(integration.id),
    )

    return IntegrationResponse.model_validate(integration)


@router.get(
    "",
    response_model=list[IntegrationResponse],
    summary="List project integrations",
)
async def list_integrations(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[IntegrationResponse]:
    """Return all integrations configured for a project."""
    await _get_project_or_404(project_id, db)

    result = await db.execute(
        select(ProjectIntegration).where(ProjectIntegration.project_id == project_id)
    )
    integrations = result.scalars().all()
    return [IntegrationResponse.model_validate(i) for i in integrations]


@router.get(
    "/{integration_type}",
    response_model=IntegrationResponse,
    summary="Get a specific project integration",
)
async def get_integration(
    project_id: uuid.UUID,
    integration_type: str,
    db: AsyncSession = Depends(get_db),
) -> IntegrationResponse:
    """Return a single integration by type (github | jira | rally | confluence)."""
    await _get_project_or_404(project_id, db)
    integration = await _get_integration_or_404(project_id, integration_type, db)
    return IntegrationResponse.model_validate(integration)


@router.patch(
    "/{integration_type}",
    response_model=IntegrationResponse,
    summary="Update a project integration",
)
async def update_integration(
    project_id: uuid.UUID,
    integration_type: str,
    payload: IntegrationUpdate,
    db: AsyncSession = Depends(get_db),
) -> IntegrationResponse:
    """Partially update an existing integration's config or enabled state."""
    await _get_project_or_404(project_id, db)
    integration = await _get_integration_or_404(project_id, integration_type, db)

    update_data = payload.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(integration, field, value)

    await db.commit()
    await db.refresh(integration)

    logger.info(
        "integration.updated",
        project_id=str(project_id),
        integration_type=integration_type,
        fields=list(update_data.keys()),
    )

    return IntegrationResponse.model_validate(integration)


@router.delete(
    "/{integration_type}",
    status_code=204,
    summary="Delete a project integration",
)
async def delete_integration(
    project_id: uuid.UUID,
    integration_type: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete an integration. The project itself is unaffected."""
    await _get_project_or_404(project_id, db)
    integration = await _get_integration_or_404(project_id, integration_type, db)

    await db.delete(integration)
    await db.commit()

    logger.info(
        "integration.deleted",
        project_id=str(project_id),
        integration_type=integration_type,
    )


@router.post(
    "/{integration_type}/sync",
    status_code=202,
    response_model=dict[str, Any],
    summary="Trigger an on-demand integration sync",
)
async def sync_integration(
    project_id: uuid.UUID,
    integration_type: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Dispatch a background task to refresh data from the given integration.

    Returns 202 Accepted with the Celery task ID so the caller can poll status.
    """
    await _get_project_or_404(project_id, db)
    await _get_integration_or_404(project_id, integration_type, db)

    # Import tasks lazily to avoid circular imports at module load time
    from tasks.refresh_tasks import (
        refresh_github_data,
        refresh_jira_data,
        refresh_rally_data,
    )

    pid = str(project_id)

    task_map = {
        "github": refresh_github_data,
        "jira": refresh_jira_data,
        "rally": refresh_rally_data,
    }

    task_fn = task_map.get(integration_type)
    if task_fn is None:
        raise HTTPException(
            status_code=400,
            detail={
                "type": "https://apex-sdlc/errors/sync-not-supported",
                "title": "Sync Not Supported",
                "status": 400,
                "detail": (
                    f"On-demand sync is not available for {integration_type!r}. "
                    "Supported: github, jira, rally."
                ),
                "instance": (
                    f"/api/v1/projects/{project_id}/integrations/{integration_type}/sync"
                ),
            },
        )

    task = task_fn.delay(pid)

    logger.info(
        "integration.sync_dispatched",
        project_id=pid,
        integration_type=integration_type,
        task_id=task.id,
    )

    return {
        "task_id": task.id,
        "project_id": pid,
        "integration_type": integration_type,
        "status": "queued",
        "queued_at": datetime.now(timezone.utc).isoformat(),
    }
