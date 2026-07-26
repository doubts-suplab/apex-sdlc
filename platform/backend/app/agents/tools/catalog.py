"""DevOps tool catalog — the named, typed tools the harness registry governs.

This is the single source of truth for *which* external actions an agent may take (open a PR, create a
Jira issue, publish a Confluence page, post to Slack, trigger a Jenkins build). Each tool declares a
``side_effect`` (``read``/``write``) so the registry and audit can reason about blast radius. The concrete
behaviour is supplied separately by an *adapter* (offline deterministic today; a credentialed MCP/HTTP
adapter later) — the catalog names and shapes the contract, the adapter fulfils it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Tool name convention: "<system>.<verb_object>", no wildcards (the registry forbids them).
GITHUB_OPEN_PR = "github.open_pull_request"
JIRA_CREATE_ISSUE = "jira.create_issue"
CONFLUENCE_PUBLISH_PAGE = "confluence.publish_page"
SLACK_POST_MESSAGE = "slack.post_message"
JENKINS_TRIGGER_BUILD = "jenkins.trigger_build"


@dataclass(frozen=True)
class ToolSpec:
    """A registrable tool: its name, human description, side effect, and required argument keys."""

    name: str
    description: str
    side_effect: str  # "read" | "write"
    required_args: tuple[str, ...] = field(default_factory=tuple)


TOOL_CATALOG: tuple[ToolSpec, ...] = (
    ToolSpec(
        GITHUB_OPEN_PR,
        "Open a GitHub pull request from a head branch into a base branch.",
        "write",
        ("repo", "title", "head", "base"),
    ),
    ToolSpec(
        JIRA_CREATE_ISSUE,
        "Create a Jira issue (story/bug/task) under a project key.",
        "write",
        ("project_key", "summary", "issue_type"),
    ),
    ToolSpec(
        CONFLUENCE_PUBLISH_PAGE,
        "Publish (create/update) a Confluence page in a space.",
        "write",
        ("space_key", "title"),
    ),
    ToolSpec(
        SLACK_POST_MESSAGE,
        "Post a message to a Slack channel.",
        "write",
        ("channel", "text"),
    ),
    ToolSpec(
        JENKINS_TRIGGER_BUILD,
        "Trigger a Jenkins job build with parameters.",
        "write",
        ("job",),
    ),
)

TOOLS_BY_NAME: dict[str, ToolSpec] = {t.name: t for t in TOOL_CATALOG}
