"""apex ↔ agent-harness bridge tests.

Proves apex's phase agents run under the harness's governance: the harness decides enforcement (not the
agent), low-confidence decisions route to human review, unauthorized tools are refused, and context maps
round-trip. These tests are self-contained (no DB / FastAPI) — run with
``pytest --noconftest tests/agents/test_bridge.py``.
"""

from __future__ import annotations

import pytest
from agent_harness import AuthorityLevel, Decision, DecisionAction, ToolRegistry
from agent_harness.adapters import (
    InMemoryAudit,
    InMemoryHumanReview,
    InMemoryKillSwitch,
    InMemoryObservability,
    StubLlm,
)
from agent_harness.core.agent import ToolInvoker

from app.agents import (
    AgentContext,
    ComplianceOfficerAgent,
    build_apex_harness,
    context_from_input,
    run_agent,
    to_agent_input,
)
from app.agents.adapters import FlagKillSwitch, StructlogAudit
from app.agents.base import PhaseAgent


# -- context mapping round-trip --------------------------------------------------------------
def test_context_maps_to_scoped_input_and_back():
    ctx = AgentContext(project_id="proj-1", phase="governance", actor_id="ciso-9",
                       inputs={"risk_score": 0.4}, run_id="run-7")
    req = to_agent_input(ctx)
    assert req.tenant_id == "proj-1" and req.user_id == "ciso-9"
    assert req.is_scoped()
    back = context_from_input(req)
    assert back.project_id == "proj-1" and back.actor_id == "ciso-9"
    assert back.phase == "governance" and back.inputs["risk_score"] == 0.4


# -- helpers ---------------------------------------------------------------------------------
def _harness_with_probes():
    audit, review, obs, kill = (
        InMemoryAudit(), InMemoryHumanReview(), InMemoryObservability(), InMemoryKillSwitch(),
    )
    harness = build_apex_harness(
        registry=ToolRegistry(), audit=audit, human_review=review, observability=obs, kill_switch=kill,
    )
    return harness, audit, review, obs, kill


def _ctx(**inputs):
    return AgentContext(project_id="acme", phase="governance", actor_id="ciso",
                        inputs=inputs, run_id="run-1")


# -- the harness decides enforcement, not the agent (spec §4) --------------------------------
def test_confident_breach_auto_blocks():
    harness, audit, review, obs, _ = _harness_with_probes()
    agent = ComplianceOfficerAgent(StubLlm(reply="material breach"))
    result = run_agent(harness, agent, _ctx(policy_violations=3, risk_score=0.97))
    assert result.decision.action is DecisionAction.BLOCK
    assert result.decision.auto_enforced is True          # 0.97 ≥ 0.95 BLOCK threshold
    assert review.items == ()
    assert obs.counter("confidence_gate_bypass_total") == 0


def test_borderline_breach_routes_to_human():
    harness, audit, review, obs, _ = _harness_with_probes()
    agent = ComplianceOfficerAgent(StubLlm(reply="uncertain"))
    result = run_agent(harness, agent, _ctx(policy_violations=1, risk_score=0.6))
    assert result.decision.action is DecisionAction.ALERT
    assert result.decision.auto_enforced is False         # below ALERT threshold → human review
    assert len(review.items) == 1


def test_no_violations_allows():
    harness, *_ = _harness_with_probes()
    agent = ComplianceOfficerAgent(StubLlm(reply="clean"))
    result = run_agent(harness, agent, _ctx(policy_violations=0, risk_score=0.0))
    assert result.decision.action is DecisionAction.ALLOW
    assert result.status == "completed"


# -- kill switch (spec §7.6) -----------------------------------------------------------------
def test_kill_switch_routes_everything_to_human():
    harness, audit, review, obs, kill = _harness_with_probes()
    kill.engage()
    agent = ComplianceOfficerAgent(StubLlm(reply="x"))
    result = run_agent(harness, agent, _ctx(policy_violations=3, risk_score=0.99))
    assert result.decision.auto_enforced is False
    assert review.items[0].reason == "kill_switch"


# -- unauthorized tool is refused + audited (spec §5) ----------------------------------------
class _ToolHungryAgent(PhaseAgent):
    name = "tool-hungry"
    authority_level = AuthorityLevel.ALERT
    capabilities = frozenset({DecisionAction.ALERT, DecisionAction.DEFER})

    def decide(self, ctx, tools: ToolInvoker) -> Decision:
        tools.call("secret_store", {})  # never granted → refused inside run
        return Decision(DecisionAction.ALERT, 0.9, "should not reach here")


def test_unauthorized_tool_is_refused_and_recorded():
    harness, audit, review, obs, _ = _harness_with_probes()
    result = run_agent(harness, _ToolHungryAgent(StubLlm()), _ctx())
    assert result.decision.action is DecisionAction.DEFER   # safe failure default
    assert any(e.kind == "tool_not_authorized" for e in audit.security_events)


# -- structlog audit redacts PII (spec §7.3) -------------------------------------------------
class _CapturingLogger:
    def __init__(self):
        self.records: list[tuple[str, dict]] = []

    def info(self, event, **kw):
        self.records.append((event, kw))

    warning = info
    error = info


def test_structlog_audit_redacts_pii():
    from datetime import datetime, timezone

    from agent_harness.ports.governance import AuditEntry

    log = _CapturingLogger()
    audit = StructlogAudit(logger=log)
    audit.record(AuditEntry(
        agent_name="a", tenant_id="t", action="ALERT", confidence=0.9, auto_enforced=False,
        rationale="reach me at ceo@acme.com", outcome="human-review", correlation_id="c",
        recorded_at=datetime.now(timezone.utc),
    ))
    (_event, kw) = log.records[0]
    assert "ceo@acme.com" not in kw["rationale"]
    assert "[REDACTED_EMAIL]" in kw["rationale"]


def test_flag_kill_switch_toggles():
    ks = FlagKillSwitch()
    assert ks.is_engaged() is False
    ks.engage()
    assert ks.is_engaged() is True
