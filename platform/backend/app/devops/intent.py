"""Natural-language intent → an ordered plan of tool calls.

This is a **deterministic keyword planner**: it maps signals in a free-text request ("ship the refund
fix and tell the team") to an ordered list of :class:`PlannedCall` (open a PR → notify Slack). It stands
in for an LLM planner — offline and reproducible — and is deliberately transparent so the plan is
auditable. A real build swaps :func:`plan_from_intent` for an LLM call that returns the same
``list[PlannedCall]`` shape; everything downstream (the harness-gated executor) is unchanged.

The planner only *proposes* calls. Whether each call is allowed is decided at execution time by the
harness tool registry (default-deny), and whether the overall result auto-enforces is decided by the
confidence gate — the planner has no authority of its own.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.agents.tools.catalog import (
    CONFLUENCE_PUBLISH_PAGE,
    GITHUB_OPEN_PR,
    JENKINS_TRIGGER_BUILD,
    JIRA_CREATE_ISSUE,
    SLACK_POST_MESSAGE,
)


@dataclass(frozen=True)
class PlannedCall:
    """One proposed tool invocation: the tool name and its arguments."""

    tool: str
    arguments: dict[str, Any] = field(default_factory=dict)


# Ordered signal table: (tool, keyword-pattern). Order defines the DevOps sequence (branch → PR → CI →
# ticket → docs → notify) so a multi-signal request produces a sensible pipeline.
_SIGNALS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (GITHUB_OPEN_PR, re.compile(r"\b(pr|pull request|ship|merge|open a pr|raise a pr)\b", re.I)),
    (
        JENKINS_TRIGGER_BUILD,
        re.compile(r"\b(build|ci|pipeline|jenkins|deploy|release build)\b", re.I),
    ),
    (JIRA_CREATE_ISSUE, re.compile(r"\b(ticket|issue|jira|story|bug|task|backlog)\b", re.I)),
    (
        CONFLUENCE_PUBLISH_PAGE,
        re.compile(r"\b(doc|docs|confluence|page|publish|release notes|wiki)\b", re.I),
    ),
    (
        SLACK_POST_MESSAGE,
        re.compile(r"\b(notify|slack|announce|tell the team|message|ping)\b", re.I),
    ),
)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "change"


def plan_from_intent(intent: str, *, context: dict[str, Any] | None = None) -> list[PlannedCall]:
    """Parse a free-text intent into an ordered list of proposed tool calls.

    ``context`` supplies the concrete targets (repo, jira project key, confluence space, slack channel,
    jenkins job, branch names) that the phrasing does not carry. Missing targets fall back to explicit
    placeholders so the plan is always well-formed and the gap is visible in the audit log.
    """
    ctx = context or {}
    feature = str(ctx.get("feature", "change"))
    slug = _slug(feature)
    calls: list[PlannedCall] = []

    for tool, pattern in _SIGNALS:
        if not pattern.search(intent):
            continue
        calls.append(PlannedCall(tool=tool, arguments=_arguments_for(tool, feature, slug, ctx)))
    return calls


def _arguments_for(tool: str, feature: str, slug: str, ctx: dict[str, Any]) -> dict[str, Any]:
    if tool == GITHUB_OPEN_PR:
        return {
            "repo": str(ctx.get("repo", "org/UNSET-REPO")),
            "title": f"feat: {feature}",
            "head": f"feature/{slug}",
            "base": str(ctx.get("base_branch", "main")),
        }
    if tool == JENKINS_TRIGGER_BUILD:
        return {
            "job": str(ctx.get("jenkins_job", "UNSET-JOB")),
            "parameters": {"branch": f"feature/{slug}"},
        }
    if tool == JIRA_CREATE_ISSUE:
        return {
            "project_key": str(ctx.get("jira_project_key", "UNSET")),
            "summary": feature,
            "issue_type": str(ctx.get("issue_type", "Story")),
        }
    if tool == CONFLUENCE_PUBLISH_PAGE:
        return {
            "space_key": str(ctx.get("confluence_space", "UNSET")),
            "title": f"{feature} — Notes",
        }
    if tool == SLACK_POST_MESSAGE:
        return {
            "channel": str(ctx.get("slack_channel", "#UNSET")),
            "text": f"Shipped: {feature}.",
        }
    return {}
