"""Onboarding API — the eeik front door.

Offline and DB-free: validate an eeik manifest, resolve capability packs, generate the scaffold, and
return the registry hand-off. ``preview`` has no side effects; ``onboard`` returns the project record to
register at the Requirements phase (a DB-backed build persists it via project_service).
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Query

from app.db.session import DbSession
from app.onboarding.eeik_engine import select_engine
from app.onboarding.manifest import ProjectManifest
from app.onboarding.questions import load_questions
from app.onboarding.service import onboard as onboard_project
from app.onboarding.service import registration_payload
from app.schemas.project import ProjectCreate
from app.services.project_service import ProjectService

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.get("/questions", summary="Onboarding question sets (drives the wizard)")
async def get_questions() -> dict[str, Any]:
    """Return the eeik onboarding question sets, in wizard order."""
    return {"questions": load_questions()}


@router.post("/preview", summary="Preview onboarding — resolve packs + scaffold, no side effects")
async def preview(manifest: ProjectManifest) -> dict[str, Any]:
    """Validate a manifest and return the resolved packs + generated scaffold, without registering.

    Uses the real eeik-bootstrap engine when ``EEIK_ENGINE_PATH`` is configured, else the vendored one.
    """
    return onboard_project(manifest, engine=select_engine()).to_dict()


@router.post("/", summary="Onboard a project — scaffold + registry hand-off")
async def onboard(
    manifest: ProjectManifest,
    db: DbSession,
    organisation_id: Annotated[uuid.UUID | None, Query()] = None,
) -> dict[str, Any]:
    """Onboard: validate + scaffold, and return the registry hand-off.

    When ``organisation_id`` is supplied, the onboarded project is **persisted** as a Project row at the
    Requirements phase and its id is returned; otherwise the flow is offline/DB-free.
    """
    result = onboard_project(manifest, engine=select_engine())
    reg = registration_payload(result)
    body: dict[str, Any] = {**result.to_dict(), "registration": reg}
    if organisation_id is not None:
        project = await ProjectService(db).create(
            ProjectCreate(
                organisation_id=organisation_id,
                name=reg["name"],
                slug=reg["slug"],
                description=reg["description"],
                project_type=reg["project_type"],
                current_phase=reg["current_phase"],
                status=reg["status"],
            )
        )
        await db.commit()
        body["project_id"] = str(project.id)
    return body
