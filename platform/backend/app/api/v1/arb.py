"""ARB API — the Architecture Review Board sign-off workflow.

``POST /projects/{id}/arb`` submits an architecture change for review (Architect/Lead); an ARB
approver (CISO/Lead/Architect) records a decision at ``POST /projects/{id}/arb/{arb_id}/decision``,
persisted append-only in the audit log. ``GET`` endpoints read submissions.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.core.security import Principal, require_persona
from app.db.session import DbSession
from app.models.arb import ArbSubmission
from app.services.arb_service import ArbService
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["arb"])

# Who may prepare/submit an ARB, and who sits on the board to decide it.
_SUBMIT_PERSONAS = ("architect", "lead")
_BOARD_PERSONAS = ("ciso", "lead", "architect")


def _svc(db: DbSession) -> ArbService:
    return ArbService(db)


Svc = Annotated[ArbService, Depends(_svc)]


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


class ArbSubmitRequest(BaseModel):
    """An ARB review request — the architecture change + risk prep to sign off."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1, max_length=255)
    summary: str = Field(default="", max_length=20000)


class ArbDecisionRequest(BaseModel):
    """An ARB approver's decision."""

    model_config = ConfigDict(extra="forbid")

    decision: str = Field(..., pattern="^(approve|reject|request_changes)$")
    rationale: str = Field(default="", max_length=2000)


def _arb_dict(a: ArbSubmission) -> dict[str, Any]:
    return {
        "id": str(a.id),
        "project_id": str(a.project_id),
        "title": a.title,
        "summary": a.summary,
        "status": a.status,
        "submitted_by": a.submitted_by,
        "submitter_persona": a.submitter_persona,
        "reviewed_by": a.reviewed_by,
        "reviewer_persona": a.reviewer_persona,
        "decision_rationale": a.decision_rationale,
        "decided_at": a.decided_at.isoformat() if a.decided_at else None,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


@router.post("/{project_id}/arb", summary="Submit an architecture change for ARB review")
async def submit_arb(
    project_id: uuid.UUID,
    body: ArbSubmitRequest,
    db: DbSession,
    svc: Svc,
    principal: Annotated[Principal, Depends(require_persona(*_SUBMIT_PERSONAS))],
) -> dict[str, Any]:
    await _require_project(db, project_id)
    arb = await svc.submit(
        project_id,
        title=body.title,
        summary=body.summary,
        submitted_by=principal.subject,
        submitter_persona=principal.persona,
    )
    return _arb_dict(arb)


@router.get("/{project_id}/arb", summary="List ARB submissions for a project")
async def list_arb(project_id: uuid.UUID, db: DbSession, svc: Svc) -> dict[str, Any]:
    await _require_project(db, project_id)
    items = await svc.list(project_id)
    return {"total": len(items), "items": [_arb_dict(a) for a in items]}


@router.get("/{project_id}/arb/{arb_id}", summary="Get one ARB submission")
async def get_arb(
    project_id: uuid.UUID, arb_id: uuid.UUID, db: DbSession, svc: Svc
) -> dict[str, Any]:
    await _require_project(db, project_id)
    arb = await svc.get(project_id, arb_id)
    if arb is None:
        raise HTTPException(
            status_code=404,
            detail={
                "type": "https://apex.example.com/problems/arb-not-found",
                "title": "ARB Submission Not Found",
                "status": 404,
                "detail": f"No ARB submission {arb_id} in project {project_id}.",
            },
        )
    return _arb_dict(arb)


@router.post(
    "/{project_id}/arb/{arb_id}/decision",
    summary="Record an ARB board decision (approve / reject / request-changes)",
)
async def decide_arb(
    project_id: uuid.UUID,
    arb_id: uuid.UUID,
    body: ArbDecisionRequest,
    db: DbSession,
    svc: Svc,
    principal: Annotated[Principal, Depends(require_persona(*_BOARD_PERSONAS))],
) -> dict[str, Any]:
    await _require_project(db, project_id)
    arb = await svc.get(project_id, arb_id)
    if arb is None:
        raise HTTPException(
            status_code=404,
            detail={
                "type": "https://apex.example.com/problems/arb-not-found",
                "title": "ARB Submission Not Found",
                "status": 404,
                "detail": f"No ARB submission {arb_id} in project {project_id}.",
            },
        )
    updated = await svc.decide(
        arb,
        decision=body.decision,
        reviewer=principal.subject,
        reviewer_persona=principal.persona,
        rationale=body.rationale,
    )
    return _arb_dict(updated)
