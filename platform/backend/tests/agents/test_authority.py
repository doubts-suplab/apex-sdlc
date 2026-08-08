"""The authority model surfaces per-phase confidence thresholds and the G-5 rule.

These assert structural governance properties (not hardcoded threshold numbers, which the harness owns):
SUGGEST phases never auto-enforce (threshold is None — gate rule G-5), and auto-enforcing phases carry a
real numeric threshold in [0, 1].
"""

from __future__ import annotations

from app.agents.authority import authority_model, confidence_threshold
from app.agents.catalog import PHASE_CATALOG, spec_for


def test_suggest_phases_never_auto_enforce_g5() -> None:
    # Requirements/Architecture/Testing/Docs are SUGGEST — they can never auto-enforce (G-5).
    for phase in ("requirements", "architecture", "testing", "docs"):
        spec = spec_for(phase)
        assert spec.authority.name == "SUGGEST"
        assert spec.auto_enforces is False
        assert confidence_threshold(spec) is None


def test_auto_enforcing_phases_carry_a_numeric_threshold() -> None:
    # Development (ALERT), CI/CD (RATE_LIMIT), Governance (BLOCK) can auto-enforce → real threshold.
    for phase in ("development", "cicd", "governance"):
        spec = spec_for(phase)
        assert spec.auto_enforces is True
        threshold = confidence_threshold(spec)
        assert threshold is not None
        assert 0.0 <= threshold <= 1.0


def test_authority_model_shape() -> None:
    model = authority_model()
    assert "G-5" in model["gate_rule"]
    # The ladder runs weakest→strongest and includes the SUGGEST boundary.
    ladder = model["authority_ladder"]
    assert "SUGGEST" in ladder and "BLOCK" in ladder
    assert ladder.index("SUGGEST") < ladder.index("BLOCK")
    # One entry per catalog phase, each with the surfaced fields.
    assert len(model["phases"]) == len(PHASE_CATALOG)
    for entry in model["phases"]:
        assert set(entry) == {"phase", "label", "authority", "auto_enforces", "confidence_threshold", "note"}
        if entry["auto_enforces"]:
            assert entry["confidence_threshold"] is not None
            assert "≥" in entry["note"]
        else:
            assert entry["confidence_threshold"] is None
            assert "G-5" in entry["note"]
