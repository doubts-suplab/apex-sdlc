from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from app.core.logging import get_logger
from tasks.celery_app import celery_app

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Per-project refresh tasks
# ---------------------------------------------------------------------------


@celery_app.task(name="tasks.refresh_github_data", bind=True, max_retries=3)
def refresh_github_data(self, project_id: str) -> dict:
    """Refresh GitHub metrics for a single project.

    Fetches PR counts, commit activity, and repo stats, then stores the
    result. Called by the beat schedule via ``refresh_all_projects``.

    Args:
        project_id: UUID string of the project to refresh.

    Returns:
        Dict with ``project_id``, ``status``, and ``metrics`` (or ``error``).
    """
    logger.info("refresh_github_data.start", project_id=project_id)

    try:
        result = asyncio.run(_refresh_github(project_id))
        logger.info(
            "refresh_github_data.done",
            project_id=project_id,
            repo=result.get("repo"),
        )
        return {"project_id": project_id, "status": "ok", "metrics": result}

    except Exception as exc:
        logger.error(
            "refresh_github_data.error",
            project_id=project_id,
            error=str(exc),
            exc_info=True,
        )
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


@celery_app.task(name="tasks.refresh_jira_data", bind=True, max_retries=3)
def refresh_jira_data(self, project_id: str) -> dict:
    """Refresh Jira sprint/story metrics for a single project.

    Args:
        project_id: UUID string of the project to refresh.

    Returns:
        Dict with ``project_id``, ``status``, and ``metrics`` (or ``error``).
    """
    logger.info("refresh_jira_data.start", project_id=project_id)

    try:
        result = asyncio.run(_refresh_jira(project_id))
        logger.info(
            "refresh_jira_data.done",
            project_id=project_id,
            sprint=result.get("sprint", {}).get("name") if result.get("sprint") else None,
        )
        return {"project_id": project_id, "status": "ok", "metrics": result}

    except Exception as exc:
        logger.error(
            "refresh_jira_data.error",
            project_id=project_id,
            error=str(exc),
            exc_info=True,
        )
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


@celery_app.task(name="tasks.refresh_rally_data", bind=True, max_retries=3)
def refresh_rally_data(self, project_id: str) -> dict:
    """Refresh Rally iteration/story metrics for a single project.

    Args:
        project_id: UUID string of the project to refresh.

    Returns:
        Dict with ``project_id``, ``status``, and ``metrics`` (or ``error``).
    """
    logger.info("refresh_rally_data.start", project_id=project_id)

    try:
        result = asyncio.run(_refresh_rally(project_id))
        logger.info(
            "refresh_rally_data.done",
            project_id=project_id,
            iteration=(
                result.get("iteration", {}).get("name") if result.get("iteration") else None
            ),
        )
        return {"project_id": project_id, "status": "ok", "metrics": result}

    except Exception as exc:
        logger.error(
            "refresh_rally_data.error",
            project_id=project_id,
            error=str(exc),
            exc_info=True,
        )
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


# ---------------------------------------------------------------------------
# Fan-out beat task
# ---------------------------------------------------------------------------


@celery_app.task(name="tasks.refresh_all_projects", bind=True)
def refresh_all_projects(self) -> None:
    """Beat task: refresh all enabled integrations for all active projects.

    Queries active projects and dispatches per-integration refresh tasks based
    on which integrations are enabled. Runs every 30 minutes via beat schedule.
    """
    logger.info("refresh_all_projects.start")

    try:
        asyncio.run(_dispatch_all_refresh_tasks())
    except Exception as exc:
        logger.error(
            "refresh_all_projects.error",
            error=str(exc),
            exc_info=True,
        )
        raise


# ---------------------------------------------------------------------------
# Async implementations (run inside asyncio.run() from Celery workers)
# ---------------------------------------------------------------------------


