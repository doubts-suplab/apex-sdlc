from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.integrations.github.client import GitHubClient
from app.models.integration import ProjectIntegration
from app.models.project import Project

logger = get_logger(__name__)

# PR label constants
_LABEL_AI_ASSISTED = "ai-assisted"
_LABEL_SECURITY = "security-review-needed"


async def fetch_project_github_metrics(
    db: AsyncSession,
    project: Project,
    github_client: GitHubClient,
) -> dict:
    """Fetch PR and commit metrics from GitHub for a project.

    Looks up the project's GitHub integration config to get the repository,
    then fetches the last 30 PRs and counts key metrics by label.

    Args:
        db: Async database session.
        project: The Project ORM instance to collect metrics for.
        github_client: Authenticated GitHub API client.

    Returns:
        Dict with keys:
        - ``repo``: Repository slug (owner/repo).
        - ``total_prs``: Total number of PRs fetched.
        - ``open_prs``: Number of open PRs.
        - ``ai_assisted_prs``: PRs labelled "ai-assisted".
        - ``security_flagged_prs``: PRs labelled "security-review-needed".
        - ``repo_stats``: Stars, forks, open issues, language, default_branch.

    Raises:
        ValueError: If the project has no GitHub integration configured.
        IntegrationError: If the GitHub API call fails.
    """
    # Fetch the integration config for this project
    result = await db.execute(
        select(ProjectIntegration).where(
            ProjectIntegration.project_id == project.id,
            ProjectIntegration.integration_type == "github",
            ProjectIntegration.enabled.is_(True),
        )
    )
    integration = result.scalar_one_or_none()

    if integration is None:
        # Fall back to project.github_repo for backward compatibility
        repo = project.github_repo
        if not repo:
            raise ValueError(
                f"Project {project.id} has no GitHub integration configured."
            )
    else:
        repo = integration.config.get("repo") or project.github_repo
        if not repo:
            raise ValueError(
                f"GitHub integration for project {project.id} is missing 'repo' in config."
            )

    logger.info("github_service.fetch_metrics", project_id=str(project.id), repo=repo)

    # Fetch up to 30 recent PRs (sorted by updated desc)
    prs = await github_client.get_prs(repo=repo, state="all", per_page=30)

    total_prs = len(prs)
    open_prs = 0
    ai_assisted = 0
    security_flagged = 0

    for pr in prs:
        if pr.get("state") == "open":
            open_prs += 1

        labels = [label.get("name", "") for label in pr.get("labels", [])]
        if _LABEL_AI_ASSISTED in labels:
            ai_assisted += 1
        if _LABEL_SECURITY in labels:
            security_flagged += 1

    # Fetch repo-level stats
    repo_stats = await github_client.get_repo_stats(repo=repo)

    metrics = {
        "repo": repo,
        "total_prs": total_prs,
        "open_prs": open_prs,
        "ai_assisted_prs": ai_assisted,
        "security_flagged_prs": security_flagged,
        "repo_stats": repo_stats,
    }

    logger.info(
        "github_service.metrics_fetched",
        project_id=str(project.id),
        repo=repo,
        total_prs=total_prs,
        ai_assisted=ai_assisted,
        security_flagged=security_flagged,
    )

    return metrics
