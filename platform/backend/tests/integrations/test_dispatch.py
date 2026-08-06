"""Webhook → phase-agent dispatch routing tests.

Pure, offline. Asserts each normalized event routes to the phase the catalog owns, that noise events
route to nothing, and that the proposed agent name is a real catalog agent (never a fabricated one).
"""

from __future__ import annotations

from app.agents.catalog import spec_for
from app.integrations import dispatch


def test_pull_request_opened_routes_to_development() -> None:
    plan = dispatch.dispatch_for_github(
        {"event": "pull_request", "action": "opened", "repo": "acme/widgets", "number": 7}
    )
    assert plan is not None
    assert plan.phase == "development"
    assert plan.agent == spec_for("development").agent_name
    assert plan.persona == "developer"
    assert "PR #7" in plan.reason


def test_pull_request_synchronize_routes() -> None:
    plan = dispatch.dispatch_for_github(
        {"event": "pull_request", "action": "synchronize", "repo": "acme/widgets", "number": 8}
    )
    assert plan is not None and plan.phase == "development"


def test_pull_request_noise_action_routes_to_nothing() -> None:
    plan = dispatch.dispatch_for_github(
        {"event": "pull_request", "action": "labeled", "repo": "acme/widgets", "number": 9}
    )
    assert plan is None


def test_release_published_routes_to_cicd() -> None:
    plan = dispatch.dispatch_for_github(
        {"event": "release", "action": "published", "repo": "acme/widgets", "tag": "v1.0.0"}
    )
    assert plan is not None
    assert plan.phase == "cicd"
    assert plan.agent == spec_for("cicd").agent_name
    assert "v1.0.0" in plan.reason


def test_release_created_but_not_published_routes_to_nothing() -> None:
    plan = dispatch.dispatch_for_github(
        {"event": "release", "action": "created", "repo": "acme/widgets", "tag": "v1.0.0"}
    )
    assert plan is None


def test_push_routes_to_nothing() -> None:
    plan = dispatch.dispatch_for_github(
        {"event": "push", "action": None, "repo": "acme/widgets", "ref": "refs/heads/main"}
    )
    assert plan is None


def test_jira_story_created_routes_to_requirements() -> None:
    plan = dispatch.dispatch_for_jira(
        {"event": "jira:issue_created", "issue_key": "APEX-1", "issue_type": "Story"}
    )
    assert plan is not None
    assert plan.phase == "requirements"
    assert plan.agent == spec_for("requirements").agent_name
    assert plan.persona == "ba"
    assert "APEX-1" in plan.reason


def test_jira_non_story_type_routes_to_nothing() -> None:
    plan = dispatch.dispatch_for_jira(
        {"event": "jira:issue_created", "issue_key": "APEX-2", "issue_type": "Sub-task"}
    )
    assert plan is None


def test_jira_comment_event_routes_to_nothing() -> None:
    plan = dispatch.dispatch_for_jira(
        {"event": "comment_created", "issue_key": "APEX-3", "issue_type": "Story"}
    )
    assert plan is None
