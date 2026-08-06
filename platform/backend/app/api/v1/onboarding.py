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
from app.onboarding.manifest import ProjectManifest
from app.onboarding.questions import load_questions
from app.onboarding.repo_bootstrap import bootstrap_plan
from app.onboarding.repo_generator import _slug, generate_repo_tree
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
    """Validate a manifest and return the resolved packs + generated scaffold, without registering."""
    return onboard_project(manifest).to_dict()


@router.post("/repo-tree", summary="Emit the full scaffolded repository tree from a manifest")
async def repo_tree(manifest: ProjectManifest) -> dict[str, Any]:
    """Return the emitted repository as ``{path: content}`` plus a GitHub bootstrap dry-run.

    Deterministic and offline — the same tree a live build would commit to a new GitHub repo.
    """
    result = onboard_project(manifest)
    tree = generate_repo_tree(result, manifest)
    slug = _slug(manifest.project.name)
    return {
        "project": manifest.project.name,
        "file_count": len(tree),
        "files": tree,
        "bootstrap": bootstrap_plan(manifest.project.owner or "acme", slug, tree),
    }


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
    result = onboard_project(manifest)
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
