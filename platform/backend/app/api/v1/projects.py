from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.logging import get_logger
from app.db.session import DbSession
from app.schemas.common import PaginatedResponse, ProblemDetail
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])
logger = get_logger(__name__)


def _get_service(db: DbSession) -> ProjectService:
    return ProjectService(db)


ProjService = Annotated[ProjectService, Depends(_get_service)]

_NOT_FOUND = ProblemDetail(
    type="https://apex.example.com/problems/not-found",
    title="Project Not Found",
    status=404,
    detail="The requested project does not exist.",
)


@router.post(
    "/",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create project",
)
async def create_project(
    payload: ProjectCreate,
    service: ProjService,
) -> ProjectResponse:
    """Create a new project within an organisation."""
    project = await service.create(payload)
    return ProjectResponse.model_validate(project)


@router.get(
    "/",
    response_model=PaginatedResponse[ProjectResponse],
    status_code=status.HTTP_200_OK,
    summary="List projects",
)
async def list_projects(
    service: ProjService,
    organisation_id: Annotated[uuid.UUID | None, Query(description="Filter by org")] = None,
    status_filter: Annotated[
        str | None, Query(alias="status", description="Filter by status")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    after: Annotated[str | None, Query(description="Cursor (UUID) for next page")] = None,
) -> PaginatedResponse[ProjectResponse]:
    """Return a cursor-paginated list of projects."""
    items, total = await service.list_paginated(
        limit=limit,
        after=after,
        organisation_id=organisation_id,
        status=status_filter,
    )
    response_items = [ProjectResponse.model_validate(p) for p in items]
    next_cursor = str(items[-1].id) if len(items) == limit else None
    return PaginatedResponse[ProjectResponse](
        items=response_items,
        total=total,
        limit=limit,
        next_cursor=next_cursor,
    )


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    responses={404: {"model": ProblemDetail}},
    summary="Get project",
)
async def get_project(
    project_id: uuid.UUID,
    service: ProjService,
) -> ProjectResponse:
    """Fetch a single project by ID."""
    from fastapi import HTTPException

    project = await service.get_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=_NOT_FOUND.model_dump())
    return ProjectResponse.model_validate(project)


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    responses={404: {"model": ProblemDetail}},
    summary="Update project",
)
async def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    service: ProjService,
) -> ProjectResponse:
    """Partially update a project."""
    from fastapi import HTTPException

    project = await service.get_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=_NOT_FOUND.model_dump())
    updated = await service.update(project, payload)
    return ProjectResponse.model_validate(updated)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ProblemDetail}},
    summary="Delete project",
)
async def delete_project(
    project_id: uuid.UUID,
    service: ProjService,
) -> None:
    """Hard-delete a project and its phases."""
    from fastapi import HTTPException

    project = await service.get_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=_NOT_FOUND.model_dump())
    await service.delete(project)
