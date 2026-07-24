"""Onboarding service — validate a manifest, generate the scaffold, hand off to the APEX registry.

Pure and offline: no DB, no network. The API layer persists the registration payload via
``project_service`` when a database is available; the demo and tests use this core directly.
"""

from __future__ import annotations

import re
from typing import Any

from app.agents.catalog import PHASE_ORDER

from .manifest import ProjectManifest
from .scaffold import OnboardingResult, build_scaffold

# The onboarded project enters the spec-driven spine at the first SDLC phase (single source of truth).
ENTRY_PHASE = PHASE_ORDER[0]  # "requirements"


def onboard(manifest: ProjectManifest | dict[str, Any]) -> OnboardingResult:
    """Validate the manifest and produce the onboarding scaffold, positioned at the entry phase."""
    if not isinstance(manifest, ProjectManifest):
        manifest = ProjectManifest.from_dict(manifest)
    return build_scaffold(manifest, entry_phase=ENTRY_PHASE)


def registration_payload(result: OnboardingResult) -> dict[str, Any]:
    """The project record to register in the APEX registry after onboarding."""
    m = result.manifest
    project = m.get("project", {})
    return {
        "name": result.project_name,
        "slug": _slugify(result.project_name),
        "description": project.get("description") or None,
        "project_type": _apex_project_type(m),
        "current_phase": result.entry_phase,
        "status": "active",
    }


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "project"


def _apex_project_type(manifest: dict[str, Any]) -> str:
    """Map the eeik stack to an APEX project_type enum (see frontend types/project.ts)."""
    tech = manifest.get("technology", {})
    backend = (tech.get("backend") or {}).get("language", "")
    framework = (tech.get("backend") or {}).get("framework", "")
    frontend = (tech.get("frontend") or {}).get("framework", "none")
    if framework == "spring-boot":
        return "spring-boot"
    if backend == "python":
        return "python"
    if frontend == "angular":
        return "angular"
    return "generic"
