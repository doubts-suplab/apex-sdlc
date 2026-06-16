from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.organisation import Organisation
from app.schemas.organisation import OrganisationCreate, OrganisationUpdate

logger = get_logger(__name__)


class OrganisationService:
    """Async CRUD service for organisations."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, payload: OrganisationCreate) -> Organisation:
        """Persist a new organisation and return the ORM instance."""
        org = Organisation(
            name=payload.name,
            slug=payload.slug,
            description=payload.description,
        )
        self._db.add(org)
        await self._db.flush()
        await self._db.refresh(org)
        logger.info("organisation.created", id=str(org.id), slug=org.slug)
        return org

    async def get_by_id(self, org_id: uuid.UUID) -> Organisation | None:
        """Return an organisation by primary key, or None."""
        result = await self._db.execute(
            select(Organisation).where(Organisation.id == org_id)
        )
        return result.scalar_one_or_none()

    async def list_paginated(
        self,
        limit: int = 20,
        after: str | None = None,
    ) -> tuple[list[Organisation], int]:
        """Return a page of organisations and the total count."""
        base_q = select(Organisation).order_by(Organisation.created_at, Organisation.id)

        if after:
            try:
                after_id = uuid.UUID(after)
                base_q = base_q.where(Organisation.id > after_id)
            except ValueError:
                pass  # invalid cursor — ignore and return from start

        count_result = await self._db.execute(select(func.count()).select_from(Organisation))
        total: int = count_result.scalar_one()

        result = await self._db.execute(base_q.limit(limit))
        items = list(result.scalars().all())
        return items, total

    async def update(
        self, org: Organisation, payload: OrganisationUpdate
    ) -> Organisation:
        """Apply partial updates and persist."""
        update_data: dict[str, Any] = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(org, field, value)
        await self._db.flush()
        await self._db.refresh(org)
        logger.info("organisation.updated", id=str(org.id))
        return org

    async def delete(self, org: Organisation) -> None:
        """Hard-delete an organisation."""
        await self._db.delete(org)
        await self._db.flush()
        logger.info("organisation.deleted", id=str(org.id))
