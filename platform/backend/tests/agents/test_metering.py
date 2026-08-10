"""Metering tests — pricing, per-run token/latency capture, and journey.json determinism.

Self-contained: ``pytest --noconftest tests/agents/test_metering.py``.
"""

from __future__ import annotations

from halo_agent_harness import ToolRegistry
from halo_agent_harness.adapters import StubLlm

from app.agents import RequirementsAgent, build_apex_harness, run_agent
from app.agents.context import AgentContext
from app.agents.orchestrator import run_reference_journey
from app.agents.pricing import cost_usd
from app.integrations.llm.stub_provider import StubLLMProvider


# -- pricing ------------------------------------------------------------------------------------
def test_known_model_priced():
    # 1M input @ $15 + 1M output @ $75 = $90 for claude-opus-4-8.
    assert cost_usd("claude-opus-4-8", 1_000_000, 1_000_000) == 90.0


def test_unknown_and_stub_models_are_free():
    assert cost_usd("stub-1", 5_000, 5_000) == 0.0
    assert cost_usd("", 10, 10) == 0.0


# -- per-run capture ----------------------------------------------------------------------------
def test_run_captures_tokens_latency_and_model():
    agent = RequirementsAgent(StubLlm(reply="a substantive reply " * 30))
    ctx = AgentContext(project_id="p", phase="requirements", actor_id="ba",
                       inputs={"feature_name": "X", "brief": "b"}, run_id="p:requirements")
    result = run_agent(build_apex_harness(registry=ToolRegistry()), agent, ctx)
    assert result.token_usage.input_tokens > 0
    assert result.token_usage.output_tokens > 0
    assert result.model == "stub-1"
    assert result.duration_ms >= 0.0


def test_reference_journey_meters_every_phase():
    journey = run_reference_journey(StubLLMProvider())
    assert all(p.input_tokens > 0 for p in journey.phases)
    assert all(p.model for p in journey.phases)
    # stub is free → deterministic $0 cost.
    assert sum(p.cost_usd for p in journey.phases) == 0.0


def test_metering_is_absent_from_serialized_journey():
    # journey.json must stay deterministic — nondeterministic/metering fields are not serialized.
    phase = run_reference_journey(StubLLMProvider()).to_dict()["phases"][0]
    for excluded in ("input_tokens", "output_tokens", "cost_usd", "duration_ms", "model", "provider"):
        assert excluded not in phase
