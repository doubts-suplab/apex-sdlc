"""Tests for the GitHub API client.

Uses unittest.mock to patch httpx.AsyncClient so no real network calls are made.
Tests cover get_prs, get_repo_stats, get_pr_diff, post_pr_comment, get_commits,
and get_repo_file, plus error handling via IntegrationError.
"""
from __future__ import annotations

import base64
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.integrations.errors import IntegrationError
from app.integrations.github.client import GitHubClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client() -> GitHubClient:
    return GitHubClient(token="ghp_test_token")


def _mock_response(status_code: int, body: dict | str | list) -> MagicMock:
    """Build a mock httpx.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.is_success = 200 <= status_code < 300
    if isinstance(body, (dict, list)):
        resp.content = json.dumps(body).encode()
        resp.json.return_value = body
        resp.text = json.dumps(body)
    else:
        resp.content = body.encode() if body else b""
        resp.text = body
        resp.json.side_effect = ValueError("not json")
    return resp


def _mock_context_manager(response: MagicMock):
    """Wrap a response in an async context manager that exposes .request()."""
    http_client = AsyncMock()
    http_client.request = AsyncMock(return_value=response)
    http_client.get = AsyncMock(return_value=response)

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=http_client)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


# ---------------------------------------------------------------------------
# get_prs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_prs_returns_list(client: GitHubClient):
    """get_prs returns the list of PR dicts from the API."""
    prs = [{"id": 1, "number": 42, "state": "open"}, {"id": 2, "number": 43, "state": "closed"}]
    resp = _mock_response(200, prs)

    with patch("app.integrations.github.client.httpx.AsyncClient", return_value=_mock_context_manager(resp)):
        result = await client.get_prs("org/repo", state="all", per_page=30)

    assert result == prs
    assert len(result) == 2


@pytest.mark.asyncio
async def test_get_prs_raises_integration_error_on_failure(client: GitHubClient):
    """get_prs raises IntegrationError on non-2xx response."""
    resp = _mock_response(401, {"message": "Bad credentials"})

    with patch("app.integrations.github.client.httpx.AsyncClient", return_value=_mock_context_manager(resp)):
        with pytest.raises(IntegrationError) as exc_info:
            await client.get_prs("org/repo")

    assert exc_info.value.integration == "github"
    assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# get_repo_stats
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_repo_stats_returns_structured_dict(client: GitHubClient):
    """get_repo_stats maps GitHub API fields to the expected dict shape."""
    api_response = {
        "stargazers_count": 100,
        "forks_count": 25,
        "open_issues_count": 5,
        "language": "Python",
        "default_branch": "main",
        "name": "my-repo",
    }
    resp = _mock_response(200, api_response)

    with patch("app.integrations.github.client.httpx.AsyncClient", return_value=_mock_context_manager(resp)):
        result = await client.get_repo_stats("org/repo")

    assert result == {
        "stars": 100,
        "forks": 25,
        "open_issues": 5,
        "language": "Python",
        "default_branch": "main",
    }
    # Should not include raw fields like "name"
    assert "name" not in result


@pytest.mark.asyncio
async def test_get_repo_stats_handles_missing_fields(client: GitHubClient):
    """get_repo_stats uses defaults for missing API fields."""
    resp = _mock_response(200, {})

    with patch("app.integrations.github.client.httpx.AsyncClient", return_value=_mock_context_manager(resp)):
        result = await client.get_repo_stats("org/repo")

    assert result["stars"] == 0
    assert result["forks"] == 0
    assert result["open_issues"] == 0
    assert result["language"] is None
    assert result["default_branch"] == "main"


@pytest.mark.asyncio
async def test_get_repo_stats_raises_on_404(client: GitHubClient):
    """get_repo_stats raises IntegrationError for a 404 response."""
    resp = _mock_response(404, {"message": "Not Found"})

    with patch("app.integrations.github.client.httpx.AsyncClient", return_value=_mock_context_manager(resp)):
        with pytest.raises(IntegrationError) as exc_info:
            await client.get_repo_stats("org/nonexistent")

    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# get_pr_diff
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_pr_diff_returns_diff_text(client: GitHubClient):
    """get_pr_diff returns the raw diff text from the GitHub API."""
    diff_text = "diff --git a/foo.py b/foo.py\n+++ added line\n"

    # get_pr_diff uses client.get directly (not .request)
    resp = MagicMock()
    resp.status_code = 200
    resp.is_success = True
    resp.text = diff_text

    cm = MagicMock()
    http_client = AsyncMock()
    http_client.get = AsyncMock(return_value=resp)
    cm.__aenter__ = AsyncMock(return_value=http_client)
    cm.__aexit__ = AsyncMock(return_value=False)

    with patch("app.integrations.github.client.httpx.AsyncClient", return_value=cm):
        result = await client.get_pr_diff("org/repo", pr_number=42)

    assert result == diff_text


# ---------------------------------------------------------------------------
# post_pr_comment
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_pr_comment_returns_created_comment(client: GitHubClient):
    """post_pr_comment sends the body and returns the created comment object."""
    created = {"id": 999, "body": "AI review complete"}
    resp = _mock_response(201, created)
    # Override is_success for 201
    resp.is_success = True

    with patch("app.integrations.github.client.httpx.AsyncClient", return_value=_mock_context_manager(resp)):
        result = await client.post_pr_comment("org/repo", pr_number=7, body="AI review complete")

    assert result == created


# ---------------------------------------------------------------------------
# get_commits
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_commits_returns_list(client: GitHubClient):
    """get_commits returns the list of commit objects."""
    commits = [{"sha": "abc123"}, {"sha": "def456"}]
    resp = _mock_response(200, commits)

    with patch("app.integrations.github.client.httpx.AsyncClient", return_value=_mock_context_manager(resp)):
        result = await client.get_commits("org/repo", per_page=10)

    assert result == commits


# ---------------------------------------------------------------------------
# get_repo_file
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_repo_file_decodes_base64_content(client: GitHubClient):
    """get_repo_file decodes base64 content from the GitHub contents API."""
    raw_content = "# Hello World\n"
    encoded = base64.b64encode(raw_content.encode()).decode()
    api_response = {"content": encoded, "encoding": "base64"}
    resp = _mock_response(200, api_response)

    with patch("app.integrations.github.client.httpx.AsyncClient", return_value=_mock_context_manager(resp)):
        result = await client.get_repo_file("org/repo", "README.md")

    assert result == raw_content
