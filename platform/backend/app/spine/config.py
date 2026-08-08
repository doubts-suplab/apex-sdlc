"""The `SpineConfig` value object + its validating constructor.

Pure data + validation, no I/O — safe to build anywhere and cheap to test. A `SpineConfig` names an
ordered subset of the catalog phases and any per-phase gate overrides; the orchestrator runs only the
enabled phases and the gate engine evaluates each with the configured criteria.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from app.agents.catalog import PHASE_ORDER
from app.gates.criteria import GateCriteria, default_criteria


class SpineConfigError(ValueError):
    """Raised when a requested spine is not a valid subset of the catalog phases."""


@dataclass(frozen=True)
class PhaseGateOverride:
    """Per-phase gate customisation. A ``None`` field falls back to the catalog default for that phase.

    Lets an org relax or tighten a single gate — e.g. drop the human-approval requirement on a phase it
    wants advisory-only (``require_spec_approved=False``), or narrow the required artifacts.
    """

    required_artifacts: tuple[str, ...] | None = None
    require_spec_approved: bool | None = None
    require_no_bypass: bool | None = None


@dataclass(frozen=True)
class SpineConfig:
    """A configurable SDLC spine: an ordered subset of catalog phases + optional per-phase gate overrides.

    The default (:func:`default_spine`) is the full seven-phase spine with catalog-derived gates, so an
    org that wants the whole model changes nothing.
    """

    phases: tuple[str, ...]
    gate_overrides: Mapping[str, PhaseGateOverride] = field(default_factory=dict)

    def includes(self, phase: str) -> bool:
        return phase in self.phases

    def criteria_for(self, phase: str) -> GateCriteria:
        """The gate criteria for ``phase`` — catalog default, with any override applied on top."""
        base = default_criteria(phase)
        override = self.gate_overrides.get(phase)
        if override is None:
            return base
        return GateCriteria(
            phase=phase,
            required_artifacts=(
                base.required_artifacts
                if override.required_artifacts is None
                else tuple(override.required_artifacts)
            ),
            require_spec_approved=(
                base.require_spec_approved
                if override.require_spec_approved is None
                else override.require_spec_approved
            ),
            require_no_bypass=(
                base.require_no_bypass
                if override.require_no_bypass is None
                else override.require_no_bypass
            ),
            extra=base.extra,
        )


def default_spine() -> SpineConfig:
    """The full seven-phase spine with catalog-derived gates (the reference/POC behaviour)."""
    return SpineConfig(phases=PHASE_ORDER)


def build_spine(
    phases: Iterable[str] | None = None,
    *,
    gate_overrides: Mapping[str, PhaseGateOverride] | None = None,
) -> SpineConfig:
    """Validate and canonicalise a requested spine.

    - ``phases`` must be a non-empty subset of the catalog phases; an unknown phase is an error.
    - Duplicates are collapsed and the result is ordered by the canonical ``PHASE_ORDER`` (so upstream
      phases always precede the phases that depend on them — the spine can be trimmed, not reordered).
    - A gate override may only target an enabled phase.

    ``phases=None`` yields the full default spine.
    """
    if phases is None:
        selected = PHASE_ORDER
    else:
        requested = list(phases)
        unknown = [p for p in requested if p not in PHASE_ORDER]
        if unknown:
            raise SpineConfigError(
                f"unknown phase(s): {', '.join(unknown)}; valid phases: {', '.join(PHASE_ORDER)}"
            )
        wanted = set(requested)
        if not wanted:
            raise SpineConfigError("a spine must enable at least one phase")
        # Canonical order + dedup: keep catalog order so dependencies precede dependents.
        selected = tuple(p for p in PHASE_ORDER if p in wanted)

    overrides = dict(gate_overrides or {})
    stray = [p for p in overrides if p not in selected]
    if stray:
        raise SpineConfigError(f"gate override(s) target disabled phase(s): {', '.join(stray)}")
    return SpineConfig(phases=selected, gate_overrides=overrides)
