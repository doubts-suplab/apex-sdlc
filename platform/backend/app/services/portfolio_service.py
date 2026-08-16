from __future__ import annotations

import uuid

from sqlalchemy import Integer, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.delivery import DELIVERY_PRIORITIES, DELIVERY_STATUSES, Delivery
from app.models.project import Project
from app.schemas.portfolio import PortfolioProjectRow, PortfolioSummary

logger = get_logger(__name__)

# Deliveries still in flight — everything that is neither done nor dropped.
_OPEN_STATUSES = ("proposed", "planned", "in_progress")


class PortfolioService:
    """Aggregates deliveries across an organisation's projects into a portfolio rollup.

    Read-only: it never mutates deliveries, only summarises them. All queries are scoped to the
    organisation via a ``Delivery → Project`` join on ``organisation_id``, so one org never sees
    another's deliveries.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def summarise(self, organisation_id: uuid.UUID) -> PortfolioSummary:
        """Return the portfolio rollup for one organisation."""
        by_status = await self._counts_by(Delivery.status, organisation_id, DELIVERY_STATUSES)
        by_priority = await self._counts_by(
            Delivery.priority, organisation_id, DELIVERY_PRIORITIES
        )
        projects = await self._project_rows(organisation_id)

        delivery_count = sum(row.delivery_count for row in projects)
        total_estimate = sum(row.estimate_points for row in projects)
        open_count = sum(by_status[s] for s in _OPEN_STATUSES)

        logger.info(
            "portfolio.summarised",
            organisation_id=str(organisation_id),
            project_count=len(projects),
            delivery_count=delivery_count,
        )
        return PortfolioSummary(
            organisation_id=organisation_id,
            project_count=len(projects),
            delivery_count=delivery_count,
            open_count=open_count,
            total_estimate_points=total_estimate,
            by_status=by_status,
            by_priority=by_priority,
            projects=projects,
        )

    async def _counts_by(
        self, column, organisation_id: uuid.UUID, keys: tuple[str, ...]
    ) -> dict[str, int]:
        """Zero-filled grouped counts of the org's deliveries by the given delivery column."""
        result = await self._db.execute(
            select(column, func.count(Delivery.id))
            .join(Project, Delivery.project_id == Project.id)
            .where(Project.organisation_id == organisation_id)
            .group_by(column)
        )
        counts = {key: 0 for key in keys}
        for value, count in result.all():
            counts[value] = int(count)
        return counts

    async def _project_rows(self, organisation_id: uuid.UUID) -> list[PortfolioProjectRow]:
        """Per-project rollup, including projects that have no deliveries yet (outer join)."""
        open_estimate = func.coalesce(func.sum(Delivery.estimate_points), 0)
        open_flag = cast(Delivery.status.in_(_OPEN_STATUSES), Integer)
        result = await self._db.execute(
            select(
                Project.id,
                Project.name,
                Project.slug,
                Project.github_repo,
                func.count(Delivery.id).label("delivery_count"),
                open_estimate.label("estimate_points"),
                func.coalesce(func.sum(open_flag), 0).label("open_count"),
            )
            .outerjoin(Delivery, Delivery.project_id == Project.id)
            .where(Project.organisation_id == organisation_id)
            .group_by(Project.id, Project.name, Project.slug, Project.github_repo)
            .order_by(Project.name)
        )
        return [
            PortfolioProjectRow(
                project_id=row.id,
                name=row.name,
                slug=row.slug,
                github_repo=row.github_repo,
                delivery_count=int(row.delivery_count),
                estimate_points=int(row.estimate_points),
                open_count=int(row.open_count),
            )
            for row in result.all()
        ]
