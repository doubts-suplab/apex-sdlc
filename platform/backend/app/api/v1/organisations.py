from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.logging import get_logger
from app.db.session import DbSession
from app.schemas.common import PaginatedResponse, ProblemDetail
from app.schemas.organisation import OrganisationCreate, OrganisationResponse, OrganisationUpdate
from app.services.organisation_service import OrganisationService

router = APIRouter(prefix="/organisations", tags=["organisations"])
logger = get_logger(__name__)


def _get_service(db: DbSession) -> OrganisationService:
    return OrganisationService(db)


OrgService = Annotated[OrganisationService, Depends(_get_service)]

_NOT_FOUND = ProblemDetail(
    type="https://apex.example.com/problems/not-found",
    title="Organisation Not Found",
    status=404,
    detail="The requested organisation does not exist.",
)


@router.post(
    "/",
    response_model=OrganisationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create organisation",
)
async def create_organisation(
    payload: OrganisationCreate,
    service: OrgService,
) -> OrganisationResponse:
    """Create a new top-level organisation."""
    org = await service.create(payload)
    return OrganisationResponse.model_validate(org)


@router.get(
    "/",
    response_model=PaginatedResponse[OrganisationResponse],
    status_code=status.HTTP_200_OK,
    summary="List organisations",
)
async def list_organisations(
    service: OrgService,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    after: Annotated[str | None, Query(description="Cursor (UUID) for next page")] = None,
) -> PaginatedResponse[OrganisationResponse]:
    """Return a cursor-paginated list of organisations."""
    items, total = await service.list_paginated(limit=limit, after=after)
    response_items = [OrganisationResponse.model_validate(o) for o in items]
    next_cursor = str(items[-1].id) if len(items) == limit else None
    return PaginatedResponse[OrganisationResponse](
        items=response_items,
        total=total,
        limit=limit,
        next_cursor=next_cursor,
    )


@router.get(
    "/{org_id}",
    response_model=OrganisationResponse,
    responses={404: {"model": ProblemDetail}},
    summary="Get organisation",
)
async def get_organisation(
    org_id: uuid.UUID,
    service: OrgService,
) -> OrganisationResponse:
    """Fetch a single organisation by ID."""
    from fastapi import HTTPException

    org = await service.get_by_id(org_id)
    if org is None:
        raise HTTPException(status_code=404, detail=_NOT_FOUND.model_dump())
    return OrganisationResponse.model_validate(org)


@router.patch(
    "/{org_id}",
    response_model=OrganisationResponse,
    responses={404: {"model": ProblemDetail}},
    summary="Update organisation",
)
async def update_organisation(
    org_id: uuid.UUID,
    payload: OrganisationUpdate,
    service: OrgService,
) -> OrganisationResponse:
    """Partially update an organisation."""
    from fastapi import HTTPException

    org = await service.get_by_id(org_id)
    if org is None:
        raise HTTPException(status_code=404, detail=_NOT_FOUND.model_dump())
    updated = await service.update(org, payload)
    return OrganisationResponse.model_validate(updated)


@router.delete(
    "/{org_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ProblemDetail}},
    summary="Delete organisation",
)
async def delete_organisation(
    org_id: uuid.UUID,
    service: OrgService,
) -> None:
    """Hard-delete an organisation and all its projects."""
    from fastapi import HTTPException

    org = await service.get_by_id(org_id)
    if org is None:
        raise HTTPException(status_code=404, detail=_NOT_FOUND.model_dump())
    await service.delete(org)
