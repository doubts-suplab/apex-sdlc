from __future__ import annotations

from halo_agent_harness import DecisionAction, ToolRegistry

from app.agents.context import AgentContext
from app.agents.planning import PlanningAgent
from app.agents.runtime import build_apex_harness, run_agent
from app.integrations.llm.stub_provider import StubLLMProvider


def _run(brief: str) -> tuple[PlanningAgent, object]:
    agent = PlanningAgent(StubLLMProvider())
    harness = build_apex_harness(registry=ToolRegistry())
    ctx = AgentContext(project_id="p1", phase="planning", actor_id="u1", inputs={"brief": brief})
    result = run_agent(harness, agent, ctx)
    return agent, result


def test_planning_agent_proposes_deliveries_at_suggest() -> None:
    agent, result = _run("Ship the export API. Add retention purge; wire CI.")

    # SUGGEST authority — the harness never auto-enforces a plan.
    assert result.decision.action == DecisionAction.SUGGEST
    assert result.decision.auto_enforced is False

    proposed = agent.proposed()
    assert len(proposed) == 3
    titles = [d["title"] for d in proposed]
    assert titles[0] == "Ship the export API"
    assert all(d["priority"] in {"low", "medium", "high", "critical"} for d in proposed)
    assert all(isinstance(d["estimate_points"], int) for d in proposed)
    # a human-readable plan artifact rides alongside
    assert any(a["name"] == "delivery-plan.md" for a in result.artifacts)


def test_planning_agent_empty_brief_yields_default_backlog() -> None:
    agent, result = _run("")

    assert result.decision.action == DecisionAction.SUGGEST
    assert len(agent.proposed()) == 3  # default starter backlog, never empty


def test_planning_agent_caps_backlog_size() -> None:
    brief = ". ".join(f"Goal {i}" for i in range(20))
    agent, _ = _run(brief)
    assert len(agent.proposed()) == 5  # _MAX_DELIVERIES
