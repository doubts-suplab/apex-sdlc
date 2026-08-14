"""Live, credentialed tool adapters — the production swap-in for the offline set.

Each adapter matches the offline adapter's ``dict -> dict`` signature and normalises its response to the
same shape, so nothing above the registry changes when going live. Every endpoint is **config-driven**:
base URLs and tokens come from :class:`app.core.config.Settings`, so a system can point at the real API, a
mock server, or a self-hosted instance purely via environment variables. The integration clients are
async; adapters bridge to sync via the harness's ``_run_sync`` (the harness ``Agent.run`` is sync).

:func:`resolve_adapters` decides, **per tool**, whether to use the live adapter (its credentials are
configured) or fall back to the deterministic offline one — so a partially-configured environment still
runs end-to-end, live where it can and offline elsewhere.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.agents.base import _run_sync
from app.agents.tools.adapters import OFFLINE_ADAPTERS
from app.agents.tools.catalog import (
    CONFLUENCE_PUBLISH_PAGE,
    GITHUB_OPEN_PR,
    JENKINS_TRIGGER_BUILD,
    JIRA_CREATE_ISSUE,
    SLACK_POST_MESSAGE,
)
from app.agents.tools.retry import retry_async
from app.core.config import Settings, get_settings
from app.core.logging import get_logger

_log = get_logger("apex.tools.live")

ToolImpl = Callable[[dict[str, Any]], dict[str, Any]]


def _resilient(settings: Settings, tool: str, factory: Callable[[], Any]) -> Any:
    """Run a live client call under retry+backoff, then bridge async→sync for the adapter."""
    return _run_sync(
        retry_async(
            factory,
            attempts=settings.TOOL_RETRY_ATTEMPTS,
            base_delay=settings.TOOL_RETRY_BASE_DELAY,
            tool=tool,
        )
    )


def _github_adapter(settings: Settings) -> ToolImpl:
    from app.integrations.github.client import GitHubClient

    def _impl(args: dict[str, Any]) -> dict[str, Any]:
        client = GitHubClient(settings.GITHUB_TOKEN, base_url=settings.GITHUB_API_BASE)
        pr = _resilient(
            settings,
            "github",
            lambda: client.create_pull_request(
                repo=args["repo"],
                title=args["title"],
                head=args["head"],
                base=args["base"],
                body=args.get("body", ""),
            ),
        )
        return {
            "system": "github",
            "action": "open_pull_request",
            "number": pr.get("number"),
            "url": pr.get("html_url", ""),
            "title": pr.get("title", args["title"]),
            "state": pr.get("state", "open"),
        }

    return _impl


def _jira_adapter(settings: Settings) -> ToolImpl:
    from app.integrations.jira.client import JiraClient

    def _impl(args: dict[str, Any]) -> dict[str, Any]:
        client = JiraClient(settings.JIRA_BASE_URL, settings.JIRA_EMAIL, settings.JIRA_API_TOKEN)
        issue = _resilient(
            settings,
            "jira",
            lambda: client.create_story(
                project_key=args["project_key"],
                summary=args["summary"],
                description=args.get("description", args["summary"]),
            ),
        )
        return {
            "system": "jira",
            "action": "create_issue",
            "key": issue.get("key", ""),
            "issue_type": args.get("issue_type", "Story"),
            "summary": args["summary"],
            "status": "To Do",
        }

    return _impl


def _confluence_adapter(settings: Settings) -> ToolImpl:
    from app.integrations.confluence.client import ConfluenceClient

    def _impl(args: dict[str, Any]) -> dict[str, Any]:
        client = ConfluenceClient(
            settings.CONFLUENCE_BASE_URL, settings.CONFLUENCE_EMAIL, settings.CONFLUENCE_TOKEN
        )
        page = _resilient(
            settings,
            "confluence",
            lambda: client.create_page(
                space_key=args["space_key"],
                title=args["title"],
                body_html=args.get("body_html", f"<p>{args['title']}</p>"),
            ),
        )
        page_id = page.get("id", "")
        return {
            "system": "confluence",
            "action": "publish_page",
            "page_id": page_id,
            "url": f"{settings.CONFLUENCE_BASE_URL.rstrip('/')}/wiki/pages/{page_id}",
            "title": args["title"],
        }

    return _impl


def _slack_adapter(settings: Settings) -> ToolImpl:
    from app.integrations.slack.client import SlackClient

    def _impl(args: dict[str, Any]) -> dict[str, Any]:
        client = SlackClient(settings.SLACK_BOT_TOKEN, base_url=settings.SLACK_BASE_URL)
        res = _resilient(
            settings,
            "slack",
            lambda: client.post_message(channel=args["channel"], text=args["text"]),
        )
        return {
            "system": "slack",
            "action": "post_message",
            "channel": res.get("channel", args["channel"]),
            "ts": res.get("ts", ""),
            "delivered": bool(res.get("ok", True)),
        }

    return _impl


def _jenkins_adapter(settings: Settings) -> ToolImpl:
    from app.integrations.jenkins.client import JenkinsClient

    def _impl(args: dict[str, Any]) -> dict[str, Any]:
        client = JenkinsClient(
            settings.JENKINS_BASE_URL, settings.JENKINS_USER, settings.JENKINS_API_TOKEN
        )
        res = _resilient(
            settings,
            "jenkins",
            lambda: client.trigger_build(job=args["job"], parameters=args.get("parameters", {})),
        )
        return {
            "system": "jenkins",
            "action": "trigger_build",
            "job": args["job"],
            "queue_url": res.get("queue_url", ""),
            "queued": bool(res.get("queued", True)),
        }

    return _impl


# Per-tool: (factory, predicate). The predicate reports whether that system's credentials are configured.
_LIVE_TOOLS: dict[str, tuple[Callable[[Settings], ToolImpl], Callable[[Settings], bool]]] = {
    GITHUB_OPEN_PR: (_github_adapter, lambda s: bool(s.GITHUB_TOKEN)),
    JIRA_CREATE_ISSUE: (_jira_adapter, lambda s: bool(s.JIRA_BASE_URL and s.JIRA_API_TOKEN)),
    CONFLUENCE_PUBLISH_PAGE: (
        _confluence_adapter,
        lambda s: bool(s.CONFLUENCE_BASE_URL and s.CONFLUENCE_TOKEN),
    ),
    SLACK_POST_MESSAGE: (_slack_adapter, lambda s: bool(s.SLACK_BOT_TOKEN)),
    JENKINS_TRIGGER_BUILD: (
        _jenkins_adapter,
        lambda s: bool(s.JENKINS_BASE_URL and s.JENKINS_API_TOKEN),
    ),
}


def resolve_adapters(settings: Settings | None = None) -> dict[str, ToolImpl]:
    """Return the adapter set to run: live per tool where its credentials are configured, else offline.

    An unconfigured environment resolves to the fully-offline set (the default), which keeps the demo and
    tests deterministic; setting a system's env vars flips just that tool to its live adapter.
    """
    settings = settings or get_settings()
    resolved: dict[str, ToolImpl] = dict(OFFLINE_ADAPTERS)
    live_names: list[str] = []
    for name, (factory, is_configured) in _LIVE_TOOLS.items():
        if is_configured(settings):
            resolved[name] = factory(settings)
            live_names.append(name)
    if live_names:
        _log.info("tools.live_adapters_selected", tools=live_names)
    return resolved
