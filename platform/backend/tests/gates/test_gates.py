"""Phase-gate engine tests — self-contained (no DB / FastAPI).

Run with ``pytest --noconftest tests/gates/test_gates.py``.
"""

from __future__ import annotations

from agent_harness.adapters import StubLlm

from app.agents.orchestrator import run_reference_journey
from app.gates.criteria import default_criteria
from app.gates.engine import evaluate_gate, evaluate_journey


# -- single-gate rules ---------------------------------------------------------------------------
def test_auto_enforced_phase_with_artifacts_passes():
    r = evaluate_gate(
        "development",
        produced_artifacts=["pr-review.md", "quality-report.md"],
        auto_enforced=True,
    )
    assert r.status == "passed"


def test_suggest_phase_pending_until_approved():
    kwargs = dict(produced_artifacts=["user-stories.md", "gap-analysis.md"], auto_enforced=False)
    pending = evaluate_gate("requirements", **kwargs)
    assert pending.status == "pending" and "approval" in pending.reason.lower()
    approved = evaluate_gate("requirements", approved=True, **kwargs)
    assert approved.status == "passed"


def test_missing_artifact_fails():
    r = evaluate_gate("requirements", produced_artifacts=["user-stories.md"], auto_enforced=True)
    assert r.status == "failed"
    assert any(c.name == "required_artifacts" and not c.passed for c in r.checks)


def test_gate_bypass_fails_even_if_approved():
    r = evaluate_gate(
        "development",
        produced_artifacts=["pr-review.md", "quality-report.md"],
        auto_enforced=True,
        bypass_total=1,
    )
    assert r.status == "failed"
    assert any(c.name == "no_gate_bypass" and not c.passed for c in r.checks)


def test_default_criteria_come_from_catalog():
    crit = default_criteria("architecture")
    assert "ADR-0001-refund-service.md" in crit.required_artifacts


# -- full journey --------------------------------------------------------------------------------
def test_journey_blocks_at_requirements_with_no_approvals():
    journey = run_reference_journey(StubLlm(reply="ok"))
    res = evaluate_journey(journey, set())
    assert res["blocking_phase"] == "requirements"
    assert res["all_passed"] is False
    by_phase = {g["phase"]: g["status"] for g in res["gates"]}
    # Auto-enforced phases pass without approval; SUGGEST phases are pending.
    assert by_phase["development"] == "passed"
    assert by_phase["cicd"] == "passed"
    assert by_phase["requirements"] == "pending"


def test_journey_clears_when_all_human_review_specs_approved():
    journey = run_reference_journey(StubLlm(reply="ok"))
    human_review = {p.phase for p in journey.phases if not p.auto_enforced}
    res = evaluate_journey(journey, human_review)
    assert res["all_passed"] is True
    assert res["blocking_phase"] is None
    assert all(g["status"] == "passed" for g in res["gates"])
