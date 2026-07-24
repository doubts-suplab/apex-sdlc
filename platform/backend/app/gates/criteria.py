"""Gate criteria — what a phase must satisfy to transition, derived from the catalog.

Default criteria come straight from the phase's expected artifacts (``PhaseSpec.artifacts``), so the gate
can never drift from the agent catalog. Criteria are plain data, so a project can tighten a gate later
(e.g. add a coverage threshold) without touching the engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.agents.catalog import spec_for


@dataclass(frozen=True)
class GateCriteria:
    """The criteria a phase's gate evaluates."""

    phase: str
    required_artifacts: tuple[str, ...] = ()
    require_spec_approved: bool = True
    require_no_bypass: bool = True
    extra: dict[str, object] = field(default_factory=dict)  # future: min_coverage, approvers, policies


def default_criteria(phase: str) -> GateCriteria:
    """Default gate criteria for a phase: its catalog-expected artifacts + spec approval + no bypass."""
    spec = spec_for(phase)  # raises KeyError for an unknown phase
    return GateCriteria(phase=phase, required_artifacts=tuple(spec.artifacts))
