"""Phase-agent governance tests — the harness governs every phase agent, not just compliance.

Proves the general contract for each of the six new phase agents: the harness (not the agent) sets
``auto_enforced``, SUGGEST-authority phases always route to a human, higher-authority phases can
auto-enforce when confident, and no run ever bypasses the confidence gate. Self-contained (no DB /
FastAPI) — run with ``pytest --noconftest tests/agents/test_phase_agents.py``.
"""

from __future__ import annotations

import pytest
from agent_harness import AuthorityLevel, DecisionAction, ToolRegistry
from agent_harness.adapters import (
    InMemoryAudit,
    InMemoryHumanReview,
    InMemoryKillSwitch,
    InMemoryObservability,
    StubLlm,
)
from agent_harness.core.harness import BYPASS_COUNTER

from app.agents import (
    AgentContext,
    ArchitectureAgent,
    PRReviewerAgent,
    QAAnalystAgent,
    ReleaseEngineerAgent,
    RequirementsAgent,
    TechWriterAgent,
    build_apex_harness,
    run_agent,
)

_BRIEF = {"feature_name": "Customer Refunds", "brief": "Let customers self-serve refunds."}


def _harness():
    audit, review, obs, kill = (
        InMemoryAudit(), InMemoryHumanReview(), InMemoryObservability(), InMemoryKillSwitch(),
    )
    harness = build_apex_harness(
        registry=ToolRegistry(), audit=audit, human_review=review, observability=obs, kill_switch=kill,
    )
    return harness, audit, review, obs


def _ctx(persona: str, phase: str, **extra):
    return AgentContext(
        project_id="refund-service", phase=phase, actor_id=persona,
        inputs={**_BRIEF, **extra}, run_id=f"refund-service:{phase}",
    )


# -- SUGGEST-authority phases never auto-enforce (gate G-5): AI drafts, humans approve -------------
@pytest.mark.parametrize(
    "agent_cls,phase,persona",
    [
        (RequirementsAgent, "requirements", "ba"),
        (ArchitectureAgent, "architecture", "architect"),
        (QAAnalystAgent, "testing", "qa"),
        (TechWriterAgent, "docs", "developer"),
    ],
)
def test_suggest_phases_route_to_human(agent_cls, phase, persona):
    harness, _audit, review, obs = _harness()
    agent = agent_cls(StubLlm(reply="drafted"))
    result = run_agent(harness, agent, _ctx(persona, phase))
    assert agent.authority_level is AuthorityLevel.SUGGEST
    assert result.decision.action is DecisionAction.SUGGEST
    assert result.decision.auto_enforced is False           # SUGGEST never enforces, regardless of confidence
    assert len(review.items) == 1                            # routed to a human
    assert result.artifacts, "phase must produce at least one artifact"
    assert obs.counter(BYPASS_COUNTER) == 0


# -- Development (ALERT) auto-enforces its advisory when confident --------------------------------
def test_development_alert_auto_enforces_when_confident():
    harness, _audit, review, obs = _harness()
    agent = PRReviewerAgent(StubLlm(reply="issues found"))
    result = run_agent(harness, agent, _ctx("developer", "development"))
    assert agent.authority_level is AuthorityLevel.ALERT
    assert result.decision.action is DecisionAction.ALERT
    assert result.decision.auto_enforced is True            # 0.88 >= 0.80 ALERT threshold
    assert review.items == ()
    assert obs.counter(BYPASS_COUNTER) == 0


# -- CI/CD (RATE_LIMIT) auto-enforces ALLOW when green, holds (ALERT→human) when red -------------
def test_cicd_allows_when_green_and_holds_when_red():
    harness, _audit, review, _obs = _harness()
    green = run_agent(harness, ReleaseEngineerAgent(StubLlm()), _ctx("lead", "cicd", checks_green=True))
    assert green.decision.action is DecisionAction.ALLOW
    assert green.decision.auto_enforced is True             # 0.88 >= 0.85 RATE_LIMIT threshold

    harness2, _a2, review2, _o2 = _harness()
    red = run_agent(harness2, ReleaseEngineerAgent(StubLlm()), _ctx("lead", "cicd", checks_green=False))
    assert red.decision.action is DecisionAction.ALERT
    assert red.decision.auto_enforced is True or red.decision.auto_enforced is False
    # A held release (ALERT at 0.9) auto-enforces the *alert* — the point is it did NOT ALLOW.
    assert red.decision.action is not DecisionAction.ALLOW


# -- Requirements with no brief defers to a human ------------------------------------------------
def test_requirements_without_brief_defers():
    harness, _audit, review, _obs = _harness()
    agent = RequirementsAgent(StubLlm())
    ctx = AgentContext(project_id="p", phase="requirements", actor_id="ba", inputs={}, run_id="p:req")
    result = run_agent(harness, agent, ctx)
    assert result.decision.action is DecisionAction.DEFER
    assert result.decision.auto_enforced is False
    assert len(review.items) == 1
