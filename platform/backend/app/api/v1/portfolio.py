from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.core.logging import get_logger
from app.db.session import DbSession
from app.schemas.common import ProblemDetail
from app.schemas.portfolio import PortfolioSummary
from app.services.organisation_service import OrganisationService
from app.services.portfolio_service import PortfolioService

router = APIRouter(prefix="/organisations/{organisation_id}", tags=["portfolio"])
logger = get_logger(__name__)


def _get_portfolio_service(db: DbSession) -> PortfolioService:
    return PortfolioService(db)


def _get_organisation_service(db: DbSession) -> OrganisationService:
    return OrganisationService(db)


PortfolioSvc = Annotated[PortfolioService, Depends(_get_portfolio_service)]
OrgSvc = Annotated[OrganisationService, Depends(_get_organisation_service)]

_ORG_NOT_FOUND = ProblemDetail(
    type="https://apex.example.com/problems/not-found",
    title="Organisation Not Found",
    status=404,
    detail="The requested organisation does not exist.",
)


@router.get(
    "/portfolio",
    response_model=PortfolioSummary,
    responses={404: {"model": ProblemDetail}},
    summary="Cross-project delivery rollup for an organisation",
)
async def get_portfolio(
    organisation_id: uuid.UUID,
    service: PortfolioSvc,
    organisations: OrgSvc,
) -> PortfolioSummary:
    """Aggregate every delivery across the organisation's projects into a portfolio view.

    Returns totals (counts by status and priority, open count, total estimate points) plus a
    per-project breakdown — the ecosystem-wide planning picture, not one project at a time.
    """
    if await organisations.get_by_id(organisation_id) is None:
        raise HTTPException(status_code=404, detail=_ORG_NOT_FOUND.model_dump())
    return await service.summarise(organisation_id)
