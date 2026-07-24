"""Real-generation path tests — agents generate artifact bodies via the LLM port with a safe fallback.

Proves: (1) a substantive completion from the provider becomes the artifact body; (2) a short reply (the
offline stub) falls back to the deterministic template — keeping the reference journey reproducible.
Self-contained (no DB / FastAPI): ``pytest --noconftest tests/agents/test_generation.py``.
"""

from __future__ import annotations

from agent_harness import ToolRegistry
from agent_harness.adapters import StubLlm

from app.agents import AgentContext, RequirementsAgent, build_apex_harness, run_agent

# A body long enough to clear _MIN_GENERATED_LEN (200) — stands in for a real provider's output.
_GENERATED = (
    "# Customer Refunds — User Stories (provider-generated)\n\n"
    "This distinctive body proves the LLM output flows into the emitted artifact rather than the "
    "deterministic template. It is deliberately longer than the offline stub's one-line reply so that "
    "PhaseAgent.generate() uses it verbatim. Feature: refunds; scenarios: eligible, expired, duplicate.\n"
)
_MARKER = "provider-generated"


def _ctx():
    return AgentContext(
        project_id="p",
        phase="requirements",
        actor_id="ba",
        inputs={"feature_name": "Customer Refunds", "brief": "Let customers self-serve refunds."},
        run_id="p:requirements",
    )


def _run(agent):
    return run_agent(build_apex_harness(registry=ToolRegistry()), agent, _ctx())


def test_substantive_completion_becomes_the_artifact():
    result = _run(RequirementsAgent(StubLlm(reply=_GENERATED)))
    stories = next(a for a in result.artifacts if a["name"] == "user-stories.md")
    assert _MARKER in stories["content"]  # the generated body was used, not the template


def test_short_reply_falls_back_to_template():
    agent = RequirementsAgent(StubLlm(reply="ok"))  # 2 chars → below the generation threshold
    result = _run(agent)
    stories = next(a for a in result.artifacts if a["name"] == "user-stories.md")
    # Falls back to the deterministic template — byte-identical to the fallback builder's output.
    assert stories["content"] == agent._stories("Customer Refunds", "Let customers self-serve refunds.")
    assert _MARKER not in stories["content"]


def test_generation_does_not_change_the_governed_decision():
    # Whichever provider is used, the phase's decision/authority are unchanged (governance is orthogonal).
    gen = _run(RequirementsAgent(StubLlm(reply=_GENERATED))).decision
    stub = _run(RequirementsAgent(StubLlm(reply="ok"))).decision
    assert gen.action == stub.action
    assert gen.auto_enforced == stub.auto_enforced is False
