"""Live-adapter tests — credential-gated resolution + a live call against a mock endpoint.

Proves (a) ``resolve_adapters`` falls back to offline when creds are absent and flips a single tool to
live when its env vars are set, and (b) a live adapter honours the **configurable base URL** by driving a
GitHub PR against an in-process mock server (no real network).

Self-contained: ``pytest --noconftest tests/devops/test_live_adapters.py``.
"""

from __future__ import annotations

import httpx

from app.agents.tools.adapters import OFFLINE_ADAPTERS
from app.agents.tools.catalog import GITHUB_OPEN_PR
from app.agents.tools.live_adapters import resolve_adapters
from app.core.config import Settings


def _settings(**overrides: str) -> Settings:
    # Explicitly clear every credential so ambient session env (e.g. a real GITHUB_TOKEN) never leaks
    # in — constructor kwargs take precedence over env in pydantic-settings, making this hermetic.
    base = {
        "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
        "REDIS_URL": "redis://localhost:6379/0",
        "SECRET_KEY": "test",
        "GITHUB_TOKEN": "",
        "JIRA_BASE_URL": "",
        "JIRA_API_TOKEN": "",
        "CONFLUENCE_BASE_URL": "",
        "CONFLUENCE_TOKEN": "",
        "SLACK_BOT_TOKEN": "",
        "JENKINS_BASE_URL": "",
        "JENKINS_API_TOKEN": "",
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


def test_resolves_to_offline_without_credentials():
    resolved = resolve_adapters(_settings())
    # Every tool falls back to its offline adapter (identity match).
    assert resolved == OFFLINE_ADAPTERS


def test_configured_tool_flips_to_live():
    resolved = resolve_adapters(_settings(GITHUB_TOKEN="ghp_x"))
    assert resolved[GITHUB_OPEN_PR] is not OFFLINE_ADAPTERS[GITHUB_OPEN_PR]  # github is live now
    # The others, still unconfigured, remain offline.
    from app.agents.tools.catalog import JIRA_CREATE_ISSUE

    assert resolved[JIRA_CREATE_ISSUE] is OFFLINE_ADAPTERS[JIRA_CREATE_ISSUE]


def test_live_github_adapter_uses_configurable_base_url(monkeypatch):
    captured: dict[str, str] = {}

    def _handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(
            201,
            json={"number": 42, "html_url": "https://mock.local/acme/x/pull/42", "state": "open",
                  "title": "feat: y"},
        )

    transport = httpx.MockTransport(_handler)
    real_async_client = httpx.AsyncClient

    def _mock_async_client(*args, **kwargs):  # noqa: ANN002, ANN003
        kwargs["transport"] = transport
        return real_async_client(*args, **kwargs)

    # Point the client at a mock base URL and route all traffic to the in-process transport.
    monkeypatch.setattr(httpx, "AsyncClient", _mock_async_client)
    adapters = resolve_adapters(_settings(GITHUB_TOKEN="ghp_x", GITHUB_API_BASE="https://mock.local"))

    result = adapters[GITHUB_OPEN_PR](
        {"repo": "acme/x", "title": "feat: y", "head": "feature/y", "base": "main"}
    )

    assert captured["url"] == "https://mock.local/repos/acme/x/pulls"  # configurable base honoured
    assert result == {
        "system": "github",
        "action": "open_pull_request",
        "number": 42,
        "url": "https://mock.local/acme/x/pull/42",
        "title": "feat: y",
        "state": "open",
    }
