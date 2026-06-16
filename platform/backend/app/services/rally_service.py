from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.integrations.rally.client import RallyClient
from app.models.integration import ProjectIntegration
from app.models.project import Project

logger = get_logger(__name__)


async def fetch_project_rally_metrics(
    db: AsyncSession,
    project: Project,
    rally_client: RallyClient,
) -> dict:
    """Fetch active iteration and story metrics from Rally for a project.

    Args:
        db: Async database session.
        project: The Project ORM instance to collect metrics for.
        rally_client: Authenticated Rally API client.

    Returns:
        Dict with keys:
        - ``project_ref``: Rally project ref used.
        - ``iteration``: Active iteration object (or ``None``).
        - ``total_stories``: Number of user stories in the active iteration.
        - ``story_statuses``: Dict mapping state name → count.
        - ``total_plan_estimate``: Sum of all PlanEstimate values.
        - ``completed_plan_estimate``: PlanEstimate in "Completed"/"Accepted" state.

    Raises:
        ValueError: If the project has no Rally integration configured.
        IntegrationError: If the Rally API call fails.
    """
    result = await db.execute(
        select(ProjectIntegration).where(
            ProjectIntegration.project_id == project.id,
            ProjectIntegration.integration_type == "rally",
            ProjectIntegration.enabled.is_(True),
        )
    )
    integration = result.scalar_one_or_none()

    if integration is None:
        raise ValueError(f"Project {project.id} has no Rally integration configured.")

    project_oid = integration.config.get("project_oid")
    if not project_oid:
        raise ValueError(
            f"Rally integration for project {project.id} is missing 'project_oid' in config."
        )

    project_ref = f"/project/{project_oid}"

    logger.info(
        "rally_service.fetch_metrics",
        project_id=str(project.id),
        project_ref=project_ref,
    )

    iteration = await rally_client.get_active_iteration(project_ref=project_ref)

    if iteration is None:
        logger.info("rally_service.no_active_iteration", project_id=str(project.id))
        return {
            "project_ref": project_ref,
            "iteration": None,
            "total_stories": 0,
            "story_statuses": {},
            "total_plan_estimate": 0.0,
            "completed_plan_estimate": 0.0,
        }

    iteration_ref = iteration.get("_ref", "")
    stories = await rally_client.get_user_stories(
        project_ref=project_ref,
        iteration_ref=iteration_ref,
    )

    story_statuses: dict[str, int] = {}
    total_pe = 0.0
    completed_pe = 0.0

    for story in stories:
        state = story.get("State", "Unknown")
        story_statuses[state] = story_statuses.get(state, 0) + 1

        pe = story.get("PlanEstimate") or 0.0
        total_pe += float(pe)
        if state.lower() in ("completed", "accepted"):
            completed_pe += float(pe)

    metrics = {
        "project_ref": project_ref,
        "iteration": {
            "ref": iteration_ref,
            "name": iteration.get("Name"),
            "state": iteration.get("State"),
            "start_date": iteration.get("StartDate"),
            "end_date": iteration.get("EndDate"),
            "planned_velocity": iteration.get("PlannedVelocity"),
        },
        "total_stories": len(stories),
        "story_statuses": story_statuses,
        "total_plan_estimate": total_pe,
        "completed_plan_estimate": completed_pe,
    }

    logger.info(
        "rally_service.metrics_fetched",
        project_id=str(project.id),
        iteration_name=iteration.get("Name"),
        total_stories=len(stories),
        total_pe=total_pe,
        completed_pe=completed_pe,
    )

    return metrics
