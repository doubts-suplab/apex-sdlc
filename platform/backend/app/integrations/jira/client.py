from __future__ import annotations

from typing import Any

import httpx

from app.core.logging import get_logger
from app.integrations.errors import IntegrationError

logger = get_logger(__name__)

# Standard Jira story points custom field (used by most Jira Cloud instances)
_STORY_POINTS_FIELD = "customfield_10016"


class JiraClient:
    """Async Jira REST API client (Agile v1 + API v3)."""

    def __init__(self, base_url: str, email: str, api_token: str) -> None:
        self._base = base_url.rstrip("/")
        self._auth = httpx.BasicAuth(email, api_token)
        self._headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        base_path: str = "/rest",
        **kwargs: Any,
    ) -> Any:
        """Execute an authenticated Jira API request and return parsed JSON."""
        url = f"{self._base}{base_path}{path}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method,
                url,
                auth=self._auth,
                headers=self._headers,
                **kwargs,
            )

        if not response.is_success:
            body = response.text[:500]
            logger.warning(
                "jira.request_error",
                method=method,
                path=path,
                status=response.status_code,
                body=body,
            )
            raise IntegrationError(
                integration="jira",
                message=f"{method} {path} → HTTP {response.status_code}: {body}",
                status_code=response.status_code,
            )

        if response.content:
            return response.json()
        return {}

    # ------------------------------------------------------------------
    # Agile (board/sprint) endpoints — /rest/agile/1.0/
    # ------------------------------------------------------------------

    async def get_active_sprint(self, board_id: str) -> dict | None:
        """Return the currently active sprint for a board, or None.

        Args:
            board_id: Numeric Jira board ID as a string.

        Returns:
            Sprint object dict, or ``None`` if no active sprint exists.
        """
        data = await self._request(
            "GET",
            f"/agile/1.0/board/{board_id}/sprint",
            params={"state": "active"},
        )
        sprints = data.get("values", [])
        return sprints[0] if sprints else None

    async def get_sprint_issues(
        self,
        sprint_id: str,
        fields: list[str] | None = None,
    ) -> list[dict]:
        """Fetch all issues in a sprint.

        Args:
            sprint_id: Numeric Jira sprint ID as a string.
            fields: Jira field IDs to include. Defaults to common set.

        Returns:
            List of Jira issue dicts with the requested fields.
        """
        default_fields = [
            "summary",
            "status",
            "assignee",
            "issuetype",
            "priority",
            _STORY_POINTS_FIELD,
        ]
        requested_fields = fields or default_fields

        results: list[dict] = []
        start_at = 0
        max_results = 50

        while True:
            data = await self._request(
                "GET",
                f"/agile/1.0/sprint/{sprint_id}/issue",
                params={
                    "fields": ",".join(requested_fields),
                    "startAt": start_at,
                    "maxResults": max_results,
                },
            )
            issues = data.get("issues", [])
            results.extend(issues)
            total = data.get("total", 0)
            start_at += len(issues)
            if start_at >= total or not issues:
                break

        return results

    # ------------------------------------------------------------------
    # Issue CRUD endpoints — /rest/api/3/
    # ------------------------------------------------------------------

    async def create_story(
        self,
        project_key: str,
        summary: str,
        description: str,
        story_points: float | None = None,
    ) -> dict:
        """Create a Story issue in the given Jira project.

        Args:
            project_key: Jira project key (e.g. ``"APEX"``).
            summary: One-line issue summary.
            description: Full story description (plain text; converted to ADF).
            story_points: Optional story point estimate.

        Returns:
            Created Jira issue object (with ``id``, ``key``, ``self`` fields).
        """
        fields: dict[str, Any] = {
            "project": {"key": project_key},
            "issuetype": {"name": "Story"},
            "summary": summary,
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": description}],
                    }
                ],
            },
        }

        if story_points is not None:
            fields[_STORY_POINTS_FIELD] = story_points

        return await self._request(
            "POST",
            "/api/3/issue",
            json={"fields": fields},
        )

    async def create_epic(
        self,
        project_key: str,
        name: str,
        summary: str,
    ) -> dict:
        """Create an Epic issue in the given Jira project.

        Args:
            project_key: Jira project key.
            name: Epic name (displayed in the roadmap).
            summary: One-line epic summary.

        Returns:
            Created Jira issue object.
        """
        fields: dict[str, Any] = {
            "project": {"key": project_key},
            "issuetype": {"name": "Epic"},
            "summary": summary,
            # customfield_10011 is the Epic Name field (Jira Software default)
            "customfield_10011": name,
        }

        return await self._request(
            "POST",
            "/api/3/issue",
            json={"fields": fields},
        )

    async def get_project_info(self, project_key: str) -> dict:
        """Fetch metadata for a Jira project.

        Args:
            project_key: Jira project key (e.g. ``"APEX"``).

        Returns:
            Jira project object with ``id``, ``key``, ``name``, ``issueTypes``, etc.
        """
        return await self._request(
            "GET",
            f"/api/3/project/{project_key}",
        )
