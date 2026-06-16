from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.integrations.confluence.client import ConfluenceClient
from app.models.integration import ProjectIntegration
from app.models.project import Project

logger = get_logger(__name__)


async def list_project_pages(
    db: AsyncSession,
    project: Project,
    confluence_client: ConfluenceClient,
    limit: int = 25,
) -> list[dict]:
    """List Confluence pages in a project's configured space.

    Args:
        db: Async database session.
        project: The Project ORM instance.
        confluence_client: Authenticated Confluence client.
        limit: Maximum number of pages to return.

    Returns:
        List of Confluence page dicts (``id``, ``title``, ``version``).

    Raises:
        ValueError: If the project has no Confluence integration configured.
        IntegrationError: If the Confluence API call fails.
    """
    space_key = await _resolve_space_key(db, project)

    logger.info(
        "confluence_service.list_pages",
        project_id=str(project.id),
        space_key=space_key,
    )

    return await confluence_client.get_space_pages(space_key=space_key, limit=limit)


async def create_artifact_page(
    db: AsyncSession,
    project: Project,
    confluence_client: ConfluenceClient,
    title: str,
    body_html: str,
    parent_id: str | None = None,
) -> dict:
    """Create an artifact page in the project's Confluence space.

    Args:
        db: Async database session.
        project: The Project ORM instance.
        confluence_client: Authenticated Confluence client.
        title: Page title (must be unique within the space).
        body_html: Page body in Confluence storage format (XHTML).
        parent_id: Optional parent page ID.

    Returns:
        Created Confluence page object.

    Raises:
        ValueError: If the project has no Confluence integration configured.
        IntegrationError: If the Confluence API call fails.
    """
    space_key = await _resolve_space_key(db, project)

    logger.info(
        "confluence_service.create_page",
        project_id=str(project.id),
        space_key=space_key,
        title=title,
    )

    page = await confluence_client.create_page(
        space_key=space_key,
        title=title,
        body_html=body_html,
        parent_id=parent_id,
    )

    logger.info(
        "confluence_service.page_created",
        project_id=str(project.id),
        page_id=page.get("id"),
        title=title,
    )

    return page


async def update_artifact_page(
    db: AsyncSession,
    project: Project,
    confluence_client: ConfluenceClient,
    page_id: str,
    title: str,
    body_html: str,
) -> dict:
    """Update an existing artifact page in Confluence.

    Fetches the current page version first, then increments it.

    Args:
        db: Async database session (used only for validation).
        project: The Project ORM instance.
        confluence_client: Authenticated Confluence client.
        page_id: Numeric Confluence page ID.
        title: Page title.
        body_html: New page body in Confluence storage format.

    Returns:
        Updated Confluence page object.

    Raises:
        IntegrationError: If the Confluence API call fails.
    """
    # Fetch current version
    current = await confluence_client.get_page(page_id=page_id)
    current_version = current.get("version", {}).get("number", 0)

    logger.info(
        "confluence_service.update_page",
        project_id=str(project.id),
        page_id=page_id,
        current_version=current_version,
    )

    return await confluence_client.update_page(
        page_id=page_id,
        title=title,
        body_html=body_html,
        version=current_version,
    )


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


async def _resolve_space_key(db: AsyncSession, project: Project) -> str:
    """Return the Confluence space key for a project.

    Checks the integration config first, then falls back to
    ``project.confluence_space_key``.

    Raises:
        ValueError: If no space key can be resolved.
    """
    result = await db.execute(
        select(ProjectIntegration).where(
            ProjectIntegration.project_id == project.id,
            ProjectIntegration.integration_type == "confluence",
            ProjectIntegration.enabled.is_(True),
        )
    )
    integration = result.scalar_one_or_none()

    if integration is not None:
        space_key = integration.config.get("space_key") or project.confluence_space_key
    else:
        space_key = project.confluence_space_key

    if not space_key:
        raise ValueError(
            f"Project {project.id} has no Confluence space key configured."
        )

    return space_key
