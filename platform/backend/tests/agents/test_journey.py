"""Orchestrator / reference-journey tests.

Proves the full lifecycle runs on the harness: all seven phases execute in order, each produces
artifacts, the harness sets enforcement (a mix of auto-enforced and human-review), and the confidence
gate is never bypassed. Self-contained (no DB / FastAPI) — run with
``pytest --noconftest tests/agents/test_journey.py``.
"""

from __future__ import annotations

from agent_harness.adapters import StubLlm

from app.agents import PHASE_ORDER, phases_for_persona, run_reference_journey
from app.agents.catalog import PERSONAS
from app.integrations.llm.stub_provider import StubLLMProvider


def test_journey_runs_all_phases_in_order():
    result = run_reference_journey(StubLlm(reply="ok"))
    assert [p.phase for p in result.phases] == list(PHASE_ORDER)
    assert result.stats["phase_count"] == 7


def test_journey_produces_artifacts_and_no_gate_bypass():
    result = run_reference_journey(StubLLMProvider())
    assert result.stats["artifact_count"] >= 14          # every phase emits at least two, most three
    assert all(p.artifacts for p in result.phases)
    # spec §4.2 — the gate must never be bypassed.
    assert result.stats["confidence_gate_bypass_total"] == 0
    assert result.stats["audit_entries"] == 7            # one append-only audit entry per phase


def test_journey_mixes_auto_enforced_and_human_review():
    result = run_reference_journey(StubLLMProvider())
    outcomes = {p.phase: p.outcome for p in result.phases}
    # AI drafts, humans approve: the four SUGGEST phases route to a human.
    assert outcomes["requirements"] == "human-review"
    assert outcomes["architecture"] == "human-review"
    assert outcomes["testing"] == "human-review"
    assert outcomes["docs"] == "human-review"
    # Higher-authority phases can auto-enforce when confident.
    assert outcomes["development"] == "auto-enforced"
    assert outcomes["cicd"] == "auto-enforced"
    assert result.stats["auto_enforced_count"] >= 2
    assert result.stats["human_review_count"] >= 4


def test_every_persona_has_at_least_one_phase():
    for persona in PERSONAS:
        assert phases_for_persona(persona), f"persona {persona} owns/contributes to no phase"


def test_reference_journey_is_serialisable():
    result = run_reference_journey(StubLLMProvider())
    data = result.to_dict()
    assert set(data) == {"project", "phases", "stats"}
    assert data["project"]["slug"] == "refund-service"
    first = data["phases"][0]
    assert {"phase", "persona", "authority", "action", "auto_enforced", "artifacts"} <= set(first)
