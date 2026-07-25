"""Onboarding service — validate a manifest, generate the scaffold, hand off to the APEX registry.

Pure and offline: no DB, no network. The API layer persists the registration payload via
``project_service`` when a database is available; the demo and tests use this core directly.
"""

from __future__ import annotations

import re
from typing import Any

from app.agents.catalog import PHASE_ORDER

from .eeik_engine import EeikEngine, get_engine
from .manifest import ProjectManifest
from .scaffold import OnboardingResult, build_scaffold

# The onboarded project enters the spec-driven spine at the first SDLC phase (single source of truth).
ENTRY_PHASE = PHASE_ORDER[0]  # "requirements"


class ManifestInvalidError(ValueError):
    """Raised when the real eeik engine rejects a manifest during onboarding."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors) or "manifest is invalid")


def onboard(manifest: ProjectManifest | dict[str, Any]) -> OnboardingResult:
    """Validate the manifest and produce the onboarding scaffold, positioned at the entry phase."""
    if not isinstance(manifest, ProjectManifest):
        manifest = ProjectManifest.from_dict(manifest)
    return build_scaffold(manifest, entry_phase=ENTRY_PHASE)


def onboard_with_eeik(
    manifest: ProjectManifest | dict[str, Any],
    *,
    mode: str | None = None,
    engine: EeikEngine | None = None,
) -> tuple[OnboardingResult, dict[str, Any]]:
    """Onboard, using the real eeik engine as the authority when it is available.

    When an eeik engine (SDK or MCP) is reachable, the manifest is validated against eeik's *canonical*
    schema + governance rules (raising ``ManifestInvalidError`` on hard errors) and eeik's authoritative
    pack resolution is recorded. When it is not, APEX falls back to its vendored offline path and says so
    in the provenance. Either way the deterministic scaffold is produced.

    Returns ``(result, provenance)`` where provenance records which engine authored the decision.
    """
    # Validate the manifest *as provided* against eeik's canonical schema. When callers pass an
    # already-built ProjectManifest we dump it, but a raw dict is validated verbatim — APEX's Pydantic
    # model is an internal scaffolding representation, not the schema authority (eeik owns that).
    prebuilt = manifest if isinstance(manifest, ProjectManifest) else None
    manifest_dict = prebuilt.model_dump(exclude_none=True) if prebuilt else manifest

    engine = engine or get_engine(mode)
    provenance: dict[str, Any] = {
        "engine": engine.mode if engine else "vendored",
        "eeik_available": engine is not None,
        "validation": None,
        "eeik_resolved_packs": None,
    }

    # eeik is the schema authority: validate through it *before* APEX builds its Pydantic model, so a
    # bad manifest fails with ManifestInvalidError (eeik's errors), not an internal model error.
    if engine is not None:
        validation = engine.validate(manifest_dict)
        provenance["validation"] = validation
        if not validation.get("valid", False):
            raise ManifestInvalidError(validation.get("errors", []))
        provenance["eeik_resolved_packs"] = engine.resolve_packs(manifest_dict)

    project_manifest = prebuilt if prebuilt is not None else ProjectManifest.from_dict(manifest)
    return onboard(project_manifest), provenance


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
