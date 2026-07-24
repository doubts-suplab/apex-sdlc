"""The phase-gate engine — pure evaluation of whether a phase may transition.

A gate is ``passed`` only when every hard check holds (required artifacts present, no confidence-gate
bypass) and the spec is approved. A spec is approved when the phase's decision auto-enforced, or a human
explicitly approved it; otherwise the gate is ``pending`` (the spine blocks here, awaiting a human). A
missing artifact or a gate bypass makes the gate ``failed``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .criteria import GateCriteria, default_criteria

PASSED = "passed"
PENDING = "pending"
FAILED = "failed"


@dataclass
class GateCheck:
    name: str
    passed: bool
    detail: str


@dataclass
class GateResult:
    phase: str
    status: str  # passed | pending | failed
    checks: list[GateCheck] = field(default_factory=list)
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_gate(
    phase: str,
    *,
    produced_artifacts: list[str],
    auto_enforced: bool,
    approved: bool = False,
    bypass_total: int = 0,
    criteria: GateCriteria | None = None,
) -> GateResult:
    """Evaluate one phase's gate. Pure — all inputs are explicit."""
    crit = criteria or default_criteria(phase)
    checks: list[GateCheck] = []

    produced = set(produced_artifacts)
    missing = [a for a in crit.required_artifacts if a not in produced]
    artifacts_ok = not missing
    checks.append(
        GateCheck(
            name="required_artifacts",
            passed=artifacts_ok,
            detail="all present" if artifacts_ok else f"missing: {', '.join(missing)}",
        )
    )

    bypass_ok = bypass_total == 0
    if crit.require_no_bypass:
        checks.append(
            GateCheck(
                name="no_gate_bypass",
                passed=bypass_ok,
                detail="confidence_gate_bypass_total == 0" if bypass_ok else f"bypass_total={bypass_total}",
            )
        )

    spec_approved = auto_enforced or approved
    if crit.require_spec_approved:
        how = "auto-enforced" if auto_enforced else ("approved" if approved else "awaiting human approval")
        checks.append(GateCheck(name="spec_approved", passed=spec_approved, detail=how))

    # Hard failures (artifacts / bypass) dominate; an unapproved spec is a soft block (pending).
    hard_failed = not artifacts_ok or (crit.require_no_bypass and not bypass_ok)
    if hard_failed:
        status, reason = FAILED, _first_failure_reason(checks, hard=True)
    elif crit.require_spec_approved and not spec_approved:
        status, reason = PENDING, "spec awaiting human approval"
    else:
        status, reason = PASSED, "all gate criteria satisfied"

    return GateResult(phase=phase, status=status, checks=checks, reason=reason)


def evaluate_journey(journey: Any, approvals: set[str] | None = None) -> dict[str, Any]:
    """Evaluate every phase gate across a JourneyResult (or its dict), given approved phases.

    Returns ``{"gates": [GateResult...], "blocking_phase": str|None, "all_passed": bool}``. The
    ``blocking_phase`` is the first phase whose gate is not ``passed`` — where the spine halts.
    """
    approvals = approvals or set()
    phases = _journey_phases(journey)
    bypass_total = int(_journey_stats(journey).get("confidence_gate_bypass_total", 0))

    gates: list[GateResult] = []
    for ph in phases:
        gates.append(
            evaluate_gate(
                ph["phase"],
                produced_artifacts=[a["name"] for a in ph.get("artifacts", [])],
                auto_enforced=bool(ph["auto_enforced"]),
                approved=ph["phase"] in approvals,
                bypass_total=bypass_total,
            )
        )

    blocking = next((g.phase for g in gates if g.status != PASSED), None)
    return {
        "gates": [g.to_dict() for g in gates],
        "blocking_phase": blocking,
        "all_passed": blocking is None,
    }


# -- adapters over JourneyResult (dataclass) or a plain dict -------------------------------------
def _journey_phases(journey: Any) -> list[dict[str, Any]]:
    phases = getattr(journey, "phases", None)
    if phases is None:  # dict form
        return list(journey["phases"])
    out: list[dict[str, Any]] = []
    for p in phases:  # JourneyPhase dataclasses
        out.append(
            {
                "phase": p.phase,
                "auto_enforced": p.auto_enforced,
                "artifacts": p.artifacts,
            }
        )
    return out


def _journey_stats(journey: Any) -> dict[str, Any]:
    stats = getattr(journey, "stats", None)
    return stats if stats is not None else journey.get("stats", {})


def _first_failure_reason(checks: list[GateCheck], *, hard: bool) -> str:
    for c in checks:
        if not c.passed and c.name in ("required_artifacts", "no_gate_bypass"):
            return f"{c.name}: {c.detail}"
    return "gate failed"
