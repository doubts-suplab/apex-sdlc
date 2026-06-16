from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.integrations.jira.client import JiraClient
from app.models.integration import ProjectIntegration
from app.models.project import Project

logger = get_logger(__name__)

_STORY_POINTS_FIELD = "customfield_10016"


async def fetch_project_jira_metrics(
    db: AsyncSession,
    project: Project,
    jira_client: JiraClient,
) -> dict:
    """Fetch active sprint and story metrics from Jira for a project.

    Args:
        db: Async database session.
        project: The Project ORM instance to collect metrics for.
        jira_client: Authenticated Jira API client.

    Returns:
        Dict with keys:
        - ``board_id``: Jira board ID used.
        - ``sprint``: Active sprint object (or ``None``).
        - ``total_stories``: Number of stories in the active sprint.
        - ``story_statuses``: Dict mapping status name → count.
        - ``total_story_points``: Sum of all story point values.
        - ``completed_story_points``: Story points in "Done" status.

    Raises:
        ValueError: If the project has no Jira board configured.
        IntegrationError: If the Jira API call fails.
    """
    # Fetch the integration config
    result = await db.execute(
        select(ProjectIntegration).where(
            ProjectIntegration.project_id == project.id,
            ProjectIntegration.integration_type == "jira",
            ProjectIntegration.enabled.is_(True),
        )
    )
    integration = result.scalar_one_or_none()

    if integration is None:
        board_id = project.jira_board_id
        if not board_id:
            raise ValueError(
                f"Project {project.id} has no Jira integration configured."
            )
    else:
        board_id = integration.config.get("board_id") or project.jira_board_id
        if not board_id:
            raise ValueError(
                f"Jira integration for project {project.id} is missing 'board_id' in config."
            )

    logger.info("jira_service.fetch_metrics", project_id=str(project.id), board_id=board_id)

    sprint = await jira_client.get_active_sprint(board_id=board_id)

    if sprint is None:
        logger.info("jira_service.no_active_sprint", project_id=str(project.id))
        return {
            "board_id": board_id,
            "sprint": None,
            "total_stories": 0,
            "story_statuses": {},
            "total_story_points": 0.0,
            "completed_story_points": 0.0,
        }

    sprint_id = str(sprint["id"])
    issues = await jira_client.get_sprint_issues(sprint_id=sprint_id)

    story_statuses: dict[str, int] = {}
    total_sp = 0.0
    completed_sp = 0.0

    for issue in issues:
        fields = issue.get("fields", {})
        status_name = fields.get("status", {}).get("name", "Unknown")
        story_statuses[status_name] = story_statuses.get(status_name, 0) + 1

        sp = fields.get(_STORY_POINTS_FIELD) or 0.0
        total_sp += float(sp)
        if status_name.lower() in ("done", "closed", "resolved"):
            completed_sp += float(sp)

    metrics = {
        "board_id": board_id,
        "sprint": {
            "id": sprint.get("id"),
            "name": sprint.get("name"),
            "state": sprint.get("state"),
            "start_date": sprint.get("startDate"),
            "end_date": sprint.get("endDate"),
            "goal": sprint.get("goal"),
        },
        "total_stories": len(issues),
        "story_statuses": story_statuses,
        "total_story_points": total_sp,
        "completed_story_points": completed_sp,
    }

    logger.info(
        "jira_service.metrics_fetched",
        project_id=str(project.id),
        sprint_name=sprint.get("name"),
        total_stories=len(issues),
        total_sp=total_sp,
        completed_sp=completed_sp,
    )

    return metrics
