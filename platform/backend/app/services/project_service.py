from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate

logger = get_logger(__name__)


class ProjectService:
    """Async CRUD service for projects."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, payload: ProjectCreate) -> Project:
        """Persist a new project and return the ORM instance."""
        project = Project(
            organisation_id=payload.organisation_id,
            name=payload.name,
            slug=payload.slug,
            description=payload.description,
            project_type=payload.project_type,
            github_repo=payload.github_repo,
            jira_board_id=payload.jira_board_id,
            confluence_space_key=payload.confluence_space_key,
            current_phase=payload.current_phase,
            status=payload.status,
        )
        self._db.add(project)
        await self._db.flush()
        await self._db.refresh(project)
        logger.info(
            "project.created",
            id=str(project.id),
            org_id=str(project.organisation_id),
        )
        return project

    async def get_by_id(self, project_id: uuid.UUID) -> Project | None:
        """Return a project by primary key, or None."""
        result = await self._db.execute(
            select(Project).where(Project.id == project_id)
        )
        return result.scalar_one_or_none()

    async def list_paginated(
        self,
        limit: int = 20,
        after: str | None = None,
        organisation_id: uuid.UUID | None = None,
        status: str | None = None,
    ) -> tuple[list[Project], int]:
        """Return a filtered/paginated list of projects and the total count."""
        base_q = select(Project).order_by(Project.created_at, Project.id)
        count_q = select(func.count()).select_from(Project)

        if organisation_id is not None:
            base_q = base_q.where(Project.organisation_id == organisation_id)
            count_q = count_q.where(Project.organisation_id == organisation_id)

        if status is not None:
            base_q = base_q.where(Project.status == status)
            count_q = count_q.where(Project.status == status)

        if after:
            try:
                after_id = uuid.UUID(after)
                base_q = base_q.where(Project.id > after_id)
            except ValueError:
                pass

        count_result = await self._db.execute(count_q)
        total: int = count_result.scalar_one()

        result = await self._db.execute(base_q.limit(limit))
        items = list(result.scalars().all())
        return items, total

    async def update(self, project: Project, payload: ProjectUpdate) -> Project:
        """Apply partial updates and persist."""
        update_data: dict[str, Any] = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(project, field, value)
        await self._db.flush()
        await self._db.refresh(project)
        logger.info("project.updated", id=str(project.id))
        return project

    async def delete(self, project: Project) -> None:
        """Hard-delete a project."""
        await self._db.delete(project)
        await self._db.flush()
        logger.info("project.deleted", id=str(project.id))
