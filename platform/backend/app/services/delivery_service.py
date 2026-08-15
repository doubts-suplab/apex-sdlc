from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.delivery import Delivery
from app.schemas.delivery import DeliveryCreate, DeliveryUpdate

logger = get_logger(__name__)


class DeliveryService:
    """Async CRUD service for project deliveries."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, project_id: uuid.UUID, payload: DeliveryCreate) -> Delivery:
        """Persist a new delivery under a project and return the ORM instance."""
        delivery = Delivery(
            project_id=project_id,
            title=payload.title,
            description=payload.description,
            status=payload.status,
            priority=payload.priority,
            estimate_points=payload.estimate_points,
            target_ref=payload.target_ref,
            source=payload.source,
        )
        self._db.add(delivery)
        await self._db.flush()
        await self._db.refresh(delivery)
        logger.info(
            "delivery.created",
            id=str(delivery.id),
            project_id=str(project_id),
            source=delivery.source,
        )
        return delivery

    async def get_for_project(
        self, project_id: uuid.UUID, delivery_id: uuid.UUID
    ) -> Delivery | None:
        """Return a delivery by id, scoped to its project, or None."""
        result = await self._db.execute(
            select(Delivery).where(
                Delivery.id == delivery_id, Delivery.project_id == project_id
            )
        )
        return result.scalar_one_or_none()

    async def list_for_project(
        self,
        project_id: uuid.UUID,
        limit: int = 20,
        after: str | None = None,
        status: str | None = None,
    ) -> tuple[list[Delivery], int]:
        """Return a filtered/paginated list of a project's deliveries and the total count."""
        base_q = (
            select(Delivery)
            .where(Delivery.project_id == project_id)
            .order_by(Delivery.created_at, Delivery.id)
        )
        count_q = (
            select(func.count())
            .select_from(Delivery)
            .where(Delivery.project_id == project_id)
        )

        if status is not None:
            base_q = base_q.where(Delivery.status == status)
            count_q = count_q.where(Delivery.status == status)

        if after:
            try:
                after_id = uuid.UUID(after)
                base_q = base_q.where(Delivery.id > after_id)
            except ValueError:
                pass

        count_result = await self._db.execute(count_q)
        total: int = count_result.scalar_one()

        result = await self._db.execute(base_q.limit(limit))
        items = list(result.scalars().all())
        return items, total

    async def update(self, delivery: Delivery, payload: DeliveryUpdate) -> Delivery:
        """Apply partial updates and persist."""
        update_data: dict[str, Any] = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(delivery, field, value)
        await self._db.flush()
        await self._db.refresh(delivery)
        logger.info("delivery.updated", id=str(delivery.id))
        return delivery

    async def delete(self, delivery: Delivery) -> None:
        """Hard-delete a delivery."""
        await self._db.delete(delivery)
        await self._db.flush()
        logger.info("delivery.deleted", id=str(delivery.id))
