"""Onboarding API — the eeik front door.

Offline and DB-free: validate an eeik manifest, resolve capability packs, generate the scaffold, and
return the registry hand-off. ``preview`` has no side effects; ``onboard`` returns the project record to
register at the Requirements phase (a DB-backed build persists it via project_service).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.onboarding.manifest import ProjectManifest
from app.onboarding.questions import load_questions
from app.onboarding.service import onboard as onboard_project
from app.onboarding.service import registration_payload

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.get("/questions", summary="Onboarding question sets (drives the wizard)")
async def get_questions() -> dict[str, Any]:
    """Return the eeik onboarding question sets, in wizard order."""
    return {"questions": load_questions()}


@router.post("/preview", summary="Preview onboarding — resolve packs + scaffold, no side effects")
async def preview(manifest: ProjectManifest) -> dict[str, Any]:
    """Validate a manifest and return the resolved packs + generated scaffold, without registering."""
    return onboard_project(manifest).to_dict()


@router.post("/", summary="Onboard a project — scaffold + registry hand-off")
async def onboard(manifest: ProjectManifest) -> dict[str, Any]:
    """Onboard: validate + scaffold, and return the project record to register at the Requirements phase."""
    result = onboard_project(manifest)
    return {**result.to_dict(), "registration": registration_payload(result)}
