"""Configurable-spine tests — trimming phases and customising gates.

Proves an org can run a lighter model (a subset of the seven phases) and tune a gate, while the default
(no spine) is unchanged. Self-contained (harness + stub LLM, no DB / FastAPI).
"""

from __future__ import annotations

import pytest

from app.agents.catalog import PHASE_ORDER
from app.agents.orchestrator import run_reference_journey
from app.gates.engine import evaluate_journey
from app.integrations.llm.stub_provider import StubLLMProvider
from app.spine import (
    PhaseGateOverride,
    SpineConfigError,
    build_spine,
    default_spine,
)


# -- config / validation (no harness needed) ---------------------------------------------------

def test_default_spine_is_the_full_catalog() -> None:
    assert default_spine().phases == PHASE_ORDER


def test_build_spine_canonicalises_order_and_dedups() -> None:
    # Requested out of order and with a duplicate → canonical catalog order, no dupes.
    spine = build_spine(["development", "requirements", "requirements"])
    assert spine.phases == ("requirements", "development")


def test_build_spine_rejects_unknown_phase() -> None:
    with pytest.raises(SpineConfigError, match="unknown phase"):
        build_spine(["requirements", "nonsense"])


def test_build_spine_rejects_empty() -> None:
    with pytest.raises(SpineConfigError):
        build_spine([])


def test_gate_override_for_disabled_phase_is_rejected() -> None:
    with pytest.raises(SpineConfigError, match="disabled phase"):
        build_spine(["requirements"], gate_overrides={"testing": PhaseGateOverride()})


def test_criteria_for_applies_override() -> None:
    spine = build_spine(
        ["requirements"],
        gate_overrides={"requirements": PhaseGateOverride(require_spec_approved=False)},
    )
    crit = spine.criteria_for("requirements")
    assert crit.require_spec_approved is False
    # Untouched fields fall back to the catalog default.
    assert crit.required_artifacts == spine.criteria_for("requirements").required_artifacts
    assert crit.require_no_bypass is True


# -- running a trimmed spine (harness + stub) --------------------------------------------------

def test_run_journey_runs_only_the_enabled_phases_in_order() -> None:
    spine = build_spine(["architecture", "requirements", "development"])
    result = run_reference_journey(StubLLMProvider(), spine=spine)
    assert [p.phase for p in result.phases] == ["requirements", "architecture", "development"]
    assert result.stats["phase_count"] == 3


def test_gates_evaluate_only_enabled_phases() -> None:
    spine = build_spine(["requirements", "architecture"])
    journey = run_reference_journey(StubLLMProvider(), spine=spine)
    report = evaluate_journey(journey, set(), spine=spine)
    assert [g["phase"] for g in report["gates"]] == ["requirements", "architecture"]


def test_gate_override_lets_a_suggest_phase_pass_without_human_approval() -> None:
    # Requirements is SUGGEST → normally pending until approved. Relaxing require_spec_approved makes the
    # gate pass with no approval — the configurable-gate escape hatch for an advisory-only phase.
    spine = build_spine(
        ["requirements"],
        gate_overrides={"requirements": PhaseGateOverride(require_spec_approved=False)},
    )
    journey = run_reference_journey(StubLLMProvider(), spine=spine)

    strict = evaluate_journey(journey, set())  # no spine → default criteria
    assert strict["gates"][0]["status"] == "pending"

    relaxed = evaluate_journey(journey, set(), spine=spine)
    assert relaxed["gates"][0]["status"] == "passed"
    assert relaxed["all_passed"] is True
