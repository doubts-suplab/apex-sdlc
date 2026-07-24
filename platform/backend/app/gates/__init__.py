"""APEX phase-gate engine — makes the spec-driven spine enforceable.

Each SDLC phase produces an artifact ("spec"); a phase cannot advance until its gate passes: its required
artifacts are present, its spec is approved (an auto-enforced decision counts; a human-review decision
needs explicit approval), and the run never bypassed the confidence gate. Pure and offline — the engine
takes explicit inputs and returns a ``GateResult``; DB persistence of evaluations is a separate concern.
"""

from __future__ import annotations

from .criteria import GateCriteria, default_criteria
from .engine import GateCheck, GateResult, evaluate_gate, evaluate_journey

__all__ = [
    "GateCriteria",
    "default_criteria",
    "GateCheck",
    "GateResult",
    "evaluate_gate",
    "evaluate_journey",
]
