"""Members + Teams API — the persona↔identity administration surface.

Teams live under an organisation; members hold a persona on a project. Writes are Lead/CISO-gated
(project administration); reads are open (consistent with the other read endpoints today). This is the
CRUD the RBAC layer needs so a token subject can be reconciled against a real project member.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException

from app.core.security import Principal, require_persona
from app.db.session import DbSession
from app.schemas.team import MemberCreate, TeamCreate
from app.services.member_service import MemberService
from app.services.organisation_service import OrganisationService
from app.services.project_service import ProjectService

router = APIRouter(tags=["members"])

_ADMIN_PERSONAS = ("lead", "ciso")


def _member_svc(db: DbSession) -> MemberService:
    return MemberService(db)


Svc = Annotated[MemberService, Depends(_member_svc)]


async def _require_org(db: DbSession, organisation_id: uuid.UUID) -> None:
    if await OrganisationService(db).get_by_id(organisation_id) is None:
        raise HTTPException(
            status_code=404,
            detail={
                "type": "https://apex.example.com/problems/organisation-not-found",
                "title": "Organisation Not Found",
                "status": 404,
                "detail": f"No organisation with id={organisation_id} exists.",
            },
        )


async def _require_project(db: DbSession, project_id: uuid.UUID) -> None:
    if await ProjectService(db).get_by_id(project_id) is None:
        raise HTTPException(
            status_code=404,
            detail={
                "type": "https://apex.example.com/problems/project-not-found",
                "title": "Project Not Found",
                "status": 404,
                "detail": f"No project with id={project_id} exists.",
            },
        )


def _team_dict(team: Any) -> dict[str, Any]:
    return {
        "id": str(team.id),
        "organisation_id": str(team.organisation_id),
        "name": team.name,
        "slug": team.slug,
        "description": team.description,
    }


def _member_dict(m: Any) -> dict[str, Any]:
    return {
        "id": str(m.id),
        "project_id": str(m.project_id),
        "team_id": str(m.team_id) if m.team_id else None,
        "subject": m.subject,
        "persona": m.persona,
        "display_name": m.display_name,
        "email": m.email,
    }


# -- teams (org-scoped) ---------------------------------------------------------------------------
@router.post("/organisations/{organisation_id}/teams", summary="Create a team")
async def create_team(
    organisation_id: uuid.UUID,
    payload: TeamCreate,
    db: DbSession,
    svc: Svc,
    _p: Annotated[Principal, Depends(require_persona(*_ADMIN_PERSONAS))],
) -> dict[str, Any]:
    await _require_org(db, organisation_id)
    team = await svc.create_team(organisation_id, payload)
    return _team_dict(team)


@router.get("/organisations/{organisation_id}/teams", summary="List an org's teams")
async def list_teams(organisation_id: uuid.UUID, db: DbSession, svc: Svc) -> dict[str, Any]:
    await _require_org(db, organisation_id)
    teams = await svc.list_teams(organisation_id)
    return {"total": len(teams), "items": [_team_dict(t) for t in teams]}


# -- members (project-scoped) ---------------------------------------------------------------------
@router.post("/projects/{project_id}/members", summary="Add a member (persona holder) to a project")
async def add_member(
    project_id: uuid.UUID,
    payload: MemberCreate,
    db: DbSession,
    svc: Svc,
    _p: Annotated[Principal, Depends(require_persona(*_ADMIN_PERSONAS))],
) -> dict[str, Any]:
    await _require_project(db, project_id)
    member = await svc.add_member(project_id, payload)
    return _member_dict(member)


@router.get("/projects/{project_id}/members", summary="List a project's members")
async def list_members(project_id: uuid.UUID, db: DbSession, svc: Svc) -> dict[str, Any]:
    await _require_project(db, project_id)
    members = await svc.list_members(project_id)
    return {"total": len(members), "items": [_member_dict(m) for m in members]}
