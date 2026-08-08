"""Configurable SDLC spine — which phases run, and the gate criteria that govern each.

The default spine is the full seven-phase catalog with catalog-derived gates, so nothing changes for an
org that wants the whole model (and the reference journey / committed fixtures are unaffected). An org
that wants a lighter model — "PR review only", "requirements + architecture", a relaxed gate — builds a
`SpineConfig` and threads it through `run_journey` / `evaluate_journey`.
"""

from __future__ import annotations

from .config import (
    PhaseGateOverride,
    SpineConfig,
    SpineConfigError,
    build_spine,
    default_spine,
)

__all__ = [
    "PhaseGateOverride",
    "SpineConfig",
    "SpineConfigError",
    "build_spine",
    "default_spine",
]
