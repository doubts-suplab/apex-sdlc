from __future__ import annotations

from app.agents.tools.retry import retry_async
from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.integrations.github.client import GitHubClient
from app.models.audit import AuditLog
from app.models.delivery import Delivery
from app.models.project import Project

logger = get_logger(__name__)

_ISSUE_LABEL = "apex-delivery"


class DeliveryPublishError(Exception):
    """Raised when a delivery cannot be published (no repo, or already published)."""


class DeliveryPublishService:
    """Publishes a planned delivery to GitHub as a tracking issue — the governed write-back seam.

    Turns an apex-planned delivery into a real GitHub issue on the project's repository and records
    the issue URL back on the delivery (``target_ref``), advancing it to ``planned``. The GitHub call
    runs under retry+backoff (matching the live tool adapters), and every successful publish writes an
    append-only ``audit_log`` entry — so a real write-back is resilient and fully accountable. The
    GitHub client is injected so tests exercise the flow with a fake (no network).
    """

    def __init__(
        self,
        db,
        github_client: GitHubClient,
        settings: Settings | None = None,
    ) -> None:
        self._db = db
        self._github = github_client
        self._settings = settings or get_settings()

    async def publish(
        self, project: Project, delivery: Delivery, actor: str = "operator"
    ) -> tuple[Delivery, dict]:
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

        # Resilient live call — retries transient GitHub failures, matching the live tool adapters.
        issue = await retry_async(
            lambda: self._github.create_issue(
                repo=repo,
                title=delivery.title,
                body=self._issue_body(delivery),
                labels=[_ISSUE_LABEL],
            ),
            attempts=self._settings.TOOL_RETRY_ATTEMPTS,
            base_delay=self._settings.TOOL_RETRY_BASE_DELAY,
            tool="github",
        )
        issue_url = issue.get("html_url", "")
        delivery.target_ref = issue_url
        delivery.status = "planned"

        # Golden rule #10 — an append-only audit entry for every governed write-back.
        self._db.add(
            AuditLog(
                project_id=project.id,
                actor=actor,
                phase="planning",
                agent_name="delivery-publish",
                action="ALLOW",
                model="",
                auto_enforced=False,  # human-initiated write-back, not an agent auto-enforcement
                summary=(
                    f"Published delivery '{delivery.title}' to {repo} "
                    f"(issue #{issue.get('number')}) → {issue_url}"
                )[:2000],
            )
        )
        await self._db.flush()
        await self._db.refresh(delivery)

        logger.info(
            "delivery.published",
            delivery_id=str(delivery.id),
            repo=repo,
            issue_number=issue.get("number"),
            actor=actor,
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
