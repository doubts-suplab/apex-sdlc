from __future__ import annotations

import base64
from typing import Any

import httpx

from app.core.logging import get_logger
from app.integrations.errors import IntegrationError

logger = get_logger(__name__)

_GITHUB_API_BASE = "https://api.github.com"
_GITHUB_API_VERSION = "2022-11-28"


class GitHubClient:
    """Async GitHub REST API v3 client."""

    def __init__(self, token: str) -> None:
        self._token = token
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": _GITHUB_API_VERSION,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> Any:
        """Execute an authenticated GitHub API request and return parsed JSON."""
        url = f"{_GITHUB_API_BASE}{path}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method, url, headers=self._headers, **kwargs
            )

        if not response.is_success:
            body = response.text[:500]
            logger.warning(
                "github.request_error",
                method=method,
                path=path,
                status=response.status_code,
                body=body,
            )
            raise IntegrationError(
                integration="github",
                message=f"{method} {path} → HTTP {response.status_code}: {body}",
                status_code=response.status_code,
            )

        if response.content:
            return response.json()
        return {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_prs(
        self,
        repo: str,
        state: str = "all",
        per_page: int = 30,
    ) -> list[dict]:
        """List pull requests for a repository.

        Args:
            repo: ``"owner/repo"`` format.
            state: ``"open"``, ``"closed"``, or ``"all"``.
            per_page: Number of results per page (max 100).

        Returns:
            List of pull request objects from the GitHub API.
        """
        return await self._request(
            "GET",
            f"/repos/{repo}/pulls",
            params={"state": state, "per_page": per_page, "sort": "updated", "direction": "desc"},
        )

    async def get_pr_diff(self, repo: str, pr_number: int) -> str:
        """Fetch the unified diff for a pull request.

        Args:
            repo: ``"owner/repo"`` format.
            pr_number: Pull request number.

        Returns:
            Unified diff as a plain string.
        """
        url = f"{_GITHUB_API_BASE}/repos/{repo}/pulls/{pr_number}"
        diff_headers = {**self._headers, "Accept": "application/vnd.github.v3.diff"}
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(url, headers=diff_headers)

        if not response.is_success:
            raise IntegrationError(
                integration="github",
                message=f"Failed to fetch PR diff for {repo}#{pr_number}: HTTP {response.status_code}",
                status_code=response.status_code,
            )
        return response.text

    async def post_pr_comment(
        self,
        repo: str,
        pr_number: int,
        body: str,
    ) -> dict:
        """Post a comment on a pull request.

        Args:
            repo: ``"owner/repo"`` format.
            pr_number: Pull request number.
            body: Markdown comment body.

        Returns:
            Created issue comment object.
        """
        return await self._request(
            "POST",
            f"/repos/{repo}/issues/{pr_number}/comments",
            json={"body": body},
        )

    async def get_repo_file(
        self,
        repo: str,
        path: str,
        ref: str = "main",
    ) -> str:
        """Fetch and decode the content of a file from a repository.

        Args:
            repo: ``"owner/repo"`` format.
            path: File path within the repository (e.g. ``"README.md"``).
            ref: Branch, tag, or commit SHA (default: ``"main"``).

        Returns:
            Decoded file content as a string.
        """
        data = await self._request(
            "GET",
            f"/repos/{repo}/contents/{path}",
            params={"ref": ref},
        )
        encoded = data.get("content", "")
        # GitHub returns base64 with newlines
        return base64.b64decode(encoded.replace("\n", "")).decode("utf-8")

    async def get_commits(
        self,
        repo: str,
        since: str | None = None,
        per_page: int = 30,
    ) -> list[dict]:
        """List commits for a repository.

        Args:
            repo: ``"owner/repo"`` format.
            since: ISO 8601 timestamp; only commits after this date are returned.
            per_page: Number of results per page.

        Returns:
            List of commit objects.
        """
        params: dict[str, Any] = {"per_page": per_page}
        if since:
            params["since"] = since

        return await self._request(
            "GET",
            f"/repos/{repo}/commits",
            params=params,
        )

    async def get_repo_stats(self, repo: str) -> dict:
        """Fetch high-level repository statistics.

        Args:
            repo: ``"owner/repo"`` format.

        Returns:
            Dict with keys: ``stars``, ``forks``, ``open_issues``, ``language``,
            ``default_branch``.
        """
        data = await self._request("GET", f"/repos/{repo}")
        return {
            "stars": data.get("stargazers_count", 0),
            "forks": data.get("forks_count", 0),
            "open_issues": data.get("open_issues_count", 0),
            "language": data.get("language"),
            "default_branch": data.get("default_branch", "main"),
        }
