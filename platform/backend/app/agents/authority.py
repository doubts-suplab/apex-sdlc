"""The authority ladder + per-phase confidence thresholds — surfaced from the harness gate.

This is the read model behind "surface confidence thresholds + the G-5 rule". It derives, per SDLC
phase, the harness confidence-gate threshold the agent must clear to auto-enforce, and makes the
founding rule explicit: **SUGGEST/OBSERVE authority can never auto-enforce (gate rule G-5)** — those
phases always route to a human, so "AI drafts; humans approve" is a property of the authority ladder,
not a convention.

Everything is catalog-derived (`PHASE_CATALOG`) and harness-derived (`ConfidenceGate`), so it can never
drift from the governed behaviour. No DB, no network — safe to serve offline.
"""

from __future__ import annotations

from typing import Any

from halo_agent_harness import AuthorityLevel, ConfidenceGate

from .catalog import PHASE_CATALOG, PhaseSpec

# Gate rule G-5 (harness spec): SUGGEST and OBSERVE authority can never auto-enforce.
GATE_RULE_G5 = (
    "G-5 — SUGGEST and OBSERVE authority can never auto-enforce: those phases always route to a human, "
    "regardless of confidence. Higher authorities (ALERT, RATE_LIMIT, BLOCK) auto-enforce only when the "
    "agent's confidence clears the harness confidence-gate threshold for that authority."
)

# The harness owns the thresholds; one shared gate instance reads them.
_GATE = ConfidenceGate()


def confidence_threshold(spec: PhaseSpec) -> float | None:
    """The confidence an agent must clear to auto-enforce this phase, or ``None`` if it never can.

    ``None`` is the machine-readable form of gate rule G-5: a SUGGEST/OBSERVE phase has no auto-enforce
    threshold because it is always routed to a human.
    """
    if not spec.auto_enforces:
        return None
    try:
        return round(float(_GATE.threshold_for(spec.authority)), 2)
    except Exception:  # pragma: no cover - defensive: unknown authority in the harness gate
        return None


def _phase_authority(spec: PhaseSpec) -> dict[str, Any]:
    threshold = confidence_threshold(spec)
    if threshold is None:
        note = "Never auto-enforces — always routed to a human (G-5)."
    else:
        note = f"Auto-enforces only at confidence ≥ {threshold:.2f}; below that a human decides."
    return {
        "phase": spec.phase,
        "label": spec.label,
        "authority": spec.authority.name,
        "auto_enforces": spec.auto_enforces,
        "confidence_threshold": threshold,
        "note": note,
    }


def _authority_ladder() -> list[str]:
    """The authority levels from weakest to strongest (OBSERVE … BLOCK)."""
    return [level.name for level in sorted(AuthorityLevel)]


def authority_model() -> dict[str, Any]:
    """The full governance read model: the G-5 rule, the authority ladder, and per-phase thresholds."""
    return {
        "gate_rule": GATE_RULE_G5,
        "authority_ladder": _authority_ladder(),
        "phases": [_phase_authority(spec) for spec in PHASE_CATALOG],
    }
