from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from fastapi.responses import JSONResponse

from app.api.deps import get_github_client
from app.core.logging import get_logger
from app.db.session import DbSession
from app.integrations.github.client import GitHubClient
from app.schemas.common import PaginatedResponse, ProblemDetail
from app.schemas.delivery import (
    DeliveryCreate,
    DeliveryPublishResponse,
    DeliveryResponse,
    DeliveryUpdate,
)
from app.services.delivery_publish_service import (
    DeliveryPublishError,
    DeliveryPublishService,
)
from app.services.delivery_service import DeliveryService
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects/{project_id}/deliveries", tags=["deliveries"])
logger = get_logger(__name__)


def _get_delivery_service(db: DbSession) -> DeliveryService:
    return DeliveryService(db)


def _get_project_service(db: DbSession) -> ProjectService:
    return ProjectService(db)


DelService = Annotated[DeliveryService, Depends(_get_delivery_service)]
ProjService = Annotated[ProjectService, Depends(_get_project_service)]
GitHubDep = Annotated[GitHubClient, Depends(get_github_client)]

_PROJECT_NOT_FOUND = ProblemDetail(
    type="https://apex.example.com/problems/not-found",
    title="Project Not Found",
    status=404,
    detail="The requested project does not exist.",
)
_DELIVERY_NOT_FOUND = ProblemDetail(
    type="https://apex.example.com/problems/not-found",
    title="Delivery Not Found",
    status=404,
    detail="The requested delivery does not exist for this project.",
)


async def _require_project(projects: ProjectService, project_id: uuid.UUID) -> None:
    if await projects.get_by_id(project_id) is None:
        raise HTTPException(status_code=404, detail=_PROJECT_NOT_FOUND.model_dump())


@router.post(
    "/",
    response_model=DeliveryResponse,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": ProblemDetail}},
    summary="Create delivery",
)
async def create_delivery(
    project_id: uuid.UUID,
    payload: DeliveryCreate,
    service: DelService,
    projects: ProjService,
) -> DeliveryResponse:
    """Create a delivery under a project."""
    await _require_project(projects, project_id)
    delivery = await service.create(project_id, payload)
    return DeliveryResponse.model_validate(delivery)


@router.get(
    "/",
    response_model=PaginatedResponse[DeliveryResponse],
    responses={404: {"model": ProblemDetail}},
    summary="List a project's deliveries",
)
async def list_deliveries(
    project_id: uuid.UUID,
    service: DelService,
    projects: ProjService,
    status_filter: Annotated[
        str | None, Query(alias="status", description="Filter by delivery status")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    after: Annotated[str | None, Query(description="Cursor (UUID) for next page")] = None,
) -> PaginatedResponse[DeliveryResponse]:
    """Return a cursor-paginated list of a project's deliveries."""
    await _require_project(projects, project_id)
    items, total = await service.list_for_project(
        project_id, limit=limit, after=after, status=status_filter
    )
    response_items = [DeliveryResponse.model_validate(d) for d in items]
    next_cursor = str(items[-1].id) if len(items) == limit else None
    return PaginatedResponse[DeliveryResponse](
        items=response_items,
        total=total,
        limit=limit,
        next_cursor=next_cursor,
    )


@router.get(
    "/{delivery_id}",
    response_model=DeliveryResponse,
    responses={404: {"model": ProblemDetail}},
    summary="Get a delivery",
)
async def get_delivery(
    project_id: uuid.UUID,
    delivery_id: uuid.UUID,
    service: DelService,
) -> DeliveryResponse:
    """Fetch a single delivery scoped to its project."""
    delivery = await service.get_for_project(project_id, delivery_id)
    if delivery is None:
        raise HTTPException(status_code=404, detail=_DELIVERY_NOT_FOUND.model_dump())
    return DeliveryResponse.model_validate(delivery)


@router.patch(
    "/{delivery_id}",
    response_model=DeliveryResponse,
    responses={404: {"model": ProblemDetail}},
    summary="Update a delivery",
)
async def update_delivery(
    project_id: uuid.UUID,
    delivery_id: uuid.UUID,
    payload: DeliveryUpdate,
    service: DelService,
) -> DeliveryResponse:
    """Partially update a delivery."""
    delivery = await service.get_for_project(project_id, delivery_id)
    if delivery is None:
        raise HTTPException(status_code=404, detail=_DELIVERY_NOT_FOUND.model_dump())
    updated = await service.update(delivery, payload)
    return DeliveryResponse.model_validate(updated)


@router.post(
    "/{delivery_id}/publish",
    response_model=DeliveryPublishResponse,
    responses={404: {"model": ProblemDetail}, 409: {"model": ProblemDetail}},
    summary="Publish a delivery to GitHub as a tracking issue",
)
async def publish_delivery(
    project_id: uuid.UUID,
    delivery_id: uuid.UUID,
    service: DelService,
    projects: ProjService,
    db: DbSession,
    github: GitHubDep,
) -> DeliveryPublishResponse:
    """Create a GitHub issue for the delivery and mark it ``planned`` (the write-back seam).

    Records the created issue's URL on the delivery's ``target_ref``. Fails with ``409`` when the
    project has no repository configured or the delivery is already published.
    """
    project = await projects.get_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=_PROJECT_NOT_FOUND.model_dump())
    delivery = await service.get_for_project(project_id, delivery_id)
    if delivery is None:
        raise HTTPException(status_code=404, detail=_DELIVERY_NOT_FOUND.model_dump())

    publisher = DeliveryPublishService(db, github)
    try:
        published, issue = await publisher.publish(project, delivery)
    except DeliveryPublishError as exc:
        # Return the RFC-7807 body at top level (no generic HTTPException flattener for 409).
        return JSONResponse(
            status_code=409,
            content=ProblemDetail(
                type="https://apex.example.com/problems/conflict",
                title="Delivery Cannot Be Published",
                status=409,
                detail=str(exc),
            ).model_dump(),
        )

    return DeliveryPublishResponse(
        delivery=DeliveryResponse.model_validate(published),
        issue_url=issue.get("html_url", ""),
        issue_number=issue.get("number"),
    )


@router.delete(
    "/{delivery_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ProblemDetail}},
    summary="Delete a delivery",
)
async def delete_delivery(
    project_id: uuid.UUID,
    delivery_id: uuid.UUID,
    service: DelService,
) -> None:
    """Hard-delete a delivery."""
    delivery = await service.get_for_project(project_id, delivery_id)
    if delivery is None:
        raise HTTPException(status_code=404, detail=_DELIVERY_NOT_FOUND.model_dump())
    await service.delete(delivery)