async def _refresh_github(project_id: str) -> dict:
    """Inner async implementation for GitHub refresh."""
    from app.core.config import get_settings
    from app.db.session import get_engine
    from app.integrations.github.client import GitHubClient
    from app.models.project import Project
    from app.services.github_service import fetch_project_github_metrics
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import select

    settings = get_settings()
    github_client = GitHubClient(token=settings.GITHUB_TOKEN)

    engine = get_engine()
    async with AsyncSession(engine) as session:
        result = await session.execute(
            select(Project).where(Project.id == project_id)  # type: ignore[arg-type]
        )
        project = result.scalar_one_or_none()
        if project is None:
            raise ValueError(f"Project {project_id} not found")

        metrics = await fetch_project_github_metrics(
            db=session,
            project=project,
            github_client=github_client,
        )

        # Update last_synced_at on the GitHub integration record
        from app.models.integration import ProjectIntegration

        int_result = await session.execute(
            select(ProjectIntegration).where(
                ProjectIntegration.project_id == project.id,
                ProjectIntegration.integration_type == "github",
            )
        )
        integration = int_result.scalar_one_or_none()
        if integration:
            integration.last_synced_at = datetime.now(timezone.utc)
            await session.commit()

    return metrics


async def _refresh_jira(project_id: str) -> dict:
    """Inner async implementation for Jira refresh."""
    from app.core.config import get_settings
    from app.db.session import get_engine
    from app.integrations.jira.client import JiraClient
    from app.models.integration import ProjectIntegration
    from app.models.project import Project
    from app.services.jira_service import fetch_project_jira_metrics
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import select

    settings = get_settings()
    jira_client = JiraClient(
        base_url=settings.JIRA_BASE_URL,
        email=settings.JIRA_EMAIL,
        api_token=settings.JIRA_API_TOKEN,
    )

    engine = get_engine()
    async with AsyncSession(engine) as session:
        result = await session.execute(
            select(Project).where(Project.id == project_id)  # type: ignore[arg-type]
        )
        project = result.scalar_one_or_none()
        if project is None:
            raise ValueError(f"Project {project_id} not found")

        metrics = await fetch_project_jira_metrics(
            db=session,
            project=project,
            jira_client=jira_client,
        )

        int_result = await session.execute(
            select(ProjectIntegration).where(
                ProjectIntegration.project_id == project.id,
                ProjectIntegration.integration_type == "jira",
            )
        )
        integration = int_result.scalar_one_or_none()
        if integration:
            integration.last_synced_at = datetime.now(timezone.utc)
            await session.commit()

    return metrics


async def _refresh_rally(project_id: str) -> dict:
    """Inner async implementation for Rally refresh."""
    from app.core.config import get_settings
    from app.db.session import get_engine
    from app.integrations.rally.client import RallyClient
    from app.models.integration import ProjectIntegration
    from app.models.project import Project
    from app.services.rally_service import fetch_project_rally_metrics
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import select

    settings = get_settings()
    rally_client = RallyClient(
        api_key=settings.RALLY_API_KEY,
        base_url=settings.RALLY_BASE_URL,
        workspace_oid=settings.RALLY_WORKSPACE_OID,
    )

    engine = get_engine()
    async with AsyncSession(engine) as session:
        result = await session.execute(
            select(Project).where(Project.id == project_id)  # type: ignore[arg-type]
        )
        project = result.scalar_one_or_none()
        if project is None:
            raise ValueError(f"Project {project_id} not found")

        metrics = await fetch_project_rally_metrics(
            db=session,
            project=project,
            rally_client=rally_client,
        )

        int_result = await session.execute(
            select(ProjectIntegration).where(
                ProjectIntegration.project_id == project.id,
                ProjectIntegration.integration_type == "rally",
            )
        )
        integration = int_result.scalar_one_or_none()
        if integration:
            integration.last_synced_at = datetime.now(timezone.utc)
            await session.commit()

    return metrics


async def _dispatch_all_refresh_tasks() -> None:
    """Query all active projects and dispatch appropriate refresh tasks."""
    from app.db.session import get_engine
    from app.models.integration import ProjectIntegration
    from app.models.project import Project
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    engine = get_engine()
    async with AsyncSession(engine) as session:
        result = await session.execute(
            select(Project)
            .where(Project.status == "active")
            .options(selectinload(Project.integrations))
        )
        projects = result.scalars().all()

    dispatched = 0
    for project in projects:
        for integration in project.integrations:
            if not integration.enabled:
                continue

            itype = integration.integration_type
            pid = str(project.id)

            if itype == "github":
                refresh_github_data.delay(pid)
                dispatched += 1
            elif itype == "jira":
                refresh_jira_data.delay(pid)
                dispatched += 1
            elif itype == "rally":
                refresh_rally_data.delay(pid)
                dispatched += 1
            # Confluence does not have a periodic refresh task (written on demand)

    logger.info(
        "refresh_all_projects.dispatched",
        project_count=len(projects),
        task_count=dispatched,
    )
