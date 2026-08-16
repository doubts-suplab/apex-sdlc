from __future__ import annotations

from app.core.logging import get_logger
from app.integrations.github.client import GitHubClient
from app.models.delivery import Delivery
from app.models.project import Project

logger = get_logger(__name__)

_ISSUE_LABEL = "apex-delivery"


class DeliveryPublishError(Exception):
    """Raised when a delivery cannot be published (no repo, or already published)."""


class DeliveryPublishService:
    """Publishes a planned delivery to GitHub as a tracking issue — the write-back seam.

    Turns an apex-planned delivery into a real GitHub issue on the project's repository and records
    the issue URL back on the delivery (``target_ref``), advancing it to ``planned``. The GitHub
    client is injected so tests exercise the flow with a fake (no network).
    """

    def __init__(self, db, github_client: GitHubClient) -> None:
        self._db = db
        self._github = github_client

    async def publish(self, project: Project, delivery: Delivery) -> tuple[Delivery, dict]:
        """Create a GitHub issue for the delivery and mark it planned. Returns (delivery, issue)."""
        repo = project.github_repo
        if not repo:
            raise DeliveryPublishError(
                f"Project {project.id} has no github_repo configured; cannot publish."
            )
        if delivery.target_ref:
            raise DeliveryPublishError(
                f"Delivery {delivery.id} is already published to {delivery.target_ref}."
            )

        issue = await self._github.create_issue(
            repo=repo,
            title=delivery.title,
            body=self._issue_body(delivery),
            labels=[_ISSUE_LABEL],
        )
        issue_url = issue.get("html_url", "")
        delivery.target_ref = issue_url
        delivery.status = "planned"
        await self._db.flush()
        await self._db.refresh(delivery)

        logger.info(
            "delivery.published",
            delivery_id=str(delivery.id),
            repo=repo,
            issue_number=issue.get("number"),
        )
        return delivery, issue

    @staticmethod
    def _issue_body(delivery: Delivery) -> str:
        lines = [
            delivery.description or "_Planned via APEX delivery planning._",
            "",
            f"- **Priority:** {delivery.priority}",
            f"- **Estimate:** {delivery.estimate_points if delivery.estimate_points is not None else 'unsized'}",
            f"- **Source:** {delivery.source}",
            f"- **APEX delivery id:** `{delivery.id}`",
        ]
        return "\n".join(lines)
