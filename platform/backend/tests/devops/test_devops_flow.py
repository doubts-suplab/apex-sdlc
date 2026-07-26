"""DevOps-flow tests — NL intent → plan → harness-gated multi-tool execution.

Self-contained (no DB / FastAPI): ``pytest --noconftest tests/devops/test_devops_flow.py``.
"""

from __future__ import annotations

import json

import pytest
from agent_harness import ToolNotAuthorizedError, ToolRegistry
from agent_harness.adapters import StubLlm

from app.agents.tools import DEVOPS_AGENT_NAME, build_tool_registry
from app.agents.tools.adapters import OFFLINE_ADAPTERS, ToolArgumentError, open_pull_request
from app.devops import plan_from_intent, run_devops_flow

_TARGETS = {
    "feature": "Refund retry fix",
    "repo": "acme/refund-service",
    "jira_project_key": "REF",
    "confluence_space": "REF",
    "slack_channel": "#refunds",
    "jenkins_job": "refund-service-ci",
}


# -- adapters -----------------------------------------------------------------------------------
def test_adapter_is_deterministic():
    args = {"repo": "acme/x", "title": "feat: y", "head": "feature/y", "base": "main"}
    assert open_pull_request(args) == open_pull_request(args)


def test_adapter_requires_arguments():
    with pytest.raises(ToolArgumentError):
        open_pull_request({"repo": "acme/x"})  # missing title/head/base


# -- registry (default-deny) --------------------------------------------------------------------
def test_registry_grants_only_the_devops_tools():
    registry = build_tool_registry()
    allowed = registry.allowlist(DEVOPS_AGENT_NAME)
    assert allowed == frozenset(OFFLINE_ADAPTERS)  # exactly the five tools, nothing more


def test_unauthorized_tool_is_denied_before_side_effect():
    registry = build_tool_registry()
    with pytest.raises(ToolNotAuthorizedError):
        registry.invoke(DEVOPS_AGENT_NAME, "github.delete_repo", {})  # never granted


def test_ungranted_agent_is_denied():
    registry = build_tool_registry()
    with pytest.raises(ToolNotAuthorizedError):
        registry.invoke("some-other-agent", "github.open_pull_request", {})


# -- intent planning ----------------------------------------------------------------------------
def test_intent_orders_the_pipeline():
    plan = plan_from_intent(
        "open a PR, run the build, file a ticket, publish docs, notify slack", context=_TARGETS
    )
    assert [c.tool for c in plan] == [
        "github.open_pull_request",
        "jenkins.trigger_build",
        "jira.create_issue",
        "confluence.publish_page",
        "slack.post_message",
    ]


def test_intent_with_no_signal_is_empty():
    assert plan_from_intent("what's the weather", context=_TARGETS) == []


# -- end-to-end flow under the harness ----------------------------------------------------------
def test_full_pipeline_executes_and_auto_enforces():
    result = run_devops_flow(
        llm=StubLlm(),
        intent="ship the PR, run the build, file a story, publish docs, tell the team",
        context=_TARGETS,
    )
    assert result.decision.action.name == "ALLOW"
    assert result.decision.auto_enforced is True
    log = next(a for a in result.artifacts if a["name"] == "devops-execution-log.json")
    payload = json.loads(log["content"])
    assert payload["executed"] is True
    assert len(payload["results"]) == 5
    assert payload["results"][0]["result"]["system"] == "github"


def test_underspecified_intent_is_held_for_review_not_executed():
    # Recognised intent, but no concrete targets → SUGGEST, no side effects, human review.
    result = run_devops_flow(llm=StubLlm(), intent="open a PR and notify the team", context={})
    assert result.decision.action.name == "SUGGEST"
    assert result.decision.auto_enforced is False
    plan = next(a for a in result.artifacts if a["name"] == "devops-plan.json")
    assert json.loads(plan["content"])["executed"] is False


def test_unrecognised_intent_defers():
    result = run_devops_flow(llm=StubLlm(), intent="hello there", context={})
    assert result.decision.action.name == "DEFER"
    assert result.decision.auto_enforced is False
